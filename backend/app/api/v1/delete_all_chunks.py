"""Endpoint for deleting all rows from the database."""
from logging import getLogger

from app.core.config import app_config
from app.core.log_config import set_logging_options
from app.core.middleware import job_id_contextvar
from app.db.models import Chunk
from app.db.session import get_db
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

set_logging_options(level=app_config.LOGGING_LEVEL)
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
    job_id = job_id_contextvar.get()
    logger.info(f"[Job ID: {job_id}] Deleting all rows from the Chunk table...")
    try:
        # Delete all records from the Chunk table
        num_deleted = db.query(Chunk).delete()
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"[Job ID: {job_id}] Error deleting all rows from the Chunk table: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

    logger.info(f"[Job ID: {job_id}] Successfully deleted all rows from the Chunk table.")
    return DeleteAllChunksResponse(status="success", n_deleted=num_deleted)
