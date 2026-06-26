from __future__ import annotations

from pydantic import BaseModel, Field


class InitAdminRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class AdminUserOut(BaseModel):
    id: int
    username: str
    role: str
    created_at: int
    last_login_at: int | None = None


class TokenOut(BaseModel):
    token: str
    token_type: str = "bearer"
    user: AdminUserOut

