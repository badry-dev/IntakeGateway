# Phase 6 Implementation Quick Reference

## 🧾 Session Addendum (Jan 30, 2026)
- Added run labels (`task_name`) plus retry metadata (`is_retry`, `retry_of_run_id`) for UI badges.
- Fixed ColumnMappingEditor save crash when mappings lack IDs.

**Last Updated**: January 2026  
**Status**: 10/15 Tasks Complete (Backend + Frontend Infrastructure Done)

---

## 🎯 What's Been Implemented

### Backend: Complete ✅ (1,380+ lines)

| File | Purpose | Status |
|------|---------|--------|
| `api_connector.py` | Fetch API samples, infer types, flatten JSON | ✅ |
| `mapper.py` | Added 3 new transforms (to_timestamp, to_date, format_date) | ✅ |
| `oracle_metadata.py` | Query table schema, type mapping | ✅ |
| `transform_suggester.py` | Recommend transforms based on type mismatch | ✅ |
| `routes/column_mappings.py` | 6 REST endpoints for mapping CRUD | ✅ |
| `schemas/column_mapping.py` | 9 Pydantic schemas with validation | ✅ |

### Frontend Infrastructure: Complete ✅ (700+ lines)

| File | Purpose | Status |
|------|---------|--------|
| `types/index.ts` | 10 TypeScript interfaces | ✅ |
| `hooks/api.ts` | 8 React Query hooks | ✅ |
| `api/client.ts` | 6 API client methods | ✅ |
| `components/ColumnMappingEditor.tsx` | Reusable mapping component (~400 lines) | ✅ |

### Frontend Components: In Progress ⏳

| File | Purpose | Status |
|------|---------|--------|
| `pages/TaskWizard.tsx` | Add Step 4.5: Mapping | ⏳ |
| `pages/TaskDetail.tsx` | Add Mappings Tab | ⏳ |

### Testing: Not Started ❌

| Scope | Count | Status |
|-------|-------|--------|
| Backend Unit Tests | 15+ | ❌ |
| Backend Integration Tests | 8+ | ❌ |
| Frontend Tests | 18+ | ❌ |

---

## 🔧 Key APIs & Functions

### Backend

#### REST Endpoints
```
GET    /api/v1/tasks/{task_id}/mappings                      # List mappings
POST   /api/v1/tasks/{task_id}/mappings                      # Bulk create
PUT    /api/v1/mappings/{mapping_id}                         # Update
DELETE /api/v1/mappings/{mapping_id}                         # Delete
POST   /api/v1/tasks/{task_id}/preview-fields                # Fetch fields
GET    /api/v1/oracle/tables/{table_name}/columns            # Query columns
```

#### Core Functions (api_connector.py)
```python
async fetch_sample_response(method, url, headers, params, json_body, record_path)
    → dict | list
    # Fetch API response and extract at JSONPath

get_record_type_info(data, record_path)
    → dict
    # Flatten nested JSON, infer field types
    # {"user.name": {"field_type": "string", "sample_value": "Alice", ...}}
```

#### Transforms (mapper.py)
```python
TRANSFORMS = {
    "trim": trim,              # Remove whitespace
    "upper": upper,            # UPPERCASE
    "lower": lower,            # lowercase
    "to_int": to_int,          # Parse integer
    "to_float": to_float,      # Parse float
    "to_bool": to_bool,        # Parse boolean
    "to_timestamp": to_timestamp,    # ISO 8601 → TIMESTAMP (NEW)
    "to_date": to_date,              # → DATE (NEW)
    "format_date": format_date,      # → ISO format (NEW)
}
```

### Frontend

#### React Hooks (from hooks/api.ts)
```typescript
useColumnMappings(taskId, skip, limit, activeOnly)
    → Query<ColumnMapping[]>

useCreateMappings()
    → Mutation<({taskId, mappings}) → ColumnMapping[]>

usePreviewFields(taskId, sampleJson?)
    → Query<MappingPreview>

useOracleColumns(tableName)
    → Query<OracleColumnsResponse>

useSuggestTransforms(sourceType, destType)
    → Query<TransformSuggestionsResponse>

useSaveMappingTemplate(onSuccess?)
    → Mutation<MappingTemplate → Promise>

useLoadMappingTemplates()
    → Query<MappingTemplate[]>

useDeleteMappingTemplate(onSuccess?)
    → Mutation<string → Promise>
```

#### ColumnMappingEditor Component
```typescript
<ColumnMappingEditor
  taskId={123}
  fields={[...]}
  oracleColumns={[...]}
  existingMappings={[...]}
  onSave={(mappings) => Promise<void>}
  onFieldsLoad={() => void}
  isLoading={false}
  readOnly={false}
/>
```

---

## 📊 TypeScript Types

