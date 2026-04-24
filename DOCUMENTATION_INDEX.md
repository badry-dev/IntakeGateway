# IntakeGateway: Documentation Index

---

## Core Documentation

| File | Description |
|------|-------------|
| [README.md](README.md) | Project overview, setup, and quick start |
| [frontend/README.md](frontend/README.md) | Frontend setup and structure |
| [.env.example](.env.example) | Environment variable reference |

## API Reference

The interactive API documentation is available at **http://localhost:8000/docs** when the backend is running.

### Endpoint Groups

| Group | Base path |
|-------|-----------|
| Tasks | `/api/v1/tasks` |
| Runs | `/api/v1/runs` |
| Schedules | `/api/v1/schedules` |
| Column Mappings | `/api/v1/tasks/{id}/mappings` |
| Database Connections | `/api/v1/connections` |
| Statistics | `/api/v1/stats` |

## Architecture

```
IntakeGateway/
├── backend/app/
│   ├── api/v1/routes/     # FastAPI route handlers
│   ├── services/          # Business logic (runner, mapper, normalizer, etc.)
│   ├── db/                # SQLAlchemy models, Pydantic schemas, session
│   ├── workers/           # Celery task definitions
│   └── core/              # Config, encryption, logging
└── frontend/src/
    ├── pages/             # 8 page components
    ├── components/        # Editor components (Mapping, Connection, Schedule, Upsert)
    ├── hooks/api.ts       # React Query hooks
    ├── api/client.ts      # Axios HTTP client
    └── types/index.ts     # TypeScript interfaces
```

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + TypeScript, Ant Design 5, React Query 5, Vite |
| Backend | Python 3.11, FastAPI 0.104, SQLAlchemy 2.0, Pydantic 2.4 |
| Queue | Celery 5.4 + Redis |
| Scheduler | APScheduler 3.10 |
| App DB | SQLite (default via `APP_DATABASE_URL`) |
| Destination DB | Oracle / PostgreSQL / MySQL |
| Testing | pytest (110+ cases), Vitest + RTL (60+ cases) |
