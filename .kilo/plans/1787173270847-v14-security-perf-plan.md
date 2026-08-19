# IntakeGateway v1.4 — Security & Performance Review + Implementation Plan

**Date:** 2026-08-19 · **Codebase:** v1.3.0 (commit `03ddf8b`, main)
**Scope:** Static code review of `backend/`, `frontend/`, `docker-compose.yml`, CI, docs — security, performance, correctness. No runtime profiling possible in review environment (sandbox lacks project deps); all findings are code-verified with `file:line` references.

---

## Part 1 — Findings

### Severity legend
Critical = data corruption, broken core feature, or remotely exploitable. High = significant risk or normal-use performance impact. Medium = bounded risk / robustness. Low = hygiene.

### 1.1 Critical

| ID | Finding | Location |
|---|---|---|
| C1 | **Scheduler is broken**: `_execute_scheduled_task` calls `enqueue_run.delay(task_id)` but `enqueue_run` is a plain function (no `.delay`) → `AttributeError` on every cron fire, swallowed by `except Exception`. No scheduled import ever runs; manual triggers work (they call `enqueue_run(...)` correctly), which masked the bug. | `backend/app/services/scheduler.py:119`, `backend/app/workers/tasks.py:140` |
| C2 | **Bulk CASE-UPDATE NULLs existing data**: `SET col = CASE WHEN key=r1 THEN v1 ... END` has no `ELSE`, but `WHERE` covers all batch rows. Rows with `None` for a column are excluded from the WHEN list, so the CASE evaluates NULL and **overwrites the column with NULL** — reintroducing ORA-01407, the exact bug Phase 10 claimed fixed. Also `update_cols` derives from the first row only: columns absent/None in row 1 are silently dropped for all rows. | `backend/app/services/runner.py:823-924` |
| C3 | **Skip condition unimplemented in batch path**: the documented `skip_column`/`skip_value` guard is `pass  # TODO`; `rows_skipped` is always 0; rows a third party marked processed get overwritten. The working single-row implementation (`_process_single_row`, `_should_skip`) is dead code. | `backend/app/services/runner.py:784-788`, `927-1030` |
| C4 | **Full-read SSRF**: `/preview-fields-standalone` fetches any caller-supplied URL server-side and returns the body (`sample_response`). No scheme/host validation, no private-range blocking, no auth. Reaches cloud metadata (169.254.169.254), compose-local Redis, internal services. Saved tasks same issue: `endpoint_path` has zero URL validation. | `backend/app/api/v1/routes/column_mappings.py:466-551,298-394`, `backend/app/db/schemas/task.py:146` |
| C5 | **Secrets/PII in logs**: `fetch_json` logs all headers at INFO and an "Equivalent curl" with raw values for every non-`Authorization` header — custom API-key header names (`api_key_header` is configurable) are never masked. `runner.run_import` `print()`s sample flattened/mapped records (upstream PII) and SQL; `mapper.to_date` `print()`s every converted value per row. | `backend/app/services/api_connector.py:200-218,101`, `backend/app/services/runner.py:271-293,548-574`, `backend/app/services/mapper.py:115-134` |

### 1.2 High

