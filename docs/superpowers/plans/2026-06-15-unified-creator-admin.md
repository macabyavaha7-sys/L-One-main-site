# Unified Creator Admin Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在现有轻量服务器内容服务上建立统一创作后台，支持 Works、Notes、Materials 的新增、校对、预览、发布、下线、回收与审计，并让主站通过稳定公开 API 读取新增内容。

**Architecture:** 保留现有 FastAPI、SQLite、Nginx、systemd、FFmpeg 技术栈。新增结构化内容域、版本记录、媒体关系、导入任务和发布任务；后台采用服务器托管的原生 HTML/CSS/JavaScript 单页界面；主站保留现有 14 条 Works 与现有视觉，仅增加公开 API 适配层和内容渲染器。媒体与数据库均归档至轻量服务器，GitHub 继续负责主站前端代码部署。

**Tech Stack:** Python 3.12, FastAPI, SQLite WAL, unittest, HTML/CSS/JavaScript, Nginx, systemd, FFmpeg, EdgeOne Pages.

---

## Delivery Rules

- 每个任务先写失败测试，再做最小实现，再运行相关测试。
- 每个任务独立提交，禁止顺带修改已交付页面、现有 14 条 Works、Motion Library 64 个效果及 Materials 转码规则。
- 所有服务器持久数据写入 `/var/lib/l-one-content` 或 `/www/l-one-static`。
- 本地只修改 `D:\L-One Lab\03_独立项目\L-One-main-site`。
- 用户可见内容禁止自动补写；外链识别结果必须进入人工校对。
- 公开 API 只返回 `published` 且已到发布时间的内容。
- 每个阶段完成后执行完整测试、浏览器视觉检查和回滚检查。

## Checkpoint 1: Content Foundation And APIs

### Task 1: Add versioned database migrations

**Files:**
- Create: `server/materials-service/app/migrations.py`
- Modify: `server/materials-service/app/database.py`
- Test: `server/materials-service/tests/test_migrations.py`

**Step 1: Write the failing migration tests**

覆盖以下行为：

```python
def test_initialize_preserves_existing_material_jobs(self): ...
def test_initialize_creates_content_schema_once(self): ...
def test_schema_version_advances_transactionally(self): ...
```

断言原有 `jobs`、`audit_log` 数据不丢失，并创建：

```text
schema_migrations
content_items
content_versions
media_assets
content_media
categories
tags
content_tags
import_jobs
publication_jobs
```

**Step 2: Run the test to verify it fails**

Run from `server/materials-service`:

```powershell
python -m unittest tests.test_migrations -v
```

Expected: FAIL because `app.migrations` and the content tables do not exist.

**Step 3: Implement the migration runner**

Use ordered migrations with an immediate transaction:

```python
MIGRATIONS = [(1, "content foundation", migrate_content_foundation)]

def apply_all(connection: sqlite3.Connection) -> None:
    connection.execute("BEGIN IMMEDIATE")
    ...
```

`database.initialize()` must configure WAL, foreign keys, busy timeout, then call `migrations.apply_all(connection)`.

**Step 4: Run tests**

```powershell
python -m unittest tests.test_migrations tests.test_core tests.test_admin -v
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add server/materials-service/app/migrations.py server/materials-service/app/database.py server/materials-service/tests/test_migrations.py
git commit -m "feat(admin): add versioned content migrations"
```

### Task 2: Implement the content repository and validation rules

**Files:**
- Create: `server/materials-service/app/content/__init__.py`
- Create: `server/materials-service/app/content/models.py`
- Create: `server/materials-service/app/content/validation.py`
- Create: `server/materials-service/app/content/repository.py`
- Test: `server/materials-service/tests/test_content_repository.py`

**Step 1: Write failing repository tests**

Test:

```python
def test_create_draft_assigns_stable_id_and_slug(self): ...
def test_slug_is_unique_per_target(self): ...
def test_publish_rejects_missing_title_body_or_cover(self): ...
def test_update_creates_content_version(self): ...
def test_recycle_and_restore_preserve_relations(self): ...
```

