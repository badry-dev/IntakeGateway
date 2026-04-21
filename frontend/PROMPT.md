# IntakeGateway — Admin Dashboard UI Prompt (Ant Design)

Design a high-quality, production-ready admin dashboard UI for the **IntakeGateway** application using the Ant Design (AntD) system in a React + TypeScript environment. The interface must be visually clean, data-dense, and optimized for usability, following Ant Design principles: clarity, efficiency, and consistency.

> **Migration context**: The frontend is currently built with Radix UI primitives, Tailwind CSS, and CVA (Class Variance Authority). This prompt defines the target Ant Design architecture to migrate toward.

---

## Tech Stack

- **Framework**: React 18 + TypeScript 5 (strict mode)
- **Build Tool**: Vite 5
- **UI Library**: Ant Design 5 (`antd`)
- **Icons**: `@ant-design/icons`
- **Routing**: React Router v6
- **State Management**: React Query (TanStack Query 5) for server state
- **Forms**: Ant Design `Form` component with built-in validation
- **HTTP Client**: Axios
- **Date Handling**: dayjs (Ant Design's default date library)

---

## Visual Design & Theme

- **Theme**: Light (default)
- **Primary Color**: #1677FF (Ant Design blue)
- **Secondary Accent**: #13C2C2 (teal)

### Status Colors
- Success: #52C41A
- Warning: #FAAD14
- Error: #FF4D4F
- Running/In-progress: #1677FF

### Backgrounds
- App background: #F5F7FA
- Card background: #FFFFFF
- Sidebar: #001529 (dark navy)

### Text
- Primary: rgba(0, 0, 0, 0.85)
- Secondary: rgba(0, 0, 0, 0.45)

### Styling Rules
- Borders: subtle (#F0F0F0)
- Shadows: soft (Ant Design defaults)
- Spacing: 8px grid system
- Avoid visual clutter and heavy customization
- Use Ant Design's `ConfigProvider` for global theme configuration

---

## Typography

- Font: System default or Inter
- Hierarchy:
  - Page titles: 20–24px, semi-bold
  - Section headers: 16–18px
  - Body text: 14px

Use spacing and layout over excessive font weights.

---

## Layout

Use Ant Design `Layout` components (`Layout`, `Layout.Sider`, `Layout.Header`, `Layout.Content`):

- **Sider (Sidebar)**:
  - Width: 240px (expanded), 80px (collapsed)
  - Dark theme (#001529)
  - Collapsible with trigger
  - Logo section: Database icon + "IntakeGateway" branding
  - Footer: version info (v0.1.0) + backend connection status indicator

- **Header**:
  - White background
  - Contains:
    - Breadcrumb navigation
    - Notifications icon (BellOutlined)
    - User profile dropdown (avatar + name)

- **Content**:
  - Padding: 24px
  - Background: #F5F7FA
  - Use `Row` / `Col` grid for responsive layouts
  - Group sections using `Card`

---

## Navigation & Iconography

Use `@ant-design/icons` consistently.

### Sidebar Menu

| Section      | Icon                     | Route         |
|-------------|--------------------------|---------------|
| Dashboard   | DashboardOutlined        | `/`           |
| Tasks       | ApiOutlined              | `/tasks`      |
| Runs        | ThunderboltOutlined      | `/runs`       |
| Schedules   | ClockCircleOutlined      | `/schedules`  |
| Settings    | SettingOutlined          | `/settings`   |

### Icon Rules

- Default: outlined icons
- Active menu item: primary color (#1677FF) + subtle background
- Use icons in buttons:
  - Create → PlusOutlined
  - Edit → EditOutlined
  - Delete → DeleteOutlined
  - Run/Execute → PlayCircleOutlined
  - View → EyeOutlined
- Avoid unnecessary icon usage

---

## Core Pages

### 1. Dashboard (`/`)

- **KPI Cards** (4 cards in a `Row` with `Col span={6}`):
  - Running tasks → ThunderboltOutlined (blue)
  - Succeeded runs → CheckCircleOutlined (green)
  - Failed runs → CloseCircleOutlined (red)
  - Total tasks → DatabaseOutlined (default)
  - Use `Card` + `Statistic` with `valueStyle` for status colors
  - Include trend indicators where applicable

- **Recent Runs** section:
  - `Card` containing a `Table` of the latest 5 task executions
  - Columns: Task ID, Status (Tag), Rows Fetched, Rows Inserted, Started At
  - Status column uses color-coded `Tag`:
    - SUCCESS → green
    - FAILED → red
    - RUNNING → blue
    - PENDING → default
    - PARTIAL_SUCCESS → orange

- **Quick Actions** section:
  - `Card` with action buttons:
    - "New Task" → links to `/tasks/new`
    - "View All Tasks" → links to `/tasks`
    - "View All Runs" → links to `/runs`

---

### 2. Tasks Page (`/tasks`)

**Task List** — Use `Card`-based layout (one card per task):

- **Header toolbar**:
  - Left: page title "Tasks"
  - Right: primary "New Task" button (PlusOutlined) → links to `/tasks/new`

- **Each Task Card** displays:
  - Task name (clickable, links to `/tasks/:id`)
  - Description (if available)
  - Active/Inactive status badge (green/gray `Tag`)
  - Schedule indicator (ClockCircleOutlined, green if active)
  - Metadata grid: HTTP Method, Destination Table, Endpoint URL
  - Action buttons:
    - Run (PlayCircleOutlined) — triggers task execution
    - Edit (EditOutlined) — links to `/tasks/:id`
    - Delete (DeleteOutlined) — with confirmation

- **Empty State**: Use `Empty` component with "Create Your First Task" CTA

- **Pagination**: `Pagination` component below the card list

- **Delete Confirmation**: Use `Modal.confirm` with destructive styling

---

### 3. Task Wizard (`/tasks/new`)

Multi-step task creation using `Steps` component:

- **Step 1**: Basic Info (name, description, HTTP method, endpoint URL)
- **Step 2**: Authentication (none, bearer, api_key, basic, oauth)
- **Step 3**: Response Mapping (JSON path, field preview)
- **Step 4**: Column Mappings (source field → destination column)
- **Step 5**: Review & Create

Use `Form` with:
- `Input`, `Select`, `Switch` for fields
- Inline validation with clear error messages
- "Next" / "Previous" / "Create Task" action buttons

---

### 4. Task Detail (`/tasks/:id`)

- **Header**: Task name + active status `Tag` + action buttons (Run, Delete)
- **Tabs** (`Tabs` component):
  - **Details**: Editable form with task configuration
  - **Column Mappings**: `ColumnMappingEditor` — field mapping table with add/edit/delete
  - **Schedules**: `ScheduleEditor` — cron expression management
  - **Upsert Config**: `UpsertConfigEditor` — upsert keys and skip logic

---

### 5. Runs Page (`/runs`)

Use `Table` with:

- **Columns**: ID, Task ID, Status, Rows Fetched, Rows Inserted, Rows Updated, Rows Skipped, Errors, Started At, Finished At
- **Features**:
  - Sorting on all columns
  - Filtering by status (`Select` dropdown)
  - Pagination
- **Status column**: Color-coded `Tag` (same scheme as Dashboard)
- **Row click**: Navigate to `/runs/:id`

---

### 6. Run Detail (`/runs/:id`)

- **Summary Card**: Status tag, row counts (fetched, inserted, updated, skipped, errors), timestamps
- **Execution Logs**: Collapsible `Collapse` panel or `Table` showing log entries
- **Error Breakdown**: `Table` of row-level errors with details

---

### 7. Schedules Page (`/schedules`)

Use `Table` with:

- **Columns**: ID, Task ID, Cron Expression, Active Status, Last Run, Next Run
- **Actions**:
  - Activate/Deactivate toggle (`Switch`)
  - Edit (opens `ScheduleEditor`)
  - Delete (with confirmation)
- **Create**: Button opens a `Modal` or `Drawer` with the schedule form

---

### 8. Settings Page (`/settings`)

Organized using `Tabs`:

- **Database Connections** tab:
  - `Table` listing all connections: Name, Type (Tag), Host:Port, Status, Updated At, Actions
  - Active connection highlighted with `CheckCircleOutlined` badge
  - "Add Connection" button (PlusOutlined) → opens `Modal` with `ConnectionEditor` form
  - Edit button → opens `Modal` with pre-filled form
  - "Set Active" button for inactive connections
  - Info alert (`Alert` component): fallback to environment variables

- **Future tabs**: General settings, notifications, etc.

---

## Forms (Create / Edit)

- Use Ant Design `Form` component with `layout="vertical"`
- Group related fields using `Card` sections

### Input Components
- `Input` / `Input.TextArea`
- `Select` / `Cascader`
- `DatePicker`
- `Switch`
- `Upload`
- `InputNumber`

### Behavior
- Inline validation using `Form.Item` `rules`
- Clear error messages below each field
- Async validation where needed (e.g., test connection)

### Actions
- Primary submit button (blue)
- Secondary cancel button
- Destructive delete button (red, with `Popconfirm`)

### Presentation
- Simple forms → `Modal` (e.g., ConnectionEditor, ScheduleEditor)
- Complex forms → `Drawer` or full page (e.g., TaskWizard)

---

## Data Models

### Task
- `id`, `name`, `description`, `http_method`, `endpoint_path`
- `auth_type` (none | bearer | api_key | basic | oauth)
- `dest_table`, `batch_size`, `is_active`
- `upsert_enabled`, `upsert_keys[]`
- `skip_column`, `skip_value`, `continue_on_error`

### TaskRun
- `id`, `task_id`, `status` (PENDING | RUNNING | SUCCESS | PARTIAL_SUCCESS | FAILED)
- `rows_fetched`, `rows_inserted`, `rows_updated`, `rows_skipped`, `error_count`
- `started_at`, `finished_at`

### ColumnMapping
- `id`, `task_id`, `source_field`, `dest_column`, `transform`, `is_active`

### TaskSchedule
- `id`, `task_id`, `cron_expression`, `is_active`, `last_run_at`, `next_run_at`

### Connection
- `id`, `name`, `db_type` (oracle | postgresql | mysql), `host`, `port`
- `is_default`, `created_at`, `updated_at`

---

## UX & Interaction

- **Loading**:
  - `Skeleton` for initial page loads
  - `Spin` for in-place data refreshes
  - `Loader2`-style spinning icon in buttons during mutations

- **Feedback**:
  - `message.success()` / `message.error()` for quick actions (run triggered, delete complete)
  - `notification` for long-running operations or background task completion

- **Destructive Actions**:
  - `Modal.confirm` for delete operations
  - `Popconfirm` for inline destructive toggles

- **Hover States**:
  - Subtle card shadow elevation on hover (`hoverable` prop on Card)
  - Row highlight on table hover (default Ant Design behavior)

---

## Responsiveness

- Sidebar collapses on smaller screens (use `Sider` `breakpoint` prop)
- Tables scroll horizontally (`scroll={{ x: true }}`)
- KPI cards stack vertically on mobile (`Col` responsive: `xs={24} sm={12} lg={6}`)
- Maintain usability at all breakpoints

---

## Accessibility

- Proper color contrast (Ant Design defaults meet WCAG AA)
- Keyboard navigation support (built into Ant Design components)
- ARIA attributes where needed
- Labels correctly mapped to inputs via `Form.Item`

---

## API Integration

- **Base URL**: `/api/v1` (proxied via Vite to `http://localhost:8000`)
- **HTTP Client**: Axios instance with base URL configured
- **Server State**: React Query (TanStack Query 5)
  - Query key factories per entity (tasks, runs, mappings, schedules, connections)
  - Automatic cache invalidation on mutations
  - Configurable stale times (30s tasks, 15s runs, 60s metadata)
- **Hooks pattern**: Custom hooks wrapping `useQuery` / `useMutation` in `src/hooks/api.ts`

---

## Code Expectations

- React functional components with TypeScript
- Clean folder structure:

```
frontend/src/
├── pages/
│   ├── Dashboard.tsx
│   ├── TaskList.tsx
│   ├── TaskDetail.tsx
│   ├── TaskWizard.tsx
│   ├── RunsList.tsx
│   ├── RunDetail.tsx
│   ├── Schedules.tsx
│   └── Settings.tsx
├── components/
│   ├── ColumnMappingEditor.tsx
│   ├── ConnectionEditor.tsx
│   ├── ScheduleEditor.tsx
│   ├── UpsertConfigEditor.tsx
│   └── layout/
│       ├── AppLayout.tsx        # Layout with Sider + Header + Content
│       └── SidebarMenu.tsx      # Navigation menu component
├── api/
│   └── client.ts               # Axios HTTP client
├── hooks/
│   └── api.ts                  # React Query hooks
├── types/
│   └── index.ts                # TypeScript interfaces
├── lib/
│   └── utils.ts                # Utility functions
├── App.tsx                      # Routing + QueryClientProvider
├── main.tsx                     # React entry point
└── theme.ts                     # Ant Design theme configuration (ConfigProvider token)
```

### Key Conventions
- Import Ant Design components directly: `import { Card, Table, Button } from 'antd'`
- Import icons: `import { PlusOutlined, EditOutlined } from '@ant-design/icons'`
- Use `ConfigProvider` at app root for global theme token overrides
- Use React Query hooks for all data fetching (no direct API calls in components)
- TypeScript strict mode — all props and state properly typed
- Path alias: `@/*` maps to `src/*`
