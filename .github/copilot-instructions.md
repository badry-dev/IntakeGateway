# API2DB-Importer: AI Coding Agent Instructions

**Last Updated**: January 2026 | **Status**: Production Ready

Quick reference for AI agents developing or extending this full-stack application.

## 🎯 Project Essence

**API2DB-Importer** is a web app enabling users to:
1. Define data import tasks (API config → database mapping)
2. Trigger async task executions via Celery workers
3. Monitor runs with detailed logs and error reporting
4. Dashboard with live statistics

**Tech Stack**: FastAPI + SQLAlchemy (backend) | React 18 + TypeScript + Vite (frontend)

---

## 🏗️ Critical Architecture Understanding

### Backend Data Flow Pattern
```
User Request → FastAPI Route → Service Layer → SQLAlchemy ORM → Oracle DB
                                    ↓
                            Celery Queue
                                    ↓
                            Worker Process → API Connector → External API → Mapper → DB
```

**Key Services** (in `backend/app/services/`):
- `api_connector.py` - Calls external APIs with configured headers/auth
- `mapper.py` - Maps API response fields to DB columns with **transforms** (trim, upper, lower, to_int, to_float, to_bool)
- `normalizer.py` - Data structure transformation
- `validator.py` - Input/schema validation
- `runner.py` - Orchestrates the full pipeline
- `scheduler.py` - Task scheduling logic

### Database Schema Pattern
**Key Tables**:
- `Task` - Configuration (endpoint, headers, mappings, destination table)
- `TaskRun` - Execution instances with status tracking
- `ColumnMapping` - Field mappings with transform rules (stored as JSON)
- `TaskLog`, `TaskRunLog` - Audit trail for debugging

**Critical Detail**: `Task` uses `JSONEncodedDict` TypeDecorator for Oracle compatibility—stores complex objects as JSON strings.

### Frontend Architecture
- **Pages** (6): Dashboard, TaskList, TaskDetail, TaskWizard, RunsList, RunDetail
- **State Management**: React Query (server state) + Zustand (optional UI state)
- **API Integration**: `src/api/client.ts` wraps Axios with base config
- **TaskWizard**: 5-step form (Basic → Endpoint → Headers → Mapping → Review)

---

## 🔧 Critical Development Workflows

### Backend Setup & Running
```bash
# Initial setup
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Development server (auto-reload)
make dev              # OR: uvicorn app.main:app --reload --port 8000

# Celery worker (separate terminal)
make worker           # OR: celery -A app.workers.celery_app.celery_app worker --loglevel=INFO

# Task scheduler (separate terminal, if needed)
make scheduler        # OR: python backend/app/services/scheduler.py

# Format code
make fmt              # OR: python -m black backend
```

**API Docs**: http://localhost:8000/docs

### Frontend Setup & Running
```bash
cd frontend
npm install
npm run dev           # Starts Vite dev server on http://localhost:5173

npm run build         # Production build (tsc + vite build)
npm run test          # Run Vitest
npm run test:ui       # Vitest UI
npm run lint          # ESLint on .ts/.tsx
```

### Testing
```bash
# Backend unit tests
pytest backend/tests/unit/ -v

# Backend integration tests
pytest backend/tests/integration/ -v

# Frontend tests
cd frontend && npm test

# Full test coverage
cd frontend && npm test -- --coverage
```

---

## 📋 Project Conventions & Patterns

### Backend Patterns

**1. API Routes Structure** (`app/api/v1/routes/`)
```python
@router.post("/", response_model=TaskOut, status_code=201)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    # Pattern: Always return pydantic model, handle 400/404 with HTTPException
```
- Always use `response_model` to validate output
- Validate uniqueness constraints early (e.g., duplicate task names)
- Use HTTP status codes consistently: 201 (create), 400 (validation), 404 (not found), 500 (server error)

**2. Service Layer Validation** (`app/services/`)
- Normalizers and validators run **before** mapper to catch bad data early
- Mapper applies field-level transforms and null handling
- All services are unit-testable (minimal DB dependencies)

**3. Celery Task Pattern** (`app/workers/tasks.py`)
```python
@celery_app.task(queue="imports")
def run_import_task(task_id: int, run_id: int):
    # Pattern: Minimal parameters (IDs), fetch from DB inside task
    # Exception handling: Update run.status = "failed", log details
```
- Tasks take only IDs (reduce serialization issues with Oracle connections)
- Fetch full objects inside the task
- Always update `run.status` and `run.error_message` for UI feedback

**4. JSON in Oracle** (`app/db/models/task.py`)
- Use `JSONEncodedDict` TypeDecorator for complex fields (headers, body_json, column mappings)
- Automatically handles serialization/deserialization

### Frontend Patterns

**1. API Hooks** (`src/hooks/api.ts`)
```typescript
export function useGetTasks() {
  return useQuery({
    queryKey: ["tasks"],
    queryFn: () => apiClient.get("/tasks").then(res => res.data),
  })
}
```
- Pattern: useQuery for reads, useMutation for writes
- Auto-invalidation on mutations (configured in hooks)