Core enums:

```python
TARGETS = {"works", "notes"}
CONTENT_TYPES = {"article", "gallery", "video", "external"}
STATUSES = {"draft", "pending", "published", "offline", "recycled"}
```

**Step 2: Run failing test**

```powershell
python -m unittest tests.test_content_repository -v
```

**Step 3: Implement minimal repository methods**

Required public methods:

```python
create_content(payload, actor)
get_content(content_id)
list_content(filters)
update_content(content_id, payload, actor, expected_version)
change_status(content_id, status, actor, publish_at=None)
restore_version(content_id, version_id, actor)
attach_tags(content_id, tag_names)
attach_category(content_id, category_slug)
```

Use optimistic locking via `revision` to prevent concurrent overwrites.

**Step 4: Run tests**

```powershell
python -m unittest tests.test_content_repository tests.test_migrations -v
```

**Step 5: Commit**

```powershell
git add server/materials-service/app/content server/materials-service/tests/test_content_repository.py
git commit -m "feat(admin): add structured content repository"
```

### Task 3: Define and sanitize the canonical content body

**Files:**
- Create: `server/materials-service/app/content/blocks.py`
- Modify: `server/materials-service/requirements.txt`
- Test: `server/materials-service/tests/test_content_blocks.py`

**Step 1: Write failing block tests**

Supported block types:

```text
paragraph, heading, quote, list, image, gallery, video,
divider, code, attachment, external_link
```

Tests must reject unknown blocks, inline scripts, event attributes, `javascript:` URLs, invalid media IDs, oversized documents and malformed nesting.

**Step 2: Run failing test**

```powershell
python -m unittest tests.test_content_blocks -v
```

**Step 3: Implement normalization and safe rendering**

Add pinned dependency:

```text
bleach==6.2.0
```

Implement:

```python
def normalize_blocks(raw: list[dict]) -> list[dict]: ...
def render_blocks(blocks: list[dict], media_lookup) -> str: ...
def excerpt_from_blocks(blocks: list[dict], limit: int = 180) -> str: ...
```

Render only allowlisted tags and attributes. External links use `rel="noopener noreferrer"`.

**Step 4: Run tests**

```powershell
python -m unittest tests.test_content_blocks tests.test_content_repository -v
```

**Step 5: Commit**

```powershell
git add server/materials-service/app/content/blocks.py server/materials-service/requirements.txt server/materials-service/tests/test_content_blocks.py
git commit -m "feat(admin): add safe canonical content blocks"
```

### Task 4: Add protected admin content APIs

**Files:**
- Create: `server/materials-service/app/routers/__init__.py`
- Create: `server/materials-service/app/routers/admin_content.py`
- Create: `server/materials-service/app/routers/admin_taxonomy.py`
- Modify: `server/materials-service/app/api.py`
- Test: `server/materials-service/tests/test_admin_content_api.py`

**Step 1: Write failing API tests**

Cover authentication, CSRF, validation, optimistic locking and audit records for:

```text
GET    /api/admin/v1/content
POST   /api/admin/v1/content
GET    /api/admin/v1/content/{id}
PATCH  /api/admin/v1/content/{id}
POST   /api/admin/v1/content/{id}/status
GET    /api/admin/v1/content/{id}/versions
POST   /api/admin/v1/content/{id}/versions/{version_id}/restore
GET    /api/admin/v1/categories
GET    /api/admin/v1/tags
POST   /api/admin/v1/account/password
```

**Step 2: Run failing test**

```powershell
python -m unittest tests.test_admin_content_api -v
```

**Step 3: Implement routers**

Reuse existing signed session and CSRF validation from `app/security.py`. Password changes require the current password, revoke existing sessions and store only the new password hash. Every mutation records actor, action, target, result and timestamp in `audit_log`.

**Step 4: Run tests**

