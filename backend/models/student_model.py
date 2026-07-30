"""Student model.

Fix applied: deleting a student previously left orphaned rows in `enrollments`
and `notifications` (and broke the foreign key). Both are now cascaded.
"""

import enum
import uuid

from sqlalchemy import Boolean, Column, Enum, String, Text
from sqlalchemy.orm import relationship

from database import Base


class TrackEnum(str, enum.Enum):
    frontend = "Frontend"
    backend = "Backend"


class Student(Base):
    __tablename__ = "students"

    id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    student_id = Column(String(20), unique=True, nullable=False, index=True)
    track = Column(Enum(TrackEnum), nullable=False)
    password = Column(String(255), nullable=False)
    is_default_password = Column(Boolean, default=True, nullable=False)

    enrollments = relationship(
        "Enrollment",
        back_populates="student",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    notifications = relationship(
        "Notification",
        back_populates="student",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
