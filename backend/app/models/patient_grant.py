from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.base import utcnow


class PatientClinicianGrant(SQLModel, table=True):
    __tablename__ = "patient_clinician_grants"
    __table_args__ = (
        UniqueConstraint("patient_id", "clinician_user_id", name="uq_patient_clinician_grant"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    patient_id: UUID = Field(foreign_key="patients.id", index=True, ondelete="CASCADE")
    clinician_user_id: UUID = Field(foreign_key="users.id", index=True, ondelete="CASCADE")
    granted_by_user_id: UUID = Field(foreign_key="users.id", ondelete="RESTRICT")
    created_at: datetime = Field(
        default_factory=utcnow, sa_type=DateTime(timezone=True), nullable=False
    )
    expires_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    revoked_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))