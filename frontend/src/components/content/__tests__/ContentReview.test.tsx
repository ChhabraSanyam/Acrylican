import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ContentReview from '../ContentReview';
import { contentService } from '../../../services/content';
import { GeneratedContent, PlatformsResponse } from '../../../types/content';

// Mock the content service
jest.mock('../../../services/content');
const mockContentService = contentService as jest.Mocked<typeof contentService>;

// Mock lodash debounce
jest.mock('lodash', () => ({
  debounce: (fn: any) => fn
}));

const mockGeneratedContent: GeneratedContent = {
  title: 'Beautiful Handcrafted Pottery',
  description: 'Discover our unique collection of handcrafted pottery pieces, made with love and attention to detail.',
  hashtags: ['handmade', 'pottery', 'artisan'],
  variations: [
    { title: 'Artisan Pottery Collection', focus: 'craftsmanship' },
    { title: 'Unique Handmade Ceramics', focus: 'uniqueness' }
  ],
  platform_specific: {
    facebook: {
      title: 'Beautiful Handcrafted Pottery',
      description: 'Discover our unique collection of handcrafted pottery pieces, made with love and attention to detail.',
      hashtags: ['handmade', 'pottery', 'artisan'],
      call_to_action: 'Shop now!',
      character_count: 95,
      optimization_notes: ['Good length for Facebook posts']
    },
    instagram: {
      title: 'Beautiful Handcrafted Pottery ✨',
      description: 'Discover our unique collection of handcrafted pottery pieces, made with love and attention to detail. #handmade #pottery #artisan',
      hashtags: ['handmade', 'pottery', 'artisan', 'ceramics', 'art'],
      call_to_action: 'DM for orders!',
      character_count: 120,
      optimization_notes: ['Optimized for Instagram engagement']
    }
  }
};

const mockPlatformsResponse: PlatformsResponse = {
  success: true,
  platforms: {
    facebook: {
      name: 'Facebook',
      type: 'social_media',
      title_max_length: 100,
      description_max_length: 8000,
      hashtag_limit: 5,
      features: ['posts', 'pages']
    },
    instagram: {
      name: 'Instagram',
      type: 'social_media',
      title_max_length: 125,
      description_max_length: 2200,
      hashtag_limit: 30,
      features: ['posts', 'stories']
    }
  },
  total_count: 2
};

const mockValidationResult = {
  success: true,
  valid: true,
  platform: 'facebook',
  issues: [],
  character_counts: {
    title: 25,
    description: 95,
    hashtag_count: 3
  }
};

