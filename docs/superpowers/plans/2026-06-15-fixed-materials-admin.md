# Fixed Materials Admin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a secure permanent materials administration page at `admin.l-one.asia` with browser login, upload, replace, soft delete, job status, disk status, and audit records.

**Architecture:** Extend the existing FastAPI service with signed server-side sessions, CSRF validation, audit tables, replacement jobs, and a seven-day recycle directory. Serve the existing admin UI through an admin-only Nginx virtual host while keeping `static.l-one.asia/admin/` blocked.

**Tech Stack:** Python 3, FastAPI, SQLite, Nginx, systemd, FFmpeg, unittest.

---

### Task 1: Authentication and audit foundation

**Files:**
- Create: `server/materials-service/app/security.py`
- Modify: `server/materials-service/app/settings.py`
- Modify: `server/materials-service/app/database.py`
- Test: `server/materials-service/tests/test_admin.py`

- [ ] Write failing tests for password verification, session expiry, CSRF validation, login throttling, and audit persistence.
- [ ] Run focused tests and confirm expected failures.
- [ ] Implement minimal security and database helpers.
- [ ] Run focused and existing tests.
- [ ] Commit the unit.

### Task 2: Authenticated administration API

**Files:**
- Modify: `server/materials-service/app/api.py`
- Test: `server/materials-service/tests/test_admin.py`

- [ ] Write failing API tests for login, logout, protected reads, CSRF rejection, and disk status.
- [ ] Run tests and confirm expected failures.
- [ ] Add cookie-session endpoints and protect browser API routes.
- [ ] Preserve header-token access for deployment diagnostics.
- [ ] Run the complete service test suite.
- [ ] Commit the unit.

### Task 3: Replacement and recycle workflow

**Files:**
- Modify: `server/materials-service/app/database.py`
- Modify: `server/materials-service/app/pipeline.py`
- Modify: `server/materials-service/app/worker.py`
- Modify: `server/materials-service/cleanup.py`
- Modify: `server/materials-service/app/api.py`
- Test: `server/materials-service/tests/test_admin.py`

- [ ] Write failing tests for stable-ID replacement, soft deletion, and expired recycle cleanup.
- [ ] Run tests and confirm expected failures.
- [ ] Implement replacement jobs and seven-day recycle storage.
- [ ] Run the complete service test suite.
- [ ] Commit the unit.

### Task 4: Permanent administration UI

**Files:**
- Modify: `server/materials-service/app/admin.html`
- Test: `server/materials-service/tests/test_admin.py`

- [ ] Write failing markup checks for account login, logout, disk status, replace, and delete controls.
- [ ] Run tests and confirm expected failures.
- [ ] Replace raw-token storage with secure-session requests and CSRF headers.
- [ ] Add disk status, replacement, audit feedback, and responsive states.
- [ ] Run service tests and inspect the page locally.
- [ ] Commit the unit.

### Task 5: Server routing and deployment

**Files:**
- Modify: `server/materials-service/nginx/l-one-static.conf`
- Modify: `server/materials-service/README.md`
- Modify: `SITE_STATUS.md`

- [ ] Add a dedicated `admin.l-one.asia` HTTPS virtual host and keep static-host admin access blocked.
- [ ] Generate a strong password hash and session secret in the server environment.
- [ ] Deploy source, restart services, and validate Nginx configuration.
- [ ] Add DNS and TLS for `admin.l-one.asia`.
- [ ] Verify public health, blocked static admin, admin login, upload workflow, and public manifest.
- [ ] Update status documentation and commit deployment records.

### Task 6: Final verification and synchronization

**Files:**
- Verify only.

- [ ] Run all Python service tests.
- [ ] Run `node scripts/site-audit.js`.
- [ ] Check `git diff --check` and repository status.
- [ ] Push commits to GitHub.
- [ ] Report the permanent admin URL and the location of the locally stored administrator credential.
