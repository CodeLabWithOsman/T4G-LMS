from sqlalchemy import Column, String, Text, DateTime
from database import Base
import uuid
from datetime import datetime


class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    posted_by = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
