"""
PDF parsing using LlamaParse (handles both text PDFs and scanned image PDFs via OCR).
Falls back to pdfminer for simple text PDFs when LlamaParse is unavailable.
"""
import os
from dataclasses import dataclass
from typing import Optional

from backend.config import get_settings

settings = get_settings()


@dataclass
class ParsedDocument:
    text: str
    pages: list[str]
    metadata: dict


async def parse_pdf(pdf_path: str) -> ParsedDocument:
    """
    Parse a PDF file using LlamaParse.
    Handles both text-based and image/scanned PDFs (OCR).
    """
    try:
        return await _parse_with_llamaparse(pdf_path)
    except Exception as e:
        print(f"[parser] LlamaParse failed ({e}), falling back to pdfminer")
        return await _parse_with_pdfminer(pdf_path)


async def _parse_with_llamaparse(pdf_path: str) -> ParsedDocument:
    from llama_parse import LlamaParse
    from llama_index.core import SimpleDirectoryReader

    parser = LlamaParse(
        api_key=settings.llama_cloud_api_key,
        result_type="markdown",          # preserves table structure
        num_workers=1,
        verbose=False,
        language="en",
    )

    file_extractor = {".pdf": parser}
    documents = await SimpleDirectoryReader(
        input_files=[pdf_path],
        file_extractor=file_extractor,
    ).aload_data()

    full_text = "\n\n".join([doc.text for doc in documents])
    pages = [doc.text for doc in documents]

    return ParsedDocument(
        text=full_text,
        pages=pages,
        metadata={
            "source": pdf_path,
            "num_pages": len(pages),
            "parser": "llamaparse",
        },
    )


async def _parse_with_pdfminer(pdf_path: str) -> ParsedDocument:
    """Fallback: simple text extraction using pdfminer.six"""
    try:
        from pdfminer.high_level import extract_pages
        from pdfminer.layout import LTTextContainer
        pages = []
        for page_layout in extract_pages(pdf_path):
            page_text = ""
            for element in page_layout:
                if isinstance(element, LTTextContainer):
                    page_text += element.get_text()
            pages.append(page_text)
        full_text = "\n\n".join(pages)
    except Exception:
        full_text = ""
        pages = []

    return ParsedDocument(
        text=full_text,
        pages=pages,
        metadata={"source": pdf_path, "parser": "pdfminer"},
    )


async def parse_pdf_from_url(url: str) -> ParsedDocument:
    """Download a PDF from a URL and parse it."""
    import httpx
    import tempfile

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url)
        resp.raise_for_status()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(resp.content)
        tmp_path = tmp.name

    try:
        result = await parse_pdf(tmp_path)
        result.metadata["url"] = url
        return result
    finally:
        os.unlink(tmp_path)
