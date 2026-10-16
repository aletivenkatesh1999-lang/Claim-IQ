from pathlib import Path

from fastapi import HTTPException
from pypdf import PdfReader

from .config import settings


def extract_text_from_pdf(file_path: Path) -> str:
    try:
        reader = PdfReader(str(file_path))
        extracted_pages = []

        for page_number, page in enumerate(reader.pages, start=1):
            page_text = (page.extract_text() or "").strip()

            if page_text:
                extracted_pages.append(
                    f"[Page {page_number}]\n{page_text}"
                )

        full_text = "\n\n".join(extracted_pages).strip()

        if not full_text:
            raise HTTPException(
                status_code=422,
                detail=(
                    "No readable text was found. "
                    "The PDF may be scanned and require OCR."
                ),
            )

        return full_text

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Unable to extract text from PDF: {str(exc)}",
        )


def clean_text(text: str) -> str:
    cleaned_lines = []

    for line in text.splitlines():
        cleaned_line = " ".join(line.split())

        if cleaned_line:
            cleaned_lines.append(cleaned_line)

    return "\n".join(cleaned_lines)


def chunk_text(text: str) -> list[str]:
    chunk_size = settings.chunk_size
    overlap = settings.chunk_overlap

    if chunk_size <= 0:
        raise ValueError(
            "CHUNK_SIZE must be greater than zero"
        )

    if overlap < 0:
        raise ValueError(
            "CHUNK_OVERLAP cannot be negative"
        )

    if overlap >= chunk_size:
        raise ValueError(
            "CHUNK_OVERLAP must be less than CHUNK_SIZE"
        )

    words = text.split()

    if not words:
        return []

    chunks = []
    start = 0

    while start < len(words):
        end = min(
            start + chunk_size,
            len(words),
        )

        chunk = " ".join(
            words[start:end]
        ).strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(words):
            break

        start = end - overlap

    return chunks


def process_pdf(file_path: Path) -> list[str]:
    extracted_text = extract_text_from_pdf(
        file_path
    )

    cleaned_text = clean_text(
        extracted_text
    )

    chunks = chunk_text(
        cleaned_text
    )

    if not chunks:
        raise HTTPException(
            status_code=422,
            detail="Document produced no usable chunks",
        )

    return chunks