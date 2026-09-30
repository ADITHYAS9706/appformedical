from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.api.deps import CurrentUserDep, SessionDep
from app.core.config import settings
from app.core.security import create_access_token, get_signing_secret, hash_password, verify_password
from app.models.user import AppUser
from app.schemas.auth import TokenRead, UserLogin, UserRead, UserRegister

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(payload: UserRegister, session: SessionDep):
    if payload.role.value == "clinician":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Clinician accounts must be provisioned by a trusted operator.",
        )
    try:
        get_signing_secret()
    except RuntimeError:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Authentication is not configured securely. Set AUTH_SECRET_KEY to a random value of at least 32 bytes, then restart the backend.",
        )
    user = AppUser(
        email=str(payload.email).strip().lower(),
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.") from exc
    await session.refresh(user)
    return user


@router.post("/login", response_model=TokenRead)
async def login(payload: UserLogin, session: SessionDep):
    user = (
        await session.exec(
            select(AppUser).where(AppUser.email == str(payload.email).strip().lower())
        )
    ).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        get_signing_secret()
    except RuntimeError:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Authentication is not configured securely on the server. Set a 32-byte AUTH_SECRET_KEY.",
        )
    return TokenRead(
        access_token=create_access_token(user.id),
        expires_in=settings.auth_token_expire_minutes * 60,
    )


@router.get("/me", response_model=UserRead)
async def get_me(user: CurrentUserDep):
    return user