from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import EmailStr
from sqlmodel import Field, SQLModel

from app.models.enums import UserRole


class UserRegister(SQLModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    role: UserRole = UserRole.PATIENT


class UserLogin(SQLModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserRead(SQLModel):
    id: UUID
    email: EmailStr
    role: UserRole
    created_at: datetime


class TokenRead(SQLModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class ClinicianGrantCreate(SQLModel):
    clinician_email: EmailStr
    expires_at: datetime | None = None


class ClinicianGrantRead(SQLModel):
    id: UUID
    patient_id: UUID
    clinician_user_id: UUID
    clinician_email: EmailStr
    created_at: datetime
    expires_at: datetime | None
    revoked_at: datetime | None
