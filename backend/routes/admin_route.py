"""Admin routes.

Fixes applied:
- Login previously returned only a token with no role claim and no admin
  object, so the admin dashboard had nothing to persist and no way to show who
  was signed in. It now returns expires_in and an admin payload, and the token
  carries role="admin".
- Added GET /admin/me for session revalidation.
- Login no longer reveals whether an email is registered.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from auth import (
    create_access_token,
    get_current_payload,
    get_token_expiry_seconds,
    hash_password,
    verify_password,
)
from database import get_db
from models.admin_model import Admin

router = APIRouter(prefix="/admin", tags=["Admin"])


class AdminCreate(BaseModel):
    email: EmailStr
    password: str


class AdminLogin(BaseModel):
    email: EmailStr
    password: str


def _admin_payload(admin: Admin) -> dict:
    email = admin.email or ""
    return {
        "id": admin.id,
        "email": email,
        "first_name": getattr(admin, "first_name", None) or email.split("@")[0],
        "last_name": getattr(admin, "last_name", None) or "",
        "role": "admin",
    }


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_admin(admin: AdminCreate, db: Session = Depends(get_db)):
    existing = db.query(Admin).filter(Admin.email == admin.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An admin with this email already exists",
        )
    new_admin = Admin(email=admin.email, password=hash_password(admin.password))
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    return {"message": "Admin registered successfully", "admin": _admin_payload(new_admin)}


@router.post("/login")
def login_admin(admin: AdminLogin, db: Session = Depends(get_db)):
    db_admin = db.query(Admin).filter(Admin.email == admin.email).first()
    if not db_admin or not verify_password(admin.password, db_admin.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    token = create_access_token(
        data={"sub": db_admin.email, "role": "admin", "id": db_admin.id}
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": get_token_expiry_seconds(),
        "admin": _admin_payload(db_admin),
    }


@router.get("/me")
def read_current_admin(
    payload: dict = Depends(get_current_payload),
    db: Session = Depends(get_db),
):
    if payload.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is for admin accounts",
        )
    admin = db.query(Admin).filter(Admin.email == payload.get("sub")).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account no longer exists",
        )
    return _admin_payload(admin)
