"""Student service layer.

Fixes applied:
- Student.track is an Enum column. Calling .ilike() on it crashes on
  PostgreSQL ("operator does not exist: trackenum ~~* unknown"). It is now
  cast to text before the LIKE comparison.
- Type hints corrected: ids are UUID strings, not ints.
- create_student rolls back on failure instead of leaving the session dirty.
- Empty/whitespace search terms no longer return the entire table.
"""

import uuid
from typing import Optional

from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Session

from auth import hash_password
from models.student_model import Student
from schemas.student_schema import StudentCreate

DEFAULT_PASSWORD = "temp1234"


def generate_student_id() -> str:
    unique = uuid.uuid4().hex[:6].upper()
    return f"TG-2026-{unique}"


def create_student(db: Session, student: StudentCreate) -> Student:
    db_student = Student(
        first_name=student.first_name.strip(),
        last_name=student.last_name.strip(),
        email=student.email.strip().lower(),
        student_id=generate_student_id(),
        track=student.track,
        password=hash_password(DEFAULT_PASSWORD),
        is_default_password=True,
    )
    try:
        db.add(db_student)
        db.commit()
        db.refresh(db_student)
    except Exception:
        db.rollback()
        raise
    return db_student


def get_all_students(db: Session) -> list[Student]:
    return db.query(Student).order_by(Student.first_name, Student.last_name).all()


def get_student_by_id(db: Session, student_id: str) -> Optional[Student]:
    return db.query(Student).filter(Student.id == student_id).first()


def get_student_by_email(db: Session, email: str) -> Optional[Student]:
    if not email:
        return None
    return db.query(Student).filter(Student.email == email.strip().lower()).first()


def search_students(db: Session, q: str) -> list[Student]:
    term = (q or "").strip()
    if not term:
        return []
    keyword = f"%{term}%"
    return (
        db.query(Student)
        .filter(
            or_(
                Student.first_name.ilike(keyword),
                Student.last_name.ilike(keyword),
                Student.email.ilike(keyword),
                Student.student_id.ilike(keyword),
                cast(Student.track, String).ilike(keyword),
            )
        )
        .order_by(Student.first_name, Student.last_name)
        .all()
    )


def delete_student(db: Session, student_id: str) -> Optional[Student]:
    student = db.query(Student).filter(Student.id == student_id).first()
    if student:
        try:
            db.delete(student)
            db.commit()
        except Exception:
            db.rollback()
            raise
    return student
