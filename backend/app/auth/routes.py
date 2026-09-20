"""Register, login, logout, current user."""
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth.schemas import LoginIn, RegisterIn, TokenOut, UserOut
from app.auth.security import DUMMY_HASH, create_access_token, get_current_user, hash_password, verify_password
from app.database.database import get_db
from app.database.models import User

router = APIRouter(prefix="/auth", tags=["Authentication"])

# basic rate limiting: at most 5 failed logins per email + address in 15 minutes
MAX_FAILURES, WINDOW_SECONDS = 5, 15 * 60
_failures: dict[str, list[float]] = {}


def _recent_failures(key: str) -> list[float]:
    cutoff = time.time() - WINDOW_SECONDS
    _failures[key] = [moment for moment in _failures.get(key, []) if moment > cutoff]
    return _failures[key]


@router.post("/register", response_model=UserOut, status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    user = User(name=body.name.strip(), email=email, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    key = f"{email}|{request.client.host if request.client else 'unknown'}"
    if len(_recent_failures(key)) >= MAX_FAILURES:
        raise HTTPException(status_code=429, detail="Too many failed logins. Try again in 15 minutes.")

    user = db.query(User).filter(User.email == email).first()
    password_ok = verify_password(body.password, user.password_hash if user else DUMMY_HASH)
    if not user or not password_ok:
        _failures[key].append(time.time())
        # the same message for "no such email" and "wrong password": never reveal which one it was
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    _failures.pop(key, None)
    return {"access_token": create_access_token(user.id), "token_type": "bearer", "user": user}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/logout")
def logout(user: User = Depends(get_current_user)):
    """A JWT lives on the client, so logging out means the client deletes its token."""
    return {"message": f"Goodbye {user.name}. Delete the token on the client to finish logging out."}