### Core Mapping Types
```typescript
interface ColumnMapping {
  id: number
  task_id: number
  source_field: string      // Flattened: "user.address.city"
  dest_column: string       // Oracle column name
  transform_rules?: string  // JSON: "[\"trim\", \"upper\"]"
  is_active: boolean
  created_at: string
  updated_at: string
}

interface ColumnMappingCreate {
  source_field: string
  dest_column: string
  transform_rules?: string | Record<string, any>
  is_active?: boolean
}

interface FieldPreview {
  field_name: string        // "user.address.city"
  field_type: 'string' | 'number' | 'boolean' | 'null' | 'array' | 'object'
  sample_value: any
  nullable: boolean
  parent_path?: string      // "user.address"
}

interface MappingPreview {
  fields: FieldPreview[]
  total_fields: number
  flattened_successfully: boolean
  errors?: string[]
}

interface OracleColumn {
  column_name: string
  data_type: string        // Oracle type: VARCHAR2, NUMBER, DATE, etc.
  nullable: string         // 'Y' or 'N'
  max_length?: number
}

interface TransformSuggestion {
  transform_name: string
  description: string
  confidence: 'high' | 'medium' | 'low'
  reason: string
}

interface MappingTemplate {
  name: string
  description?: string
  mappings: ColumnMappingCreate[]
  created_at: string
  updated_at: string
}
```

---

## 🎨 UI Components

### ColumnMappingEditor Features

**Three-Section Layout**:
1. **Sample Data Loader**
   - Auto-fetch tab (calls API with task config)
   - Manual paste tab (textarea + parse button)
   - Error display with guidance

2. **API Fields Tree (Left Column)**
   - Hierarchical tree view (expandable nodes)
   - Type badges (string, number, etc.)
   - Copy-to-clipboard buttons
   - Shows sample values

3. **Mapping Configuration (Right Column)**
   - Repeating mapping rows
   - Source field input (or select from tree)
   - Destination column select
   - Transform multi-select (pill buttons)
   - Add/remove row buttons

**Transforms UI**:
- 9 transforms available as pill buttons
- Visual feedback (blue = selected)
- Disabled state when read-only
- Hover effects

**Validation**:
- Red error badge for missing fields
- Yellow warning for unmapped fields
- Green success for copied path
- Required field indicators

---

## 🔄 Data Flow Examples

### Sample 1: Nested JSON Flattening

**Input** (API Response):
```json
{
  "user": {
    "id": 123,
    "name": "Alice",
    "address": {
      "city": "NYC",
      "zip": "10001"
    }
  },
  "tags": ["vip", "verified"]
}
```

**Flattened Output** (from get_record_type_info):
```python
{
  "user.id": {
    "field_type": "number",
    "sample_value": 123,
    "nullable": False,
    "parent_path": "user"
  },
  "user.name": {
    "field_type": "string",
    "sample_value": "Alice",
    "nullable": False,
    "parent_path": "user"
  },
  "user.address.city": {
    "field_type": "string",
    "sample_value": "NYC",
    "nullable": False,
    "parent_path": "user.address"
  },
  "user.address.zip": {
    "field_type": "string",
    "sample_value": "10001",
    "nullable": False,
    "parent_path": "user.address"
  },
  "tags": {
    "field_type": "array",
    "sample_value": ["vip", "verified"],
    "nullable": False,
    "parent_path": None
  }
}
```

### Sample 2: Transform Suggestion

**Input** (Type Mismatch):
- Source field type: `"string"` (value: "123")
- Destination column type: `"number"`

**Output** (from transform_suggester):
```json
{
  "source_type": "string",
  "dest_type": "number",
  "suggestions": [
    {
      "transform_name": "to_int",
      "description": "Convert to integer",
      "confidence": "high",
      "reason": "Direct type conversion from string to integer"
    },
    {
      "transform_name": "to_float",
      "description": "Convert to float",
      "confidence": "high",
      "reason": "Direct type conversion from string to float"
    }
  ],
  "requires_transform": true,
  "warning_message": "Type mismatch: string source cannot be directly inserted to number column"
}
```

### Sample 3: Mapping Application

**Mapping Configuration**:
```
Source: "user.name" → Dest: "USER_NAME" → Transforms: [trim, upper]
```

**Data Flow**:
```
Source Row: {"user.name": "  alice  "}
           ↓ (mapping applied)
Dest Row: {"USER_NAME": "ALICE"}
           (trim: "alice" → upper: "ALICE")
```

---

## 🧪 Testing Strategy

### Backend Tests (23+ total)

**Unit Tests** (15+):
```python
test_to_timestamp_iso_format()
test_to_date_multiple_formats()
test_format_date_parsing()
test_flatten_nested_dict()
test_extract_by_path_with_arrays()
test_oracle_type_mapping()
test_transform_suggestions_string_to_number()
test_api_connector_fetch_sample()
test_column_mapping_routes()
```

**Integration Tests** (8+):
```python
test_end_to_end_nested_flattening()
test_three_level_nesting()
test_mapping_pipeline_with_transforms()
test_sample_fetch_and_preview()
```

