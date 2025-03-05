"""Utilities for parsing and chunking documents using docling library."""
import io
from logging import Logger
from pathlib import Path

from docling.backend.docling_parse_v2_backend import DoclingParseV2DocumentBackend
from docling.chunking import BaseChunker
from docling.datamodel.base_models import DocumentStream
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, InputFormat, PdfFormatOption


def parse_and_chunk_pdf(
    pdf_filename: str, pdf_bytes: bytes, chunker: BaseChunker, logger: Logger
) -> list:
    """Parse PDF using docling, chunk it, return chunk objects."""
    logger.info(f"Parsing document {pdf_filename} ...")
    docling_models_path = Path.home() / ".cache" / "docling" / "models"
    pipeline_options = PdfPipelineOptions(artifacts_path=docling_models_path)
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
    logger.info("Successfully parsed the document.")
    logger.info(f"Chunking document {pdf_filename} ...")
    chunks = chunker.chunk(document)
    logger.info("Successfully chunked the document.")
    return chunks
