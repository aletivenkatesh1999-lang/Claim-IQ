from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import (
    authenticate_user,
    create_access_token,
    get_password_hash,
)
from ..database import get_db


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post(
    "/register",
    response_model=schemas.UserRead,
    status_code=status.HTTP_201_CREATED
)
def register(
    payload: schemas.UserCreate,
    db: Session = Depends(get_db)
):
    existing_user = (
        db.query(models.User)
        .filter(
            (models.User.username == payload.username)
            | (models.User.email == payload.email)
        )
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="Username or email already exists"
        )

    first_user = db.query(models.User).count() == 0

    assigned_role = (
        models.UserRole.admin
        if first_user
        else models.UserRole.user
    )

    user = models.User(
        username=payload.username,
        email=payload.email,
        hashed_password=get_password_hash(
            payload.password
        ),
        role=assigned_role
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.post(
    "/login",
    response_model=schemas.Token
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = authenticate_user(
        db,
        form_data.username,
        form_data.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={
                "WWW-Authenticate": "Bearer"
            }
        )

    access_token = create_access_token(
        subject=user.username
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }