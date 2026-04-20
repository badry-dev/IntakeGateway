# IntakeGateway: Full-Stack Application

**Status**: ✅ Phase 8 Complete (Upsert/Skip) | ✅ Phase 9 Complete (Ant Design Migration) | Production Ready

A modern web application for importing data from external APIs into Oracle databases. Features a comprehensive React frontend with Ant Design UI, a robust Python FastAPI backend with async task processing, and full test coverage.

---

## Quick Links

- **[Project Context & Guidelines](claude.md)** - AI development reference
- **[Project Orientation](PROJECT_ORIENTATION.md)** - Architecture overview
- **[Frontend UI Prompt](frontend/PROMPT.md)** - Ant Design UI specification
- **[Documentation Index](DOCUMENTATION_INDEX.md)** - All guides

---

## Project Overview

**IntakeGateway** enables users to:
- Create and manage API data import tasks
- Configure API endpoints with authentication (Bearer, API Key, Basic, OAuth)
- Map API response fields to database columns with transform suggestions
- Schedule recurring imports with cron expressions
- Trigger task executions with real-time monitoring
- Configure upsert logic with skip conditions
- View detailed logs, statistics, and error reports
- Manage multiple database connections with encrypted credentials

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
- **Python 3.11** with **FastAPI 0.104**
- **SQLAlchemy 2.0** ORM for database operations
- **Celery 5.4** with Redis for async task execution
- **APScheduler 3.10** for cron-based scheduling
- **Pydantic 2.4** for data validation
- **cryptography** for encrypted credential storage
- **pytest** for testing (110+ test cases)
- **Oracle Database** (11g+ compatible)

---

## Project Metrics

| Metric | Backend | Frontend | Total |
|--------|---------|----------|-------|
| **Lines of Code** | 2,500+ | 2,600+ | 5,100+ |
| **Test Files** | 11 | 14 | 25 |
| **Test Cases** | 110+ | 60+ | 170+ |
| **Components/Services** | 8 services | 12 components | 20 |
| **Routes/Endpoints** | 15+ | 8 | 23+ |
| **TypeScript Coverage** | N/A | 100% | - |

---

## Quick Start

### Prerequisites
- Node.js 18+ (for frontend)
- Python 3.11+ (for backend)
- Oracle Database (production) or test Oracle instance
- Redis (for Celery)

### Setup Frontend

```bash
cd frontend
npm install
npm run dev
```
Frontend available at: **http://localhost:5173**

### Setup Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```
Backend API available at: **http://localhost:8000**
API Docs available at: **http://localhost:8000/docs**

### Run Tests

**Frontend**:
```bash
cd frontend
npm run test
```

**Backend**:
```bash
cd backend
pytest tests/ -v
```

---

## Project Structure

```
IntakeGateway/
├── backend/                    # FastAPI application
│   ├── app/
│   │   ├── api/v1/routes/     # REST endpoints (tasks, runs, schedules, connections, mappings)
│   │   ├── services/          # Business logic (runner, api_connector, mapper, validator, etc.)
│   │   ├── db/                # Database models & schemas (SQLAlchemy)
│   │   ├── workers/           # Celery task queue configuration
│   │   └── core/              # Config, encryption, logging
│   └── tests/                 # Unit + integration tests (110+ cases)
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
│   ├── PROMPT.md             # Ant Design UI specification
│   └── package.json
│
├── docker-compose.yml         # Multi-container setup
├── Makefile                   # Convenience commands
├── claude.md                  # AI development guide
├── PROJECT_ORIENTATION.md     # Architecture overview
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
- **Validator** - Data validation against Oracle schema
- **Normalizer** - JSON flattening and data normalization
- **ConnectionService** - Multi-database connection management
- **Scheduler** - APScheduler integration for cron jobs
- **TransformSuggester** - Type-based transform recommendations

### Infrastructure
- Oracle connection pooling (thin mode)
- Encrypted credential storage
- Async task processing with Celery + Redis
- Comprehensive error handling and logging (loguru)
- Request validation with Pydantic v2

---

## Development Phases

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1-4 | ✅ Complete | Backend API, services, database models |
| Phase 5 | ✅ Complete | React frontend with Radix UI + Tailwind |
| Phase 6 | ✅ Complete | Column mapping editor, field preview |
| Phase 7 | ✅ Complete | Encrypted connections, multi-DB support |
| Phase 8 | ✅ Complete | Upsert logic, skip conditions, continue-on-error |
| Phase 9 | ✅ Complete | **Ant Design UI migration** (from Radix UI + Tailwind) |

---

## Docker Setup

```bash
docker compose up --build
```

This starts:
- FastAPI backend (port 8000)
- React frontend (port 5173)
- Redis (port 6379)
- Celery worker (background)
- Scheduler (background)

---

## Environment Variables

```env
# Backend
ORACLE_USER=your_oracle_user
ORACLE_PASSWORD=your_oracle_password
ORACLE_HOST=localhost
ORACLE_PORT=1521
ORACLE_SERVICE_NAME=your_service
REDIS_URL=redis://localhost:6379
CELERY_BROKER_URL=redis://localhost:6379/0
SECRET_KEY=your_secret_key
```

---

## Contributing

1. Read [claude.md](claude.md) for development guidelines
2. Follow coding conventions (TypeScript strict, type hints, testing)
3. Ensure all tests pass: `tsc -b` + `vite build` + `npm test`
4. Update documentation for major changes
5. Keep commits atomic and well-described

---

**Last Updated**: April 2026
**Version**: 2.0.0
**Status**: Production Ready

For detailed project context, see [claude.md](claude.md)
