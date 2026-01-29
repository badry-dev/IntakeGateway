# API2DB-Importer: Project Context & Development Guidelines

**Last Updated**: January 2026  
**Project Status**: Phase 5 Complete (Frontend) | Phase 4 Complete (Backend) | Phase 6 In Progress (Column Mapping)  
**AI Assistant Guide**: Use this document to understand the project architecture, conventions, and development practices.

---

## 📋 Project Overview

**API2DB-Importer** is a full-stack web application that enables users to:
- Create data import tasks that fetch from external APIs
- Configure API endpoints with headers, authentication, and request bodies
- Map API response fields to database columns
- Trigger task executions and monitor runs
- View detailed logs, statistics, and error reports

### Technology Stack

**Backend**:
- Python 3.11 with FastAPI
- SQLAlchemy ORM with Oracle Database
- Celery for async task execution
- Pydantic for data validation
- pytest for testing (110+ tests passing)

**Frontend**:
- React 18.2 with TypeScript 5.3
- Vite 5.0 build tool
- React Router v6
- React Query 5.28 for state management
- Tailwind CSS 3.4 + Radix UI for styling
- Vitest for testing (42+ tests passing)

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
│   │           ├── runs.py     # Run endpoints (GET, POST, detail)
│   │           ├── tasks.py    # Task endpoints (CRUD)
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
│   │   └── test_validator.py
│   └── integration/
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
│   ├── pages/                  # Page components (6 pages)
│   │   ├── Dashboard.tsx       # Overview with stats
│   │   ├── TaskList.tsx        # All tasks
│   │   ├── TaskDetail.tsx      # Single task view + edit
│   │   ├── TaskWizard.tsx      # 5-step task creation
│   │   ├── RunsList.tsx        # All runs
│   │   └── RunDetail.tsx       # Single run view
│   │
│   ├── components/
│   │   ├── ui/                 # UI component library (9 components)
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── input.tsx
│   │   │   ├── label.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── table.tsx
│   │   │   ├── select.tsx
│   │   │   ├── toast.tsx
│   │   │   ├── tabs.tsx
│   │   │   └── __init__.ts
│   │   └── layout/
│   │       └── [Navigation, Sidebar components]
│   │
│   ├── hooks/                  # React Query hooks (10 hooks)
│   │   ├── api.ts              # All API hooks (useTasks, useTask, etc.)
│   │   └── useQuery utilities
│   │
│   ├── api/
│   │   ├── client.ts           # ApiClient class with all endpoints
│   │   └── types.ts            # Request/response types
│   │
│   ├── types/
│   │   ├── task.ts             # Task interfaces
│   │   ├── run.ts              # Run interfaces
│   │   └── common.ts           # Common types
│   │
│   ├── __tests__/              # Test suite
│   │   └── pages/
│   │       ├── Dashboard.test.tsx
│   │       ├── TaskList.test.tsx
│   │       ├── TaskDetail.test.tsx
│   │       ├── RunsList.test.tsx
│   │       ├── RunDetail.test.tsx
│   │       └── TaskWizard.test.tsx
│   │
│   ├── App.tsx                 # Main routing configuration
│   ├── main.tsx                # Entry point
│   └── index.css               # Global styles
│
├── public/                     # Static assets
├── vite.config.ts              # Vite configuration
├── tsconfig.json               # TypeScript configuration
├── tailwind.config.ts          # Tailwind CSS configuration
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

**Location**: `frontend/src/__tests__/pages/`

**Coverage Areas**:
- Component rendering
- Hook behavior
- User interactions
- Error handling
- Navigation

**Test Files**:
- Dashboard.test.tsx (6 tests)
- TaskList.test.tsx (7 tests)
- TaskDetail.test.tsx (7 tests)
- RunsList.test.tsx (7 tests)
- RunDetail.test.tsx (8 tests)
- TaskWizard.test.tsx (7 tests)

**Running Tests**:
```bash
cd frontend
npm run test
```

**Test Count**: 42+ tests passing

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

## 🎯 Phase 6: Column Mapping Enhancement (In Progress)

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

## 🎯 Current Project Status

### Phase 4: Backend ✅ COMPLETE
- FastAPI REST API fully implemented
- 6 service modules for business logic
- Database models and schemas
- Celery task queue setup
- 110+ unit tests passing
- Ready for production

### Phase 5: Frontend ✅ COMPLETE
- React + TypeScript application
- 6 pages with full CRUD
- 11 routes configured
- 9 UI components built
- 42+ tests passing
- Production-ready codebase

### Phase 6: Advanced Features ✅ IN PROGRESS
- **Column Mapping Enhancement** (Current Phase)
  - Nested JSON flattening display (tree view UI)
  - API response sample fetching (manual paste + auto-fetch)
  - Oracle metadata querying for column types
  - Transform suggestions based on type mismatches
  - Mapping templates (localStorage)
  - Batch column operations (apply transform to all)
  - REST API endpoints for mapping CRUD
  - Enhanced TaskWizard with dedicated mapping step (Step 4.5)
  - Advanced mapping management in TaskDetail page
  - Pydantic fallback alternatives documented (Dataclasses/Attrs/Marshmallow)
- Future: E2E testing, Authentication, Real-time updates, Advanced search

---

## 📝 Last Updated

- **Date**: January 2026
- **Version**: 1.0.0 + Phase 6 (Column Mapping)
- **Status**: Phase 5 Production Ready | Phase 6 In Progress
- **Next Phase**: Phase 6 Column Mapping Completion → Phase 6B Validation → Phase 6C Advanced Array Handling

---

**This document is the single source of truth for project context and development practices. Keep it updated as the project evolves.**
