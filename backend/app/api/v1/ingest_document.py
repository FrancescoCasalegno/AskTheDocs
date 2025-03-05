"""Endpoint for ingesting a document in the database."""
import asyncio
from logging import getLogger

from app.db.models import Chunk
from app.db.session import get_db_session
from app.utils.ai_utils import embed_text
from app.utils.docling_utils import parse_and_chunk_pdf
from docling.chunking import HybridChunker
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = getLogger(__name__)

ingest_document_router = APIRouter()


@ingest_document_router.post("/v1/ingest_document")
async def ingest_document(
    doc_id: str = Form(...),  # noqa: B008
    file: UploadFile = File(...),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
):
    """Ingest a document into the database.

    Breakdown:
    1) Receive PDF file + doc_id
    2) Parse/Chunk document
    3) Embed each chunk
    4) Replace existing doc_id data or inserts new
    5) Return success
    """
    logger.info(f"Ingesting document with doc_id: {doc_id} and filename: {file.filename}")
    # Read the PDF bytes
    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty or invalid.")
    await file.close()

    # Parse & chunk
    logger.info("Parsing and chunking the document...")
    chunker = HybridChunker()
    # Run parsing in a separate thread, because it's slow (CPU-bound)
    chunk_objects = asyncio.to_thread(
        parse_and_chunk_pdf,
        pdf_filename=file.filename,
        pdf_bytes=pdf_bytes,
        chunker=chunker,
        logger=logger,
    )
    logger.info("Successfully parsed and chunked the document.")

    # Single transaction
    logger.info("Start transaction: Inserting new rows into Chunk table...")
    try:
        # Check if doc_id already exists
        select_query = select(Chunk).filter(Chunk.doc_id == doc_id)
        existing = (await db.execute(select_query)).scalars().first()
        if existing:
            # Delete old rows with this doc_id
            delete_query = delete(Chunk).filter(Chunk.doc_id == doc_id)
            await db.execute(delete_query)

        # Insert new chunk rows
        for chunk_obj in chunk_objects:
            serialized = chunker.serialize(chunk=chunk_obj)
            pages = sorted(
                {prov.page_no for item in chunk_obj.meta.doc_items for prov in item.prov}
            )
            section_headers = list(chunk_obj.meta.headings)
            origin_filename = chunk_obj.meta.origin.filename or file.filename
            origin_uri = chunk_obj.meta.origin.uri or ""

            embedding_vector = await embed_text(serialized)

            new_row = Chunk(
                doc_id=doc_id,
                origin_filename=origin_filename,
                origin_uri=origin_uri,
                section_headers=section_headers,
                pages=pages,
                serialized_chunk=serialized,
                embedding=embedding_vector,
            )
            db.add(new_row)

        await db.commit()
    except Exception as e:
        logger.error(f"Error inserting new rows into Chunk table: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    logger.info("Successfully inserted new rows into Chunk table.")

    return {"status": "success", "doc_id": doc_id}
