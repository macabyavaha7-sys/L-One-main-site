import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from .settings import ASSET_ROOT, FFMPEG, FFPROBE, MANIFEST_PATH, PROCESSING_ROOT, RECYCLE_ROOT


def run(command: list[str]) -> None:
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)


def probe(path: Path) -> dict:
    result = subprocess.run(
        [FFPROBE, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    video = next(stream for stream in data["streams"] if stream.get("codec_type") == "video")
    audio = next((stream for stream in data["streams"] if stream.get("codec_type") == "audio"), None)
    duration = float(data.get("format", {}).get("duration") or video.get("duration") or 0)
    return {
        "duration": duration,
        "width": int(video["width"]),
        "height": int(video["height"]),
        "has_audio": audio is not None,
    }


def scale_filter(max_edge: int, fps: int | None = None) -> str:
    value = f"scale='if(gte(iw,ih),min({max_edge},iw),-2)':'if(gte(iw,ih),-2,min({max_edge},ih))'"
    return f"{value},fps={fps}" if fps else value


def process(job: dict) -> dict:
    source = Path(job["source_path"])
    working = PROCESSING_ROOT / job["id"]
    asset_id = job.get("replace_asset_id") or job["id"]
    final = ASSET_ROOT / asset_id
    shutil.rmtree(working, ignore_errors=True)
    working.mkdir(parents=True)
    info = probe(source)
    seek = 1 if info["duration"] > 1 else 0
    preview_length = min(4, max(0.1, info["duration"] - seek))

    video = working / "video.mp4"
    thumbnail = working / "thumbnail.webp"
    preview = working / "preview.webm"

    video_command = [
        FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(source),
        "-map_metadata", "-1", "-vf", scale_filter(1280), "-c:v", "libx264",
        "-preset", "medium", "-crf", "24", "-maxrate", "2M", "-bufsize", "4M",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
    ]
    video_command += ["-c:a", "aac", "-b:a", "96k"] if info["has_audio"] else ["-an"]
    run(video_command + [str(video)])
    run([
        FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-ss", str(seek), "-i", str(source),
        "-vf", scale_filter(640), "-frames:v", "1", "-c:v", "libwebp", "-quality", "72", str(thumbnail),
    ])
    run([
        FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-ss", str(seek), "-t", str(preview_length),
        "-i", str(source), "-vf", scale_filter(640, 15), "-an", "-c:v", "libvpx-vp9",
        "-b:v", "0", "-crf", "42", "-deadline", "good", "-row-mt", "1", str(preview),
    ])

    published = probe(video)
    preview_info = probe(preview)
    if max(published["width"], published["height"]) > 1280:
        raise RuntimeError("published video exceeds 1280 pixels")
    if max(preview_info["width"], preview_info["height"]) > 640:
        raise RuntimeError("preview exceeds 640 pixels")

    asset = {
        "id": asset_id,
        "title": job["title"],
        "category": job["category"],
        "tags": job["tags"],
        "fileName": job["original_name"],
        "folderPath": job["category"],
        "relativePath": job["original_name"],
        "fileTypes": ["MP4", "WebM", "WebP"],
        "duration": round(info["duration"], 3),
        "width": published["width"],
        "height": published["height"],
        "video": f"assets/{asset_id}/video.mp4",
        "previewVideo": f"assets/{asset_id}/preview.webm",
        "thumbnail": f"assets/{asset_id}/thumbnail.webp",
    }
    (working / "metadata.json").write_text(json.dumps(asset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    publish_directory(working, asset_id)
    rebuild_manifest()
    return asset


def rebuild_manifest() -> None:
    assets = []
    for metadata in sorted(ASSET_ROOT.glob("*/metadata.json")):
        try:
            assets.append(json.loads(metadata.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = MANIFEST_PATH.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(assets, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, MANIFEST_PATH)


def list_assets() -> list[dict]:
    try:
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def recycle_name(asset_id: str, now: int | None = None) -> str:
    return f"{asset_id}-{int(time.time() if now is None else now)}"


def publish_directory(working: Path, asset_id: str, now: int | None = None) -> Path:
    final = ASSET_ROOT / asset_id
    RECYCLE_ROOT.mkdir(parents=True, exist_ok=True)
    if final.exists():
        os.replace(final, RECYCLE_ROOT / recycle_name(asset_id, now))
    os.replace(working, final)
    return final


def soft_delete_asset(asset_id: str, now: int | None = None) -> bool:
    if not re.fullmatch(r"[0-9a-f]{32}", asset_id):
        return False
    target = ASSET_ROOT / asset_id
    if not target.is_dir():
        return False
    RECYCLE_ROOT.mkdir(parents=True, exist_ok=True)
    os.replace(target, RECYCLE_ROOT / recycle_name(asset_id, now))
    rebuild_manifest()
    return True


def delete_asset(asset_id: str) -> bool:
    return soft_delete_asset(asset_id)


def cleanup_recycle(root: Path = RECYCLE_ROOT, retention_seconds: int = 604800, now: int | None = None) -> int:
    if not root.exists():
        return 0
    current = time.time() if now is None else now
    removed = 0
    for path in root.iterdir():
        if path.stat().st_mtime + retention_seconds >= current:
            continue
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)
        removed += 1
    return removed
