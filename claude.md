# IntakeGateway: Project Context & Development Guidelines

**Last Updated**: April 13, 2026
**Project Status**: Phase 4 Complete | Phase 5 Complete | Phase 6 Complete | Phase 7 Complete | Phase 8 Complete | Phase 9 Complete (Ant Design Migration)
**AI Assistant Guide**: Use this document to understand the project architecture, conventions, and development practices.

---

## 📋 Project Overview

**IntakeGateway** is a full-stack web application that enables users to:
- Create data import tasks that fetch from external APIs
- Configure API endpoints with headers, authentication, and request bodies
- Map API response fields to database columns
- Trigger task executions and monitor runs
- View detailed logs, statistics, and error reports

### Technology Stack

**Backend**:
- Python 3.11 with FastAPI
- SQLAlchemy ORM with Oracle Database (11g+ compatible)
- Celery for async task execution
- APScheduler for cron-based task scheduling
- Pydantic for data validation
- pytest for testing (13 test files: 7 unit + 6 integration)

**Frontend**:
- React 18.2 with TypeScript 5.3
- Vite 5.0 build tool
- React Router v6
- React Query 5.28 (TanStack Query) for server state management
- **Ant Design 5** UI component library (migrated from Radix UI + Tailwind in Phase 9)
- **@ant-design/icons** for iconography
- **dayjs** for date handling
- Vitest + React Testing Library for testing (14 test files)

---

## 🏗️ Architecture Overview

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Browser                              │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              React Frontend (Port 5173)                   │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐    │   │
│  │  │   Dashboard │  │   TaskList   │  │  RunDetail   │    │   │
│  │  └──────┬──────┘  └──────┬───────┘  └──────┬───────┘    │   │
│  │         │                │                 │             │   │
│  │  ┌──────────────────────────────────────────────┐        │   │
│  │  │     React Query (Hooks + Cache)             │        │   │
│  │  └──────────────────┬─────────────────────────┘        │   │
│  │                     │                                    │   │
│  └─────────────────────┼────────────────────────────────────┘   │
│                        │ HTTP/HTTPS                             │
│                        ▼                                         │
├─────────────────────────────────────────────────────────────────┤
│                      Network/Internet                            │
└─────────────────────────────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│               FastAPI Backend (Port 8000)                        │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │          API Routes (v1)                                 │   │
│  │  ┌──────────┐  ┌──────────┐  ┌────────────┐             │   │
│  │  │  /tasks  │  │  /runs   │  │ /stats     │             │   │
│  │  └────┬─────┘  └────┬─────┘  └─────┬──────┘             │   │
│  └───────┼─────────────┼──────────────┼────────────────────┘   │
│          │             │              │                         │
│  ┌───────▼─────────────▼──────────────▼────────────────────┐   │
│  │          Service Layer                                  │   │
│  │  ┌─────────────────────────────────────────────────┐   │   │
│  │  │ • TaskService    (CRUD, validation)             │   │   │
│  │  │ • RunService     (execution, monitoring)        │   │   │
│  │  │ • ApiConnector   (external API calls)           │   │   │
│  │  │ • Mapper         (field mapping logic)          │   │   │
│  │  │ • Normalizer     (data transformation)          │   │   │
│  │  │ • Validator      (data validation)              │   │   │
│  │  └─────────────────┬──────────────────────────────┘   │   │
│  └────────────────────┼──────────────────────────────────┘   │
│                       │                                        │
│  ┌────────────────────▼──────────────────────────────────┐   │
│  │          Celery Task Queue                            │   │
│  │  • Background task execution                         │   │
│  │  • Async run processing                              │   │
│  │  • Task scheduling                                   │   │
│  └────────────────────┬──────────────────────────────────┘   │
│                       │                                        │
│  ┌────────────────────▼──────────────────────────────────┐   │
│  │          Database Layer (SQLAlchemy)                 │   │
│  │  ┌──────────────┐  ┌──────────────┐                  │   │
│  │  │  Task Model  │  │  Run Model   │                  │   │
│  │  └──────────────┘  └──────────────┘                  │   │
│  └────────────────────┬──────────────────────────────────┘   │
│                       │                                        │
└───────────────────────┼────────────────────────────────────────┘
                        ▼
            ┌───────────────────────┐
            │   Oracle Database     │
            │  (Production Data)    │
            └───────────────────────┘