```powershell
python -m unittest tests.test_admin_content_api tests.test_admin -v
```

**Step 5: Commit**

```powershell
git add server/materials-service/app/routers server/materials-service/app/api.py server/materials-service/tests/test_admin_content_api.py
git commit -m "feat(admin): expose protected content APIs"
```

### Task 5: Add public versioned content APIs

**Files:**
- Create: `server/materials-service/app/routers/public_content.py`
- Modify: `server/materials-service/app/api.py`
- Test: `server/materials-service/tests/test_public_content_api.py`

**Step 1: Write failing public API tests**

Cover:

```text
GET /api/public/v1/content?target=works&type=video
GET /api/public/v1/content/{target}/{slug}
GET /api/public/v1/categories?target=works
GET /api/public/v1/tags?target=notes
```

Assert drafts, pending, offline and recycled records never appear. Assert scheduled content appears only after `publish_at`.

**Step 2: Run failing test**

```powershell
python -m unittest tests.test_public_content_api -v
```

**Step 3: Implement read-only API**

Return a stable envelope:

```json
{"api_version":"v1","items":[],"next_cursor":null}
```

Set `Cache-Control: public, max-age=60, stale-while-revalidate=300` and deterministic ETags.

**Step 4: Run tests and checkpoint verification**

```powershell
python -m unittest discover -s tests -v
```

Expected: all tests PASS and Materials APIs remain unchanged.

**Step 5: Commit**

```powershell
git add server/materials-service/app/routers/public_content.py server/materials-service/app/api.py server/materials-service/tests/test_public_content_api.py
git commit -m "feat(api): add public content v1 endpoints"
```

## Checkpoint 2: Unified Creator Admin

### Task 6: Split the admin frontend into stable modules

**Files:**
- Create: `server/materials-service/app/admin/index.html`
- Create: `server/materials-service/app/admin/admin.css`
- Create: `server/materials-service/app/admin/api.js`
- Create: `server/materials-service/app/admin/state.js`
- Create: `server/materials-service/app/admin/app.js`
- Modify: `server/materials-service/app/api.py`
- Delete after parity verification: `server/materials-service/app/admin.html`
- Test: `server/materials-service/tests/test_admin_shell.py`

**Step 1: Write failing shell tests**

Assert `/admin/` serves the shell, module assets load, unauthenticated access shows login, and authenticated access exposes these navigation items:

```text
创作发布, 内容管理, 素材库, 回收站, 操作记录, 系统状态
```

**Step 2: Run failing test**

```powershell
python -m unittest tests.test_admin_shell -v
```

**Step 3: Implement shell and route map**

Client routes:

```text
#/create
#/content
#/materials
#/recycle
#/activity
#/system
```

Use the existing monochrome L-One visual language. Keep the primary workspace usable from 1280 px down to 390 px.

**Step 4: Run tests and browser check**

```powershell
python -m unittest tests.test_admin_shell tests.test_admin -v
python -m uvicorn app.api:app --host 127.0.0.1 --port 8011
```

Open `http://127.0.0.1:8011/admin/` and verify desktop and mobile layouts before deleting `admin.html`.

**Step 5: Commit**

```powershell
git add server/materials-service/app/admin server/materials-service/app/api.py server/materials-service/tests/test_admin_shell.py
git rm server/materials-service/app/admin.html
git commit -m "refactor(admin): split creator console frontend"
```

### Task 7: Build the unified editor with autosave

**Files:**
- Create: `server/materials-service/app/admin/editor.js`
- Create: `server/materials-service/app/admin/editor.css`
- Create: `server/materials-service/app/admin/editor-model.js`
- Modify: `server/materials-service/app/admin/app.js`
- Test: `server/materials-service/tests/test_editor_contract.py`

**Step 1: Write failing editor contract tests**

Test the editor HTML exposes fields for:

```text
target, content type, title, excerpt, body blocks, cover,
gallery/video, category, tags, publish date, original URL
```

