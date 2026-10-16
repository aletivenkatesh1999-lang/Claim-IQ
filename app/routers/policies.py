from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db
from ..dependencies import officer_or_admin


router = APIRouter(
    prefix="/policies",
    tags=["Policies"]
)


def get_visible_policy(
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
            detail="You can access only your policies"
        )

    return policy


@router.post(
    "/",
    response_model=schemas.PolicyRead,
    status_code=status.HTTP_201_CREATED
)
def create_policy(
    payload: schemas.PolicyCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        get_current_user
    )
):
    existing_policy = (
        db.query(models.Policy)
        .filter(
            models.Policy.policy_number
            == payload.policy_number
        )
        .first()
    )

    if existing_policy:
        raise HTTPException(
            status_code=409,
            detail="Policy number already exists"
        )

    if current_user.role == models.UserRole.user:
        owner_id = current_user.id
    else:
        owner_id = payload.owner_id or current_user.id

    owner = db.get(
        models.User,
        owner_id
    )

    if not owner:
        raise HTTPException(
            status_code=404,
            detail="Policy owner not found"
        )

    policy_data = payload.model_dump(
        exclude={"owner_id"}
    )

    policy = models.Policy(
        **policy_data,
        owner_id=owner_id
    )

    db.add(policy)
    db.commit()
    db.refresh(policy)

    return policy


@router.get(
    "/",
    response_model=list[schemas.PolicyRead]
)
def list_policies(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        get_current_user
    )
):
    query = db.query(models.Policy)

    if current_user.role == models.UserRole.user:
        query = query.filter(
            models.Policy.owner_id
            == current_user.id
        )

    return (
        query
        .order_by(models.Policy.id.desc())
        .all()
    )


@router.get(
    "/{policy_id}",
    response_model=schemas.PolicyRead
)
def get_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        get_current_user
    )
):
    return get_visible_policy(
        db,
        policy_id,
        current_user
    )


@router.put(
    "/{policy_id}",
    response_model=schemas.PolicyRead
)
def update_policy(
    policy_id: int,
    payload: schemas.PolicyUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        officer_or_admin
    )
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

    update_data = payload.model_dump(
        exclude_unset=True
    )

    for field, value in update_data.items():
        setattr(
            policy,
            field,
            value
        )

    db.commit()
    db.refresh(policy)

    return policy


@router.delete(
    "/{policy_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        officer_or_admin
    )
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

    db.delete(policy)
    db.commit()

    return None