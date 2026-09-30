"""Create a trusted account and optionally claim legacy unowned profiles."""

import argparse
import asyncio
from getpass import getpass

from pydantic import EmailStr, TypeAdapter
from sqlalchemy import update

from app.core.database import async_session_factory, engine, init_db
from app.core.security import hash_password
from app.models.enums import UserRole
from app.models.patient import Patient
from app.models.user import AppUser


async def bootstrap(
    email: str,
    password: str,
    role: UserRole,
    claim_existing_profiles: bool,
) -> int:
    await init_db()
    async with async_session_factory() as session:
        user = AppUser(email=email, password_hash=hash_password(password), role=role)
        session.add(user)
        await session.flush()
        result = None
        if role == UserRole.CAREGIVER and claim_existing_profiles:
            result = await session.exec(
                update(Patient)
                .where(Patient.owner_user_id.is_(None))
                .values(owner_user_id=user.id)
            )
        await session.commit()
        return result.rowcount if result is not None else 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("email", help="Email for the trusted initial account")
    parser.add_argument(
        "--role",
        choices=[UserRole.CAREGIVER.value, UserRole.CLINICIAN.value],
        default=UserRole.CAREGIVER.value,
    )
    parser.add_argument(
        "--claim-existing-profiles",
        action="store_true",
        help="Assign every unowned legacy profile to this caregiver (only for a single-owner dataset).",
    )
    args = parser.parse_args()
    email = str(TypeAdapter(EmailStr).validate_python(args.email)).lower()
    password = getpass("Password (minimum 12 characters): ")
    confirmation = getpass("Confirm password: ")
    if password != confirmation:
        parser.error("Passwords do not match.")
    if len(password) < 12:
        parser.error("Password must contain at least 12 characters.")

    try:
        claimed = asyncio.run(
            bootstrap(email, password, UserRole(args.role), args.claim_existing_profiles)
        )
        print(f"Created {args.role} account for {email}; assigned {claimed} existing profiles.")
    finally:
        asyncio.run(engine.dispose())


if __name__ == "__main__":
    main()