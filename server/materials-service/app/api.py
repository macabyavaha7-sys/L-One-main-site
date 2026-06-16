import hashlib
import hmac
import json
import os
import secrets
import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, Header, HTTPException, Request, Response, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from .database import create_job, initialize, list_audit, list_jobs, record_audit, retry_job
from .pipeline import list_assets, soft_delete_asset
from .security import LoginLimiter, create_session, hash_password, read_session, valid_csrf, verify_password
from .settings import (
    ADMIN_PASSWORD_HASH,
    ADMIN_CREDENTIALS_PATH,
    ADMIN_TOKEN,
    ADMIN_USERNAME,
    ALLOWED_SUFFIXES,
    INCOMING_ROOT,
    MAX_UPLOAD_BYTES,
    MIN_FREE_BYTES,
    SESSION_SECRET,
    SESSION_TTL_SECONDS,
    SESSION_COOKIE_SECURE,
    STATE_ROOT,
    ensure_directories,
)


app = FastAPI(title="L-One Materials Service", docs_url=None, redoc_url=None)
ADMIN_PAGE = Path(__file__).with_name("admin.html")
SESSION_COOKIE = "lone_admin_session"
login_limiter = LoginLimiter(max_attempts=5, window_seconds=900)


class LoginRequest(BaseModel):
    username: str
    password: str


def current_credentials() -> tuple[str, str]:
    if ADMIN_CREDENTIALS_PATH.exists():
        try:
            stored = json.loads(ADMIN_CREDENTIALS_PATH.read_text(encoding="utf-8"))
            return stored.get("password_hash", ""), stored.get("session_secret", "")
        except (OSError, json.JSONDecodeError):
            pass
    return ADMIN_PASSWORD_HASH, SESSION_SECRET


