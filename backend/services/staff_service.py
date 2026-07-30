"""Staff service layer.

Fixes applied:
- Staff.track is an Enum column; .ilike() on it crashes on PostgreSQL. It is
  now cast to text before the LIKE comparison.
- Rollback on write failure.
- Empty search terms no longer return the entire table.
"""

import uuid
from typing import Optional

from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Session

from auth import hash_password
from models.staff_model import Staff
from schemas.staff_schema import StaffCreate

DEFAULT_PASSWORD = "temp1234"


def generate_staff_id() -> str:
    unique = uuid.uuid4().hex[:6].upper()
    return f"STF-2026-{unique}"


def get_all_staff(db: Session) -> list[Staff]:
    return db.query(Staff).order_by(Staff.first_name, Staff.last_name).all()


def get_staff_by_id(db: Session, staff_id: str) -> Optional[Staff]:
    return db.query(Staff).filter(Staff.id == staff_id).first()


def get_staff_by_email(db: Session, email: str) -> Optional[Staff]:
    if not email:
        return None
    return db.query(Staff).filter(Staff.email == email.strip().lower()).first()


def create_staff(db: Session, staff: StaffCreate) -> Staff:
    db_staff = Staff(
        first_name=staff.first_name.strip(),
        last_name=staff.last_name.strip(),
        email=staff.email.strip().lower(),
        staff_id=generate_staff_id(),
        track=staff.track,
        password=hash_password(DEFAULT_PASSWORD),
        is_default_password=True,
    )
    try:
        db.add(db_staff)
        db.commit()
        db.refresh(db_staff)
    except Exception:
        db.rollback()
        raise
    return db_staff


def search_staff(db: Session, q: str) -> list[Staff]:
    """Search staff by name, email, staff ID or track. Case-insensitive."""
    term = (q or "").strip()
    if not term:
        return []
    keyword = f"%{term}%"
    return (
        db.query(Staff)
        .filter(
            or_(
                Staff.first_name.ilike(keyword),
                Staff.last_name.ilike(keyword),
                Staff.email.ilike(keyword),
                Staff.staff_id.ilike(keyword),
                cast(Staff.track, String).ilike(keyword),
            )
        )
        .order_by(Staff.first_name, Staff.last_name)
        .all()
    )


def delete_staff(db: Session, staff_id: str) -> Optional[Staff]:
    staff = db.query(Staff).filter(Staff.id == staff_id).first()
    if staff:
        try:
            db.delete(staff)
            db.commit()
        except Exception:
            db.rollback()
            raise
    return staff
