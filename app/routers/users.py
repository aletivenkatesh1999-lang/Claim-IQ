from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db
from ..dependencies import admin_only


router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


@router.get(
    "/me",
    response_model=schemas.UserRead
)
def get_my_profile(
    current_user: models.User = Depends(
        get_current_user
    )
):
    return current_user


@router.get(
    "/",
    response_model=list[schemas.UserRead]
)
def list_users(
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(
        admin_only
    )
):
    return (
        db.query(models.User)
        .order_by(models.User.id)
        .all()
    )


@router.patch(
    "/{user_id}/role",
    response_model=schemas.UserRead
)
def change_user_role(
    user_id: int,
    role: models.UserRole,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(
        admin_only
    )
):
    user = db.get(
        models.User,
        user_id
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    user.role = role

    db.commit()
    db.refresh(user)

    return user