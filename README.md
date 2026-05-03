# IntakeGateway

> Import data from any HTTP API into your database — with scheduling, transforms, upsert logic, and full observability.

**Version**: 0.2.0 | **Status**: Production Ready | **Health Score**: 73 / 100

IntakeGateway is a full-stack web application that lets you define, schedule, and monitor data import tasks. It fetches records from external REST APIs, maps fields to destination database columns, and loads them with configurable insert/upsert/skip logic. The app stores its own state in a local SQLite database, so the UI and API remain fully operational even when no destination database is configured.

---

## Features

- **Task Management** — Create and manage API import tasks with a 6-step wizard
- **Flexible Authentication** — Bearer token, API Key, HTTP Basic, or OAuth for external APIs
- **Column Mapping** — Map API response fields (including nested JSON) to destination columns with transform suggestions
- **Scheduling** — Cron-based recurring imports with auto-pause on consecutive failures
- **Upsert & Skip Logic** — Insert-or-update with configurable unique keys and skip conditions for already-processed rows
- **Connection Management** — Save, test, and activate destination DB connections (Oracle, PostgreSQL, MySQL) with encrypted credentials
- **Monitoring** — Run history, row-level error breakdown, logs, and dashboard statistics

---

## Architecture

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

App-owned state (tasks, runs, schedules, mappings, logs) lives in a local SQLite database by default. Destination DB access is isolated — the backend and UI work fully even when no destination connection is configured. Destination connections are stored in an encrypted file (`connections.enc`) and can be managed at runtime through the Settings page.

---

## Technology Stack

### Frontend
- **React 18.2** with **TypeScript 5.3** (strict mode)
- **Vite 5.0** development environment with HMR
- **Ant Design 5** UI component library
- **@ant-design/icons** for iconography
- **React Router v6** for routing (8 routes)
- **React Query 5.28** (TanStack Query) for server state management
- **dayjs** for date handling
- **Vitest** + **React Testing Library** for testing (14 test files)

### Backend
- **Python 3.11** with **FastAPI 0.115**
- **SQLAlchemy 2.0** ORM for database operations
- **SQLite** for local app state via `APP_DATABASE_URL`
- **Celery 5.4** with Redis for async task execution
- **APScheduler 3.10** for cron-based scheduling
- **Pydantic v2** for data validation
- **cryptography 46.0.7** for encrypted credential storage
- **pytest** for testing (409+ test cases)
- **Oracle Database** as the current ingestion destination

---

## Project Metrics

| Metric | Backend | Frontend | Total |
|--------|---------|----------|-------|
| **Lines of Code** | 2,500+ | 2,600+ | 5,100+ |
| **Test Files** | 11 | 14 | 25 |
| **Test Cases** | 409+ | 60+ | 469+ |
| **Components/Services** | 8 services | 12 components | 20 |
| **Routes/Endpoints** | 15+ | 8 | 23+ |
| **TypeScript Coverage** | N/A | 100% | - |

---

## Quick Start

### Prerequisites
- Node.js 18+
- Python 3.11+
- Redis
- Optional: Oracle / PostgreSQL / MySQL access for destination ingestion

### 1. Copy environment config

```bash
cp .env.example .env
# Edit .env and set ENCRYPTION_KEY to a valid Fernet key:
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 2. Start the backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

- API: **http://localhost:8000**
- Interactive docs: **http://localhost:8000/docs**

The backend automatically creates `intakegateway_app.db` for app state. Destination database settings are optional at startup.

### 3. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

UI available at: **http://localhost:5173**

### 4. Start the Celery worker (for task execution)

```bash
cd backend
celery -A app.workers.celery_app.celery_app worker --loglevel=INFO
```

### Docker (alternative)

```bash
cp .env.example .env  # configure .env first
docker compose up --build
```

Starts the backend API (port 8000), Celery worker, scheduler, and Redis. Run the frontend separately with `npm run dev`.

The `redis` and `api` services have healthchecks configured; `worker` and `scheduler` use `depends_on: condition: service_healthy` on Redis so they start only after Redis is ready. The `api` healthcheck uses the Python standard library (`urllib.request`) — no `curl` required in the image.

### Run Tests

```bash
# Backend
cd backend && pytest tests/ -v

