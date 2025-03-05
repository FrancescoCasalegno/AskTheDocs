"""Endpoint for deleting all rows from the database."""
from logging import getLogger

from app.db.models import Chunk
from app.db.session import get_db
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

logger = getLogger(__name__)

delete_all_chunks_router = APIRouter()


class DeleteAllChunksResponse(BaseModel):
    """Model for the response from the delete_all_chunks endpoint."""

    status: str
    n_deleted: int


@delete_all_chunks_router.delete(
    "/v1/delete_all_chunks", status_code=200, response_model=DeleteAllChunksResponse
)
def delete_all_chunks(db: Session = Depends(get_db)):  # noqa: B008
    """Delete all rows from the chunks table."""
    logger.info("Deleting all rows from the Chunk table...")
    try:
        # Delete all records from the Chunk table
        num_deleted = db.query(Chunk).delete()
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting all rows from the Chunk table: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

    logger.info("Successfully deleted all rows from the Chunk table.")
    return DeleteAllChunksResponse(status="success", n_deleted=num_deleted)
