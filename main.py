import os
from datetime import datetime, timezone
from typing import Optional

import pandas as pd

from fastapi import (
    Depends,
    FastAPI,
    File,
    HTTPException,
    Query,
    UploadFile,
    status
)

from fastapi.security import (
    OAuth2PasswordRequestForm
)

from pypdf import PdfReader
from sqlalchemy import or_
from sqlalchemy.orm import Session

from auth import (
    create_access_token,
    get_current_user,
    hash_password,
    require_roles,
    verify_password
)

from database import (
    Base,
    engine,
    get_db
)

from models import (
    AuditLog,
    ChatQueryLog,
    Claim,
    ClaimNote,
    Document,
    DocumentChunk,
    Policy,
    User
)

from schemas import (
    AdminBootstrapRequest,
    AIQueryRequest,
    ClaimCreate,
    ClaimResponse,
    ClaimStatusUpdate,
    DocumentStatusUpdate,
    PolicyCreate,
    PolicyResponse,
    TokenResponse,
    UserCreate,
    UserResponse,
    VALID_ROLES,
    VALID_STATUSES
)

from services.rag_service import (
    answer_question,
    create_chunks
)


app = FastAPI(
    title="ClaimIQ",
    description=(
        "Intelligent Insurance Claims "
        "and Policy Knowledge Platform"
    ),
    version="1.0.0"
)

Base.metadata.create_all(
    bind=engine
)

UPLOAD_DIRECTORY = os.getenv(
    "UPLOAD_DIRECTORY",
    "uploads"
)

os.makedirs(
    UPLOAD_DIRECTORY,
    exist_ok=True
)


STATUS_TRANSITIONS = {
    "Submitted": [
        "Under Review"
    ],
    "Under Review": [
        "Approved",
        "Rejected"
    ],
    "Approved": [
        "Closed"
    ],
    "Rejected": [
        "Closed"
    ],
    "Closed": []
}


def utc_now():
    return datetime.now(
        timezone.utc
    ).replace(tzinfo=None)


def add_audit_log(
    db: Session,
    user: User,
    action: str,
    entity: str,
    entity_id: Optional[int] = None,
    detail: Optional[str] = None
):
    db.add(
        AuditLog(
            actor_id=user.id,
            action=action,
            entity=entity,
            entity_id=entity_id,
            detail=detail
        )
    )


@app.get("/")
def home():
    return {
        "application": "ClaimIQ",
        "status": "running",
        "swagger": "/docs"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "application": "ClaimIQ"
    }


@app.post(
    "/api/v1/auth/bootstrap-admin",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
def bootstrap_admin(
    data: AdminBootstrapRequest,
    db: Session = Depends(get_db)
):
    user_count = (
        db.query(User)
        .count()
    )

    if user_count > 0:
        raise HTTPException(
            status_code=409,
            detail=(
                "Bootstrap is disabled because "
                "users already exist"
            )
        )

    admin = User(
        username=data.username,
        password_hash=hash_password(
            data.password
        ),
        role="admin",
        region=data.region,
        active=True
    )

    db.add(admin)
    db.commit()
    db.refresh(admin)

    return admin


@app.post(
    "/api/v1/auth/login",
    response_model=TokenResponse
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = (
        db.query(User)
        .filter(
            User.username
            == form_data.username
        )
        .first()
    )

    is_valid = (
        user is not None
        and verify_password(
            form_data.password,
            user.password_hash
        )
    )

    if not is_valid:
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "Invalid username or password"
            ),
            headers={
                "WWW-Authenticate": "Bearer"
            }
        )

    if not user.active:
        raise HTTPException(
            status_code=401,
            detail="User account is inactive"
        )

    access_token = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@app.get(
    "/api/v1/auth/me",
    response_model=UserResponse
)
def get_my_profile(
    user: User = Depends(
        get_current_user
    )
):
    return user


