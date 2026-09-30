from typing import Annotated
from datetime import datetime, timezone
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import or_
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.security import get_signing_secret
from app.core.database import get_session
from app.models.enums import UserRole
from app.models.patient import Patient
from app.models.patient_grant import PatientClinicianGrant
from app.models.user import AppUser

SessionDep = Annotated[AsyncSession, Depends(get_session)]

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
	credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
	session: SessionDep,
) -> AppUser:
	unauthorized = HTTPException(
		status.HTTP_401_UNAUTHORIZED,
		"Authentication is required.",
		headers={"WWW-Authenticate": "Bearer"},
	)
	if credentials is None:
		raise unauthorized
	try:
		secret = get_signing_secret()
	except RuntimeError:
		raise HTTPException(
			status.HTTP_503_SERVICE_UNAVAILABLE,
			"Authentication is not configured securely on the server.",
		)
	try:
		payload = jwt.decode(
			credentials.credentials,
			secret,
			algorithms=["HS256"],
		)
		user_id = UUID(payload["sub"])
	except (jwt.InvalidTokenError, KeyError, ValueError):
		raise unauthorized
	user = await session.get(AppUser, user_id)
	if user is None:
		raise unauthorized
	return user


CurrentUserDep = Annotated[AppUser, Depends(get_current_user)]


async def get_accessible_patient_ids(session: AsyncSession, user: AppUser) -> set[UUID]:
	owned = set(
		(await session.exec(select(Patient.id).where(Patient.owner_user_id == user.id))).all()
	)
	if user.role != UserRole.CLINICIAN:
		return owned
	now = datetime.now(timezone.utc)
	grants = await session.exec(
		select(PatientClinicianGrant.patient_id).where(
			PatientClinicianGrant.clinician_user_id == user.id,
			PatientClinicianGrant.revoked_at.is_(None),
			or_(PatientClinicianGrant.expires_at.is_(None), PatientClinicianGrant.expires_at > now),
		)
	)
	return owned | set(grants.all())


async def require_patient_access(
	session: AsyncSession,
	user: AppUser,
	patient_id: UUID,
	*,
	write: bool = False,
) -> Patient:
	patient = await session.get(Patient, patient_id)
	if patient is None:
		raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient profile not found.")
	if patient.owner_user_id == user.id and (
		not write or user.role in {UserRole.PATIENT, UserRole.CAREGIVER}
	):
		return patient
	if not write and user.role == UserRole.CLINICIAN:
		now = datetime.now(timezone.utc)
		grant = await session.exec(
			select(PatientClinicianGrant.id).where(
				PatientClinicianGrant.patient_id == patient_id,
				PatientClinicianGrant.clinician_user_id == user.id,
				PatientClinicianGrant.revoked_at.is_(None),
				or_(
					PatientClinicianGrant.expires_at.is_(None),
					PatientClinicianGrant.expires_at > now,
				),
			)
		)
		if grant.first() is not None:
			return patient
	raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient profile not found.")
