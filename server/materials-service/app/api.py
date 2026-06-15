import hashlib
import hmac
import json
import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import HTMLResponse

from .database import create_job, initialize, list_jobs, retry_job
from .pipeline import delete_asset, list_assets
from .settings import (
    ADMIN_TOKEN,
    ALLOWED_SUFFIXES,
    INCOMING_ROOT,
    MAX_UPLOAD_BYTES,
    MIN_FREE_BYTES,
    STATE_ROOT,
    ensure_directories,
)


app = FastAPI(title="L-One Materials Service", docs_url=None, redoc_url=None)
ADMIN_PAGE = Path(__file__).with_name("admin.html")


@app.on_event("startup")
def startup() -> None:
    ensure_directories()
    initialize()


def authorize(token: str | None) -> None:
    if not ADMIN_TOKEN or not token or not hmac.compare_digest(token, ADMIN_TOKEN):
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/api/health")
def health() -> dict:
    usage = shutil.disk_usage(STATE_ROOT)
    return {"status": "ok", "freeBytes": usage.free, "workerQueue": len([j for j in list_jobs() if j["status"] == "queued"])}


@app.get("/api/admin/jobs")
def jobs(x_l_one_admin_token: str | None = Header(default=None)) -> list[dict]:
    authorize(x_l_one_admin_token)
    return list_jobs()


@app.get("/api/admin/assets")
def assets(x_l_one_admin_token: str | None = Header(default=None)) -> list[dict]:
    authorize(x_l_one_admin_token)
    return list_assets()


@app.post("/api/admin/assets", status_code=202)
async def upload_asset(
    file: UploadFile = File(...),
    title: str = Form(...),
    category: str = Form("未分类"),
    tags: str = Form(""),
    x_l_one_admin_token: str | None = Header(default=None),
) -> dict:
    authorize(x_l_one_admin_token)
    original = Path(file.filename or "upload.mp4").name
    suffix = Path(original).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=415, detail="Unsupported video type")
    if shutil.disk_usage(STATE_ROOT).free < MIN_FREE_BYTES:
        raise HTTPException(status_code=507, detail="Insufficient disk space")
    job_id = uuid.uuid4().hex
    target = INCOMING_ROOT / f"{job_id}{suffix}"
    digest = hashlib.sha256()
    size = 0
    try:
        with target.open("xb") as output:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="Upload exceeds size limit")
                digest.update(chunk)
                output.write(chunk)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    clean_tags = [value.strip() for value in tags.split(",") if value.strip()]
    create_job(job_id, str(target), original, title.strip() or Path(original).stem, category.strip() or "未分类", clean_tags)
    return {"id": job_id, "status": "queued", "sizeBytes": size, "sha256": digest.hexdigest()}


@app.post("/api/admin/jobs/{job_id}/retry")
def retry(job_id: str, x_l_one_admin_token: str | None = Header(default=None)) -> dict:
    authorize(x_l_one_admin_token)
    if not retry_job(job_id):
        raise HTTPException(status_code=409, detail="Job is not retryable")
    return {"id": job_id, "status": "queued"}


@app.delete("/api/admin/assets/{asset_id}")
def remove(asset_id: str, x_l_one_admin_token: str | None = Header(default=None)) -> dict:
    authorize(x_l_one_admin_token)
    if not delete_asset(asset_id):
        raise HTTPException(status_code=404, detail="Asset not found")
    return {"id": asset_id, "deleted": True}


@app.get("/admin/", response_class=HTMLResponse)
def admin_page() -> str:
    return ADMIN_PAGE.read_text(encoding="utf-8")