@app.post(
    "/api/v1/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("admin")
    )
):
    role = data.role.lower()

    if role not in VALID_ROLES:
        raise HTTPException(
            status_code=422,
            detail=(
                "Role must be admin, manager, "
                "adjuster, or support"
            )
        )

    existing = (
        db.query(User)
        .filter(
            User.username == data.username
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Username already exists"
        )

    user = User(
        username=data.username,
        password_hash=hash_password(
            data.password
        ),
        role=role,
        region=data.region,
        active=True
    )

    db.add(user)
    db.flush()

    add_audit_log(
        db,
        current_user,
        "create",
        "user",
        user.id
    )

    db.commit()
    db.refresh(user)

    return user


@app.get(
    "/api/v1/users",
    response_model=list[UserResponse]
)
def list_users(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles("admin")
    )
):
    return db.query(User).all()


@app.post(
    "/api/v1/policies",
    response_model=PolicyResponse,
    status_code=status.HTTP_201_CREATED
)
def create_policy(
    data: PolicyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles("admin")
    )
):
    existing = (
        db.query(Policy)
        .filter(
            Policy.policy_number
            == data.policy_number
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail=(
                "Policy number already exists"
            )
        )

    policy = Policy(
        **data.model_dump()
    )

    db.add(policy)
    db.flush()

    add_audit_log(
        db,
        user,
        "create",
        "policy",
        policy.id
    )

    db.commit()
    db.refresh(policy)

    return policy


@app.get(
    "/api/v1/policies",
    response_model=list[PolicyResponse]
)
def list_policies(
    active_only: bool = True,
    db: Session = Depends(get_db),
    user: User = Depends(
        get_current_user
    )
):
    query = db.query(Policy)

    if active_only:
        query = query.filter(
            Policy.active.is_(True)
        )

    return query.all()


@app.get(
    "/api/v1/policies/{policy_id}",
    response_model=PolicyResponse
)
def get_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(
        get_current_user
    )
):
    policy = db.get(
        Policy,
        policy_id
    )

    if not policy:
        raise HTTPException(
            status_code=404,
            detail="Policy not found"
        )

    return policy


@app.patch(
    "/api/v1/policies/{policy_id}/deactivate"
)
def deactivate_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles("admin")
    )
):
    policy = db.get(
        Policy,
        policy_id
    )

    if not policy:
        raise HTTPException(
            status_code=404,
            detail="Policy not found"
        )

    policy.active = False

    add_audit_log(
        db,
        user,
        "deactivate",
        "policy",
        policy.id
    )

    db.commit()

    return {
        "message": "Policy deactivated",
        "policy_id": policy.id
    }
@app.post(
    "/api/v1/claims",
    response_model=ClaimResponse,
    status_code=status.HTTP_201_CREATED
)
def create_claim(
    data: ClaimCreate,
    db: Session = Depends(get_db),
    user: User = Depends(
        get_current_user
    )
):
    policy = db.get(
        Policy,
        data.policy_id
    )

    if not policy or not policy.active:
        raise HTTPException(
            status_code=422,
            detail=(
                "A valid active policy is required"
            )
        )

    claim = Claim(
        **data.model_dump()
    )

    db.add(claim)
    db.flush()

    add_audit_log(
        db,
        user,
        "create",
        "claim",
        claim.id
    )

    db.commit()
    db.refresh(claim)

    return claim


@app.get("/api/v1/claims")
def list_claims(
    claim_status: Optional[str] = Query(
        default=None,
        alias="status"
    ),
    claimant: Optional[str] = None,
    policy_number: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(
        get_current_user
    )
):
    query = (
        db.query(Claim)
        .join(
            Policy,
            Policy.id == Claim.policy_id
        )
    )

    if user.role == "adjuster":
        query = query.filter(
            or_(
                Claim.assigned_to == user.id,
                Claim.region == user.region
            )
        )

    if claim_status:
        query = query.filter(
            Claim.status == claim_status
        )

    if claimant:
        query = query.filter(
            Claim.claimant.ilike(
                f"%{claimant}%"
            )
        )

    if policy_number:
        query = query.filter(
            Policy.policy_number
            == policy_number
        )

    claims = query.all()

    return [
        {
            "id": claim.id,
            "policy_id": claim.policy_id,
            "claimant": claim.claimant,
            "claim_type": claim.claim_type,
            "region": claim.region,
            "amount": claim.amount,
            "status": claim.status,
            "assigned_to": claim.assigned_to,
            "created_at": claim.created_at,
            "updated_at": claim.updated_at
        }
        for claim in claims
    ]


