"""Endpoint for ingesting a document in the database."""
from logging import getLogger

from app.db.models import Chunk
from app.db.session import get_db
from app.utils.ai_utils import embed_text
from app.utils.docling_utils import parse_and_chunk_pdf
from docling.chunking import HybridChunker
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

logger = getLogger(__name__)

ingest_document_router = APIRouter()


@ingest_document_router.post("/v1/ingest_document")
def ingest_document(
    doc_id: str = Form(...),  # noqa: B008
    file: UploadFile = File(...),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
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
    pdf_bytes = file.file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty or invalid.")
    file.file.close()

    # Parse & chunk
    logger.info("Parsing and chunking the document...")
    chunker = HybridChunker()
    chunk_objects = parse_and_chunk_pdf(
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
        existing = db.query(Chunk).filter(Chunk.doc_id == doc_id).first()
        if existing:
            # Delete old rows with this doc_id
            db.query(Chunk).filter(Chunk.doc_id == doc_id).delete()

        # Insert new chunk rows
        for chunk_obj in chunk_objects:
            serialized = chunker.serialize(chunk=chunk_obj)
            pages = sorted(
                {prov.page_no for item in chunk_obj.meta.doc_items for prov in item.prov}
            )
            section_headers = list(chunk_obj.meta.headings)
            origin_filename = chunk_obj.meta.origin.filename or file.filename
            origin_uri = chunk_obj.meta.origin.uri or ""

            embedding_vector = embed_text(serialized)

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

        db.commit()
    except Exception as e:
        logger.error(f"Error inserting new rows into Chunk table: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    logger.info("Successfully inserted new rows into Chunk table.")

    return {"status": "success", "doc_id": doc_id}