# Frontend
cd frontend && npm test
```

---

## Project Structure

```
IntakeGateway/
├── backend/                    # FastAPI application
│   ├── app/
│   │   ├── api/v1/routes/     # REST endpoints (tasks, runs, schedules, connections, mappings)
│   │   ├── services/          # Business logic (runner, api_connector, mapper, validator, etc.)
│   │   ├── db/                # App DB models, schemas, and cross-database types
│   │   ├── workers/           # Celery task queue configuration
│   │   └── core/              # Config, encryption, logging
│   └── tests/                 # Unit + integration tests (409+ cases)
│
├── frontend/                   # React application (Ant Design)
│   ├── src/
│   │   ├── pages/            # 8 page components
│   │   ├── components/       # 4 editor components (ColumnMapping, Connection, Schedule, Upsert)
│   │   ├── hooks/            # React Query hooks (api.ts)
│   │   ├── api/              # Axios HTTP client (client.ts)
│   │   ├── types/            # TypeScript interfaces
│   │   ├── __tests__/        # 14 test files
│   │   ├── theme.ts          # Ant Design theme configuration
│   │   └── App.tsx           # Routing + AntD Layout
│   └── package.json
│
├── docker-compose.yml         # Multi-container setup
├── Makefile                   # Convenience commands
├── DOCUMENTATION_INDEX.md     # Documentation index
└── README.md                  # This file
```

---

## API Endpoints

### Task Management
```
GET    /api/v1/tasks              # List all tasks (paginated)
GET    /api/v1/tasks/{task_id}    # Get task details
POST   /api/v1/tasks              # Create new task
PUT    /api/v1/tasks/{task_id}    # Update task
DELETE /api/v1/tasks/{task_id}    # Delete task
POST   /api/v1/tasks/{task_id}/run # Trigger task execution
```

### Run Management
```
GET    /api/v1/runs               # List recent runs
GET    /api/v1/runs/{run_id}      # Get run details
```

### Schedule Management
```
GET    /api/v1/schedules          # List all schedules
POST   /api/v1/tasks/{task_id}/schedule  # Create schedule
PUT    /api/v1/schedules/{id}     # Update schedule
DELETE /api/v1/schedules/{id}     # Delete schedule
```

### Column Mappings
```
GET    /api/v1/tasks/{task_id}/mappings         # Get mappings
POST   /api/v1/tasks/{task_id}/mappings         # Create mappings
POST   /api/v1/tasks/{task_id}/preview-fields   # Preview API fields
POST   /api/v1/tasks/preview-fields-standalone  # Preview fields (wizard)
```

### Database Connections
```
GET    /api/v1/connections        # List connections
POST   /api/v1/connections        # Create connection
PUT    /api/v1/connections/{id}   # Update connection
DELETE /api/v1/connections/{id}   # Delete connection
POST   /api/v1/connections/test   # Test connection
POST   /api/v1/connections/{id}/activate  # Set active connection
```

---

## Frontend Features

### Pages
- **Dashboard** - KPI cards (running, succeeded, failed, total), recent runs table, quick actions
- **Tasks** - Card-based task list with run/edit/delete actions, schedule indicators
- **Task Wizard** - 6-step form (Basic Info, Endpoint, Headers, Auth, Mapping, Review)
- **Task Detail** - Tabbed view (Details, Schedule, Column Mappings) with edit/delete
- **Runs List** - Table with status tags, pagination, duration tracking
- **Run Detail** - Statistics, execution logs, row-level error breakdown
- **Schedules** - Table with filter controls, cron management, create dialog
- **Settings** - Database connection management with test, activate, CRUD

### UI Components (Ant Design)
- Layout with collapsible dark sidebar, menu navigation
- Cards, Tables, Tags, Badges for data display
- Modals, Steps, Tabs for navigation
- Statistic, Descriptions for data presentation
- Alert, message, Result for feedback
- Form inputs: Input, Select, Switch, Radio, Checkbox, InputNumber

---

## Backend Features

### Services
- **Runner** - Main execution pipeline (fetch → normalize → validate → map → insert)
- **ApiConnector** - External API communication with auth support
- **Mapper** - Field value mapping and transformation
- **Validator** - Data validation against the selected destination schema
- **Normalizer** - JSON flattening and data normalization
- **Connection Services** - Encrypted destination connection storage and pooling
- **Scheduler** - APScheduler integration for cron jobs
- **TransformSuggester** - Type-based transform recommendations

### Infrastructure
- Local SQLite app database (`APP_DATABASE_URL`)
- Destination DB connection pooling and metadata lookup
- Encrypted credential storage with graceful empty-state fallback
- Async task processing with Celery + Redis
- Comprehensive error handling and logging (loguru)
- Request validation with Pydantic v2

---

## Environment Variables

See `.env.example` for the full reference. Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_DATABASE_URL` | `sqlite:///./intakegateway_app.db` | Local app state database |
| `ENCRYPTION_KEY` | — | Fernet key for credential encryption (required) |
| `CONNECTIONS_FILE_PATH` | `connections.enc` | Encrypted destination connections file |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis URL for Celery |
| `FRONTEND_URL` | `http://localhost:5173` | CORS allow-origin for the UI |
| `ORACLE_USER` / `ORACLE_HOST` / … | — | Oracle fallback (optional; used only when no active saved connection exists) |

Generate a valid `ENCRYPTION_KEY`:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## Contributing

1. Follow coding conventions — TypeScript strict mode, Python type hints, tests for new functionality
2. Ensure all tests pass before opening a PR: `pytest tests/ -v` and `npm test`
3. Update documentation for any API or behaviour changes
4. Keep commits atomic and descriptive

---

## License

GPLv3

---
