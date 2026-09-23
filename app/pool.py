import asyncpg
from app.config import Config

_pool: asyncpg.Pool | None = None


async def init_pool(config: Config) -> None:
    """Initialize the global asyncpg connection pool."""

    global _pool
    _pool = await asyncpg.create_pool(
        config.database_url,
        min_size=config.db_pool_min,
        max_size=config.db_pool_max,
    )


async def close_pool() -> None:
    """Close the global asyncpg pool if it has been initialized."""

    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    """Return the initialized database pool or raise a clear setup error."""

    if _pool is None:
        raise RuntimeError("Database pool not initialized")
    return _pool
