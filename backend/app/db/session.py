"""Database session setup."""
from app.core.config import app_config
from app.db.base import Base
from sqlalchemy import create_engine, sql
from sqlalchemy.orm import sessionmaker

engine = create_engine(url=app_config.POSTGRES_DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database with extensions and tables."""
    # Install the `vector` (aka pgvector) extension if it doesn't exist
    with SessionLocal() as session:
        session.execute(sql.text("CREATE EXTENSION IF NOT EXISTS vector"))
        session.commit()
    # Create the tables if they don't exist
    Base.metadata.create_all(bind=engine)


def get_db():
    """Context manager to handle database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
