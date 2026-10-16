import json

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import models
from ..ai_service import generate_rag_answer
from ..auth import get_current_user
from ..database import get_db
from ..vector_store import search_policy_chunks


router = APIRouter(
    prefix="/ai",
    tags=["AI Assistant"]
)


class AskRequest(BaseModel):
    question: str = Field(
        min_length=3,
        max_length=2000
    )

    policy_id: int

    session_id: int | None = None


def verify_policy_access(
    db: Session,
    policy_id: int,
    current_user: models.User
):
    policy = db.get(
        models.Policy,
        policy_id
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

    return policy


@router.post("/ask")
def ask_claimiq(
    payload: AskRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        get_current_user
    )
):
    verify_policy_access(
        db,
        payload.policy_id,
        current_user
    )

    session = None

    if payload.session_id is not None:
        session = db.get(
            models.ChatSession,
            payload.session_id
        )

        if not session:
            raise HTTPException(
                status_code=404,
                detail="Chat session not found"
            )

        if session.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Chat session access denied"
            )

    if session is None:
        session = models.ChatSession(
            user_id=current_user.id,
            policy_id=payload.policy_id,
            title=payload.question[:100]
        )

        db.add(session)
        db.commit()
        db.refresh(session)

    user_message = models.ChatMessage(
        session_id=session.id,
        role="user",
        content=payload.question
    )

    db.add(user_message)
    db.commit()

    matches = search_policy_chunks(
        question=payload.question,
        policy_id=payload.policy_id
    )

    source_list = []

    for match in matches:
        metadata = match["metadata"]

        source_list.append(
            {
                "document_id": metadata.get(
                    "document_id"
                ),
                "policy_id": metadata.get(
                    "policy_id"
                ),
                "filename": metadata.get(
                    "filename"
                ),
                "chunk_number": metadata.get(
                    "chunk_number"
                ),
                "distance": match["distance"],
            }
        )

    answer = generate_rag_answer(
        question=payload.question,
        matches=matches
    )

    source_json = json.dumps(
        source_list
    )

    assistant_message = models.ChatMessage(
        session_id=session.id,
        role="assistant",
        content=answer,
        sources=source_json
    )

    query_log = models.AIQueryLog(
        user_id=current_user.id,
        session_id=session.id,
        policy_id=payload.policy_id,
        question=payload.question,
        source_references=source_json
    )

    db.add(assistant_message)
    db.add(query_log)
    db.commit()

    return {
        "session_id": session.id,
        "question": payload.question,
        "answer": answer,
        "sources": source_list
    }