Test JavaScript source includes debounced autosave, dirty-state warning, revision conflict handling, manual save and preview actions.

**Step 2: Run failing test**

```powershell
python -m unittest tests.test_editor_contract -v
```

**Step 3: Implement editor behavior**

Use one canonical editor for Works and Notes. Target/type selection controls field visibility without changing stored schema. Autosave drafts after 1.5 seconds of inactivity and display save state explicitly.

**Step 4: Run tests and visual check**

```powershell
python -m unittest tests.test_editor_contract -v
```

In browser create one Works article draft and one Notes draft, reload, and verify both restore correctly.

**Step 5: Commit**

```powershell
git add server/materials-service/app/admin/editor.js server/materials-service/app/admin/editor.css server/materials-service/app/admin/editor-model.js server/materials-service/app/admin/app.js server/materials-service/tests/test_editor_contract.py
git commit -m "feat(admin): add unified content editor"
```

### Task 8: Build content management, recycle, activity and system views

**Files:**
- Create: `server/materials-service/app/admin/content-list.js`
- Create: `server/materials-service/app/admin/recycle.js`
- Create: `server/materials-service/app/admin/activity.js`
- Create: `server/materials-service/app/admin/system.js`
- Modify: `server/materials-service/app/admin/app.js`
- Test: `server/materials-service/tests/test_admin_views.py`

**Step 1: Write failing view tests**

Require filters for target, type, status, category, tag, date and keyword. Require actions for edit, preview, publish, offline, recycle, restore and permanent delete.

**Step 2: Run failing test**

```powershell
python -m unittest tests.test_admin_views -v
```

**Step 3: Implement views**

The system view displays:

```text
API health, worker health, queue depth, disk usage,
database size, backup time, failed jobs
```

The system view also provides the owner password-change form. Permanent delete requires a second confirmation containing the content title.

**Step 4: Run tests and browser check**

```powershell
python -m unittest tests.test_admin_views -v
```

Verify filters and actions against seeded test data.

**Step 5: Commit**

```powershell
git add server/materials-service/app/admin server/materials-service/tests/test_admin_views.py
git commit -m "feat(admin): add content management views"
```

### Task 9: Add server-side desktop and mobile previews

**Files:**
- Create: `server/materials-service/app/routers/admin_preview.py`
- Create: `server/materials-service/app/admin/preview.js`
- Modify: `server/materials-service/app/api.py`
- Modify: `server/materials-service/app/admin/app.js`
- Test: `server/materials-service/tests/test_preview_api.py`

**Step 1: Write failing preview tests**

Preview tokens must be signed, expire within 15 minutes, and render drafts without making them public.

**Step 2: Run failing test**

```powershell
python -m unittest tests.test_preview_api -v
```

**Step 3: Implement preview endpoint**

```text
POST /api/admin/v1/content/{id}/preview-token
GET  /api/admin/v1/preview/{token}
```

Render with the same canonical block renderer used by the public API. The admin preview panel switches between 390 px mobile and 1280 px desktop frames.

**Step 4: Run tests and checkpoint verification**

```powershell
python -m unittest discover -s tests -v
```

Verify title, cover, body order, gallery/video and original-link button match between editor and preview.

**Step 5: Commit**

```powershell
git add server/materials-service/app/routers/admin_preview.py server/materials-service/app/admin/preview.js server/materials-service/app/api.py server/materials-service/app/admin/app.js server/materials-service/tests/test_preview_api.py
git commit -m "feat(admin): add signed visual previews"
```

## Checkpoint 3: Import, Media And Publication

### Task 10: Add content media upload and reuse

**Files:**
- Create: `server/materials-service/app/content/media.py`
- Create: `server/materials-service/app/routers/admin_media.py`
- Modify: `server/materials-service/app/settings.py`
- Modify: `server/materials-service/app/api.py`
- Test: `server/materials-service/tests/test_content_media.py`

