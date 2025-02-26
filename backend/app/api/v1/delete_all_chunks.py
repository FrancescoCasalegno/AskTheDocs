from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import Chunk

delete_all_chunks_router = APIRouter()

class DeleteAllChunksResponse(BaseModel):
    status: str
    n_deleted: int


def get_db():
    """
    Dependency that provides a transactional session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@delete_all_chunks_router.delete("/v1/delete_all_chunks", status_code=200, response_model=DeleteAllChunksResponse)
def delete_all_chunks(db: Session = Depends(get_db)):
    """
    Deletes all rows from the chunks table.
    """
    try:
        # Delete all records from the Chunk table
        num_deleted = db.query(Chunk).delete()
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
    return DeleteAllChunksResponse(status="success", n_deleted=num_deleted)
