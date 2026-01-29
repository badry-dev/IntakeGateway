# Frontend Setup & Running Guide

## Quick Start

### 1. Install Dependencies
```bash
cd frontend
npm install
```

This installs all packages from package.json:
- React 18.2.0
- React Router 6.20.1
- React Query 5.28.0
- Tailwind CSS 3.4.1
- shadcn/ui components
- Axios for API calls
- Vite as build tool
- Vitest for testing

**Troubleshooting Installation (Updated January 2026)**:

If you encounter errors during `npm install`:

1. **PostCSS ES Module Error**
   ```bash
   # Error: "module is not defined in ES module scope"
   mv postcss.config.js postcss.config.cjs
   ```

2. **Radix UI Version Not Found**
   - Check `package.json` has `"@radix-ui/react-slot": "^1.1.0"` (not 2.x)
   - Run `npm install` again

3. **Missing date-fns**
   ```bash
   npm install date-fns
   ```

### 2. Start Development Server
```bash
npm run dev
```

Output:
```
  VITE v5.0.8  ready in 234 ms

  ➜  Local:   http://localhost:5173/
  ➜  press h to show help
```

The app opens on **http://localhost:5173**

### 3. Ensure Backend is Running
The frontend proxies API calls to http://localhost:8000

```bash
# In another terminal, from the backend directory:
python -m uvicorn app.main:app --reload --port 8000
```

---

## Available Commands

### Development
```bash
npm run dev       # Start dev server with HMR (hot reload)
```

### Building
```bash
npm run build     # Production build to dist/ folder
npm run preview   # Preview production build locally
```

### Testing
```bash
npm run test      # Run Vitest test suite
npm run test:ui   # Interactive test UI
npm run coverage  # Generate coverage report
```

### Linting
```bash
npm run lint      # Check code quality with ESLint
npm run lint:fix  # Auto-fix linting issues
```

---

## Project Structure

```
frontend/
├── src/
│   ├── main.tsx          # React entry point
│   ├── App.tsx           # Root component with routing
│   ├── index.css         # Global styles + CSS variables
│   │
│   ├── pages/            # Page components
│   │   ├── Dashboard.tsx
│   │   ├── TaskList.tsx
│   │   ├── TaskDetail.tsx
│   │   ├── RunsList.tsx
│   │   ├── RunDetail.tsx
│   │   └── TaskWizard.tsx
│   │
│   ├── components/       # Reusable components
│   │   └── ui/          # shadcn-style UI components
│   │
│   ├── hooks/           # React hooks
│   │   └── api.ts      # React Query hooks for API
│   │
│   ├── api/            # API client
│   │   └── client.ts   # Axios HTTP client
│   │
│   ├── types/          # TypeScript interfaces
│   │   └── index.ts
│   │
│   └── lib/            # Utilities
│       └── utils.ts
│
├── index.html          # HTML template
├── package.json        # Dependencies
├── tsconfig.json       # TypeScript config
├── vite.config.ts      # Vite config
├── vitest.config.ts    # Test config
└── tailwind.config.ts  # Design tokens
```

---

## Routes & Pages

| Route | Component | Purpose |
|-------|-----------|---------|
| `/` | Dashboard | Overview with stats and recent runs |
| `/tasks` | TaskList | Manage all tasks (CRUD) |
| `/tasks/new` | TaskWizard | Create new task (5-step wizard) |
| `/tasks/:id` | TaskDetail | View/edit individual task |
| `/runs` | RunsList | Monitor all task executions |
| `/runs/:id` | RunDetail | View run details and error logs |

---

## Key Features Implemented

### ✅ Complete CRUD for Tasks
- **Create**: 5-step wizard form
- **Read**: List with pagination, detail view
- **Update**: Edit modal with form validation
- **Delete**: Confirmation dialog with cascading deletes

### ✅ Run Management
- **Trigger**: Run button from task cards
- **Monitor**: Global runs list with filtering
- **Details**: View logs, error rows, execution stats
- **Status**: Real-time status badges (SUCCESS, FAILED, RUNNING, etc.)

