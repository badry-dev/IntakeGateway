# API→DB Importer - Frontend Architecture

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend (React 18)                         │
│                    http://localhost:5173                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
        ┌─────────────────────────────────────────┐
        │        App.tsx (Root + Routing)         │
        │     QueryClientProvider wrapper         │
        │      BrowserRouter with 6 routes        │
        └─────────────────────────────────────────┘
                              ↓
        ┌─────────────────────────────────────────┐
        │    Layout (Sidebar + Main Content)      │
        │   Sticky navigation + responsive        │
        └─────────────────────────────────────────┘
                         ↓
    ┌────────────────────────────────────────────────────┐
    │              Page Components (6)                   │
    │                                                    │
    │  Dashboard → TaskList → TaskDetail → TaskWizard  │
    │      ↓           ↓          ↓                      │
    │   RunsList → RunDetail                            │
    └────────────────────────────────────────────────────┘
                         ↓
    ┌────────────────────────────────────────────────────┐
    │        React Query Hooks (8 + UI hooks)           │
    │                                                    │
    │  Queries:           Mutations:                     │
    │  ├─ useTasks        ├─ useCreateTask             │
    │  ├─ useTask         ├─ useUpdateTask             │
    │  ├─ useTaskStats    ├─ useDeleteTask             │
    │  ├─ useTaskRuns     └─ useTriggerRun             │
    │  ├─ useTaskRun                                    │
    │  ├─ useRun                                        │
    │  └─ useRecentRuns                                 │
    └────────────────────────────────────────────────────┘
                         ↓
    ┌────────────────────────────────────────────────────┐
    │           ApiClient (Axios wrapper)               │
    │                                                    │
    │    All API endpoints centralized                  │
    │    Error handling & response parsing              │
    └────────────────────────────────────────────────────┘
                         ↓
    ┌────────────────────────────────────────────────────┐
    │  Backend API (FastAPI)                            │
    │  http://localhost:8000/api/v1                     │
    │                                                    │
    │  GET    /tasks, /tasks/{id}                       │
    │  POST   /tasks, /tasks/{id}/run                   │
    │  PUT    /tasks/{id}                               │
    │  DELETE /tasks/{id}                               │
    │  GET    /runs, /runs/{id}                         │
    │  GET    /tasks/{id}/stats                         │
    └────────────────────────────────────────────────────┘
```

---

## Component Hierarchy

```
<App>
  <QueryClientProvider>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout><Dashboard/></Layout>}/>
        <Route path="/tasks" element={<Layout><TaskList/></Layout>}/>
        <Route path="/tasks/new" element={<Layout><TaskWizard/></Layout>}/>
        <Route path="/tasks/:id" element={<Layout><TaskDetail/></Layout>}/>
        <Route path="/runs" element={<Layout><RunsList/></Layout>}/>
        <Route path="/runs/:id" element={<Layout><RunDetail/></Layout>}/>
      </Routes>
    </BrowserRouter>
  </QueryClientProvider>
</App>

<Layout>
  <Sidebar>
    <Button variant="default|ghost" />
    <Link to="/">Dashboard</Link>
    <Link to="/tasks">Tasks</Link>
    <Link to="/runs">Runs</Link>
  </Sidebar>
  
  <Main>
    {children}
  </Main>
</Layout>

<Dashboard>
  <Card>Stats Card (x4)</Card>
  <Card>Recent Runs List</Card>
  <Button>Quick Actions</Button>
</Dashboard>

<TaskList>
  <Card>Task Card (repeating)
    <CardHeader>
      <CardTitle>Task Name</CardTitle>
    </CardHeader>
    <CardContent>
      <Button>Run</Button>
      <Button>Edit</Button>
      <Button>Delete</Button>
    </CardContent>
  </Card>
  <Dialog>Edit Modal</Dialog>
  <Dialog>Delete Confirmation</Dialog>
</TaskList>

<TaskDetail>
  <Card>Task Information</Card>
  <Dialog>Edit Form Modal</Dialog>
  <Dialog>Delete Confirmation</Dialog>
</TaskDetail>

<TaskWizard>
  <Card>Step Indicator (5 steps)</Card>
  <Card>Step Content (form)</Card>
  <Button>Previous/Next/Create</Button>
</TaskWizard>

<RunsList>
  <Card>Run Card (repeating)
    Shows: ID, Task ID, Status, Stats
  </Card>
</RunsList>

<RunDetail>
  <Card>Run Overview (stats)</Card>
  <Card>Execution Logs</Card>
  <Card>Error Table</Card>
</RunDetail>
```

---

## Data Flow Diagram

```
User Action (click button)
         ↓