| ID | Finding | Location |
|---|---|---|
| H1 | **No authentication/authorization** on any management endpoint (task CRUD, run trigger, connections incl. arbitrary-host `POST /connections/test`, schedules, backfill/replay). | all `backend/app/api/v1/routes/`, `backend/app/main.py` |
| H2 | **Redis unauthenticated and published on host `6379`**; broker + result backend → task injection/result reading from the network. | `docker-compose.yml:2-11` |
| H3 | **PUT /tasks/{id} wipes credentials**: full `TaskCreate.model_dump()` applied; unset secrets become `None` (wiping stored encrypted creds) or 422 via validators forcing secret re-entry on every edit; `upsert_enabled` etc. reset to defaults. | `backend/app/api/v1/routes/tasks.py:155-191`, `backend/app/db/schemas/task.py:141-199` |
| H4 | **connections.enc races**: API/worker/scheduler are separate processes sharing the file; non-atomic read-modify-write (`write_text`, no lock, no temp+rename). Crash mid-write → `_read_file` silently returns empty store (all connections vanish). | `backend/app/services/connection_storage.py:62-109` |
| H5 | **Batch error granularity contradicts "never stop on row errors"**: one bad row aborts the whole 500-row batch, counting all rows as errors; per-row path exists but unused. | `backend/app/services/runner.py:739-820` |
| H6 | **Bind/parse explosion**: existence SELECT builds 500-row OR-chains (defeats indexes); CASE UPDATE builds rows×(keys+cols) bind params (~10k binds per statement). | `backend/app/services/runner.py:747-762,823-924` |
| H7 | **Unbounded queries**: `get_task_stats` loads ALL runs into Python; `list_runs` does an N+1 `get_retry_info` query per row; run-detail returns entire `execution_logs`+`row_errors` uncapped. | `backend/app/api/v1/routes/tasks.py:480-524`, `runs.py:182-235,41-115` |
| H8 | **Retries retry everything + duplicate risk**: `autoretry_for=(Exception,)` retries permanent errors despite docs claiming discriminated retry; per-batch commits mean a mid-run failure + retry duplicates batches 1..n-1 for non-upsert tasks; no per-task concurrency lock; `on_task_failure` races on "most recent RUNNING run". | `backend/app/workers/tasks.py:82-133`, `runner.py:604-628` |

### 1.3 Medium

| ID | Finding | Location |
|---|---|---|
| M1 | Per-row `db.commit()` in `log_step`/`log_row_error` → thousands of SQLite commits per failing run. | `runner.py:1080-1111` |
| M2 | SQLite shared by 3 processes without WAL/`busy_timeout` → `database is locked` under concurrency. | `backend/app/db/session.py:15-27`, `docker-compose.yml` |
| M3 | **PG/MySQL destinations non-functional**: `psycopg2`/`pymysql` not in `requirements.txt`; write path is Oracle-specific (`TO_DATE`, double-quoted identifiers, uppercase skip-column lookup). Roadmap parity is larger than documented. | `connection_pool.py:71-78`, `backend/requirements.txt`, `runner.py:566,890,1021,1062` |
| M4 | SQL identifiers (`dest_table`, `upsert_keys`, `skip_column`) validated only at run time; injection-safe (regex-whitelisted) but fails mid-import instead of 422 at save. | `schemas/task.py:167-181`, `runner.py:504-523` |
| M5 | `HTTP_MAX_RESPONSE_MB` checked after full buffering → memory exhaustion possible; new `httpx.AsyncClient` per attempt (no connection reuse). | `api_connector.py:236-250` |
| M6 | Deprecated `@app.on_event("startup")`; `/docs`+`/openapi.json` exposed in all envs. | `main.py:35-52` |
| M7 | **Frontend bundle**: zero route-level code splitting (no `React.lazy`), unused deps `zustand`+`minimatch`, duplicate date libs (`date-fns` and `dayjs`); contradicts claude.md "<100KB / code splitting" claims. | `frontend/src/App.tsx`, `frontend/package.json` |
| M8 | Axios client has no timeout; Oracle `test_connection` probe has no connect timeout (can hang UI). | `frontend/src/api/client.ts:33-39`, `connection_pool.py:192-198` |
| M9 | Cursor watermark uses lexicographic `max()` — wrong for numeric-string cursors ("9" > "10") → permanent row skips/re-fetches. | `runner.py:423-441` |

### 1.4 Low / hygiene

