import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import app.models
import app.api.routes.records as records_routes
from app.api.deps import get_session
from app.api.routes.records import delete_record
from app.core.config import settings
from app.main import app
from app.models.enums import EventType, ProcessingStatus
from app.models.event import MedicalEvent
from app.models.patient import Patient
from app.models.record import MedicalRecord
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession


class TestRecordDeletion(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.engine = create_async_engine(
            f"sqlite+aiosqlite:///{self.root / 'records.db'}"
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def asyncTearDown(self):
        await self.engine.dispose()
        self.temp_dir.cleanup()

    async def test_delete_removes_failed_record_file_and_events_only(self):
        patient = Patient(first_name="Test", last_name="Patient")
        target_path = self.root / "failed-upload.jpg"
        sibling_path = self.root / "other-upload.jpg"
        target_path.write_bytes(b"target")
        sibling_path.write_bytes(b"sibling")

        target = MedicalRecord(
            patient_id=patient.id,
            original_filename="failed-upload.jpg",
            content_type="image/jpeg",
            file_size=6,
            storage_path=str(target_path),
            status=ProcessingStatus.FAILED,
        )
        sibling = MedicalRecord(
            patient_id=patient.id,
            original_filename="other-upload.jpg",
            content_type="image/jpeg",
            file_size=7,
            storage_path=str(sibling_path),
            status=ProcessingStatus.COMPLETED,
        )
        target_event = MedicalEvent(
            patient_id=patient.id,
            record_id=target.id,
            event_type=EventType.TEST,
            event_date=date(2025, 1, 2),
            description="Target event",
        )
        sibling_event = MedicalEvent(
            patient_id=patient.id,
            record_id=sibling.id,
            event_type=EventType.VISIT,
            event_date=date(2025, 2, 3),
            description="Sibling event",
        )

        async with self.session_factory() as session:
            session.add_all([patient, target, sibling, target_event, sibling_event])
            await session.commit()

            response = await delete_record(target.id, session)

            self.assertEqual(response.status_code, 204)
            self.assertIsNone(await session.get(MedicalRecord, target.id))
            self.assertIsNotNone(await session.get(MedicalRecord, sibling.id))
            events = (await session.exec(select(MedicalEvent))).all()
            self.assertEqual([event.id for event in events], [sibling_event.id])
            self.assertFalse(target_path.exists())
            self.assertTrue(sibling_path.exists())
            self.assertIsNotNone(await session.get(Patient, patient.id))

            await delete_record(sibling.id, session)
            self.assertIsNone(await session.get(MedicalRecord, sibling.id))
            self.assertFalse(sibling_path.exists())
            self.assertEqual((await session.exec(select(MedicalEvent))).all(), [])

            with self.assertRaises(HTTPException) as error:
                await delete_record(target.id, session)
            self.assertEqual(error.exception.status_code, 404)

    async def test_upload_process_and_delete_lifecycle(self):
        patient = Patient(first_name="Test", last_name="Timeline")
        async with self.session_factory() as session:
            session.add(patient)
            await session.commit()

        original_upload_dir = settings.upload_dir
        original_overrides = app.dependency_overrides.copy()
        settings.upload_dir = self.root / "uploads"

        async def override_session():
            async with self.session_factory() as session:
                yield session

        async def process_without_llm(record_id):
            async with self.session_factory() as session:
                record = await session.get(MedicalRecord, record_id)
                record.status = ProcessingStatus.COMPLETED
                session.add(
                    MedicalEvent(
                        patient_id=patient.id,
                        record_id=record_id,
                        event_type=EventType.TEST,
                        event_date=date(2025, 3, 4),
                        description="Synthetic test event",
                    )
                )
                await session.commit()

        app.dependency_overrides[get_session] = override_session
        try:
            with patch.object(records_routes, "process_record", process_without_llm):
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    upload = await client.post(
                        "/api/records/upload",
                        data={"patient_id": str(patient.id)},
                        files={"files": ("synthetic.jpg", b"\xff\xd8\xffimage", "image/jpeg")},
                    )
                    self.assertEqual(upload.status_code, 202)
                    record_id = upload.json()[0]["id"]

                    records = await client.get(
                        "/api/records",
                        params={"patient_id": str(patient.id)},
                    )
                    self.assertEqual(records.json()[0]["status"], "completed")
                    events = await client.get(
                        "/api/events",
                        params={"patient_id": str(patient.id)},
                    )
                    self.assertEqual(len(events.json()["items"]), 1)

                    stored_files = list(settings.upload_dir.rglob("*"))
                    stored_files = [path for path in stored_files if path.is_file()]
                    self.assertEqual(len(stored_files), 1)

                    deleted = await client.delete(f"/api/records/{record_id}")
                    self.assertEqual(deleted.status_code, 204)
                    self.assertFalse(stored_files[0].exists())

                    records = await client.get(
                        "/api/records",
                        params={"patient_id": str(patient.id)},
                    )
                    events = await client.get(
                        "/api/events",
                        params={"patient_id": str(patient.id)},
                    )
                    self.assertEqual(records.json(), [])
                    self.assertEqual(events.json()["items"], [])
        finally:
            settings.upload_dir = original_upload_dir
            app.dependency_overrides.clear()
            app.dependency_overrides.update(original_overrides)


if __name__ == "__main__":
    unittest.main()