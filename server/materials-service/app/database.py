import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone

from .settings import DATABASE_PATH


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    return connection


def initialize() -> None:
    with closing(connect()) as connection:
        connection.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                source_path TEXT NOT NULL,
                original_name TEXT NOT NULL,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                tags_json TEXT NOT NULL,
                replace_asset_id TEXT,
                error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS jobs_status_created
                ON jobs(status, created_at);
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                action TEXT NOT NULL,
                target TEXT NOT NULL,
                result TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(jobs)").fetchall()}
        if "replace_asset_id" not in columns:
            connection.execute("ALTER TABLE jobs ADD COLUMN replace_asset_id TEXT")
        connection.commit()


def create_job(
    job_id: str,
    source_path: str,
    original_name: str,
    title: str,
    category: str,
    tags: list[str],
    replace_asset_id: str | None = None,
) -> None:
    now = utc_now()
    with closing(connect()) as connection:
        connection.execute(
            """
            INSERT INTO jobs(
                id, status, source_path, original_name, title, category, tags_json,
                replace_asset_id, created_at, updated_at
            ) VALUES (?, 'queued', ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id, source_path, original_name, title, category,
                json.dumps(tags, ensure_ascii=False), replace_asset_id, now, now,
            ),
        )
        connection.commit()


def list_jobs(limit: int = 100) -> list[dict]:
    with closing(connect()) as connection:
        rows = connection.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [serialize(row) for row in rows]


def claim_next_job() -> dict | None:
    with closing(connect()) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT * FROM jobs WHERE status = 'queued' ORDER BY created_at LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        now = utc_now()
        connection.execute(
            "UPDATE jobs SET status = 'processing', updated_at = ? WHERE id = ?",
            (now, row["id"]),
        )
        connection.commit()
        data = serialize(row)
        data["status"] = "processing"
        data["updated_at"] = now
        return data


def update_job(job_id: str, status: str, error: str | None = None) -> None:
    with closing(connect()) as connection:
        connection.execute(
            "UPDATE jobs SET status = ?, error = ?, updated_at = ? WHERE id = ?",
            (status, error, utc_now(), job_id),
        )
        connection.commit()


def retry_job(job_id: str) -> bool:
    with closing(connect()) as connection:
        result = connection.execute(
            """
            UPDATE jobs SET status = 'queued', error = NULL, updated_at = ?
            WHERE id = ? AND status = 'failed'
            """,
            (utc_now(), job_id),
        )
        connection.commit()
        return result.rowcount == 1


def serialize(row: sqlite3.Row) -> dict:
    result = dict(row)
    result["tags"] = json.loads(result.pop("tags_json"))
    return result


def record_audit(username: str, action: str, target: str, result: str) -> None:
    with closing(connect()) as connection:
        connection.execute(
            "INSERT INTO audit_log(username, action, target, result, created_at) VALUES (?, ?, ?, ?, ?)",
            (username, action, target, result, utc_now()),
        )
        connection.commit()


def list_audit(limit: int = 100) -> list[dict]:
    with closing(connect()) as connection:
        rows = connection.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(row) for row in rows]
