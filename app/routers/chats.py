from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from sqlalchemy.orm import Session

from .. import models
from ..auth import get_current_user
from ..database import get_db


router = APIRouter(
    prefix="/chats",
    tags=["Chats"]
)


@router.get("/")
def list_chat_sessions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        get_current_user
    )
):
    sessions = (
        db.query(models.ChatSession)
        .filter(
            models.ChatSession.user_id
            == current_user.id
        )
        .order_by(
            models.ChatSession.id.desc()
        )
        .all()
    )

    return [
        {
            "id": session.id,
            "title": session.title,
            "policy_id": session.policy_id,
            "claim_id": session.claim_id,
            "created_at": session.created_at,
        }
        for session in sessions
    ]


@router.get("/{session_id}")
def get_chat_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        get_current_user
    )
):
    session = db.get(
        models.ChatSession,
        session_id
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

    messages = (
        db.query(models.ChatMessage)
        .filter(
            models.ChatMessage.session_id
            == session.id
        )
        .order_by(
            models.ChatMessage.id
        )
        .all()
    )

    return {
        "id": session.id,
        "title": session.title,
        "policy_id": session.policy_id,
        "claim_id": session.claim_id,
        "created_at": session.created_at,
        "messages": [
            {
                "id": message.id,
                "role": message.role,
                "content": message.content,
                "sources": message.sources,
                "created_at": message.created_at,
            }
            for message in messages
        ]
    }