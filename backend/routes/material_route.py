"""Material routes.

Fixes applied:
- Download and preview hardcoded media_type="application/pdf" for every file,
  so a DOCX/PPTX/image opened as a broken PDF. The content type is now derived
  from the stored filename.
- Filenames in Content-Disposition are now quoted and RFC 5987 encoded, so
  files with spaces or non-ASCII characters download with the correct name
  instead of being truncated.
- Corrupt base64 payloads return 422 instead of an unhandled 500.
- Preview is only served inline for types a browser can safely render; other
  types fall back to an attachment.
"""

import base64
import mimetypes
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from database import get_db
from schemas.material_schema import MaterialCreate, MaterialResponse
from services.material_service import (
    create_material,
    delete_material,
    get_material_by_id,
    get_materials_by_course,
)

router = APIRouter(prefix="/materials", tags=["Materials"])

# Types a browser can render inline safely.
INLINE_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    "image/svg+xml",
    "text/plain",
}


def _guess_media_type(file_name: str) -> str:
    guessed, _ = mimetypes.guess_type(file_name or "")
    return guessed or "application/octet-stream"


def _content_disposition(disposition: str, file_name: str) -> str:
    safe_name = (file_name or "download").replace('"', "")
    encoded = quote(safe_name)
    return f"{disposition}; filename=\"{safe_name}\"; filename*=UTF-8''{encoded}"


def _decode(material) -> bytes:
    try:
        return base64.b64decode(material.file_data)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This file is corrupted and cannot be opened.",
        )


@router.get("/course/{course_id}", response_model=list[MaterialResponse])
def get_course_materials(course_id: str, db: Session = Depends(get_db)):
    return get_materials_by_course(db, course_id)


@router.post("/", response_model=MaterialResponse, status_code=status.HTTP_201_CREATED)
def upload_material(material: MaterialCreate, db: Session = Depends(get_db)):
    return create_material(db, material)


@router.get("/download/{material_id}")
def download_material(material_id: str, db: Session = Depends(get_db)):
    material = get_material_by_id(db, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    return Response(
        content=_decode(material),
        media_type=_guess_media_type(material.file_name),
        headers={
            "Content-Disposition": _content_disposition("attachment", material.file_name)
        },
    )


@router.get("/preview/{material_id}")
def preview_material(material_id: str, db: Session = Depends(get_db)):
    material = get_material_by_id(db, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    media_type = _guess_media_type(material.file_name)
    disposition = "inline" if media_type in INLINE_TYPES else "attachment"

    return Response(
        content=_decode(material),
        media_type=media_type,
        headers={
            "Content-Disposition": _content_disposition(disposition, material.file_name)
        },
    )


@router.delete("/{material_id}")
def remove_material(material_id: str, db: Session = Depends(get_db)):
    material = delete_material(db, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    return {"message": "Material deleted successfully"}
