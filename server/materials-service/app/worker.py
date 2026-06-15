import time
from pathlib import Path

from .database import claim_next_job, initialize, update_job
from .pipeline import process
from .settings import ensure_directories


def main() -> None:
    ensure_directories()
    initialize()
    while True:
        job = claim_next_job()
        if job is None:
            time.sleep(2)
            continue
        source = Path(job["source_path"])
        try:
            process(job)
            source.unlink(missing_ok=True)
            update_job(job["id"], "completed")
        except Exception as error:
            update_job(job["id"], "failed", str(error)[-2000:])


if __name__ == "__main__":
    main()
