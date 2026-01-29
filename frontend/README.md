# API→DB Importer Frontend

React 18 + TypeScript frontend dashboard for the API→DB Importer.

## Setup

```bash
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

### Setup Troubleshooting (Updated January 2026)

If you encounter errors during setup:

1. **PostCSS ES Module Error**
   ```bash
   # Error: "module is not defined in ES module scope"
   mv postcss.config.js postcss.config.cjs
   ```

2. **Radix UI Installation Failure**
   - Ensure `@radix-ui/react-slot` is version `^1.1.0` in package.json (not 2.x)
   - Run `npm install` again

3. **Missing date-fns Dependency**
   ```bash
   npm install date-fns
   ```

4. **Backend Not Running**
   ```bash
   # Start backend server in separate terminal
   cd ../backend
   python -m uvicorn app.main:app --reload --port 8000
   ```

## Project Structure

```
src/
├── components/
│   └── ui/                    # shadcn/ui components
├── pages/                     # Route pages
├── hooks/
│   └── api.ts                # React Query hooks
├── api/
│   └── client.ts             # Axios API client
├── types/
│   └── index.ts              # TypeScript types
├── lib/
│   └── utils.ts              # Utility functions
├── App.tsx                   # Main app component
├── main.tsx                  # Entry point
└── index.css                 # Tailwind styles
```

## Features

- Dashboard with task summary and recent runs
- Task list with pagination
- Task CRUD operations
- Run monitoring with real-time updates
- Run list labels with task name + retry badge
- Responsive design with Tailwind CSS
- Type-safe API client with React Query
- Error handling and loading states

## Technology Stack

- React 18 with TypeScript
- Vite for fast development
- React Router v6 for navigation
- React Query (TanStack Query) for server state
- Tailwind CSS for styling
- shadcn/ui for accessible components
- Lucide icons for UI icons
- Vitest for unit testing