### ✅ Dashboard Analytics
- Stats cards (total tasks, running, succeeded, failed)
- Recent runs list with trends
- Quick action shortcuts
- Health status indicator

### ✅ User Experience
- Responsive design (mobile + desktop)
- Loading states on all operations
- Error messages with recovery options
- Confirmation dialogs for destructive actions
- Copy-to-clipboard for URLs

---

## API Integration

All requests are made via React Query hooks. Example:

```typescript
// In a component
const { data: tasks, isLoading, error } = useTasks(skip, limit, isActive)
const createTaskMutation = useCreateTask()

// Create a task
await createTaskMutation.mutateAsync(taskFormData)

// Lists all automatically invalidate and refetch
```

### API Base URL
- Dev: `http://localhost:8000/api/v1` (via Vite proxy)
- Prod: `https://your-domain.com/api/v1` (configure in ApiClient)

### Endpoints Covered
```
Tasks:
  POST   /tasks                  → Create task
  GET    /tasks?skip=0&limit=10  → List tasks
  GET    /tasks/{id}             → Get task
  PUT    /tasks/{id}             → Update task
  DELETE /tasks/{id}             → Delete task

Runs:
  POST   /tasks/{id}/run         → Trigger run
  GET    /tasks/{id}/runs        → List task runs
  GET    /runs                   → List all runs
  GET    /runs/{id}              → Get run details
  GET    /tasks/{id}/stats       → Task statistics
```

---

## Development Tips

### Hot Module Reload (HMR)
- Save a file → instant reload in browser
- Component state is preserved
- Styles update without reload

### React Query DevTools
To add React Query DevTools for debugging:
```bash
npm install @tanstack/react-query-devtools
```

Then in App.tsx:
```typescript
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      {/* ... routes ... */}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  )
}
```

### Debugging API Calls
1. Open browser DevTools (F12)
2. Go to Network tab
3. Make an API call
4. Click the request to see headers, body, response

### Tailwind CSS Utilities
All styles use Tailwind utility classes. Reference:
- https://tailwindcss.com/docs
- Spacing: `p-4` = 1rem padding, `m-2` = 0.5rem margin
- Colors: `text-red-600`, `bg-blue-100`
- Responsive: `md:grid-cols-2` (medium screens and up)

---

## Environment Variables

None required for dev. Set these in `.env` for production:

```env
VITE_API_BASE_URL=https://your-api.com/api/v1
VITE_APP_NAME=API→DB Importer
```

Access via:
```typescript
const apiUrl = import.meta.env.VITE_API_BASE_URL
```

---

## Troubleshooting

### "Cannot find module '@/...'"
- Check tsconfig.json has `"@/*": ["src/*"]` in paths
- Restart dev server (Ctrl+C, npm run dev)

### "API calls 404"
- Ensure backend running on http://localhost:8000
- Check vite.config.ts has `/api` proxy configured
- Look in Network tab of DevTools to see actual URL

### "React Query not updating"
- Clear browser cache (Ctrl+Shift+Delete)
- Open DevTools Console for errors
- Check network requests to see if API returned data

### "Tailwind styles not applying"
- Styles file imported in main.tsx
- Check class names match Tailwind docs
- Restart dev server if adding new classes

### "TypeScript errors"
- Check types/index.ts for correct interfaces
- Ensure API response matches Type definition
- Run `npm run lint` to see all errors

---

## Next Steps

1. **Start Dev Server**: `npm run dev`
2. **Test Navigation**: Click links in sidebar
3. **Create Task**: Click "New Task" button
4. **Trigger Run**: Run button on task card
5. **View Details**: Click run card to see logs
6. **Write Tests**: Add test files in `src/__tests__/`

---

## Production Build

```bash
npm run build
npm run preview

# dist/ folder contains optimized production build
# Can be deployed to any static host (Netlify, Vercel, etc.)
```

---

## Support

- **Documentation**: Check README.md in each folder
- **API Docs**: Backend OpenAPI at http://localhost:8000/docs
- **React Query**: https://tanstack.com/query/latest
- **Tailwind**: https://tailwindcss.com/docs

---

**Last Updated:** Current Session  
**Version:** 0.1.0-alpha
