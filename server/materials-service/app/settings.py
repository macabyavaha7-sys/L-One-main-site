from pathlib import Path
import os


STATE_ROOT = Path(os.environ.get("LONE_STATE_ROOT", "/var/lib/l-one-materials"))
PUBLIC_ROOT = Path(os.environ.get("LONE_PUBLIC_ROOT", "/www/l-one-static/materials"))
INCOMING_ROOT = STATE_ROOT / "incoming"
PROCESSING_ROOT = STATE_ROOT / "processing"
FAILED_ROOT = STATE_ROOT / "failed"
DATABASE_PATH = STATE_ROOT / "jobs.db"
ASSET_ROOT = PUBLIC_ROOT / "assets"
MANIFEST_PATH = PUBLIC_ROOT / "data" / "assets.json"
FFMPEG = os.environ.get("LONE_FFMPEG", "/usr/bin/ffmpeg")
FFPROBE = os.environ.get("LONE_FFPROBE", "/usr/bin/ffprobe")
ADMIN_TOKEN = os.environ.get("LONE_ADMIN_TOKEN", "")
MAX_UPLOAD_BYTES = int(os.environ.get("LONE_MAX_UPLOAD_BYTES", str(2 * 1024**3)))
MIN_FREE_BYTES = int(os.environ.get("LONE_MIN_FREE_BYTES", str(10 * 1024**3)))
ALLOWED_SUFFIXES = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi"}


def ensure_directories() -> None:
    for path in (
        STATE_ROOT,
        INCOMING_ROOT,
        PROCESSING_ROOT,
        FAILED_ROOT,
        ASSET_ROOT,
        MANIFEST_PATH.parent,
    ):
        path.mkdir(parents=True, exist_ok=True)
    if not MANIFEST_PATH.exists():
        MANIFEST_PATH.write_text("[]\n", encoding="utf-8")
