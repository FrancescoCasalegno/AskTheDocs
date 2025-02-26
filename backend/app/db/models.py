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
    doc_id = Column(Text, nullable=False, index=True)

    origin_filename = Column(Text, nullable=True)
    origin_uri = Column(Text, nullable=True)

    # For arrays, we'll store them as Postgres arrays
    section_headers = Column(postgresql.ARRAY(Text), nullable=True)
    pages = Column(postgresql.ARRAY(Integer), nullable=True)

    serialized_chunk = Column(Text, nullable=True)

    # Vector column using pgvector
    # dimension must match the embedding dimension
    embedding = Column(Vector(app_config.EMBEDDING_DIM))