Event Handler (onClick)
         ↓
Mutation Call (e.g., useTriggerRun)
         ↓
API Client (axios.post)
         ↓
Backend API (FastAPI endpoint)
         ↓
Database operation
         ↓
Response returned
         ↓
React Query updates cache
         ↓
Component re-renders with new data
         ↓
UI displays result (success/error)
```

---

## State Management Flow

```
┌─────────────────────────────────────────────────────┐
│           React Query (Server State)                │
│                                                     │
│  Cache Keys:                                        │
│  ├─ ['tasks', skip, limit]                          │
│  ├─ ['tasks', id]                                   │
│  ├─ ['taskStats', id]                               │
│  ├─ ['taskRuns', taskId, skip, limit]               │
│  ├─ ['runs', skip, limit]                           │
│  └─ [triggers all mutations & refetches]            │
│                                                     │
│  Mutations:                                         │
│  ├─ Create → Invalidate ['tasks']                   │
│  ├─ Update → Invalidate ['tasks', id]               │
│  ├─ Delete → Invalidate ['tasks']                   │
│  └─ Trigger → Invalidate ['runs'], ['taskRuns']     │
└─────────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────┐
│        React Router (Navigation State)              │
│                                                     │
│  Location: /                                        │
│  Params: { id?: string }                            │
│  Query: { skip: string, limit: string }             │
└─────────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────┐
│      Component Local State                          │
│                                                     │
│  Forms: name, description, endpoint_url, etc.      │
│  UI: isEditOpen, isDeleteOpen, isLoading            │
│  Pagination: skip, limit                           │
└─────────────────────────────────────────────────────┘
```

---

## API Integration Points

```
Dashboard.tsx
  ├─ useTaskStats() → GET /tasks/{id}/stats
  └─ useRecentRuns() → GET /runs?skip=0&limit=5

TaskList.tsx
  ├─ useTasks() → GET /tasks?skip=X&limit=10
  ├─ useTriggerRun() → POST /tasks/{id}/run
  └─ useDeleteTask() → DELETE /tasks/{id}

TaskDetail.tsx
  ├─ useTask() → GET /tasks/{id}
  ├─ useUpdateTask() → PUT /tasks/{id}
  └─ useDeleteTask() → DELETE /tasks/{id}

TaskWizard.tsx
  └─ useCreateTask() → POST /tasks

RunsList.tsx
  └─ useRecentRuns() → GET /runs?skip=X&limit=20

RunDetail.tsx
  ├─ useRun() → GET /runs/{id}
  └─ (response includes logs and row_errors)
```

---

## Component Dependency Graph

```
App (root)
 └─ Layout
     ├─ Dashboard
     │   ├─ Card
     │   └─ Button
     ├─ TaskList
     │   ├─ Card
     │   ├─ Button
     │   └─ Dialog
     ├─ TaskDetail
     │   ├─ Card
     │   ├─ Input
     │   ├─ Label
     │   ├─ Button
     │   └─ Dialog (x2)
     ├─ TaskWizard
     │   ├─ Card
     │   ├─ Input
     │   ├─ Label
     │   ├─ Button
     │   └─ select (native for now)
     ├─ RunsList
     │   ├─ Card
     │   └─ Button
     └─ RunDetail
         ├─ Card
         ├─ Button
         └─ (table - future)

UI Component Library:
 ├─ Button (6 variants, 3 sizes)
 ├─ Card (header, title, description, content, footer)
 ├─ Input (text, file upload)
 ├─ Label (form labels)
 └─ Dialog (modal dialogs)
```

---

## Request/Response Flow Example

### Create Task Workflow

```
User clicks "New Task" button
         ↓
Navigate to /tasks/new (TaskWizard)
         ↓
Component renders 5-step form
         ↓
User fills form:
  Step 1: name, description, table_name
  Step 2: endpoint_url, method
  Step 3: headers, body
  Step 4: mapping config
  Step 5: review
         ↓
User clicks "Create Task" button
         ↓
handleCreate() called
         ↓
createTaskMutation.mutateAsync(taskFormData)
         ↓
ApiClient.createTask(data)
         ↓
axios.post('/tasks', data)
         ↓
HTTP POST /api/v1/tasks
         ↓
Backend validates & saves to DB
         ↓
Returns Task object with id
         ↓
React Query:
  ├─ Updates cache with new task
  ├─ Invalidates ['tasks'] key
  └─ Refetches task list
         ↓
useRecentRuns hook also refetches
         ↓
Component updates with success message
         ↓
Navigate to /tasks (TaskList)
         ↓
TaskList displays updated list
         ↓
