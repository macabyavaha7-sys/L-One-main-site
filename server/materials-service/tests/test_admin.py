import json
import shutil
import time
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import api, database, maintenance, pipeline, security


class AdminTests(unittest.TestCase):
    def make_directory(self) -> Path:
        path = Path("D:/L-One Center/test-temp/materials-admin") / uuid.uuid4().hex
        path.mkdir(parents=True)
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def test_password_hash_verifies_only_matching_password(self):
        encoded = security.hash_password("correct horse battery staple", iterations=1000)
        self.assertTrue(security.verify_password("correct horse battery staple", encoded))
        self.assertFalse(security.verify_password("wrong", encoded))

    def test_signed_session_expires_and_validates_csrf(self):
        token, csrf = security.create_session("owner", "secret", ttl_seconds=60, now=100)
        session = security.read_session(token, "secret", now=120)
        self.assertEqual(session["username"], "owner")
        self.assertTrue(security.valid_csrf(session, csrf))
        self.assertIsNone(security.read_session(token, "secret", now=161))

    def test_login_limiter_blocks_repeated_failures(self):
        limiter = security.LoginLimiter(max_attempts=3, window_seconds=60)
        for _ in range(3):
            limiter.record_failure("client", now=100)
        self.assertFalse(limiter.allowed("client", now=120))
        self.assertTrue(limiter.allowed("client", now=161))

    def test_audit_log_round_trip(self):
        database_path = self.make_directory() / "jobs.db"
        with patch.object(database, "DATABASE_PATH", database_path):
            database.initialize()
            database.record_audit("owner", "delete", "asset-1", "ok")
            row = database.list_audit()[0]
        self.assertEqual(row["action"], "delete")
        self.assertEqual(row["target"], "asset-1")

    def test_soft_delete_moves_asset_to_recycle(self):
        root = self.make_directory()
        asset_root = root / "assets"
        recycle_root = root / "recycle"
        manifest = root / "data" / "assets.json"
        asset_id = "a" * 32
        item = asset_root / asset_id
        item.mkdir(parents=True)
        (item / "metadata.json").write_text(json.dumps({"id": asset_id}), encoding="utf-8")
        with patch.object(pipeline, "ASSET_ROOT", asset_root), patch.object(pipeline, "RECYCLE_ROOT", recycle_root), patch.object(pipeline, "MANIFEST_PATH", manifest):
            self.assertTrue(pipeline.soft_delete_asset(asset_id, now=100))
        self.assertFalse(item.exists())
        self.assertEqual(len(list(recycle_root.iterdir())), 1)
        self.assertEqual(json.loads(manifest.read_text(encoding="utf-8")), [])

    def test_publish_replacement_keeps_stable_asset_id(self):
        root = self.make_directory()
        asset_root = root / "assets"
        recycle_root = root / "recycle"
        old = asset_root / ("b" * 32)
        working = root / "working"
        old.mkdir(parents=True)
        working.mkdir()
        (old / "old.txt").write_text("old", encoding="utf-8")
        (working / "new.txt").write_text("new", encoding="utf-8")
        with patch.object(pipeline, "ASSET_ROOT", asset_root), patch.object(pipeline, "RECYCLE_ROOT", recycle_root):
            target = pipeline.publish_directory(working, "b" * 32, now=100)
        self.assertEqual(target.name, "b" * 32)
        self.assertTrue((target / "new.txt").exists())
        self.assertEqual(len(list(recycle_root.iterdir())), 1)

    def test_cleanup_recycle_removes_only_expired_entries(self):
        root = self.make_directory()
        expired = root / "expired"
        current = root / "current"
        expired.mkdir()
        current.mkdir()
        with patch("app.pipeline.time.time", return_value=1_000_000):
            pipeline.cleanup_recycle(root, retention_seconds=100, now=1_000_000)
        self.assertTrue(current.exists())
        old = 1_000_000 - 101
        import os
        os.utime(expired, (old, old))
        pipeline.cleanup_recycle(root, retention_seconds=100, now=1_000_000)
        self.assertFalse(expired.exists())
        self.assertTrue(current.exists())

    def test_backup_state_copies_database_and_manifest(self):
        root = self.make_directory()
        database_path = root / "jobs.db"
        manifest_path = root / "assets.json"
        backup_root = root / "backups"
        database_path.write_text("db", encoding="utf-8")
        manifest_path.write_text("[]", encoding="utf-8")
        target = maintenance.backup_state(database_path, manifest_path, backup_root, stamp="20260615-120000")
        self.assertEqual((target / "jobs.db").read_text(encoding="utf-8"), "db")
        self.assertEqual((target / "assets.json").read_text(encoding="utf-8"), "[]")

    def test_login_creates_cookie_and_allows_protected_read(self):
        password_hash = security.hash_password("test-password", iterations=1000)
        with patch.object(api, "ADMIN_USERNAME", "owner"), patch.object(api, "ADMIN_PASSWORD_HASH", password_hash), patch.object(api, "SESSION_SECRET", "session-secret"), patch.object(api, "ensure_directories"), patch.object(api, "initialize"), patch.object(api, "record_audit"), patch.object(api, "list_assets", return_value=[]):
            with TestClient(api.app, base_url="https://admin.l-one.asia") as client:
                login = client.post("/api/admin/login", json={"username": "owner", "password": "test-password"})
                self.assertEqual(login.status_code, 200)
                self.assertIn("lone_admin_session", login.cookies)
                self.assertTrue(login.json()["csrfToken"])
                assets = client.get("/api/admin/assets")
                self.assertEqual(assets.status_code, 200)

    def test_mutation_rejects_missing_csrf(self):
        password_hash = security.hash_password("test-password", iterations=1000)
        with patch.object(api, "ADMIN_USERNAME", "owner"), patch.object(api, "ADMIN_PASSWORD_HASH", password_hash), patch.object(api, "SESSION_SECRET", "session-secret"), patch.object(api, "ensure_directories"), patch.object(api, "initialize"), patch.object(api, "record_audit"):
            with TestClient(api.app, base_url="https://admin.l-one.asia") as client:
                client.post("/api/admin/login", json={"username": "owner", "password": "test-password"})
                response = client.post("/api/admin/logout")
                self.assertEqual(response.status_code, 403)

    def test_disk_status_is_available_to_session(self):
        password_hash = security.hash_password("test-password", iterations=1000)
        usage = type("Usage", (), {"total": 1000, "used": 250, "free": 750})()
        with patch.object(api, "ADMIN_USERNAME", "owner"), patch.object(api, "ADMIN_PASSWORD_HASH", password_hash), patch.object(api, "SESSION_SECRET", "session-secret"), patch.object(api, "ensure_directories"), patch.object(api, "initialize"), patch.object(api, "record_audit"), patch.object(api, "list_jobs", return_value=[]), patch.object(api, "list_audit", return_value=[]), patch.object(api.shutil, "disk_usage", return_value=usage):
            with TestClient(api.app, base_url="https://admin.l-one.asia") as client:
                client.post("/api/admin/login", json={"username": "owner", "password": "test-password"})
                response = client.get("/api/admin/status")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["disk"]["freeBytes"], 750)


if __name__ == "__main__":
    unittest.main()