**Step 1: Write failing media tests**

Cover MIME allowlists, size limits, SHA-256 deduplication, safe filenames, image metadata, stable public URLs and orphan cleanup protection.

**Step 2: Run failing test**

```powershell
python -m unittest tests.test_content_media -v
```

**Step 3: Implement media storage**

Paths:

```text
/var/lib/l-one-content/incoming
/www/l-one-static/content/<content-id>/<media-id>/
```

Images retain a quality master plus generated display sizes. Content videos reuse FFmpeg helpers while writing under `content/`, leaving `materials/` untouched.

**Step 4: Run tests**

```powershell
python -m unittest tests.test_content_media tests.test_core -v
```

**Step 5: Commit**

```powershell
git add server/materials-service/app/content/media.py server/materials-service/app/routers/admin_media.py server/materials-service/app/settings.py server/materials-service/app/api.py server/materials-service/tests/test_content_media.py
git commit -m "feat(admin): add reusable content media storage"
```

### Task 11: Add safe external-link import and manual review

**Files:**
- Create: `server/materials-service/app/importing/__init__.py`
- Create: `server/materials-service/app/importing/security.py`
- Create: `server/materials-service/app/importing/generic.py`
- Create: `server/materials-service/app/importing/xiaohongshu.py`
- Create: `server/materials-service/app/routers/admin_imports.py`
- Create: `server/materials-service/app/admin/import-review.js`
- Test: `server/materials-service/tests/fixtures/xiaohongshu-note.html`
- Test: `server/materials-service/tests/test_imports.py`

**Step 1: Write failing import tests**

Cover URL normalization, redirects, private/reserved IP blocking, response-size limits, content-type checks, title/body/media extraction and provenance fields.

Fixture assertions must preserve the exact source title/body/media order. Missing source fields remain empty.

**Step 2: Run failing test**

```powershell
python -m unittest tests.test_imports -v
```

**Step 3: Implement provider adapters**

Interface:

```python
class ImportProvider(Protocol):
    def supports(self, url: str) -> bool: ...
    def extract(self, response: FetchResult) -> ImportResult: ...
```

The generic adapter reads OpenGraph/JSON-LD. The Xiaohongshu adapter reads deterministic embedded page state when available. Every result stores source URL, fetch time, provider and raw evidence hash.

**Step 4: Implement review workflow**

```text
POST /api/admin/v1/imports
GET  /api/admin/v1/imports/{id}
POST /api/admin/v1/imports/{id}/create-draft
```

The review page displays extracted and editable fields side by side. Creating a draft requires explicit confirmation.

**Step 5: Run tests and commit**

```powershell
python -m unittest tests.test_imports tests.test_content_repository -v
git add server/materials-service/app/importing server/materials-service/app/routers/admin_imports.py server/materials-service/app/admin/import-review.js server/materials-service/tests
git commit -m "feat(admin): add reviewed external content imports"
```

### Task 12: Add scheduled publication and automatic state transitions

**Files:**
- Create: `server/materials-service/app/publication.py`
- Create: `server/materials-service/app/publication_worker.py`
- Create: `server/materials-service/systemd/l-one-publication-worker.service`
- Create: `server/materials-service/scripts/install.sh`
- Test: `server/materials-service/tests/test_publication.py`

**Step 1: Write failing scheduler tests**

Test immediate publish, future publish, idempotent retry, failed publication logging and offline behavior.

**Step 2: Run failing test**

```powershell
python -m unittest tests.test_publication -v
```

**Step 3: Implement serial publication worker**

Claim one due job transactionally, publish, record audit, invalidate public cache metadata, then claim the next job. A crash must leave the job retryable.

**Step 4: Run tests and checkpoint verification**

```powershell
python -m unittest discover -s tests -v
```

**Step 5: Commit**

```powershell
git add server/materials-service/app/publication.py server/materials-service/app/publication_worker.py server/materials-service/systemd/l-one-publication-worker.service server/materials-service/scripts/install.sh server/materials-service/tests/test_publication.py
git commit -m "feat(admin): add scheduled publication worker"
```