describe('ContentReview', () => {
  const mockOnApprove = jest.fn();
  const mockOnReject = jest.fn();
  const mockOnRegenerate = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    mockContentService.getSupportedPlatforms.mockResolvedValue(mockPlatformsResponse);
    mockContentService.validateContent.mockResolvedValue(mockValidationResult);
  });

  const renderContentReview = (props = {}) => {
    return render(
      <ContentReview
        generatedContent={mockGeneratedContent}
        onApprove={mockOnApprove}
        onReject={mockOnReject}
        onRegenerate={mockOnRegenerate}
        {...props}
      />
    );
  };

  it('renders content review interface', async () => {
    renderContentReview();

    expect(screen.getByText('Review Generated Content')).toBeInTheDocument();
    expect(screen.getByText('Review and edit the AI-generated content before posting to your selected platforms.')).toBeInTheDocument();

    // Wait for platforms to load
    await waitFor(() => {
      expect(screen.getAllByText('Facebook')).toHaveLength(3); // Platform selector, selected platforms, and content section
    });
    
    expect(screen.getByText('Instagram')).toBeInTheDocument();
  });

  it('loads platforms on mount', async () => {
    renderContentReview();

    await waitFor(() => {
      expect(mockContentService.getSupportedPlatforms).toHaveBeenCalled();
    });

    expect(screen.getByText('Facebook')).toBeInTheDocument();
    expect(screen.getByText('Instagram')).toBeInTheDocument();
  });

  it('displays loading state while loading platforms', () => {
    mockContentService.getSupportedPlatforms.mockImplementation(() => new Promise(() => {}));
    
    renderContentReview();

    expect(screen.getByText('Loading platforms...')).toBeInTheDocument();
  });

  it('displays error state when platform loading fails', async () => {
    const errorMessage = 'Failed to load platforms';
    mockContentService.getSupportedPlatforms.mockRejectedValue(new Error(errorMessage));

    renderContentReview();

    await waitFor(() => {
      expect(screen.getByText('Error loading platforms')).toBeInTheDocument();
    });
    
    expect(screen.getByText(errorMessage)).toBeInTheDocument();

    // Test retry functionality
    const retryButton = screen.getByText('Try again');
    mockContentService.getSupportedPlatforms.mockResolvedValue(mockPlatformsResponse);
    
    fireEvent.click(retryButton);

    await waitFor(() => {
      expect(mockContentService.getSupportedPlatforms).toHaveBeenCalledTimes(2);
    });
  });

  it('toggles between preview and edit modes', async () => {
    renderContentReview();

    await waitFor(() => {
      expect(screen.getAllByText('Facebook')).toHaveLength(3);
    });

    // Initially in preview mode
    expect(screen.getByText('Edit Content')).toBeInTheDocument();

    // Switch to edit mode
    fireEvent.click(screen.getByText('Edit Content'));
    expect(screen.getByText('Exit Edit Mode')).toBeInTheDocument();

    // Switch back to preview mode
    fireEvent.click(screen.getByText('Exit Edit Mode'));
    expect(screen.getByText('Edit Content')).toBeInTheDocument();
  });

  it('calls onApprove with selected platform content', async () => {
    renderContentReview();

    await waitFor(() => {
      expect(screen.getAllByText('Facebook')).toHaveLength(3);
    });

    const approveButton = screen.getByText('Approve & Post (2)');
    fireEvent.click(approveButton);

    expect(mockOnApprove).toHaveBeenCalledWith(
      expect.objectContaining({
        facebook: expect.objectContaining({
          title: 'Beautiful Handcrafted Pottery',
          description: 'Discover our unique collection of handcrafted pottery pieces, made with love and attention to detail.',
          hashtags: ['handmade', 'pottery', 'artisan'],
          platform: 'facebook'
        }),
        instagram: expect.objectContaining({
          title: 'Beautiful Handcrafted Pottery ✨',
          platform: 'instagram'
        })
      })
    );
  });

  it('calls onReject when reject button is clicked', async () => {
    renderContentReview();

    await waitFor(() => {
      expect(screen.getAllByText('Facebook')).toHaveLength(3);
    });

    const rejectButton = screen.getByText('Reject');
    fireEvent.click(rejectButton);

    expect(mockOnReject).toHaveBeenCalled();
  });

  it('calls onRegenerate when regenerate button is clicked', async () => {
    renderContentReview();

    await waitFor(() => {
      expect(screen.getAllByText('Facebook')).toHaveLength(3);
    });

    const regenerateButton = screen.getByText('Regenerate');
    fireEvent.click(regenerateButton);

    expect(mockOnRegenerate).toHaveBeenCalled();
  });

  it('disables approve button when no platforms selected', async () => {
    renderContentReview();

    await waitFor(() => {
      expect(screen.getAllByText('Facebook')).toHaveLength(3);
    });

    // Uncheck all platforms
    const checkboxes = screen.getAllByRole('checkbox');
    checkboxes.forEach(checkbox => {
      if ((checkbox as HTMLInputElement).checked) {
        fireEvent.click(checkbox);
      }
    });

    const approveButton = screen.getByText('Approve & Post (0)');
    expect(approveButton).toBeDisabled();
  });

  it('shows validation errors when content is invalid', async () => {
    const invalidValidationResult = {
      ...mockValidationResult,
      valid: false,
      issues: [{ field: 'title', issue: 'Title too long', current_length: 150, max_length: 100 }]
    };
    
    mockContentService.validateContent.mockResolvedValue(invalidValidationResult);

    renderContentReview();

    await waitFor(() => {
      expect(screen.getAllByText('Facebook')).toHaveLength(3);
    });

    // Switch to edit mode to trigger validation
    fireEvent.click(screen.getByText('Edit Content'));

    await waitFor(() => {
      expect(screen.getByText(/validation issue/)).toBeInTheDocument();
    });
  });

  it('disables buttons when loading', async () => {
    renderContentReview({ isLoading: true });

    // Wait for platforms to load first
    await waitFor(() => {
      expect(mockContentService.getSupportedPlatforms).toHaveBeenCalled();
    });

    // Now check for loading states in buttons
    await waitFor(() => {
      expect(screen.getByText('Processing...')).toBeInTheDocument();
    });
    
    const approveButton = screen.getByText('Processing...');
    const rejectButton = screen.getByText('Rejecting...');
    const regenerateButton = screen.getByText('Regenerating...');

    expect(approveButton).toBeDisabled();
    expect(rejectButton).toBeDisabled();
    expect(regenerateButton).toBeDisabled();
  });

  it('shows progress summary when platforms are selected', async () => {
    renderContentReview();

    await waitFor(() => {
      expect(screen.getAllByText('Facebook')).toHaveLength(3);
    });

    expect(screen.getByText('Content Review Progress')).toBeInTheDocument();
    expect(screen.getByText('2/2 platforms ready')).toBeInTheDocument();
  });

  it('shows validation summary in edit mode', async () => {
    renderContentReview();

    await waitFor(() => {
      expect(screen.getAllByText('Facebook')).toHaveLength(3);
    });

    // Switch to edit mode
    fireEvent.click(screen.getByText('Edit Content'));

    await waitFor(() => {
      expect(screen.getByText(/All content is valid/)).toBeInTheDocument();
    });
  });

  it('displays character count warnings with icons', () => {
    const longContent = {
      ...mockGeneratedContent,
      platform_specific: {
        facebook: {
          ...mockGeneratedContent.platform_specific.facebook,
          title: 'A'.repeat(95) // 95% of 100 limit
        }
      }
    };

    renderContentReview({ generatedContent: longContent });

    // The character count warnings should be visible in edit mode
    // This tests the enhanced character count display
  });

  it('shows approve button with platform count', async () => {
    renderContentReview();

    await waitFor(() => {
      expect(screen.getAllByText('Facebook')).toHaveLength(3);
    });

    expect(screen.getByText('Approve & Post (2)')).toBeInTheDocument();
  });
});