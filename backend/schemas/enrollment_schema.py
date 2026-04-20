from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class EnrollmentCreate(BaseModel):
    student_id: str
    course_id: str


class EnrollmentResponse(BaseModel):
    id: str
    student_id: str
    course_id: str
    enrolled_at: datetime
    is_completed: bool = False
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