## Checkpoint 4: Public Site Integration

### Task 13: Add a public content API adapter to the main site

**Files:**
- Create: `assets/js/content-api.js`
- Create: `assets/js/content-renderer.js`
- Create: `assets/css/dynamic-content.css`
- Modify: `index.html`
- Test: `tests/site/test_dynamic_content.ps1`

**Step 1: Write failing static integration checks**

The script must assert:

- existing `assets/works/index.json` remains referenced or preserved unchanged;
- the API base is centralized in one configuration constant;
- failed API requests fall back to current static content;
- dynamic records are deduplicated by stable ID;
- Works and Notes filters use `target` and `content_type`.

**Step 2: Run failing check**

```powershell
powershell -ExecutionPolicy Bypass -File tests/site/test_dynamic_content.ps1
```

**Step 3: Implement adapter and renderer**

Use:

```javascript
const CONTENT_API_BASE = "https://admin.l-one.asia/api/public/v1";
```

Fetch published records, merge with the static Works array, and render canonical blocks. Preserve existing static Works detail behavior and current Works layout.

**Step 4: Run checks and local browser verification**

```powershell
powershell -ExecutionPolicy Bypass -File tests/site/test_dynamic_content.ps1
```

Verify these routes:

```text
#works
#notes
#work-<existing-static-slug>
#work-<new-api-slug>
#note-<new-api-slug>
```

Test with API available and unavailable.

**Step 5: Commit**

```powershell
git add assets/js/content-api.js assets/js/content-renderer.js assets/css/dynamic-content.css index.html tests/site/test_dynamic_content.ps1
git commit -m "feat(site): render published API content"
```

### Task 14: Add cache invalidation and publication smoke tests

**Files:**
- Create: `server/materials-service/tests/test_end_to_end_content.py`
- Create: `server/materials-service/scripts/smoke-content.ps1`
- Modify: `server/materials-service/app/publication.py`

**Step 1: Write failing end-to-end tests**

Scenario:

```text
login -> create draft -> upload cover -> preview -> publish ->
public list -> public detail -> offline -> absent from public API -> restore
```

**Step 2: Run failing test**

```powershell
python -m unittest tests.test_end_to_end_content -v
```

**Step 3: Implement deterministic cache versioning**

Increment a public content generation value on publish/offline/delete. Include it in ETags and expose it in `/api/health`.

**Step 4: Run tests and commit**

```powershell
python -m unittest discover -s tests -v
git add server/materials-service/app/publication.py server/materials-service/tests/test_end_to_end_content.py server/materials-service/scripts/smoke-content.ps1
git commit -m "test(content): cover full publishing lifecycle"
```

## Checkpoint 5: Operations, Deployment And Documentation

### Task 15: Add backup, retention and disk safeguards

**Files:**
- Modify: `server/materials-service/app/maintenance.py`
- Modify: `server/materials-service/app/settings.py`
- Create: `server/materials-service/systemd/l-one-content-backup.service`
- Create: `server/materials-service/systemd/l-one-content-backup.timer`
- Modify: `server/materials-service/scripts/install.sh`
- Test: `server/materials-service/tests/test_content_maintenance.py`

**Step 1: Write failing maintenance tests**

Cover daily SQLite backup, metadata snapshot, 14-day retention, 30-day recycle purge, low-disk upload blocking and safe partial-file cleanup.

**Step 2: Run failing test**

```powershell
python -m unittest tests.test_content_maintenance -v
```

**Step 3: Implement maintenance jobs**

Backup with SQLite online backup API. Write first to a temporary file and rename atomically. Never delete the newest successful backup.

**Step 4: Run tests and commit**

