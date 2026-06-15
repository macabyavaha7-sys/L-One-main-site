import time

from app.maintenance import backup_state, cleanup_old_paths
from app.pipeline import cleanup_recycle
from app.settings import (
    BACKUP_ROOT,
    DATABASE_PATH,
    INCOMING_ROOT,
    MANIFEST_PATH,
    PROCESSING_ROOT,
    RECYCLE_RETENTION_SECONDS,
    ensure_directories,
)


def main() -> None:
    ensure_directories()
    cutoff = time.time() - 24 * 60 * 60
    cleanup_old_paths(INCOMING_ROOT, cutoff)
    cleanup_old_paths(PROCESSING_ROOT, cutoff)
    cleanup_recycle(retention_seconds=RECYCLE_RETENTION_SECONDS)
    backup_state(DATABASE_PATH, MANIFEST_PATH, BACKUP_ROOT)
    cleanup_old_paths(BACKUP_ROOT, time.time() - 30 * 24 * 60 * 60)


if __name__ == "__main__":
    main()
