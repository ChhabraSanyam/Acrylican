import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ContentEditor from '../ContentEditor';
import { contentService } from '../../../services/content';
import { EditableContent, Platform } from '../../../types/content';

// Mock the content service
jest.mock('../../../services/content');
const mockContentService = contentService as jest.Mocked<typeof contentService>;

// Mock lodash debounce
jest.mock('lodash', () => ({
  debounce: (fn: any) => fn
}));

const mockContent: EditableContent = {
  title: 'Beautiful Handcrafted Pottery',
  description: 'Discover our unique collection of handcrafted pottery pieces.',
  hashtags: ['handmade', 'pottery', 'artisan'],
  platform: 'facebook'
};

const mockPlatform: Platform = {
  name: 'Facebook',
  type: 'social_media',
  title_max_length: 100,
  description_max_length: 8000,
  hashtag_limit: 5,
  features: ['posts', 'pages']
};

const mockValidationResult = {
  success: true,
  valid: true,
  platform: 'facebook',
  issues: [],
  character_counts: {
    title: 25,
    description: 60,
    hashtag_count: 3
  }
};

describe('ContentEditor', () => {
  const mockOnContentChange = jest.fn();
  const mockOnValidationUpdate = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    mockContentService.validateContent.mockResolvedValue(mockValidationResult);
  });

  const renderContentEditor = (props = {}) => {
    return render(
      <ContentEditor
        content={mockContent}
        platform={mockPlatform}
        onContentChange={mockOnContentChange}
        onValidationUpdate={mockOnValidationUpdate}
        {...props}
      />
    );
  };

  it('renders content editor with form fields', () => {
    renderContentEditor();

    expect(screen.getByDisplayValue('Beautiful Handcrafted Pottery')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Discover our unique collection of handcrafted pottery pieces.')).toBeInTheDocument();
    expect(screen.getByDisplayValue('handmade, pottery, artisan')).toBeInTheDocument();
  });

  it('displays character counts for each field', () => {
    renderContentEditor();

    expect(screen.getByText('25/100')).toBeInTheDocument(); // Title count
    expect(screen.getByText('60/8000')).toBeInTheDocument(); // Description count
    expect(screen.getByText('3/5')).toBeInTheDocument(); // Hashtag count
  });

  it('calls onContentChange when title is edited', async () => {
    const user = userEvent.setup();
    renderContentEditor();

    const titleInput = screen.getByDisplayValue('Beautiful Handcrafted Pottery');
    await user.clear(titleInput);
    await user.type(titleInput, 'New Title');

    expect(mockOnContentChange).toHaveBeenCalledWith('title', 'New Title');
  });

  it('calls onContentChange when description is edited', async () => {
    const user = userEvent.setup();
    renderContentEditor();

    const descriptionInput = screen.getByDisplayValue('Discover our unique collection of handcrafted pottery pieces.');
    await user.clear(descriptionInput);
    await user.type(descriptionInput, 'New description');

    expect(mockOnContentChange).toHaveBeenCalledWith('description', 'New description');
  });

  it('calls onContentChange when hashtags are edited', async () => {
    const user = userEvent.setup();
    renderContentEditor();

    const hashtagInput = screen.getByDisplayValue('handmade, pottery, artisan');
    await user.clear(hashtagInput);
    await user.type(hashtagInput, 'new, tags');

    expect(mockOnContentChange).toHaveBeenCalledWith('hashtags', ['new', 'tags']);
  });

  it('validates content when content changes', async () => {
    renderContentEditor();

    await waitFor(() => {
      expect(mockContentService.validateContent).toHaveBeenCalledWith(mockContent);
    });
    
    await waitFor(() => {
      expect(mockOnValidationUpdate).toHaveBeenCalledWith(mockValidationResult);
    });
  });

  it('displays validation success state', async () => {
    renderContentEditor();

    await waitFor(() => {
      expect(screen.getByText('Content is valid for Facebook')).toBeInTheDocument();
    });
  });

  it('displays validation errors', async () => {
    const invalidValidationResult = {
      ...mockValidationResult,
      valid: false,
      issues: [
        { field: 'title', issue: 'Title too long', current_length: 150, max_length: 100 },
        { field: 'description', issue: 'Description too long', current_length: 9000, max_length: 8000 }
      ]
    };

    mockContentService.validateContent.mockResolvedValue(invalidValidationResult);
    renderContentEditor();

    await waitFor(() => {
      expect(screen.getByText('2 validation issues:')).toBeInTheDocument();
    });
    
    expect(screen.getByText('Title too long')).toBeInTheDocument();
    expect(screen.getByText('Description too long')).toBeInTheDocument();
  });

  it('shows loading spinner during validation', () => {
    mockContentService.validateContent.mockImplementation(() => new Promise(() => {}));
    renderContentEditor();

    const spinner = screen.getByTestId('validation-spinner');
    expect(spinner).toBeInTheDocument();
  });

  it('displays hashtag tags with remove buttons', () => {
    renderContentEditor();

    expect(screen.getByText('#handmade')).toBeInTheDocument();
    expect(screen.getByText('#pottery')).toBeInTheDocument();
    expect(screen.getByText('#artisan')).toBeInTheDocument();

    // Check for remove buttons by looking for buttons with aria-label
    const removeButtons = screen.getAllByLabelText(/remove hashtag/i);
    expect(removeButtons).toHaveLength(3);
  });

  it('removes hashtag when remove button is clicked', () => {
    renderContentEditor();

    const removeButton = screen.getByLabelText('Remove hashtag handmade');
    fireEvent.click(removeButton);
    
    expect(mockOnContentChange).toHaveBeenCalledWith('hashtags', ['pottery', 'artisan']);
  });

  it('adds suggested hashtag when clicked', () => {
    renderContentEditor();

    const suggestedHashtag = screen.getByText('#craft');
    fireEvent.click(suggestedHashtag);

    expect(mockOnContentChange).toHaveBeenCalledWith('hashtags', ['handmade', 'pottery', 'artisan', 'craft']);
  });

  it('disables suggested hashtags when limit is reached', () => {
    const contentAtLimit = {
      ...mockContent,
      hashtags: ['tag1', 'tag2', 'tag3', 'tag4', 'tag5'] // At limit of 5
    };

    renderContentEditor({ content: contentAtLimit });

    const suggestedHashtag = screen.getByText('#craft');
    expect(suggestedHashtag).toBeDisabled();
  });

  it('disables suggested hashtags that are already added', () => {
    renderContentEditor();

    const handmadeButton = screen.getByText('#handmade');
    expect(handmadeButton).toBeDisabled();
  });

  it('shows live preview of content', () => {
    renderContentEditor();

    expect(screen.getByText('Live Preview')).toBeInTheDocument();
    
    // Check preview content exists
    expect(screen.getByText('Beautiful Handcrafted Pottery')).toBeInTheDocument();
    expect(screen.getByText('Discover our unique collection of handcrafted pottery pieces.')).toBeInTheDocument();
    expect(screen.getByText('#handmade #pottery #artisan')).toBeInTheDocument();
  });

  it('updates live preview when content changes', async () => {
    const user = userEvent.setup();
    renderContentEditor();

    const titleInput = screen.getByDisplayValue('Beautiful Handcrafted Pottery');
    await user.clear(titleInput);
    await user.type(titleInput, 'Updated Title');

    // The preview should update through the parent component's state management
    expect(mockOnContentChange).toHaveBeenCalledWith('title', 'Updated Title');
  });

  it('handles hashtag input parsing correctly', async () => {
    const user = userEvent.setup();
    renderContentEditor();

    const hashtagInput = screen.getByDisplayValue('handmade, pottery, artisan');
    await user.clear(hashtagInput);
    
    // Test various input formats
    await user.type(hashtagInput, '#tag1, tag2, #tag3');
    expect(mockOnContentChange).toHaveBeenCalledWith('hashtags', ['tag1', 'tag2', 'tag3']);
  });

  it('shows character count colors based on usage', () => {
    const longContent = {
      ...mockContent,
      title: 'A'.repeat(95), // 95% of 100 limit
      description: 'B'.repeat(7900) // 98% of 8000 limit
    };

    renderContentEditor({ content: longContent });

    // Should show warning colors for high usage
    expect(screen.getByText('95/100')).toHaveClass('text-yellow-600');
    expect(screen.getByText('7900/8000')).toHaveClass('text-yellow-600');
  });

  it('shows red character count when over limit', () => {
    const overLimitContent = {
      ...mockContent,
      title: 'A'.repeat(105) // Over 100 limit
    };

    const overLimitValidation = {
      ...mockValidationResult,
      valid: false,
      issues: [{ field: 'title', issue: 'Title too long', current_length: 105, max_length: 100 }]
    };

    mockContentService.validateContent.mockResolvedValue(overLimitValidation);
    renderContentEditor({ content: overLimitContent });

    expect(screen.getByText('105/100')).toHaveClass('text-red-600');
  });

  it('does not show hashtag section when platform has no hashtag limit', () => {
    const noHashtagPlatform = {
      ...mockPlatform,
      hashtag_limit: 0
    };

    renderContentEditor({ platform: noHashtagPlatform });

    expect(screen.queryByText('Hashtags')).not.toBeInTheDocument();
    expect(screen.queryByText('Suggested Hashtags')).not.toBeInTheDocument();
  });

  it('shows warning icons for character counts near limits', () => {
    const nearLimitContent = {
      ...mockContent,
      title: 'A'.repeat(95), // 95% of 100 limit
      description: 'B'.repeat(7200) // 90% of 8000 limit
    };

    renderContentEditor({ content: nearLimitContent });

    // Warning icons should be present for high usage
    const warningIcons = screen.getAllByRole('img', { hidden: true });
    expect(warningIcons.length).toBeGreaterThan(0);
  });

  it('has proper accessibility attributes', () => {
    renderContentEditor();

    const titleInput = screen.getByDisplayValue('Beautiful Handcrafted Pottery');
    const descriptionInput = screen.getByDisplayValue('Discover our unique collection of handcrafted pottery pieces.');
    const hashtagInput = screen.getByDisplayValue('handmade, pottery, artisan');

    expect(titleInput).toHaveAttribute('aria-describedby');
    expect(descriptionInput).toHaveAttribute('aria-describedby');
    expect(hashtagInput).toHaveAttribute('aria-describedby');
  });

  it('shows enhanced validation feedback', async () => {
    const invalidValidationResult = {
      ...mockValidationResult,
      valid: false,
      issues: [
        { field: 'title', issue: 'Title too long', current_length: 150, max_length: 100 }
      ]
    };

    mockContentService.validateContent.mockResolvedValue(invalidValidationResult);
    renderContentEditor();

    await waitFor(() => {
      expect(screen.getByText('1 validation issue:')).toBeInTheDocument();
    });

    // Should show enhanced validation display
    expect(screen.getByText('Title too long')).toBeInTheDocument();
  });
});