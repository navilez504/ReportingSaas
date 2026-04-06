from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.user import UserOut


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)

    @field_validator("email", mode="before")
    @classmethod
    def strip_email(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)
    full_name: str = Field(default="", max_length=255)

    @field_validator("email", mode="before")
    @classmethod
    def strip_email(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("full_name", mode="before")
    @classmethod
    def strip_full_name(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v
