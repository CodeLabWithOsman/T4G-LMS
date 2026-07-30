"""Course service layer.

Fixes applied:
- Type hints corrected: course ids are UUID strings, not ints.
- update_course now supports partial updates instead of overwriting fields
  with None when the client omits them.
- Rollback on write failure.
"""

from typing import Optional

from sqlalchemy.orm import Session

from models.course_model import Course
from schemas.course_schema import CourseCreate


def get_all_courses(db: Session) -> list[Course]:
    return db.query(Course).order_by(Course.course_name).all()


def get_course_by_id(db: Session, course_id: str) -> Optional[Course]:
    return db.query(Course).filter(Course.id == course_id).first()


def create_course(db: Session, course: CourseCreate) -> Course:
    db_course = Course(
        course_name=course.course_name.strip(),
        description=course.description,
        track=course.track,
        status=course.status,
    )
    try:
        db.add(db_course)
        db.commit()
        db.refresh(db_course)
    except Exception:
        db.rollback()
        raise
    return db_course


def update_course(db: Session, course_id: str, course: CourseCreate) -> Optional[Course]:
    db_course = db.query(Course).filter(Course.id == course_id).first()
    if not db_course:
        return None

    if course.course_name is not None:
        db_course.course_name = course.course_name.strip()
    if course.description is not None:
        db_course.description = course.description
    if course.track is not None:
        db_course.track = course.track
    if course.status is not None:
        db_course.status = course.status

    try:
        db.commit()
        db.refresh(db_course)
    except Exception:
        db.rollback()
        raise
    return db_course


def delete_course(db: Session, course_id: str) -> Optional[Course]:
    db_course = db.query(Course).filter(Course.id == course_id).first()
    if db_course:
        try:
            db.delete(db_course)
            db.commit()
        except Exception:
            db.rollback()
            raise
    return db_course
