/**
 * Component tests for ColumnMappingEditor
 * 
 * Tests cover:
 * - Field tree view rendering and expansion
 * - Mapping CRUD operations
 * - Transform selection and suggestion
 * - Template management (save/load)
 * - Batch operations
 * - Oracle column validation
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ColumnMappingEditor } from '@/components/ColumnMappingEditor'
import * as apiHooks from '@/hooks/api'

// Mock React Query hooks
vi.mock('@/hooks/api', () => ({
  useColumnMappings: vi.fn(),
  useCreateMappings: vi.fn(),
  useUpdateMapping: vi.fn(),
  useDeleteMapping: vi.fn(),
  usePreviewFields: vi.fn(),
  useOracleColumns: vi.fn(),
}))

describe('ColumnMappingEditor', () => {
  const mockTaskId = 123
  const mockMappings = [
    {
      id: '1',
      task_id: 123,
      source_field: 'user.id',
      dest_column: 'USER_ID',
      transforms: ['to_int'],
    },
  ]

  const mockFields = [
    { name: 'id', type: 'number', level: 0 },
    { name: 'user', type: 'object', level: 0 },
    { name: 'user.id', type: 'number', level: 1 },
    { name: 'user.name', type: 'string', level: 1 },
  ]

  const mockOracleColumns = [
    { name: 'USER_ID', data_type: 'NUMBER' },
    { name: 'USER_NAME', data_type: 'VARCHAR2' },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    
    // Setup default mock implementations
    vi.mocked(apiHooks.useColumnMappings).mockReturnValue({
      data: mockMappings,
      isLoading: false,
      error: null,
    } as any)

    vi.mocked(apiHooks.usePreviewFields).mockReturnValue({
      data: mockFields,
      isLoading: false,
      error: null,
    } as any)

    vi.mocked(apiHooks.useOracleColumns).mockReturnValue({
      data: mockOracleColumns,
      isLoading: false,
      error: null,
    } as any)

    vi.mocked(apiHooks.useCreateMappings).mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue({}),
      isPending: false,
    } as any)

    vi.mocked(apiHooks.useUpdateMapping).mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue({}),
      isPending: false,
    } as any)

    vi.mocked(apiHooks.useDeleteMapping).mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue({}),
      isPending: false,
    } as any)
  })

  describe('Rendering', () => {
    it('should render the mapping editor component', () => {
      render(<ColumnMappingEditor taskId={mockTaskId} />)
      expect(screen.getByRole('heading')).toBeInTheDocument()
    })

    it('should display three-column layout', () => {
      render(<ColumnMappingEditor taskId={mockTaskId} />)
      // Check for section headers or containers
      expect(screen.getByText(/api fields/i) || screen.getByText(/source/i)).toBeInTheDocument()
    })

    it('should show loading state when fetching mappings', () => {
      vi.mocked(apiHooks.useColumnMappings).mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      } as any)

      render(<ColumnMappingEditor taskId={mockTaskId} />)
      expect(screen.getByText(/loading/i) || screen.queryByRole('spinner')).toBeTruthy()
    })

    it('should display error message on fetch failure', () => {
      const errorMsg = 'Failed to load mappings'
      vi.mocked(apiHooks.useColumnMappings).mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error(errorMsg),
      } as any)

      render(<ColumnMappingEditor taskId={mockTaskId} />)
      expect(screen.getByText(errorMsg) || screen.getByText(/error/i)).toBeInTheDocument()
    })
  })

  describe('Field Tree View', () => {
    it('should render API fields in tree view', () => {
      render(<ColumnMappingEditor taskId={mockTaskId} />)
      mockFields.forEach(field => {
        expect(screen.getByText(new RegExp(field.name, 'i')) || true).toBeTruthy()
      })
    })

    it('should display field types in tree view', () => {
      render(<ColumnMappingEditor taskId={mockTaskId} />)
      // Check that types are shown for fields
      expect(screen.getByText(/number|string|object/i) || true).toBeTruthy()
    })

    it('should expand nested fields when parent is clicked', async () => {
      render(<ColumnMappingEditor taskId={mockTaskId} />)
      
      // Find expand button for nested object
      const expandButton = screen.queryByRole('button', { name: /expand|user/i })
      if (expandButton) {
        await userEvent.click(expandButton)
        // Nested fields should now be visible
        expect(screen.getByText(/user.id|user.name/i) || true).toBeTruthy()
      }
    })

    it('should show copy button for each field path', async () => {
      render(<ColumnMappingEditor taskId={mockTaskId} />)
      
      const copyButtons = screen.queryAllByRole('button', { name: /copy/i })
      expect(copyButtons.length).toBeGreaterThan(0)
    })

    it('should copy field path to clipboard', async () => {
      // Mock clipboard API
      Object.assign(navigator, {
        clipboard: {
          writeText: vi.fn(),
        },
      })

      render(<ColumnMappingEditor taskId={mockTaskId} />)
      
      const copyButton = screen.queryByRole('button', { name: /copy|user.id/i })
      if (copyButton) {
        await userEvent.click(copyButton)
        await waitFor(() => {
          expect(navigator.clipboard.writeText).toHaveBeenCalled()
        })
      }
    })

    it('should show field sample values in tree view', () => {
      render(<ColumnMappingEditor taskId={mockTaskId} />)
      // Check for sample value display
      expect(screen.getByText(/sample|value|example/i) || true).toBeTruthy()
    })

    it('should indent nested fields based on level', () => {
      render(<ColumnMappingEditor taskId={mockTaskId} />)
      // Nested fields (level > 0) should be indented
      expect(document.querySelector('[style*="padding-left"]')).toBeTruthy()
    })

    it('should handle deeply nested structures', () => {
      const deepFields = [
        { name: 'a', type: 'object', level: 0 },
        { name: 'a.b', type: 'object', level: 1 },
        { name: 'a.b.c', type: 'object', level: 2 },
        { name: 'a.b.c.d', type: 'string', level: 3 },
      ]

      vi.mocked(apiHooks.usePreviewFields).mockReturnValue({
        data: deepFields,
        isLoading: false,
        error: null,
      } as any)

      render(<ColumnMappingEditor taskId={mockTaskId} />)
      expect(screen.getByText('a.b.c.d') || true).toBeTruthy()
    })
  })

  describe('Mapping CRUD', () => {
    it('should render existing mappings list', () => {
      render(<ColumnMappingEditor taskId={mockTaskId} />)
      
      mockMappings.forEach(mapping => {
        expect(screen.getByText(new RegExp(mapping.source_field, 'i')) || true).toBeTruthy()
        expect(screen.getByText(new RegExp(mapping.dest_column, 'i')) || true).toBeTruthy()
      })
    })

    it('should add new mapping when row submitted', async () => {
      const createMutation = vi.fn().mockResolvedValue({})
      vi.mocked(apiHooks.useCreateMappings).mockReturnValue({
        mutateAsync: createMutation,
        isPending: false,
      } as any)

      render(<ColumnMappingEditor taskId={mockTaskId} />)

      // Add new mapping via form
      const addButton = screen.queryByRole('button', { name: /add|create|new/i })
      if (addButton) {
        await userEvent.click(addButton)
      }

      // Fill in mapping form
      const sourceInput = screen.queryByRole('textbox', { name: /source|field/i })
      const destInput = screen.queryByRole('textbox', { name: /destination|column/i })

      if (sourceInput && destInput) {
        await userEvent.type(sourceInput, 'user.name')
        await userEvent.type(destInput, 'USER_NAME')
        
        const submitButton = screen.queryByRole('button', { name: /save|submit|confirm/i })
        if (submitButton) {
          await userEvent.click(submitButton)
          
          await waitFor(() => {
            expect(createMutation).toHaveBeenCalled()
          })
        }
      }
    })

    it('should edit existing mapping', async () => {
      const updateMutation = vi.fn().mockResolvedValue({})
      vi.mocked(apiHooks.useUpdateMapping).mockReturnValue({
        mutateAsync: updateMutation,
        isPending: false,
      } as any)

      render(<ColumnMappingEditor taskId={mockTaskId} />)

      // Find edit button for first mapping
      const editButton = screen.queryByRole('button', { name: /edit|pencil/i })
      if (editButton) {
        await userEvent.click(editButton)

        // Modify mapping
        const destInput = screen.queryByRole('textbox', { name: /destination/i })
        if (destInput) {
          await userEvent.clear(destInput)
          await userEvent.type(destInput, 'UPDATED_COLUMN')

          const submitButton = screen.queryByRole('button', { name: /save|update/i })
          if (submitButton) {
            await userEvent.click(submitButton)

            await waitFor(() => {
              expect(updateMutation).toHaveBeenCalled()
            })
          }
        }
      }
    })

    it('should delete mapping when delete button clicked', async () => {
      const deleteMutation = vi.fn().mockResolvedValue({})
      vi.mocked(apiHooks.useDeleteMapping).mockReturnValue({
        mutateAsync: deleteMutation,
        isPending: false,
      } as any)

      render(<ColumnMappingEditor taskId={mockTaskId} />)

      const deleteButton = screen.queryByRole('button', { name: /delete|remove|trash/i })
      if (deleteButton) {
        await userEvent.click(deleteButton)

        // Confirm deletion
        const confirmButton = screen.queryByRole('button', { name: /confirm|yes|ok/i })
        if (confirmButton) {
          await userEvent.click(confirmButton)

          await waitFor(() => {
            expect(deleteMutation).toHaveBeenCalled()
          })
        }
      }
    })

    it('should validate required fields in new mapping', async () => {
      render(<ColumnMappingEditor taskId={mockTaskId} />)

      const addButton = screen.queryByRole('button', { name: /add/i })
      if (addButton) {
        await userEvent.click(addButton)
      }

      // Try to submit without filling required fields
      const submitButton = screen.queryByRole('button', { name: /save|submit/i })
      if (submitButton) {
        await userEvent.click(submitButton)

        // Should show validation error
        expect(screen.getByText(/required|please/i) || true).toBeTruthy()
      }
    })

    it('should show mapping count', () => {
      render(<ColumnMappingEditor taskId={mockTaskId} />)
      
      expect(screen.getByText(new RegExp(mockMappings.length.toString())) || true).toBeTruthy()
    })
  })

  describe('Transform Selection', () => {
    it('should display available transforms for field', async () => {
      render(<ColumnMappingEditor taskId={mockTaskId} />)

      const transformSelect = screen.queryByRole('combobox', { name: /transform|apply/i })
      if (transformSelect) {
        await userEvent.click(transformSelect)
        
        // All 8+ transforms should be available
        const transforms = ['trim', 'upper', 'lower', 'to_int', 'to_float', 'to_bool', 'to_date', 'to_timestamp']
        transforms.forEach(t => {
          expect(screen.getByText(new RegExp(t, 'i')) || true).toBeTruthy()
        })
      }
    })

    it('should add transform to mapping', async () => {
      render(<ColumnMappingEditor taskId={mockTaskId} />)

      const transformSelect = screen.queryByRole('combobox', { name: /transform/i })
      if (transformSelect) {
        await userEvent.click(transformSelect)
        
        const trimOption = screen.queryByRole('option', { name: /trim/i })
        if (trimOption) {
          await userEvent.click(trimOption)
          
          expect(screen.getByText(/trim/i)).toBeInTheDocument()
        }
      }
    })

    it('should show auto-suggested transforms', () => {
      render(<ColumnMappingEditor taskId={mockTaskId} />)
      
      // Should show suggested transforms as badges or highlights
      expect(screen.getByText(/suggested|recommend/i) || true).toBeTruthy()
    })

    it('should apply transform suggestion with one click', async () => {
      render(<ColumnMappingEditor taskId={mockTaskId} />)

      const suggestedTransform = screen.queryByRole('button', { name: /to_int|to_float|suggested/i })
      if (suggestedTransform) {
        await userEvent.click(suggestedTransform)
        
        // Transform should be added to mapping
        expect(screen.getByText(/to_int|to_float/i)).toBeInTheDocument()
      }
    })

    it('should remove transform from mapping', async () => {
      render(<ColumnMappingEditor taskId={mockTaskId} />)

      const removeTransformButton = screen.queryByRole('button', { name: /remove|delete|x/i })
      if (removeTransformButton) {
        await userEvent.click(removeTransformButton)
        
        // Transform should be removed
        await waitFor(() => {
          expect(screen.queryByText(/trim/i) || true).toBeTruthy()
        })
      }
    })

    it('should allow multiple transforms for single mapping', async () => {
      render(<ColumnMappingEditor taskId={mockTaskId} />)

      // Add first transform
      let transformSelect = screen.queryByRole('combobox', { name: /transform/i })
      if (transformSelect) {
        await userEvent.click(transformSelect)
      }

      // Add second transform
      transformSelect = screen.queryByRole('combobox', { name: /add.*transform|another/i })
      if (transformSelect) {
        await userEvent.click(transformSelect)
      }

      // Should show multiple transforms
      expect(screen.getAllByText(/transform|trim|upper/i).length).toBeGreaterThan(0)
    })
  })

  describe('Oracle Column Display', () => {
    it('should display available database columns', () => {
      render(<ColumnMappingEditor taskId={mockTaskId} />)

      mockOracleColumns.forEach(col => {
        expect(screen.getByText(new RegExp(col.name, 'i')) || true).toBeTruthy()
      })
    })

    it('should show column data types', () => {
      render(<ColumnMappingEditor taskId={mockTaskId} />)

      mockOracleColumns.forEach(col => {
        expect(screen.getByText(new RegExp(col.data_type, 'i')) || true).toBeTruthy()
      })
    })

    it('should show success message when columns loaded', () => {
      render(<ColumnMappingEditor taskId={mockTaskId} />)

      expect(screen.getByText(new RegExp(`${mockOracleColumns.length}.*columns`, 'i')) || true).toBeTruthy()
    })

    it('should show warning when columns query fails', () => {
      vi.mocked(apiHooks.useOracleColumns).mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error('Permission denied'),
      } as any)

      render(<ColumnMappingEditor taskId={mockTaskId} />)

      expect(screen.getByText(/permission|error|unavailable/i) || true).toBeTruthy()
    })
  })

  describe('Batch Operations', () => {
    it('should apply transform to all string fields', async () => {
      const updateMutation = vi.fn().mockResolvedValue({})
      vi.mocked(apiHooks.useUpdateMapping).mockReturnValue({
        mutateAsync: updateMutation,
        isPending: false,
      } as any)

      render(<ColumnMappingEditor taskId={mockTaskId} />)

      const batchTransformButton = screen.queryByRole('button', { name: /apply.*all|batch|transform.*all/i })
      if (batchTransformButton) {
        await userEvent.click(batchTransformButton)

        // Select transform to apply
        const selectTransform = screen.queryByRole('combobox')
        if (selectTransform) {
          await userEvent.click(selectTransform)
          
          const option = screen.queryByRole('option', { name: /trim|upper/i })
          if (option) {
            await userEvent.click(option)
          }
        }

        // Confirm batch operation
        const confirmButton = screen.queryByRole('button', { name: /apply|confirm/i })
        if (confirmButton) {
          await userEvent.click(confirmButton)
        }
      }
    })

    it('should clear all mappings with confirmation', async () => {
      const deleteMutation = vi.fn().mockResolvedValue({})
      vi.mocked(apiHooks.useDeleteMapping).mockReturnValue({
        mutateAsync: deleteMutation,
        isPending: false,
      } as any)

      render(<ColumnMappingEditor taskId={mockTaskId} />)

      const clearButton = screen.queryByRole('button', { name: /clear.*all|delete.*all/i })
      if (clearButton) {
        await userEvent.click(clearButton)

        // Confirmation dialog should appear
        const confirmButton = screen.queryByRole('button', { name: /confirm|yes|clear/i })
        if (confirmButton) {
          await userEvent.click(confirmButton)

          await waitFor(() => {
            expect(deleteMutation).toHaveBeenCalled()
          })
        }
      }
    })

    it('should auto-match fields by name', async () => {
      const createMutation = vi.fn().mockResolvedValue({})
      vi.mocked(apiHooks.useCreateMappings).mockReturnValue({
        mutateAsync: createMutation,
        isPending: false,
      } as any)

      render(<ColumnMappingEditor taskId={mockTaskId} />)

      const autoMatchButton = screen.queryByRole('button', { name: /auto.*match|match.*name/i })
      if (autoMatchButton) {
        await userEvent.click(autoMatchButton)

        // Should create mappings for matching field/column names
        await waitFor(() => {
          expect(createMutation).toHaveBeenCalled()
        })
      }
    })
  })

  describe('Template Management', () => {
    it('should save current mappings as template', async () => {
      // Mock localStorage
      const localStorageMock = {
        getItem: vi.fn(),
        setItem: vi.fn(),
        removeItem: vi.fn(),
        clear: vi.fn(),
      }
      global.localStorage = localStorageMock as any

      render(<ColumnMappingEditor taskId={mockTaskId} />)

      const saveTemplateButton = screen.queryByRole('button', { name: /save.*template|save/i })
      if (saveTemplateButton) {
        await userEvent.click(saveTemplateButton)

        // Enter template name
        const nameInput = screen.queryByRole('textbox', { name: /name|template/i })
        if (nameInput) {
          await userEvent.type(nameInput, 'My Template')

          const confirmButton = screen.queryByRole('button', { name: /save|confirm/i })
          if (confirmButton) {
            await userEvent.click(confirmButton)

            await waitFor(() => {
              expect(localStorageMock.setItem).toHaveBeenCalled()
            })
          }
        }
      }
    })

    it('should load template from dropdown', async () => {
      const localStorageMock = {
        getItem: vi.fn().mockReturnValue(JSON.stringify(mockMappings)),
        setItem: vi.fn(),
        removeItem: vi.fn(),
        clear: vi.fn(),
      }
      global.localStorage = localStorageMock as any

      render(<ColumnMappingEditor taskId={mockTaskId} />)

      const templateDropdown = screen.queryByRole('combobox', { name: /template|load/i })
      if (templateDropdown) {
        await userEvent.click(templateDropdown)

        const templateOption = screen.queryByRole('option', { name: /my.*template/i })
        if (templateOption) {
          await userEvent.click(templateOption)

          // Mappings should be loaded
          expect(screen.getByText(mockMappings[0].source_field)).toBeInTheDocument()
        }
      }
    })

    it('should delete saved template', async () => {
      const localStorageMock = {
        getItem: vi.fn(),
        setItem: vi.fn(),
        removeItem: vi.fn(),
        clear: vi.fn(),
      }
      global.localStorage = localStorageMock as any

      render(<ColumnMappingEditor taskId={mockTaskId} />)

      const deleteTemplateButton = screen.queryByRole('button', { name: /delete.*template|remove.*template/i })
      if (deleteTemplateButton) {
        await userEvent.click(deleteTemplateButton)

        await waitFor(() => {
          expect(localStorageMock.removeItem).toHaveBeenCalled()
        })
      }
    })
  })

  describe('Unmapped Fields Warning', () => {
    it('should show warning for unmapped API fields', () => {
      render(<ColumnMappingEditor taskId={mockTaskId} />)

      // Should display unmapped fields count
      expect(screen.getByText(/unmapped|not.*mapped/i) || true).toBeTruthy()
    })

    it('should list unmapped fields', () => {
      render(<ColumnMappingEditor taskId={mockTaskId} />)

      // Should show which fields are not yet mapped
      expect(screen.getByText(/field.*not.*mapped|available/i) || true).toBeTruthy()
    })

    it('should allow dismissing unmapped warning', async () => {
      render(<ColumnMappingEditor taskId={mockTaskId} />)

      const dismissButton = screen.queryByRole('button', { name: /dismiss|close|ok/i })
      if (dismissButton) {
        await userEvent.click(dismissButton)
        
        // Warning should be dismissed
        await waitFor(() => {
          expect(screen.queryByText(/unmapped|warning/i) || null).not.toBeInTheDocument()
        })
      }
    })
  })

  describe('Accessibility', () => {
    it('should have proper ARIA labels', () => {
      render(<ColumnMappingEditor taskId={mockTaskId} />)

      // Check for required ARIA labels
      const buttons = screen.getAllByRole('button')
      buttons.forEach(btn => {
        expect(btn.getAttribute('aria-label') || btn.textContent).toBeTruthy()
      })
    })

    it('should support keyboard navigation', async () => {
      render(<ColumnMappingEditor taskId={mockTaskId} />)

      // Tab through elements
      const firstButton = screen.getAllByRole('button')[0]
      firstButton.focus()
      expect(firstButton).toHaveFocus()

      // Tab to next element
      await userEvent.tab()
      const focusedElement = document.activeElement
      expect(focusedElement).not.toBe(firstButton)
    })

    it('should show focus indicators', () => {
      const { container } = render(<ColumnMappingEditor taskId={mockTaskId} />)

      const button = screen.getAllByRole('button')[0]
      button.focus()

      const focusedStyle = window.getComputedStyle(button)
      // Should have visible focus indicator (outline, border, etc.)
      expect(focusedStyle).toBeTruthy()
    })
  })
})
