# L-One Unified Creator Administration Design

## 1. Goal

Build one private creator administration system at `https://admin.l-one.asia/admin/` for publishing and managing new Works, Notes, and Materials content without editing source files, running commands, or depending on Codex for routine updates.

The administration system becomes the source of truth for all content created after this phase. The public site reads published records through a versioned public API. Existing static content remains available during the transition.

## 2. Confirmed Decisions

- One administrator account with a changeable long-term password.
- The administrator can create, edit, publish, unpublish, replace, delete, restore, and permanently remove content.
- Content states are `draft`, `pending`, `published`, `offline`, and `recycled`.
- One editor supports rich text and Markdown, including image drag-and-drop.
- New content can be created as image-and-text, video-and-text, or an imported external link.
- Every record targets either Works or Notes.
- External links enter an automatic extraction flow followed by mandatory manual review.
- Media files are archived on the Tencent lightweight server.
- Recycled content is retained for 30 days.
- Every saved revision creates a restorable version.
- Desktop and mobile visual previews are available before publication.
- Publication can be immediate or scheduled.
- Content management provides unified search, status filters, target filters, type filters, category filters, and date filters.
- The current Materials processing pipeline remains available inside the unified administration system.
- Administrative mutations are recorded in an audit log.
- SQLite and metadata backups run daily and retain 14 days.
- The administration URL remains `https://admin.l-one.asia/admin/`.
- The existing 14 Works records are not migrated in this phase.
- Newly created Works and Notes are delivered to the public site through a read-only API.
- The interface follows a creator-platform structure with creation as the primary action.

## 3. Scope and Protected Boundaries

### In scope

- Extend the existing FastAPI service into a unified creator administration backend.
- Add structured storage for Works and Notes.
- Build a unified editor and content management interface.
- Add external-link extraction jobs and manual review.
- Add publishing, scheduling, version history, recycling, audit, backup status, and disk status.
- Expose a read-only public content API.
- Update the public site to display newly published API content alongside existing static content.

### Protected and unchanged in this phase

- The 14 Works records currently stored under `assets/works/` remain static and read-only.
- Existing static Works detail pages retain their current URLs and rendering.
- The 64 Motion Library effects and their independent code packages remain unchanged.
- The current Materials FFmpeg queue, generated WebP cover, WebM preview, downloadable MP4, and public manifest remain operational.
- The public site design is not rebuilt as part of the administration project.
- Existing GitHub and EdgeOne deployment continues for public frontend code.

## 4. Architecture

The system has five isolated layers:

1. **Administration interface**: browser UI at `admin.l-one.asia/admin/`.
2. **Protected administration API**: authenticated FastAPI endpoints for content, media, imports, versions, publishing, and system operations.
3. **Content and workflow storage**: SQLite database for structured records, versions, jobs, schedules, and audit events.
4. **Media storage and processing**: lightweight-server filesystem plus the existing serial FFmpeg worker.
5. **Public read API**: unauthenticated, read-only, versioned endpoints that expose published content only.

The public frontend consumes the API contract. It does not read administration tables, server folders, draft records, or editor-specific state.

## 5. Administration Information Architecture

The administration shell uses a fixed left navigation and a single main workspace.

### Navigation

- **Create**: default landing page and unified editor.
- **Content**: all Works and Notes records.
- **Materials**: existing material upload and processing workflow.
- **Publishing**: pending, scheduled, published, and offline records.
- **Recycle Bin**: recoverable content and media awaiting expiry.
- **Activity**: audit records and version history access.
- **System**: disk capacity, queue state, backups, API health, and worker health.

### Content list

Each row displays cover, title, target, content type, status, original publication date, site publication date, last edited time, and actions. Actions include preview, edit, duplicate, publish, offline, move to recycle bin, and open version history.

The list supports keyword search and combined filters. Bulk operations are limited to publish, offline, and move to recycle bin. Permanent deletion remains a single-record confirmation action.

## 6. Unified Editor

### Creation modes

- **Image and text**: cover, gallery, title, summary, structured body, categories, tags, dates, and original link.
- **Video and text**: cover, video, title, summary, structured body, categories, tags, dates, and original link.
- **External link import**: URL submission, extraction progress, extracted media and text, validation warnings, and manual correction before save.

### Required fields

- Target: Works or Notes.
- Content type: image-text or video.
- Title.
- Slug generated from the title and editable before first publication.
- Body.
- Cover.
- Site publication mode: immediate or scheduled.

### Optional fields

- Summary.
- Gallery.
- Video.
- Category.
- Tags.
- Source platform.
- Source URL shown as `阅读原文` on the public page.
- Original platform publication date.
- Attachment files for Notes.

### Canonical body format

