"""Course model.

Fix applied: deleting a course previously left orphaned rows in `enrollments`
and `materials`. Both are now cascaded.
"""

import enum
import uuid

from sqlalchemy import Column, Enum, String, Text
from sqlalchemy.orm import relationship

from database import Base


class StatusEnum(str, enum.Enum):
    active = "Active"
    inactive = "Inactive"


class Course(Base):
    __tablename__ = "courses"

    id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    course_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    track = Column(String(50), nullable=False, index=True)
    status = Column(Enum(StatusEnum), default=StatusEnum.active, nullable=False)

    enrollments = relationship(
        "Enrollment",
        back_populates="course",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    materials = relationship(
        "Material",
        back_populates="course",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
