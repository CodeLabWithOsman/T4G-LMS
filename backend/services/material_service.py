from sqlalchemy.orm import Session
from models.material_model import Material
from schemas.material_schema import MaterialCreate


def get_materials_by_course(db: Session, course_id: str):
    return db.query(Material).filter(Material.course_id == course_id).all()


def get_material_by_id(db: Session, material_id: str):
    return db.query(Material).filter(Material.id == material_id).first()


def create_material(db: Session, material: MaterialCreate):
    import base64
    file_size = len(base64.b64decode(material.file_data))
    db_material = Material(
        course_id=material.course_id,
        title=material.title,
        description=material.description,
        file_name=material.file_name,
        file_data=material.file_data,
        file_size=file_size
    )
    db.add(db_material)
    db.commit()
    db.refresh(db_material)
    return db_material


def delete_material(db: Session, material_id: str):
    material = db.query(Material).filter(Material.id == material_id).first()
    if material:
        db.delete(material)
        db.commit()
    return material
