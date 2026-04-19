from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from services.material_service import (
    get_materials_by_course,
    get_material_by_id,
    create_material,
    delete_material
)
from schemas.material_schema import MaterialCreate, MaterialResponse
from fastapi.responses import Response
import base64

router = APIRouter(prefix="/materials", tags=["Materials"])


@router.get("/course/{course_id}", response_model=list[MaterialResponse])
def get_course_materials(course_id: str, db: Session = Depends(get_db)):
    return get_materials_by_course(db, course_id)


@router.post("/", response_model=MaterialResponse)
def upload_material(material: MaterialCreate, db: Session = Depends(get_db)):
    return create_material(db, material)


@router.get("/download/{material_id}")
def download_material(material_id: str, db: Session = Depends(get_db)):
    material = get_material_by_id(db, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    file_bytes = base64.b64decode(material.file_data)
    return Response(
        content=file_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={material.file_name}"}
    )
    
@router.get("/preview/{material_id}")
def preview_material(material_id: str, db: Session = Depends(get_db)):
    material = get_material_by_id(db, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    file_bytes = base64.b64decode(material.file_data)
    return Response(
        content=file_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={material.file_name}"}
    )


@router.delete("/{material_id}")
def remove_material(material_id: str, db: Session = Depends(get_db)):
    material = delete_material(db, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    return {"message": "Material deleted successfully"}
