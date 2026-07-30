"""Announcement model.

Fix applied: timezone-aware default (datetime.utcnow is deprecated).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String, Text

from database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    posted_by = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=_utcnow)
