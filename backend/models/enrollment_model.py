"""Enrollment model.

Fixes applied:
- ondelete="CASCADE" on both foreign keys so removing a student or course does
  not leave dangling enrollments.
- Unique constraint on (student_id, course_id) so the same student cannot be
  enrolled twice in one course via a race.
- Timezone-aware default (datetime.utcnow is deprecated).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("student_id", "course_id", name="uq_enrollment_student_course"),
    )

    id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(
        Text, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    course_id = Column(
        Text, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    enrolled_at = Column(DateTime, default=_utcnow)
    is_completed = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    student = relationship("Student", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")
