set[str]
list[str]
list[dict]
import re

from sqlalchemy.orm import Session

from models import (
    Document,
    DocumentChunk
)


def tokenize(
    text: str
) -> set[str]:
    return set(
        re.findall(
            r"[a-zA-Z0-9]+",
            text.lower()
        )
    )


def create_chunks(
    text: str,
    size: int = 300,
    overlap: int = 50
) -> list[str]:
    words = text.split()
    chunks = []

    if not words:
        return chunks

    start = 0

    while start < len(words):
        end = start + size

        chunks.append(
            " ".join(
                words[start:end]
            )
        )

        if end >= len(words):
            break

        start += size - overlap

    return chunks


def retrieve_chunks(
    db: Session,
    question: str,
    top_k: int = 3
) -> list[dict]:
    question_tokens = tokenize(
        question
    )

    rows = (
        db.query(
            DocumentChunk,
            Document
        )
        .join(
            Document,
            Document.id
            == DocumentChunk.document_id
        )
        .filter(
            Document.active.is_(True)
        )
        .all()
    )

    results = []

    for chunk, document in rows:
        chunk_tokens = tokenize(
            chunk.content
        )

        matched_words = (
            question_tokens
            .intersection(chunk_tokens)
        )

        score = (
            len(matched_words)
            / max(
                1,
                len(question_tokens)
            )
        )

        if score > 0:
            results.append(
                {
                    "score": score,
                    "chunk": chunk,
                    "document": document
                }
            )

    results.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return results[:top_k]


def answer_question(
    db: Session,
    question: str
) -> dict:
    results = retrieve_chunks(
        db,
        question,
        top_k=3
    )

    if not results:
        return {
            "answer": (
                "No relevant information was found "
                "in the approved policy documents."
            ),
            "sources": [],
            "matched": False
        }

    answer_parts = []
    sources = []

    for result in results:
        chunk = result["chunk"]
        document = result["document"]

        answer_parts.append(
            chunk.content
        )

        sources.append(
            {
                "document": document.filename,
                "section": chunk.section,
                "chunk_number": (
                    chunk.chunk_number
                ),
                "score": round(
                    result["score"],
                    3
                )
            }
        )

    return {
        "answer": (
            "\n\n".join(answer_parts)
        )[:2500],
        "sources": sources,
        "matched": True
    }