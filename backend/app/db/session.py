"""Database session setup."""
from app.core.config import app_config
from app.db.base import Base
from sqlalchemy import sql
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

engine = create_async_engine(url=app_config.POSTGRES_DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(
    bind=engine, autocommit=False, autoflush=False, expire_on_commit=False
)


async def init_db():
    """Initialize database with extensions and tables."""
    async with engine.begin() as conn:
        # 1. Install the pgvector extension
        await conn.execute(sql.text("CREATE EXTENSION IF NOT EXISTS vector"))

        # 2. Create tables if they don't exist
        # Use run_sync() to run synchronous code in an async context!
        await conn.run_sync(Base.metadata.create_all)


async def get_db_session():
    """Async context manager for database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            # The session is closed automatically by exiting the 'async with' block
            pass
