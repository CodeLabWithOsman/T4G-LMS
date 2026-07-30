"""Authentication helpers.

Fixes applied:
- Safe defaults for every environment variable. Previously a missing
  ACCESS_TOKEN_EXPIRE_MINUTES raised TypeError at import time and a missing
  SECRET_KEY/ALGORITHM made every JWT operation fail.
- Long-lived tokens (30 days by default) so a signed-in user is not silently
  logged out while they are still using the app.
- Timezone-aware datetimes (datetime.utcnow() is deprecated).
- Tokens now carry the subject's role and id, so /me endpoints can resolve the
  caller without a second lookup by email.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

load_dotenv()


def _get_int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or str(raw).strip() == "":
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


SECRET_KEY = os.getenv("SECRET_KEY") or "t4g-lms-dev-secret-change-me"
ALGORITHM = os.getenv("ALGORITHM") or "HS256"

# 30 days. The frontend keeps the user signed in until they explicitly log out,
# so the token must outlive a normal usage session by a wide margin.
ACCESS_TOKEN_EXPIRE_MINUTES = _get_int_env("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24 * 30)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not plain_password or not hashed_password:
        return False
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        # Malformed/legacy hash in the database must not raise a 500.
        return False


def create_access_token(data: dict, expires_minutes: Optional[int] = None) -> str:
    to_encode = data.copy()
    minutes = expires_minutes or ACCESS_TOKEN_EXPIRE_MINUTES
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_token_expiry_seconds() -> int:
    """Value returned to the frontend as `expires_in`."""
    return ACCESS_TOKEN_EXPIRE_MINUTES * 60


def decode_token(token: str) -> Optional[dict]:
    """Return the full JWT payload, or None when the token is unusable."""
    if not token:
        return None
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def verify_token(token: str) -> Optional[str]:
    """Backwards-compatible helper: returns the token subject."""
    payload = decode_token(token)
    if not payload:
        return None
    return payload.get("sub")


def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """Returns the subject (email) of the caller."""
    if not token:
        raise CREDENTIALS_EXCEPTION
    subject = verify_token(token)
    if not subject:
        raise CREDENTIALS_EXCEPTION
    return subject


def get_current_payload(token: str = Depends(oauth2_scheme)) -> dict:
    """Returns the full token payload (sub, role, id)."""
    if not token:
        raise CREDENTIALS_EXCEPTION
    payload = decode_token(token)
    if not payload or not payload.get("sub"):
        raise CREDENTIALS_EXCEPTION
    return payload


def require_role(*allowed_roles: str):
    """Dependency factory that enforces the role claim on a token."""

    def _dependency(payload: dict = Depends(get_current_payload)) -> dict:
        role = payload.get("role")
        if allowed_roles and role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this resource",
            )
        return payload

    return _dependency
