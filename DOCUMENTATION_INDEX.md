# IntakeGateway: Documentation Index

**Project Status**: All Phases Complete (1-9) | Production Ready
**Last Updated**: April 2026

---

## Quick Links

### Core Documentation
1. **[README.md](README.md)** - Project overview, setup, and quick start
2. **[claude.md](claude.md)** - AI development guide, architecture, API reference
3. **[PROJECT_ORIENTATION.md](PROJECT_ORIENTATION.md)** - Detailed architecture and business flows
4. **[PROJECT_ORIENTATION_MERMAID.md](PROJECT_ORIENTATION_MERMAID.md)** - Architecture diagrams

### Frontend
5. **[frontend/PROMPT.md](frontend/PROMPT.md)** - Ant Design UI specification (target design)
6. **[frontend/README.md](frontend/README.md)** - Frontend setup and structure

### Phase Documentation
- [PHASE_8_FEATURE_1_SESSION_SUMMARY.md](PHASE_8_FEATURE_1_SESSION_SUMMARY.md) - Upsert feature implementation
- [PHASE_8_FEATURE_1_VALIDATION.md](PHASE_8_FEATURE_1_VALIDATION.md) - Upsert validation report

---

## What Was Built

### Phase 1-4: Backend API
- FastAPI REST API with 15+ endpoints
- SQLAlchemy ORM models (Task, TaskRun, ColumnMapping, TaskSchedule)
- Service layer (runner, api_connector, mapper, validator, normalizer)
- Celery async task processing with Redis
- 110+ backend tests

### Phase 5: Frontend (Initial)
- React 18 + TypeScript + Vite frontend
- 8 page components with routing
- React Query hooks for all API entities
- Axios HTTP client

### Phase 6: Column Mapping Editor
- Field tree view with API response preview
- Auto-fetch and manual JSON paste modes
- Oracle column metadata integration
- Transform suggestions

### Phase 7: Database Connections
- Multi-database connection management (Oracle, PostgreSQL, MySQL)
- Encrypted credential storage
- Connection testing and activation

### Phase 8: Upsert & Skip Logic
- Upsert (insert or update) with configurable key columns
- Skip conditions for already-processed records
- Continue-on-error mode
- Row-level error tracking

### Phase 9: Ant Design UI Migration
- **Migrated entire frontend from Radix UI + Tailwind CSS to Ant Design 5**
- Dark collapsible sidebar with `Layout.Sider` and `Menu`
- `ConfigProvider` theme with brand colors (#1677FF primary)
- All pages rewritten with AntD components (Card, Table, Tag, Modal, Steps, Tabs, Statistic, etc.)
- All 4 editor components migrated (ColumnMapping, Connection, Schedule, Upsert)
- Removed 11 Radix UI wrapper components, Tailwind CSS, CVA, lucide-react
- Added `@ant-design/icons`, `dayjs`
- 14 test files rewritten for new component APIs
- Fixed `TaskCreate` interface type conflict
- Zero TypeScript errors

### Architecture Update: Local App State + Destination Separation
- App-owned tables now live in a local SQLite database by default via `APP_DATABASE_URL`
- Destination connectivity is isolated so the backend and UI still work when Oracle or another target DB is unavailable
- Tasks can optionally target a specific saved `connection_id`, while the active connection remains the fallback
- `connections.enc` is recreated on first save and missing or unreadable files degrade to an empty connection list

---

## Technology Stack

### Backend
- Python 3.11 + FastAPI 0.104
- SQLAlchemy 2.0 + SQLite app DB + Oracle destination ingestion
- Celery 5.4 + Redis
- APScheduler 3.10
- Pydantic 2.4
- cryptography (encrypted credentials)

### Frontend
- React 18.2 + TypeScript 5.3
- Vite 5.0
- **Ant Design 5** + **@ant-design/icons**
- React Router v6
- React Query 5.28 (TanStack Query)
- Axios + dayjs
- Vitest + React Testing Library

---

## Project Structure

```
IntakeGateway/
├── backend/                    # FastAPI application
│   ├── app/
│   │   ├── api/v1/routes/     # REST endpoints
│   │   ├── services/          # Business logic
│   │   ├── db/                # Models, schemas, session
│   │   ├── workers/           # Celery tasks
│   │   └── core/              # Config, encryption, logging
│   └── tests/                 # 110+ test cases
│
├── frontend/                   # React + Ant Design application
│   ├── src/
│   │   ├── pages/             # 8 pages
│   │   ├── components/        # 4 editor components
│   │   ├── hooks/api.ts       # React Query hooks
│   │   ├── api/client.ts      # Axios HTTP client
│   │   ├── types/index.ts     # TypeScript interfaces
│   │   ├── __tests__/         # 14 test files
│   │   ├── theme.ts           # Ant Design theme config
│   │   └── App.tsx            # Routing + Layout
│   └── PROMPT.md              # Ant Design UI specification
│
├── docker-compose.yml
├── claude.md                   # AI development guide
├── PROJECT_ORIENTATION.md      # Architecture overview
└── README.md
```

---

## Quick Start

```bash
# Frontend
cd frontend && npm install && npm run dev
# → http://localhost:5173

# Backend
cd backend && pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
# → http://localhost:8000

# Tests
cd frontend && npm test
cd backend && pytest tests/ -v
```

---

**Status**: All phases complete. Production ready.
