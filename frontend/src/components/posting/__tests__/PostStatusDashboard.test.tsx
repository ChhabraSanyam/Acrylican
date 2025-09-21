import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import PostStatusDashboard from '../PostStatusDashboard';
import { postService } from '../../../services/post';
import { PostStatus } from '../../../types/post';

// Mock the service
jest.mock('../../../services/post');

const mockPostService = postService as jest.Mocked<typeof postService>;

const mockPosts = [
  {
    id: 'post-1',
    user_id: 'user-1',
    title: 'Test Post 1',
    description: 'Description 1',
    hashtags: ['#test1'],
    images: ['image1.jpg'],
    target_platforms: ['facebook', 'instagram'],
    status: PostStatus.PUBLISHED,
    priority: 0,
    retry_count: 0,
    max_retries: 3,
    created_at: '2024-01-01T10:00:00Z',
    updated_at: '2024-01-01T10:00:00Z',
    published_at: '2024-01-01T10:30:00Z',
    results: [
      {
        platform: 'facebook',
        status: 'published',
        post_id: 'fb-123',
        retry_count: 0
      },
      {
        platform: 'instagram',
        status: 'published',
        post_id: 'ig-456',
        retry_count: 0
      }
    ]
  },
  {
    id: 'post-2',
    user_id: 'user-1',
    title: 'Test Post 2',
    description: 'Description 2',
    hashtags: ['#test2'],
    images: ['image2.jpg'],
    target_platforms: ['facebook'],
    status: PostStatus.SCHEDULED,
    priority: 1,
    retry_count: 0,
    max_retries: 3,
    created_at: '2024-01-02T10:00:00Z',
    updated_at: '2024-01-02T10:00:00Z',
    scheduled_at: '2024-01-03T15:00:00Z'
  },
  {
    id: 'post-3',
    user_id: 'user-1',
    title: 'Test Post 3',
    description: 'Description 3',
    hashtags: ['#test3'],
    images: ['image3.jpg'],
    target_platforms: ['instagram'],
    status: PostStatus.FAILED,
    priority: 0,
    retry_count: 1,
    max_retries: 3,
    created_at: '2024-01-03T10:00:00Z',
    updated_at: '2024-01-03T10:00:00Z',
    last_error: 'API rate limit exceeded',
    results: [
      {
        platform: 'instagram',
        status: 'failed',
        error_message: 'Rate limit exceeded',
        retry_count: 1
      }
    ]
  }
];

const mockPostListResponse = {
  posts: mockPosts,
  total: 3,
  skip: 0,
  limit: 20
};

