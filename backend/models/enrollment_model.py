from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean
from sqlalchemy import Text
from database import Base
import uuid
from datetime import datetime


class Enrollment(Base):
    __tablename__ = "enrollments"

    id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(Text, ForeignKey("students.id"), nullable=False)
    course_id = Column(Text, ForeignKey("courses.id"), nullable=False)
    enrolled_at = Column(DateTime, default=datetime.utcnow)
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
