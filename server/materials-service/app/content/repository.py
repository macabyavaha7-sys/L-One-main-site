import json
import re
import uuid
from contextlib import closing
from datetime import datetime, timezone

from app import database

from .models import EDITABLE_FIELDS
from .validation import (
    ContentNotFound,
    ContentValidationError,
    RevisionConflict,
    validate_identity,
    validate_publishable,
    validate_status,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^\w\u3400-\u9fff]+", "-", value, flags=re.UNICODE)
    return value.strip("-") or "untitled"


def _unique_slug(connection, target: str, requested: str, exclude_id: str | None = None) -> str:
    base = slugify(requested)
    candidate = base
    index = 2
    while True:
        row = connection.execute(
            "SELECT id FROM content_items WHERE target = ? AND slug = ?",
            (target, candidate),
        ).fetchone()
        if row is None or row["id"] == exclude_id:
            return candidate
        candidate = f"{base}-{index}"
        index += 1


def _snapshot(row: dict) -> dict:
    return {
        key: row.get(key)
        for key in (
            "target", "content_type", "slug", "title", "excerpt", "body",
            "cover_media_id", "original_url", "status", "publish_at",
        )
    }


def _write_version(connection, item: dict, actor: str) -> None:
    connection.execute(
        """INSERT INTO content_versions(id, content_id, revision, snapshot_json, actor, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            uuid.uuid4().hex,
            item["id"],
            item["revision"],
            json.dumps(_snapshot(item), ensure_ascii=False, separators=(",", ":")),
            actor,
            utc_now(),
        ),
    )


def _row_to_item(connection, row) -> dict:
    item = dict(row)
    item["body"] = json.loads(item.pop("body_json"))
    category = connection.execute(
        """SELECT c.id, c.slug, c.name FROM categories c
           JOIN content_categories cc ON cc.category_id = c.id
           WHERE cc.content_id = ?""",
        (item["id"],),
    ).fetchone()
    item["category"] = dict(category) if category else None
    tags = connection.execute(
        """SELECT t.id, t.slug, t.name FROM tags t
           JOIN content_tags ct ON ct.tag_id = t.id
           WHERE ct.content_id = ? ORDER BY t.name""",
        (item["id"],),
    ).fetchall()
    item["tags"] = [dict(tag) for tag in tags]
    return item


def create_content(payload: dict, actor: str) -> dict:
    target = payload.get("target", "works")
    content_type = payload.get("content_type", "article")
    validate_identity(target, content_type)
    content_id = uuid.uuid4().hex
    now = utc_now()
    with closing(database.connect()) as connection:
        slug = _unique_slug(connection, target, payload.get("slug") or payload.get("title") or content_id)
        connection.execute(
            """INSERT INTO content_items(
                id, target, content_type, slug, title, excerpt, body_json,
                cover_media_id, original_url, status, publish_at, revision,
                created_by, updated_by, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', ?, 1, ?, ?, ?, ?)""",
            (
                content_id, target, content_type, slug,
                str(payload.get("title", "")).strip(),
                str(payload.get("excerpt", "")).strip(),
                json.dumps(payload.get("body", []), ensure_ascii=False),
                str(payload.get("cover_media_id", "")).strip() or None,
                str(payload.get("original_url", "")).strip(),
                payload.get("publish_at"), actor, actor, now, now,
            ),
        )
        row = connection.execute("SELECT * FROM content_items WHERE id = ?", (content_id,)).fetchone()
        item = _row_to_item(connection, row)
        _write_version(connection, item, actor)
        connection.commit()
        return item


def get_content(content_id: str) -> dict:
    with closing(database.connect()) as connection:
        row = connection.execute("SELECT * FROM content_items WHERE id = ?", (content_id,)).fetchone()
        if row is None:
            raise ContentNotFound("Content not found")
        return _row_to_item(connection, row)


def list_content(filters: dict | None = None) -> list[dict]:
    filters = filters or {}
    clauses = []
    values = []
    for field in ("target", "content_type", "status"):
        if filters.get(field):
            clauses.append(f"{field} = ?")
            values.append(filters[field])
    if filters.get("query"):
        clauses.append("(title LIKE ? OR excerpt LIKE ?)")
        value = f"%{filters['query']}%"
        values.extend((value, value))
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with closing(database.connect()) as connection:
        rows = connection.execute(
            f"SELECT * FROM content_items {where} ORDER BY updated_at DESC", values
        ).fetchall()
        return [_row_to_item(connection, row) for row in rows]


def update_content(content_id: str, payload: dict, actor: str, expected_version: int) -> dict:
    with closing(database.connect()) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute("SELECT * FROM content_items WHERE id = ?", (content_id,)).fetchone()
        if row is None:
            raise ContentNotFound("Content not found")
        current = _row_to_item(connection, row)
        if current["revision"] != expected_version:
            raise RevisionConflict("Content was changed by another request")
        merged = dict(current)
        merged.update({key: value for key, value in payload.items() if key in EDITABLE_FIELDS})
        validate_identity(merged["target"], merged["content_type"])
        slug_source = merged.get("slug") or merged.get("title") or content_id
        merged["slug"] = _unique_slug(connection, merged["target"], slug_source, content_id)
        revision = current["revision"] + 1
        now = utc_now()
        connection.execute(
            """UPDATE content_items SET target=?, content_type=?, slug=?, title=?, excerpt=?,
               body_json=?, cover_media_id=?, original_url=?, publish_at=?, revision=?,
               updated_by=?, updated_at=? WHERE id=? AND revision=?""",
            (
                merged["target"], merged["content_type"], merged["slug"],
                str(merged.get("title", "")).strip(), str(merged.get("excerpt", "")).strip(),
                json.dumps(merged.get("body", []), ensure_ascii=False),
                str(merged.get("cover_media_id") or "").strip() or None,
                str(merged.get("original_url", "")).strip(), merged.get("publish_at"),
                revision, actor, now, content_id, expected_version,
            ),
        )
        updated = _row_to_item(
            connection,
            connection.execute("SELECT * FROM content_items WHERE id = ?", (content_id,)).fetchone(),
        )
        _write_version(connection, updated, actor)
        connection.commit()
        return updated


def change_status(content_id: str, status: str, actor: str, publish_at: str | None = None) -> dict:
    validate_status(status)
    with closing(database.connect()) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute("SELECT * FROM content_items WHERE id = ?", (content_id,)).fetchone()
        if row is None:
            raise ContentNotFound("Content not found")
        item = _row_to_item(connection, row)
        if status == "published":
            validate_publishable(item)
        revision = item["revision"] + 1
        recycled_at = utc_now() if status == "recycled" else None
        effective_publish_at = publish_at if publish_at is not None else item.get("publish_at")
        connection.execute(
            """UPDATE content_items SET status=?, publish_at=?, revision=?, updated_by=?,
               updated_at=?, recycled_at=? WHERE id=?""",
            (status, effective_publish_at, revision, actor, utc_now(), recycled_at, content_id),
        )
        updated = _row_to_item(connection, connection.execute("SELECT * FROM content_items WHERE id=?", (content_id,)).fetchone())
        _write_version(connection, updated, actor)
        connection.commit()
        return updated


def list_versions(content_id: str) -> list[dict]:
    with closing(database.connect()) as connection:
        rows = connection.execute(
            "SELECT * FROM content_versions WHERE content_id=? ORDER BY revision DESC", (content_id,)
        ).fetchall()
    result = []
    for row in rows:
        value = dict(row)
        value["snapshot"] = json.loads(value.pop("snapshot_json"))
        result.append(value)
    return result


def restore_version(content_id: str, version_id: str, actor: str) -> dict:
    with closing(database.connect()) as connection:
        row = connection.execute(
            "SELECT snapshot_json FROM content_versions WHERE id=? AND content_id=?",
            (version_id, content_id),
        ).fetchone()
    if row is None:
        raise ContentNotFound("Version not found")
    current = get_content(content_id)
    snapshot = json.loads(row["snapshot_json"])
    status = snapshot.pop("status", current["status"])
    updated = update_content(content_id, snapshot, actor, current["revision"])
    if status != updated["status"]:
        updated = change_status(content_id, status, actor, snapshot.get("publish_at"))
    return updated


def attach_category(content_id: str, category_slug: str, name: str | None = None) -> dict:
    item = get_content(content_id)
    slug = slugify(category_slug)
    with closing(database.connect()) as connection:
        row = connection.execute(
            "SELECT id FROM categories WHERE target=? AND slug=?", (item["target"], slug)
        ).fetchone()
        category_id = row["id"] if row else uuid.uuid4().hex
        if row is None:
            connection.execute(
                "INSERT INTO categories(id,target,slug,name,created_at) VALUES(?,?,?,?,?)",
                (category_id, item["target"], slug, name or category_slug, utc_now()),
            )
        connection.execute(
            "INSERT OR REPLACE INTO content_categories(content_id,category_id) VALUES(?,?)",
            (content_id, category_id),
        )
        connection.commit()
    return get_content(content_id)


def attach_tags(content_id: str, tag_names: list[str]) -> dict:
    item = get_content(content_id)
    with closing(database.connect()) as connection:
        connection.execute("DELETE FROM content_tags WHERE content_id=?", (content_id,))
        for name in dict.fromkeys(value.strip() for value in tag_names if value.strip()):
            slug = slugify(name)
            row = connection.execute(
                "SELECT id FROM tags WHERE target=? AND slug=?", (item["target"], slug)
            ).fetchone()
            tag_id = row["id"] if row else uuid.uuid4().hex
            if row is None:
                connection.execute(
                    "INSERT INTO tags(id,target,slug,name,created_at) VALUES(?,?,?,?,?)",
                    (tag_id, item["target"], slug, name, utc_now()),
                )
            connection.execute(
                "INSERT INTO content_tags(content_id,tag_id) VALUES(?,?)", (content_id, tag_id)
            )
        connection.commit()
    return get_content(content_id)