```powershell
python -m unittest tests.test_content_maintenance tests.test_admin -v
git add server/materials-service/app/maintenance.py server/materials-service/app/settings.py server/materials-service/systemd server/materials-service/scripts/install.sh server/materials-service/tests/test_content_maintenance.py
git commit -m "feat(ops): protect content storage and backups"
```

### Task 16: Deploy to the lightweight server and verify domains

**Files:**
- Modify: `server/materials-service/nginx/l-one-admin.conf`
- Modify: `server/materials-service/nginx/l-one-static.conf`
- Create: `server/materials-service/scripts/deploy.ps1`
- Create: `server/materials-service/scripts/verify-production.ps1`
- Modify: `server/materials-service/README.md`

**Step 1: Add deployment preflight checks**

The script must stop when git is dirty, tests fail, SSH is unavailable, disk free space is below threshold, or required environment variables are absent.

**Step 2: Run local verification**

```powershell
Set-Location server/materials-service
python -m unittest discover -s tests -v
powershell -ExecutionPolicy Bypass -File scripts/verify-production.ps1 -Mode Preflight
```

**Step 3: Deploy**

Deploy application code, install dependencies, run migrations, restart API/publication/material workers and reload Nginx. Never copy local database files to production.

**Step 4: Verify production**

```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify-production.ps1 -Mode Production
```

Verify:

```text
https://admin.l-one.asia/admin/
https://admin.l-one.asia/api/health
https://admin.l-one.asia/api/public/v1/content
https://static.l-one.asia/content/
https://l-one.asia/
```

Also verify HTTPS redirects, authentication, CSRF, failed-login throttling, upload limits and mobile admin access.

**Step 5: Commit**

```powershell
git add server/materials-service/nginx server/materials-service/scripts server/materials-service/README.md
git commit -m "ops(admin): deploy unified creator console"
```

### Task 17: Publish maintenance rules and update project status

**Files:**
- Create: `docs/CONTENT_SYSTEM_MAINTENANCE.md`
- Create: `docs/CONTENT_API_CONTRACT.md`
- Create: `docs/ADMIN_OPERATIONS.md`
- Modify: `SITE_STATUS.md`

**Step 1: Document immutable boundaries**

Record:

- editable and protected file boundaries;
- database and media ownership;
- API versioning and compatibility rules;
- content status transitions;
- deployment and rollback procedures;
- backup restore procedure;
- incident checklist;
- instructions for future Codex conversations.

**Step 2: Verify documentation against implementation**

Run every documented command in a test environment. Check every endpoint and path exists exactly as written.

**Step 3: Update status**

Update `SITE_STATUS.md` date, deployed services, domain status, backup status, recent changes and next known work. Remind the user that main-site frontend commits must be pushed to GitHub for EdgeOne Pages deployment.

**Step 4: Run final verification**

```powershell
Push-Location server/materials-service
python -m unittest discover -s tests -v
Pop-Location
powershell -ExecutionPolicy Bypass -File tests/site/test_dynamic_content.ps1
git diff --check
git status --short
```

Expected: tests pass, no whitespace errors, only intentional changes remain.

**Step 5: Commit**

```powershell
git add docs SITE_STATUS.md
git commit -m "docs: define content system maintenance rules"
```

## Final Acceptance Checklist

- One owner can log in and change the long-term password.
- Works and Notes use one editor and one content schema.
- Materials upload/transcode/delete behavior remains operational.
- External links enter review before draft creation.
- Drafts autosave and retain version history.
- Desktop and mobile previews match public rendering.
- Immediate and scheduled publication work.
- Recycle, restore, audit and permanent deletion work.
- Existing 14 Works remain byte-for-byte unchanged.
- Motion Library 64 effects remain unchanged.
- Public site remains usable when the content API is unavailable.
- Database and metadata backups run daily with 14-day retention.
- Recycle content expires after 30 days.
- Disk safeguards block risky uploads before the server is full.
- `admin.l-one.asia`, `static.l-one.asia` and `l-one.asia` use HTTPS.
- Maintenance, API and operator documentation match production.
