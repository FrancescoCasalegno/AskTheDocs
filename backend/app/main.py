"""Main FastAPI application."""
from contextlib import asynccontextmanager

from app.api.v1.delete_all_chunks import delete_all_chunks_router
from app.api.v1.ingest_document import ingest_document_router
from app.api.v1.query import query_router
from app.core.config import app_config
from app.core.log_config import set_logging_options
from app.core.middleware import JobIdMiddleware
from app.db.session import init_db
from fastapi import FastAPI

# Set logging options and formatting
set_logging_options(level=app_config.LOGGING_LEVEL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Context manager to handle application startup and shutdown."""
    # 1. Startup (initialize db, etc.)
    await init_db()

    # 2. Run the application
    yield

    # 3. Shutdown and cleanup (if needed)
    pass


app = FastAPI(lifespan=lifespan)

# Include routers
app.include_router(ingest_document_router)
app.include_router(query_router)
app.include_router(delete_all_chunks_router)

# Include middleware
app.add_middleware(JobIdMiddleware)
