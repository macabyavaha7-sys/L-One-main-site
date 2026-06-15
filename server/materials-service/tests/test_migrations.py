import sqlite3
import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from app import database


CONTENT_TABLES = {
    "schema_migrations",
    "content_items",
    "content_versions",
    "media_assets",
    "content_media",
    "categories",
    "tags",
    "content_tags",
    "import_jobs",
    "publication_jobs",
}


class MigrationTests(unittest.TestCase):
    def make_database(self) -> Path:
        root = Path("D:/L-One Center/test-temp/content-migrations") / uuid.uuid4().hex
        root.mkdir(parents=True)
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        return root / "jobs.db"

    def table_names(self, path: Path) -> set[str]:
        with sqlite3.connect(path) as connection:
            return {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }

    def test_initialize_preserves_existing_material_jobs(self):
        path = self.make_database()
        with patch.object(database, "DATABASE_PATH", path):
            database.initialize()
            database.create_job("job-1", "/tmp/a.mp4", "a.mp4", "A", "Test", ["one"])
            database.record_audit("owner", "upload", "job-1", "queued")
            database.initialize()
            self.assertEqual(database.list_jobs()[0]["id"], "job-1")
            self.assertEqual(database.list_audit()[0]["target"], "job-1")

    def test_initialize_creates_content_schema_once(self):
        path = self.make_database()
        with patch.object(database, "DATABASE_PATH", path):
            database.initialize()
            database.initialize()
        self.assertTrue(CONTENT_TABLES.issubset(self.table_names(path)))
        with sqlite3.connect(path) as connection:
            rows = connection.execute("SELECT version FROM schema_migrations").fetchall()
        self.assertEqual(rows, [(1,)])

    def test_schema_version_advances_transactionally(self):
        path = self.make_database()
        with patch.object(database, "DATABASE_PATH", path):
            database.initialize()
        with patch.object(database, "DATABASE_PATH", path), database.connect() as connection:
            version = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]
            foreign_keys = connection.execute("PRAGMA foreign_keys").fetchone()[0]
        self.assertEqual(version, 1)
        self.assertEqual(foreign_keys, 1)


if __name__ == "__main__":
    unittest.main()
