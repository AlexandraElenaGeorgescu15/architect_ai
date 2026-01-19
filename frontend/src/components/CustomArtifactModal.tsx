import { useState, useEffect } from 'react'
import { X, Plus, Sparkles, Loader2, Trash2, Edit2, Save } from 'lucide-react'
import api from '../services/api'
import { useUIStore } from '../stores/uiStore'

interface CustomArtifactType {
  id: string
  name: string
  category: string
  prompt_template: string
  description: string
  default_model?: string
  is_enabled: boolean
  created_at: string
  updated_at: string
}

interface CustomArtifactModalProps {
  isOpen: boolean
  onClose: () => void
  onTypeCreated?: (typeId: string) => void
}

export default function CustomArtifactModal({ isOpen, onClose, onTypeCreated }: CustomArtifactModalProps) {
  const { addNotification } = useUIStore()
  
  // Form state
  const [typeId, setTypeId] = useState('')
  const [name, setName] = useState('')
  const [category, setCategory] = useState('')
  const [customCategory, setCustomCategory] = useState('')
  const [description, setDescription] = useState('')
  const [promptTemplate, setPromptTemplate] = useState(
    `Generate a {artifact_name} based on the following requirements:

{meeting_notes}

Use the following context from the codebase:
{context}

Requirements:
- Be specific and actionable
- Follow best practices
- Include relevant details from the context`
  )
  const [defaultModel, setDefaultModel] = useState('')
  
  // List state
  const [customTypes, setCustomTypes] = useState<CustomArtifactType[]>([])
  const [categories, setCategories] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [editingType, setEditingType] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'create' | 'manage'>('create')

  // Load existing custom types and categories
  useEffect(() => {
    if (isOpen) {
      loadCustomTypes()
      loadCategories()
    }
  }, [isOpen])

  const loadCustomTypes = async () => {
    try {
      setLoading(true)
      const response = await api.get('/api/generation/artifact-types/custom', {
        params: { include_disabled: true }
      })
      if (response.data.success) {
        setCustomTypes(response.data.custom_types || [])
      }
    } catch (error) {
      console.error('Failed to load custom types:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadCategories = async () => {
    try {
      const response = await api.get('/api/generation/artifact-types/categories')
      if (response.data.success) {
        setCategories(response.data.categories || [])
      }
    } catch (error) {
      console.error('Failed to load categories:', error)
    }
  }

  const resetForm = () => {
    setTypeId('')
    setName('')
    setCategory('')
    setCustomCategory('')
    setDescription('')
    setPromptTemplate(
      `Generate a {artifact_name} based on the following requirements:

{meeting_notes}

Use the following context from the codebase:
{context}

Requirements:
- Be specific and actionable
- Follow best practices
- Include relevant details from the context`
    )
    setDefaultModel('')
    setEditingType(null)
  }

  const handleCreate = async () => {
    // Validation
    const finalCategory = category === '__custom__' ? customCategory : category
    
    if (!typeId.trim()) {
      addNotification('error', 'Type ID is required')
      return
    }
    if (!name.trim()) {
      addNotification('error', 'Name is required')
      return
    }
    if (!finalCategory.trim()) {
      addNotification('error', 'Category is required')
      return
    }
    if (!promptTemplate.trim()) {
      addNotification('error', 'Prompt template is required')
      return
    }

    setSaving(true)
    try {
      const response = await api.post('/api/generation/artifact-types/custom', null, {
        params: {
          type_id: typeId.toLowerCase().replace(/\s+/g, '_'),
          name: name.trim(),
          category: finalCategory.trim(),
          prompt_template: promptTemplate.trim(),
          description: description.trim(),
          default_model: defaultModel || undefined
        }
      })

      if (response.data.success) {
        addNotification('success', `Custom artifact type "${name}" created successfully!`)
        resetForm()
        loadCustomTypes()
        if (onTypeCreated) {
          onTypeCreated(response.data.custom_type.id)
        }
      }
    } catch (error: any) {
      addNotification('error', error?.response?.data?.detail || 'Failed to create custom artifact type')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm(`Are you sure you want to delete "${id}"? This cannot be undone.`)) {
      return
    }

    try {
      const response = await api.delete(`/api/generation/artifact-types/custom/${id}`)
      if (response.data.success) {
        addNotification('success', `Custom artifact type "${id}" deleted`)
        loadCustomTypes()
      }
    } catch (error: any) {
      addNotification('error', error?.response?.data?.detail || 'Failed to delete custom artifact type')
    }
  }

  const handleToggleEnabled = async (id: string, currentEnabled: boolean) => {
    try {
      const response = await api.put(`/api/generation/artifact-types/custom/${id}`, null, {
        params: { is_enabled: !currentEnabled }
      })
      if (response.data.success) {
        addNotification('success', `Custom artifact type "${id}" ${!currentEnabled ? 'enabled' : 'disabled'}`)
        loadCustomTypes()
      }
    } catch (error: any) {
      addNotification('error', error?.response?.data?.detail || 'Failed to update custom artifact type')
    }
  }

  const startEditing = (type: CustomArtifactType) => {
    setEditingType(type.id)
    setTypeId(type.id)
    setName(type.name)
    setCategory(type.category)
    setDescription(type.description)
    setPromptTemplate(type.prompt_template)
    setDefaultModel(type.default_model || '')
    setActiveTab('create')
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-card border border-border rounded-xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border bg-muted/50">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-primary" />
            <h2 className="text-lg font-semibold text-foreground">Custom Artifact Types</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-muted rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-muted-foreground" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-border">
          <button
            onClick={() => { setActiveTab('create'); resetForm(); }}
            className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === 'create' 
                ? 'text-primary border-b-2 border-primary bg-primary/5' 
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <Plus className="w-4 h-4 inline mr-1" />
            {editingType ? 'Edit Type' : 'Create New'}
          </button>
          <button
            onClick={() => setActiveTab('manage')}
            className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === 'manage' 
                ? 'text-primary border-b-2 border-primary bg-primary/5' 
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <Edit2 className="w-4 h-4 inline mr-1" />
            Manage ({customTypes.length})
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {activeTab === 'create' ? (
            <div className="space-y-4">
              {/* Type ID */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Type ID <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={typeId}
                  onChange={(e) => setTypeId(e.target.value.toLowerCase().replace(/\s+/g, '_'))}
                  placeholder="e.g., security_review"
                  disabled={!!editingType}
                  className="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:opacity-50"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Unique identifier (snake_case, 3-50 characters)
                </p>
              </div>

              {/* Name */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Display Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g., Security Review"
                  className="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
              </div>

              {/* Category */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Category <span className="text-red-500">*</span>
                </label>
                <div className="flex gap-2">
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    className="flex-1 px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
                  >
                    <option value="">Select a category...</option>
                    {categories.map((cat) => (
                      <option key={cat} value={cat}>{cat}</option>
                    ))}
                    <option value="__custom__">+ Custom Category</option>
                  </select>
                  {category === '__custom__' && (
                    <input
                      type="text"
                      value={customCategory}
                      onChange={(e) => setCustomCategory(e.target.value)}
                      placeholder="Enter custom category"
                      className="flex-1 px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
                    />
                  )}
                </div>
              </div>

              {/* Description */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Description
                </label>
                <input
                  type="text"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Brief description of what this artifact generates"
                  className="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
              </div>

              {/* Prompt Template */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Prompt Template <span className="text-red-500">*</span>
                </label>
                <textarea
                  value={promptTemplate}
                  onChange={(e) => setPromptTemplate(e.target.value)}
                  rows={8}
                  className="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 font-mono text-sm"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Use <code className="bg-muted px-1 rounded">{'{meeting_notes}'}</code> and{' '}
                  <code className="bg-muted px-1 rounded">{'{context}'}</code> as placeholders
                </p>
              </div>

              {/* Default Model (optional) */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Preferred Model (optional)
                </label>
                <input
                  type="text"
                  value={defaultModel}
                  onChange={(e) => setDefaultModel(e.target.value)}
                  placeholder="e.g., llama3:8b-instruct-q4_K_M"
                  className="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-primary" />
                </div>
              ) : customTypes.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <p>No custom artifact types yet.</p>
                  <button
                    onClick={() => setActiveTab('create')}
                    className="mt-2 text-primary hover:underline"
                  >
                    Create your first one
                  </button>
                </div>
              ) : (
                customTypes.map((type) => (
                  <div
                    key={type.id}
                    className={`p-3 border rounded-lg ${
                      type.is_enabled 
                        ? 'border-border bg-background' 
                        : 'border-muted bg-muted/30 opacity-60'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium text-foreground">{type.name}</div>
                        <div className="text-xs text-muted-foreground">
                          {type.id} • {type.category}
                        </div>
                        {type.description && (
                          <div className="text-sm text-muted-foreground mt-1">
                            {type.description}
                          </div>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleToggleEnabled(type.id, type.is_enabled)}
                          className={`px-2 py-1 text-xs rounded ${
                            type.is_enabled 
                              ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' 
                              : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
                          }`}
                        >
                          {type.is_enabled ? 'Enabled' : 'Disabled'}
                        </button>
                        <button
                          onClick={() => startEditing(type)}
                          className="p-1 text-blue-500 hover:bg-blue-100 dark:hover:bg-blue-900/30 rounded"
                          title="Edit"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(type.id)}
                          className="p-1 text-red-500 hover:bg-red-100 dark:hover:bg-red-900/30 rounded"
                          title="Delete"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        {activeTab === 'create' && (
          <div className="flex items-center justify-between p-4 border-t border-border bg-muted/30">
            <button
              onClick={resetForm}
              className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Reset
            </button>
            <button
              onClick={handleCreate}
              disabled={saving}
              className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 transition-colors"
            >
              {saving ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  {editingType ? 'Updating...' : 'Creating...'}
                </>
              ) : (
                <>
                  <Save className="w-4 h-4" />
                  {editingType ? 'Update Type' : 'Create Type'}
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