The editor stores a canonical block document in JSON. Supported block types are paragraph, heading, quote, list, image, gallery, video, divider, code, attachment, and external-link button. Markdown and rich-text views edit the same canonical document through controlled conversion.

The backend also generates sanitized HTML for public delivery. Frontend layout rules are never stored inside content records. This keeps typography, spacing, card dimensions, and responsive behavior independent from the publishing workflow.

## 7. External Link Import

External import runs as a background job:

1. Validate the URL and reject local, private-network, unsupported, or unsafe destinations.
2. Fetch page metadata and content using a provider adapter.
3. Extract title, body, publication date, author, tags, cover, gallery, and video references when available.
4. Download permitted media into a temporary server directory.
5. Normalize extracted text and media into the canonical content model.
6. Present the result as an editable draft with field-level warnings.
7. Require manual confirmation before saving or publishing.

Provider adapters are isolated modules. A failure in Xiaohongshu parsing does not alter WeChat, generic web pages, or manually created content. Imported text is preserved without invented descriptions. Missing information remains empty and visibly flagged.

## 8. Data Model

### `content_items`

- `id`: stable UUID.
- `target`: `works` or `notes`.
- `content_type`: `image_text` or `video`.
- `title`, `slug`, `summary`.
- `body_json`, `body_html`.
- `status`.
- `source_platform`, `source_url`.
- `original_published_at`.
- `site_publish_at`, `published_at`, `offline_at`.
- `current_version`.
- `created_at`, `updated_at`, `recycled_at`.

### `content_versions`

Stores a complete immutable snapshot for every save, including editor identity, version number, creation time, and change note. Restoring a version creates a new current version rather than deleting later history.

### `media_assets`

Stores stable media IDs, media type, original filename, MIME type, byte size, dimensions, duration, public URL, internal path, checksum, processing status, and timestamps.

### `content_media`

Links content records to cover, gallery, video, attachment, and inline media with explicit ordering.

### Taxonomy tables

`categories`, `tags`, and `content_tags` provide normalized filtering values. A content record has at most one primary category and any number of tags.

### Workflow tables

- `import_jobs`: provider, URL, status, extracted payload, warnings, and error.
- `publication_jobs`: target time, status, attempt count, and error.
- Existing `jobs`: retained for Materials and media processing.
- Existing `audit_log`: extended with content target, request ID, and structured details.

Database migrations are additive and versioned. Existing Materials tables and records are preserved.

## 9. Media Storage

Server paths are separated by responsibility:

```text
/var/lib/l-one-content/
  database/
  imports/
  incoming/
  recycle/
  backups/
  logs/

/www/l-one-static/
  content/<content-id>/
  materials/
```

Image uploads are validated, orientation-normalized, and converted to web-friendly derivatives while retaining a controlled source copy when required. Video uploads use the existing serial worker to create a maximum-1280-pixel H.264/AAC MP4, WebP cover, and short WebM preview. Temporary sources are deleted after successful processing.

Published files are served from `static.l-one.asia`. Database records store stable public URLs and internal paths. Media URLs are never scattered as provider constants in frontend components.

## 10. API Contract

### Protected administration API

```text
/api/admin/v1/content
/api/admin/v1/content/{id}
/api/admin/v1/content/{id}/versions
/api/admin/v1/content/{id}/preview
/api/admin/v1/content/{id}/publish
/api/admin/v1/content/{id}/offline
/api/admin/v1/content/{id}/restore
/api/admin/v1/imports
/api/admin/v1/media
/api/admin/v1/materials
/api/admin/v1/system
```

Mutating requests require the secure administrator session and CSRF token. Responses use stable error codes and field-level validation messages.

### Public read API

```text
/api/public/v1/content
/api/public/v1/content/{target}/{slug}
/api/public/v1/categories
/api/public/v1/tags
```

The public API returns published records whose publication time has passed. Drafts, pending records, offline records, recycled records, internal paths, audit data, and editor metadata are excluded.

List responses support target, type, category, tag, date, pagination, and sort parameters. ETags and cache headers allow EdgeOne and browsers to cache published responses safely.

## 11. Publication and Frontend Integration

Immediate publication performs validation, commits the published state, clears the relevant API cache, and records an audit event. Scheduled publication is handled by a server-side worker that claims due jobs transactionally and retries recoverable failures.

The current static frontend merges two sources:

1. Existing static Works records from `assets/works/index.json`.
2. New API records from `/api/public/v1/content`.

Static IDs and API UUIDs use separate namespaces, preventing accidental duplicates. New Works details use the existing hash-navigation pattern during this phase. New Notes use the same renderer with a Notes target template. A future clean-URL migration can change routing without changing stored content or administration workflows.

If the API is unavailable, existing static content remains visible and the page shows a restrained loading failure for new records. A frontend failure cannot modify administration data.

