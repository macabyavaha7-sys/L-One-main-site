import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import api, database
from app.content import repository


class PublicContentApiTests(unittest.TestCase):
    def setUp(self):
        self.root = Path("D:/L-One Center/test-temp/public-content-api") / uuid.uuid4().hex
        self.root.mkdir(parents=True)
        self.database_path = self.root / "content.db"
        self.db_patch = patch.object(database, "DATABASE_PATH", self.database_path)
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)
        database.initialize()
        self.client = TestClient(api.app)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def create(self, title: str, content_type: str = "article", publish_at=None):
        return repository.create_content(
            {
                "target": "works",
                "content_type": content_type,
                "title": title,
                "slug": title.lower().replace(" ", "-"),
                "excerpt": "summary",
                "cover_media_id": "b" * 32,
                "body": [{"type": "paragraph", "text": "Body"}],
                "publish_at": publish_at,
            },
            "owner",
        )

    def test_list_exposes_only_due_published_records_and_filters_type(self):
        published = self.create("Published video", "video")
        repository.change_status(published["id"], "published", "owner")
        self.create("Draft video", "video")
        future = self.create("Future video", "video", "2099-01-01T00:00:00+00:00")
        repository.change_status(future["id"], "published", "owner")
        offline = self.create("Offline video", "video")
        repository.change_status(offline["id"], "offline", "owner")
        article = self.create("Published article", "article")
        repository.change_status(article["id"], "published", "owner")

        response = self.client.get("/api/public/v1/content?target=works&type=video")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["title"] for item in response.json()["data"]], ["Published video"])
        self.assertIn("ETag", response.headers)
        cached = self.client.get(
            "/api/public/v1/content?target=works&type=video",
            headers={"If-None-Match": response.headers["ETag"]},
        )
        self.assertEqual(cached.status_code, 304)

    def test_detail_uses_target_and_slug_and_hides_non_public_records(self):
        published = self.create("Visible detail")
        repository.change_status(published["id"], "published", "owner")
        draft = self.create("Hidden detail")
        visible = self.client.get("/api/public/v1/content/works/visible-detail")
        hidden = self.client.get("/api/public/v1/content/works/hidden-detail")
        self.assertEqual(visible.status_code, 200)
        self.assertEqual(visible.json()["data"]["id"], published["id"])
        self.assertNotIn("updated_by", visible.json()["data"])
        self.assertEqual(hidden.status_code, 404)
        self.assertTrue(draft["id"])

    def test_public_taxonomy_contains_only_terms_used_by_published_content(self):
        public = self.create("Tagged public")
        repository.attach_category(public["id"], "travel", "Travel")
        repository.attach_tags(public["id"], ["Beijing"])
        repository.change_status(public["id"], "published", "owner")
        draft = self.create("Tagged draft")
        repository.attach_category(draft["id"], "private", "Private")
        repository.attach_tags(draft["id"], ["Hidden"])

        categories = self.client.get("/api/public/v1/categories?target=works").json()["data"]
        tags = self.client.get("/api/public/v1/tags?target=works").json()["data"]
        self.assertEqual([item["slug"] for item in categories], ["travel"])
        self.assertEqual([item["slug"] for item in tags], ["beijing"])


if __name__ == "__main__":
    unittest.main()