### Frontend Tests (18+)

**Component Tests** (10+):
```typescript
test_render_tree_view()
test_expand_collapse_nodes()
test_copy_field_path()
test_add_remove_mappings()
test_transform_selection()
test_manual_json_paste()
test_validation_errors()
test_save_mappings()
test_load_templates()
```

**Hook Tests** (5+):
```typescript
test_useColumnMappings()
test_usePreviewFields()
test_useSuggestTransforms()
test_useSaveMappingTemplate()
```

**Integration Tests** (3+):
```typescript
test_taskwizard_step_4_5()
test_taskdetail_mappings_tab()
test_mapping_end_to_end()
```

---

## 📋 File Quick Reference

### Backend Key Files
```
backend/app/
├── api/v1/routes/
│   └── column_mappings.py         [NEW] 6 endpoints
├── db/
│   └── schemas/
│       └── column_mapping.py      [NEW] 9 schemas
├── services/
│   ├── api_connector.py           [ENHANCED] +400 lines
│   ├── mapper.py                  [ENHANCED] +100 lines
│   ├── oracle_metadata.py         [NEW] 200 lines
│   └── transform_suggester.py     [NEW] 250 lines
└── main.py                        [MODIFIED] router registration
```

### Frontend Key Files
```
frontend/src/
├── types/
│   └── index.ts                   [ENHANCED] +10 interfaces
├── hooks/
│   └── api.ts                     [ENHANCED] +8 hooks
├── api/
│   └── client.ts                  [ENHANCED] +6 methods
└── components/
    └── ColumnMappingEditor.tsx    [NEW] 400 lines
```

---

## 🚀 Next Steps for Completion

### Task 11: TaskWizard Step 4.5 (Mapping)
**Estimated**: 2-3 hours
```typescript
// In pages/TaskWizard.tsx
// Add new step between Headers and Review
const steps = [
  'Basic Info',
  'Endpoint',
  'Headers',
  'Mapping',        // ← NEW STEP
  'Review',
  'Confirmation'
];

// Embed ColumnMappingEditor:
<ColumnMappingEditor
  taskId={wizardState.taskId}
  fields={previewedFields}
  oracleColumns={oracleColumns}
  onSave={saveMappings}
/>

// Validation: require min 1 mapping before "Next"
```

### Task 12: TaskDetail Mappings Tab
**Estimated**: 2-3 hours
```typescript
// In pages/TaskDetail.tsx
// Add new tab for mappings management
<Tabs>
  <TabContent value="mappings">
    <ColumnMappingEditor
      taskId={task.id}
      existingMappings={mappings}
      readOnly={false}
      onSave={updateMappings}
    />
    
    <BatchOperations>
      <Button>Apply Transform to All Strings</Button>
      <Button>Auto-Match by Name</Button>
      <Button>Clear All</Button>
    </BatchOperations>
  </TabContent>
</Tabs>
```

### Task 13-15: Testing (25+ tests)
**Estimated**: 4-5 hours
- Backend unit tests for services
- Backend integration tests for pipeline
- Frontend component tests
- Frontend hook tests
- Frontend integration tests

---

## 💡 Key Implementation Notes

### Why This Architecture?

1. **Service Layer**: Business logic separate from routes = testable, reusable
2. **Lenient JSON Parsing**: Don't fail on formatting; guide users to fix
3. **Type-First Design**: TypeScript interfaces + Pydantic = compile-time safety
4. **React Query**: Server state management with caching strategies
5. **Component Isolation**: ColumnMappingEditor works standalone or embedded

### Phase 1 Limitations (Documented)

- Arrays kept as-is, not exploded (Phase 2 feature)
- Simple transforms only (Phase 2: complex formulas)
- localStorage templates only (Phase 2: database storage)
- Type suggestions basic (Phase 2: ML-based suggestions)

### Backwards Compatibility

- ✅ All existing Task/Run functionality preserved
- ✅ Mappings optional (task can run without)
- ✅ Existing tests still pass
- ✅ No breaking changes to API

---

## 📞 Quick Help

### Common Questions

**Q: How do I use the ColumnMappingEditor?**
A: Import it and pass taskId + fields. It handles the rest.

```typescript
import { ColumnMappingEditor } from '@/components/ColumnMappingEditor'

<ColumnMappingEditor
  taskId={task.id}
  fields={fields}
  oracleColumns={columns}
  onSave={handleSave}
/>
```

**Q: What's the difference between transforms?**
A: See [Transforms List](#transforms-list). Each is designed for type conversion or formatting.

**Q: Why is localStorage used for templates?**
A: Phase 1 simplicity. Phase 2 will add database storage for sharing.

**Q: Can I use ColumnMappingEditor outside TaskWizard?**
A: Yes! It's fully reusable. Just pass the required props.

---

**Document Version**: 1.0  
**Last Updated**: January 2026  
**Next Review**: After frontend component completion
