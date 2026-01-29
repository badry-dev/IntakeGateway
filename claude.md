# API2DB-Importer: Project Context & Development Guidelines

**Last Updated**: January 2024  
**Project Status**: Phase 5 Complete (Frontend) | Phase 4 Complete (Backend) | Production Ready  
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

### Phase 6: Advanced Features (Future)
- E2E testing with Cypress
- Authentication & authorization
- Real-time updates (WebSocket)
- Advanced search & filtering
- Performance optimization

---

## 📝 Last Updated

- **Date**: January 2024
- **Version**: 1.0.0
- **Status**: Production Ready
- **Next Phase**: Phase 6 Planning

---

**This document is the single source of truth for project context and development practices. Keep it updated as the project evolves.**
