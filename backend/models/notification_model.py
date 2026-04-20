from sqlalchemy import Column, String, Boolean, Text, DateTime, ForeignKey
from database import Base
import uuid
from datetime import datetime


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(Text, ForeignKey("students.id"), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
