import json
import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from app import database, pipeline, settings


class CoreTests(unittest.TestCase):
    def make_directory(self) -> Path:
        path = Path("D:/L-One Center/test-temp/materials-service") / uuid.uuid4().hex
        path.mkdir(parents=True)
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def test_scale_filter_preserves_aspect_ratio(self):
        self.assertIn("min(1280,iw)", pipeline.scale_filter(1280))
        self.assertIn("fps=15", pipeline.scale_filter(640, 15))

    def test_database_round_trip(self):
        database_path = self.make_directory() / "jobs.db"
        with patch.object(database, "DATABASE_PATH", database_path):
            database.initialize()
            database.create_job("abc", "/tmp/a.mp4", "a.mp4", "A", "Test", ["one"])
            self.assertEqual(database.list_jobs()[0]["tags"], ["one"])
            self.assertEqual(database.claim_next_job()["status"], "processing")

    def test_manifest_contains_relative_paths(self):
        root = self.make_directory()
        asset_root = root / "assets"
        manifest = root / "data" / "assets.json"
        item = asset_root / "one"
        item.mkdir(parents=True)
        (item / "metadata.json").write_text(json.dumps({"id": "one", "video": "assets/one/video.mp4"}), encoding="utf-8")
        with patch.object(pipeline, "ASSET_ROOT", asset_root), patch.object(pipeline, "MANIFEST_PATH", manifest):
            pipeline.rebuild_manifest()
        data = json.loads(manifest.read_text(encoding="utf-8"))
        self.assertEqual(data[0]["video"], "assets/one/video.mp4")

    def test_list_assets_reads_manifest(self):
        root = self.make_directory()
        manifest = root / "data" / "assets.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(
            json.dumps([{"id": "a" * 32, "title": "测试素材"}], ensure_ascii=False),
            encoding="utf-8",
        )
        with patch.object(pipeline, "MANIFEST_PATH", manifest):
            self.assertEqual(pipeline.list_assets()[0]["title"], "测试素材")

    def test_admin_page_contains_management_panels(self):
        page = (Path(__file__).parents[1] / "app" / "admin.html").read_text(encoding="utf-8")
        self.assertIn('id="jobs-panel"', page)
        self.assertIn('id="assets-panel"', page)
        self.assertIn('id="upload-form"', page)


if __name__ == "__main__":
    unittest.main()
