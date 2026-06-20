# IntakeGateway

Import data from any HTTP API into your database, with scheduling, field mapping, upsert logic, and run-level observability.

[![CI](https://github.com/Badry-Kudu/IntakeGateway/actions/workflows/ci.yml/badge.svg)](https://github.com/Badry-Kudu/IntakeGateway/actions/workflows/ci.yml)
[![License: GPLv3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE.txt)
[![Python 3.11](https://img.shields.io/badge/python-3.11-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![React 18](https://img.shields.io/badge/react-18-61DAFB.svg?logo=react&logoColor=black)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)

IntakeGateway is a self-hosted, full-stack web application for moving data from external REST APIs into a relational database. You define a source endpoint, map its response fields to destination columns, choose a schedule, and the application handles fetching, transforming, upserting, retrying, and monitoring. Configuration is done through a web UI rather than code.

The application keeps its own state in a local SQLite database, so the UI and API remain fully operational even when no destination database is configured.

## Contents

- [Why IntakeGateway](#why-intakegateway)
- [Features](#features)
- [How it works](#how-it-works)
- [Quick start](#quick-start)
- [Technology stack](#technology-stack)
- [API reference](#api-reference)
- [Configuration](#configuration)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Project structure](#project-structure)
- [License](#license)

## Why IntakeGateway

Teams regularly need to pull data out of a third-party REST API and load it into a database: a CRM export, a payments feed, an inventory endpoint, a partner integration. The common approach is a one-off script driven by cron, with hand-written SQL, little error handling, and no visibility into what ran or why it failed.

IntakeGateway replaces that pattern with a single, observable application. An import is configured once through a guided wizard and then provides scheduling, field mapping, insert/upsert/skip logic, encrypted credential storage, run history, and row-level error reporting.

It is intended for:

- Data and platform engineers who want a repeatable way to onboard new API sources without writing a new ingestion script each time.
- Backend teams that need a self-hosted, auditable alternative to a hosted ETL service for moving API data into Oracle, PostgreSQL, or MySQL.
- Anyone maintaining cron-driven ingestion scripts who wants scheduling and monitoring without building them by hand.

API credentials and destination connections stay on your own infrastructure. They are stored encrypted on disk, and the application keeps its operational state in a local SQLite database.

## Features

| Feature | Description |
|---|---|
| Guided task wizard | Define an import (endpoint, headers, auth, mapping) through a six-step form. No config files. |
| Flexible authentication | Bearer token, API key, HTTP Basic, or OAuth for source APIs. |
| Column mapping | Map API fields, including nested JSON, to destination columns, with transform suggestions based on column types. |
| Cron scheduling | Recurring imports on any cron expression, with automatic pause after consecutive failures. |
| Upsert and skip logic | Insert-or-update on configurable unique keys, plus skip conditions for already-processed rows. |
| Batched bulk writes | Upserts are processed in batches with bulk SQL rather than row by row, which reduces query volume substantially on large imports. |
| Multiple destinations | Oracle, PostgreSQL, and MySQL. Connections can be saved, tested, and activated at runtime with encrypted credentials. |
| Observability | Dashboard metrics, run history, execution logs, and a row-level error breakdown. |
| Graceful degradation | The UI and API stay operational even when no destination database is configured or reachable. |

A typical workflow:

1. Create a task and point it at a source endpoint, then choose an authentication method.
2. Preview and map fields. IntakeGateway fetches a sample, flattens the JSON, and lets you assign each field to a destination column, suggesting transforms such as string to date.
3. Configure upsert, for example using `order_id` as the unique key so re-runs update existing records instead of duplicating them.
4. Add a schedule, such as `0 * * * *` for an hourly sync.
5. Monitor runs from the dashboard, which shows successes, failures, durations, and per-row errors.

The application ships with eight pages: Dashboard, Tasks, Task Wizard, Task Detail, Runs, Run Detail, Schedules, and Settings.

## How it works

```text
User Browser
    |
    v
React Frontend (port 5173)
    |  HTTP
    v
FastAPI Backend (port 8000)
    |                    |
    v                    v
Local SQLite DB      Celery + Redis
(app state)          (async execution)
                         |
                         v
                  Destination Database
                  (Oracle / PostgreSQL / MySQL)
```

The execution pipeline is fetch, normalize, validate, map, then insert or upsert. The `Runner` service orchestrates it: `ApiConnector` handles authentication and fetching, `Normalizer` flattens nested JSON, `Validator` checks data against the destination schema, and `Mapper` applies transforms before the batched write.

Application state (tasks, runs, schedules, mappings, logs) lives in a local SQLite database by default, so no external service is required just to run the UI. Destination database access is isolated, so broken destination connectivity does not take down core application routes. Destination connections are stored in an encrypted file (`connections.enc`) and managed at runtime from the Settings page.

## Quick start

### Prerequisites

- Node.js 18 or later
- Python 3.11 or later
- Redis
- Optional: Oracle, PostgreSQL, or MySQL access for destination ingestion

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

- API: http://localhost:8000
- Interactive docs (Swagger): http://localhost:8000/docs

The backend creates `intakegateway_app.db` for application state on first run. A destination database is optional at startup.

### 3. Start the frontend

```bash
cd frontend
npm install
npm run dev          # UI: http://localhost:5173
```

### 4. Start the Celery worker

```bash
cd backend
celery -A app.workers.celery_app.celery_app worker --loglevel=INFO --pool=solo --concurrency=1
```

On Windows, keep `--pool=solo --concurrency=1`. Celery's default prefork pool can fail with Windows handle permission errors from billiard multiprocessing.

### Docker

```bash
cp .env.example .env   # configure first
docker compose up --build
```

This starts the backend API (port 8000), Celery worker, scheduler, and Redis. Run the frontend separately with `npm run dev`. Redis and the API expose health checks; the worker and scheduler wait for Redis via `depends_on: condition: service_healthy`.

### Run the tests

```bash
cd backend && pytest tests/ -v     # backend
cd frontend && npm test            # frontend
```

## Technology stack

| Layer | Technology |
|---|---|
| Frontend | React 18.2, TypeScript 5.3 (strict), Vite 5, Ant Design 5, React Router v6, React Query 5 (TanStack) |
| Backend | Python 3.11, FastAPI 0.115, SQLAlchemy 2.0, Pydantic v2 |
| Async and queue | Celery 5.4, Redis |
| Scheduling | APScheduler 3.10, croniter |
| Security | cryptography (Fernet) for encrypted credential storage |
| Application state | SQLite (via `APP_DATABASE_URL`) |
| Destinations | Oracle (current target), PostgreSQL, MySQL |
| Testing | pytest (409+ cases), Vitest with React Testing Library (60+ cases) |

## API reference

Interactive documentation is generated by FastAPI at http://localhost:8000/docs when the backend is running. The main endpoint groups:

| Group | Base path | Notes |
|---|---|---|
| Tasks | `/api/v1/tasks` | CRUD plus `POST /{id}/run` to trigger execution |
| Runs | `/api/v1/runs` | List and inspect run history |
| Schedules | `/api/v1/schedules` | Cron schedule management |
| Column Mappings | `/api/v1/tasks/{id}/mappings` | Mapping CRUD and field preview |
| Connections | `/api/v1/connections` | Create, test, and activate destination databases |

## Configuration

See [`.env.example`](.env.example) for the full reference. Key variables:

| Variable | Default | Description |
|---|---|---|
| `APP_DATABASE_URL` | `sqlite:///./intakegateway_app.db` | Local application state database |
| `ENCRYPTION_KEY` | (required) | Fernet key for credential encryption |
| `CONNECTIONS_FILE_PATH` | `connections.enc` | Encrypted destination connections file |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis URL for Celery |
| `FRONTEND_URL` | `http://localhost:5173` | CORS allow-origin for the UI |
| `APP_LOG_LEVEL` | `INFO` | Application log verbosity |

## Roadmap

Items under consideration. Contributions and feedback are welcome through [issues](https://github.com/Badry-Kudu/IntakeGateway/issues).

- First-class PostgreSQL and MySQL destination parity with Oracle
- Pagination strategies for source APIs (cursor, offset, link header)
- Incremental and delta sync based on a watermark column
- Webhook and alerting on run failure
- Pluggable transforms and custom mapping functions
- Export and import of task definitions as JSON

## Contributing

Contributions are welcome, including bug reports, feature requests, documentation, and code.

1. Fork the repository and create a feature branch.
2. Follow the project conventions: TypeScript strict mode, Python type hints, and tests for new functionality.
3. Confirm the test suites pass: `pytest tests/ -v` and `npm test`.
4. Keep commits focused and descriptive, and update documentation for any API or behavior change.
5. Open a pull request describing the motivation for the change, not only the implementation.

Issues labelled `good first issue` are a reasonable place to start.

## Project structure

```text
IntakeGateway/
├── backend/                    # FastAPI application
│   ├── app/
│   │   ├── api/v1/routes/      # REST endpoints (tasks, runs, schedules, connections, mappings)
│   │   ├── services/           # Business logic (runner, api_connector, mapper, validator, ...)
│   │   ├── db/                 # App DB models, schemas, cross-database types
│   │   ├── workers/            # Celery task queue
│   │   └── core/               # Config, encryption, logging
│   └── tests/                  # Unit and integration tests
├── frontend/                   # React + Ant Design app
│   └── src/
│       ├── pages/              # Page components
│       ├── components/         # Editor components (Mapping, Connection, Schedule, Upsert)
│       ├── hooks/api.ts        # React Query hooks
│       └── api/client.ts       # Axios HTTP client
├── docker-compose.yml          # Multi-container setup
├── Makefile                    # Convenience commands
└── DOCUMENTATION_INDEX.md      # Documentation index
```

## License

Licensed under the GNU General Public License v3.0. See [LICENSE.txt](LICENSE.txt).
