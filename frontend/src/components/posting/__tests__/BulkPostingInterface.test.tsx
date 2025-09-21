import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import BulkPostingInterface from '../BulkPostingInterface';
import { postService } from '../../../services/post';
import { contentService } from '../../../services/content';
import { PostStatus } from '../../../types/post';

// Mock the services
jest.mock('../../../services/post');
jest.mock('../../../services/content');

const mockPostService = postService as jest.Mocked<typeof postService>;
const mockContentService = contentService as jest.Mocked<typeof contentService>;

const mockPosts = [
  {
    id: 'post-1',
    user_id: 'user-1',
    title: 'Test Post 1',
    description: 'Description 1',
    hashtags: ['#test1'],
    images: ['image1.jpg'],
    target_platforms: ['facebook'],
    status: PostStatus.DRAFT,
    priority: 0,
    retry_count: 0,
    max_retries: 3,
    created_at: '2024-01-01T10:00:00Z',
    updated_at: '2024-01-01T10:00:00Z'
  },
  {
    id: 'post-2',
    user_id: 'user-1',
    title: 'Test Post 2',
    description: 'Description 2',
    hashtags: ['#test2'],
    images: ['image2.jpg'],
    target_platforms: ['instagram'],
    status: PostStatus.DRAFT,
    priority: 0,
    retry_count: 0,
    max_retries: 3,
    created_at: '2024-01-02T10:00:00Z',
    updated_at: '2024-01-02T10:00:00Z'
  }
];

const mockPlatforms = {
  facebook: {
    name: 'Facebook',
    type: 'social'
  },
  instagram: {
    name: 'Instagram',
    type: 'social'
  }
};

const mockBulkResults = [
  {
    success: true,
    post_id: 'post-1',
    results: [],
    queued_items: ['queue-1'],
    message: 'Post published successfully'
  },
  {
    success: true,
    post_id: 'post-2',
    results: [],
    queued_items: ['queue-2'],
    message: 'Post published successfully'
  }
];

