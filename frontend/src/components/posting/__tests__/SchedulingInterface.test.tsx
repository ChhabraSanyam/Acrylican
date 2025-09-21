import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import SchedulingInterface from '../SchedulingInterface';
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
    target_platforms: ['facebook'],
    status: PostStatus.SCHEDULED,
    priority: 0,
    retry_count: 0,
    max_retries: 3,
    created_at: '2024-01-01T10:00:00Z',
    updated_at: '2024-01-01T10:00:00Z',
    scheduled_at: '2024-01-15T14:30:00Z'
  },
  {
    id: 'post-2',
    user_id: 'user-1',
    title: 'Test Post 2',
    description: 'Description 2',
    hashtags: ['#test2'],
    images: ['image2.jpg'],
    target_platforms: ['instagram'],
    status: PostStatus.SCHEDULED,
    priority: 0,
    retry_count: 0,
    max_retries: 3,
    created_at: '2024-01-02T10:00:00Z',
    updated_at: '2024-01-02T10:00:00Z',
    scheduled_at: '2024-01-15T16:00:00Z'
  },
  {
    id: 'post-3',
    user_id: 'user-1',
    title: 'Test Post 3',
    description: 'Description 3',
    hashtags: ['#test3'],
    images: ['image3.jpg'],
    target_platforms: ['facebook'],
    status: PostStatus.PUBLISHED,
    priority: 0,
    retry_count: 0,
    max_retries: 3,
    created_at: '2024-01-03T10:00:00Z',
    updated_at: '2024-01-03T10:00:00Z',
    published_at: '2024-01-10T12:00:00Z'
  }
];

