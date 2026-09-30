import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
