"""Password hashing (Argon2) and login tokens (JWT)."""
import datetime as dt

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import Argon2Error
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import ACCESS_TOKEN_MINUTES, JWT_ALGORITHM, SECRET_KEY
from app.database.database import get_db
from app.database.models import User

_hasher = PasswordHasher()
_bearer = HTTPBearer(auto_error=False, description="Paste the access_token you got from /auth/login")


def hash_password(password: str) -> str:
    """One-way: the hash can be checked, but the password cannot be recovered from it."""
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (Argon2Error, ValueError):
        return False


# checked when the email does not exist, so both cases take the same time (no hint for attackers)
DUMMY_HASH = hash_password("not-a-real-password")


def create_access_token(user_id: int) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    payload = {"sub": str(user_id), "iat": now, "exp": now + dt.timedelta(minutes=ACCESS_TOKEN_MINUTES)}
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
                     db: Session = Depends(get_db)) -> User:
    """Put `user: User = Depends(get_current_user)` on a route to make it require a login."""
    unauthorized = HTTPException(status_code=401, detail="Not authenticated. Log in and send the token.",
                                 headers={"WWW-Authenticate": "Bearer"})
    if credentials is None:
        raise unauthorized
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise unauthorized          # wrong signature, expired, or not a token at all
    user = db.get(User, user_id)
    if user is None:
        raise unauthorized
    return user