import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import api, database, security
from app.content import repository


class AdminContentApiTests(unittest.TestCase):
    def setUp(self):
        self.root = Path("D:/L-One Center/test-temp/content-api") / uuid.uuid4().hex
        self.root.mkdir(parents=True)
        self.database_path = self.root / "content.db"
        self.credentials_path = self.root / "credentials.json"
        self.password_hash = security.hash_password("old-password", iterations=1000)
        self.patches = [
            patch.object(database, "DATABASE_PATH", self.database_path),
            patch.object(api, "ADMIN_USERNAME", "owner"),
            patch.object(api, "ADMIN_PASSWORD_HASH", self.password_hash),
            patch.object(api, "SESSION_SECRET", "session-secret"),
            patch.object(api, "ADMIN_CREDENTIALS_PATH", self.credentials_path),
            patch.object(api, "ensure_directories"),
            patch.object(api, "initialize"),
        ]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)
        database.initialize()
        self.client = TestClient(api.app, base_url="https://admin.l-one.asia")
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def login(self):
        response = self.client.post(
            "/api/admin/login",
            json={"username": "owner", "password": "old-password"},
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["csrfToken"]

    def content_payload(self):
        return {
            "target": "works",
            "content_type": "article",
            "title": "API draft",
            "excerpt": "summary",
            "cover_media_id": "a" * 32,
            "body": [{"type": "paragraph", "text": "Body"}],
        }

    def test_content_endpoints_require_authentication_and_csrf(self):
        self.assertEqual(self.client.get("/api/admin/v1/content").status_code, 401)
        self.login()
        self.assertEqual(
            self.client.post("/api/admin/v1/content", json=self.content_payload()).status_code,
            403,
        )

    def test_create_update_publish_version_restore_and_audit(self):
        csrf = self.login()
        headers = {"X-CSRF-Token": csrf}
        created_response = self.client.post(
            "/api/admin/v1/content", json=self.content_payload(), headers=headers
        )
        self.assertEqual(created_response.status_code, 201)
        created = created_response.json()["data"]
        content_id = created["id"]

        updated_response = self.client.patch(
            f"/api/admin/v1/content/{content_id}",
            json={"revision": created["revision"], "title": "Updated title"},
            headers=headers,
        )
        self.assertEqual(updated_response.status_code, 200)
        updated = updated_response.json()["data"]
        conflict = self.client.patch(
            f"/api/admin/v1/content/{content_id}",
            json={"revision": created["revision"], "title": "Stale"},
            headers=headers,
        )
        self.assertEqual(conflict.status_code, 409)

        published = self.client.post(
            f"/api/admin/v1/content/{content_id}/status",
            json={"status": "published"},
            headers=headers,
        )
        self.assertEqual(published.status_code, 200)
        versions = self.client.get(f"/api/admin/v1/content/{content_id}/versions")
        self.assertGreaterEqual(len(versions.json()["data"]), 3)
        oldest = versions.json()["data"][-1]
        restored = self.client.post(
            f"/api/admin/v1/content/{content_id}/versions/{oldest['id']}/restore",
            headers=headers,
        )
        self.assertEqual(restored.status_code, 200)
        self.assertEqual(restored.json()["data"]["title"], "API draft")
        actions = {entry["action"] for entry in database.list_audit(20)}
        self.assertTrue({"content.create", "content.update", "content.status", "content.restore"} <= actions)
        self.assertEqual(updated["revision"], created["revision"] + 1)

    def test_taxonomy_filters_by_target(self):
        item = repository.create_content(self.content_payload(), "owner")
        repository.attach_category(item["id"], "travel", "Travel")
        repository.attach_tags(item["id"], ["Beijing", "Photo"])
        self.login()
        categories = self.client.get("/api/admin/v1/categories?target=works")
        tags = self.client.get("/api/admin/v1/tags?target=works")
        self.assertEqual(categories.json()["data"][0]["slug"], "travel")
        self.assertEqual({tag["slug"] for tag in tags.json()["data"]}, {"beijing", "photo"})

    def test_password_change_revokes_existing_session_and_persists_hash_only(self):
        csrf = self.login()
        response = self.client.post(
            "/api/admin/v1/account/password",
            json={"current_password": "old-password", "new_password": "new-password-123"},
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/admin/session").status_code, 401)
        stored = self.credentials_path.read_text(encoding="utf-8")
        self.assertNotIn("new-password-123", stored)
        login = self.client.post(
            "/api/admin/login",
            json={"username": "owner", "password": "new-password-123"},
        )
        self.assertEqual(login.status_code, 200)


if __name__ == "__main__":
    unittest.main()
