"""Staff model."""

import enum
import uuid

from sqlalchemy import Boolean, Column, Enum, String, Text

from database import Base


class StaffTrackEnum(str, enum.Enum):
    frontend = "Frontend"
    backend = "Backend"


class Staff(Base):
    __tablename__ = "staff"

    id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    staff_id = Column(String(20), unique=True, nullable=False, index=True)
    track = Column(Enum(StaffTrackEnum), nullable=False)
    password = Column(String(255), nullable=False)
    is_default_password = Column(Boolean, default=True, nullable=False)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
