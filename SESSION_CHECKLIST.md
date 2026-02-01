# Next Session Checklist & Quick Reference

**Target**: Complete remaining 4 frontend tasks (40% of work)  
**Estimated Time**: 6-8 hours  
**Focus**: TaskWizard + TaskDetail integration + Final tests

---

## ⚡ Quick Start (Do This First)

```bash
# 1. Install fresh dependencies
cd frontend
npm install

# 2. Run tests to verify setup
npm test
# Expected: 31 tests passing ✅

# 3. Check build
npm run build
# Expected: Build succeeds ✅

# 4. Start dev server
npm run dev
# Frontend: http://localhost:5173 ✅

# 5. Start backend (separate terminal)
cd backend
python -m uvicorn app.main:app --reload
# Backend: http://localhost:8000/docs ✅
```

---

## 📋 Session Tasks (Priority Order)

### 1️⃣ Task 7: Authentication Step (2-3 hours) 🔴 HIGH PRIORITY

**File**: `frontend/src/pages/TaskWizard.tsx`

**What to do**:
1. Find step 3 (Headers) in the wizard
2. Add new step 4 for Authentication
3. Shift Mapping to step 5, Review to 6, Confirmation to 7
4. Create auth type selector with 5 options
5. Add conditional fields for each auth type
6. Update wizard state management
7. Test all auth types work
8. Create 10+ test cases

**Code Structure**:
```tsx
// New auth step
const [authStep, setAuthStep] = useState({
  authType: 'none',
  bearerToken: '',
  apiKeyHeaderName: '',
  apiKeyValue: '',
  username: '',
  password: '',
  oauthConfig: null
})

// In render:
{step === 4 && (
  <AuthenticationStep 
    data={authStep}
    onChange={setAuthStep}
    onNext={() => setStep(5)}
    onBack={() => setStep(3)}
  />
)}
```

**UI Elements**:
- Auth type select: none | bearer | api_key | basic | oauth
- Conditional inputs based on type
- Labels and descriptions
- Previous/Next buttons
- Validation

**Test Coverage**:
- All 5 auth types render
- Conditional fields show/hide
- Form validation works
- State persists
- Navigation works

---

### 2️⃣ Task 9: Schedule Tab in TaskDetail (1-2 hours) 🔴 HIGH PRIORITY

**File**: `frontend/src/pages/TaskDetail.tsx`

**What to do**:
1. Find tabs component in TaskDetail
2. Add new "Schedule" tab
3. Embed ScheduleEditor component
4. Load schedule with `useSchedule(taskId)`
5. Handle create/update/delete
6. Show loading/error/empty states
7. Add create button if no schedule
8. Test all operations

**Code Structure**:
```tsx
import { ScheduleEditor } from '@/components/ScheduleEditor'
import { useSchedule, useCreateSchedule, useUpdateSchedule, useDeleteSchedule } from '@/hooks/api'

// In TaskDetail component:
const { data: schedule, isLoading } = useSchedule(task.id)
const createSchedule = useCreateSchedule()
const updateSchedule = useUpdateSchedule()
const deleteSchedule = useDeleteSchedule()

// In tabs:
{activeTab === 'schedule' && (
  <ScheduleEditor
    taskId={task.id}
    schedule={schedule}
    isEditing={!!schedule}
    onSave={schedule ? updateSchedule.mutate : createSchedule.mutate}
    onDelete={deleteSchedule.mutate}
    isLoading={isLoading}
  />
)}
```

**UI Elements**:
- New "Schedule" tab
- Loading skeleton
- ScheduleEditor component
- "No schedule configured" message
- Create/Update buttons
- Success toast message

**Test Coverage**:
- Tab renders
- Schedule loads
- Create schedule works
- Update schedule works
- Delete schedule works

---

### 3️⃣ Task 6: Schedule Indicators on TaskList (1-2 hours) 🟡 MEDIUM PRIORITY

**File**: `frontend/src/pages/TaskList.tsx`

**What to do**:
1. Find where tasks are rendered in table
2. Add optional clock icon column
3. Show icon for scheduled tasks
4. Color: Green if active, gray if inactive
5. Add tooltip with cron expression
6. Make it clickable to navigate to Schedules page
7. Test rendering and interactions

**Code Structure**:
```tsx
import { Clock } from 'lucide-react'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'

// In table body:
{task.schedule && (
  <TableCell>
    <Link to={`/schedules?task=${task.id}`}>
      <Tooltip>
        <TooltipTrigger>
          <Clock 
            className={`h-4 w-4 cursor-pointer ${
              task.schedule.is_active 
                ? 'text-green-600' 
                : 'text-gray-400'
            }`}
          />
        </TooltipTrigger>
        <TooltipContent>
          {task.schedule.cron_expression}
        </TooltipContent>
      </Tooltip>
    </Link>
  </TableCell>
)}
```

**UI Elements**:
- Clock icon (from lucide-react)
- Tooltip on hover
- Color-coded status
- Link to schedule page

**Test Coverage**:
- Icon renders for scheduled tasks
- Tooltip shows cron
- Colors correct

---

### 4️⃣ Task 10: Polish TaskWizard Mapping (1-2 hours) 🟡 MEDIUM PRIORITY

**File**: `frontend/src/pages/TaskWizard.tsx`

**What to do**:
1. Review current mapping step (now step 5)
2. Verify state persists through auth step
3. Test validation flows
4. Ensure no errors between steps
5. Polish UI if needed
6. Manual end-to-end testing
7. Create final summary

**Checklist**:
- [ ] State persists: Headers → Auth → Mapping
- [ ] Validation passes correctly
- [ ] No console errors
- [ ] All required fields enforced
- [ ] Preview shows correctly
- [ ] Submit works end-to-end

---

### 5️⃣ BONUS: Authentication Tests (1-2 hours) 🟢 OPTIONAL

**File**: `frontend/src/__tests__/components/AuthenticationStep.test.tsx`

**Test Cases**:
1. All auth types render
2. Conditional fields show correctly
3. Bearer token input works
4. API key fields work
5. Basic auth fields work
6. OAuth config works
7. None auth hides all fields
8. Form validation works
9. Save/Cancel buttons work
10. State persists

---

## ✅ Pre-Work Verification

Before starting each task:

- [ ] Latest code pulled
- [ ] Dependencies installed: `npm install`
- [ ] Tests passing: `npm test`
- [ ] No ESLint errors: `npm run lint`
- [ ] Build succeeds: `npm run build`
- [ ] TypeScript clean: No errors in IDE
- [ ] Backend running on :8000
- [ ] Frontend ready on :5173

---

## 🧪 Testing Strategy

### For Each Task:
1. Write tests FIRST (TDD)
2. Create mock data/components
3. Implement feature
4. Run tests: `npm test`
5. Manual testing in browser
6. Check ESLint: `npm run lint`
7. Verify build: `npm run build`

### Test Commands:
```bash
# Run all tests
npm test

# Run specific test file
npm test -- AuthenticationStep.test.tsx

# Run with coverage
npm test -- --coverage

# Watch mode
npm test -- --watch
```

---

## 📁 Files Involved

### Will Need to Modify:
- ✏️ `frontend/src/pages/TaskWizard.tsx` (Task 7, 10)
- ✏️ `frontend/src/pages/TaskDetail.tsx` (Task 9)
- ✏️ `frontend/src/pages/TaskList.tsx` (Task 6)

### Will Create:
- 📝 `frontend/src/components/AuthenticationStep.tsx` (optional)
- 📝 `frontend/src/__tests__/components/AuthenticationStep.test.tsx` (optional)

### Already Exist (Use These):
- ✅ `frontend/src/components/ScheduleEditor.tsx`
- ✅ `frontend/src/pages/Schedules.tsx`
- ✅ `frontend/src/hooks/api.ts`
- ✅ `frontend/src/types/index.ts`
- ✅ `frontend/src/api/client.ts`

---

## 🎯 Definition of Done

For each task, mark complete when:

- [ ] Code written and tested
- [ ] All new tests pass: ✅ green
- [ ] All existing tests still pass: ✅ green
- [ ] ESLint clean: `npm run lint` → 0 errors
- [ ] TypeScript clean: No red squiggles
- [ ] Manual testing in browser works
- [ ] Component is reusable (if applicable)
- [ ] Code reviewed for quality
- [ ] Documentation updated
- [ ] No console warnings/errors

---

## 🚨 Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Tests failing after npm install | Clear cache: `npm cache clean --force` |
| Port 5173 already in use | Kill process: `lsof -i :5173` |
| TypeScript errors in IDE | Restart IDE, run `tsc --build` |
| Backend not responding | Check terminal, verify `http://localhost:8000/docs` |
| React Query cache stale | Add `queryClient.invalidateQueries()` |
| Styling not applying | Check Tailwind classes, reload browser |
| Tests timeout | Increase timeout: `vi.setConfig({testTimeout: 10000})` |

---

## 💡 Implementation Tips

### Auth Step Component
- Create separate `AuthenticationStep.tsx` for reusability
- Use conditional rendering based on auth type
- Validate required fields for each type
- Show password field as password input type (not text)
- Never console.log credentials

### Schedule Tab
- Reuse existing ScheduleEditor component
- Handle create/update/delete mutations
- Show loading spinner during operations
- Display success toast after save
- Add error boundary for safety

