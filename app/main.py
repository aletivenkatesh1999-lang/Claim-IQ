from pathlib import Path

from fastapi import FastAPI

from .config import settings
from .database import Base, engine

from .routers import (
    ai,
    analytics,
    audit,
    auth,
    chats,
    claims,
    documents,
    policies,
    rag,
    users,
)


# Create database tables
Base.metadata.create_all(bind=engine)


# Create required directories
Path(settings.upload_dir).mkdir(
    parents=True,
    exist_ok=True
)

Path(
    settings.upload_dir,
    "policies"
).mkdir(
    parents=True,
    exist_ok=True
)

Path(
    settings.upload_dir,
    "claims"
).mkdir(
    parents=True,
    exist_ok=True
)

Path(settings.vector_db_dir).mkdir(
    parents=True,
    exist_ok=True
)


# Create FastAPI application
app = FastAPI(
    title="ClaimIQ API",
    description=(
        "Insurance Policy, Claims, "
        "Documents and RAG Platform"
    ),
    version="3.0.0"
)


# Register routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(policies.router)
app.include_router(claims.router)
app.include_router(documents.router)
app.include_router(rag.router)
app.include_router(ai.router)
app.include_router(chats.router)
app.include_router(audit.router)
app.include_router(analytics.router)


@app.get(
    "/",
    tags=["Health"]
)
def root():
    return {
        "message": "ClaimIQ API is running",
        "swagger": "/docs"
    }


@app.get(
    "/health",
    tags=["Health"]
)
def health():
    return {
        "status": "healthy"
    }