@app.get(
    "/api/v1/claims/{claim_id}",
    response_model=ClaimResponse
)
def get_claim(
    claim_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(
        get_current_user
    )
):
    claim = db.get(
        Claim,
        claim_id
    )

    if not claim:
        raise HTTPException(
            status_code=404,
            detail="Claim not found"
        )

    restricted = (
        user.role == "adjuster"
        and claim.assigned_to != user.id
        and claim.region != user.region
    )

    if restricted:
        raise HTTPException(
            status_code=403,
            detail=(
                "Claim is outside your assignment"
            )
        )

    return claim


@app.patch(
    "/api/v1/claims/{claim_id}/status"
)
def update_claim_status(
    claim_id: int,
    data: ClaimStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            "adjuster",
            "manager"
        )
    )
):
    if data.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail="Invalid claim status"
        )

    claim = db.get(
        Claim,
        claim_id
    )

    if not claim:
        raise HTTPException(
            status_code=404,
            detail="Claim not found"
        )

    restricted = (
        user.role == "adjuster"
        and claim.assigned_to != user.id
        and claim.region != user.region
    )

    if restricted:
        raise HTTPException(
            status_code=403,
            detail=(
                "Claim is outside your assignment"
            )
        )

    allowed = STATUS_TRANSITIONS.get(
        claim.status,
        []
    )

    manager_override = (
        user.role == "manager"
        and data.status not in allowed
        and bool(data.justification)
    )

    if (
        data.status not in allowed
        and not manager_override
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                f"Invalid transition from "
                f"{claim.status} to {data.status}"
            )
        )

    old_status = claim.status
    claim.status = data.status
    claim.updated_at = utc_now()

    if data.note:
        db.add(
            ClaimNote(
                claim_id=claim.id,
                user_id=user.id,
                note=data.note
            )
        )

    detail = (
        f"{old_status} -> "
        f"{claim.status}"
    )

    if data.justification:
        detail += (
            "; manager justification: "
            f"{data.justification}"
        )

    add_audit_log(
        db,
        user,
        "status_change",
        "claim",
        claim.id,
        detail
    )

    db.commit()
    db.refresh(claim)

    return {
        "message": "Claim status updated",
        "claim_id": claim.id,
        "old_status": old_status,
        "new_status": claim.status
    }


@app.post(
    "/api/v1/documents",
    status_code=status.HTTP_201_CREATED
)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles("admin")
    )
):
    filename = os.path.basename(
        file.filename or "document.txt"
    )

    extension = os.path.splitext(
        filename
    )[1].lower()

    if extension not in {
        ".txt",
        ".md",
        ".pdf"
    }:
        raise HTTPException(
            status_code=422,
            detail=(
                "Only TXT, MD, and PDF files "
                "are supported"
            )
        )

    file_path = os.path.join(
        UPLOAD_DIRECTORY,
        filename
    )

    file_bytes = await file.read()

    with open(
        file_path,
        "wb"
    ) as saved_file:
        saved_file.write(file_bytes)

    if extension == ".pdf":
        try:
            reader = PdfReader(file_path)

            text = "\n".join(
                page.extract_text() or ""
                for page in reader.pages
            )

        except Exception as error:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Unable to extract text "
                    "from PDF"
                )
            ) from error
    else:
        text = file_bytes.decode(
            "utf-8",
            errors="ignore"
        )

    if not text.strip():
        raise HTTPException(
            status_code=422,
            detail=(
                "Document does not contain "
                "readable text"
            )
        )

    document = Document(
        filename=filename,
        path=file_path,
        active=True,
        uploaded_by=user.id
    )

    db.add(document)
    db.flush()

    chunks = create_chunks(
        text,
        size=300,
        overlap=50
    )

    for index, chunk_text in enumerate(
        chunks,
        start=1
    ):
        db.add(
            DocumentChunk(
                document_id=document.id,
                chunk_number=index,
                section=f"chunk-{index}",
                content=chunk_text
            )
        )

    add_audit_log(
        db,
        user,
        "upload",
        "document",
        document.id,
        f"Created {len(chunks)} chunks"
    )

    db.commit()

    return {
        "message": (
            "Document uploaded and processed"
        ),
        "document_id": document.id,
        "filename": filename,
        "chunks_created": len(chunks)
    }


