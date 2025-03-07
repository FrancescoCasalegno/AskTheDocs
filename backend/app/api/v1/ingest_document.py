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
    chunk_objects = await asyncio.to_thread(
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

        # Insert new chunk rows with their embeddings
        # 1. Create embedding tasks to run asynchronously
        async_tasks = []
        serialized_chunks = []
        for chunk_obj in chunk_objects:
            serialized_chunk = chunker.serialize(chunk=chunk_obj)
            serialized_chunks.append(serialized_chunk)
            async_tasks.append(embed_text(serialized_chunk))
        # 2. Run tasks concurrently
        logger.info(f"Started embedding {len(async_tasks)} chunks...")
        embeddings = await asyncio.gather(*async_tasks)
        logger.info(f"Successfully embedded all {len(embeddings)} chunks.")
        # 3. Create and add new rows to the database
        for chunk_obj, serialized_chunk, embedding_vector in zip(
            chunk_objects, serialized_chunks, embeddings
        ):
            pages = sorted(
                {prov.page_no for item in chunk_obj.meta.doc_items for prov in item.prov}
            )
            new_row = Chunk(
                doc_id=doc_id,
                origin_filename=chunk_obj.meta.origin.filename or file.filename,
                origin_uri=chunk_obj.meta.origin.uri or "",
                section_headers=list(chunk_obj.meta.headings or []),
                pages=pages,
                serialized_chunk=serialized_chunk,
                embedding=embedding_vector,
            )
            logger.info(f"Adding new row: {new_row}")
            db.add(new_row)

        await db.commit()
    except Exception as e:
        logger.error(f"Error inserting new rows into Chunk table: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    logger.info(f"Successfully inserted {len(chunk_objects)} new rows into Chunk table.")

    return {"status": "success", "doc_id": doc_id}
