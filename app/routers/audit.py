from fastapi import (
    APIRouter,
    Depends,
    Query,
)

from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..dependencies import admin_only


router = APIRouter(
    prefix="/audit",
    tags=["Audit"]
)


@router.get("/")
def list_audit_logs(
    action: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(
        admin_only
    )
):
    query = db.query(
        models.AuditLog
    )

    if action:
        query = query.filter(
            models.AuditLog.action
            == action
        )

    if entity_type:
        query = query.filter(
            models.AuditLog.entity_type
            == entity_type
        )

    logs = (
        query
        .order_by(
            models.AuditLog.id.desc()
        )
        .all()
    )

    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "details": log.details,
            "created_at": log.created_at
        }
        for log in logs
    ]