@app.get("/api/v1/documents")
def list_documents(
    db: Session = Depends(get_db),
    user: User = Depends(
        get_current_user
    )
):
    documents = (
        db.query(Document)
        .all()
    )

    return [
        {
            "id": item.id,
            "filename": item.filename,
            "active": item.active,
            "uploaded_at": item.uploaded_at
        }
        for item in documents
    ]


@app.patch(
    "/api/v1/documents/{document_id}/status"
)
def update_document_status(
    document_id: int,
    data: DocumentStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles("admin")
    )
):
    document = db.get(
        Document,
        document_id
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    document.active = data.active

    add_audit_log(
        db,
        user,
        "document_status_change",
        "document",
        document.id,
        f"active={data.active}"
    )

    db.commit()

    return {
        "message": (
            "Document status updated"
        ),
        "document_id": document.id,
        "active": document.active
    }


@app.post("/api/v1/ai/query")
def query_policy_documents(
    data: AIQueryRequest,
    db: Session = Depends(get_db),
    user: User = Depends(
        get_current_user
    )
):
    result = answer_question(
        db,
        data.question
    )

    references = ", ".join(
        (
            f"{source['document']}:"
            f"{source['section']}"
        )
        for source in result["sources"]
    )

    db.add(
        ChatQueryLog(
            user_id=user.id,
            question=data.question,
            source_reference=(
                references or None
            ),
            matched=result["matched"]
        )
    )

    db.commit()

    return result


@app.get("/api/v1/analytics/claims")
def claim_analytics(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            "admin",
            "manager"
        )
    )
):
    claims = db.query(Claim).all()

    if not claims:
        return {
            "volume": 0,
            "approval_rate": 0,
            "rejection_rate": 0,
            "average_turnaround_hours": 0,
            "by_status": {},
            "by_region": {},
            "by_claim_type": {}
        }

    rows = [
        {
            "status": claim.status,
            "amount": claim.amount,
            "region": claim.region,
            "claim_type": claim.claim_type,
            "created_at": claim.created_at,
            "updated_at": claim.updated_at
        }
        for claim in claims
    ]

    dataframe = pd.DataFrame(rows)

    completed = dataframe[
        dataframe["status"].isin(
            [
                "Approved",
                "Rejected"
            ]
        )
    ]

    approved_count = int(
        (
            dataframe["status"]
            == "Approved"
        ).sum()
    )

    rejected_count = int(
        (
            dataframe["status"]
            == "Rejected"
        ).sum()
    )

    completed_count = len(completed)

    turnaround = (
        pd.to_datetime(
            dataframe["updated_at"]
        )
        - pd.to_datetime(
            dataframe["created_at"]
        )
    ).dt.total_seconds() / 3600

    return {
        "volume": int(
            len(dataframe)
        ),
        "approval_rate": (
            approved_count / completed_count
            if completed_count
            else 0
        ),
        "rejection_rate": (
            rejected_count / completed_count
            if completed_count
            else 0
        ),
        "average_turnaround_hours": float(
            turnaround.mean()
        ),
        "by_status": (
            dataframe
            .groupby("status")
            .size()
            .astype(int)
            .to_dict()
        ),
        "by_region": (
            dataframe
            .groupby("region")
            .size()
            .astype(int)
            .to_dict()
        ),
        "by_claim_type": (
            dataframe
            .groupby("claim_type")
            .size()
            .astype(int)
            .to_dict()
        )
    }


@app.get("/api/v1/audit-logs")
def get_audit_logs(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles("admin")
    )
):
    logs = (
        db.query(AuditLog)
        .order_by(
            AuditLog.id.desc()
        )
        .limit(100)
        .all()
    )

    return [
        {
            "id": item.id,
            "actor_id": item.actor_id,
            "action": item.action,
            "entity": item.entity,
            "entity_id": item.entity_id,
            "detail": item.detail,
            "created_at": item.created_at
        }
        for item in logs
    ]