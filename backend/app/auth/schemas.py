"""Request and response shapes for authentication."""
import datetime as dt

from pydantic import BaseModel, ConfigDict, Field

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=100, examples=["Asha Patel"])
    email: str = Field(pattern=EMAIL_PATTERN, max_length=255, examples=["asha@example.com"])
    password: str = Field(min_length=8, max_length=128, examples=["a-long-password"])


class LoginIn(BaseModel):
    email: str = Field(max_length=255, examples=["asha@example.com"])
    password: str = Field(max_length=128, examples=["a-long-password"])


class UserOut(BaseModel):
    """Note what is NOT here: password_hash never leaves the server."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    created_at: dt.datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut