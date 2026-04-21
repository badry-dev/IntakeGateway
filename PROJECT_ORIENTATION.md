# IntakeGateway: Project Orientation Document

**Document Version:** 1.0
**Date:** February 4, 2026
**Project Codename:** IntakeGateway

---

## Phase 1 — Project Orientation

### Product Purpose

**IntakeGateway** is an enterprise-grade data integration platform that automates the extraction of data from REST APIs and imports it into Oracle databases. It eliminates manual data entry by providing:

- **Automated API Data Fetching** - Connect to any REST API with configurable authentication
- **Intelligent Field Mapping** - Map JSON response fields to Oracle table columns with transformation suggestions
- **Scheduled Execution** - Cron-based scheduling for recurring imports
- **Audit Trail** - Complete logging of all import operations with row-level error tracking
- **Upsert Support** - Insert or update records with skip logic for processed rows

### Users and Roles

| Role | Responsibilities | Access Level |
|------|------------------|--------------|
| **Data Engineer** | Configure tasks, mappings, and schedules | Full CRUD access |
| **System Admin** | Manage database connections, monitor runs | Configuration + monitoring |
| **Business Analyst** | View dashboards, verify data imports | Read-only access |

*Note: Current implementation has no built-in authentication/authorization. All users have full access.*

### Critical Business Flows

1. **Task Creation Flow**
   - User creates task with API endpoint configuration
   - User configures authentication (Bearer, API Key, Basic, OAuth)
   - User maps source JSON fields to Oracle columns
   - User optionally configures upsert/skip logic
   - Task saved to database

2. **Task Execution Flow**
   - User triggers task manually OR scheduler triggers via cron
   - System fetches data from external API
   - System normalizes/flattens JSON response
   - System validates data against Oracle schema
   - System inserts/updates records in Oracle
   - System logs results (rows inserted, updated, skipped, errors)

3. **Schedule Management Flow**
   - User creates cron schedule for a task
   - APScheduler registers the job
   - At scheduled time, task executes automatically
   - Next run date calculated and displayed

### High-Level System Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          EXTERNAL SYSTEMS                                │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐   │
│  │   REST API #1   │     │   REST API #2   │     │   REST API #N   │   │
│  │  (Bearer Auth)  │     │   (API Key)     │     │    (OAuth)      │   │
│  └────────┬────────┘     └────────┬────────┘     └────────┬────────┘   │
└───────────┼──────────────────────┼──────────────────────┼──────────────┘
            │                      │                      │
            └──────────────────────┼──────────────────────┘
                                   │ HTTPS
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Port 5173)                            │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐  ┌───────────────┐  │
│  │  Dashboard  │  │   TaskList   │  │  RunsList  │  │   Schedules   │  │
│  │  (Stats)    │  │   (CRUD)     │  │  (History) │  │   (Cron)      │  │
│  └─────────────┘  └──────────────┘  └────────────┘  └───────────────┘  │
│  ┌─────────────────────────┐  ┌─────────────────────────────────────┐  │
│  │      TaskWizard         │  │      ColumnMappingEditor            │  │
│  │  (5-Step Creation)      │  │  (Drag-Drop Field Mapping)          │  │
│  └─────────────────────────┘  └─────────────────────────────────────┘  │
└─────────────────────────────────────┬───────────────────────────────────┘
                                      │ HTTP (Axios)
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       BACKEND API (Port 8000)                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    FastAPI Application                          │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │   │
│  │  │ /api/v1/    │  │ /api/v1/    │  │ /api/v1/               │ │   │
│  │  │ tasks       │  │ runs        │  │ schedules + mappings    │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                      │                                  │
│  ┌───────────────────────────────────┼────────────────────────────┐    │
│  │                    SERVICE LAYER                               │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │    │
│  │  │ runner.py    │  │ api_connector│  │ oracle_metadata.py   │ │    │
│  │  │ (Pipeline)   │  │ (API Fetch)  │  │ (Schema Discovery)   │ │    │
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘ │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │    │
│  │  │ mapper.py    │  │ validator.py │  │ transform_suggester  │ │    │
│  │  │ (Field Map)  │  │ (Validation) │  │ (Type Suggestions)   │ │    │
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘ │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │    │
│  │  │ normalizer   │  │ scheduler.py │  │ connection_service   │ │    │
│  │  │ (Flatten)    │  │ (APScheduler)│  │ (Encrypted Storage)  │ │    │
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘ │    │
│  └────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────┬───────────────────────────────────┘
                                      │
            ┌─────────────────────────┼─────────────────────────┐
            │                         │                         │
            ▼                         ▼                         ▼
┌───────────────────┐    ┌───────────────────┐    ┌───────────────────┐
│   Celery Worker   │    │   APScheduler     │    │      Redis        │
│   (Async Tasks)   │    │   (Cron Jobs)     │    │   (Port 6379)     │
│                   │    │                   │    │   Message Broker  │
└─────────┬─────────┘    └─────────┬─────────┘    └───────────────────┘
          │                        │
          └────────────┬───────────┘
                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        DATA LAYER                                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    SQLAlchemy ORM                               │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │   │
│  │  │  Task    │  │ TaskRun  │  │ TaskLog  │  │ ColumnMapping  │  │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └────────────────┘  │   │
│  │  ┌──────────┐  ┌──────────────────────────────────────────────┐│   │
│  │  │ Schedule │  │             TaskRunLog (Errors)              ││   │
│  │  └──────────┘  └──────────────────────────────────────────────┘│   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                      │                                  │
│                                      ▼                                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │               Oracle Database (11g+ / 19c+)                     │   │
│  │  ┌──────────────────────────────────────────────────────────┐  │   │
│  │  │  Application Tables      │  Destination Tables (User)    │  │   │
│  │  │  - TASKS                 │  - <user-defined tables>      │  │   │
│  │  │  - TASK_RUNS             │                               │  │   │
│  │  │  - TASK_LOGS             │                               │  │   │
│  │  │  - TASK_RUN_LOGS         │                               │  │   │
│  │  │  - TASK_SCHEDULES        │                               │  │   │
│  │  │  - COLUMN_MAPPINGS       │                               │  │   │
│  │  └──────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Core Flows Summary

| Flow | Entry Point | Critical Path | Side Effects |
|------|-------------|---------------|--------------|
| Create Task | POST /api/v1/tasks | Route → Pydantic → SQLAlchemy → Oracle | None |
| Execute Task | POST /api/v1/tasks/{id}/run | Route → Celery → Runner Pipeline → Oracle | External API call, DB writes, Logging |
| View Runs | GET /api/v1/runs | Route → SQLAlchemy → Response | None |
| Create Schedule | POST /api/v1/schedules/{task_id} | Route → APScheduler Registration → Oracle | Cron job registered |
| Map Columns | POST /api/v1/tasks/{id}/mappings | Route → OracleMetadata → SQLAlchemy | None |

---

## Phase 2 — Run It Locally

### SETUP_NOTES.md

#### Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Python | 3.11+ | Backend runtime |
| Node.js | 18+ | Frontend runtime |
| Docker | 24+ | Container orchestration |
| Docker Compose | 2.20+ | Multi-container setup |
| Oracle Database | 11g+ / 19c+ | Target database |

#### Environment Setup

1. **Clone Repository**
```bash
git clone https://github.com/Badry-Kudu/API2DB-Importer.git
cd API2DB-Importer
```

2. **Copy Environment File**
```bash
cp .env.example .env
```

3. **Configure Environment Variables**
```bash
# Edit .env with your Oracle connection details
# Required variables:
ORACLE_USER=your_oracle_user
ORACLE_PASSWORD=your_oracle_password
ORACLE_HOST=your_oracle_host
ORACLE_PORT=1521
ORACLE_SERVICE_NAME=ORCLPDB1

# Required for encryption (change in production!)
SECRET_KEY=your-secret-key-change-me-in-production

# Optional
APP_TIMEZONE=Asia/Riyadh
APP_LOG_LEVEL=INFO
```

#### Starting Each Layer

**Option A: Docker Compose (Recommended)**
```bash
# Start all services
docker-compose up -d

# Services started:
# - api (FastAPI): http://localhost:8000
# - worker (Celery): background processing
# - scheduler (APScheduler): cron jobs
# - redis: message broker on port 6379
```

**Option B: Manual Start (Development)**

1. **Start Redis**
```bash
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

2. **Start Backend**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

3. **Start Celery Worker (separate terminal)**
```bash
cd backend
source venv/bin/activate
celery -A app.celery_app worker --loglevel=info
```

4. **Start Frontend**
```bash
cd frontend
npm install
npm run dev
# Frontend available at http://localhost:5173
```

#### Verification Checklist

| Check | How to Verify | Expected Result |
|-------|---------------|-----------------|
| Frontend loads | Visit http://localhost:5173 | Dashboard displays |
| Backend responds | Visit http://localhost:8000/docs | Swagger UI loads |
| Database connected | Check backend logs | "Connected to Oracle" |
| Redis connected | Check Celery worker logs | "Connected to redis://..." |

#### Complete User Flow Test

1. Navigate to http://localhost:5173
2. Click "New Task" → TaskWizard opens
3. Enter task name: "Test Task"
4. Enter API endpoint: https://jsonplaceholder.typicode.com/users
5. Select Auth: None
6. Select destination table (from your Oracle schema)
7. Map fields: name → NAME_COLUMN, email → EMAIL_COLUMN
8. Save task
9. Click "Run Now"
10. Verify run appears in Runs list with "completed" status

---

## Phase 3 — Architecture & Boundaries

### Where Does Business Logic Live?

| Logic Type | Location | Files |
|------------|----------|-------|
| **API Data Fetching** | Service Layer | `backend/app/services/api_connector.py` |
| **Data Transformation** | Service Layer | `backend/app/services/normalizer.py`, `mapper.py` |
| **Validation** | Service Layer | `backend/app/services/validator.py` |
| **Database Operations** | Service Layer | `backend/app/services/runner.py:320-568` |
| **Scheduling** | Service Layer | `backend/app/services/scheduler.py` |
| **Task Orchestration** | Service Layer | `backend/app/services/runner.py:run_import()` |

### Where Is Validation Done?

| Validation Type | Location | Implementation |
|-----------------|----------|----------------|
| **Request Validation** | API Layer | Pydantic models in `backend/app/db/schemas/` |
| **Auth Validation** | Schema Layer | `backend/app/db/schemas/task.py:validate_auth_config()` |
| **Data Type Validation** | Service Layer | `backend/app/services/validator.py:validate_row()` |
| **Oracle Schema Validation** | Service Layer | `backend/app/services/oracle_metadata.py` |

### How Does Frontend Talk to Backend?

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND                                  │
│  ┌─────────────────┐     ┌─────────────────┐                   │
│  │  React Query    │────▶│  API Client     │                   │
│  │  Hooks          │     │  (Axios)        │                   │
│  │  api.ts:1-400   │     │  client.ts:1-150│                   │
│  └─────────────────┘     └────────┬────────┘                   │
└──────────────────────────────────┼──────────────────────────────┘
                                   │
                                   │ HTTP/JSON
                                   │ Base URL: /api/v1
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                        BACKEND                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  FastAPI Router Registration (main.py:20-30)            │   │
│  │  /api/v1/tasks    → tasks.py                            │   │
│  │  /api/v1/runs     → runs.py                             │   │
│  │  /api/v1/mappings → column_mappings.py                  │   │
│  │  /api/v1/schedules→ schedules.py                        │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Where Are Side Effects?

| Side Effect | Location | Trigger |
|-------------|----------|---------|
| **External API Calls** | `api_connector.py:fetch()` | Task execution |
| **Database Writes** | `runner.py:_insert_single_row()`, `_update_existing_row()` | Task execution |
| **Logging to DB** | `runner.py:log_step()`, `log_row_error()` | Throughout execution |
| **File Writes** | `connection_service.py:_write_connections()` | Connection management |
| **Cron Registration** | `scheduler.py:add_job()` | Schedule creation |

### Annotated Architecture with File Paths

```
ENTRY POINTS (Controllers/Routes)
├── backend/app/api/v1/routes/tasks.py          # Task CRUD (304 lines)
├── backend/app/api/v1/routes/runs.py           # Run history/trigger (138 lines)
├── backend/app/api/v1/routes/column_mappings.py # Mapping CRUD (492 lines)
└── backend/app/api/v1/routes/schedules.py      # Schedule CRUD (315 lines)

CORE SERVICES/MODULES
├── backend/app/services/runner.py              # Main pipeline (568 lines)
│   ├── run_import()                            # Orchestrator function
│   ├── process_rows_with_upsert()              # Upsert/skip logic
│   └── _process_single_row()                   # Row-level processing
├── backend/app/services/api_connector.py       # External API (394 lines)
│   └── fetch()                                 # HTTP request handler
├── backend/app/services/mapper.py              # Field mapping (218 lines)
├── backend/app/services/validator.py           # Validation (263 lines)
├── backend/app/services/normalizer.py          # JSON flattening (33 lines)
├── backend/app/services/oracle_metadata.py     # Schema discovery (285 lines)
├── backend/app/services/transform_suggester.py # Type suggestions (256 lines)
├── backend/app/services/scheduler.py           # APScheduler (189 lines)
└── backend/app/services/connection_service.py  # Encrypted storage (359 lines)

PERSISTENCE LAYER
├── backend/app/db/models/                      # SQLAlchemy models
│   ├── task.py                                 # Task config (54 lines)
│   ├── task_run.py                             # Execution records (29 lines)
│   ├── task_log.py                             # Step logs (14 lines)
│   ├── task_run_log.py                         # Row errors (16 lines)
│   ├── task_schedule.py                        # Cron config (16 lines)
│   └── column_mapping.py                       # Field mappings (16 lines)
├── backend/app/db/schemas/                     # Pydantic schemas
│   ├── task.py                                 # Task schemas (200+ lines)
│   ├── column_mapping.py                       # Mapping schemas
│   └── schedule.py                             # Schedule schemas
└── backend/app/db/database.py                  # DB session management

EXTERNAL INTEGRATIONS
├── backend/app/services/api_connector.py       # REST API clients
├── backend/app/celery_app.py                   # Celery configuration
└── docker-compose.yml                          # Redis, services
```

---

## Phase 4 — Data & State Audit

### Database Schema

```sql
-- Application Tables (managed by SQLAlchemy/Alembic)

TABLE: tasks
├── id                  NUMBER PRIMARY KEY
├── name                VARCHAR2(100) NOT NULL UNIQUE
├── endpoint_path       VARCHAR2(500) NOT NULL
├── http_method         VARCHAR2(10) DEFAULT 'GET'
├── auth_type           VARCHAR2(20) -- bearer, api_key, basic, oauth, none
├── auth_config         CLOB (JSON)  -- Encrypted auth credentials
├── dest_table          VARCHAR2(100) NOT NULL
├── batch_size          NUMBER DEFAULT 100
├── is_active           NUMBER(1) DEFAULT 1
├── upsert_enabled      NUMBER(1) DEFAULT 0
├── upsert_keys         CLOB (JSON)  -- Array of key columns
├── skip_column         VARCHAR2(100)
├── skip_value          VARCHAR2(100)
├── continue_on_error   NUMBER(1) DEFAULT 1
├── created_at          TIMESTAMP WITH TIME ZONE
└── updated_at          TIMESTAMP WITH TIME ZONE

TABLE: task_runs
├── id                  NUMBER PRIMARY KEY
├── task_id             NUMBER REFERENCES tasks(id) ON DELETE CASCADE
├── status              VARCHAR2(20) -- pending, running, completed, failed
├── started_at          TIMESTAMP WITH TIME ZONE
├── completed_at        TIMESTAMP WITH TIME ZONE
├── rows_fetched        NUMBER DEFAULT 0
├── rows_inserted       NUMBER DEFAULT 0
├── rows_updated        NUMBER DEFAULT 0
├── rows_skipped        NUMBER DEFAULT 0
├── rows_failed         NUMBER DEFAULT 0
└── error_message       CLOB

TABLE: task_logs
├── id                  NUMBER PRIMARY KEY
├── task_run_id         NUMBER REFERENCES task_runs(id) ON DELETE CASCADE
├── step_name           VARCHAR2(50)
├── message             VARCHAR2(500)
├── details             CLOB (JSON)
└── created_at          TIMESTAMP WITH TIME ZONE

TABLE: task_run_logs (Row-level Errors)
├── id                  NUMBER PRIMARY KEY
├── task_run_id         NUMBER REFERENCES task_runs(id) ON DELETE CASCADE
├── row_number          NUMBER
├── error_message       VARCHAR2(1000)
├── column_name         VARCHAR2(100)
└── created_at          TIMESTAMP WITH TIME ZONE

TABLE: task_schedules
├── id                  NUMBER PRIMARY KEY
├── task_id             NUMBER REFERENCES tasks(id) ON DELETE CASCADE UNIQUE
├── cron_expression     VARCHAR2(100)
├── is_enabled          NUMBER(1) DEFAULT 1
├── last_run_date       TIMESTAMP WITH TIME ZONE
├── next_run_date       TIMESTAMP WITH TIME ZONE
└── created_at          TIMESTAMP WITH TIME ZONE

TABLE: column_mappings
├── id                  NUMBER PRIMARY KEY
├── task_id             NUMBER REFERENCES tasks(id) ON DELETE CASCADE
├── source_field        VARCHAR2(200) NOT NULL
├── dest_column         VARCHAR2(100) NOT NULL
├── transform_rules     CLOB (JSON)
├── is_key_field        NUMBER(1) DEFAULT 0
└── created_at          TIMESTAMP WITH TIME ZONE
```

### Critical Tables and Invariants

| Table | Criticality | Invariants | Corruption Risk |
|-------|-------------|------------|-----------------|
| **tasks** | HIGH | name UNIQUE, auth_config encrypted | Task duplication, auth exposure |
| **task_runs** | MEDIUM | status must be valid enum | Orphaned runs, wrong status |
| **column_mappings** | HIGH | task_id FK valid | Invalid mappings break execution |
| **task_schedules** | MEDIUM | task_id UNIQUE | Duplicate schedules |

### Source of Truth vs Derived Data

| Data Type | Source | Derived From | Cache Location |
|-----------|--------|--------------|----------------|
| Task Configuration | `tasks` table | - | - |
| Run History | `task_runs` table | - | - |
| Task Statistics | Aggregated | `task_runs` | Computed on-demand |
| Oracle Table Schema | Oracle DB | - | Not cached |
| Next Run Date | Calculated | cron_expression | `task_schedules.next_run_date` |

### Write Operation Trace: Task Execution

```
Request: POST /api/v1/tasks/{id}/run

1. VALIDATION (runs.py:trigger_run())
   ├── Verify task exists
   ├── Check task is_active
   └── Validate task has mappings

2. CREATE RUN RECORD (runs.py:45-60)
   ├── INSERT INTO task_runs (task_id, status='pending', started_at)
   └── COMMIT

3. QUEUE CELERY TASK (runs.py:65-70)
   └── celery_app.send_task('run_import', args=[task_id, run_id])

