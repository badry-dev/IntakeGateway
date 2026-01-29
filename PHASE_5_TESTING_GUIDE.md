# Phase 5 Testing Guide

Complete guide for testing the Phase 5 frontend implementation.

## Prerequisites

- Node.js 18+ installed
- Backend API running on `http://localhost:8000`
- Frontend dependencies installed (`npm install`)

### Setup Verification (Updated January 2026)

Before running tests, verify your setup:

1. **Fix PostCSS Configuration** (if needed)
   ```bash
   cd frontend
   # If postcss.config.js exists, rename it
   mv postcss.config.js postcss.config.cjs
   ```

2. **Verify Dependencies**
   ```bash
   # Ensure all dependencies are installed
   npm install
   
   # Verify date-fns is installed (needed for RunDetail tests)
   npm list date-fns
   ```

3. **Check Radix UI Version**
   - Ensure `@radix-ui/react-slot` is version `^1.1.0` in package.json
   - If version is 2.x, downgrade to 1.1.0 and run `npm install`

## Unit Testing (Vitest)

### Run All Tests

```bash
cd frontend
npm run test
```

### Expected Output

```
✓ src/__tests__/pages/Dashboard.test.tsx (6 tests)
✓ src/__tests__/pages/TaskList.test.tsx (7 tests)
✓ src/__tests__/pages/TaskDetail.test.tsx (7 tests)
✓ src/__tests__/pages/RunsList.test.tsx (7 tests)
✓ src/__tests__/pages/RunDetail.test.tsx (8 tests)
✓ src/__tests__/pages/TaskWizard.test.tsx (7 tests)

Test Files  6 passed (6)
Tests      42 passed (42)
```

### Run Specific Test File

```bash
npm run test Dashboard
npm run test TaskList
npm run test TaskDetail
npm run test RunsList
npm run test RunDetail
npm run test TaskWizard
```

### Watch Mode (Auto-rerun on changes)

```bash
npm run test -- --watch
```

## Integration Testing (Frontend with Backend)

### Step 1: Start the Backend

```bash
# In backend directory
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

Verify backend is running: `http://localhost:8000/docs`

### Step 2: Start the Frontend

```bash
# In frontend directory
cd frontend
npm run dev
```

Frontend will be available at: `http://localhost:5173`

### Step 3: Manual Test Scenarios

#### Scenario 1: Dashboard Loading
1. Navigate to `http://localhost:5173`
2. **Verify**:
   - Dashboard heading displays
   - Three stat cards show counts (Tasks, Active, Failed)
   - Recent runs list shows (or "No runs yet")
   - "New Task" button visible
   - No console errors

**Expected**: Dashboard loads within 2 seconds with all data visible

---

#### Scenario 2: View Tasks
1. Click "Tasks" in navigation
2. **Verify**:
   - Task list loads
   - Each task shows: name, description, endpoint, method
   - Three buttons per task: Run, Edit, Delete
   - "New Task" button visible
   - Pagination works (if >10 tasks)

**Expected**: All tasks display with proper layout

---

#### Scenario 3: Create a Task
1. Click "New Task" button
2. **Step 1 - Basic Info**:
   - Fill "Task Name": "Test API Sync"
   - Fill "Description": "Test task for verification"
   - Fill "Table Name": "test_data"
   - Click "Next"

3. **Step 2 - Endpoint**:
   - Fill "API Endpoint": "https://jsonplaceholder.typicode.com/posts"
   - Select "Method": "GET"
   - Click "Next"

4. **Step 3 - Headers & Body**:
   - Leave empty for GET request
   - Click "Next"

5. **Step 4 - Mapping** (Optional):
   - Click "Next" to skip

6. **Step 5 - Review**:
   - Verify all information correct
   - Click "Create Task"

**Expected**:
- Task created successfully
- Redirected to task list
- New task appears in list
- Toast notification: "Task created successfully"

---

#### Scenario 4: View Task Details
1. Click "Edit" on any task in the list
2. **Verify**:
   - Task name displays
   - Task description displays
   - Task metadata: endpoint, method, table
   - "Copy ID" button works (copies to clipboard)
   - "Edit" button visible
   - "Delete" button visible

**Expected**: All task details display correctly

---

#### Scenario 5: Edit a Task
1. On task detail page, click "Edit" button
2. Modal opens with form fields
3. Change "Description" to: "Updated description"
4. Click "Save"

**Expected**:
- Modal closes
- Task detail updates
- Toast notification: "Task updated successfully"
- Description shows new value

---

