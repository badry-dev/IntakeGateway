<div align="center">

# 🛰️ IntakeGateway

### Turn any HTTP API into a managed, scheduled pipeline into your database — no glue code required.

Define a source API, map its fields to your table, pick a schedule, and let IntakeGateway handle fetching, transforming, upserting, retrying, and monitoring. All from a clean web UI.

[![CI](https://github.com/Badry-Kudu/IntakeGateway/actions/workflows/ci.yml/badge.svg)](https://github.com/Badry-Kudu/IntakeGateway/actions/workflows/ci.yml)
[![License: GPLv3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE.txt)
[![Python 3.11](https://img.shields.io/badge/python-3.11-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![React 18](https://img.shields.io/badge/react-18-61DAFB.svg?logo=react&logoColor=black)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](#-contributing)

[Why?](#-why-intakegateway) • [Features](#-features) • [How it works](#-how-it-works) • [Quick start](#-quick-start) • [Roadmap](#-roadmap) • [Contributing](#-contributing)

</div>

---

## 💡 Why IntakeGateway?

Almost every team eventually needs to pull data *out* of some third-party REST API and land it *into* a database — a CRM export, a payments feed, an inventory endpoint, a partner integration. The usual answer is a one-off script: a cron job, a fragile `requests` loop, hand-written SQL, no retries, no visibility, and a pager that goes off when the API changes its date format.

**IntakeGateway replaces that pile of scripts with a single, observable application.** You configure an import once through a guided wizard, and you get scheduling, field mapping, insert/upsert/skip logic, encrypted credential storage, run history, and row-level error reporting out of the box.

It's built for:

- **Data & platform engineers** who want a repeatable way to onboard new API sources without writing a new ingestion script each time.
- **Backend teams** that need a self-hosted, auditable alternative to a SaaS ETL tool for moving API data into Oracle/Postgres/MySQL.
- **Anyone** tired of debugging a cron-driven `curl | python | sqlplus` pipeline at 2 a.m.

> **Self-hosted by design.** Your API credentials and destination connections never leave your infrastructure — they're stored encrypted on disk, and the app keeps its own state in a local SQLite database.

---

## ✨ Features

| | Feature | What it does for you |
|---|---|---|
| 🧭 | **Guided task wizard** | Define a full import — endpoint, headers, auth, mapping — in a 6-step form. No config files. |
| 🔐 | **Flexible authentication** | Bearer token, API Key, HTTP Basic, or OAuth for talking to source APIs. |
| 🗺️ | **Smart column mapping** | Map API fields (including **nested JSON**) to destination columns, with automatic transform suggestions based on column types. |
| ⏰ | **Cron scheduling** | Recurring imports on any cron expression, with **auto-pause** after consecutive failures so a broken source doesn't hammer your DB. |
| 🔁 | **Upsert & skip logic** | Insert-or-update on configurable unique keys, plus skip conditions to ignore already-processed rows. |
| ⚡ | **Batched bulk writes** | Upserts are processed in batches with bulk SQL — **200–300× faster** than row-by-row (10k rows in seconds, not minutes). |
| 🗄️ | **Multi-database destinations** | Oracle, PostgreSQL, and MySQL. Save, **test**, and activate connections at runtime with encrypted credentials. |
| 📊 | **Full observability** | Dashboard KPIs, run history, execution logs, and a **row-level error breakdown** so you know exactly which records failed and why. |
| 🛟 | **Fails gracefully** | The UI and API stay fully operational even when no destination database is configured or reachable. |

---

## 🧭 A quick tour

A typical workflow takes a couple of minutes end to end:

1. **Create a task** → point it at `https://api.example.com/v1/orders` and choose your auth method.
2. **Preview & map fields** → IntakeGateway fetches a sample, flattens the JSON, and you drag each field onto a destination column. It even suggests transforms (e.g. string → date).
3. **Configure upsert** → pick `order_id` as the unique key so re-runs update instead of duplicate.
4. **Schedule it** → `0 * * * *` to sync hourly. Done.
5. **Watch it run** → the dashboard shows successes, failures, durations, and per-row errors in real time.

The app ships with **eight pages** — Dashboard, Tasks, Task Wizard, Task Detail, Runs, Run Detail, Schedules, and Settings — built with Ant Design.

<!--
📸 Screenshots welcome! Drop UI captures or a short demo GIF into a docs/assets/ folder
   and embed them here, e.g.:
   ![Dashboard](docs/assets/dashboard.png)
-->

---

## 🏗️ How it works

```
User Browser
    │
    ▼
React Frontend (port 5173)
    │  HTTP
    ▼
FastAPI Backend (port 8000)
    │                    │
    ▼                    ▼
Local SQLite DB      Celery + Redis
(app state)          (async execution)
                         │
                         ▼
                  Destination Database
                  (Oracle / PostgreSQL / MySQL)
```

The execution pipeline is straightforward: **fetch → normalize → validate → map → insert/upsert**. The `Runner` service orchestrates it; `ApiConnector` handles auth and fetching, `Normalizer` flattens nested JSON, `Validator` checks against the destination schema, and `Mapper` applies transforms before the batched write.

App-owned state (tasks, runs, schedules, mappings, logs) lives in a local SQLite database by default, so there are no external dependencies just to run the UI. Destination DB access is fully isolated — broken destination connectivity never takes down core app routes. Destination connections are stored in an encrypted file (`connections.enc`) and managed at runtime from the Settings page.

---

## 🚀 Quick start

### Prerequisites
- Node.js 18+
- Python 3.11+
- Redis
- *Optional:* Oracle / PostgreSQL / MySQL access for destination ingestion

### 1. Configure environment

```bash
cp .env.example .env
# Set ENCRYPTION_KEY to a valid Fernet key:
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 2. Start the backend

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

- API → **http://localhost:8000**
- Interactive docs (Swagger) → **http://localhost:8000/docs**

The backend auto-creates `intakegateway_app.db` for app state. A destination database is optional at startup.

### 3. Start the frontend

```bash
cd frontend
npm install
npm run dev          # UI → http://localhost:5173
```

### 4. Start the Celery worker (runs tasks)

```bash
cd backend
celery -A app.workers.celery_app.celery_app worker --loglevel=INFO --pool=solo --concurrency=1
```

> On Windows, keep `--pool=solo --concurrency=1`. Celery's default prefork pool can fail with Windows handle permission errors from billiard multiprocessing.

### 🐳 Docker (alternative)

```bash
cp .env.example .env   # configure first
docker compose up --build
```

Starts the backend API (port 8000), Celery worker, scheduler, and Redis. Run the frontend separately with `npm run dev`. Redis and the API expose healthchecks; the worker and scheduler wait for Redis via `depends_on: condition: service_healthy`.

### ✅ Run the tests

```bash
cd backend && pytest tests/ -v     # backend
cd frontend && npm test            # frontend
```

---

## 🛠️ Tech stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18.2 + TypeScript 5.3 (strict), Vite 5, Ant Design 5, React Router v6, React Query 5 (TanStack) |
| **Backend** | Python 3.11, FastAPI 0.115, SQLAlchemy 2.0, Pydantic v2 |
| **Async / queue** | Celery 5.4 + Redis |
| **Scheduling** | APScheduler 3.10 + croniter |
| **Security** | `cryptography` (Fernet) for encrypted credential storage |
| **App state** | SQLite (via `APP_DATABASE_URL`) |
| **Destinations** | Oracle (current target), PostgreSQL, MySQL |
| **Testing** | pytest (409+ cases), Vitest + React Testing Library (60+ cases) |

---

## 📚 API reference

Full interactive documentation is generated by FastAPI at **http://localhost:8000/docs** when the backend is running. The main endpoint groups:

| Group | Base path | Highlights |
|-------|-----------|-----------|
| Tasks | `/api/v1/tasks` | CRUD + `POST /{id}/run` to trigger execution |
| Runs | `/api/v1/runs` | List and inspect run history |
| Schedules | `/api/v1/schedules` | Cron schedule management |
| Column Mappings | `/api/v1/tasks/{id}/mappings` | Mapping CRUD + field preview |
| Connections | `/api/v1/connections` | Create, **test**, and activate destination DBs |

---

## 🔧 Configuration

See [`.env.example`](.env.example) for the full reference. Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_DATABASE_URL` | `sqlite:///./intakegateway_app.db` | Local app state database |
| `ENCRYPTION_KEY` | *(required)* | Fernet key for credential encryption |
| `CONNECTIONS_FILE_PATH` | `connections.enc` | Encrypted destination connections file |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis URL for Celery |
| `FRONTEND_URL` | `http://localhost:5173` | CORS allow-origin for the UI |
| `LOG_LEVEL` | `INFO` | Application log verbosity |

---

## 🗺️ Roadmap

IntakeGateway is open source and actively evolving. Ideas on the table (contributions and votes welcome via [issues](https://github.com/Badry-Kudu/IntakeGateway/issues)):

- [ ] First-class PostgreSQL & MySQL destination parity with Oracle
- [ ] Pagination strategies for source APIs (cursor / offset / link-header)
- [ ] Incremental / delta sync based on a watermark column
- [ ] Webhook & alerting on run failure
- [ ] Pluggable transforms and custom mapping functions
- [ ] Export / import of task definitions as JSON

> Have a use case we haven't listed? [Open an issue](https://github.com/Badry-Kudu/IntakeGateway/issues/new) — we'd love to hear it.

---

## 🤝 Contributing

Contributions of all kinds are welcome — bug reports, feature ideas, docs, and code.

1. Fork the repo and create a feature branch.
2. Follow the conventions: TypeScript strict mode, Python type hints, and tests for new functionality.
3. Make sure everything passes: `pytest tests/ -v` and `npm test`.
4. Keep commits atomic and descriptive, and update docs for any API or behaviour change.
5. Open a pull request — describe the *why*, not just the *what*.

New to the project? Issues labelled **`good first issue`** are a great place to start.

If you find IntakeGateway useful, please consider **⭐ starring the repo** — it genuinely helps others discover it.

---

## 📁 Project structure

```
IntakeGateway/
├── backend/                    # FastAPI application
│   ├── app/
│   │   ├── api/v1/routes/      # REST endpoints (tasks, runs, schedules, connections, mappings)
│   │   ├── services/           # Business logic (runner, api_connector, mapper, validator, …)
│   │   ├── db/                 # App DB models, schemas, cross-database types
│   │   ├── workers/            # Celery task queue
│   │   └── core/               # Config, encryption, logging
│   └── tests/                  # Unit + integration tests
├── frontend/                   # React + Ant Design app
│   └── src/
│       ├── pages/              # 8 page components
│       ├── components/         # Editor components (Mapping, Connection, Schedule, Upsert)
│       ├── hooks/api.ts        # React Query hooks
│       └── api/client.ts       # Axios HTTP client
├── docker-compose.yml          # Multi-container setup
├── Makefile                    # Convenience commands
└── DOCUMENTATION_INDEX.md      # Full documentation index
```

---

## 📄 License

Licensed under the **GNU General Public License v3.0** — see [LICENSE.txt](LICENSE.txt).

<div align="center">
<sub>Built with FastAPI, React, and Celery. If this saved you from writing one more ingestion script, give it a ⭐.</sub>
</div>