| ID | Finding | Location |
|---|---|---|
| L1 | Dead modules: `connection_service.py` (fixed PBKDF2 salt, import-time instantiation) and `db/oracle_pool.py` — zero importers; delete. | `backend/app/services/connection_service.py`, `backend/app/db/oracle_pool.py` |
| L2 | Hardcoded `C:\oracle\instantclient_23_0` attempted on Linux; make env-configurable. | `connection_pool.py:36` |
| L3 | `build_connection_url` URL-encodes password but not username. | `connection_pool.py:62-76` |
| L4 | `SECRET_KEY="dev-secret"` default; `FRONTEND_URL` default port 3000 vs Vite 5173. | `core/config.py:32-33`, `main.py:12-25` |
| L5 | CI commits a plaintext Fernet fallback key; generate per-run instead. | `.github/workflows/ci.yml:44` |
| L6 | `alembic` installed but never run; schema drift for existing installs as columns are added. | `backend/alembic/`, `db/session.py:30-40` |

### 1.5 Documentation contradictions (fix alongside code)

1. `docs/code-health-final.md` claims lifespan migration — `main.py` still uses `on_event`.
2. Same doc claims "no SQL surface, all ORM binds" — runner builds raw (though bound + identifier-whitelisted) SQL.
3. Same doc references `/api/v1/auth/token` and `connection_service.py` usage that no longer exist.
4. README/claude.md "409+ tests passing" vs code-health "327 passed, 60 failed, 21 errors" — needs a fresh CI run to establish truth (unverifiable in this sandbox).
5. claude.md claims batch upsert fixed NULL-constraint violations — C2 shows the bulk path reintroduces them.
6. claude.md claims route code splitting / <100KB bundle — contradicted by M7.

### 1.6 Alignment with existing project goals

| Goal (README roadmap / claude.md next focus) | Dependency on these findings |
|---|---|
| PostgreSQL/MySQL parity | Requires M3 drivers **and** dialect-aware SQL; sequence after C2/C3 |
| Pagination strategies | Requires M5 streaming/size caps first |
| Incremental/delta sync (partial) | Requires M9 cursor typing + H8 retry/watermark interplay |
| Webhook/alerting | Natural follow-on to H8 (auto-pause exists, notification absent) |
| Pluggable transforms | Requires hoisting transform-rule parsing (P-task 2 below) |
| Task export/import | Requires H3 fix + auth (H1) before sharing definitions |

---

## Part 2 — Implementation Plan (v1.4)

### Step 0 — Submit this plan as a PR (execute first)
Run from the repo root (`/workspace/.../sessions/agent_13187963-...` is the repo checkout; remote `origin` = `github.com/badry-dev/IntakeGateway`, `gh` authenticated as `badry-dev`):

```bash
git checkout -b docs/v14-security-performance-plan
git add .kilo/plans/1787173270847-v14-security-perf-plan.md
git commit -m "docs: add v1.4 security & performance review and implementation plan"
git push -u origin docs/v14-security-performance-plan
gh pr create --base main --head docs/v14-security-performance-plan \
  --title "docs: v1.4 security & performance review + implementation plan" \
  --body "Adds the codebase security/performance review findings (critical: broken scheduler dispatch, bulk-update NULL corruption, unimplemented skip condition, SSRF via preview endpoints, secret leakage in logs) and the ordered v1.4 implementation plan. Documentation-only change; no code modified."
```

Constraints: commit **only** the plan file (verify with `git status` / `git diff --cached` before committing — do not stage anything else); do not force-push; report the resulting PR URL.

**Goal:** ship a correct, hardened v1.4: fix broken scheduling and upsert corruption, close the SSRF/log-leak/auth gaps, and remove the dominant per-row performance costs. Ordered so each phase is independently mergeable and testable.

**Constraints:** keep API shape stable except where noted (PUT tasks partial update is a deliberate contract change); no new infra services; Oracle stays the primary destination; Python 3.11 / FastAPI 0.115 / React 18 unchanged.

