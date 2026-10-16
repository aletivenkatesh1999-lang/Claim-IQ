from pathlib import Path
from uuid import uuid4

from fastapi import (
    HTTPException,
    UploadFile,
    status,
)

from .config import settings


ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "text/plain",
}


MAX_FILE_SIZE = 10 * 1024 * 1024


def save_upload(
    upload: UploadFile,
    category: str
) -> tuple[str, int]:

    if upload.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF, JPG, PNG and TXT files are allowed"
        )

    original_name = upload.filename or "document"

    extension = Path(
        original_name
    ).suffix.lower()

    stored_filename = (
        f"{uuid4().hex}{extension}"
    )

    folder = (
        Path(settings.upload_dir)
        / category
    )

    folder.mkdir(
        parents=True,
        exist_ok=True
    )

    file_path = (
        folder
        / stored_filename
    )

    file_size = 0

    with file_path.open("wb") as target:

        while True:
            chunk = upload.file.read(
                1024 * 1024
            )

            if not chunk:
                break

            file_size += len(chunk)

            if file_size > MAX_FILE_SIZE:
                target.close()
                file_path.unlink(
                    missing_ok=True
                )

                raise HTTPException(
                    status_code=413,
                    detail="File exceeds the 10 MB limit"
                )

            target.write(chunk)

    return stored_filename, file_size


def delete_upload(
    category: str,
    stored_filename: str
) -> None:

    file_path = (
        Path(settings.upload_dir)
        / category
        / stored_filename
    )

    file_path.unlink(
        missing_ok=True
    )