import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import PostCreationWizard from '../PostCreationWizard';
import { postService } from '../../../services/post';
import { contentService } from '../../../services/content';

// Mock the services
jest.mock('../../../services/post');
jest.mock('../../../services/content');

const mockPostService = postService as jest.Mocked<typeof postService>;
const mockContentService = contentService as jest.Mocked<typeof contentService>;

const mockPlatforms = {
  facebook: {
    name: 'Facebook',
    type: 'social',
    title_max_length: 255,
    description_max_length: 8000,
    hashtag_limit: 5,
    features: ['posts', 'pages', 'groups']
  },
  instagram: {
    name: 'Instagram',
    type: 'social',
    title_max_length: 100,
    description_max_length: 2200,
    hashtag_limit: 30,
    features: ['posts', 'stories', 'reels']
  }
};

const mockGeneratedContent = {
  title: 'Test Product Title',
  description: 'Test product description',
  hashtags: ['#test', '#product'],
  variations: [],
  platform_specific: {
    facebook: {
      title: 'Facebook Title',
      description: 'Facebook description',
      hashtags: ['#facebook'],
      call_to_action: 'Shop Now',
      character_count: { title: 14, description: 19 },
      optimization_notes: 'Optimized for Facebook'
    }
  }
};

describe('PostCreationWizard', () => {
  beforeEach(() => {
    mockContentService.getSupportedPlatforms.mockResolvedValue({
      success: true,
      platforms: mockPlatforms,
      total_count: 2
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('renders the wizard with initial step', async () => {
    render(<PostCreationWizard />);
    
    expect(screen.getByText('Create New Post')).toBeInTheDocument();
    expect(screen.getByText('Content')).toBeInTheDocument();
    expect(screen.getByText('Add your post content and images')).toBeInTheDocument();
  });

  it('loads platforms on mount', async () => {
    render(<PostCreationWizard />);
    
    await waitFor(() => {
      expect(mockContentService.getSupportedPlatforms).toHaveBeenCalled();
    });
  });

  it('populates form with generated content', () => {
    render(
      <PostCreationWizard 
        generatedContent={mockGeneratedContent}
      />
    );
    
    expect(screen.getByDisplayValue('Test Product Title')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Test product description')).toBeInTheDocument();
    expect(screen.getByDisplayValue('#test #product')).toBeInTheDocument();
  });

  it('validates content step before allowing next', () => {
    render(<PostCreationWizard />);
    
    const nextButton = screen.getByText('Next');
    expect(nextButton).toBeDisabled();
    
    // Fill in required fields
    fireEvent.change(screen.getByPlaceholderText('Enter post title...'), {
      target: { value: 'Test Title' }
    });
    fireEvent.change(screen.getByPlaceholderText('Enter post description...'), {
      target: { value: 'Test Description' }
    });
    
    // Still disabled because no images
    expect(nextButton).toBeDisabled();
  });

  it('navigates through wizard steps', async () => {
    render(
      <PostCreationWizard 
        initialData={{
          title: 'Test Title',
          description: 'Test Description',
          images: ['image1.jpg'],
          hashtags: ['#test'],
          target_platforms: []
        }}
      />
    );
    
    // Should be on content step
    expect(screen.getByText('Content')).toBeInTheDocument();
    
    // Go to platforms step
    fireEvent.click(screen.getByText('Next'));
    await waitFor(() => {
      expect(screen.getByText('Platforms')).toBeInTheDocument();
    });
    
    // Should not be able to proceed without selecting platforms
    expect(screen.getByText('Next')).toBeDisabled();
  });

  it('handles platform selection', async () => {
    render(
      <PostCreationWizard 
        initialData={{
          title: 'Test Title',
          description: 'Test Description',
          images: ['image1.jpg'],
          hashtags: ['#test'],
          target_platforms: []
        }}
      />
    );
    
    // Navigate to platforms step
    fireEvent.click(screen.getByText('Next'));
    
    await waitFor(() => {
      expect(screen.getByText('Platforms')).toBeInTheDocument();
    });
    
    // Platform selector should be rendered
    // Note: This would need the actual PlatformSelector component to be tested
  });

  it('handles scheduling options', async () => {
    render(
      <PostCreationWizard 
        initialData={{
          title: 'Test Title',
          description: 'Test Description',
          images: ['image1.jpg'],
          hashtags: ['#test'],
          target_platforms: ['facebook']
        }}
      />
    );
    
    // Navigate to schedule step
    fireEvent.click(screen.getByText('Next')); // Content -> Platforms
    fireEvent.click(screen.getByText('Next')); // Platforms -> Schedule
    
    await waitFor(() => {
      expect(screen.getByText('Schedule')).toBeInTheDocument();
    });
    
    // Should have scheduling options
    expect(screen.getByText('Publish immediately after creation')).toBeInTheDocument();
    expect(screen.getByText('Schedule for later')).toBeInTheDocument();
    
    // Select schedule for later
    fireEvent.click(screen.getByLabelText('Schedule for later'));
    
    // Should show datetime input
    expect(screen.getByLabelText('Schedule Date & Time')).toBeInTheDocument();
  });

  it('creates post successfully', async () => {
    const mockPost = {
      id: 'post-1',
      title: 'Test Title',
      description: 'Test Description',
      status: 'draft'
    };
    
    mockPostService.createPost.mockResolvedValue(mockPost as any);
    
    const onPostCreated = jest.fn();
    
    render(
      <PostCreationWizard 
        onPostCreated={onPostCreated}
        initialData={{
          title: 'Test Title',
          description: 'Test Description',
          images: ['image1.jpg'],
          hashtags: ['#test'],
          target_platforms: ['facebook']
        }}
      />
    );
    
    // Navigate to review step
    fireEvent.click(screen.getByText('Next')); // Content -> Platforms
    fireEvent.click(screen.getByText('Next')); // Platforms -> Schedule
    fireEvent.click(screen.getByText('Next')); // Schedule -> Review
    
    await waitFor(() => {
      expect(screen.getByText('Review')).toBeInTheDocument();
    });
    
    // Create post
    fireEvent.click(screen.getByText('Create Post'));
    
    await waitFor(() => {
      expect(mockPostService.createPost).toHaveBeenCalledWith({
        title: 'Test Title',
        description: 'Test Description',
        images: ['image1.jpg'],
        hashtags: ['#test'],
        target_platforms: ['facebook'],
        product_id: undefined,
        scheduled_at: undefined,
        priority: 0,
        platform_specific_content: {}
      });
      expect(onPostCreated).toHaveBeenCalledWith(mockPost);
    });
  });

  it('handles post creation error', async () => {
    mockPostService.createPost.mockRejectedValue(new Error('Creation failed'));
    
    render(
      <PostCreationWizard 
        initialData={{
          title: 'Test Title',
          description: 'Test Description',
          images: ['image1.jpg'],
          hashtags: ['#test'],
          target_platforms: ['facebook']
        }}
      />
    );
    
    // Navigate to review step and create post
    fireEvent.click(screen.getByText('Next')); // Content -> Platforms
    fireEvent.click(screen.getByText('Next')); // Platforms -> Schedule
    fireEvent.click(screen.getByText('Next')); // Schedule -> Review
    
    await waitFor(() => {
      fireEvent.click(screen.getByText('Create Post'));
    });
    
    await waitFor(() => {
      expect(screen.getByText('Creation failed')).toBeInTheDocument();
    });
  });

  it('handles cancel action', () => {
    const onCancel = jest.fn();
    
    render(<PostCreationWizard onCancel={onCancel} />);
    
    fireEvent.click(screen.getByText('Cancel'));
    expect(onCancel).toHaveBeenCalled();
  });

  it('shows loading state during creation', async () => {
    mockPostService.createPost.mockImplementation(() => 
      new Promise(resolve => setTimeout(resolve, 100))
    );
    
    render(
      <PostCreationWizard 
        initialData={{
          title: 'Test Title',
          description: 'Test Description',
          images: ['image1.jpg'],
          hashtags: ['#test'],
          target_platforms: ['facebook']
        }}
      />
    );
    
    // Navigate to review step
    fireEvent.click(screen.getByText('Next')); // Content -> Platforms
    fireEvent.click(screen.getByText('Next')); // Platforms -> Schedule
    fireEvent.click(screen.getByText('Next')); // Schedule -> Review
    
    await waitFor(() => {
      fireEvent.click(screen.getByText('Create Post'));
    });
    
    expect(screen.getByText('Creating...')).toBeInTheDocument();
  });

  it('updates post data correctly', () => {
    render(<PostCreationWizard />);
    
    // Update title
    const titleInput = screen.getByPlaceholderText('Enter post title...');
    fireEvent.change(titleInput, { target: { value: 'New Title' } });
    expect(titleInput).toHaveValue('New Title');
    
    // Update description
    const descriptionInput = screen.getByPlaceholderText('Enter post description...');
    fireEvent.change(descriptionInput, { target: { value: 'New Description' } });
    expect(descriptionInput).toHaveValue('New Description');
    
    // Update hashtags
    const hashtagsInput = screen.getByPlaceholderText('Enter hashtags separated by spaces...');
    fireEvent.change(hashtagsInput, { target: { value: '#new #hashtags' } });
    expect(hashtagsInput).toHaveValue('#new #hashtags');
  });
});