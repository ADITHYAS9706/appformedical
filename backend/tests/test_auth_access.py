import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

import app.models
from app.api.deps import get_session
from app.core.config import settings
from app.main import app
from app.models.enums import UserRole
from app.models.patient_grant import PatientClinicianGrant
from app.models.user import AppUser
from app.core.security import hash_password


class TestAuthAccess(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "auth.db"
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}")
        async with self.engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        self.original_secret = settings.auth_secret_key
        self.original_overrides = app.dependency_overrides.copy()
        settings.auth_secret_key = "test-only-signing-key-at-least-thirty-two-bytes-long"

        async def override_session():
            async with self.session_factory() as session:
                yield session

        app.dependency_overrides[get_session] = override_session
        self.client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.original_overrides)
        settings.auth_secret_key = self.original_secret
        await self.engine.dispose()
        self.temp_dir.cleanup()

    async def register_and_login(self, email, role="caregiver"):
        registered = await self.client.post(
            "/api/auth/register",
            json={"email": email, "password": "long-test-password-123", "role": role},
        )
        self.assertEqual(registered.status_code, 201, registered.text)
        logged_in = await self.client.post(
            "/api/auth/login",
            json={"email": email, "password": "long-test-password-123"},
        )
        self.assertEqual(logged_in.status_code, 200, logged_in.text)
        return {"Authorization": f"Bearer {logged_in.json()['access_token']}"}

    async def test_role_scopes_and_revocable_clinician_access(self):
        self.assertEqual((await self.client.get("/api/patients")).status_code, 401)
        self.assertEqual(
            (
                await self.client.post(
                    "/api/auth/register",
                    json={
                        "email": "self-appointed@example.com",
                        "password": "long-test-password-123",
                        "role": "clinician",
                    },
                )
            ).status_code,
            403,
        )

        caregiver_headers = await self.register_and_login("caregiver@example.com")
        first = await self.client.post(
            "/api/patients",
            headers=caregiver_headers,
            json={"first_name": "Dependent", "last_name": "One"},
        )
        second = await self.client.post(
            "/api/patients",
            headers=caregiver_headers,
            json={"first_name": "Dependent", "last_name": "Two"},
        )
        self.assertEqual(first.status_code, 201, first.text)
        self.assertEqual(second.status_code, 201, second.text)
        first_id = first.json()["id"]
        second_id = second.json()["id"]
        caregiver_patients = await self.client.get("/api/patients", headers=caregiver_headers)
        self.assertEqual({p["id"] for p in caregiver_patients.json()}, {first_id, second_id})

        stranger_headers = await self.register_and_login("stranger@example.com")
        self.assertEqual((await self.client.get("/api/patients", headers=stranger_headers)).json(), [])
        self.assertEqual(
            (await self.client.get(f"/api/patients/{first_id}", headers=stranger_headers)).status_code,
            404,
        )

        async with self.session_factory() as session:
            clinician = AppUser(
                email="clinician@example.com",
                password_hash=hash_password("long-test-password-123"),
                role=UserRole.CLINICIAN,
            )
            session.add(clinician)
            await session.commit()
        clinician_headers = await self.client.post(
            "/api/auth/login",
            json={"email": "clinician@example.com", "password": "long-test-password-123"},
        )
        self.assertEqual(clinician_headers.status_code, 200)
        clinician_auth = {"Authorization": f"Bearer {clinician_headers.json()['access_token']}"}

        grant = await self.client.post(
            f"/api/patients/{first_id}/clinician-grants",
            headers=caregiver_headers,
            json={"clinician_email": "clinician@example.com"},
        )
        self.assertEqual(grant.status_code, 201, grant.text)
        clinician_patients = await self.client.get("/api/patients", headers=clinician_auth)
        self.assertEqual([p["id"] for p in clinician_patients.json()], [first_id])
        self.assertEqual(
            (await self.client.get(f"/api/patients/{second_id}", headers=clinician_auth)).status_code,
            404,
        )

        async with self.session_factory() as session:
            active_grant = await session.get(
                PatientClinicianGrant,
                UUID(grant.json()["id"]),
            )
            active_grant.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
            session.add(active_grant)
            await session.commit()
        self.assertEqual(
            (await self.client.get(f"/api/patients/{first_id}", headers=clinician_auth)).status_code,
            404,
        )
        grant = await self.client.post(
            f"/api/patients/{first_id}/clinician-grants",
            headers=caregiver_headers,
            json={"clinician_email": "clinician@example.com"},
        )
        self.assertEqual(grant.status_code, 201, grant.text)
        self.assertIsNone(grant.json()["expires_at"])

        event = await self.client.post(
            "/api/events",
            headers=caregiver_headers,
            json={
                "patient_id": first_id,
                "event_type": "test",
                "event_date": "2025-01-02",
                "description": "Caregiver-created event",
            },
        )
        self.assertEqual(event.status_code, 201, event.text)
        visible_events = await self.client.get(
            "/api/events",
            headers=clinician_auth,
            params={"patient_id": first_id},
        )
        self.assertEqual(visible_events.json()["total"], 1)
        denied_write = await self.client.patch(
            f"/api/events/{event.json()['id']}",
            headers=clinician_auth,
            json={"description": "Unauthorized edit"},
        )
        self.assertEqual(denied_write.status_code, 404)

        revoked = await self.client.delete(
            f"/api/patients/{first_id}/clinician-grants/{grant.json()['id']}",
            headers=caregiver_headers,
        )
        self.assertEqual(revoked.status_code, 204)
        self.assertEqual(
            (await self.client.get(f"/api/patients/{first_id}", headers=clinician_auth)).status_code,
            404,
        )
        still_owned = await self.client.get(f"/api/patients/{first_id}", headers=caregiver_headers)
        self.assertEqual(still_owned.status_code, 200)

    async def test_registration_fails_clearly_without_signing_secret(self):
        settings.auth_secret_key = None
        response = await self.client.post(
            "/api/auth/register",
            json={
                "email": "not-created@example.com",
                "password": "long-test-password-123",
                "role": "patient",
            },
        )
        self.assertEqual(response.status_code, 503)
        self.assertIn("AUTH_SECRET_KEY", response.json()["detail"])

        async with self.session_factory() as session:
            user = (
                await session.exec(
                    select(AppUser).where(AppUser.email == "not-created@example.com")
                )
            ).first()
            self.assertIsNone(user)


if __name__ == "__main__":
    unittest.main()