4. CELERY WORKER EXECUTION (runner.py:run_import())

   4a. UPDATE STATUS
       └── UPDATE task_runs SET status='running' WHERE id=run_id

   4b. FETCH API DATA (api_connector.py)
       └── HTTP GET to external API (SIDE EFFECT)

   4c. NORMALIZE DATA (normalizer.py)
       └── Flatten nested JSON (no DB write)

   4d. MAP FIELDS (mapper.py)
       └── Apply column mappings (no DB write)

   4e. VALIDATE DATA (validator.py)
       └── Check against Oracle schema (no DB write)

   4f. PROCESS ROWS (runner.py:process_rows_with_upsert())
       FOR EACH ROW:
       ├── Check skip condition
       │   └── If skip_column value matches → INCREMENT rows_skipped
       ├── Check if record exists (upsert mode)
       │   ├── If exists → UPDATE destination_table
       │   └── If not exists → INSERT INTO destination_table
       ├── On error AND continue_on_error=true
       │   ├── INSERT INTO task_run_logs (error details)
       │   └── INCREMENT rows_failed
       └── COMMIT after batch_size rows

   4g. LOG COMPLETION (runner.py)
       ├── INSERT INTO task_logs (step_name='complete', ...)
       └── UPDATE task_runs SET status='completed',
                               rows_fetched=X, rows_inserted=Y, ...

5. UPDATE SCHEDULE (if scheduled)
   └── UPDATE task_schedules SET last_run_date=NOW(),
                                next_run_date=calculated
