from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import Chunk
from app.utils.docling_utils import parse_and_chunk_pdf
from app.utils.ai_utils import embed_text

from docling.chunking import HybridChunker

ingest_document_router = APIRouter()

def get_db():
    """
    Dependency that provides a transactional session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@ingest_document_router.post("/v1/ingest_document")
def ingest_document(
    doc_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    1) Receives PDF file + doc_id
    2) Parses/Chunks via docling
    3) Embeds each chunk
    4) Replaces existing doc_id data or inserts new
    5) Returns success
    """
    # Read the PDF bytes
    pdf_bytes = file.file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty or invalid.")
    file.file.close()

    # Parse & chunk
    chunker = HybridChunker()
    chunk_objects = parse_and_chunk_pdf(
        pdf_filename=file.filename, 
        pdf_bytes=pdf_bytes, 
        chunker=chunker)

    # Single transaction
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
                set(prov.page_no for item in chunk_obj.meta.doc_items for prov in item.prov)
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
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "success", "doc_id": doc_id}

