import sqlite3
from collections.abc import Callable


Migration = tuple[int, str, Callable[[sqlite3.Connection], None]]


def migrate_content_foundation(connection: sqlite3.Connection) -> None:
    statements = (
        """CREATE TABLE content_items (
            id TEXT PRIMARY KEY,
            target TEXT NOT NULL CHECK(target IN ('works', 'notes')),
            content_type TEXT NOT NULL CHECK(content_type IN ('article', 'gallery', 'video', 'external')),
            slug TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            excerpt TEXT NOT NULL DEFAULT '',
            body_json TEXT NOT NULL DEFAULT '[]',
            cover_media_id TEXT,
            original_url TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft', 'pending', 'published', 'offline', 'recycled')),
            publish_at TEXT,
            revision INTEGER NOT NULL DEFAULT 1,
            created_by TEXT NOT NULL,
            updated_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            recycled_at TEXT,
            UNIQUE(target, slug)
        )""",
        "CREATE INDEX content_items_public ON content_items(target, status, publish_at, updated_at)",
        """CREATE TABLE content_versions (
            id TEXT PRIMARY KEY,
            content_id TEXT NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
            revision INTEGER NOT NULL,
            snapshot_json TEXT NOT NULL,
            actor TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(content_id, revision)
        )""",
        """CREATE TABLE media_assets (
            id TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            mime_type TEXT NOT NULL,
            storage_path TEXT NOT NULL,
            public_url TEXT NOT NULL DEFAULT '',
            original_name TEXT NOT NULL DEFAULT '',
            size_bytes INTEGER NOT NULL DEFAULT 0,
            sha256 TEXT NOT NULL DEFAULT '',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        )""",
        """CREATE TABLE content_media (
            content_id TEXT NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
            media_id TEXT NOT NULL REFERENCES media_assets(id) ON DELETE RESTRICT,
            role TEXT NOT NULL DEFAULT 'body',
            position INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(content_id, media_id, role)
        )""",
        """CREATE TABLE categories (
            id TEXT PRIMARY KEY,
            target TEXT NOT NULL CHECK(target IN ('works', 'notes')),
            slug TEXT NOT NULL,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(target, slug)
        )""",
        """CREATE TABLE content_categories (
            content_id TEXT PRIMARY KEY REFERENCES content_items(id) ON DELETE CASCADE,
            category_id TEXT NOT NULL REFERENCES categories(id) ON DELETE RESTRICT
        )""",
        """CREATE TABLE tags (
            id TEXT PRIMARY KEY,
            target TEXT NOT NULL CHECK(target IN ('works', 'notes')),
            slug TEXT NOT NULL,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(target, slug)
        )""",
        """CREATE TABLE content_tags (
            content_id TEXT NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
            tag_id TEXT NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
            PRIMARY KEY(content_id, tag_id)
        )""",
        """CREATE TABLE import_jobs (
            id TEXT PRIMARY KEY,
            source_url TEXT NOT NULL,
            provider TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'queued',
            result_json TEXT NOT NULL DEFAULT '{}',
            error TEXT,
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE publication_jobs (
            id TEXT PRIMARY KEY,
            content_id TEXT NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
            action TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued',
            run_at TEXT NOT NULL,
            error TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""",
    )
    for statement in statements:
        connection.execute(statement)


MIGRATIONS: tuple[Migration, ...] = (
    (1, "content foundation", migrate_content_foundation),
)


def apply_all(connection: sqlite3.Connection) -> None:
    connection.execute("BEGIN IMMEDIATE")
    try:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        applied = {
            row[0]
            for row in connection.execute("SELECT version FROM schema_migrations").fetchall()
        }
        for version, name, migration in MIGRATIONS:
            if version in applied:
                continue
            migration(connection)
            connection.execute(
                "INSERT INTO schema_migrations(version, name) VALUES (?, ?)",
                (version, name),
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
