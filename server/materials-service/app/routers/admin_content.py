from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app.content.blocks import BlockValidationError, normalize_blocks
from app.content import repository
from app.content.validation import ContentNotFound, ContentValidationError, RevisionConflict
from app.database import record_audit


router = APIRouter(prefix="/api/admin/v1", tags=["admin-content"])


class ContentCreate(BaseModel):
    target: str = "works"
    content_type: str = "article"
    slug: str | None = None
    title: str = ""
    excerpt: str = ""
    body: list[dict[str, Any]] = Field(default_factory=list)
    cover_media_id: str | None = None
    original_url: str = ""
    publish_at: str | None = None
    category: str | None = None
    tags: list[str] = Field(default_factory=list)


class ContentUpdate(BaseModel):
    revision: int
    target: str | None = None
    content_type: str | None = None
    slug: str | None = None
    title: str | None = None
    excerpt: str | None = None
    body: list[dict[str, Any]] | None = None
    cover_media_id: str | None = None
    original_url: str | None = None
    publish_at: str | None = None
    category: str | None = None
    tags: list[str] | None = None


class StatusUpdate(BaseModel):
    status: str
    publish_at: str | None = None


class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str


def _authorize(request: Request, token: str | None, csrf: str | None = None, mutation: bool = False) -> dict:
    return request.app.state.authorize(request, token, csrf, mutation)


def _raise_content_error(error: Exception) -> None:
    if isinstance(error, ContentNotFound):
        raise HTTPException(status_code=404, detail=str(error))
    if isinstance(error, RevisionConflict):
        raise HTTPException(status_code=409, detail=str(error))
    raise HTTPException(status_code=422, detail=str(error))


def _prepare(payload: dict) -> dict:
    if "body" in payload and payload["body"] is not None:
        payload["body"] = normalize_blocks(payload["body"])
    return payload


def _relations(item: dict, category: str | None, tags: list[str] | None) -> dict:
    if category is not None:
        item = repository.attach_category(item["id"], category)
    if tags is not None:
        item = repository.attach_tags(item["id"], tags)
    return item


@router.get("/content")
def content_list(
    request: Request,
    target: str | None = None,
    type: str | None = None,
    status: str | None = None,
    query: str | None = None,
    x_l_one_admin_token: str | None = Header(default=None),
) -> dict:
    _authorize(request, x_l_one_admin_token)
    return {"data": repository.list_content({"target": target, "content_type": type, "status": status, "query": query})}


@router.post("/content", status_code=201)
def content_create(
    payload: ContentCreate,
    request: Request,
    x_csrf_token: str | None = Header(default=None),
    x_l_one_admin_token: str | None = Header(default=None),
) -> dict:
    session = _authorize(request, x_l_one_admin_token, x_csrf_token, True)
    values = payload.model_dump()
    category, tags = values.pop("category"), values.pop("tags")
    try:
        item = repository.create_content(_prepare(values), session["username"])
        item = _relations(item, category, tags)
    except (ContentValidationError, BlockValidationError) as error:
        _raise_content_error(error)
    record_audit(session["username"], "content.create", item["id"], "ok")
    return {"data": item}


@router.get("/content/{content_id}")
def content_detail(
    content_id: str,
    request: Request,
    x_l_one_admin_token: str | None = Header(default=None),
) -> dict:
    _authorize(request, x_l_one_admin_token)
    try:
        return {"data": repository.get_content(content_id)}
    except ContentValidationError as error:
        _raise_content_error(error)


@router.patch("/content/{content_id}")
def content_update(
    content_id: str,
    payload: ContentUpdate,
    request: Request,
    x_csrf_token: str | None = Header(default=None),
    x_l_one_admin_token: str | None = Header(default=None),
) -> dict:
    session = _authorize(request, x_l_one_admin_token, x_csrf_token, True)
    values = payload.model_dump(exclude_unset=True)
    revision = values.pop("revision")
    category = values.pop("category", None)
    tags = values.pop("tags", None)
    try:
        item = repository.update_content(content_id, _prepare(values), session["username"], revision)
        item = _relations(item, category, tags)
    except (ContentValidationError, BlockValidationError) as error:
        _raise_content_error(error)
    record_audit(session["username"], "content.update", content_id, "ok")
    return {"data": item}


@router.post("/content/{content_id}/status")
def content_status(
    content_id: str,
    payload: StatusUpdate,
    request: Request,
    x_csrf_token: str | None = Header(default=None),
    x_l_one_admin_token: str | None = Header(default=None),
) -> dict:
    session = _authorize(request, x_l_one_admin_token, x_csrf_token, True)
    try:
        item = repository.change_status(content_id, payload.status, session["username"], payload.publish_at)
    except ContentValidationError as error:
        _raise_content_error(error)
    record_audit(session["username"], "content.status", content_id, payload.status)
    return {"data": item}


@router.get("/content/{content_id}/versions")
def content_versions(
    content_id: str,
    request: Request,
    x_l_one_admin_token: str | None = Header(default=None),
) -> dict:
    _authorize(request, x_l_one_admin_token)
    return {"data": repository.list_versions(content_id)}


@router.post("/content/{content_id}/versions/{version_id}/restore")
def content_restore(
    content_id: str,
    version_id: str,
    request: Request,
    x_csrf_token: str | None = Header(default=None),
    x_l_one_admin_token: str | None = Header(default=None),
) -> dict:
    session = _authorize(request, x_l_one_admin_token, x_csrf_token, True)
    try:
        item = repository.restore_version(content_id, version_id, session["username"])
    except ContentValidationError as error:
        _raise_content_error(error)
    record_audit(session["username"], "content.restore", content_id, version_id)
    return {"data": item}


@router.post("/account/password")
def password_update(
    payload: PasswordUpdate,
    request: Request,
    x_csrf_token: str | None = Header(default=None),
    x_l_one_admin_token: str | None = Header(default=None),
) -> dict:
    session = _authorize(request, x_l_one_admin_token, x_csrf_token, True)
    if len(payload.new_password) < 12:
        raise HTTPException(status_code=422, detail="New password must contain at least 12 characters")
    request.app.state.change_password(payload.current_password, payload.new_password)
    record_audit(session["username"], "account.password", session["username"], "changed")
    return {"data": {"changed": True}}
