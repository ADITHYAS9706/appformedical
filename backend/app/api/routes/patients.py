from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import col, func, select

from app.api.deps import (
    CurrentUserDep,
    SessionDep,
    get_accessible_patient_ids,
    require_patient_access,
)
from app.models.base import utcnow
from app.models.enums import UserRole
from app.models.patient_grant import PatientClinicianGrant
from app.models.patient import Patient
from app.models.user import AppUser
from app.schemas.auth import ClinicianGrantCreate, ClinicianGrantRead
from app.schemas.patient import PatientCreate, PatientRead

router = APIRouter(prefix="/patients", tags=["patients"])


@router.post("", response_model=PatientRead, status_code=status.HTTP_201_CREATED)
async def create_patient(payload: PatientCreate, session: SessionDep, user: CurrentUserDep):
    if user.role == UserRole.CLINICIAN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Clinicians cannot create patient profiles.")
    if user.role == UserRole.PATIENT:
        count = (
            await session.exec(
                select(func.count()).select_from(Patient).where(Patient.owner_user_id == user.id)
            )
        ).one()
        if count:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Patient accounts can own one profile. Caregiver accounts can manage dependents.",
            )
    patient = Patient.model_validate(payload)
    patient.owner_user_id = user.id
    session.add(patient)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "A patient with this MRN already exists.")
    return patient


@router.get("", response_model=list[PatientRead])
async def list_patients(
    session: SessionDep,
    user: CurrentUserDep,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    accessible_ids = await get_accessible_patient_ids(session, user)
    stmt = (
        select(Patient)
        .where(col(Patient.id).in_(accessible_ids))
        .order_by(col(Patient.last_name), col(Patient.first_name))
        .limit(limit)
        .offset(offset)
    )
    return (await session.exec(stmt)).all()


@router.get("/{patient_id}", response_model=PatientRead)
async def get_patient(patient_id: UUID, session: SessionDep, user: CurrentUserDep):
    return await require_patient_access(session, user, patient_id)


@router.get("/{patient_id}/clinician-grants", response_model=list[ClinicianGrantRead])
async def list_clinician_grants(
    patient_id: UUID,
    session: SessionDep,
    user: CurrentUserDep,
):
    await require_patient_access(session, user, patient_id, write=True)
    rows = await session.exec(
        select(PatientClinicianGrant, AppUser.email)
        .join(AppUser, AppUser.id == PatientClinicianGrant.clinician_user_id)
        .where(PatientClinicianGrant.patient_id == patient_id)
        .order_by(col(PatientClinicianGrant.created_at).desc())
    )
    return [
        ClinicianGrantRead(
            id=grant.id,
            patient_id=grant.patient_id,
            clinician_user_id=grant.clinician_user_id,
            clinician_email=email,
            created_at=grant.created_at,
            expires_at=grant.expires_at,
            revoked_at=grant.revoked_at,
        )
        for grant, email in rows.all()
    ]


@router.post(
    "/{patient_id}/clinician-grants",
    response_model=ClinicianGrantRead,
    status_code=status.HTTP_201_CREATED,
)
async def grant_clinician_access(
    patient_id: UUID,
    payload: ClinicianGrantCreate,
    session: SessionDep,
    user: CurrentUserDep,
):
    await require_patient_access(session, user, patient_id, write=True)
    if payload.expires_at and payload.expires_at.tzinfo is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "expires_at must include a timezone.")
    if payload.expires_at and payload.expires_at <= utcnow():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "expires_at must be in the future.")

    clinician = (
        await session.exec(
            select(AppUser).where(AppUser.email == str(payload.clinician_email).strip().lower())
        )
    ).first()
    if clinician is None or clinician.role != UserRole.CLINICIAN:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Clinician account not found.")

    grant = (
        await session.exec(
            select(PatientClinicianGrant).where(
                PatientClinicianGrant.patient_id == patient_id,
                PatientClinicianGrant.clinician_user_id == clinician.id,
            )
        )
    ).first()
    if grant is None:
        grant = PatientClinicianGrant(
            patient_id=patient_id,
            clinician_user_id=clinician.id,
            granted_by_user_id=user.id,
            expires_at=payload.expires_at,
        )
    else:
        grant.granted_by_user_id = user.id
        grant.created_at = utcnow()
        grant.expires_at = payload.expires_at
        grant.revoked_at = None
    session.add(grant)
    await session.commit()
    await session.refresh(grant)
    return ClinicianGrantRead(
        id=grant.id,
        patient_id=patient_id,
        clinician_user_id=clinician.id,
        clinician_email=clinician.email,
        created_at=grant.created_at,
        expires_at=grant.expires_at,
        revoked_at=grant.revoked_at,
    )


@router.delete("/{patient_id}/clinician-grants/{grant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_clinician_access(
    patient_id: UUID,
    grant_id: UUID,
    session: SessionDep,
    user: CurrentUserDep,
):
    await require_patient_access(session, user, patient_id, write=True)
    grant = (
        await session.exec(
            select(PatientClinicianGrant).where(
                PatientClinicianGrant.id == grant_id,
                PatientClinicianGrant.patient_id == patient_id,
                PatientClinicianGrant.revoked_at.is_(None),
            )
        )
    ).first()
    if grant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Active clinician grant not found.")
    grant.revoked_at = utcnow()
    session.add(grant)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
