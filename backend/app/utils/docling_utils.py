import io
from docling.datamodel.base_models import DocumentStream
from docling.backend.docling_parse_v2_backend import DoclingParseV2DocumentBackend
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, InputFormat, PdfFormatOption
from docling.chunking import BaseChunker

def parse_and_chunk_pdf(pdf_filename:str, pdf_bytes: bytes, chunker: BaseChunker):
    """Parse PDF using docling, chunk it, return chunk objects."""
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options,
                backend=DoclingParseV2DocumentBackend
            )
        }
    )

    document_stream = DocumentStream(
        name=pdf_filename,
        stream=io.BytesIO(pdf_bytes)
    )
    document = converter.convert(document_stream).document
    return chunker.chunk(document)