describe('SchedulingInterface', () => {
  const defaultProps = {
    posts: mockPosts,
    onPostScheduled: jest.fn(),
    onRefresh: jest.fn()
  };

  beforeEach(() => {
    mockPostService.schedulePost.mockResolvedValue({
      success: true,
      post_id: 'post-1',
      results: [],
      queued_items: []
    });
    mockPostService.cancelScheduledPost.mockResolvedValue();
    
    // Mock current date to January 1, 2024
    jest.useFakeTimers();
    jest.setSystemTime(new Date('2024-01-01T00:00:00Z'));
  });

  afterEach(() => {
    jest.clearAllMocks();
    jest.useRealTimers();
  });

  it('renders scheduling interface', () => {
    render(<SchedulingInterface {...defaultProps} />);
    
    expect(screen.getByText('Post Schedule')).toBeInTheDocument();
    expect(screen.getByText('January 2024')).toBeInTheDocument();
  });

  it('displays calendar with current month', () => {
    render(<SchedulingInterface {...defaultProps} />);
    
    // Should show days of the week
    expect(screen.getByText('Sun')).toBeInTheDocument();
    expect(screen.getByText('Mon')).toBeInTheDocument();
    expect(screen.getByText('Tue')).toBeInTheDocument();
    expect(screen.getByText('Wed')).toBeInTheDocument();
    expect(screen.getByText('Thu')).toBeInTheDocument();
    expect(screen.getByText('Fri')).toBeInTheDocument();
    expect(screen.getByText('Sat')).toBeInTheDocument();
  });

  it('navigates between months', () => {
    render(<SchedulingInterface {...defaultProps} />);
    
    // Navigate to next month
    const nextButton = screen.getByRole('button', { name: /next/i });
    fireEvent.click(nextButton);
    
    expect(screen.getByText('February 2024')).toBeInTheDocument();
    
    // Navigate to previous month
    const prevButton = screen.getByRole('button', { name: /previous/i });
    fireEvent.click(prevButton);
    fireEvent.click(prevButton);
    
    expect(screen.getByText('December 2023')).toBeInTheDocument();
  });

  it('displays scheduled posts on calendar', () => {
    render(<SchedulingInterface {...defaultProps} />);
    
    // Posts scheduled for January 15, 2024
    // Should show posts on the 15th
    const dayElements = screen.getAllByText('15');
    expect(dayElements.length).toBeGreaterThan(0);
  });

  it('shows post times on calendar days', () => {
    render(<SchedulingInterface {...defaultProps} />);
    
    // Should show formatted times for scheduled posts
    expect(screen.getByText('2:30 PM')).toBeInTheDocument();
    expect(screen.getByText('4:00 PM')).toBeInTheDocument();
  });

  it('handles date selection', () => {
    render(<SchedulingInterface {...defaultProps} />);
    
    // Click on a date
    const dateElement = screen.getByText('15');
    fireEvent.click(dateElement);
    
    // Should show selected date details
    expect(screen.getByText(/January 15, 2024/)).toBeInTheDocument();
  });

  it('displays posts for selected date', () => {
    render(<SchedulingInterface {...defaultProps} />);
    
    // Click on January 15th (where posts are scheduled)
    const dateElement = screen.getByText('15');
    fireEvent.click(dateElement);
    
    // Should show scheduled posts for that date
    expect(screen.getByText('Test Post 1')).toBeInTheDocument();
    expect(screen.getByText('Test Post 2')).toBeInTheDocument();
  });

  it('shows post status badges', () => {
    render(<SchedulingInterface {...defaultProps} />);
    
    // Click on January 15th
    const dateElement = screen.getByText('15');
    fireEvent.click(dateElement);
    
    // Should show status badges
    expect(screen.getAllByText('scheduled')).toHaveLength(2);
  });

  it('handles post editing', () => {
    render(<SchedulingInterface {...defaultProps} />);
    
    // Click on January 15th
    const dateElement = screen.getByText('15');
    fireEvent.click(dateElement);
    
    // Click edit button for a post
    const editButtons = screen.getAllByText('Edit');
    fireEvent.click(editButtons[0]);
    
    // Should open reschedule modal
    expect(screen.getByText('Reschedule Post')).toBeInTheDocument();
  });

  it('handles post cancellation', async () => {
    render(<SchedulingInterface {...defaultProps} />);
    
    // Click on January 15th
    const dateElement = screen.getByText('15');
    fireEvent.click(dateElement);
    
    // Click cancel button for a scheduled post
    const cancelButtons = screen.getAllByText('Cancel');
    fireEvent.click(cancelButtons[0]);
    
    await waitFor(() => {
      expect(mockPostService.cancelScheduledPost).toHaveBeenCalledWith('post-1');
    });
  });

  it('handles post rescheduling', async () => {
    render(<SchedulingInterface {...defaultProps} />);
    
    // Click on January 15th and edit a post
    const dateElement = screen.getByText('15');
    fireEvent.click(dateElement);
    
    const editButtons = screen.getAllByText('Edit');
    fireEvent.click(editButtons[0]);
    
    // Change the schedule time
    const timeInput = screen.getByLabelText('New Schedule Time');
    fireEvent.change(timeInput, { target: { value: '2024-01-16T10:00' } });
    
    // Click reschedule
    fireEvent.click(screen.getByText('Reschedule'));
    
    await waitFor(() => {
      expect(mockPostService.schedulePost).toHaveBeenCalled();
    });
  });

  it('closes reschedule modal on cancel', () => {
    render(<SchedulingInterface {...defaultProps} />);
    
    // Open reschedule modal
    const dateElement = screen.getByText('15');
    fireEvent.click(dateElement);
    
    const editButtons = screen.getAllByText('Edit');
    fireEvent.click(editButtons[0]);
    
    // Cancel reschedule
    fireEvent.click(screen.getByText('Cancel'));
    
    // Modal should be closed
    expect(screen.queryByText('Reschedule Post')).not.toBeInTheDocument();
  });

  it('shows empty state for dates with no posts', () => {
    render(<SchedulingInterface {...defaultProps} />);
    
    // Click on a date with no posts (e.g., January 1st)
    const dateElement = screen.getByText('1');
    fireEvent.click(dateElement);
    
    expect(screen.getByText('No posts scheduled for this date')).toBeInTheDocument();
  });

  it('highlights today on calendar', () => {
    render(<SchedulingInterface {...defaultProps} />);
    
    // January 1, 2024 should be highlighted as today
    const todayElements = screen.getAllByText('1');
    const todayElement = todayElements.find(el => 
      el.closest('.ring-2.ring-blue-500')
    );
    expect(todayElement).toBeTruthy();
  });

  it('shows correct post counts on calendar days', () => {
    const postsWithMultipleOnSameDay = [
      ...mockPosts,
      {
        id: 'post-4',
        user_id: 'user-1',
        title: 'Test Post 4',
        description: 'Description 4',
        hashtags: ['#test4'],
        images: ['image4.jpg'],
        target_platforms: ['facebook'],
        status: PostStatus.SCHEDULED,
        priority: 0,
        retry_count: 0,
        max_retries: 3,
        created_at: '2024-01-04T10:00:00Z',
        updated_at: '2024-01-04T10:00:00Z',
        scheduled_at: '2024-01-15T18:00:00Z'
      }
    ];
    
    render(<SchedulingInterface posts={postsWithMultipleOnSameDay} />);
    
    // Should show "+1 more" for the day with 3 posts (only shows first 3)
    expect(screen.getByText('+1 more')).toBeInTheDocument();
  });

  it('calls onPostScheduled callback', async () => {
    const onPostScheduled = jest.fn();
    render(<SchedulingInterface {...defaultProps} onPostScheduled={onPostScheduled} />);
    
    // Trigger reschedule
    const dateElement = screen.getByText('15');
    fireEvent.click(dateElement);
    
    const editButtons = screen.getAllByText('Edit');
    fireEvent.click(editButtons[0]);
    
    fireEvent.click(screen.getByText('Reschedule'));
    
    await waitFor(() => {
      expect(onPostScheduled).toHaveBeenCalledWith(mockPosts[0]);
    });
  });

  it('calls onRefresh callback', async () => {
    const onRefresh = jest.fn();
    render(<SchedulingInterface {...defaultProps} onRefresh={onRefresh} />);
    
    // Trigger any action that should refresh
    const dateElement = screen.getByText('15');
    fireEvent.click(dateElement);
    
    const editButtons = screen.getAllByText('Edit');
    fireEvent.click(editButtons[0]);
    
    fireEvent.click(screen.getByText('Reschedule'));
    
    await waitFor(() => {
      expect(onRefresh).toHaveBeenCalled();
    });
  });

  it('handles scheduling errors', async () => {
    mockPostService.schedulePost.mockRejectedValue(new Error('Scheduling failed'));
    
    render(<SchedulingInterface {...defaultProps} />);
    
    // Trigger reschedule
    const dateElement = screen.getByText('15');
    fireEvent.click(dateElement);
    
    const editButtons = screen.getAllByText('Edit');
    fireEvent.click(editButtons[0]);
    
    fireEvent.click(screen.getByText('Reschedule'));
    
    await waitFor(() => {
      expect(screen.getByText('Scheduling failed')).toBeInTheDocument();
    });
  });

  it('shows loading state during scheduling', async () => {
    mockPostService.schedulePost.mockImplementation(() => 
      new Promise(resolve => setTimeout(resolve, 100))
    );
    
    render(<SchedulingInterface {...defaultProps} />);
    
    // Trigger reschedule
    const dateElement = screen.getByText('15');
    fireEvent.click(dateElement);
    
    const editButtons = screen.getAllByText('Edit');
    fireEvent.click(editButtons[0]);
    
    fireEvent.click(screen.getByText('Reschedule'));
    
    expect(screen.getByText('Scheduling...')).toBeInTheDocument();
  });
});