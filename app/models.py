import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)

from sqlalchemy.orm import relationship

from .database import Base


def utcnow():
    return datetime.now(timezone.utc)


class UserRole(str, enum.Enum):
    admin = "admin"
    claim_officer = "claim_officer"
    user = "user"


class ClaimStatus(str, enum.Enum):
    submitted = "submitted"
    under_review = "under_review"
    approved = "approved"
    rejected = "rejected"
    closed = "closed"


class User(Base):
    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    username = Column(
        String(80),
        unique=True,
        nullable=False,
        index=True
    )

    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )

    hashed_password = Column(
        String(255),
        nullable=False
    )

    role = Column(
        Enum(UserRole),
        default=UserRole.user,
        nullable=False
    )

    is_active = Column(
        Boolean,
        default=True,
        nullable=False
    )

    created_at = Column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False
    )

    policies = relationship(
        "Policy",
        back_populates="owner"
    )

    claims = relationship(
        "Claim",
        back_populates="created_by"
    )


class Policy(Base):
    __tablename__ = "policies"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    policy_number = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )

    policy_type = Column(
        String(100),
        nullable=False
    )

    holder_name = Column(
        String(200),
        nullable=False
    )

    description = Column(
        Text,
        nullable=True
    )

    status = Column(
        String(50),
        default="active",
        nullable=False
    )

    owner_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    created_at = Column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False
    )

    owner = relationship(
        "User",
        back_populates="policies"
    )

    claims = relationship(
        "Claim",
        back_populates="policy",
        cascade="all, delete-orphan"
    )

    documents = relationship(
        "PolicyDocument",
        back_populates="policy",
        cascade="all, delete-orphan"
    )


class Claim(Base):
    __tablename__ = "claims"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    claim_number = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )

    policy_id = Column(
        Integer,
        ForeignKey("policies.id"),
        nullable=False,
        index=True
    )

    title = Column(
        String(200),
        nullable=False
    )

    description = Column(
        Text,
        nullable=False
    )

    status = Column(
        Enum(ClaimStatus),
        default=ClaimStatus.submitted,
        nullable=False
    )

    decision_notes = Column(
        Text,
        nullable=True
    )

    created_by_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    created_at = Column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False
    )

    policy = relationship(
        "Policy",
        back_populates="claims"
    )

    created_by = relationship(
        "User",
        back_populates="claims"
    )

    documents = relationship(
        "ClaimDocument",
        back_populates="claim",
        cascade="all, delete-orphan"
    )


class PolicyDocument(Base):

    __tablename__ = "policy_documents"
    is_active = Column(
        Boolean,
        default=True,
        nullable=False
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    policy_id = Column(
        Integer,
        ForeignKey("policies.id"),
        nullable=False,
        index=True
    )

    original_filename = Column(
        String(255),
        nullable=False
    )

    stored_filename = Column(
        String(255),
        unique=True,
        nullable=False
    )

    content_type = Column(
        String(100),
        nullable=False
    )

    file_size = Column(
        Integer,
        nullable=False
    )

    uploaded_by_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    uploaded_at = Column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False
    )

    policy = relationship(
        "Policy",
        back_populates="documents"
    )


class ClaimDocument(Base):
    __tablename__ = "claim_documents"
    is_active = Column(
        Boolean,
        default=True,
        nullable=False
    )
    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    claim_id = Column(
        Integer,
        ForeignKey("claims.id"),
        nullable=False,
        index=True
    )

    original_filename = Column(
        String(255),
        nullable=False
    )

    stored_filename = Column(
        String(255),
        unique=True,
        nullable=False
    )

    content_type = Column(
        String(100),
        nullable=False
    )

    file_size = Column(
        Integer,
        nullable=False
    )

    uploaded_by_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    uploaded_at = Column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False
    )

    claim = relationship(
        "Claim",
        back_populates="documents"
    )

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    title = Column(
        String(255),
        nullable=False,
        default="ClaimIQ Conversation"
    )

    policy_id = Column(
        Integer,
        ForeignKey("policies.id"),
        nullable=True,
        index=True
    )

    claim_id = Column(
        Integer,
        ForeignKey("claims.id"),
        nullable=True,
        index=True
    )

    created_at = Column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    session_id = Column(
        Integer,
        ForeignKey("chat_sessions.id"),
        nullable=False,
        index=True
    )

    role = Column(
        String(30),
        nullable=False
    )

    content = Column(
        Text,
        nullable=False
    )

    sources = Column(
        Text,
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False
    )


class AIQueryLog(Base):
    __tablename__ = "ai_query_logs"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    session_id = Column(
        Integer,
        ForeignKey("chat_sessions.id"),
        nullable=True,
        index=True
    )

    policy_id = Column(
        Integer,
        ForeignKey("policies.id"),
        nullable=True,
        index=True
    )

    question = Column(
        Text,
        nullable=False
    )

    source_references = Column(
        Text,
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False
    )

class ClaimStatusHistory(Base):
    __tablename__ = "claim_status_history"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    claim_id = Column(
        Integer,
        ForeignKey("claims.id"),
        nullable=False,
        index=True
    )

    old_status = Column(
        String(50),
        nullable=True
    )

    new_status = Column(
        String(50),
        nullable=False
    )

    changed_by_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    justification = Column(
        Text,
        nullable=True
    )

    changed_at = Column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True
    )

    action = Column(
        String(100),
        nullable=False,
        index=True
    )

    entity_type = Column(
        String(100),
        nullable=False,
        index=True
    )

    entity_id = Column(
        Integer,
        nullable=True,
        index=True
    )

    details = Column(
        Text,
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False
    )