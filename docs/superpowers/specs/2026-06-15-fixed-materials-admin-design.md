# Fixed Materials Admin Design

## Goal

Provide a permanent, private browser-based administration page for the L-One materials library at `https://admin.l-one.asia`, so the owner can upload, inspect, replace, and delete materials without SSH commands or Codex assistance.

## Scope

This phase covers the materials library only. Article and Works publishing remains unchanged because those pages are still rendered directly inside `index.html` and require a separate data-driven migration.

Allowed changes are limited to `server/materials-service`, deployment documentation, focused tests, `SITE_STATUS.md`, and the DNS/server configuration required for `admin.l-one.asia`. Public Works, Notes, About, Motion Library, and existing material display behavior stay unchanged.

## Architecture

- `admin.l-one.asia` points to the Tencent lightweight server.
- Nginx terminates HTTPS and serves the existing administration frontend.
- FastAPI continues to perform uploads, queue operations, deletion, and manifest rebuilding.
- Authentication uses one administrator account, a password hash stored in the server environment, an HTTP-only secure session cookie, CSRF validation, login throttling, and short session expiry.
- The existing `X-L-One-Admin-Token` remains available temporarily for deployment diagnostics, then browser code stops storing or sending the raw token.
- Public material files remain under `https://static.l-one.asia/materials/`.

## Administration Functions

1. Login and logout.
2. Upload a video with title, category, and tags.
3. Display upload and FFmpeg job status.
4. Retry a failed job.
5. Preview published material.
6. Replace a material while retaining its stable asset ID and public URL.
7. Soft-delete a material into a seven-day server recycle area.
8. Permanently remove expired recycle entries automatically.
9. Display server disk usage and reject uploads below the configured free-space threshold.

## Storage and Recovery

- Published material, recycle entries, SQLite state, and rotating operation logs live on the lightweight server.
- Recycle files expire after seven days.
- Operation logs contain account, action, asset ID, timestamp, and result; passwords and tokens are excluded.
- A daily compressed backup contains SQLite state, JSON manifests, metadata, and configuration. Large published video files are excluded from the first-phase backup.
- Backups are initially retained on the server for seven days. Tencent COS backup is a later independent task after credentials and lifecycle rules are approved.

## Data Flow

1. The administrator signs in through `admin.l-one.asia`.
2. Nginx forwards same-origin API calls to FastAPI.
3. FastAPI validates the secure session, CSRF token, file type, file size, and free disk space.
4. Uploads enter the existing single-worker FFmpeg queue.
5. Successful jobs publish MP4, WebP, WebM, and metadata, remove the temporary source, and atomically rebuild `assets.json`.
6. The public Materials page reads the updated manifest from `static.l-one.asia`.

## Failure Handling

- Interrupted uploads and failed transcodes remain visible as failed jobs and can be retried.
- Manifest updates use an atomic temporary-file replacement.
- Delete and replace operations preserve recoverable files for seven days.
- Authentication failures are rate-limited and recorded without storing submitted passwords.
- The admin hostname never appears in public site navigation.

## Verification

- Automated tests cover login, logout, session expiry, CSRF rejection, upload authorization, replacement, soft deletion, restore-window cleanup, disk thresholds, and audit logging.
- Existing material pipeline tests continue to pass.
- Nginx tests confirm public `/admin/` on `static.l-one.asia` remains blocked and `admin.l-one.asia` serves only HTTPS.
- Browser verification covers desktop and mobile login, upload, job progress, preview, replace, and delete.
- Public site audit and material manifest loading must remain unchanged.

## Delivery Boundary

The first deliverable is a permanent materials administration page. Article cover, body, keyword, and category editing will be designed as a separate content-management phase after Works rendering is migrated away from hard-coded HTML.