### Task List Icons
- Use Lucide React icons (already available)
- Keep icon styling consistent
- Use Tooltip for accessibility
- Make entire cell clickable (not just icon)

### Testing
- Mock hooks at module level
- Use userEvent not fireEvent
- Wait for async operations
- Test both happy and sad paths
- Use screen.getByText/getByRole over container queries

---

## 📊 Progress Tracking

Keep this updated as you work:

```
Task 6: Schedule Indicators
[ ] Code written
[ ] Tests created
[ ] Manual testing
[ ] Deployed

Task 7: Auth Step
[ ] Component created
[ ] Conditional fields working
[ ] Validation implemented
[ ] Tests passing
[ ] Deployed

Task 9: Schedule Tab
[ ] Tab added to TaskDetail
[ ] ScheduleEditor embedded
[ ] CRUD operations working
[ ] Tests passing
[ ] Deployed

Task 10: Polish Mapping
[ ] State persists
[ ] Validation works
[ ] Manual E2E testing
[ ] Documentation updated
```

---

## 🚀 Final Checks Before Commit

```bash
# 1. All tests pass
npm test

# 2. No linting errors
npm run lint

# 3. Build succeeds
npm run build

# 4. TypeScript clean
npx tsc --noEmit

# 5. Manual verification
# - Open http://localhost:5173
# - Test all new features
# - Check browser console for errors
# - Verify API calls in Network tab

# 6. Format code
npm run lint -- --fix
```

---

## 📝 Commit Messages

When committing, use:

```
feat(frontend): add authentication step to TaskWizard
- Implement auth type selector
- Add conditional fields for each auth type
- Create AuthenticationStep component
- Add 10+ test cases

feat(frontend): add schedule tab to TaskDetail
- Embed ScheduleEditor component
- Implement create/update/delete
- Add loading and error states

feat(frontend): add schedule indicators to TaskList
- Show clock icon for scheduled tasks
- Color-code by active status
- Add tooltip with cron expression

feat(frontend): polish TaskWizard mapping step
- Ensure state persists across steps
- Verify all validation works
- Complete end-to-end testing
```

---

## 📞 Quick Reference

| Need | Command |
|------|---------|
| Start fresh | `npm install && npm test && npm run dev` |
| Check tests | `npm test` |
| Run specific test | `npm test -- FileName.test.tsx` |
| Check linting | `npm run lint` |
| Fix linting | `npm run lint -- --fix` |
| Build for production | `npm run build` |
| Check types | `npx tsc --noEmit` |

---

## 🎯 Success Criteria

By end of next session:

- ✅ Task 7 (Auth Step): Complete with 10+ tests
- ✅ Task 9 (Schedule Tab): Complete and integrated
- ✅ Task 6 (Indicators): Complete and styled
- ✅ Task 10 (Polish): Complete and tested
- ✅ All tests passing: 40+ test cases
- ✅ No ESLint errors
- ✅ No TypeScript errors
- ✅ Full end-to-end workflow works
- ✅ Production ready

---

## 📅 Time Estimates (Revisit as Needed)

| Task | Estimate | Priority | Done By |
|------|----------|----------|---------|
| Task 7 | 2-3h | 🔴 High | Hour 3 |
| Task 9 | 1-2h | 🔴 High | Hour 5 |
| Task 6 | 1-2h | 🟡 Med | Hour 7 |
| Task 10 | 1-2h | 🟡 Med | Hour 8 |
| Tests | 1-2h | 🟢 Low | Hour 9+ |
| **Total** | **6-11h** | | |

---

## 🔗 Important Files to Reference

```
Frontend Infrastructure (Already Done):
├── frontend/src/types/index.ts ✅
├── frontend/src/api/client.ts ✅
├── frontend/src/hooks/api.ts ✅
├── frontend/src/components/ScheduleEditor.tsx ✅
└── frontend/src/pages/Schedules.tsx ✅

Today's Tasks:
├── frontend/src/pages/TaskWizard.tsx ⏳
├── frontend/src/pages/TaskDetail.tsx ⏳
├── frontend/src/pages/TaskList.tsx ⏳
└── frontend/src/__tests__/ ⏳

Supporting Docs:
├── PHASE_7_FRONTEND_PROGRESS.md
├── PHASE_7_FRONTEND_NEXT_STEPS.md
└── This file (SESSION_CHECKLIST.md)
```

---

## ✨ Final Notes

- This session is the final push for frontend Phase 7
- Remaining work is integration, not new infrastructure
- All components are already built and tested
- Focus on smooth user experience
- Test thoroughly before considering done

---

**Created**: January 30, 2026  
**For**: Next Session Execution  
**Session Target**: 100% Frontend Task Completion  
**Estimated Duration**: 6-8 hours focused work

Ready to start when next session begins! 🚀

