from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class MaterialCreate(BaseModel):
    course_id: str
    title: str
    description: Optional[str] = None
    file_name: str
    file_data: str


class MaterialResponse(BaseModel):
    id: str
    course_id: str
    title: str
    description: Optional[str] = None
    file_name: str
    file_size: Optional[int] = None
    uploaded_at: datetime

    class Config:
        from_attributes = True
