"""ORM models for the database."""
from app.core.config import app_config
from app.db.base import Base
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Integer, Text
from sqlalchemy.dialects import postgresql


class Chunk(Base):
    """ORM model of a document chunk, including metadata and vector embedding."""

    __tablename__ = "chunks"

    chunk_id = Column(Integer, primary_key=True, index=True)
    doc_name = Column(Text, nullable=False, index=True)
    section_headers = Column(postgresql.ARRAY(Text), nullable=True)
    pages = Column(postgresql.ARRAY(Integer), nullable=True)
    serialized_chunk = Column(Text, nullable=True)
    embedding = Column(Vector(app_config.EMBEDDING_DIM))
