import re
from datetime import datetime
from typing import Any, Optional, Union
from pydantic import BaseModel, Field, field_validator


class RegisterRequest(BaseModel):
    """Payload for user registration."""
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="User password (minimum 6 characters)")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("Invalid email address format.")
        return v


class LoginRequest(BaseModel):
    """Payload for user login."""
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("Invalid email address format.")
        return v


class UserResponse(BaseModel):
    """Sanitized user profile matching Supabase auth.users."""
    id: str = Field(..., description="Supabase auth.users.id (UUID)")
    email: Optional[str] = Field(None, description="User email address")
    created_at: Optional[Union[datetime, str]] = Field(None, description="Account creation timestamp")
    user_metadata: Optional[dict[str, Any]] = Field(default_factory=dict, description="User metadata dictionary")
    app_metadata: Optional[dict[str, Any]] = Field(default_factory=dict, description="Server-controlled application metadata")


class SessionResponse(BaseModel):
    """Supabase authenticated session tokens."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: Optional[str] = Field(None, description="Refresh token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: Optional[int] = Field(None, description="Token lifetime in seconds")
    expires_at: Optional[int] = Field(None, description="UNIX timestamp when token expires")


class AuthResponseSchema(BaseModel):
    """Standard response for authentication operations (register, login)."""
    user: UserResponse
    session: Optional[SessionResponse] = None
    message: Optional[str] = None


class MessageResponse(BaseModel):
    """Generic operation status response."""
    message: str
