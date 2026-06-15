import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from app import database
from app.content import repository
from app.content.validation import ContentValidationError, RevisionConflict


class ContentRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.root = Path("D:/L-One Center/test-temp/content-repository") / uuid.uuid4().hex
        self.root.mkdir(parents=True)
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))
        self.db = self.root / "content.db"
        self.database_patch = patch.object(database, "DATABASE_PATH", self.db)
        self.database_patch.start()
        self.addCleanup(self.database_patch.stop)
        database.initialize()

    def payload(self, **overrides):
        value = {
            "target": "works",
            "content_type": "article",
            "title": "首钢园 秋日记录",
            "excerpt": "摘要",
            "body": [{"type": "paragraph", "text": "正文"}],
            "cover_media_id": "cover-1",
        }
        value.update(overrides)
        return value

    def test_create_draft_assigns_stable_id_and_slug(self):
        item = repository.create_content(self.payload(), "owner")
        loaded = repository.get_content(item["id"])
        self.assertEqual(item["id"], loaded["id"])
        self.assertEqual(item["slug"], "首钢园-秋日记录")
        self.assertEqual(item["status"], "draft")

    def test_slug_is_unique_per_target(self):
        first = repository.create_content(self.payload(), "owner")
        second = repository.create_content(self.payload(), "owner")
        note = repository.create_content(self.payload(target="notes"), "owner")
        self.assertEqual(first["slug"], "首钢园-秋日记录")
        self.assertEqual(second["slug"], "首钢园-秋日记录-2")
        self.assertEqual(note["slug"], "首钢园-秋日记录")

    def test_publish_rejects_missing_title_body_or_cover(self):
        for field, empty in (("title", ""), ("body", []), ("cover_media_id", "")):
            item = repository.create_content(self.payload(**{field: empty}), "owner")
            with self.subTest(field=field), self.assertRaises(ContentValidationError):
                repository.change_status(item["id"], "published", "owner")

    def test_update_creates_content_version_and_checks_revision(self):
        item = repository.create_content(self.payload(), "owner")
        updated = repository.update_content(
            item["id"], {"title": "修改后的标题"}, "owner", expected_version=1
        )
        self.assertEqual(updated["revision"], 2)
        versions = repository.list_versions(item["id"])
        self.assertEqual([row["revision"] for row in versions], [2, 1])
        with self.assertRaises(RevisionConflict):
            repository.update_content(item["id"], {"title": "过期修改"}, "owner", expected_version=1)

    def test_recycle_and_restore_preserve_relations(self):
        item = repository.create_content(self.payload(), "owner")
        repository.attach_category(item["id"], "city", name="城市")
        repository.attach_tags(item["id"], ["北京", "摄影"])
        repository.change_status(item["id"], "recycled", "owner")
        restored = repository.change_status(item["id"], "draft", "owner")
        self.assertEqual(restored["category"]["slug"], "city")
        self.assertEqual({tag["name"] for tag in restored["tags"]}, {"北京", "摄影"})


if __name__ == "__main__":
    unittest.main()
