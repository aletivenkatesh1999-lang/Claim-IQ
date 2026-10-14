from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field
)


VALID_ROLES = {
    "admin",
    "manager",
    "adjuster",
    "support"
}

VALID_STATUSES = {
    "Submitted",
    "Under Review",
    "Approved",
    "Rejected",
    "Closed"
}


class AdminBootstrapRequest(BaseModel):
    username: str = Field(
        min_length=3,
        max_length=80
    )

    password: str = Field(
        min_length=8,
        max_length=72
    )

    region: str = "ALL"


class UserCreate(BaseModel):
    username: str = Field(
        min_length=3,
        max_length=80
    )

    password: str = Field(
        min_length=8,
        max_length=72
    )

    role: str
    region: str = "ALL"


class UserResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    username: str
    role: str
    region: str
    active: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PolicyCreate(BaseModel):
    policy_number: str = Field(
        min_length=3,
        max_length=50
    )

    policy_type: str = Field(
        min_length=2,
        max_length=50
    )

    coverage: str = Field(
        min_length=3
    )

    region: str = Field(
        min_length=2,
        max_length=50
    )


class PolicyResponse(PolicyCreate):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    active: bool


class ClaimCreate(BaseModel):
    policy_id: int

    claimant: str = Field(
        min_length=2,
        max_length=120
    )

    claim_type: str = Field(
        min_length=2,
        max_length=50
    )

    region: str = Field(
        min_length=2,
        max_length=50
    )

    amount: float = Field(gt=0)

    assigned_to: Optional[int] = None


class ClaimResponse(ClaimCreate):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    status: str


class ClaimStatusUpdate(BaseModel):
    status: str
    note: Optional[str] = None
    justification: Optional[str] = None


class AIQueryRequest(BaseModel):
    question: str = Field(
        min_length=3,
        max_length=1000
    )


class DocumentStatusUpdate(BaseModel):
    active: bool