```

### Data Flow

1. **User Creates Task**:
   - Frontend → POST /api/v1/tasks → Backend creates Task record
   - Task stored in database with configuration

2. **User Triggers Run**:
   - Frontend → POST /api/v1/runs → Backend creates Run record
   - Celery worker picks up async task
   - Worker calls ApiConnector to fetch data
   - Data normalized and validated
   - Fields mapped according to configuration
   - Results saved to database

3. **User Views Run Details**:
   - Frontend → GET /api/v1/runs/{run_id} → Backend retrieves Run with logs and errors

---

## 📁 Directory Structure

### Backend (`backend/`)

```
backend/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   │
│   ├── api/
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── routes/
│   │           ├── runs.py           # Run endpoints (GET, POST, detail)
│   │           ├── tasks.py          # Task endpoints (CRUD)
│   │           ├── schedules.py      # Schedule endpoints (CRUD)
│   │           ├── column_mappings.py # Column mapping endpoints
│   │           └── __init__.py
│   │
│   ├── core/
│   │   ├── config.py           # App configuration
│   │   ├── logging.py          # Logging setup
│   │   └── __init__.py
│   │
│   ├── db/
│   │   ├── oracle_pool.py      # Oracle connection pooling
│   │   ├── session.py          # Database session management
│   │   ├── models/
│   │   │   ├── task.py         # Task ORM model
│   │   │   ├── task_run.py     # TaskRun ORM model
│   │   │   └── __init__.py
│   │   ├── schemas/
│   │   │   ├── task.py         # Pydantic schemas for Task
│   │   │   └── __init__.py
│   │   └── sql/
│   │       └── schema.sql      # Database schema definition
│   │
│   ├── services/
│   │   ├── api_connector.py    # External API communication
│   │   ├── mapper.py           # Field mapping logic
│   │   ├── normalizer.py       # Data transformation
│   │   ├── runner.py           # Task execution logic
│   │   ├── scheduler.py        # Task scheduling
│   │   ├── validator.py        # Data validation
│   │   └── __init__.py
│   │
│   └── workers/
│       ├── celery_app.py       # Celery configuration
│       ├── tasks.py            # Celery task definitions
│       └── __init__.py
│
├── tests/
│   ├── unit/
│   │   ├── test_placeholder.py
│   │   ├── test_models.py
│   │   ├── test_mapper.py
│   │   ├── test_normalizer.py
│   │   ├── test_validator.py
│   │   ├── test_runner.py
│   │   ├── test_column_mappings.py
│   │   └── test_authentication.py
│   └── integration/
│       ├── test_api_endpoints.py
│       ├── test_schedule_routes.py
│       ├── test_mapping_pipeline.py
│       └── test_full_pipeline.py
│
├── pyproject.toml              # Poetry dependencies
├── requirements.txt            # pip requirements
├── Dockerfile                  # Docker image
└── README.md
```

### Frontend (`frontend/`)

```
frontend/
├── src/
│   ├── pages/                  # Page components (8 pages)
│   │   ├── Dashboard.tsx       # KPI cards, recent runs table, quick actions
│   │   ├── TaskList.tsx        # Card-based task list with actions
│   │   ├── TaskDetail.tsx      # Tabbed view (Details, Schedule, Mappings)
│   │   ├── TaskWizard.tsx      # 6-step task creation wizard (Steps component)
│   │   ├── RunsList.tsx        # Runs table with status tags
│   │   ├── RunDetail.tsx       # Statistics, logs, error breakdown
│   │   ├── Schedules.tsx       # Schedule table with filter controls
│   │   └── Settings.tsx        # Database connection management
│   │
│   ├── components/             # Editor components
│   │   ├── ColumnMappingEditor.tsx  # Field mapping with tree view
│   │   ├── ConnectionEditor.tsx     # DB connection form
│   │   ├── ScheduleEditor.tsx       # Cron schedule form
│   │   └── UpsertConfigEditor.tsx   # Upsert/skip configuration
│   │
│   ├── hooks/
│   │   └── api.ts              # React Query hooks (all entities)
│   │
│   ├── api/
│   │   └── client.ts           # Axios HTTP client (all endpoints)
│   │
│   ├── types/
│   │   └── index.ts            # TypeScript interfaces (all types)
│   │
│   ├── lib/
│   │   └── utils.ts            # Date parsing/formatting utilities
│   │
│   ├── __tests__/              # Test suite (14 test files)
│   │   ├── setup.ts            # jest-dom setup
│   │   ├── components/
│   │   │   ├── ColumnMappingEditor.test.tsx
│   │   │   ├── ConnectionEditor.test.tsx
│   │   │   ├── ScheduleEditor.test.tsx
│   │   │   └── ScheduleTab.test.tsx
│   │   └── pages/
│   │       ├── Dashboard.test.tsx
│   │       ├── TaskList.test.tsx
│   │       ├── TaskDetail.test.tsx
│   │       ├── RunsList.test.tsx
│   │       ├── RunDetail.test.tsx
│   │       ├── Schedules.test.tsx
│   │       ├── Settings.test.tsx
│   │       ├── TaskWizard.test.tsx
│   │       ├── TaskWizard-Mapping.test.tsx
│   │       └── TaskWizardAuth.test.tsx
│   │
│   ├── theme.ts                # Ant Design theme configuration (ConfigProvider)
│   ├── App.tsx                 # Routing + AntD Layout (Sider, Menu, Content)
│   ├── main.tsx                # Entry point
│   └── index.css               # Minimal global styles
│
├── PROMPT.md                   # Ant Design UI specification
├── vite.config.ts              # Vite configuration
├── tsconfig.json               # TypeScript configuration
├── vitest.config.ts            # Vitest configuration
├── package.json
└── README.md
```

---

## 🔌 API Endpoints

### Task Management

```
GET    /api/v1/tasks                    # List all tasks (paginated)
GET    /api/v1/tasks/{task_id}          # Get task details
POST   /api/v1/tasks                    # Create new task
PATCH  /api/v1/tasks/{task_id}          # Update task
DELETE /api/v1/tasks/{task_id}          # Delete task
```

### Run Management

```
GET    /api/v1/runs                     # List all runs (paginated)
GET    /api/v1/runs/{run_id}            # Get run details
POST   /api/v1/runs                     # Trigger new run
```

**Run labels**: Run responses include `task_name`, `is_retry`, and `retry_of_run_id` for UI labeling and retry badges.

### Schedule Management

```
GET    /api/v1/schedules                # List all schedules
POST   /api/v1/tasks/{task_id}/schedule # Create schedule for task
GET    /api/v1/tasks/{task_id}/schedule # Get task schedule
PUT    /api/v1/schedules/{schedule_id}  # Update schedule
DELETE /api/v1/schedules/{schedule_id}  # Delete schedule
POST   /api/v1/schedules/{id}/resume    # Resume paused schedule
```

### Column Mapping Management

```
GET    /api/v1/tasks/{task_id}/mappings        # List mappings
POST   /api/v1/tasks/{task_id}/mappings        # Bulk create mappings
PUT    /api/v1/mappings/{mapping_id}           # Update mapping
DELETE /api/v1/mappings/{mapping_id}           # Delete mapping
POST   /api/v1/tasks/{task_id}/preview-fields  # Fetch sample API response
GET    /api/v1/oracle/tables/{table}/columns   # Query Oracle metadata
```

### Statistics

```
GET    /api/v1/stats/tasks              # Task statistics
GET    /api/v1/stats/runs               # Run statistics
```

---

## 💾 Database Schema

### Task Table

```sql
CREATE TABLE tasks (
    id VARCHAR2(36) PRIMARY KEY,
    name VARCHAR2(255) NOT NULL,
    description CLOB,
    endpoint_url VARCHAR2(2000) NOT NULL,
    method VARCHAR2(10) NOT NULL,
    headers CLOB,                  -- JSON
    body CLOB,                     -- JSON
    table_name VARCHAR2(255) NOT NULL,
    field_mapping CLOB,            -- JSON
    is_active NUMBER(1) DEFAULT 1,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### TaskRun Table

```sql
CREATE TABLE task_runs (
    id VARCHAR2(36) PRIMARY KEY,
    task_id VARCHAR2(36) NOT NULL,
    status VARCHAR2(50) NOT NULL,  -- running, completed, failed, partial_failure
    total_records NUMBER,
    successful_records NUMBER,
    failed_records NUMBER,
    error_details CLOB,            -- JSON
    logs CLOB,                     -- JSON
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);
```

---

## 🔄 Key Components & Patterns

### Backend Patterns

#### 1. Service Layer Architecture
- All business logic in `/services/` directory
- Each service handles one domain (Mapper, Validator, etc.)
- Services are testable and reusable

#### 2. Pydantic Models
- All input validation through Pydantic schemas
- Type hints on all functions
- Request/response models in `/db/schemas/`

#### 3. Dependency Injection
- FastAPI dependencies for database session
- Clean separation of concerns
- Easy to test with mocks

#### 4. Async Task Processing
- Long-running operations via Celery
- Non-blocking API responses
- Background workers handle heavy lifting

### Frontend Patterns

#### 1. React Query Hooks
- All data fetching through hooks
- Centralized cache management
- Automatic refetching strategies

#### 2. Component Structure
- Page components handle routing
- UI components are presentational
- Custom hooks for logic

#### 3. Type Safety
- 100% TypeScript coverage
- Strict mode enabled
- All API responses typed

#### 4. Error Handling
- Centralized error handling in ApiClient
- Error boundaries on pages
- User-friendly error messages

---

## 🧪 Testing Strategies

### Backend Testing

**Location**: `backend/tests/unit/`

**Coverage Areas**:
- Model validation (test_models.py)
- Data mapping (test_mapper.py)
- Data normalization (test_normalizer.py)
- Data validation (test_validator.py)

**Running Tests**:
```bash
cd backend
pytest tests/unit/ -v --tb=short
```

**Test Count**: 110+ tests passing

### Frontend Testing

**Location**: `frontend/src/__tests__/`

**Coverage Areas**:
- Component rendering
- Hook behavior
- User interactions
- Error handling
- Navigation
- Schedule management
- Column mapping

**Test Files**:
- Dashboard.test.tsx
- TaskList.test.tsx
- TaskDetail.test.tsx
- RunsList.test.tsx
- RunDetail.test.tsx
- TaskWizard.test.tsx
- TaskWizard-Mapping.test.tsx
- TaskWizardAuth.test.tsx
- Schedules.test.tsx
- ColumnMappingEditor.test.tsx
- ScheduleEditor.test.tsx
- ScheduleTab.test.tsx

**Running Tests**:
```bash
cd frontend
npm run test
```

**Test Files**: 12 test files

---

## 📋 Coding Conventions

### Python (Backend)

```python
# Type hints required
def process_data(data: dict) -> dict:
    """Process data according to mapping."""
    pass

# Docstrings for functions
class TaskService:
    """Service for task operations."""
    
    async def create_task(self, task_data: TaskCreate) -> Task:
        """Create a new task."""
        pass

# Use constants at module level
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3

# Logging instead of print
logger.info(f"Task {task_id} started")
```

### TypeScript/React (Frontend)

```typescript
// All components typed
interface TaskListProps {
    tasks: Task[];
    onDelete: (id: string) => void;
}

// Hooks follow naming convention
const useTaskData = (id: string) => {
    return useQuery({...});
};

// Comments for complex logic
// Calculate success rate: successful / total
const successRate = (successful / total) * 100;

// Use constants for magic strings
const TASK_STATUS = {
    ACTIVE: 'active',
    INACTIVE: 'inactive',
} as const;
```

---

## 🚀 Development Workflow

### Starting Development

**Backend**:
```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

**Frontend**:
```bash
cd frontend
npm install
npm run dev
```

### Setup Troubleshooting

**Common Issues & Fixes (Updated January 2026)**:

1. **PostCSS ES Module Error**
   ```bash
   # Error: "module is not defined in ES module scope"
   # Fix: Rename postcss.config.js to .cjs extension
   cd frontend
   mv postcss.config.js postcss.config.cjs
   ```
   - **Why**: package.json has `"type": "module"`, requiring .cjs extension for CommonJS files

2. **Radix UI Installation Failure**
   ```bash
   # Error: "No matching version found for @radix-ui/react-slot@^2.0.2"
   # Fix: Update package.json to use version 1.1.0
   ```
   - In `frontend/package.json`, ensure: `"@radix-ui/react-slot": "^1.1.0"`
   - Version 2.x is not yet available in npm registry

3. **Missing date-fns Dependency**
   ```bash
   # Error: "date-fns imported but could not be resolved"
   cd frontend
   npm install date-fns
   ```

4. **Backend Missing uvicorn**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

**Access Points**:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Making Changes

1. **Create feature branch**
   ```bash
   git checkout -b feature/description
   ```

2. **Make changes** to backend or frontend
   - Follow coding conventions above
   - Add tests for new functionality
   - Update types/interfaces

3. **Run tests**
   ```bash
   # Backend
   cd backend && pytest tests/ -v
   
   # Frontend
   cd frontend && npm run test
   ```

4. **Commit changes**
   ```bash
   git add .
   git commit -m "feat: description of changes"
   ```

### Important Notes

- **Never commit to main directly**
- **All tests must pass** before merging
- **Update types** whenever changing data structures
- **Keep commits atomic** (one feature per commit)
- **Write clear commit messages**

---

## 🔐 Authentication & Security

### Current Implementation
- No authentication in Phase 5 (ready for Phase 6)
- CORS configured for localhost development
- API validation through Pydantic models

### Future Implementation (Phase 6)
- JWT token-based authentication
- Role-based access control (RBAC)
- API key for service-to-service
- Encrypted sensitive data storage

---

## 📊 Performance Considerations

### Backend
- Connection pooling for Oracle Database
- Async operations with Celery
- Query optimization with proper indexing
- Caching strategies (future enhancement)

### Frontend
- Code splitting by route
- Lazy loading components
- React Query caching
- Bundle size: < 100KB (gzipped)

### Database
- Task and run tables indexed on id
- Status queries use indexed columns
- Pagination prevents loading all records

---

## 🐛 Common Issues & Solutions

### Backend Issues

**Issue**: Oracle connection fails
```python
# Solution: Check connection string in config.py
ORACLE_URL = "oracle+cx_oracle://user:password@host:1521/service"
```

**Issue**: Celery tasks not executing
```bash
# Solution: Start Celery worker
celery -A app.workers.celery_app worker --loglevel=info
```

### Frontend Issues

**Issue**: API calls fail with CORS error
```
# Solution: Ensure backend CORS is configured for localhost:5173
```

**Issue**: Tests fail with "module not found"
```bash
# Solution: Clear node_modules and reinstall
rm -rf node_modules
npm install
```

---

## 📚 Key Files to Know

### Backend
- `app/main.py` - FastAPI app setup
- `app/api/v1/routes/tasks.py` - Task routes
- `app/api/v1/routes/runs.py` - Run routes
- `app/services/*.py` - Business logic
- `app/db/models/` - Database models
- `app/db/schemas/` - Pydantic schemas

### Frontend
- `src/App.tsx` - Routing setup
- `src/api/client.ts` - API client
- `src/hooks/api.ts` - React Query hooks
- `src/pages/*.tsx` - Page components
- `src/components/ui/*.tsx` - UI components

---

## 🔗 Documentation Links

- [Phase 5 Completion Report](PHASE_5_COMPLETION_REPORT.md)
- [Frontend Setup Guide](frontend/FRONTEND_SETUP_GUIDE.md)
- [Testing Guide](PHASE_5_TESTING_GUIDE.md)
- [Architecture Guide](frontend/FRONTEND_ARCHITECTURE.md)
- [Documentation Index](DOCUMENTATION_INDEX.md)

---

## 📞 Development Guidelines for AI Assistants

### When Making Changes

1. **Understand Context First**
   - Read relevant documentation
   - Check existing patterns
   - Review related files

2. **Type Safety**
   - Always use TypeScript/Python types
   - Update interfaces when changing data
   - Verify no type errors after changes

3. **Testing**
   - Add tests for new functionality
   - Update existing tests if needed
   - Run full test suite before completing

4. **Code Quality**
   - Follow existing code style
   - Add comments for complex logic
   - Keep functions focused and testable

5. **Documentation**
   - Update README if public API changes
   - Add comments to complex sections
   - Keep this claude.md updated with major changes

### Git Workflow

```bash
# Always work on feature branch
git checkout -b feature/name

# Make changes, test, commit
git add .
git commit -m "feat: description"

# Never force push to main
git push origin feature/name
```

### When Debugging

1. Check error messages carefully
2. Review relevant code sections
3. Add logging/console output
4. Test with minimal reproducible case
5. Refer to documentation

### When Adding Features

1. Understand requirements completely
2. Design changes (data structure, API, UI)
3. Implement with tests
4. Update documentation
5. Verify all tests pass

---

## 🎯 Phase 6: Column Mapping Enhancement (Complete)

### Overview

Phase 6 adds comprehensive column mapping functionality to enable users to map API response fields (including nested JSON) to database columns during task creation. Features advanced UI with hierarchical field display, automatic type detection, transform suggestions, and mapping templates.

### Phase 6 Architecture

#### Backend Components

**New API Routes** (`app/api/v1/routes/column_mappings.py`):
- `GET /api/v1/tasks/{task_id}/mappings` - List mappings
- `POST /api/v1/tasks/{task_id}/mappings` - Bulk create mappings
- `PUT /api/v1/mappings/{mapping_id}` - Update mapping
- `DELETE /api/v1/mappings/{mapping_id}` - Delete mapping
- `POST /api/v1/tasks/{task_id}/preview-fields` - Fetch sample API response (manual/auto)
- `GET /api/v1/oracle/tables/{table_name}/columns` - Query Oracle metadata

**New Services**:
- `oracle_metadata.py` - Query Oracle `USER_TAB_COLUMNS` for table schema
- `transform_suggester.py` - Recommend transforms based on type mismatches
- Enhanced `api_connector.py` - Fetch sample responses with lenient JSON parsing

**Enhanced Models**:
- `column_mapping.py` - ColumnMapping ORM model (already exists, exposed via API)
- `mapper.py` - Added transforms: `to_timestamp`, `to_date`, `format_date`

**Pydantic Schemas** (`app/db/schemas/column_mapping.py` - NEW):
- `ColumnMappingCreate` - Input for creating mappings
- `ColumnMappingOut` - API response model
- `ColumnMappingUpdate` - Update payload
- `BulkMappingCreate` - Batch create multiple mappings

#### Frontend Components

**New Types** (`src/types/index.ts`):
- `ColumnMapping` interface (with metadata)
- `MappingPreview` interface (hierarchical tree structure)
- `OracleColumn` interface (column name + type)
- `FieldNode` interface (tree node with parent/children)

**New Component** (`src/components/ColumnMappingEditor.tsx`):
- Three-column layout: API Fields | Mapping Config | DB Columns
- Hierarchical tree view of nested fields (expandable)
- Copy-to-clipboard dot notation for each field (e.g., `user.address.city`)
- Add/remove mapping rows with dropdowns
- Transform multi-select dropdowns (8 available)
- Auto-suggest transform badges with click-to-apply
- Fetch sample button (auto-fetch OR manual paste)
- Save all mappings button
- Template save/load (localStorage)
- Unmapped fields warning badge

**Enhanced TaskWizard** (`src/pages/TaskWizard.tsx`):
- New Step 4.5: "Mapping Configuration"
- Embeds `<ColumnMappingEditor />` component
- At least 1 mapping required (blocking validation)
- Unmapped fields warning (non-blocking)
- "Skip for Now" option (creates task without mappings)
- Mappings saved to component state on "Next" click

**Enhanced TaskDetail** (`src/pages/TaskDetail.tsx`):
- New "Configure Mappings" tab/accordion
- Reuses `<ColumnMappingEditor />` component
- Advanced Options section:
  - "Save as Template" button (save to localStorage)
  - "Load Template" dropdown
  - "Auto-Match by Name" toggle (case-insensitive name matching)
  - "Apply Transform to All Strings" (batch operation)
  - "Clear All Mappings" button

**New Hooks** (`src/hooks/api.ts`):
- `useColumnMappings(taskId)` - Fetch mappings list
- `useCreateMappings()` - Bulk create mappings
- `useUpdateMapping()` - Update single mapping
- `useDeleteMapping()` - Delete mapping
- `usePreviewFields(taskId, sampleJson?)` - Fetch flattened fields
- `useOracleColumns(tableName)` - Query DB columns
- `useSuggestTransforms(sourceType, destType)` - Transform suggestions
- `useSaveMappingTemplate()` - Save to localStorage

### Key Features

#### 1. Nested JSON Support
- **Automatic Flattening**: Converts nested objects to dot notation (e.g., `{"user": {"name": "Alice"}}` → `{"user.name": "Alice"}`)
- **Hierarchical Display**: Tree view shows nested structure intuitively
- **Copy-to-Clipboard**: Each leaf node has button to copy full path (e.g., `user.address.city`)
- **Multiple Nesting Levels**: Supports arbitrarily deep nesting

#### 2. Type-Aware Mapping
- **Auto-Detection**: Infers field types from sample API response (string, number, boolean, null, array, object)
- **Oracle Metadata**: Queries database for column types from `USER_TAB_COLUMNS`
- **Transform Suggestions**: Shows recommendations when types mismatch (e.g., string → number suggests `to_int`)
- **Visual Warnings**: Yellow badge alerts when manual transform needed

#### 3. Transform Options
```
Available transforms:
- trim          (remove whitespace)
- upper         (uppercase)
- lower         (lowercase)
- to_int        (parse integer)
- to_float      (parse float)
- to_bool       (parse boolean)
- to_timestamp  (ISO 8601 → Oracle TIMESTAMP)
- to_date       (YYYY-MM-DD → Oracle DATE)
```

#### 4. Mapping Persistence Strategy
- **During Wizard**: Saved to component state on "Next" button (not real-time)
- **After Creation**: Mappings sent with bulk create request during task creation
- **In TaskDetail**: Updates trigger individual API calls with optimistic updates

#### 5. Template Management (localStorage)
- **Save Template**: Save current mappings to browser storage with custom name
- **Load Template**: Dropdown to apply saved templates
- **Delete Template**: Remove stored templates
- **Scope**: Per-browser, not shared (Phase 2 enhancement planned)

#### 6. Batch Operations
- **Apply Transform**: Select transform, apply to all string fields
- **Auto-Match**: Create mappings for fields matching DB column names (case-insensitive)
- **Clear All**: Reset all mappings (confirmation dialog)

### Sample Response Fetching

**Manual Paste Mode**:
1. User clicks "Fetch Sample"
2. Modal opens with "Manual Paste" tab
3. User pastes JSON response
4. System attempts to parse JSON
5. If invalid: Shows error message with issue description (line/column)
6. User corrects and retries
7. On success: Displays flattened fields in tree view

**Auto-Fetch Mode**:
1. User clicks "Fetch Sample" → "Auto-Fetch" tab
2. System makes test API call using task's configured endpoint/headers
3. Extracts records using JSONPath
4. Returns sample with flattened field structure
5. Shows field types and sample values

### Error Handling & Fallbacks

**Pydantic Issues**:
If Pydantic import/compatibility errors arise, fallback to alternative validation libraries:

| Library | Migration Effort | When to Use |
|---------|------------------|------------|
| Dataclasses | ~30-45 min | Default fallback (stdlib, no dependencies) |
| Attrs | ~1-2 hours | If need rich validation + type hints |
| Marshmallow | ~2-3 hours | If need SQLAlchemy deep integration |

**Oracle Metadata Querying**:
- Graceful degradation: If `USER_TAB_COLUMNS` query fails (permissions), show manual entry fallback
- Logs permission errors for debugging

**Nested JSON Parsing**:
- Handles null values, empty objects, primitive types consistently
- Doesn't flatten arrays (kept as-is for Phase 1)
- Arrays within objects preserved (Phase 2 enhancement: array explosion)

### Testing Strategy (Phase 6)

**Unit Tests** (`backend/tests/unit/test_column_mappings.py`):
- API endpoint validation
- Transform suggestions logic
- Oracle metadata querying
- JSON parsing with lenient error handling
- 15+ test cases

**Integration Tests** (`backend/tests/integration/test_mapping_pipeline.py`):
- End-to-end nested JSON flattening
- Multi-level nesting (3-4 levels)
- Mapping creation and application
- Transform chaining
- 8+ test cases

**Frontend Tests** (`frontend/src/__tests__/components/ColumnMappingEditor.test.tsx`):
- Field preview rendering
- Tree view expansion/collapse
- Mapping CRUD operations
- Transform selection
- Template save/load
- Auto-suggest transform triggers
- 10+ test cases

**Frontend Integration Tests** (`frontend/src/__tests__/pages/TaskWizard-Mapping.test.tsx`):
- Wizard step 4.5 navigation
- Validation blocking without mappings
- Warning with unmapped fields
- State persistence
- Skip for now functionality
- 8+ test cases

**Total Target**: 25+ new tests

### Implementation Timeline

**Step 1**: Backend column mapping API + schemas (2-3 hours)
**Step 2**: Oracle metadata service (1-2 hours)
**Step 3**: Transform suggester service (1 hour)
**Step 4**: API connector sample fetching (1-2 hours)
**Step 5**: Frontend types & hooks (1-2 hours)
**Step 6**: ColumnMappingEditor component (4-5 hours)
**Step 7**: TaskWizard step 4.5 (2-3 hours)
**Step 8**: TaskDetail mapping tab (2-3 hours)
**Step 9**: Testing (3-4 hours)
**Total**: ~18-25 hours development time

### Known Limitations & Future Enhancements

**Phase 1 (Current)**:
- ✅ Nested JSON flattening
- ✅ Type-aware mapping with auto-suggestions
- ✅ Mapping templates (localStorage only)
- ✅ Batch operations
- ✅ Hierarchical field display

**Phase 2 (Future)**:
- ⏳ Array element mapping (index access: `tags.0`, `tags.1`)
- ⏳ Array explosion (one row per element)
- ⏳ Shared mapping templates (database storage)
- ⏳ Mapping import/export (JSON file)
- ⏳ Advanced validation (field existence checks)
- ⏳ Drag-and-drop field mapping UI

**Not Planned**:
- Complex JSONPATH transformations (out of scope)
- Real-time field preview updates (performance concern)

---

## 🎯 Phase 7: API Authentication & Task Scheduler UI (Complete)

### Overview

Phase 7 adds two critical production features:
1. **Flexible API Authentication**: Support for Bearer tokens, API keys, Basic Auth, and OAuth for external API data fetching
2. **Task Scheduler UI**: Complete frontend interface for creating and managing cron-based task schedules with enhanced retry logic

### Phase 7 Architecture

#### Authentication System

**Database Schema Changes**:
```sql
ALTER TABLE task ADD auth_type VARCHAR2(20) NULL;  -- 'none', 'bearer', 'api_key', 'basic', 'oauth'
ALTER TABLE task ADD api_key VARCHAR2(500) NULL;   -- Encrypted
ALTER TABLE task ADD username VARCHAR2(200) NULL;  -- For Basic auth
ALTER TABLE task ADD password VARCHAR2(200) NULL;  -- Encrypted
ALTER TABLE task ADD oauth_config CLOB NULL;       -- JSON for OAuth
```

**New Backend Components**:
- `backend/app/core/encryption.py` - Fernet encryption service for credentials
- `backend/app/services/api_connector.py` - Enhanced with `apply_authentication()` function
- Authentication types supported:
  - **None**: No authentication (default)
  - **Bearer**: Adds `Authorization: Bearer {token}` header
  - **API Key**: Adds custom header (e.g., `X-API-Key: {key}`)
  - **Basic Auth**: Adds `Authorization: Basic {base64(username:password)}`
  - **OAuth**: Token refresh flow (Phase 7.5)

**Frontend Components**:
- TaskWizard: New "Authentication" step with auth type dropdown
- Conditional input fields based on auth type selection
- Password masking for sensitive credentials

#### Scheduler UI System

**New Backend API Routes** (`backend/app/api/v1/routes/schedules.py`):
- `POST /api/v1/tasks/{task_id}/schedule` - Create schedule
- `GET /api/v1/tasks/{task_id}/schedule` - Get task schedule
- `PUT /api/v1/schedules/{schedule_id}` - Update schedule
- `DELETE /api/v1/schedules/{schedule_id}` - Delete schedule
- `GET /api/v1/schedules/` - List all schedules
- `POST /api/v1/schedules/{schedule_id}/resume` - Resume paused schedule

**Frontend Components**:
- `ScheduleEditor.tsx` - Cron expression editor with presets and validation
- `Schedules.tsx` - List page showing all schedules across tasks
- TaskDetail integration - Schedule tab for per-task configuration
- TaskList indicators - Clock icon badges for scheduled tasks

**Cron Presets**:
- Hourly: `0 * * * *`
- Daily at 2 AM: `0 2 * * *`
- Weekly (Sunday 2 AM): `0 2 * * 0`
- Monthly (1st at 2 AM): `0 2 1 * *`

#### Enhanced Retry Logic

**Discriminated Retry** (Celery task):
```python
@celery_app.task(
    autoretry_for=(
        httpx.NetworkError,
        httpx.TimeoutException,
        httpx.ConnectError,
    ),  # Only retry network issues, not validation errors
)
```

**Retry on Status Code**:
- ✅ Retry: 5xx server errors (503, 500, 502)
- ❌ No Retry: 4xx client errors (400, 401, 404) - these indicate config issues
- ❌ No Retry: Validation errors - data quality issues, not transient

**Schedule-Level Retry Configuration** (TaskSchedule model):
```python
max_retries = Column(Integer, default=3)
consecutive_failures = Column(Integer, default=0)
status = Column(String(30), default='active')  # 'active', 'paused_by_failures', 'disabled'
```

**Auto-Pause Logic**:
- Track consecutive failures per schedule
- After N failures (configurable), set status to `paused_by_failures`
- Requires manual resume via `/schedules/{id}/resume` endpoint
- Prevents endless retries of broken configurations

### Key Features

#### 1. Credential Security
- **Encryption at Rest**: All API keys and passwords encrypted using Fernet symmetric encryption
- **Key Management**: Encryption key stored in environment variable `ENCRYPTION_KEY`
- **API Response Filtering**: TaskOut schema excludes sensitive fields (`api_key`, `password`)
- **Key Rotation**: Encryption service supports key rotation for compliance

#### 2. Authentication Flow
```
User creates task with auth → Credentials encrypted → Stored in Task table
                                                           ↓
                                    Task execution triggered
                                                           ↓
                            api_connector.py retrieves Task
                                                           ↓
                            apply_authentication() decrypts & formats
                                                           ↓
                            httpx.request() includes auth headers
                                                           ↓
                            External API authenticates request
```

#### 3. Schedule Management Flow
```
User creates schedule in UI → POST /tasks/{id}/schedule → Validate cron expression
                                                               ↓
                                              Store in task_schedule table
                                                               ↓
                                        Call get_scheduler().add_schedule()
                                                               ↓
                                        APScheduler adds cron job
                                                               ↓
                            Job triggers → Enqueue Celery task → Track success/failure
                                                               ↓
                                        Update consecutive_failures counter
                                                               ↓
                            If threshold exceeded → Pause schedule + alert
```

### Implementation Status

**Track A: Authentication** (100% complete):
- [x] Database migration (auth fields)
- [x] Encryption service
- [x] API connector auth logic
- [x] Pydantic schema updates
- [x] Frontend auth UI
- [x] Unit tests

**Track B: Scheduler UI** (100% complete):
- [x] Schedule API routes (5 endpoints)
- [x] Pydantic schemas with cron validation
- [x] Frontend types & API client
- [x] React Query hooks
- [x] ScheduleEditor component
- [x] TaskDetail integration
- [x] Schedules list page
- [x] TaskList indicators
- [x] Tests

**Track C: Enhanced Retry** (100% complete):
- [x] Discriminate retryable errors
- [x] Schedule retry configuration
- [x] Failure tracking & auto-pause
- [x] Resume paused schedules

### Testing Strategy

**Backend Tests** (25+ cases planned):
- `test_authentication.py`: Bearer token formatting, API key injection, Basic auth encoding, encryption round-trip
- `test_schedule_routes.py`: CRUD operations, cron validation, scheduler reload
- `test_enhanced_retry.py`: Network error retry, 5xx retry, 4xx no-retry, consecutive failure tracking

**Frontend Tests** (15+ cases planned):
- `ScheduleEditor.test.tsx`: Cron validation, preset selection, next run calculation
- `Schedules.test.tsx`: List rendering, filter, edit/delete actions
- `AuthenticationStep.test.tsx`: Auth type dropdown, conditional fields, password masking

### Security Considerations

1. **Encryption Key Storage**: Use environment variable, not code (12factor.net principle)
2. **HTTPS Requirement**: Document that production must use HTTPS to prevent MITM attacks
3. **OAuth Refresh Tokens**: Store encrypted, implement rotation (Phase 7.5)
4. **Audit Trail**: Log schedule creates/updates/deletes (add user context when auth implemented)
5. **Rate Limiting**: Consider adding to prevent credential stuffing attacks (Phase 8)

### Known Limitations & Future Enhancements

**Phase 7** (Current scope):
- ✅ Bearer, API Key, Basic Auth support
- ✅ OAuth framework (token refresh in Phase 7.5)
- ✅ Cron-based scheduling with validation
- ✅ Auto-pause on consecutive failures
- ✅ Manual resume paused schedules

**Phase 7.5** (Future):
- ⏳ OAuth provider integration (Google, GitHub, Azure AD)
- ⏳ Schedule conflict detection (prevent overlapping runs)
- ⏳ Visual cron builder (drag-and-drop time picker)
- ⏳ Email/Slack notifications for schedule failures
- ⏳ "Test Connection" button in TaskWizard

**Phase 8** (Not planned):
- Certificate-based authentication (mTLS)
- Multi-factor authentication for UI
- Schedule templates (export/import)
- Advanced retry strategies (jitter, circuit breaker)

---

## 🎯 Phase 8: Configuration UI, Real-time Updates & UX Enhancements (Planned)

### Overview

Phase 8 focuses on production-readiness and user experience improvements:
1. **Database Connection Configuration UI** - Move DB settings from .env to secure admin page
2. **WebSocket Real-time Updates** - Live run status and log streaming
3. **Visual Cron Builder** - User-friendly schedule creation
4. **Mobile-Responsive UI** - Touch-friendly interface for all screen sizes
5. **Upsert Logic** - Insert or update records based on unique keys

### Phase 8 Architecture

---

### Feature 1: Database Connection Configuration UI

#### Security Architecture

**Threat Model**:
- Credentials must never be exposed in API responses
- Credentials must be encrypted at rest
- Only authorized admins can modify connections
- Connection strings must be validated before saving
- Audit trail for all configuration changes

**Storage Strategy (Encrypted File)**:
```
┌─────────────────────────────────────────────────────────────────┐
│  Encrypted File Storage (Recommended)                            │
├─────────────────────────────────────────────────────────────────┤
│  Default Location: connections.enc                              │
│  Override: CONNECTIONS_FILE_PATH                                │
│  Recommended Production Value: /etc/intakegateway/connections.enc │
│  Encryption: Fernet symmetric encryption                        │
│  Master Key: ENCRYPTION_KEY environment variable                │
└─────────────────────────────────────────────────────────────────┘

File Structure (JSON, encrypted at rest):
{
  "connections": [
    {
      "id": "uuid-1",
      "name": "Production Oracle",
      "host": "db.example.com",
      "port": 1521,
      "service": "ORCL",
      "username": "intakegateway_user",
      "password": "encrypted_password_here",
      "is_default": true,
      "created_at": "2026-02-03T10:00:00Z",
      "updated_at": "2026-02-03T10:00:00Z"
    }
  ],
  "metadata": {
    "version": 1,
    "last_modified_by": "admin"
  }
}

Benefits:
- Simpler for single-instance deployments
- No database dependency for connection config
- Easy backup/restore (copy encrypted file)
- Works during initial setup (before DB is configured)

Security Measures:
- File permissions: 600 (owner read/write only)
- Directory permissions: 700
- Encryption key never stored in file
- File integrity check via HMAC
```

**Backend Components**:

```
backend/app/
├── api/v1/routes/
│   └── connections.py          # Connection CRUD endpoints
├── services/
│   ├── connection_manager.py   # Connection pool management
│   └── connection_file.py      # Encrypted file read/write operations
├── db/
│   └── schemas/
│       └── connection.py       # Pydantic schemas (no password in response)
└── core/
    └── encryption.py           # Enhanced Fernet encryption (existing)
```

**Connection File Service**:
```python
# backend/app/services/connection_file.py
import os
import json
from pathlib import Path
from app.core.encryption import encrypt_data, decrypt_data

DEFAULT_CONFIG_PATH = os.getenv("DB_CONFIG_PATH", "/etc/intakegateway/connections.enc")

class ConnectionFileService:
    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH):
        self.config_path = Path(config_path)

    def read_connections(self) -> dict:
        """Read and decrypt connections file."""
        if not self.config_path.exists():
            return {"connections": [], "metadata": {"version": 1}}

        encrypted_data = self.config_path.read_bytes()
        decrypted_json = decrypt_data(encrypted_data)
        return json.loads(decrypted_json)

    def write_connections(self, data: dict, modified_by: str = "system"):
        """Encrypt and write connections file."""
        data["metadata"]["last_modified_by"] = modified_by
        json_data = json.dumps(data, indent=2)
        encrypted_data = encrypt_data(json_data.encode())

        # Ensure directory exists with secure permissions
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(self.config_path.parent, 0o700)

        # Write file with secure permissions
        self.config_path.write_bytes(encrypted_data)
        os.chmod(self.config_path, 0o600)
```

**API Endpoints**:
```
GET    /api/v1/connections              # List connections (passwords masked)
POST   /api/v1/connections              # Create connection
PUT    /api/v1/connections/{id}         # Update connection
DELETE /api/v1/connections/{id}         # Delete connection
POST   /api/v1/connections/{id}/test    # Test connection (returns success/error)
POST   /api/v1/connections/{id}/activate # Set as active connection
```

**Security Best Practices**:
1. **Never return passwords** - API responses show `password: "********"`
2. **Encrypt at rest** - Use Fernet symmetric encryption (same as Phase 7)
3. **Validate before save** - Test connection before persisting
4. **Rate limit test endpoint** - Prevent brute force attacks
5. **Audit logging** - Log all connection changes with timestamp/user
6. **Require re-authentication** - Prompt for current password before changes
7. **Environment fallback** - If no DB config exists, fall back to .env (migration path)

**Frontend Components**:
```
frontend/src/
├── pages/
│   └── Settings.tsx            # Settings page with connections tab
├── components/
│   └── ConnectionEditor.tsx    # Connection form with test button
```

**Migration Strategy**:
1. App starts → Check if `db_connections` table has entries
2. If empty → Read from .env → Create default connection → Mark as active
3. Future runs → Use database configuration
4. .env becomes backup/override for emergencies

---

### Feature 2: WebSocket Real-time Updates

#### Architecture

**Technology Choice**: FastAPI WebSocket + React useWebSocket hook

**WebSocket Events**:
```typescript
// Server → Client events
interface WSEvent {
  type: 'run_status' | 'run_progress' | 'run_log' | 'schedule_triggered';
  payload: RunStatusPayload | RunProgressPayload | RunLogPayload | SchedulePayload;
}

interface RunStatusPayload {
  run_id: string;
  status: 'PENDING' | 'RUNNING' | 'SUCCESS' | 'PARTIAL_SUCCESS' | 'FAILED';
  completed_at?: string;
}

interface RunProgressPayload {
  run_id: string;
  total_records: number;
  processed_records: number;
  failed_records: number;
  percentage: number;
}

interface RunLogPayload {
  run_id: string;
  timestamp: string;
  level: 'INFO' | 'WARNING' | 'ERROR';
  message: string;
}

interface SchedulePayload {
  schedule_id: string;
  task_id: string;
  task_name: string;
  triggered_at: string;
}
```

**Backend Components**:
```
backend/app/
├── api/v1/
│   └── websocket.py            # WebSocket endpoint handler
├── services/
│   └── ws_manager.py           # Connection manager (broadcast, rooms)
└── workers/
    └── tasks.py                # Modified to emit WS events
```

**WebSocket Endpoint**:
```python
# /api/v1/ws
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, handle client messages
            data = await websocket.receive_text()
            # Handle subscription to specific runs
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

**Frontend Integration**:
```typescript
// hooks/useWebSocket.ts
const useRunUpdates = (runId: string) => {
  const { lastMessage } = useWebSocket(`ws://localhost:8000/api/v1/ws`);

  useEffect(() => {
    if (lastMessage?.type === 'run_progress' && lastMessage.payload.run_id === runId) {
      // Update React Query cache
      queryClient.setQueryData(['run', runId], (old) => ({
        ...old,
        ...lastMessage.payload
      }));
    }
  }, [lastMessage]);
};
```

**Use Cases**:
1. **RunDetail page** - Live progress bar, streaming logs
2. **RunsList page** - Status badges update automatically
3. **Dashboard** - Recent runs list updates in real-time
4. **Toast notifications** - "Task X completed successfully"

---

### Feature 3: Visual Cron Builder

#### UI Design

**Component Structure**:
```
┌─────────────────────────────────────────────────────────────────┐
│  Schedule Configuration                                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Quick Presets                                           │    │
│  │  [Every Hour] [Daily 2AM] [Weekly Sun] [Monthly 1st]    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Frequency     [Dropdown: Hourly/Daily/Weekly/Monthly]   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Time Picker   [ 02 ▼ ] : [ 00 ▼ ]  (24-hour format)    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Days of Week (for Weekly)                               │    │
│  │  [Mon] [Tue] [Wed] [Thu] [Fri] [Sat] [Sun]              │    │
│  │   ○     ○     ○     ○     ○     ○     ●                 │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Day of Month (for Monthly)                              │    │
│  │  [ 1 ▼ ] or [Last day of month ☐]                       │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Generated Cron: 0 2 * * 0                               │    │
│  │  Human readable: "Every Sunday at 2:00 AM"               │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Next 5 Runs:                                            │    │
│  │  • Sun, Feb 9, 2026 at 2:00 AM                          │    │
│  │  • Sun, Feb 16, 2026 at 2:00 AM                         │    │
│  │  • Sun, Feb 23, 2026 at 2:00 AM                         │    │
│  │  • Sun, Mar 2, 2026 at 2:00 AM                          │    │
│  │  • Sun, Mar 9, 2026 at 2:00 AM                          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Advanced: Edit cron directly                            │    │
│  │  [ 0 2 * * 0                                         ]   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

**Frontend Components**:
```
frontend/src/components/
├── CronBuilder/
│   ├── index.tsx               # Main container
│   ├── FrequencySelector.tsx   # Hourly/Daily/Weekly/Monthly
│   ├── TimePicker.tsx          # Hour:Minute selector
│   ├── DayOfWeekPicker.tsx     # Toggle buttons for weekdays
│   ├── DayOfMonthPicker.tsx    # Dropdown 1-31 + last day
│   ├── CronPreview.tsx         # Shows cron + human readable
│   ├── NextRunsList.tsx        # Upcoming execution dates
│   └── utils.ts                # Cron generation/parsing logic
```

**Cron Generation Logic**:
```typescript
interface CronConfig {
  frequency: 'hourly' | 'daily' | 'weekly' | 'monthly';
  hour: number;        // 0-23
  minute: number;      // 0-59
  daysOfWeek: number[]; // 0-6 (Sun-Sat)
  dayOfMonth: number | 'last';
}

function generateCron(config: CronConfig): string {
  const { frequency, hour, minute, daysOfWeek, dayOfMonth } = config;

  switch (frequency) {
    case 'hourly':
      return `${minute} * * * *`;
    case 'daily':
      return `${minute} ${hour} * * *`;
    case 'weekly':
      return `${minute} ${hour} * * ${daysOfWeek.join(',')}`;
    case 'monthly':
      const dom = dayOfMonth === 'last' ? 'L' : dayOfMonth;
      return `${minute} ${hour} ${dom} * *`;
  }
}
```

**Backend Support**:
```python
# New endpoint to calculate next runs
GET /api/v1/schedules/preview?cron=0+2+*+*+0&count=5

Response:
{
  "cron": "0 2 * * 0",
  "human_readable": "Every Sunday at 2:00 AM",
  "next_runs": [
    "2026-02-09T02:00:00Z",
    "2026-02-16T02:00:00Z",
    ...
  ]
}
```

---

### Feature 4: Mobile-Responsive UI

#### Responsive Breakpoints

```css
/* Tailwind breakpoints */
sm: 640px   /* Mobile landscape */
md: 768px   /* Tablet */
lg: 1024px  /* Desktop */
xl: 1280px  /* Large desktop */
```

#### Component Adaptations

**Sidebar Navigation**:
```
Desktop (lg+):           Mobile (< lg):
┌────┬──────────────┐    ┌──────────────────┐
│ ☰  │              │    │ ☰ IntakeGateway     [≡] │  <- Hamburger menu
│    │              │    ├──────────────────┤
│ 📊 │   Content    │    │                  │
│ 📋 │              │    │     Content      │
│ ▶️  │              │    │                  │
│ 📅 │              │    │                  │
└────┴──────────────┘    └──────────────────┘

Mobile menu (slide-in):
┌──────────────────┐
│ ✕ Close          │
├──────────────────┤
│ 📊 Dashboard     │
│ 📋 Tasks         │
│ ▶️ Runs          │
│ 📅 Schedules     │
│ ⚙️ Settings      │
└──────────────────┘
```

**Data Tables**:
```
Desktop:                          Mobile (card layout):
┌────┬──────┬────────┬──────┐    ┌──────────────────┐
│ ID │ Name │ Status │ Act  │    │ Import Users     │
├────┼──────┼────────┼──────┤    │ Status: ● Active │
│ 1  │ Task │ Active │ [▶]  │    │ Last run: 2h ago │
└────┴──────┴────────┴──────┘    │ [▶ Run] [Edit]   │
                                  └──────────────────┘
                                  ┌──────────────────┐
                                  │ Sync Products    │
                                  │ ...              │
                                  └──────────────────┘
```

**Forms**:
- Stack form fields vertically on mobile
- Full-width inputs
- Larger touch targets (min 44px height)
- Floating action buttons for primary actions

**Implementation Checklist**:
- [ ] Collapsible sidebar with hamburger menu
- [ ] Responsive table → card layout switcher
- [ ] Touch-friendly button sizes (min 44x44px)
- [ ] Swipe gestures for card actions (optional)
- [ ] Bottom navigation bar for mobile (optional)
- [ ] Viewport meta tag already set
- [ ] Test on iOS Safari, Android Chrome

**Key Files to Modify**:
```
frontend/src/
├── components/
│   ├── layout/
│   │   ├── Sidebar.tsx         # Add mobile hamburger
│   │   └── MobileNav.tsx       # New slide-in menu
│   └── ui/
│       └── ResponsiveTable.tsx # Table/Card switcher
├── pages/
│   ├── TaskList.tsx            # Use ResponsiveTable
│   ├── RunsList.tsx            # Use ResponsiveTable
│   └── Schedules.tsx           # Use ResponsiveTable
└── index.css                   # Mobile-first utilities
```

---

### Feature 5: Upsert Logic for Database Records

#### Overview

Enable tasks to update existing records (if unique key matches) or insert new ones, with intelligent row skipping for already-processed records and graceful error handling.

#### Database Schema Changes

**Task Model Enhancement**:
```sql
ALTER TABLE tasks ADD upsert_enabled NUMBER(1) DEFAULT 0;
ALTER TABLE tasks ADD upsert_keys VARCHAR2(500);       -- JSON array of column names
ALTER TABLE tasks ADD skip_column VARCHAR2(100);       -- Column to check for skip condition
ALTER TABLE tasks ADD skip_value VARCHAR2(100);        -- Value that triggers skip (e.g., 'Y')
-- Example: skip_column = "processed", skip_value = "Y"
```

#### Row Skip Logic

**Use Case**: A third-party system processes records and marks them with `processed = 'Y'`. The import should skip these rows to avoid overwriting changes.

**Skip Conditions**:
1. **Pre-processed rows**: If `skip_column` has `skip_value`, skip the row
2. **Primary key errors**: Log error, skip row, continue processing
3. **Constraint violations**: Log error, skip row, continue processing

**Skip Flow Diagram**:
```
For each record in API response:
    │
    ├─► Check if record exists in DB (by upsert_keys)
    │       │
    │       ├─► EXISTS + skip_column = skip_value
    │       │       └─► SKIP (log: "Row skipped - already processed")
    │       │
    │       ├─► EXISTS + skip_column ≠ skip_value
    │       │       └─► UPDATE record
    │       │
    │       └─► NOT EXISTS
    │               └─► INSERT record
    │
    ├─► On PRIMARY KEY error
    │       └─► LOG error + SKIP + CONTINUE
    │
    └─► On CONSTRAINT error
            └─► LOG error + SKIP + CONTINUE
```

#### Upsert Strategies

**Strategy 1: MERGE Statement with Skip Logic (Oracle)**
```sql
MERGE INTO target_table t
USING (SELECT :col1 as col1, :col2 as col2 FROM dual) s
ON (t.employee_id = s.employee_id)
WHEN MATCHED THEN
  UPDATE SET t.col2 = s.col2, t.updated_at = SYSDATE
  WHERE t.processed IS NULL OR t.processed != 'Y'  -- Skip if already processed
WHEN NOT MATCHED THEN
  INSERT (col1, col2, created_at) VALUES (s.col1, s.col2, SYSDATE);
```

**Strategy 2: Check-Skip-then-Insert/Update** (With Error Handling)
```python
# For databases without MERGE support or complex skip logic
existing = session.query(Model).filter_by(unique_key=value).first()
if existing:
    if existing.processed == 'Y':
        return RowResult.SKIPPED  # Already processed by third party
    for key, val in data.items():
        setattr(existing, key, val)
else:
    session.add(Model(**data))
```

#### Backend Implementation

**Enhanced Runner Service**:
```python
# backend/app/services/runner.py
from dataclasses import dataclass
from enum import Enum

class RowStatus(Enum):
    INSERTED = "inserted"
    UPDATED = "updated"
    SKIPPED = "skipped"
    ERROR = "error"

@dataclass
class RowResult:
    status: RowStatus
    record_key: str
    message: str = ""

class TaskRunner:
    def process_records(self, task: Task, records: list[dict]) -> dict:
        """Process records with skip logic and error continuation."""
        results = {
            "inserted": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0,
            "error_details": []
        }

        for idx, record in enumerate(records):
            try:
                result = self._process_single_record(task, record)
                results[result.status.value] += 1 if result.status != RowStatus.ERROR else 0
                results["errors"] += 1 if result.status == RowStatus.ERROR else 0

                if result.status == RowStatus.ERROR:
                    results["error_details"].append({
                        "row_index": idx,
                        "record_key": result.record_key,
                        "error": result.message
                    })

            except Exception as e:
                # Catch-all: log and continue to next record
                logger.error(f"Unexpected error processing row {idx}: {e}")
                results["errors"] += 1
                results["error_details"].append({
                    "row_index": idx,
                    "error": str(e)
                })
                continue  # NEVER stop the process

        return results

    def _process_single_record(self, task: Task, record: dict) -> RowResult:
        """Process a single record with skip and error handling."""
        upsert_keys = json.loads(task.upsert_keys) if task.upsert_keys else []
        record_key = self._get_record_key(record, upsert_keys)

        try:
            # Check if record exists
            if upsert_keys:
                existing = self._find_existing_record(task, record, upsert_keys)

                if existing:
                    # Check skip condition
                    if self._should_skip(task, existing):
                        logger.info(f"Skipping row {record_key}: already processed")
                        return RowResult(
                            status=RowStatus.SKIPPED,
                            record_key=record_key,
                            message=f"Skip condition met: {task.skip_column}={task.skip_value}"
                        )

                    # Update existing record
                    self._update_record(task, existing, record)
                    return RowResult(status=RowStatus.UPDATED, record_key=record_key)

            # Insert new record
            self._insert_record(task, record)
            return RowResult(status=RowStatus.INSERTED, record_key=record_key)

        except IntegrityError as e:
            # Primary key or unique constraint violation
            logger.warning(f"Constraint error for row {record_key}: {e}")
            self.session.rollback()
            return RowResult(
                status=RowStatus.ERROR,
                record_key=record_key,
                message=f"Constraint violation: {str(e)[:200]}"
            )

        except DatabaseError as e:
            # Other database errors
            logger.error(f"Database error for row {record_key}: {e}")
            self.session.rollback()
            return RowResult(
                status=RowStatus.ERROR,
                record_key=record_key,
                message=f"Database error: {str(e)[:200]}"
            )

    def _should_skip(self, task: Task, existing_record) -> bool:
        """Check if record should be skipped based on skip_column/skip_value."""
        if not task.skip_column or not task.skip_value:
            return False

        current_value = getattr(existing_record, task.skip_column, None)
        return str(current_value).upper() == str(task.skip_value).upper()

    def _get_record_key(self, record: dict, upsert_keys: list) -> str:
        """Generate a readable key for logging."""
        if upsert_keys:
            return ", ".join(f"{k}={record.get(k)}" for k in upsert_keys)
        return f"row_{id(record)}"

    def _build_merge_sql(self, task: Task, columns: list, upsert_keys: list) -> str:
        """Generate Oracle MERGE statement with skip condition."""
        update_cols = [c for c in columns if c not in upsert_keys]

        # Build WHERE clause for skip condition
        skip_where = ""
        if task.skip_column and task.skip_value:
            skip_where = f"WHERE (t.{task.skip_column} IS NULL OR t.{task.skip_column} != '{task.skip_value}')"

        return f"""
        MERGE INTO {task.table_name} t
        USING (SELECT {', '.join(f':{c} as {c}' for c in columns)} FROM dual) s
        ON ({' AND '.join(f't.{k} = s.{k}' for k in upsert_keys)})
        WHEN MATCHED THEN
          UPDATE SET {', '.join(f't.{c} = s.{c}' for c in update_cols)}
          {skip_where}
        WHEN NOT MATCHED THEN
          INSERT ({', '.join(columns)}) VALUES ({', '.join(f's.{c}' for c in columns)})
        """
```

#### Error Handling Philosophy

**Key Principle**: The process should NEVER stop due to individual row errors.

| Error Type | Action | Logged |
|------------|--------|--------|
| Skip condition met | Skip row, continue | INFO |
| Primary key violation | Skip row, continue | WARNING |
| Unique constraint violation | Skip row, continue | WARNING |
| Data type mismatch | Skip row, continue | WARNING |
| Foreign key violation | Skip row, continue | WARNING |
| Connection lost | Retry 3x, then fail run | ERROR |
| Table not found | Fail run immediately | ERROR |

**Error Log Entry Example**:
```json
{
  "run_id": "abc-123",
  "row_index": 42,
  "record_key": "employee_id=12345",
  "error_type": "CONSTRAINT_VIOLATION",
  "error_message": "ORA-00001: unique constraint (EMPLOYEES_EMAIL_UK) violated",
  "timestamp": "2026-02-03T14:30:00Z",
  "action_taken": "SKIPPED"
}
```

#### Frontend Integration

**TaskWizard Step Enhancement**:
```
┌─────────────────────────────────────────────────────────────────┐
│  Step 5: Database Options                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Insert Mode:                                                     │
│  ○ Insert only (fail on duplicates)                              │
│  ● Upsert (update if exists, insert if new)                      │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Unique Key Columns (for upsert matching):               │    │
│  │                                                          │    │
│  │  Available Columns:        Selected Keys:                │    │
│  │  ┌──────────────┐         ┌──────────────┐              │    │
│  │  │ name         │   [>]   │ employee_id  │              │    │
│  │  │ department   │   [<]   │              │              │    │
│  │  │ salary       │         │              │              │    │
│  │  │ hire_date    │         │              │              │    │
│  │  └──────────────┘         └──────────────┘              │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Skip Already Processed Records (Optional):              │    │
│  │                                                          │    │
│  │  Skip Column:  [ processed      ▼ ]                     │    │
│  │  Skip Value:   [ Y              ]                       │    │
│  │                                                          │    │
│  │  ℹ️  Rows where this column equals this value will be   │    │
│  │     skipped during import (useful when third-party      │    │
│  │     systems mark records as processed)                  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ☑️  Continue on row errors (log and skip failed rows)          │
│                                                                   │
│  ⚠️  Upsert keys should match unique/primary key constraints     │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

**TaskDetail Enhancement**:
- Show upsert configuration in task summary
- Display "Upsert Mode: ON (key: employee_id)" badge
- Display "Skip: processed=Y" badge when configured
- Track statistics: X inserted, Y updated, Z skipped, N errors

#### Run Statistics Enhancement

```python
# TaskRun model additions
class TaskRun:
    # Existing fields...
    inserted_records = Column(Integer, default=0)
    updated_records = Column(Integer, default=0)
    skipped_records = Column(Integer, default=0)  # Rows skipped due to skip condition
    error_records = Column(Integer, default=0)    # Rows skipped due to errors
    # successful_records = inserted + updated
    # total_processed = inserted + updated + skipped + errors
```

**API Response**:
```json
{
  "run_id": "abc-123",
  "status": "SUCCESS",
  "total_records": 100,
  "inserted_records": 75,
  "updated_records": 10,
  "skipped_records": 12,
  "error_records": 3,
  "failed_records": 0
}
```

---

### Implementation Timeline

| Feature | Estimated Effort | Priority |
|---------|-----------------|----------|
| 1. DB Connection Config UI | 8-12 hours | High |
| 2. WebSocket Real-time | 10-15 hours | Medium |
| 3. Visual Cron Builder | 6-10 hours | Medium |
| 4. Mobile-Responsive UI | 8-12 hours | Medium |
| 5. Upsert Logic | 6-8 hours | High |
| **Total** | **38-57 hours** | |

### Implementation Order (Recommended)

1. **Upsert Logic** - Core functionality, no UI dependencies
2. **DB Connection Config** - Security-critical, enables multi-environment
3. **Mobile-Responsive UI** - Improves usability across devices
4. **Visual Cron Builder** - UX improvement, builds on existing scheduler
5. **WebSocket Real-time** - Polish feature, can be added last

### Testing Strategy

**Backend Tests** (40+ cases):
- `test_connections.py`: CRUD, encryption, test connection, activation, file permissions
- `test_websocket.py`: Connection lifecycle, event broadcasting, room subscriptions
- `test_upsert.py`: MERGE generation, key matching, statistics tracking
- `test_skip_logic.py`: Skip condition evaluation, error continuation, statistics
  - Test skip when processed='Y'
  - Test continue on primary key error
  - Test continue on constraint violation
  - Test error logging with continuation
  - Test mixed results (insert + update + skip + error)

**Frontend Tests** (30+ cases):
- `ConnectionEditor.test.tsx`: Form validation, password masking, test button
- `CronBuilder.test.tsx`: Preset selection, cron generation, next runs display
- `ResponsiveTable.test.tsx`: Breakpoint switching, card rendering
- `WebSocket.test.tsx`: Connection, reconnection, event handling
- `UpsertConfig.test.tsx`: Skip column selection, skip value input, validation

**E2E Tests** (15+ cases):
- Full connection configuration flow
- Real-time run monitoring
- Schedule creation with visual builder
- Mobile navigation and interactions
- Upsert with skip condition (verify skipped rows logged)
- Run with row errors (verify process continues)

---

### Security Checklist (Phase 8)

- [ ] Connection passwords encrypted with Fernet
- [ ] Passwords never returned in API responses
- [ ] Rate limiting on connection test endpoint
- [ ] Audit logging for configuration changes
- [ ] WebSocket authentication (session-based)
- [ ] CORS configuration for WebSocket
- [ ] Input validation on cron expressions
- [ ] SQL injection prevention in MERGE statements (parameterized queries)

---

## 🎯 Current Project Status

### Phase 4: Backend ✅ COMPLETE
- FastAPI REST API fully implemented
- 8 service modules for business logic
- Database models and schemas
- Celery task queue setup
- APScheduler integration for cron scheduling
- 13 test files (7 unit + 6 integration)
- Ready for production

### Phase 5: Frontend ✅ COMPLETE
- React + TypeScript application
- 7 pages with full CRUD
- 11 routes configured
- UI components built with Radix UI
- 12 test files
- Production-ready codebase

### Phase 6: Column Mapping Enhancement ✅ COMPLETE
- Nested JSON flattening display (tree view UI)
- API response sample fetching (manual paste + auto-fetch)
- Oracle metadata querying for column types
- Transform suggestions based on type mismatches
- Mapping templates (localStorage)
- Batch column operations (apply transform to all)
- REST API endpoints for mapping CRUD
- Enhanced TaskWizard with dedicated mapping step
- Advanced mapping management in TaskDetail page
- Scheduling feature integrated

### Phase 7: Authentication & Scheduler UI ✅ COMPLETE
- Bearer, API Key, Basic Auth support
- Credential encryption with Fernet
- Cron-based scheduling with APScheduler
- Schedule management UI (Schedules page)
- ScheduleEditor component
- Auto-pause on consecutive failures
- Manual resume for paused schedules
- Run labeling with task name and retry badges
- Frontend-backend field alignment
- Oracle 11g compatibility
- Timezone handling

### Phase 8: Configuration UI, Real-time & UX ⏳ PLANNED
- DB Connection Configuration UI (move from .env to admin page)
- WebSocket real-time updates for run progress
- Visual Cron Builder for schedule creation
- Mobile-responsive UI (touch-friendly, card layouts)
- Upsert logic for insert/update records

### Future Enhancements (Phase 9+)
- E2E testing with Cypress/Playwright
- OAuth provider integration (Google, GitHub, Azure AD)
- Advanced search & filtering
- Certificate-based authentication (mTLS)

---

## 📝 Last Updated

- **Date**: February 3, 2026
- **Version**: 1.0.0 (Production Release)
- **Status**: Phase 4-7 Complete | Phase 8 Planned
- **Next Phase**: Phase 8 - DB Config UI, WebSocket, Cron Builder, Mobile UI, Upsert

---

**This document is the single source of truth for project context and development practices. Keep it updated as the project evolves.**
