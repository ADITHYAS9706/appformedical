import tempfile
import unittest
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core import database
from app.core.config import settings


class TestSQLiteFallback(unittest.IsolatedAsyncioTestCase):
    async def test_init_db_works_for_sqlite_without_pg_lock(self):
        temp_db = Path(tempfile.gettempdir()) / "medical_timeline_sqlite_test.db"
        if temp_db.exists():
            temp_db.unlink()

        original_url = settings.database_url
        original_engine = database.engine
        settings.database_url = f"sqlite+aiosqlite:///{temp_db}"
        database.engine = create_async_engine(settings.database_url)

        try:
            await database.init_db()
        finally:
            await database.engine.dispose()
            settings.database_url = original_url
            database.engine = original_engine
            if temp_db.exists():
                temp_db.unlink()

    async def test_init_db_adds_owner_column_to_existing_patient_table(self):
        temp_db = Path(tempfile.gettempdir()) / "medical_timeline_legacy_test.db"
        if temp_db.exists():
            temp_db.unlink()

        original_url = settings.database_url
        original_engine = database.engine
        settings.database_url = f"sqlite+aiosqlite:///{temp_db}"
        database.engine = create_async_engine(settings.database_url)

        try:
            async with database.engine.begin() as conn:
                await conn.execute(text(
                    "CREATE TABLE patients ("
                    "id CHAR(32) PRIMARY KEY, first_name VARCHAR(100) NOT NULL, "
                    "last_name VARCHAR(100) NOT NULL, date_of_birth DATE, "
                    "mrn VARCHAR(64), created_at DATETIME NOT NULL)"
                ))

            await database.init_db()

            async with database.engine.connect() as conn:
                columns = await conn.run_sync(
                    lambda sync_conn: {
                        column["name"]
                        for column in inspect(sync_conn).get_columns("patients")
                    }
                )
            self.assertIn("owner_user_id", columns)
        finally:
            await database.engine.dispose()
            settings.database_url = original_url
            database.engine = original_engine
            if temp_db.exists():
                temp_db.unlink()


if __name__ == "__main__":
    unittest.main()
