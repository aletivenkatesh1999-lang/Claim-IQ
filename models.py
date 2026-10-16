from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text
)

from database import Base


def utc_now():
    return datetime.now(
        timezone.utc
    ).replace(tzinfo=None)


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
        index=True,
        nullable=False
    )

    password_hash = Column(
        String(255),
        nullable=False
    )

    role = Column(
        String(30),
        nullable=False
    )

    region = Column(
        String(50),
        default="ALL",
        nullable=False
    )

    active = Column(
        Boolean,
        default=True,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=utc_now,
        nullable=False
    )


class Policy(Base):
    __tablename__ = "policies"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    policy_number = Column(
        String(50),
        unique=True,
        index=True,
        nullable=False
    )

    policy_type = Column(
        String(50),
        nullable=False
    )

    coverage = Column(
        Text,
        nullable=False
    )

    region = Column(
        String(50),
        nullable=False
    )

    active = Column(
        Boolean,
        default=True,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=utc_now,
        nullable=False
    )


class Claim(Base):
    __tablename__ = "claims"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    policy_id = Column(
        Integer,
        ForeignKey("policies.id"),
        nullable=False
    )

    claimant = Column(
        String(120),
        nullable=False
    )

    claim_type = Column(
        String(50),
        nullable=False
    )

    region = Column(
        String(50),
        nullable=False
    )

    amount = Column(
        Float,
        nullable=False
    )

    status = Column(
        String(30),
        default="Submitted",
        nullable=False
    )

    assigned_to = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=utc_now,
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
        nullable=False
    )


class ClaimNote(Base):
    __tablename__ = "claim_notes"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    claim_id = Column(
        Integer,
        ForeignKey("claims.id"),
        nullable=False
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    note = Column(
        Text,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=utc_now,
        nullable=False
    )


class Document(Base):
    __tablename__ = "documents"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    filename = Column(
        String(255),
        nullable=False
    )

    path = Column(
        String(500),
        nullable=False
    )

    active = Column(
        Boolean,
        default=True,
        nullable=False
    )

    uploaded_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    uploaded_at = Column(
        DateTime,
        default=utc_now,
        nullable=False
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    document_id = Column(
        Integer,
        ForeignKey("documents.id"),
        nullable=False
    )

    chunk_number = Column(
        Integer,
        nullable=False
    )

    section = Column(
        String(100),
        nullable=False
    )

    content = Column(
        Text,
        nullable=False
    )


class ChatQueryLog(Base):
    __tablename__ = "chat_query_logs"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    question = Column(
        Text,
        nullable=False
    )

    source_reference = Column(
        Text,
        nullable=True
    )

    matched = Column(
        Boolean,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=utc_now,
        nullable=False
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    actor_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    action = Column(
        String(100),
        nullable=False
    )

    entity = Column(
        String(50),
        nullable=False
    )

    entity_id = Column(
        Integer,
        nullable=True
    )

    detail = Column(
        Text,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=utc_now,
        nullable=False
    )