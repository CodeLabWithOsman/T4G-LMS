"""Notification model.

Fixes applied:
- ondelete="CASCADE" so deleting a student removes their notifications.
- Timezone-aware default.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(
        Text, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=_utcnow)

    student = relationship("Student", back_populates="notifications")
