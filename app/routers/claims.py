from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)

from sqlalchemy.orm import Session

from .. import models, schemas
from ..audit_service import write_audit_log
from ..auth import get_current_user
from ..database import get_db
from ..dependencies import officer_or_admin


router = APIRouter(
    prefix="/claims",
    tags=["Claims"]
)


ALLOWED_TRANSITIONS = {
    models.ClaimStatus.submitted: {
        models.ClaimStatus.under_review
    },
    models.ClaimStatus.under_review: {
        models.ClaimStatus.approved,
        models.ClaimStatus.rejected
    },
    models.ClaimStatus.approved: {
        models.ClaimStatus.closed
    },
    models.ClaimStatus.rejected: {
        models.ClaimStatus.closed
    },
    models.ClaimStatus.closed: set()
}


def get_visible_claim(
    db: Session,
    claim_id: int,
    current_user: models.User
):
    claim = db.get(
        models.Claim,
        claim_id
    )

    if not claim:
        raise HTTPException(
            status_code=404,
            detail="Claim not found"
        )

    if (
        current_user.role == models.UserRole.user
        and claim.created_by_id != current_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="Claim access denied"
        )

    return claim


@router.post(
    "/",
    response_model=schemas.ClaimRead,
    status_code=status.HTTP_201_CREATED
)
def create_claim(
    payload: schemas.ClaimCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        get_current_user
    )
):
    existing_claim = (
        db.query(models.Claim)
        .filter(
            models.Claim.claim_number
            == payload.claim_number
        )
        .first()
    )

    if existing_claim:
        raise HTTPException(
            status_code=409,
            detail="Claim number already exists"
        )

    policy = db.get(
        models.Policy,
        payload.policy_id
    )

    if not policy:
        raise HTTPException(
            status_code=404,
            detail="Policy not found"
        )

    if policy.status.lower() != "active":
        raise HTTPException(
            status_code=409,
            detail="Claims require an active policy"
        )

    if (
        current_user.role == models.UserRole.user
        and policy.owner_id != current_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="Policy access denied"
        )

    claim = models.Claim(
        **payload.model_dump(),
        created_by_id=current_user.id
    )

    db.add(claim)
    db.flush()

    history = models.ClaimStatusHistory(
        claim_id=claim.id,
        old_status=None,
        new_status=models.ClaimStatus.submitted.value,
        changed_by_id=current_user.id,
        justification="Initial claim submission"
    )

    db.add(history)

    write_audit_log(
        db=db,
        user_id=current_user.id,
        action="claim_created",
        entity_type="claim",
        entity_id=claim.id,
        details={
            "claim_number": claim.claim_number,
            "policy_id": claim.policy_id
        }
    )

    db.commit()
    db.refresh(claim)

    return claim


@router.get(
    "/",
    response_model=list[schemas.ClaimRead]
)
def list_claims(
    claim_number: str | None = Query(
        default=None
    ),
    status_filter: models.ClaimStatus | None = Query(
        default=None,
        alias="status"
    ),
    policy_id: int | None = Query(
        default=None
    ),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        get_current_user
    )
):
    query = db.query(
        models.Claim
    )

    if (
        current_user.role
        == models.UserRole.user
    ):
        query = query.filter(
            models.Claim.created_by_id
            == current_user.id
        )

    if claim_number:
        query = query.filter(
            models.Claim.claim_number.contains(
                claim_number
            )
        )

    if status_filter:
        query = query.filter(
            models.Claim.status
            == status_filter
        )

    if policy_id is not None:
        query = query.filter(
            models.Claim.policy_id
            == policy_id
        )

    return (
        query
        .order_by(
            models.Claim.id.desc()
        )
        .all()
    )


@router.get(
    "/{claim_id}",
    response_model=schemas.ClaimRead
)
def get_claim(
    claim_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        get_current_user
    )
):
    return get_visible_claim(
        db,
        claim_id,
        current_user
    )


@router.put(
    "/{claim_id}",
    response_model=schemas.ClaimRead
)
def update_claim(
    claim_id: int,
    payload: schemas.ClaimUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        get_current_user
    )
):
    claim = get_visible_claim(
        db,
        claim_id,
        current_user
    )

    if (
        current_user.role == models.UserRole.user
        and claim.status
        != models.ClaimStatus.submitted
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "User can edit a claim only "
                "while it is submitted"
            )
        )

    update_data = payload.model_dump(
        exclude_unset=True
    )

    for field, value in update_data.items():
        setattr(
            claim,
            field,
            value
        )

    write_audit_log(
        db=db,
        user_id=current_user.id,
        action="claim_updated",
        entity_type="claim",
        entity_id=claim.id
    )

    db.commit()
    db.refresh(claim)

    return claim


@router.patch(
    "/{claim_id}/decision",
    response_model=schemas.ClaimRead
)
def decide_claim(
    claim_id: int,
    payload: schemas.ClaimDecision,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        officer_or_admin
    )
):
    claim = db.get(
        models.Claim,
        claim_id
    )

    if not claim:
        raise HTTPException(
            status_code=404,
            detail="Claim not found"
        )

    old_status = claim.status
    new_status = payload.status

    allowed = ALLOWED_TRANSITIONS.get(
        old_status,
        set()
    )

    if new_status not in allowed:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Invalid status transition: "
                f"{old_status.value} -> "
                f"{new_status.value}"
            )
        )

    claim.status = new_status
    claim.decision_notes = (
        payload.decision_notes
    )

    history = models.ClaimStatusHistory(
        claim_id=claim.id,
        old_status=old_status.value,
        new_status=new_status.value,
        changed_by_id=current_user.id,
        justification=payload.decision_notes
    )

    db.add(history)

    write_audit_log(
        db=db,
        user_id=current_user.id,
        action="claim_status_changed",
        entity_type="claim",
        entity_id=claim.id,
        details={
            "old_status": old_status.value,
            "new_status": new_status.value
        }
    )

    db.commit()
    db.refresh(claim)

    return claim


@router.get(
    "/{claim_id}/history"
)
def claim_history(
    claim_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        get_current_user
    )
):
    get_visible_claim(
        db,
        claim_id,
        current_user
    )

    history = (
        db.query(
            models.ClaimStatusHistory
        )
        .filter(
            models.ClaimStatusHistory.claim_id
            == claim_id
        )
        .order_by(
            models.ClaimStatusHistory.changed_at
        )
        .all()
    )

    return [
        {
            "id": item.id,
            "claim_id": item.claim_id,
            "old_status": item.old_status,
            "new_status": item.new_status,
            "changed_by_id": item.changed_by_id,
            "justification": item.justification,
            "changed_at": item.changed_at
        }
        for item in history
    ]