def change_admin_password(current_password: str, new_password: str) -> None:
    password_hash, _ = current_credentials()
    if not verify_password(current_password, password_hash):
        raise HTTPException(status_code=403, detail="Current password is invalid")
    ADMIN_CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = ADMIN_CREDENTIALS_PATH.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(
            {"password_hash": hash_password(new_password), "session_secret": secrets.token_urlsafe(48)},
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    temporary.replace(ADMIN_CREDENTIALS_PATH)
    try:
        os.chmod(ADMIN_CREDENTIALS_PATH, 0o600)
    except OSError:
        pass


@app.on_event("startup")
def startup() -> None:
    ensure_directories()
    initialize()


def authorize(
    request: Request,
    token: str | None = None,
    csrf_token: str | None = None,
    mutation: bool = False,
) -> dict:
    if ADMIN_TOKEN and token and hmac.compare_digest(token, ADMIN_TOKEN):
        return {"username": "deploy-token", "tokenAuth": True}
    _, session_secret = current_credentials()
    if not session_secret:
        raise HTTPException(status_code=503, detail="Admin session is not configured")
    session = read_session(request.cookies.get(SESSION_COOKIE, ""), session_secret)
    if session is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if mutation and not valid_csrf(session, csrf_token or ""):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")
    return session


@app.post("/api/admin/login")
def login(payload: LoginRequest, request: Request) -> JSONResponse:
    client_key = request.client.host if request.client else "unknown"
    if not login_limiter.allowed(client_key):
        raise HTTPException(status_code=429, detail="Too many login attempts")
    password_hash, session_secret = current_credentials()
    if not password_hash or not session_secret:
        raise HTTPException(status_code=503, detail="Admin login is not configured")
    if payload.username != ADMIN_USERNAME or not verify_password(payload.password, password_hash):
        login_limiter.record_failure(client_key)
        record_audit(payload.username[:80] or "unknown", "login", client_key, "failed")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    login_limiter.clear(client_key)
    session_token, csrf_token = create_session(ADMIN_USERNAME, session_secret, SESSION_TTL_SECONDS)
    response = JSONResponse({"username": ADMIN_USERNAME, "csrfToken": csrf_token})
    response.set_cookie(
        SESSION_COOKIE,
        session_token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite="strict",
        path="/",
    )
    record_audit(ADMIN_USERNAME, "login", client_key, "ok")
    return response


@app.post("/api/admin/logout")
def logout(
    request: Request,
    x_csrf_token: str | None = Header(default=None),
    x_l_one_admin_token: str | None = Header(default=None),
) -> Response:
    session = authorize(request, x_l_one_admin_token, x_csrf_token, mutation=True)
    response = JSONResponse({"loggedOut": True})
    response.delete_cookie(SESSION_COOKIE, path="/")
    record_audit(session["username"], "logout", "session", "ok")
    return response


@app.get("/api/admin/session")
def session_info(request: Request, x_l_one_admin_token: str | None = Header(default=None)) -> dict:
    session = authorize(request, x_l_one_admin_token)
    return {"username": session["username"], "csrfToken": session.get("csrf", "")}


@app.get("/api/health")
def health() -> dict:
    usage = shutil.disk_usage(STATE_ROOT)
    return {
        "status": "ok",
        "freeBytes": usage.free,
        "workerQueue": len([job for job in list_jobs() if job["status"] == "queued"]),
    }


@app.get("/api/admin/jobs")
def jobs(request: Request, x_l_one_admin_token: str | None = Header(default=None)) -> list[dict]:
    authorize(request, x_l_one_admin_token)
    return list_jobs()


@app.get("/api/admin/assets")
def assets(request: Request, x_l_one_admin_token: str | None = Header(default=None)) -> list[dict]:
    authorize(request, x_l_one_admin_token)
    return list_assets()


@app.get("/api/admin/status")
def admin_status(request: Request, x_l_one_admin_token: str | None = Header(default=None)) -> dict:
    authorize(request, x_l_one_admin_token)
    usage = shutil.disk_usage(STATE_ROOT)
    return {
        "disk": {"totalBytes": usage.total, "usedBytes": usage.used, "freeBytes": usage.free},
        "queue": {"queued": len([job for job in list_jobs() if job["status"] == "queued"])},
        "audit": list_audit(50),
    }


@app.post("/api/admin/assets", status_code=202)
async def upload_asset(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(...),
    category: str = Form("未分类"),
    tags: str = Form(""),
    replace_asset_id: str = Form(""),
    x_csrf_token: str | None = Header(default=None),
    x_l_one_admin_token: str | None = Header(default=None),
) -> dict:
    session = authorize(request, x_l_one_admin_token, x_csrf_token, mutation=True)
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
    replacement = replace_asset_id.strip() or None
    if replacement and not any(asset.get("id") == replacement for asset in list_assets()):
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=404, detail="Replacement asset not found")
    clean_tags = [value.strip() for value in tags.split(",") if value.strip()]
    create_job(
        job_id,
        str(target),
        original,
        title.strip() or Path(original).stem,
        category.strip() or "未分类",
        clean_tags,
        replacement,
    )
    record_audit(session["username"], "replace" if replacement else "upload", replacement or job_id, "queued")
    return {"id": job_id, "status": "queued", "sizeBytes": size, "sha256": digest.hexdigest()}


@app.post("/api/admin/jobs/{job_id}/retry")
def retry(
    job_id: str,
    request: Request,
    x_csrf_token: str | None = Header(default=None),
    x_l_one_admin_token: str | None = Header(default=None),
) -> dict:
    session = authorize(request, x_l_one_admin_token, x_csrf_token, mutation=True)
    if not retry_job(job_id):
        raise HTTPException(status_code=409, detail="Job is not retryable")
    record_audit(session["username"], "retry", job_id, "queued")
    return {"id": job_id, "status": "queued"}


@app.delete("/api/admin/assets/{asset_id}")
def remove(
    asset_id: str,
    request: Request,
    x_csrf_token: str | None = Header(default=None),
    x_l_one_admin_token: str | None = Header(default=None),
) -> dict:
    session = authorize(request, x_l_one_admin_token, x_csrf_token, mutation=True)
    if not soft_delete_asset(asset_id):
        raise HTTPException(status_code=404, detail="Asset not found")
    record_audit(session["username"], "delete", asset_id, "recycled")
    return {"id": asset_id, "deleted": True}


@app.get("/admin/", response_class=HTMLResponse)
def admin_page() -> str:
    return ADMIN_PAGE.read_text(encoding="utf-8")


app.state.authorize = authorize
app.state.change_password = change_admin_password

from .routers.admin_content import router as admin_content_router
from .routers.admin_taxonomy import router as admin_taxonomy_router
from .routers.public_content import router as public_content_router

app.include_router(admin_content_router)
app.include_router(admin_taxonomy_router)
app.include_router(public_content_router)
