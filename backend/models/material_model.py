"""Material model.

Fixes applied:
- ondelete="CASCADE" so deleting a course removes its materials.
- Timezone-aware default.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class Material(Base):
    __tablename__ = "materials"

    id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    course_id = Column(
        Text, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title = Column(String(200), nullable=False)
    description = Column(String(500), nullable=True)
    file_name = Column(String(200), nullable=False)
    file_data = Column(Text, nullable=False)
    file_size = Column(Integer, nullable=True)
    uploaded_at = Column(DateTime, default=_utcnow)

    course = relationship("Course", back_populates="materials")
