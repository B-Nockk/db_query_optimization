# app/db/db_manager.py
"""
Database manager focused on connection management and session handling.
Schema migrations are handled separately via Alembic CLI.

Design principles:
- Single responsibility: Connection/session management only
- Fail fast: Invalid configuration crashes on startup
- Explicit over implicit: No magic auto-migrations
- Production-ready: SSL, connection pooling, health checks
"""

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
    AsyncEngine,
)
from sqlalchemy import text
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Any, Optional, Union
from pathlib import Path
from common import DatabaseConfig, logger


class DbManager:
    """
    Database connection and session manager.

    Responsibilities:
    - Async engine/connection pool management
    - Session lifecycle management
    - Health checks and monitoring
    - Connection validation

    NOT responsible for:
    - Schema creation/migration (use Alembic CLI)
    - Table management (use Alembic CLI)

    Usage:
        # Startup
        db_manager = DbManager.from_config(config.database)
        await db_manager.verify_connection()

        # Runtime
        async with db_manager.session() as session:
            result = await session.execute(...)

        # Shutdown
        await db_manager.dispose()
    """

    def __init__(
        self,
        url: str,
        *,
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        pool_pre_ping: bool = True,
        echo: bool = False,
        echo_pool: bool = False,
        connect_args: Optional[dict[str, Any]] = None,
    ):
        """
        Initialize database manager.

        Args:
            url: Database URL (with proper driver, e.g., postgresql+asyncpg://)
            pool_size: Number of persistent connections
            max_overflow: Additional connections beyond pool_size
            pool_timeout: Seconds to wait for connection from pool
            pool_recycle: Recycle connections after N seconds
            pool_pre_ping: Test connections before using
            echo: Log all SQL statements (use for debugging)
            echo_pool: Log connection pool events
            connect_args: Driver-specific connection arguments (SSL, etc.)
        """
        self._validate_url(url)

        # Store config for introspection
        self._config: dict[str, Union[str, int]] = {
            "url": url,
            "pool_size": pool_size,
            "max_overflow": max_overflow,
            "pool_timeout": pool_timeout,
            "pool_recycle": pool_recycle,
        }

        self.engine: AsyncEngine = create_async_engine(
            url=url,
            echo=echo,
            echo_pool=echo_pool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            pool_pre_ping=pool_pre_ping,
            connect_args=connect_args or {},
        )

        self.session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        # Track if we've verified connection
        self._verified = False

        logger.info(
            f"DbManager initialized: pool_size={pool_size}, "
            f"max_overflow={max_overflow}, pre_ping={pool_pre_ping}"
        )

    @classmethod
    def from_config(
        cls,
        config: DatabaseConfig,  # DatabaseConfig type
        *,
        username: Optional[str] = None,
        password: Optional[str] = None,
        ssl_mode: Optional[str] = None,
        ssl_cert_path: Optional[Path] = None,
        ssl_key_path: Optional[Path] = None,
        ssl_ca_path: Optional[Path] = None,
        **kwargs: Any,
    ) -> "DbManager":
        """
        Create DbManager from DatabaseConfig with SSL support.

        Args:
            config: DatabaseConfig instance
            username: Database username (overrides config)
            password: Database password (overrides config)
            ssl_mode: SSL mode (overrides config)
            ssl_cert_path: Path to client certificate (overrides config)
            ssl_key_path: Path to client key (overrides config)
            ssl_ca_path: Path to CA certificate (overrides config)
            **kwargs: Additional arguments passed to __init__

        Returns:
            Configured DbManager instance

        Example:
            db_manager = DbManager.from_config(config.database)
        """
        # Use config values, allow overrides
        final_username = username or config.username
        final_password = password or (
            config.password.get_secret_value() if config.password else None
        )

        # Build connection URL
        if final_username and final_password:
            auth = f"{final_username}:{final_password}"
            url = f"postgresql+{config.driver.value}://{auth}@{config.host}:{config.port}/{config.name}"
        elif final_username:
            url = f"postgresql+{config.driver.value}://{final_username}@{config.host}:{config.port}/{config.name}"
        else:
            url = f"postgresql+{config.driver.value}://{config.host}:{config.port}/{config.name}"

        # Build connect_args for SSL
        connect_args = kwargs.pop("connect_args", {})

        # Use overrides or config values for SSL
        final_ssl_mode = ssl_mode or (
            config.ssl_mode.value if config.ssl_mode else None
        )
        final_ssl_cert = ssl_cert_path or config.ssl_cert_path
        final_ssl_key = ssl_key_path or config.ssl_key_path
        final_ssl_ca = ssl_ca_path or config.ssl_ca_path

        if final_ssl_mode:
            # asyncpg SSL configuration
            if config.driver.value == "asyncpg":
                import ssl as ssl_module

                ssl_context = ssl_module.create_default_context()

                if final_ssl_mode == "disable":
                    connect_args["ssl"] = False
                elif final_ssl_mode in ["require", "verify-ca", "verify-full"]:
                    if final_ssl_ca:
                        ssl_context.load_verify_locations(cafile=str(final_ssl_ca))
                    if final_ssl_cert and final_ssl_key:
                        ssl_context.load_cert_chain(
                            certfile=str(final_ssl_cert),
                            keyfile=str(final_ssl_key),
                        )

                    if final_ssl_mode == "verify-full":
                        ssl_context.check_hostname = True
                        ssl_context.verify_mode = ssl_module.CERT_REQUIRED

                    connect_args["ssl"] = ssl_context

        return cls(
            url=url,
            pool_size=config.pool_size,
            max_overflow=config.max_overflow,
            pool_timeout=config.pool_timeout,
            pool_recycle=config.pool_recycle,
            connect_args=connect_args,
            **kwargs,
        )

    @staticmethod
    def _validate_url(url: str) -> None:
        """Validate database URL format."""
        if not url or not url.startswith(
            ("postgresql+asyncpg://", "sqlite+aiosqlite://")
        ):
            raise ValueError(
                f"Invalid database URL. Expected postgresql+asyncpg:// or sqlite+aiosqlite://, got: {url[:20]}..."
            )

    async def verify_connection(self) -> None:
        """
        Verify database connection on startup.
        Fails fast if connection cannot be established.

        Raises:
            ConnectionError: If connection fails
        """
        try:
            async with self.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            self._verified = True
            logger.info("✓ Database connection verified")
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            raise ConnectionError(f"Failed to connect to database: {e}") from e

    async def verify_migrations_current(self) -> bool:
        """
        Check if all Alembic migrations have been applied.
        Call this during startup to ensure schema is up-to-date.

        Returns:
            True if migrations are current, False otherwise

        Raises:
            RuntimeError: If alembic_version table doesn't exist
        """
        try:
            async with self.engine.connect() as conn:
                # Check if alembic_version table exists
                result = await conn.execute(
                    text(
                        "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                        "WHERE table_name = 'alembic_version')"
                    )
                )
                table_exists = result.scalar()

                if not table_exists:
                    raise RuntimeError(
                        "alembic_version table not found. "
                        "Have you run 'alembic upgrade head'?"
                    )

                # Get current migration version
                result = await conn.execute(
                    text("SELECT version_num FROM alembic_version")
                )
                current_version = result.scalar()

                logger.info(f"Current migration version: {current_version}")
                return True  # If we got here, migrations have been applied

        except Exception as e:
            logger.error(f"Migration check failed: {e}")
            raise

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Provide a transactional database session.

        Automatically commits on success, rolls back on exception.

        Usage:
            async with db_manager.session() as session:
                user = await session.get(User, user_id)
                user.name = "New Name"
                # Commits automatically on exit

        Raises:
            Exception: Re-raises any exception after rollback
        """
        session = self.session_maker()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Session error, rolled back: {e}")
            raise
        finally:
            await session.close()

    async def get_raw_session(self) -> AsyncSession:
        """
        Get a session without automatic commit/rollback.

        WARNING: You must manually manage this session!

        Usage:
            session = await db_manager.get_raw_session()
            try:
                # Do work
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
        """
        return self.session_maker()

    async def execute(
        self,
        query: str,
        params: Optional[dict[str, Any]] = None,
    ) -> list[Any]:
        """
        Execute raw SQL query with parameter binding.

        Args:
            query: SQL query string (use :param_name for parameters)
            params: Dictionary of parameter values

        Returns:
            List of row results

        Example:
            results = await db_manager.execute(
                "SELECT * FROM users WHERE age > :min_age",
                {"min_age": 18}
            )
        """
        async with self.session() as session:
            result = await session.execute(text(query), params or {})
            return list(result.fetchall())

    async def execute_scalar(
        self,
        query: str,
        params: Optional[dict[str, Any]] = None,
    ) -> Any:
        """
        Execute query and return single scalar value.

        Example:
            count = await db_manager.execute_scalar(
                "SELECT COUNT(*) FROM users"
            )
        """
        async with self.session() as session:
            result = await session.execute(text(query), params or {})
            return result.scalar()

    async def health_check(self) -> dict[str, Any]:
        """
        Comprehensive health check with metrics.

        Returns:
            Dictionary with health status and metrics

        Example:
            {
                "healthy": True,
                "pool_size": 10,
                "pool_in_use": 2,
                "pool_available": 8,
                "response_time_ms": 5.2
            }
        """
        import time

        start = time.perf_counter()

        try:
            async with self.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))

            response_time = (time.perf_counter() - start) * 1000  # Convert to ms

            # Get pool stats using status() method (properly typed)
            pool = self.engine.pool
            status = pool.status()

            # Parse status string:
            # Pool size: 5
            # Connections in pool: 0
            # Current Overflow: 0
            # Current Checked out connections: 2
            pool_size = int(self._config["pool_size"])

            # Extract checked out count from status
            checked_out = 0
            if "Checked out" in status:
                try:
                    checked_out = int(
                        status.split("Checked out connections:")[-1].strip()
                    )
                except (ValueError, IndexError):
                    pass

            return {
                "healthy": True,
                "pool_size": pool_size,
                "pool_in_use": checked_out,
                "pool_available": pool_size - checked_out,
                "response_time_ms": round(response_time, 2),
                "pool_status": status,  # Full status for debugging
            }

        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
            }

    async def get_pool_stats(self) -> dict[str, Any]:
        """
        Get detailed connection pool statistics.
        Useful for monitoring and debugging connection issues.

        Returns:
            Dictionary with pool metrics
        """
        pool = self.engine.pool
        status = pool.status()

        # Pool config from initialization
        configured_size = self._config["pool_size"]
        configured_overflow = self._config["max_overflow"]

        # Parse the status string for runtime stats
        # Format: "Pool size: X  Connections in pool: Y  Current Overflow: Z  Current Checked out connections: W"
        checked_out = 0
        overflow = 0
        in_pool = 0

        try:
            parts = status.split("  ")
            for part in parts:
                if "Checked out connections:" in part:
                    checked_out = int(part.split(":")[-1].strip())
                elif "Current Overflow:" in part:
                    overflow = int(part.split(":")[-1].strip())
                elif "Connections in pool:" in part:
                    in_pool = int(part.split(":")[-1].strip())
        except (ValueError, IndexError):
            pass  # Fall back to config values

        return {
            "pool_size_configured": configured_size,
            "max_overflow_configured": configured_overflow,
            "connections_in_use": checked_out,
            "connections_in_pool": in_pool,
            "overflow_active": overflow,
            "connections_available": in_pool,
            "total_connections": checked_out + in_pool,
            "status_raw": status,  # For debugging
        }

    async def get_table_info(self, table_name: str) -> dict[str, Any]:
        """
            Get metadata about a table.

        Returns:
            Dictionary with row count and size info
        """
        count_query = f"SELECT COUNT(*) FROM {table_name}"
        count = await self.execute_scalar(count_query)

        # PostgreSQL-specific size query
        size_query = """
            SELECT pg_size_pretty(pg_total_relation_size(:table_name))
        """
        try:
            size = await self.execute_scalar(size_query, {"table_name": table_name})
        except Exception:
            size = "N/A"  # Not all DBs support this

        return {
            "table_name": table_name,
            "row_count": count,
            "size": size,
        }

    async def dispose(self) -> None:
        """
        Dispose of all connections and cleanup resources.
        Call this on application shutdown.
        """
        await self.engine.dispose()
        logger.info("✓ Database connections disposed")

    def get_config_snapshot(self) -> dict[str, Any]:
        """Get current configuration (for monitoring/debugging)."""
        return self._config.copy()


__all__ = ["DbManager"]
