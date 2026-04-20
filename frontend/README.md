# IntakeGateway Frontend

React 18 + TypeScript + **Ant Design 5** dashboard for IntakeGateway.

## Setup

```bash
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

Ensure the backend is running on port 8000 (API requests are proxied via Vite).

## Project Structure

```
src/
├── pages/                     # 8 page components
│   ├── Dashboard.tsx          # KPI cards, recent runs, quick actions
│   ├── TaskList.tsx           # Card-based task list
│   ├── TaskDetail.tsx         # Tabbed view (Details, Schedule, Mappings)
│   ├── TaskWizard.tsx         # 6-step creation wizard
│   ├── RunsList.tsx           # Runs table with status tags
│   ├── RunDetail.tsx          # Stats, logs, error breakdown
│   ├── Schedules.tsx          # Schedule table with filters
│   └── Settings.tsx           # Database connection management
├── components/                # Editor components
│   ├── ColumnMappingEditor.tsx
│   ├── ConnectionEditor.tsx
│   ├── ScheduleEditor.tsx
│   └── UpsertConfigEditor.tsx
├── hooks/
│   └── api.ts                # React Query hooks (all entities)
├── api/
│   └── client.ts             # Axios HTTP client
├── types/
│   └── index.ts              # TypeScript interfaces
├── lib/
│   └── utils.ts              # Date parsing utilities
├── __tests__/                # 14 test files
│   ├── setup.ts              # jest-dom setup
│   ├── components/           # Component tests
│   └── pages/                # Page tests
├── theme.ts                  # Ant Design theme (ConfigProvider token)
├── App.tsx                   # Routing + AntD Layout
├── main.tsx                  # Entry point
└── index.css                 # Minimal global styles
```

## Technology Stack

- **React 18** with TypeScript (strict mode)
- **Vite 5** for development and builds
- **Ant Design 5** (`antd`) for UI components
- **@ant-design/icons** for iconography
- **React Router v6** for navigation (8 routes)
- **React Query** (TanStack Query 5) for server state
- **Axios** for HTTP requests
- **dayjs** for date handling
- **Vitest** + **React Testing Library** for testing

## Features

- Dashboard with Statistic cards and recent runs table
- Task management with card-based list, Modal confirmations, message feedback
- 6-step task creation wizard with Steps component
- Run monitoring with Table, Tag status badges, Collapse for error details
- Schedule management with Table, filter Select, cron presets
- Database connection CRUD with test/activate functionality
- Column mapping editor with Tree field preview
- Dark collapsible sidebar navigation (AntD Layout.Sider)
- Global theme via ConfigProvider (#1677FF primary, #001529 sidebar)
- Responsive design with AntD Row/Col grid

## UI Design

See [PROMPT.md](PROMPT.md) for the full Ant Design UI specification including:
- Theme configuration and color palette
- Layout structure (Sider + Content)
- Component usage per page
- Navigation and iconography conventions

## Scripts

```bash
npm run dev      # Start dev server (port 5173)
npm run build    # TypeScript check + Vite production build
npm run test     # Run Vitest test suite
npm run lint     # ESLint check
```

## Recent Changes (Phase 9)

**Ant Design Migration** - Complete UI library replacement:
- Removed: Radix UI, Tailwind CSS, CVA, lucide-react, react-hook-form
- Added: antd, @ant-design/icons, dayjs
- Rewritten: All 8 pages, 4 editor components, App layout
- Deleted: 11 Radix UI wrapper components (`components/ui/`), Tailwind config, PostCSS config
- Created: `theme.ts` (Ant Design ConfigProvider), `__tests__/setup.ts` (jest-dom)
- Result: Zero TypeScript errors, successful Vite build
