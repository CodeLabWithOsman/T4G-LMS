from pydantic import BaseModel
from datetime import datetime


class NotificationResponse(BaseModel):
    id: str
    student_id: str
    message: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationCreate(BaseModel):
    student_id: str
    message: str
