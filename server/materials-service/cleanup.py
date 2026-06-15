import shutil
import time
from pathlib import Path


ROOTS = [Path("/var/lib/l-one-materials/incoming"), Path("/var/lib/l-one-materials/processing")]
CUTOFF = time.time() - 24 * 60 * 60


for root in ROOTS:
    if not root.exists():
        continue
    for path in root.iterdir():
        if path.stat().st_mtime >= CUTOFF:
            continue
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)