```

---

## Phase 5 — Code Reading Strategy

### Recommended Reading Order

#### 1. API Routes / Controllers
```
backend/app/api/v1/routes/tasks.py        # Start here - understand CRUD
backend/app/api/v1/routes/runs.py         # How execution is triggered
backend/app/api/v1/routes/column_mappings.py  # Field mapping management
backend/app/api/v1/routes/schedules.py    # Cron scheduling
```

#### 2. Services / Use-Cases
```
backend/app/services/runner.py            # CRITICAL - main pipeline
backend/app/services/api_connector.py     # External API communication
backend/app/services/validator.py         # Data validation
backend/app/services/mapper.py            # Field transformation
```

#### 3. Models / Schemas
```
backend/app/db/models/task.py             # Core entity
backend/app/db/schemas/task.py            # Request/response validation
```

#### 4. Frontend API Clients
```
frontend/src/api/client.ts                # HTTP client
frontend/src/hooks/api.ts                 # React Query hooks
```

#### 5. Frontend State Management
```
frontend/src/hooks/api.ts                 # React Query (server state)
frontend/src/pages/*.tsx                  # Local component state
```

### "If X Breaks, Where Do I Look?"

| Symptom | Primary Location | Secondary Location |
|---------|------------------|-------------------|
| Task creation fails | `routes/tasks.py:create_task()` | `schemas/task.py:TaskCreate` |
| API fetch returns empty | `services/api_connector.py:fetch()` | Task auth_config |
| Mapping fails | `services/mapper.py:apply_mapping()` | `column_mappings` table |
| Validation errors | `services/validator.py:validate_row()` | `oracle_metadata.py` |
| Insert fails | `services/runner.py:_insert_single_row()` | Oracle constraints |
| Upsert not working | `services/runner.py:process_rows_with_upsert()` | `upsert_keys` config |
| Skip not working | `services/runner.py:_should_skip()` | `skip_column`, `skip_value` |
| Schedule not firing | `services/scheduler.py:add_job()` | APScheduler logs |
| Frontend not loading data | `hooks/api.ts` | `api/client.ts` |
| 500 errors | Backend logs | `routes/*.py` exception handlers |

### Call Stack Examples

**Task Execution Call Stack:**
```
POST /tasks/{id}/run
  └── runs.py:trigger_run()
      └── celery_app.send_task('run_import')
          └── runner.py:run_import()
              ├── api_connector.py:fetch()
              │   └── httpx.get() / httpx.post()
              ├── normalizer.py:flatten()
              ├── mapper.py:apply_mapping()
              ├── validator.py:validate_row()
              └── process_rows_with_upsert()
                  ├── _should_skip()
                  ├── _find_existing_record()
                  └── _insert_single_row() / _update_existing_row()
```

**Frontend Data Flow:**
```
Dashboard.tsx:useTaskStats()
  └── hooks/api.ts:useTaskStats()
      └── client.ts:taskApi.getStats()
          └── axios.get('/api/v1/tasks/stats')
              └── routes/tasks.py:get_stats()
                  └── SQLAlchemy aggregate query
```

---

## Phase 6 — Audit: Quality, Security, Maintainability

### Error Handling Assessment

| Area | Status | Issues |
|------|--------|--------|
| API Routes | GOOD | Proper HTTPException usage |
| Service Layer | GOOD | Try-catch with logging |
| External API Calls | GOOD | Timeout handling, retry logic |
| Database Operations | GOOD | Transaction rollback on failure |
| Frontend | GOOD | Error boundaries, toast notifications |
| Silent Failures | CONCERN | Some errors logged but not surfaced |

**Specific Concerns:**
- `connection_service.py:60` - Decryption failure returns empty dict silently
- `runner.py` - Row errors logged but run can still show "completed"

### Auth & Authorization Boundaries

| Check | Status | Risk Level |
|-------|--------|------------|
| User Authentication | NOT IMPLEMENTED | HIGH |
| Role-Based Access | NOT IMPLEMENTED | HIGH |
| API Key Protection | N/A | - |
| Auth Credentials Storage | ENCRYPTED | LOW |
| Session Management | N/A | - |

**CRITICAL FINDING:** No authentication/authorization system. All endpoints are publicly accessible.

### Input Validation

| Layer | Validation Type | Status |
|-------|-----------------|--------|
| API Request Body | Pydantic models | GOOD |
| Query Parameters | Type hints | GOOD |
| Path Parameters | FastAPI validation | GOOD |
| External API Response | Basic JSON parsing | MODERATE |
| Database Input | SQLAlchemy types | GOOD |
| File Paths | Not applicable | - |

### Secrets Handling

| Secret Type | Storage | Risk |
|-------------|---------|------|
| Oracle Password | .env file | MODERATE (should be vault) |
| API Auth Tokens | Database (JSON) | LOW (in-transit only) |
| DB Connections | Encrypted file | LOW (Fernet encryption) |
| SECRET_KEY | .env file | MODERATE (should be vault) |

### Logging and Observability

| Aspect | Status | Implementation |
|--------|--------|----------------|
| Request Logging | PARTIAL | No request ID tracking |
| Error Logging | GOOD | Loguru with stack traces |
| Audit Trail | GOOD | task_logs, task_run_logs tables |
| Metrics | NOT IMPLEMENTED | No Prometheus/StatsD |
| Tracing | NOT IMPLEMENTED | No distributed tracing |

### Test Coverage Assessment

| Area | Unit Tests | Integration Tests | Coverage |
|------|------------|-------------------|----------|
| Services | 9 files | 4 files | ~70% |
| Routes | Via integration | 4 files | ~60% |
| Models | 1 file | Via integration | ~50% |
| Frontend | 12 files | - | ~40% |

### Prioritized Audit Report

#### DANGEROUS (Data Loss, Security)

| ID | Issue | Location | Risk | Recommendation |
|----|-------|----------|------|----------------|
| D1 | No Authentication | All routes | CRITICAL | Implement JWT/OAuth |
| D2 | No Authorization | All routes | CRITICAL | Add RBAC middleware |
| D3 | Secrets in .env | .env file | HIGH | Use HashiCorp Vault |
| D4 | No Rate Limiting | API routes | HIGH | Add rate limiting middleware |

#### FRAGILE (Hard to Change)

| ID | Issue | Location | Impact | Recommendation |
|----|-------|----------|--------|----------------|
| F1 | Tight coupling runner.py | runner.py | HIGH | Extract strategies |
| F2 | Large TaskWizard component | TaskWizard.tsx | MEDIUM | Split into sub-components |
| F3 | No dependency injection | Services | MEDIUM | Add DI container |
| F4 | Hardcoded Oracle dialect | Multiple files | MEDIUM | Abstract DB layer |

#### COSMETIC (Low Priority)

| ID | Issue | Location | Impact | Recommendation |
|----|-------|----------|--------|----------------|
| C1 | Inconsistent error messages | Various | LOW | Standardize format |
| C2 | Missing docstrings | Some functions | LOW | Add documentation |
| C3 | Console.log statements | Frontend | LOW | Remove or use logger |
| C4 | Unused imports | Various files | LOW | Run linter cleanup |

### Security Recommendations Summary

1. **Immediate (P0):**
   - Implement authentication (JWT recommended)
   - Add authorization middleware
   - Enable HTTPS enforcement

2. **Short-term (P1):**
   - Move secrets to vault
   - Add rate limiting
   - Implement request validation size limits

3. **Medium-term (P2):**
   - Add audit logging for all write operations
   - Implement session management
   - Add CSRF protection

---

## Appendix A: File Path Quick Reference

```
BACKEND ROOT: /home/user/IntakeGateway/backend/

Configuration:
├── app/core/config.py           # Settings management
├── app/main.py                  # FastAPI application
├── app/celery_app.py            # Celery configuration
└── requirements.txt             # Python dependencies

API Layer:
└── app/api/v1/routes/
    ├── tasks.py                 # /api/v1/tasks
    ├── runs.py                  # /api/v1/runs
    ├── column_mappings.py       # /api/v1/tasks/{id}/mappings
    └── schedules.py             # /api/v1/schedules

Service Layer:
└── app/services/
    ├── runner.py                # Main execution pipeline
    ├── api_connector.py         # External API calls
    ├── mapper.py                # Field mapping
    ├── validator.py             # Data validation
    ├── normalizer.py            # JSON flattening
    ├── oracle_metadata.py       # Schema discovery
    ├── transform_suggester.py   # Type suggestions
    ├── scheduler.py             # APScheduler
    └── connection_service.py    # Encrypted storage

Data Layer:
└── app/db/
    ├── database.py              # Session management
    ├── models/                  # SQLAlchemy models
    └── schemas/                 # Pydantic schemas

Tests:
└── tests/
    ├── unit/                    # Unit tests (9 files)
    └── integration/             # Integration tests (4 files)

FRONTEND ROOT: /home/user/IntakeGateway/frontend/

Source:
└── src/
    ├── pages/                   # Page components (7 files)
    ├── components/              # Reusable components
    │   ├── ui/                  # Base UI components
    │   ├── ColumnMappingEditor.tsx
    │   ├── ScheduleEditor.tsx
    │   └── UpsertConfigEditor.tsx
    ├── hooks/api.ts             # React Query hooks
    ├── api/client.ts            # Axios client
    ├── types/index.ts           # TypeScript types
    └── App.tsx                  # Router configuration

Tests:
└── src/__tests__/
    ├── pages/                   # Page tests
    └── components/              # Component tests
```

---

## Appendix B: Environment Variables Reference

```bash
# Required
ORACLE_USER=           # Oracle database username
ORACLE_PASSWORD=       # Oracle database password
ORACLE_HOST=           # Oracle host (IP or hostname)
ORACLE_PORT=1521       # Oracle port (default: 1521)
ORACLE_SERVICE_NAME=   # Oracle service name

# Required (Security)
SECRET_KEY=            # Encryption key (min 32 chars for production)

# Optional
APP_NAME=intake-gateway
APP_ENV=dev            # dev, staging, production
APP_LOG_LEVEL=INFO     # DEBUG, INFO, WARNING, ERROR
APP_TIMEZONE=UTC       # Timezone for scheduling

# Redis (required for Celery)
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=${REDIS_URL}

# HTTP Client
HTTP_TIMEOUT_SECONDS=30
HTTP_MAX_RESPONSE_MB=10

# Alternative Oracle connection (instead of individual params)
ORACLE_DSN=            # Full Oracle DSN string
```

---

*Document generated by Claude Code - February 4, 2026*