### Phase 0 — Repository hygiene (prerequisite cleanup)
1. Delete `backend/app/services/connection_service.py` and `backend/app/db/oracle_pool.py` (dead code, fixed-salt surface) [L1]. Verify no imports remain (`grep -r`).
2. Remove **all** `print()` statements from `runner.py`, `mapper.py`, `connection_service` (deleted), keeping `logger.debug` equivalents where useful [C5, P1]. Acceptance: `grep -rn "print(" backend/app` returns only docstring mentions.
3. Migrate `main.py` to `lifespan` context manager; gate `/docs`+`/openapi.json` behind `APP_ENV != "production"` [M6].
4. Replace committed CI Fernet fallback with a generated key step [L5].

### Phase 1 — Critical correctness (release blockers)
5. **Fix scheduler dispatch** [C1]: `scheduler.py:119` → `enqueue_run(task_id)`; on dispatch failure, increment `TaskSchedule.consecutive_failures` and log at ERROR — persist the counter in a **separate transaction after** the existing `rollback()` (the current `except` handler rolls back, which would discard an in-transaction increment). Add regression test asserting `run_import_task.delay` is invoked (mocked) when the job fires, and that the failure counter persists when `enqueue_run` raises.
6. **Fix bulk UPDATE NULL corruption** [C2]: add `ELSE <quoted col>` to every CASE; compute `update_cols` as a deterministic first-seen union of non-key columns across **all** rows (no first-row cap — a column present only in later rows must still be written). Tests: heterogeneous batch with `None` values asserts no NULL overwrite; batch where row 1 lacks a column present in row 2.
7. **Implement batch skip condition** [C3]: include `skip_column` in the batch SELECT; route matching rows to `to_skip` before building `to_update`; count into `results["skipped"]` and `TaskRun.rows_skipped`. Tests: existing row with skip value is not updated; stats reflect skipped count. Delete dead `_process_single_row` path or keep as Phase 2 fallback (see task 10).

### Phase 2 — Security hardening
8. **SSRF guards** [C4]:
   - Add `app/core/url_guard.py`: resolve URL host; reject non-http(s) schemes, loopback, link-local (169.254/16), RFC1918, and `::1`/`fc00::/7` unless host matches optional `ALLOWED_SOURCE_HOSTS` (comma-separated env setting, default empty).
   - Enforce at **connection time** (not only save-time) to close the DNS-rebinding gap: validate the resolved IP before connecting (or connect to the validated IP with correct Host/SNI), and set `follow_redirects=False` (or revalidate each redirect destination). Apply in `fetch_json` (single choke point) **and** in `oauth_token_service._post_token_request` (which uses its own `httpx.AsyncClient` and bypasses `fetch_json`), plus `TaskCreate`/`TaskUpdate` validators for `endpoint_path` and `oauth.token_url`.
   - `/preview-fields-standalone` auto-fetch: run through the same guard; return only derived field metadata (`fields`, `field_count`) — drop `sample_response` **and redact `FieldPreview.sample_value`/`flattened_response`** (they currently echo fetched source values) from the standalone response model (manual-paste mode keeps echoing user-supplied JSON).
   - Tests: blocked metadata URL, allowed public URL, allowlist override, DNS-rebinding, redirect-to-private, and OAuth token URL.