#### Scenario 6: Trigger a Run
1. Go back to task list (click "Tasks")
2. Click "Run" button on a task
3. **Verify**:
   - Run is triggered
   - Toast notification appears
   - Run appears in "Runs" list shortly

**Expected**: Run created and visible in runs list

---

#### Scenario 7: View Runs List
1. Click "Runs" in navigation
2. **Verify**:
   - List of runs displays
   - Each run shows: ID, status badge, record counts
   - Status badges are color-coded
   - Timestamps are formatted (e.g., "2 hours ago")

**Expected**: All runs display with proper formatting

---

#### Scenario 8: View Run Details
1. Click on a run ID in the runs list
2. **Verify**:
   - Run status displays (running, completed, failed)
   - Statistics cards: Total, Successful, Failed
   - Timing information: Started, Completed
   - Logs section (if available)
   - Errors table (if errors exist)
   - Link to parent task

**Expected**: All run details load and display correctly

---

#### Scenario 9: Delete a Task
1. Go to task list
2. Click "Delete" on a task
3. Confirmation dialog appears
4. Click "Delete" to confirm

**Expected**:
- Task deleted
- Removed from list
- Toast notification: "Task deleted successfully"

---

#### Scenario 10: Error Handling
1. Stop the backend server
2. In frontend, refresh the page
3. Try to load tasks

**Expected**:
- Error message displays
- No unhandled errors in console
- UI remains usable

## Performance Testing

### Load Time Verification

```bash
# Open browser DevTools (F12)
# Go to Network tab
# Reload page
# Check metrics:
- Page load time: < 2 seconds
- Initial bundle: < 100KB (gzipped)
- API response time: < 500ms
```

### Memory Usage

```bash
# Open browser DevTools
# Go to Memory tab
# Take heap snapshot
# Create several tasks
# Take another heap snapshot
# Compare - should be ~20-30MB increase
```

## Type Checking

Verify TypeScript compilation without errors:

```bash
cd frontend
npx tsc --noEmit
```

**Expected**: No output = no errors

## Build Verification

Test production build:

```bash
cd frontend
npm run build
```

**Expected Output**:
```
✓ 150+ modules
✓ Built successfully
✓ dist/ folder created with optimized files
```

## Troubleshooting

### Tests Failing
1. Clear node_modules and reinstall: `rm -rf node_modules && npm install`
2. Clear test cache: `npm run test -- --clearCache`
3. Check backend is not running (port 8000 conflict)

### Frontend Won't Load
1. Check backend is running: `http://localhost:8000/docs`
2. Check CORS is configured for `http://localhost:5173`
3. Clear browser cache (Ctrl+Shift+Delete)

### API Calls Failing
1. Verify backend is running on port 8000
2. Check ApiClient endpoints in `src/api/client.ts`
3. Open browser DevTools Network tab to see actual requests
4. Check API response in Network tab for errors

### Tests Hanging
1. Increase Jest timeout: `npm run test -- --testTimeout=10000`
2. Check for missing mock setups
3. Verify all hooks are mocked

## Coverage Report

Generate coverage report:

```bash
npm run test -- --coverage
```

**Current Coverage**:
- Pages: 6/6 tested (100%)
- Test Cases: 42+ covering major flows
- UI Components: All components used in pages
- Hooks: Core hooks tested via page tests

## Checklist for Passing Phase 5

- ✅ All 6 test files pass
- ✅ 42+ test cases pass
- ✅ Frontend loads without errors
- ✅ Dashboard displays stats
- ✅ Can create, read, update, delete tasks
- ✅ Can view and trigger runs
- ✅ Can navigate all routes
- ✅ Error handling works
- ✅ No TypeScript errors
- ✅ Production build succeeds

## Demo Script (2-3 minutes)

```bash
# 1. Start backend
cd backend && python -m uvicorn app.main:app --reload &

# 2. Start frontend
cd frontend && npm run dev &

# 3. Open browser to http://localhost:5173

# 4. Demonstrate:
# - Dashboard loads with stats
# - Create a task via wizard (5 steps)
# - View tasks in list
# - Edit task details
# - Trigger a run
# - View run details
# - Delete task

# 5. Show tests
# npm run test

# 6. Ctrl+C to stop both servers
```

## Next Phase (Phase 6) Prerequisites

Before moving to Phase 6, ensure:
- ✅ All Phase 5 tests pass
- ✅ Manual testing scenarios complete
- ✅ No errors in browser console
- ✅ Backend API fully integrated
- ✅ Documentation reviewed

---

**Last Updated**: January 2024  
**Frontend Version**: 1.0.0  
**Test Suite**: 42 test cases  
**Status**: Ready for Phase 6
