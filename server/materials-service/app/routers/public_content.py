import hashlib
import json

from fastapi import APIRouter, Header, HTTPException, Response
from fastapi.responses import JSONResponse

from app.content import repository
from app.content.validation import ContentNotFound


router = APIRouter(prefix="/api/public/v1", tags=["public-content"])
INTERNAL_FIELDS = {"created_by", "updated_by", "recycled_at"}


def _public_item(item: dict) -> dict:
    return {key: value for key, value in item.items() if key not in INTERNAL_FIELDS}


def _cached(data, if_none_match: str | None):
    body = json.dumps({"data": data}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    etag = f'"{hashlib.sha256(body).hexdigest()}"'
    if if_none_match == etag:
        return Response(status_code=304, headers={"ETag": etag, "Cache-Control": "public, max-age=60"})
    return JSONResponse(
        {"data": data},
        headers={"ETag": etag, "Cache-Control": "public, max-age=60, stale-while-revalidate=300"},
    )


@router.get("/content")
def content_list(
    target: str | None = None,
    type: str | None = None,
    if_none_match: str | None = Header(default=None),
):
    items = [_public_item(item) for item in repository.list_public_content(target, type)]
    return _cached(items, if_none_match)


@router.get("/content/{target}/{slug}")
def content_detail(target: str, slug: str, if_none_match: str | None = Header(default=None)):
    try:
        item = _public_item(repository.get_public_content(target, slug))
    except ContentNotFound as error:
        raise HTTPException(status_code=404, detail=str(error))
    return _cached(item, if_none_match)


@router.get("/categories")
def categories(target: str = "works", if_none_match: str | None = Header(default=None)):
    return _cached(repository.list_public_taxonomy("categories", target), if_none_match)


@router.get("/tags")
def tags(target: str = "works", if_none_match: str | None = Header(default=None)):
    return _cached(repository.list_public_taxonomy("tags", target), if_none_match)
