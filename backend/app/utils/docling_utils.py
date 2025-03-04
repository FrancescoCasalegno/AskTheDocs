"""Utilities for parsing and chunking documents using docling library."""
import io
from logging import Logger

from app.core.middleware import job_id_contextvar
from docling.backend.docling_parse_v2_backend import DoclingParseV2DocumentBackend
from docling.chunking import BaseChunker
from docling.datamodel.base_models import DocumentStream
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, InputFormat, PdfFormatOption


def parse_and_chunk_pdf(
    pdf_filename: str, pdf_bytes: bytes, chunker: BaseChunker, logger: Logger
) -> list:
    """Parse PDF using docling, chunk it, return chunk objects."""
    job_id = job_id_contextvar.get()
    logger.info(f"[Job ID: {job_id}] Parsing document {pdf_filename} ...")
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options, backend=DoclingParseV2DocumentBackend
            )
        }
    )

    document_stream = DocumentStream(name=pdf_filename, stream=io.BytesIO(pdf_bytes))
    document = converter.convert(document_stream).document
    logger.info(f"[Job ID: {job_id}] Successfully parsed the document.")
    logger.info(f"[Job ID: {job_id}] Chunking document {pdf_filename} ...")
    chunks = chunker.chunk(document)
    logger.info(f"[Job ID: {job_id}] Successfully chunked the document.")
    return chunks
