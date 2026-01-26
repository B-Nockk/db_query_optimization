from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator

# Note: No import from main.py here!


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """
    Production-grade database dependency.
    Pulls the manager from app.state to support multiple app instances.
    """
    # We pull the manager instance created during lifespan
    manager = getattr(request.app.state, "db_manager", None)

    if not manager:
        # This handles cases where the dependency is called but lifespan didn't run
        raise RuntimeError(
            "DbManager not found in app.state. Ensure lifespan is configured."
        )

    async with manager.session() as session:
        yield session


get_session = get_db

__all__ = ["get_session", "get_db"]
