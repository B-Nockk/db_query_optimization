"""
Alembic environment configuration.
Uses the same DatabaseConfig as the application for consistency.
"""

import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db.models import DbBaseModel
from common.config.initialize_config import (
    get_config,
    initialize_config,
    ConfigurationError,
)

load_dotenv()
try:
    initialize_config()
except ConfigurationError as e:
    # Can't use logger yet, but that's OK - this is a fatal startup error
    print(f"FATAL: Configuration error:\n{e}")
    import sys

    sys.exit(1)
# Alembic Config object
config = context.config

# Load app configuration (includes database config)
app_config = get_config()

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate
target_metadata = DbBaseModel.metadata


def get_sync_url() -> str:
    """
    Get synchronous database URL for Alembic.

    Alembic needs a sync URL even though the app uses async.
    This converts asyncpg -> psycopg2 for migrations.
    """
    if not app_config.database:
        raise RuntimeError("Database configuration not found in environment")

    db_config = app_config.database

    # Build the sync URL using config values
    # Convert asyncpg to psycopg2 (sync driver for Alembic)
    if db_config.driver.value == "asyncpg":
        driver = "postgresql"  # Uses psycopg2 by default
    elif db_config.driver.value == "psycopg":
        driver = "postgresql+psycopg"
    elif db_config.driver.value == "aiosqlite":
        driver = "sqlite"
    else:
        driver = db_config.driver.value

    # Build URL with credentials
    if db_config.username and db_config.password:
        password = db_config.password.get_secret_value()
        url = f"{driver}://{db_config.username}:{password}@{db_config.host}:{db_config.port}/{db_config.name}"
    elif db_config.username:
        url = f"{driver}://{db_config.username}@{db_config.host}:{db_config.port}/{db_config.name}"
    else:
        url = f"{driver}://{db_config.host}:{db_config.port}/{db_config.name}"

    return url


def get_connect_args() -> dict:
    """
    Get connection arguments including SSL configuration.

    Returns the same SSL settings used by the application.
    """
    if not app_config.database:
        return {}

    db_config = app_config.database
    connect_args = {}

    # SSL configuration (psycopg2 uses different params than asyncpg)
    if db_config.ssl_mode:
        ssl_mode = db_config.ssl_mode.value

        if ssl_mode == "disable":
            connect_args["sslmode"] = "disable"
        elif ssl_mode in ["require", "verify-ca", "verify-full"]:
            connect_args["sslmode"] = ssl_mode

            # Add certificate paths if provided
            if db_config.ssl_ca_path:
                connect_args["sslrootcert"] = str(db_config.ssl_ca_path)
            if db_config.ssl_cert_path:
                connect_args["sslcert"] = str(db_config.ssl_cert_path)
            if db_config.ssl_key_path:
                connect_args["sslkey"] = str(db_config.ssl_key_path)

    return connect_args


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine.
    Calls to context.execute() emit SQL to script output.
    """
    url = get_sync_url()

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    Creates an Engine and associates a connection with the context.
    Uses the same database configuration as the application.
    """
    # Get sync URL from our config
    sync_url = get_sync_url()

    # Get SSL/connection args
    connect_args = get_connect_args()

    # Build configuration for engine
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = sync_url

    # Create engine with NullPool (important for migrations)
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=connect_args,  # Include SSL settings
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


# Run migrations
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