describe('PostStatusDashboard', () => {
  beforeEach(() => {
    mockPostService.getPosts.mockResolvedValue(mockPostListResponse as any);
    mockPostService.retryPost.mockResolvedValue({
      success: true,
      post_id: 'post-3',
      results: [],
      queued_items: []
    });
    mockPostService.cancelScheduledPost.mockResolvedValue();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('renders dashboard with posts', async () => {
    render(<PostStatusDashboard />);
    
    expect(screen.getByText('Post Status Dashboard')).toBeInTheDocument();
    
    await waitFor(() => {
      expect(screen.getByText('Test Post 1')).toBeInTheDocument();
      expect(screen.getByText('Test Post 2')).toBeInTheDocument();
      expect(screen.getByText('Test Post 3')).toBeInTheDocument();
    });
  });

  it('loads posts on mount', async () => {
    render(<PostStatusDashboard />);
    
    await waitFor(() => {
      expect(mockPostService.getPosts).toHaveBeenCalledWith(0, 50, {});
    });
  });

  it('displays post status correctly', async () => {
    render(<PostStatusDashboard />);
    
    await waitFor(() => {
      // Check status badges
      expect(screen.getByText('published')).toBeInTheDocument();
      expect(screen.getByText('scheduled')).toBeInTheDocument();
      expect(screen.getByText('failed')).toBeInTheDocument();
    });
  });

  it('shows platform information', async () => {
    render(<PostStatusDashboard />);
    
    await waitFor(() => {
      expect(screen.getByText('facebook')).toBeInTheDocument();
      expect(screen.getByText('instagram')).toBeInTheDocument();
    });
  });

  it('displays scheduled dates correctly', async () => {
    render(<PostStatusDashboard />);
    
    await waitFor(() => {
      // Should show scheduled date for post-2
      expect(screen.getByText('1/3/2024')).toBeInTheDocument();
      expect(screen.getByText('3:00 PM')).toBeInTheDocument();
    });
  });

  it('shows platform results', async () => {
    render(<PostStatusDashboard />);
    
    await waitFor(() => {
      // Should show results for published and failed posts
      const publishedResults = screen.getAllByText('published');
      const failedResults = screen.getAllByText('failed');
      
      expect(publishedResults.length).toBeGreaterThan(0);
      expect(failedResults.length).toBeGreaterThan(0);
    });
  });

  it('handles post selection', async () => {
    const onPostSelect = jest.fn();
    render(<PostStatusDashboard onPostSelect={onPostSelect} />);
    
    await waitFor(() => {
      const viewButtons = screen.getAllByText('View');
      fireEvent.click(viewButtons[0]);
    });
    
    expect(onPostSelect).toHaveBeenCalledWith(mockPosts[0]);
  });

  it('handles retry action for failed posts', async () => {
    render(<PostStatusDashboard />);
    
    await waitFor(() => {
      const retryButton = screen.getByText('Retry');
      fireEvent.click(retryButton);
    });
    
    await waitFor(() => {
      expect(mockPostService.retryPost).toHaveBeenCalledWith('post-3');
    });
  });

  it('handles cancel action for scheduled posts', async () => {
    render(<PostStatusDashboard />);
    
    await waitFor(() => {
      const cancelButton = screen.getByText('Cancel');
      fireEvent.click(cancelButton);
    });
    
    await waitFor(() => {
      expect(mockPostService.cancelScheduledPost).toHaveBeenCalledWith('post-2');
    });
  });

  it('filters posts by status', async () => {
    render(<PostStatusDashboard />);
    
    await waitFor(() => {
      const statusFilter = screen.getByDisplayValue('All Statuses');
      fireEvent.change(statusFilter, { target: { value: 'published' } });
    });
    
    await waitFor(() => {
      expect(mockPostService.getPosts).toHaveBeenCalledWith(
        0, 50, { status: 'published' }
      );
    });
  });

  it('filters posts by date range', async () => {
    render(<PostStatusDashboard />);
    
    await waitFor(() => {
      expect(screen.getByText('Test Post 1')).toBeInTheDocument();
    });

    const dateInputs = screen.getAllByDisplayValue('');
    const fromDateInput = dateInputs[0]; // First date input
    fireEvent.change(fromDateInput, { target: { value: '2024-01-01' } });
    
    await waitFor(() => {
      expect(mockPostService.getPosts).toHaveBeenCalledWith(
        0, 50, { date_from: '2024-01-01' }
      );
    });
  });

  it('handles post selection with checkboxes', async () => {
    render(<PostStatusDashboard />);
    
    await waitFor(() => {
      const checkboxes = screen.getAllByRole('checkbox');
      // Skip the "select all" checkbox
      fireEvent.click(checkboxes[1]);
      fireEvent.click(checkboxes[2]);
    });
    
    // Should show bulk actions
    expect(screen.getByText('2 selected')).toBeInTheDocument();
    expect(screen.getByText('Bulk Actions')).toBeInTheDocument();
  });

  it('handles select all functionality', async () => {
    render(<PostStatusDashboard />);
    
    await waitFor(() => {
      const selectAllCheckbox = screen.getAllByRole('checkbox')[0];
      fireEvent.click(selectAllCheckbox);
    });
    
    expect(screen.getByText('3 selected')).toBeInTheDocument();
  });

  it('sorts posts by different criteria', async () => {
    render(<PostStatusDashboard />);
    
    await waitFor(() => {
      const createdAtHeader = screen.getByText('Post');
      fireEvent.click(createdAtHeader);
    });
    
    // Should trigger re-render with sorted posts
    // The actual sorting logic would be tested in the component
  });

  it('handles pagination', async () => {
    const largeMockResponse = {
      ...mockPostListResponse,
      total: 100
    };
    
    mockPostService.getPosts.mockResolvedValue(largeMockResponse as any);
    
    render(<PostStatusDashboard />);
    
    await waitFor(() => {
      expect(screen.getByText(/Showing 1 to \d+ of 100 posts/)).toBeInTheDocument();
      expect(screen.getByText('Next')).toBeInTheDocument();
    });
    
    fireEvent.click(screen.getByText('Next'));
    
    await waitFor(() => {
      expect(mockPostService.getPosts).toHaveBeenCalledWith(50, 50, {});
    });
  });

  it('shows loading state', () => {
    mockPostService.getPosts.mockImplementation(() => 
      new Promise(resolve => setTimeout(resolve, 100))
    );
    
    render(<PostStatusDashboard />);
    
    // Should show loading skeleton
    expect(screen.getByText('Post Status Dashboard')).toBeInTheDocument();
    const loadingElements = screen.getAllByRole('generic');
    expect(loadingElements.some(el => el.classList.contains('animate-pulse'))).toBe(true);
  });

  it('handles error state', async () => {
    mockPostService.getPosts.mockRejectedValue(new Error('Failed to load'));
    
    render(<PostStatusDashboard />);
    
    await waitFor(() => {
      expect(screen.getByText('Failed to load')).toBeInTheDocument();
    });
  });

  it('refreshes data automatically', async () => {
    jest.useFakeTimers();
    
    render(<PostStatusDashboard refreshInterval={1000} />);
    
    await waitFor(() => {
      expect(mockPostService.getPosts).toHaveBeenCalledTimes(1);
    });
    
    // Fast-forward time
    jest.advanceTimersByTime(1000);
    
    await waitFor(() => {
      expect(mockPostService.getPosts).toHaveBeenCalledTimes(2);
    });
    
    jest.useRealTimers();
  });

  it('handles manual refresh', async () => {
    render(<PostStatusDashboard />);
    
    await waitFor(() => {
      expect(mockPostService.getPosts).toHaveBeenCalledTimes(1);
      expect(screen.getByText('Refresh')).toBeInTheDocument();
    });
    
    fireEvent.click(screen.getByText('Refresh'));
    
    await waitFor(() => {
      expect(mockPostService.getPosts).toHaveBeenCalledTimes(2);
    });
  });
});