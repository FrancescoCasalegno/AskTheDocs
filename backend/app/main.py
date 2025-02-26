"""Main FastAPI application."""
from contextlib import asynccontextmanager

from app.api.v1.delete_all_chunks import delete_all_chunks_router
from app.api.v1.ingest_document import ingest_document_router
from app.api.v1.query import query_router
from app.db.session import init_db
from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Context manager to handle application startup and shutdown."""
    # 1. Startup
    # Initialize DB, create tables, install pgvector extension
    init_db()

    yield  # run the application

    # 2. Shutdown
    # (Any cleanup if needed)
    pass


app = FastAPI(lifespan=lifespan)

# Include routers
app.include_router(ingest_document_router)
app.include_router(query_router)
app.include_router(delete_all_chunks_router)