9. **Log redaction** [C5]: in `fetch_json`, mask any header matching a secret-name set (`authorization`, `*api*key*`, `*token*`, `x-auth*`, case-insensitive) instead of only `Authorization`/`X-API-Key`; fix the curl builder to mask the same set **and redact URL query parameters, JSON request bodies, and error response excerpts** (the curl log currently embeds params/body raw, and error bodies are logged verbatim); downgrade header logging to DEBUG with masked copy only.
10. **Token auth for the API** [H1]: add a FastAPI dependency checking `X-API-Key` (or `Authorization: Bearer`) against env `API_TOKEN` when set; if unset and `APP_ENV == "production"`, refuse startup with a clear error (fail-closed); dev keeps open access with a startup warning. Attach it as a **real dependency** — `FastAPI(dependencies=[...])` or per-router `dependencies=[...]` on every mounted router incl. `oracle_router` (NOT `app.dependency_overrides`, which only replaces existing dependencies and would leave routes unauthenticated). Document that the shared token authenticates the API but provides no per-user authorization.
11. **Redis auth + un-publish port** [H2]: compose Redis drops `ports`, gains `command: redis-server --requirepass ${REDIS_PASSWORD}`; update the healthcheck to authenticate (`redis-cli -a $REDIS_PASSWORD ping` or `REDISCLI_AUTH`) so `service_healthy` still passes; update `.env.example` (`REDIS_URL=redis://:password@redis:6379/0`).
12. **Partial task update** [H3]: new `TaskUpdate` schema (all optional, `model_dump(exclude_unset=True)`); secrets omitted → preserved; secret fields present but empty string → explicit clear. Switch `PUT /tasks/{task_id}` to it. Tests: update name only → api_key unchanged; auth_type change without secret → 422.
13. **Atomic connections file** [H4]: write to temp file + `os.replace`; `filelock` (or `fcntl.flock` guarded for Windows) around read-modify-write; corrupt-file path logs ERROR and preserves `.bak` instead of silently returning empty. Tests: concurrent write simulation, corrupt file behavior.

### Phase 3 — Performance & reliability
14. **Hoist transform parsing** [perf P2]: in `map_rows`, pre-parse each mapping's `transform_rules` JSON once into callable lists; `apply_transforms` accepts pre-parsed rules. Benchmark target: mapping stage for 10k rows × 20 mappings measurably faster (assert relative timing in a micro-benchmark test, or simple call-count test that `json.loads` is called once per mapping).
15. **Batched run logging** [M1]: `log_row_error` collects into a list; single `db.bulk_save_objects`/`add_all` + one commit per pipeline stage; `log_step` commits only at stage boundaries.
16. **SQLite concurrency** [M2]: on engine creation for sqlite URLs, set `PRAGMA journal_mode=WAL` and `busy_timeout=5000` via SQLAlchemy event listener; keep Postgres path unchanged.
17. **Bound the read endpoints** [H7]: stats via SQL aggregates (`func.count/sum/avg` over `TaskRun`), no full-row loads; `list_runs` computes `is_retry` in one query (subquery/lag emulation) instead of N+1; run-detail caps `row_errors` (first 500 + `row_errors_total`) and paginates `execution_logs` if >200. Update `TaskRunOut` accordingly.
18. **Batch fallback on failure** [H5]: in `_process_upsert_batch`, on exception roll back to a savepoint (or restore pre-batch state) before falling back to row-by-row processing for that batch only (revive `_process_single_row` with the fixed skip logic), so a partially-applied bulk statement is never replayed; define the commit boundary so the batch commits exactly once. Preserve per-row error attribution and the "never stop" contract; add a partial-failure test asserting no duplicate/inconsistent writes.
19. **Config-time identifier validation** [M4]: apply `_SAFE_IDENTIFIER_RE`-style validators to `dest_table`, `upsert_keys` entries, `skip_column` in `TaskCreate`/`TaskUpdate` (keep runtime guards as defense-in-depth).

