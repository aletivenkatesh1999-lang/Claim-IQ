import json

from sqlalchemy.orm import Session

from . import models


def write_audit_log(
    db: Session,
    user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    details: dict | None = None
) -> models.AuditLog:
    serialized_details = None

    if details is not None:
        serialized_details = json.dumps(
            details,
            default=str
        )

    log = models.AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=serialized_details
    )

    db.add(log)

    return log