describe('BulkPostingInterface', () => {
  const defaultProps = {
    posts: mockPosts,
    onBulkAction: jest.fn(),
    onClose: jest.fn()
  };

  beforeEach(() => {
    mockContentService.getSupportedPlatforms.mockResolvedValue({
      success: true,
      platforms: mockPlatforms,
      total_count: 2
    });
    mockPostService.bulkPublish.mockResolvedValue(mockBulkResults as any);
    mockPostService.bulkSchedule.mockResolvedValue(mockBulkResults as any);
    mockPostService.deletePost.mockResolvedValue();
    mockPostService.createPost.mockResolvedValue(mockPosts[0] as any);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('renders bulk posting interface', async () => {
    render(<BulkPostingInterface {...defaultProps} />);
    
    expect(screen.getByText('Bulk Post Management')).toBeInTheDocument();
    expect(screen.getByText('Select Posts (0 selected)')).toBeInTheDocument();
    expect(screen.getByText('Choose Action')).toBeInTheDocument();
  });

  it('displays posts for selection', () => {
    render(<BulkPostingInterface {...defaultProps} />);
    
    expect(screen.getByText('Test Post 1')).toBeInTheDocument();
    expect(screen.getByText('Test Post 2')).toBeInTheDocument();
    expect(screen.getByText('Description 1')).toBeInTheDocument();
    expect(screen.getByText('Description 2')).toBeInTheDocument();
  });

  it('handles post selection', () => {
    render(<BulkPostingInterface {...defaultProps} />);
    
    const post1Checkbox = screen.getAllByRole('checkbox')[1]; // Skip select all
    fireEvent.click(post1Checkbox);
    
    expect(screen.getByText('Select Posts (1 selected)')).toBeInTheDocument();
  });

  it('handles select all functionality', () => {
    render(<BulkPostingInterface {...defaultProps} />);
    
    const selectAllButton = screen.getByText('Select All');
    fireEvent.click(selectAllButton);
    
    expect(screen.getByText('Select Posts (2 selected)')).toBeInTheDocument();
    
    // Click again to deselect all
    fireEvent.click(screen.getByText('Deselect All'));
    expect(screen.getByText('Select Posts (0 selected)')).toBeInTheDocument();
  });

  it('displays bulk action options', () => {
    render(<BulkPostingInterface {...defaultProps} />);
    
    expect(screen.getByText('Publish Now')).toBeInTheDocument();
    expect(screen.getByText('Schedule')).toBeInTheDocument();
    expect(screen.getByText('Delete')).toBeInTheDocument();
    expect(screen.getByText('Duplicate')).toBeInTheDocument();
  });

  it('disables actions when no posts selected', () => {
    render(<BulkPostingInterface {...defaultProps} />);
    
    const publishButton = screen.getByText('Publish Now');
    expect(publishButton).toBeDisabled();
  });

  it('enables actions when posts are selected', () => {
    render(<BulkPostingInterface {...defaultProps} />);
    
    // Select a post
    const post1Checkbox = screen.getAllByRole('checkbox')[1];
    fireEvent.click(post1Checkbox);
    
    const publishButton = screen.getByText('Publish Now');
    expect(publishButton).not.toBeDisabled();
  });

  it('handles publish now action', async () => {
    render(<BulkPostingInterface {...defaultProps} />);
    
    // Select posts
    const post1Checkbox = screen.getAllByRole('checkbox')[1];
    fireEvent.click(post1Checkbox);
    
    // Select publish action
    fireEvent.click(screen.getByText('Publish Now'));
    
    // Execute action
    fireEvent.click(screen.getByText('Execute Publish Now'));
    
    await waitFor(() => {
      expect(mockPostService.bulkPublish).toHaveBeenCalledWith({
        post_ids: ['post-1'],
        platforms: undefined
      });
    });
  });

  it('handles schedule action with date and time', async () => {
    render(<BulkPostingInterface {...defaultProps} />);
    
    // Select posts
    const post1Checkbox = screen.getAllByRole('checkbox')[1];
    fireEvent.click(post1Checkbox);
    
    // Select schedule action
    fireEvent.click(screen.getByText('Schedule'));
    
    // Set schedule date and time
    const dateInput = screen.getByLabelText('Date');
    const timeInput = screen.getByLabelText('Time');
    
    fireEvent.change(dateInput, { target: { value: '2024-12-25' } });
    fireEvent.change(timeInput, { target: { value: '15:30' } });
    
    // Execute action
    fireEvent.click(screen.getByText('Execute Schedule'));
    
    await waitFor(() => {
      expect(mockPostService.bulkSchedule).toHaveBeenCalled();
    });
  });

  it('handles staggered scheduling', async () => {
    render(<BulkPostingInterface {...defaultProps} />);
    
    // Select multiple posts
    const post1Checkbox = screen.getAllByRole('checkbox')[1];
    const post2Checkbox = screen.getAllByRole('checkbox')[2];
    fireEvent.click(post1Checkbox);
    fireEvent.click(post2Checkbox);
    
    // Select schedule action
    fireEvent.click(screen.getByText('Schedule'));
    
    // Enable staggering
    const staggerCheckbox = screen.getByLabelText('Stagger posts over time');
    fireEvent.click(staggerCheckbox);
    
    // Set interval
    const intervalInput = screen.getByDisplayValue('15');
    fireEvent.change(intervalInput, { target: { value: '30' } });
    
    // Set schedule date and time
    fireEvent.change(screen.getByLabelText('Date'), { target: { value: '2024-12-25' } });
    fireEvent.change(screen.getByLabelText('Time'), { target: { value: '15:30' } });
    
    // Execute action
    fireEvent.click(screen.getByText('Execute Schedule'));
    
    await waitFor(() => {
      expect(mockPostService.bulkSchedule).toHaveBeenCalledTimes(2);
    });
  });

  it('handles delete action with confirmation', async () => {
    render(<BulkPostingInterface {...defaultProps} />);
    
    // Select posts
    const post1Checkbox = screen.getAllByRole('checkbox')[1];
    fireEvent.click(post1Checkbox);
    
    // Select delete action
    fireEvent.click(screen.getByText('Delete'));
    
    // Should show confirmation warning
    expect(screen.getByText('Confirm Deletion')).toBeInTheDocument();
    expect(screen.getByText(/1 post\(s\) will be permanently deleted/)).toBeInTheDocument();
    
    // Execute action
    fireEvent.click(screen.getByText('Execute Delete'));
    
    await waitFor(() => {
      expect(mockPostService.deletePost).toHaveBeenCalledWith('post-1');
    });
  });

  it('handles duplicate action', async () => {
    render(<BulkPostingInterface {...defaultProps} />);
    
    // Select posts
    const post1Checkbox = screen.getAllByRole('checkbox')[1];
    fireEvent.click(post1Checkbox);
    
    // Select duplicate action
    fireEvent.click(screen.getByText('Duplicate'));
    
    // Should show duplicate info
    expect(screen.getByText(/1 post\(s\) will be duplicated/)).toBeInTheDocument();
    
    // Execute action
    fireEvent.click(screen.getByText('Execute Duplicate'));
    
    await waitFor(() => {
      expect(mockPostService.createPost).toHaveBeenCalledWith({
        title: 'Test Post 1 (Copy)',
        description: 'Description 1',
        hashtags: ['#test1'],
        images: ['image1.jpg'],
        target_platforms: ['facebook'],
        product_data: undefined,
        platform_specific_content: undefined
      });
    });
  });

  it('shows platform selection for publish action', async () => {
    render(<BulkPostingInterface {...defaultProps} />);
    
    // Select posts and publish action
    const post1Checkbox = screen.getAllByRole('checkbox')[1];
    fireEvent.click(post1Checkbox);
    fireEvent.click(screen.getByText('Publish Now'));
    
    await waitFor(() => {
      expect(screen.getByText('Facebook')).toBeInTheDocument();
      expect(screen.getByText('Instagram')).toBeInTheDocument();
    });
  });

  it('handles platform selection for actions', async () => {
    render(<BulkPostingInterface {...defaultProps} />);
    
    // Select posts and publish action
    const post1Checkbox = screen.getAllByRole('checkbox')[1];
    fireEvent.click(post1Checkbox);
    fireEvent.click(screen.getByText('Publish Now'));
    
    await waitFor(() => {
      // Select Facebook platform
      const facebookCheckbox = screen.getByLabelText('Facebook');
      fireEvent.click(facebookCheckbox);
    });
    
    // Execute action
    fireEvent.click(screen.getByText('Execute Publish Now'));
    
    await waitFor(() => {
      expect(mockPostService.bulkPublish).toHaveBeenCalledWith({
        post_ids: ['post-1'],
        platforms: ['facebook']
      });
    });
  });

  it('shows processing state during action execution', async () => {
    mockPostService.bulkPublish.mockImplementation(() => 
      new Promise(resolve => setTimeout(resolve, 100))
    );
    
    render(<BulkPostingInterface {...defaultProps} />);
    
    // Select posts and execute action
    const post1Checkbox = screen.getAllByRole('checkbox')[1];
    fireEvent.click(post1Checkbox);
    fireEvent.click(screen.getByText('Publish Now'));
    fireEvent.click(screen.getByText('Execute Publish Now'));
    
    expect(screen.getByText('Processing...')).toBeInTheDocument();
  });

  it('displays action results', async () => {
    render(<BulkPostingInterface {...defaultProps} />);
    
    // Select posts and execute action
    const post1Checkbox = screen.getAllByRole('checkbox')[1];
    fireEvent.click(post1Checkbox);
    fireEvent.click(screen.getByText('Publish Now'));
    fireEvent.click(screen.getByText('Execute Publish Now'));
    
    await waitFor(() => {
      expect(screen.getByText('Results')).toBeInTheDocument();
      expect(screen.getByText('Post post-1')).toBeInTheDocument();
      expect(screen.getByText('Success: Post published successfully')).toBeInTheDocument();
    });
  });

  it('handles action errors', async () => {
    mockPostService.bulkPublish.mockRejectedValue(new Error('Bulk action failed'));
    
    render(<BulkPostingInterface {...defaultProps} />);
    
    // Select posts and execute action
    const post1Checkbox = screen.getAllByRole('checkbox')[1];
    fireEvent.click(post1Checkbox);
    fireEvent.click(screen.getByText('Publish Now'));
    fireEvent.click(screen.getByText('Execute Publish Now'));
    
    await waitFor(() => {
      expect(screen.getByText('Bulk action failed')).toBeInTheDocument();
    });
  });

  it('calls onBulkAction callback after successful action', async () => {
    const onBulkAction = jest.fn();
    render(<BulkPostingInterface {...defaultProps} onBulkAction={onBulkAction} />);
    
    // Select posts and execute action
    const post1Checkbox = screen.getAllByRole('checkbox')[1];
    fireEvent.click(post1Checkbox);
    fireEvent.click(screen.getByText('Publish Now'));
    fireEvent.click(screen.getByText('Execute Publish Now'));
    
    await waitFor(() => {
      expect(onBulkAction).toHaveBeenCalledWith(mockBulkResults);
    });
  });

  it('handles close action', () => {
    const onClose = jest.fn();
    render(<BulkPostingInterface {...defaultProps} onClose={onClose} />);
    
    fireEvent.click(screen.getByText('Cancel'));
    expect(onClose).toHaveBeenCalled();
  });

  it('validates schedule action requires date and time', async () => {
    render(<BulkPostingInterface {...defaultProps} />);
    
    // Select posts and schedule action
    const post1Checkbox = screen.getAllByRole('checkbox')[1];
    fireEvent.click(post1Checkbox);
    fireEvent.click(screen.getByText('Schedule'));
    
    // Try to execute without setting date/time
    fireEvent.click(screen.getByText('Execute Schedule'));
    
    await waitFor(() => {
      expect(screen.getByText('Please select a date and time for scheduling')).toBeInTheDocument();
    });
  });
});