**2. Type Safety** (`src/types/index.ts`)
- All API responses have matching TypeScript types
- Use strict mode TypeScript (no `any`, no `unknown` without narrowing)

**3. TaskWizard Navigation** (`src/pages/TaskWizard.tsx`)
- 5-step linear flow: Basic → Endpoint → Headers → Mapping → Review
- Step validation prevents forward progression without required fields
- Convert header array to object before API submission

**4. Component Reusability** (`src/components/`)
- Radix UI primitives (button, card, dialog, select)
- Tailwind for styling (no CSS files, config-driven)

---

## 🔗 Integration Points & Data Contracts

### Backend ↔ Frontend API Contract
**Base URL**: `http://localhost:8000/api/v1`

**Key Endpoints**:
- `POST /tasks` - Create (accepts `TaskCreate` schema)
- `GET /tasks/{id}` - Get single task
- `PUT /tasks/{id}` - Update task
- `GET /runs` - List runs with pagination
- `POST /runs` - Trigger new run (requires `task_id`)
- `GET /runs/{id}` - Get run details with logs

**Response Format**: All responses return the resource directly (not wrapped), with metadata in headers if needed.

### External API Integration Pattern
```python
# In services/api_connector.py:
# 1. Build URL from task.endpoint_path
# 2. Merge headers from task.headers_json
# 3. Include body from task.body_json if applicable
# 4. Extract data at task.record_path (e.g., "data.items[0]")
# 5. Return list of records for mapping
```

---

## 🚨 Common Pitfalls & Solutions

| Problem | Solution |
|---------|----------|
| Celery worker won't pick up tasks | Ensure `celery_broker` and `celery_backend` env vars are set; restart worker; check Redis is running |
| "Task with this name already exists" on update | Update endpoint checks for name conflicts; only skip check if name unchanged |
| JSON serialization errors in Oracle fields | Use `JSONEncodedDict` TypeDecorator; don't store raw Python objects |
| Frontend stuck on stale data | Check React Query cache invalidation on mutations (configured in `useCreateTask`, `useUpdateTask`) |
| TaskWizard validation passes but submission fails | Validate step-by-step (check frontend console + backend logs at `/docs`) |
| Oracle connection pooling issues | Verify `oracle_pool.py` connection string; pool size settings; max retries |

---

## 📁 File Navigation Quick Reference

**Backend Critical Files**:
- `app/main.py` - FastAPI app, CORS, route registration
- `app/api/v1/routes/tasks.py` - Task CRUD endpoints (294 lines)
- `app/api/v1/routes/runs.py` - Run execution endpoints
- `app/workers/tasks.py` - Celery task definitions
- `app/services/mapper.py` - Field mapping + transforms (116 lines)
- `app/db/models/task.py` - Task ORM model with JSONEncodedDict
- `app/core/config.py` - Environment configuration

**Frontend Critical Files**:
- `src/pages/TaskWizard.tsx` - 5-step task creation (448 lines)
- `src/pages/RunDetail.tsx` - Run monitoring UI
- `src/hooks/api.ts` - React Query hooks
- `src/types/index.ts` - TypeScript type definitions
- `vite.config.ts` - Build configuration

**Configuration**:
- `.env` / `app/core/config.py` - Backend config (API_ENV, DATABASE_URL, CELERY_*)
- `frontend/.env` - Frontend config (VITE_API_URL)
- `docker-compose.yml` - Local Oracle + Redis setup

---

## 📚 Reference Documentation

For detailed context, see:
- **[claude.md](../claude.md)** - Full architecture, data flow, troubleshooting
- **[PHASE_5_TESTING_GUIDE.md](../PHASE_5_TESTING_GUIDE.md)** - Comprehensive test examples
- **[README.md](../README.md)** - Quick start, setup verification
- **[Backend README](../backend/README.md)** - Backend-specific setup

---

## ✅ Checklist for Common Tasks

### Adding a New Task Endpoint
- [ ] Create route in `app/api/v1/routes/tasks.py`
- [ ] Add Pydantic schema in `app/db/schemas/task.py`
- [ ] Update TypeScript types in `frontend/src/types/index.ts`
- [ ] Create React hook in `frontend/src/hooks/api.ts`
- [ ] Add UI component/page in `frontend/src/pages/`
- [ ] Test with Vitest + pytest

### Modifying Task Schema
- [ ] Update `Task` model in `app/db/models/task.py`
- [ ] Create Alembic migration: `alembic revision --autogenerate`
- [ ] Update Pydantic schema `TaskCreate`/`TaskOut`
- [ ] Update frontend types
- [ ] Test with migration: `alembic upgrade head`

### Fixing a Bug in Mapper
- [ ] Reproduce with unit test in `backend/tests/unit/test_mapper.py`
- [ ] Fix `app/services/mapper.py`
- [ ] Add transform test if applicable
- [ ] Run full test suite: `pytest backend/tests/ -v`

---

**Questions?** Consult the detailed [claude.md](../claude.md) guide or run tests to understand current behavior.