### Phase 4 — Next-version candidates (after P0-P3 merge; include if scope allows)
20. **Native upsert** [H6, enables roadmap parity]: dialect-aware writer — Oracle `MERGE` + `executemany`, PG `INSERT ... ON CONFLICT`, MySQL `ON DUPLICATE KEY UPDATE`; removes pre-SELECT and CASE binds; folds in M3 driver additions (`psycopg2`, `pymysql` in requirements) and de-Oracle-izes `TO_DATE`/quoting via a small dialect module. Until this lands, gate the Settings UI `db_type` choices to `oracle`.
21. **Retry classification + run lock** [H8]: split retryable (network/5xx/broker) from permanent exceptions; per-task Redis lock (`SET NX EX`) preventing overlapping runs; store `retry_of_run_id` at creation instead of inferring.
22. **Streaming fetch with cap** [M5]: `client.stream()` + incremental size check, abort over `HTTP_MAX_RESPONSE_MB`; reuse one client per run.
23. **Frontend bundle** [M7, M8]: route-level `React.lazy`+`Suspense`; drop `zustand`/`minimatch`; consolidate `date-fns`→`dayjs`; axios default timeout 30s. Verify with `vite build` chunk report.
24. **Webhook alerting** (roadmap #4): task-level webhook URL (encrypted), fired on FAILED/auto-pause with run summary payload.
25. **Cursor typing** [M9]: optional `cursor_type` (`numeric`/`iso_date`/`opaque`) in cursor config; typed comparison in `_max_cursor`.

### Failure modes & risks
- **Task 8 (SSRF guard)** may break legitimate internal-source deployments → the `ALLOWED_SOURCE_HOSTS` escape hatch is mandatory, documented in `.env.example`.
- **Task 10 (API token)** breaks existing automation on upgrade → default dev behavior unchanged; production fail-closed announced in release notes.
- **Tasks 6/7/18 (upsert path)** carry regression risk on the hottest code path → every change lands with unit tests against an in-memory SQLite destination where possible, plus the existing integration suite.
- **Task 17 response shape change** (`row_errors_total`) requires frontend RunDetail update in the same PR.
- Retry semantics change (task 21) can leave previously-retried scenarios un-retried — intentional; document.

### Validation plan
- Backend: `cd backend && pytest tests/ -v` must pass; add/extend: `test_scheduler.py` (dispatch), `test_runner_upsert_batch.py` (NULL preservation, skip counts, heterogeneous batches, fallback path), `test_url_guard.py`, `test_tasks_partial_update.py`, `test_connection_storage_atomic.py`, stats/aggregation tests. Batch-upsert SQL emits Oracle `TO_DATE(...)` and quoted identifiers, which SQLite cannot execute — keep SQLite only for dialect-independent batching logic and add Oracle-compatible integration/SQL-execution tests for C2/C3 and the fallback path (mixed NULLs, date conversion, quoted identifiers, skip behavior).
- Frontend: `cd frontend && npm test` and `npm run build` (chunk report for task 23).
- Lint/type: `ruff check app/ tests/` + `ruff format --check`, `npx tsc --noEmit`.
- Manual smoke (docker compose): create scheduled task → verify run fires; trigger 10k-row upsert with mixed None values → verify no NULL overwrites and skipped counts; preview-fields against `http://169.254.169.254/` → blocked. Auth: production startup with `API_TOKEN` unset → refuses to start (fail-closed); with `API_TOKEN` set, a request with missing/invalid token → 401.
- Establish true test-suite baseline (resolve docs contradiction 1.5.4) and update `claude.md`/`code-health` claims accordingly.

### Migration/rollout notes
- Existing installs: require an Alembic `upgrade head` procedure (L6) — `init_app_database()` currently only calls `create_all`, so existing DBs never receive new columns; add upgrade/downgrade tests, and add a `retry_of_run_id` migration if Phase 4 task 21 lands. Connections file format unchanged (atomic write is transparent).
- `.env.example` additions: `API_TOKEN`, `REDIS_PASSWORD`, `ALLOWED_SOURCE_HOSTS`, `ORACLE_CLIENT_LIB_DIR` (L2).
- Sequence: Phase 0 → 1 → 2 are independent PRs; Phase 3 tasks merge independently; Phase 4 items are separate PRs and individually optional.

### Open questions (explicitly out of scope for v1.4)
- Full user authentication / RBAC (JWT) — superseded for now by task 10's shared token.
- KMS/HSM-managed encryption keys and key-rotation runbook (only single-env `ENCRYPTION_KEY` today).
- Multi-instance/HA deployment (needs Postgres app DB + shared connections store in DB instead of file).
- OAuth `authorization_code` grant (PKCE) — flagged in `oauth_token_service.py` docstring already.
