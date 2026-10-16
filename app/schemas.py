from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
)

from .models import ClaimStatus, UserRole


class UserCreate(BaseModel):
    username: str = Field(
        min_length=3,
        max_length=80
    )

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128
    )


class UserRead(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PolicyCreate(BaseModel):
    policy_number: str = Field(
        min_length=3,
        max_length=100
    )

    policy_type: str = Field(
        min_length=2,
        max_length=100
    )

    holder_name: str = Field(
        min_length=2,
        max_length=200
    )

    description: str | None = None
    status: str = "active"
    owner_id: int | None = None


class PolicyUpdate(BaseModel):
    policy_type: str | None = None
    holder_name: str | None = None
    description: str | None = None
    status: str | None = None


class PolicyRead(BaseModel):
    id: int
    policy_number: str
    policy_type: str
    holder_name: str
    description: str | None
    status: str
    owner_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


class ClaimCreate(BaseModel):
    claim_number: str = Field(
        min_length=3,
        max_length=100
    )

    policy_id: int

    title: str = Field(
        min_length=3,
        max_length=200
    )

    description: str = Field(
        min_length=3
    )


class ClaimUpdate(BaseModel):
    title: str | None = None
    description: str | None = None


class ClaimDecision(BaseModel):
    status: ClaimStatus
    decision_notes: str | None = None


class ClaimRead(BaseModel):
    id: int
    claim_number: str
    policy_id: int
    title: str
    description: str
    status: ClaimStatus
    decision_notes: str | None
    created_by_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


class DocumentRead(BaseModel):
    id: int
    original_filename: str
    content_type: str
    file_size: int
    uploaded_by_id: int
    uploaded_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )