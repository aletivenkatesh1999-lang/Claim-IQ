from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import models
from ..auth import get_current_user
from ..config import settings
from ..database import get_db
from ..dependencies import officer_or_admin
from ..document_processor import process_pdf
from ..vector_store import (
    index_policy_chunks,
    search_policy_chunks,
)


router = APIRouter(
    prefix="/rag",
    tags=["RAG"]
)


class SearchRequest(BaseModel):
    question: str = Field(
        min_length=3,
        max_length=2000
    )

    policy_id: int | None = None


@router.post(
    "/policy-documents/{document_id}/process"
)
def process_policy_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        officer_or_admin
    )
):
    document = db.get(
        models.PolicyDocument,
        document_id
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Policy document not found"
        )

    if document.content_type != "application/pdf":
        raise HTTPException(
            status_code=415,
            detail="RAG processing currently supports PDF files only"
        )

    file_path = (
        Path(settings.upload_dir)
        / "policies"
        / document.stored_filename
    )

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Stored PDF file not found"
        )

    chunks = process_pdf(
        file_path
    )

    chunk_count = index_policy_chunks(
        document_id=document.id,
        policy_id=document.policy_id,
        filename=document.original_filename,
        chunks=chunks
    )

    return {
        "message": "Policy document processed successfully",
        "document_id": document.id,
        "policy_id": document.policy_id,
        "filename": document.original_filename,
        "chunk_count": chunk_count
    }


@router.post(
    "/search"
)
def search_policy_documents(
    payload: SearchRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        get_current_user
    )
):
    if payload.policy_id is not None:
        policy = db.get(
            models.Policy,
            payload.policy_id
        )

        if not policy:
            raise HTTPException(
                status_code=404,
                detail="Policy not found"
            )

        if (
            current_user.role == models.UserRole.user
            and policy.owner_id != current_user.id
        ):
            raise HTTPException(
                status_code=403,
                detail="Policy access denied"
            )

    matches = search_policy_chunks(
        question=payload.question,
        policy_id=payload.policy_id
    )

    return {
        "question": payload.question,
        "matches": matches
    }