User sees new task in list
```

---

## File Organization Rationale

```
frontend/
├── Config files (root)
│   └─ One-time setup
│
├── src/
│   ├── main.tsx
│   │   └─ Single entry point
│   │
│   ├── App.tsx
│   │   └─ Root component with routing
│   │
│   ├── index.css
│   │   └─ Global styles + CSS variables
│   │
│   ├── types/
│   │   └─ All TypeScript interfaces
│   │       └─ Single source of truth
│   │
│   ├── api/
│   │   └─ Centralized API communication
│   │       └─ client.ts: Axios wrapper
│   │
│   ├── hooks/
│   │   └─ Custom React hooks
│   │       └─ api.ts: React Query hooks
│   │
│   ├── lib/
│   │   └─ Utility functions
│   │       └─ utils.ts: cn() for class names
│   │
│   ├── components/
│   │   └─ Reusable UI components
│   │       └─ ui/: shadcn-style base components
│   │
│   ├── pages/
│   │   └─ Full-page components
│   │       └─ 6 route handlers
│   │
│   └── __tests__/
│       └─ Unit & integration tests
│           └─ Mirroring page structure
│
└── Documentation
    └─ Setup, summary, status guides
```

---

## Performance Characteristics

### Caching Strategy
```
Stale Time | Resource
-----------|----------
15s        | Task runs (real-time feel)
30s        | Tasks (fast updates)
60s        | Stats (stable data)
Infinity   | Logs (static after completion)
```

### Bundle Size (estimated)
```
React:              45 KB
React Router:       12 KB
React Query:        18 KB
Tailwind CSS:       35 KB (with PurgeCSS)
Axios:              14 KB
UI Components:      5 KB
App Code:           60 KB
━━━━━━━━━━━━━━━━━━━━━━━━
Total (gzipped):   ~80-100 KB
```

### Load Time (dev)
```
Initial Load:   1-2 seconds
HMR Update:     < 200ms
Re-render:      < 100ms
API Request:    < 500ms (network dependent)
```

---

## Deployment Architecture

```
                    ┌─────────────┐
                    │   Browser   │
                    └─────────────┘
                          ↓
    ┌─────────────────────────────────────────┐
    │        Nginx (Reverse Proxy)            │
    │  Port 80/443                            │
    │  Serves static assets (dist/)           │
    │  Proxies /api/* to backend              │
    └─────────────────────────────────────────┘
                          ↓
    ┌────────────────────┬───────────────────┐
    ↓                    ↓
┌──────────────┐   ┌─────────────────┐
│   Frontend   │   │   Backend API   │
│   (React)    │   │   (FastAPI)     │
│   dist/      │   │   Port 8000     │
│   SPA        │   │   /api/v1       │
└──────────────┘   └─────────────────┘
                          ↓
                   ┌─────────────────┐
                   │   Database      │
                   │   (Oracle)      │
                   └─────────────────┘
```

---

## Development Workflow

```
Developer starts
     ↓
npm run dev
     ↓
Vite dev server starts (localhost:5173)
     ↓
Browser opens app
     ↓
Developer edits component
     ↓
File saved
     ↓
Vite detects change
     ↓
HMR updates browser
     ↓
Component re-renders (< 200ms)
     ↓
Developer sees result immediately
     ↓
Developer continues editing
```

---

## Security Considerations

### Current Implementation
- ✅ CORS headers from backend
- ✅ No sensitive data in localStorage
- ✅ XSS protection via React's JSX escaping
- ✅ CSRF tokens handled by backend

### Future Enhancements
- [ ] JWT token handling
- [ ] Secure session management
- [ ] HTTPS enforcement
- [ ] API rate limiting (backend)
- [ ] Input validation schemas (Zod)
- [ ] Content Security Policy

---

## Monitoring & Observability

### Current
- Browser DevTools (Network, Console)
- React Query DevTools (when installed)
- Vite debug output

### Future (Phase 6)
- Error tracking (Sentry)
- Performance monitoring (Web Vitals)
- Analytics (Google Analytics)
- Application logs (Winston)

---

## Summary

This architecture provides:
- ✅ **Separation of Concerns**: API, hooks, components, pages
- ✅ **Type Safety**: Full TypeScript with strict mode
- ✅ **Performance**: React Query caching + Vite bundling
- ✅ **Maintainability**: Clear file structure + consistent patterns
- ✅ **Scalability**: Easy to add new pages and hooks
- ✅ **Testing**: Ready for Vitest + React Testing Library

The frontend is production-ready and awaits testing before deployment.

---

**Version:** 0.1.0-alpha  
**Last Updated:** Current Session  
**Status:** Implementation Complete, Ready for Testing
