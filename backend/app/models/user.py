from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, String
from sqlmodel import Field, SQLModel

from app.models.base import utcnow
from app.models.enums import UserRole, pg_enum


class AppUser(SQLModel, table=True):
    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(sa_column=Column(String(320), unique=True, index=True, nullable=False))
    password_hash: str
    role: UserRole = Field(
        sa_column=Column(pg_enum(UserRole, "user_role"), nullable=False, index=True)
    )
    created_at: datetime = Field(
        default_factory=utcnow, sa_type=DateTime(timezone=True), nullable=False
    )