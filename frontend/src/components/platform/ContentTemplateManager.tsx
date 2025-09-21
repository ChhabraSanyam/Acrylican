import React, { useState, useEffect } from 'react';
import { preferencesService, ContentTemplate, CreateContentTemplate, UpdateContentTemplate } from '../../services/preferences';

interface ContentTemplateManagerProps {
  onClose: () => void;
  selectedPlatform?: string;
}

const CONTENT_STYLES = [
  { value: 'professional', label: 'Professional' },
  { value: 'casual', label: 'Casual' },
  { value: 'promotional', label: 'Promotional' },
  { value: 'storytelling', label: 'Storytelling' }
];

const PLATFORMS = [
  { value: 'facebook', label: 'Facebook' },
  { value: 'instagram', label: 'Instagram' },
  { value: 'pinterest', label: 'Pinterest' },
  { value: 'etsy', label: 'Etsy' },
  { value: 'shopify', label: 'Shopify' },
  { value: 'meesho', label: 'Meesho' },
  { value: 'snapdeal', label: 'Snapdeal' },
  { value: 'indiamart', label: 'IndiaMART' }
];

export const ContentTemplateManager: React.FC<ContentTemplateManagerProps> = ({
  onClose,
  selectedPlatform
}) => {
  const [templates, setTemplates] = useState<ContentTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<ContentTemplate | null>(null);
  const [filters, setFilters] = useState({
    platform: selectedPlatform || '',
    style: '',
    category: '',
    include_system: true
  });

  // Form state
  const [formData, setFormData] = useState<CreateContentTemplate>({
    name: '',
    description: '',
    title_template: '',
    description_template: '',
    hashtag_template: '',
    platforms: selectedPlatform ? [selectedPlatform] : [],
    category: '',
    style: 'professional',
    is_default: false
  });

  useEffect(() => {
    loadTemplates();
  }, [filters]);

  const loadTemplates = async () => {
    try {
      setLoading(true);
      const templateList = await preferencesService.getContentTemplates(filters);
      setTemplates(templateList);
    } catch (err) {
      setError('Failed to load templates');
      console.error('Error loading templates:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTemplate = async () => {
    try {
      setError(null);
      await preferencesService.createContentTemplate(formData);
      await loadTemplates();
      setShowCreateForm(false);
      resetForm();
    } catch (err) {
      setError('Failed to create template');
      console.error('Error creating template:', err);
    }
  };

  const handleUpdateTemplate = async () => {
    if (!editingTemplate) return;

    try {
      setError(null);
      await preferencesService.updateContentTemplate(editingTemplate.id, formData);
      await loadTemplates();
      setEditingTemplate(null);
      resetForm();
    } catch (err) {
      setError('Failed to update template');
      console.error('Error updating template:', err);
    }
  };

  const handleDeleteTemplate = async (templateId: string) => {
    if (!confirm('Are you sure you want to delete this template?')) return;

    try {
      setError(null);
      await preferencesService.deleteContentTemplate(templateId);
      await loadTemplates();
    } catch (err) {
      setError('Failed to delete template');
      console.error('Error deleting template:', err);
    }
  };

  const handleEditTemplate = (template: ContentTemplate) => {
    setEditingTemplate(template);
    setFormData({
      name: template.name,
      description: template.description || '',
      title_template: template.title_template,
      description_template: template.description_template,
      hashtag_template: template.hashtag_template || '',
      platforms: template.platforms,
      category: template.category || '',
      style: template.style,
      is_default: template.is_default
    });
    setShowCreateForm(true);
  };

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      title_template: '',
      description_template: '',
      hashtag_template: '',
      platforms: selectedPlatform ? [selectedPlatform] : [],
      category: '',
      style: 'professional',
      is_default: false
    });
    setEditingTemplate(null);
  };

  const handleCancel = () => {
    setShowCreateForm(false);
    resetForm();
  };

  const updateFormData = (field: keyof CreateContentTemplate, value: any) => {
    setFormData({ ...formData, [field]: value });
  };

  const togglePlatform = (platform: string) => {
    const platforms = formData.platforms.includes(platform)
      ? formData.platforms.filter(p => p !== platform)
      : [...formData.platforms, platform];
    updateFormData('platforms', platforms);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg w-full max-w-6xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-semibold">Content Template Manager</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="flex h-[calc(90vh-80px)]">
          {/* Sidebar - Template List */}
          <div className="w-1/2 border-r">
            {/* Filters */}
            <div className="p-4 border-b bg-gray-50">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Platform
                  </label>
                  <select
                    value={filters.platform}
                    onChange={(e) => setFilters({ ...filters, platform: e.target.value })}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                  >
                    <option value="">All Platforms</option>
                    {PLATFORMS.map((platform) => (
                      <option key={platform.value} value={platform.value}>
                        {platform.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Style
                  </label>
                  <select
                    value={filters.style}
                    onChange={(e) => setFilters({ ...filters, style: e.target.value })}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                  >
                    <option value="">All Styles</option>
                    {CONTENT_STYLES.map((style) => (
                      <option key={style.value} value={style.value}>
                        {style.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="mt-4 flex items-center justify-between">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={filters.include_system}
                    onChange={(e) => setFilters({ ...filters, include_system: e.target.checked })}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="ml-2 text-sm text-gray-700">Include system templates</span>
                </label>

                <button
                  onClick={() => setShowCreateForm(true)}
                  className="px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700"
                >
                  Create Template
                </button>
              </div>
            </div>

            {/* Template List */}
            <div className="overflow-y-auto h-full">
              {loading ? (
                <div className="flex items-center justify-center h-32">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </div>
              ) : templates.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  No templates found
                </div>
              ) : (
                <div className="p-4 space-y-3">
                  {templates.map((template) => (
                    <div
                      key={template.id}
                      className="border border-gray-200 rounded-lg p-4 hover:border-gray-300"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center space-x-2">
                            <h3 className="font-medium text-gray-900">{template.name}</h3>
                            {template.is_default && (
                              <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded">
                                Default
                              </span>
                            )}
                            {template.is_system_template && (
                              <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">
                                System
                              </span>
                            )}
                          </div>
                          {template.description && (
                            <p className="text-sm text-gray-600 mt-1">{template.description}</p>
                          )}
                          <div className="flex items-center space-x-4 mt-2 text-xs text-gray-500">
                            <span>Style: {template.style}</span>
                            <span>Used: {template.usage_count} times</span>
                            <span>Platforms: {template.platforms.length}</span>
                          </div>
                        </div>
                        {!template.is_system_template && (
                          <div className="flex space-x-2">
                            <button
                              onClick={() => handleEditTemplate(template)}
                              className="text-blue-600 hover:text-blue-800 text-sm"
                            >
                              Edit
                            </button>
                            <button
                              onClick={() => handleDeleteTemplate(template.id)}
                              className="text-red-600 hover:text-red-800 text-sm"
                            >
                              Delete
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Main Content - Create/Edit Form */}
          <div className="w-1/2">
            {showCreateForm ? (
              <div className="p-6 overflow-y-auto h-full">
                <h3 className="text-lg font-medium text-gray-900 mb-6">
                  {editingTemplate ? 'Edit Template' : 'Create New Template'}
                </h3>

                {error && (
                  <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md">
                    <p className="text-red-600">{error}</p>
                  </div>
                )}

                <div className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Template Name *
                    </label>
                    <input
                      type="text"
                      value={formData.name}
                      onChange={(e) => updateFormData('name', e.target.value)}
                      className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Enter template name"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Description
                    </label>
                    <textarea
                      value={formData.description}
                      onChange={(e) => updateFormData('description', e.target.value)}
                      rows={2}
                      className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Optional description"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Title Template *
                    </label>
                    <input
                      type="text"
                      value={formData.title_template}
                      onChange={(e) => updateFormData('title_template', e.target.value)}
                      className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="e.g., ✨ {title} ✨"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Use {'{title}'} as placeholder for the product title
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Description Template *
                    </label>
                    <textarea
                      value={formData.description_template}
                      onChange={(e) => updateFormData('description_template', e.target.value)}
                      rows={4}
                      className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="e.g., {description}&#10;&#10;🔹 High Quality&#10;🔹 Fast Shipping"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Use {'{description}'} as placeholder for the product description
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Hashtag Template
                    </label>
                    <input
                      type="text"
                      value={formData.hashtag_template}
                      onChange={(e) => updateFormData('hashtag_template', e.target.value)}
                      className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="e.g., #handmade #artisan #quality"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Style *
                      </label>
                      <select
                        value={formData.style}
                        onChange={(e) => updateFormData('style', e.target.value)}
                        className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        {CONTENT_STYLES.map((style) => (
                          <option key={style.value} value={style.value}>
                            {style.label}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Category
                      </label>
                      <input
                        type="text"
                        value={formData.category}
                        onChange={(e) => updateFormData('category', e.target.value)}
                        className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="e.g., jewelry, clothing"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Platforms *
                    </label>
                    <div className="grid grid-cols-2 gap-2">
                      {PLATFORMS.map((platform) => (
                        <label key={platform.value} className="flex items-center">
                          <input
                            type="checkbox"
                            checked={formData.platforms.includes(platform.value)}
                            onChange={() => togglePlatform(platform.value)}
                            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                          />
                          <span className="ml-2 text-sm text-gray-700">{platform.label}</span>
                        </label>
                      ))}
                    </div>
                  </div>

                  <div>
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={formData.is_default}
                        onChange={(e) => updateFormData('is_default', e.target.checked)}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span className="ml-2 text-sm font-medium text-gray-700">
                        Set as default template
                      </span>
                    </label>
                  </div>
                </div>

                <div className="flex justify-end space-x-3 mt-8 pt-6 border-t">
                  <button
                    onClick={handleCancel}
                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={editingTemplate ? handleUpdateTemplate : handleCreateTemplate}
                    disabled={!formData.name || !formData.title_template || !formData.description_template || formData.platforms.length === 0}
                    className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {editingTemplate ? 'Update Template' : 'Create Template'}
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-full text-gray-500">
                <div className="text-center">
                  <svg className="w-12 h-12 mx-auto mb-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <p>Select a template to view details or create a new one</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};