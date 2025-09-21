import { render, screen, waitFor } from '@testing-library/react';
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
  title: 'Test Product',
  description: 'Test description',
  hashtags: ['test'],
  variations: [],
  platform_specific: {
    facebook: {
      title: 'Test Product',
      description: 'Test description',
      hashtags: ['test'],
      call_to_action: 'Buy now',
      character_count: 50,
      optimization_notes: []
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
      features: ['posts']
    }
  },
  total_count: 1
};

describe('ContentReview Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockContentService.getSupportedPlatforms.mockResolvedValue(mockPlatformsResponse);
    mockContentService.validateContent.mockResolvedValue({
      success: true,
      valid: true,
      platform: 'facebook',
      issues: [],
      character_counts: { title: 12, description: 16, hashtag_count: 1 }
    });
  });

  it('renders and loads content successfully', async () => {
    const mockOnApprove = jest.fn();
    const mockOnReject = jest.fn();
    const mockOnRegenerate = jest.fn();

    render(
      <ContentReview
        generatedContent={mockGeneratedContent}
        onApprove={mockOnApprove}
        onReject={mockOnReject}
        onRegenerate={mockOnRegenerate}
      />
    );

    // Wait for platforms to load
    await waitFor(() => {
      expect(mockContentService.getSupportedPlatforms).toHaveBeenCalled();
    });

    // Check that basic elements are present
    expect(screen.getByText('Review Generated Content')).toBeInTheDocument();
    expect(screen.getByText('Select Platforms')).toBeInTheDocument();
  });

  it('validates content editing functionality', async () => {
    const mockOnApprove = jest.fn();
    const mockOnReject = jest.fn();
    const mockOnRegenerate = jest.fn();

    render(
      <ContentReview
        generatedContent={mockGeneratedContent}
        onApprove={mockOnApprove}
        onReject={mockOnReject}
        onRegenerate={mockOnRegenerate}
      />
    );

    // Wait for platforms to load
    await waitFor(() => {
      expect(mockContentService.getSupportedPlatforms).toHaveBeenCalled();
    });

    // Verify validation is called
    await waitFor(() => {
      expect(mockContentService.validateContent).toHaveBeenCalled();
    });
  });
});