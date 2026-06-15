import shutil
from datetime import datetime, timezone
from pathlib import Path


def backup_state(database_path: Path, manifest_path: Path, backup_root: Path, stamp: str | None = None) -> Path:
    name = stamp or datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    target = backup_root / name
    target.mkdir(parents=True, exist_ok=False)
    if database_path.exists():
        shutil.copy2(database_path, target / database_path.name)
    if manifest_path.exists():
        shutil.copy2(manifest_path, target / manifest_path.name)
    return target


def cleanup_old_paths(root: Path, cutoff: float) -> int:
    if not root.exists():
        return 0
    removed = 0
    for path in root.iterdir():
        if path.stat().st_mtime >= cutoff:
            continue
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)
        removed += 1
    return removed
