"""Endpoint for deleting all rows from the database."""
from logging import getLogger

from app.db.models import Chunk
from app.db.session import get_db_session
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

logger = getLogger(__name__)
delete_all_chunks_router = APIRouter()


class DeleteAllChunksResponse(BaseModel):
    """Model for the response from the delete_all_chunks endpoint."""

    status: str
    n_deleted: int


@delete_all_chunks_router.delete(
    "/v1/delete_all_chunks", status_code=200, response_model=DeleteAllChunksResponse
)
async def delete_all_chunks(db: AsyncSession = Depends(get_db_session)):  # noqa: B008
    """Delete all rows from the chunks table."""
    logger.info("Deleting all rows from the Chunk table...")
    try:
        # Delete all records from the Chunk table
        result = await db.execute(delete(Chunk))
        num_deleted = result.rowcount if result.rowcount is not None else 0
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting all rows from the Chunk table: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

    logger.info("Successfully deleted all rows from the Chunk table.")
    return DeleteAllChunksResponse(status="success", n_deleted=num_deleted)
