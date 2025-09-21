import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ContentTemplateManager } from '../ContentTemplateManager';
import { preferencesService } from '../../../services/preferences';

// Mock the preferences service
jest.mock('../../../services/preferences');
const mockPreferencesService = preferencesService as jest.Mocked<typeof preferencesService>;

const mockTemplates = [
  {
    id: '1',
    user_id: 'user1',
    name: 'Professional Template',
    description: 'A professional template for products',
    title_template: '✨ {title} ✨',
    description_template: '{description}\n\n🔹 High Quality\n🔹 Fast Shipping',
    hashtag_template: '#handmade #quality #professional',
    platforms: ['facebook', 'instagram'],
    category: 'general',
    style: 'professional',
    usage_count: 10,
    is_default: true,
    is_system_template: false,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z'
  },
  {
    id: '2',
    user_id: 'system',
    name: 'System Template',
    description: 'A system-provided template',
    title_template: '{title}',
    description_template: '{description}',
    hashtag_template: '#system #template',
    platforms: ['facebook'],
    category: null,
    style: 'professional',
    usage_count: 50,
    is_default: false,
    is_system_template: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z'
  }
];

describe('ContentTemplateManager', () => {
  const mockOnClose = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    mockPreferencesService.getContentTemplates.mockResolvedValue(mockTemplates);
  });

  it('renders template manager modal', async () => {
    render(<ContentTemplateManager onClose={mockOnClose} />);

    expect(screen.getByText('Content Template Manager')).toBeInTheDocument();
    expect(screen.getByText('Create Template')).toBeInTheDocument();
  });

  it('loads and displays templates', async () => {
    render(<ContentTemplateManager onClose={mockOnClose} />);

    await waitFor(() => {
      expect(mockPreferencesService.getContentTemplates).toHaveBeenCalled();
    });

    expect(screen.getByText('Professional Template')).toBeInTheDocument();
    expect(screen.getByText('System Template')).toBeInTheDocument();
    expect(screen.getByText('Default')).toBeInTheDocument();
    expect(screen.getByText('System')).toBeInTheDocument();
  });

  it('filters templates by platform', async () => {
    render(<ContentTemplateManager onClose={mockOnClose} />);

    await waitFor(() => {
      expect(screen.getByText('Professional Template')).toBeInTheDocument();
    });

    // Change platform filter
    const platformSelect = screen.getByDisplayValue('All Platforms');
    fireEvent.change(platformSelect, { target: { value: 'facebook' } });

    await waitFor(() => {
      expect(mockPreferencesService.getContentTemplates).toHaveBeenCalledWith({
        platform: 'facebook',
        style: '',
        category: '',
        include_system: true
      });
    });
  });

  it('filters templates by style', async () => {
    render(<ContentTemplateManager onClose={mockOnClose} />);

    await waitFor(() => {
      expect(screen.getByText('Professional Template')).toBeInTheDocument();
    });

    // Change style filter
    const styleSelect = screen.getByDisplayValue('All Styles');
    fireEvent.change(styleSelect, { target: { value: 'professional' } });

    await waitFor(() => {
      expect(mockPreferencesService.getContentTemplates).toHaveBeenCalledWith({
        platform: '',
        style: 'professional',
        category: '',
        include_system: true
      });
    });
  });

  it('toggles system templates filter', async () => {
    render(<ContentTemplateManager onClose={mockOnClose} />);

    await waitFor(() => {
      expect(screen.getByText('Professional Template')).toBeInTheDocument();
    });

    // Toggle system templates checkbox
    const systemTemplatesCheckbox = screen.getByLabelText('Include system templates');
    fireEvent.click(systemTemplatesCheckbox);

    await waitFor(() => {
      expect(mockPreferencesService.getContentTemplates).toHaveBeenCalledWith({
        platform: '',
        style: '',
        category: '',
        include_system: false
      });
    });
  });

  it('opens create template form', async () => {
    render(<ContentTemplateManager onClose={mockOnClose} />);

    await waitFor(() => {
      expect(screen.getByText('Create Template')).toBeInTheDocument();
    });

    // Click create template button
    fireEvent.click(screen.getByText('Create Template'));

    expect(screen.getByText('Create New Template')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Enter template name')).toBeInTheDocument();
  });

  it('creates a new template', async () => {
    const newTemplate = { ...mockTemplates[0], id: '3', name: 'New Template' };
    mockPreferencesService.createContentTemplate.mockResolvedValue(newTemplate);

    render(<ContentTemplateManager onClose={mockOnClose} />);

    // Open create form
    fireEvent.click(screen.getByText('Create Template'));

    await waitFor(() => {
      expect(screen.getByText('Create New Template')).toBeInTheDocument();
    });

    // Fill form
    fireEvent.change(screen.getByPlaceholderText('Enter template name'), {
      target: { value: 'New Template' }
    });
    fireEvent.change(screen.getByPlaceholderText('e.g., ✨ {title} ✨'), {
      target: { value: '🌟 {title} 🌟' }
    });
    fireEvent.change(screen.getByPlaceholderText(/e.g., {description}/), {
      target: { value: '{description}\n\nNew template content' }
    });

    // Select platforms
    const facebookCheckbox = screen.getByLabelText('Facebook');
    fireEvent.click(facebookCheckbox);

    // Submit form
    const createButton = screen.getByText('Create Template');
    fireEvent.click(createButton);

    await waitFor(() => {
      expect(mockPreferencesService.createContentTemplate).toHaveBeenCalledWith({
        name: 'New Template',
        description: '',
        title_template: '🌟 {title} 🌟',
        description_template: '{description}\n\nNew template content',
        hashtag_template: '',
        platforms: ['facebook'],
        category: '',
        style: 'professional',
        is_default: false
      });
    });
  });

  it('edits an existing template', async () => {
    const updatedTemplate = { ...mockTemplates[0], name: 'Updated Template' };
    mockPreferencesService.updateContentTemplate.mockResolvedValue(updatedTemplate);

    render(<ContentTemplateManager onClose={mockOnClose} />);

    await waitFor(() => {
      expect(screen.getByText('Professional Template')).toBeInTheDocument();
    });

    // Click edit button
    const editButton = screen.getByText('Edit');
    fireEvent.click(editButton);

    await waitFor(() => {
      expect(screen.getByText('Edit Template')).toBeInTheDocument();
    });

    // Update template name
    const nameInput = screen.getByDisplayValue('Professional Template');
    fireEvent.change(nameInput, { target: { value: 'Updated Template' } });

    // Submit form
    const updateButton = screen.getByText('Update Template');
    fireEvent.click(updateButton);

    await waitFor(() => {
      expect(mockPreferencesService.updateContentTemplate).toHaveBeenCalledWith(
        '1',
        expect.objectContaining({
          name: 'Updated Template'
        })
      );
    });
  });

  it('deletes a template', async () => {
    // Mock window.confirm
    window.confirm = jest.fn(() => true);
    mockPreferencesService.deleteContentTemplate.mockResolvedValue({ message: 'Template deleted' });

    render(<ContentTemplateManager onClose={mockOnClose} />);

    await waitFor(() => {
      expect(screen.getByText('Professional Template')).toBeInTheDocument();
    });

    // Click delete button
    const deleteButton = screen.getByText('Delete');
    fireEvent.click(deleteButton);

    await waitFor(() => {
      expect(mockPreferencesService.deleteContentTemplate).toHaveBeenCalledWith('1');
    });
  });

  it('does not show edit/delete buttons for system templates', async () => {
    render(<ContentTemplateManager onClose={mockOnClose} />);

    await waitFor(() => {
      expect(screen.getByText('System Template')).toBeInTheDocument();
    });

    // System template should not have edit/delete buttons
    const systemTemplateCard = screen.getByText('System Template').closest('div');
    expect(systemTemplateCard).not.toHaveTextContent('Edit');
    expect(systemTemplateCard).not.toHaveTextContent('Delete');
  });

  it('validates required fields in create form', async () => {
    render(<ContentTemplateManager onClose={mockOnClose} />);

    // Open create form
    fireEvent.click(screen.getByText('Create Template'));

    await waitFor(() => {
      expect(screen.getByText('Create New Template')).toBeInTheDocument();
    });

    // Try to submit without required fields
    const createButton = screen.getByText('Create Template');
    expect(createButton).toBeDisabled();

    // Fill required fields
    fireEvent.change(screen.getByPlaceholderText('Enter template name'), {
      target: { value: 'Test Template' }
    });
    fireEvent.change(screen.getByPlaceholderText('e.g., ✨ {title} ✨'), {
      target: { value: '{title}' }
    });
    fireEvent.change(screen.getByPlaceholderText(/e.g., {description}/), {
      target: { value: '{description}' }
    });

    // Select at least one platform
    const facebookCheckbox = screen.getByLabelText('Facebook');
    fireEvent.click(facebookCheckbox);

    // Button should now be enabled
    expect(createButton).not.toBeDisabled();
  });

  it('cancels template creation', async () => {
    render(<ContentTemplateManager onClose={mockOnClose} />);

    // Open create form
    fireEvent.click(screen.getByText('Create Template'));

    await waitFor(() => {
      expect(screen.getByText('Create New Template')).toBeInTheDocument();
    });

    // Fill some fields
    fireEvent.change(screen.getByPlaceholderText('Enter template name'), {
      target: { value: 'Test Template' }
    });

    // Click cancel
    fireEvent.click(screen.getByText('Cancel'));

    // Should return to template list view
    expect(screen.queryByText('Create New Template')).not.toBeInTheDocument();
    expect(screen.getByText('Select a template to view details or create a new one')).toBeInTheDocument();
  });

  it('handles platform selection in form', async () => {
    render(<ContentTemplateManager onClose={mockOnClose} />);

    // Open create form
    fireEvent.click(screen.getByText('Create Template'));

    await waitFor(() => {
      expect(screen.getByText('Create New Template')).toBeInTheDocument();
    });

    // Select multiple platforms
    const facebookCheckbox = screen.getByLabelText('Facebook');
    const instagramCheckbox = screen.getByLabelText('Instagram');
    
    fireEvent.click(facebookCheckbox);
    fireEvent.click(instagramCheckbox);

    expect(facebookCheckbox).toBeChecked();
    expect(instagramCheckbox).toBeChecked();

    // Deselect one platform
    fireEvent.click(facebookCheckbox);
    expect(facebookCheckbox).not.toBeChecked();
    expect(instagramCheckbox).toBeChecked();
  });

  it('displays error message when loading fails', async () => {
    mockPreferencesService.getContentTemplates.mockRejectedValue(new Error('Failed to load'));

    render(<ContentTemplateManager onClose={mockOnClose} />);

    await waitFor(() => {
      expect(screen.getByText('No templates found')).toBeInTheDocument();
    });
  });

  it('displays error message when creating template fails', async () => {
    mockPreferencesService.createContentTemplate.mockRejectedValue(new Error('Failed to create'));

    render(<ContentTemplateManager onClose={mockOnClose} />);

    // Open create form and fill required fields
    fireEvent.click(screen.getByText('Create Template'));

    await waitFor(() => {
      expect(screen.getByText('Create New Template')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByPlaceholderText('Enter template name'), {
      target: { value: 'Test Template' }
    });
    fireEvent.change(screen.getByPlaceholderText('e.g., ✨ {title} ✨'), {
      target: { value: '{title}' }
    });
    fireEvent.change(screen.getByPlaceholderText(/e.g., {description}/), {
      target: { value: '{description}' }
    });
    fireEvent.click(screen.getByLabelText('Facebook'));

    // Submit form
    fireEvent.click(screen.getByText('Create Template'));

    await waitFor(() => {
      expect(screen.getByText('Failed to create template')).toBeInTheDocument();
    });
  });

  it('closes modal when close button is clicked', () => {
    render(<ContentTemplateManager onClose={mockOnClose} />);

    // Click close button (X)
    const closeButton = screen.getByRole('button', { name: /close/i });
    fireEvent.click(closeButton);

    expect(mockOnClose).toHaveBeenCalled();
  });

  it('initializes with selected platform', async () => {
    render(<ContentTemplateManager onClose={mockOnClose} selectedPlatform="facebook" />);

    await waitFor(() => {
      expect(mockPreferencesService.getContentTemplates).toHaveBeenCalledWith({
        platform: 'facebook',
        style: '',
        category: '',
        include_system: true
      });
    });

    // Open create form to check if platform is pre-selected
    fireEvent.click(screen.getByText('Create Template'));

    await waitFor(() => {
      expect(screen.getByLabelText('Facebook')).toBeChecked();
    });
  });
});