## 12. Security

- One administrator account with a modern password hash and change-password flow.
- HTTP-only, secure, same-site session cookie with expiry and logout invalidation.
- CSRF protection on all mutations.
- Login throttling and audit events for failed and successful authentication.
- File extension, MIME, content signature, size, and disk-space validation.
- HTML sanitization before preview and publication.
- External-import SSRF protection blocking loopback, private, link-local, metadata-service, and non-HTTP destinations.
- Import download limits, timeouts, redirect limits, and content-type allowlists.
- Nginx request-size and rate limits.
- Public API is read-only and has no path to administration mutations.
- The admin hostname is absent from public navigation and search indexing.

## 13. Recycle, Versions, Backups, and Capacity

- Content and media moved to the recycle bin remain recoverable for 30 days.
- Expired recycle entries are permanently removed by a daily cleanup task.
- Every save creates a version snapshot; version history is retained while the content record exists.
- SQLite, manifests, metadata, and configuration are backed up daily and retained for 14 days.
- Large published media files are not duplicated in the first server-local backup because the server disk is limited to 40 GB.
- The system shows total, used, and free disk space and rejects uploads below the configured safety threshold.
- Warning and critical thresholds are configurable and visible in the System page.

## 14. Error Handling

- Autosave failures preserve the editor state in the browser and show a retry action.
- Media failures remain visible as retryable jobs.
- Import failures retain the URL, provider, error, and partial results when safe.
- Publication is blocked when required fields, media processing, or sanitization fail.
- Database mutations use transactions.
- Public cache invalidation failures are retried and do not roll back a valid database publication.
- Scheduled jobs use claim locks to prevent duplicate publication.

## 15. Visual Direction

The administration interface uses a restrained creator-platform layout:

- Fixed left navigation.
- Light neutral background and white content surfaces.
- Black, white, and gray as the base palette with one restrained action color.
- Creation workspace as the default landing page.
- Wide editor canvas, compact metadata sidebar, and persistent save/preview/publish controls.
- Content management uses dense, readable records rather than decorative public-site cards.
- Responsive support prioritizes review, status changes, and simple uploads on mobile. Long-form editing remains optimized for desktop and tablet.

## 16. Change Permissions

Implementation work must declare its editable scope before changes begin.

- Content-schema tasks may change migrations, models, repositories, and focused tests.
- Administration UI tasks may change admin assets and administration endpoints.
- Public integration tasks may change public API adapters and the smallest required frontend renderer.
- Materials tasks may change the Materials pipeline only when explicitly requested.
- Existing static Works, Motion Library, About, homepage, and unrelated navigation are read-only unless the task names them.

No task may rewrite an already delivered area as a side effect of another feature. Shared files require focused diffs and regression verification.

## 17. Delivery Phases

### Phase 1: foundation

- Add versioned database migrations.
- Add content, version, media-link, taxonomy, import, and publication repositories.
- Add protected administration API and public read API contracts.
- Add focused backend tests.

### Phase 2: unified administration UI

- Replace the Materials-only page with the administration shell.
- Add Create, Content, Materials, Publishing, Recycle Bin, Activity, and System screens.
- Add unified editor, autosave, validation, desktop preview, and mobile preview.

### Phase 3: import and media workflows

- Add generic and provider-specific import adapters.
- Add manual review state and field warnings.
- Reuse the serial media worker for content video and image derivatives.

### Phase 4: public integration

- Add published content API caching.
- Merge new API Works with existing static Works.
- Add API-backed Notes records and detail rendering.
- Verify fallback behavior when the API is unavailable.

### Phase 5: deployment and operations

- Deploy migrations, service, worker, Nginx rules, cleanup, scheduler, and backups.
- Verify HTTPS, authentication, upload limits, disk thresholds, and API caching.
- Run end-to-end publication tests from draft through public display and offline removal.

## 18. Acceptance Criteria

1. The administrator can sign in from desktop, tablet, or phone using `admin.l-one.asia`.
2. A new image-and-text Works record can be drafted, previewed, published, displayed publicly, taken offline, and restored.
3. A new video Works record produces its cover, preview, and public video through the server queue.
4. A new Notes record supports rich text, Markdown, attachments, categories, tags, and `阅读原文`.
5. An external link can be extracted into a reviewable draft without invented content.
6. Published records appear through the public API; unpublished records never appear.
7. Existing 14 Works and existing Materials remain available throughout deployment.
8. Version restoration creates a new version and preserves audit history.
9. Recycled records remain recoverable for 30 days and expire automatically.
10. Disk warnings, upload rejection thresholds, queue state, backup status, and audit events are visible.
11. Public frontend layout changes can be made without changing stored content or administration endpoints.
12. Focused automated tests and browser verification pass before deployment.
