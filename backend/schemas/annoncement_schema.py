from pydantic import BaseModel
from datetime import datetime


class AnnouncementCreate(BaseModel):
    title: str
    message: str
    posted_by: str


class AnnouncementResponse(BaseModel):
    id: str
    title: str
    message: str
    posted_by: str
    created_at: datetime

    class Config:
        from_attributes = True
