import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import UploadProgress from '../UploadProgress';
import { ImageUploadProgress } from '../../../types/image';

const mockFile = new File([''], 'test-image.jpg', { type: 'image/jpeg' });
Object.defineProperty(mockFile, 'size', { value: 1024000 }); // 1MB

describe('UploadProgress', () => {
  const mockOnRetry = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders pending status correctly', () => {
    const progress: ImageUploadProgress = {
      file: mockFile,
      progress: 0,
      status: 'pending',
    };

    render(<UploadProgress progress={progress} />);
    
    expect(screen.getByText('test-image.jpg')).toBeInTheDocument();
    expect(screen.getByText('1000 KB')).toBeInTheDocument();
    expect(screen.getByText('Waiting...')).toBeInTheDocument();
    
    // Should show spinning icon
    expect(document.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('renders uploading status with progress', () => {
    const progress: ImageUploadProgress = {
      file: mockFile,
      progress: 45,
      status: 'uploading',
    };

    render(<UploadProgress progress={progress} />);
    
    expect(screen.getByText('Uploading... 45%')).toBeInTheDocument();
    
    // Should show progress bar
    const progressBar = document.querySelector('.bg-primary-500');
    expect(progressBar).toBeInTheDocument();
    expect(progressBar).toHaveStyle({ width: '45%' });
  });

  it('renders processing status', () => {
    const progress: ImageUploadProgress = {
      file: mockFile,
      progress: 100,
      status: 'processing',
    };

    render(<UploadProgress progress={progress} />);
    
    expect(screen.getByText('Processing...')).toBeInTheDocument();
    
    // Should show spinning icon
    expect(document.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('renders completed status', () => {
    const progress: ImageUploadProgress = {
      file: mockFile,
      progress: 100,
      status: 'completed',
    };

    render(<UploadProgress progress={progress} />);
    
    expect(screen.getByText('Completed')).toBeInTheDocument();
    
    // Should show checkmark icon
    const checkIcon = document.querySelector('svg path[d*="M5 13l4 4L19 7"]');
    expect(checkIcon).toBeInTheDocument();
  });

  it('renders error status with retry button', () => {
    const progress: ImageUploadProgress = {
      file: mockFile,
      progress: 0,
      status: 'error',
      error: 'Upload failed due to network error',
    };

    render(<UploadProgress progress={progress} onRetry={mockOnRetry} />);
    
    expect(screen.getByText('Upload failed due to network error')).toBeInTheDocument();
    expect(screen.getByText('Retry')).toBeInTheDocument();
    
    // Should show error icon
    const errorIcon = document.querySelector('svg path[d*="M6 18L18 6M6 6l12 12"]');
    expect(errorIcon).toBeInTheDocument();
  });

  it('renders error status without custom error message', () => {
    const progress: ImageUploadProgress = {
      file: mockFile,
      progress: 0,
      status: 'error',
    };

    render(<UploadProgress progress={progress} />);
    
    expect(screen.getByText('Upload failed')).toBeInTheDocument();
  });

  it('calls onRetry when retry button is clicked', async () => {
    const user = userEvent.setup();
    const progress: ImageUploadProgress = {
      file: mockFile,
      progress: 0,
      status: 'error',
      error: 'Network error',
    };

    render(<UploadProgress progress={progress} onRetry={mockOnRetry} />);
    
    const retryButton = screen.getByText('Retry');
    await user.click(retryButton);
    
    expect(mockOnRetry).toHaveBeenCalledTimes(1);
  });

  it('does not show retry button when onRetry is not provided', () => {
    const progress: ImageUploadProgress = {
      file: mockFile,
      progress: 0,
      status: 'error',
      error: 'Network error',
    };

    render(<UploadProgress progress={progress} />);
    
    expect(screen.queryByText('Retry')).not.toBeInTheDocument();
  });

  it('formats file sizes correctly', () => {
    const largeFile = new File([''], 'large-image.jpg', { type: 'image/jpeg' });
    Object.defineProperty(largeFile, 'size', { value: 5 * 1024 * 1024 }); // 5MB
    
    const progress: ImageUploadProgress = {
      file: largeFile,
      progress: 0,
      status: 'pending',
    };

    render(<UploadProgress progress={progress} />);
    
    expect(screen.getByText('5 MB')).toBeInTheDocument();
  });

  it('handles zero byte files', () => {
    const emptyFile = new File([''], 'empty.jpg', { type: 'image/jpeg' });
    Object.defineProperty(emptyFile, 'size', { value: 0 });
    
    const progress: ImageUploadProgress = {
      file: emptyFile,
      progress: 0,
      status: 'pending',
    };

    render(<UploadProgress progress={progress} />);
    
    expect(screen.getByText('0 Bytes')).toBeInTheDocument();
  });

  it('truncates long file names', () => {
    const longNameFile = new File([''], 'very-long-file-name-that-should-be-truncated-in-the-ui.jpg', { type: 'image/jpeg' });
    Object.defineProperty(longNameFile, 'size', { value: 1024 });
    
    const progress: ImageUploadProgress = {
      file: longNameFile,
      progress: 0,
      status: 'pending',
    };

    render(<UploadProgress progress={progress} />);
    
    const fileName = screen.getByText('very-long-file-name-that-should-be-truncated-in-the-ui.jpg');
    expect(fileName).toHaveClass('truncate');
  });

  it('shows correct progress bar colors for different statuses', () => {
    const uploadingProgress: ImageUploadProgress = {
      file: mockFile,
      progress: 50,
      status: 'uploading',
    };

    const { rerender } = render(<UploadProgress progress={uploadingProgress} />);
    
    let progressBar = document.querySelector('.h-1\\.5');
    expect(progressBar?.firstChild).toHaveClass('bg-primary-500');

    const completedProgress: ImageUploadProgress = {
      file: mockFile,
      progress: 100,
      status: 'completed',
    };

    rerender(<UploadProgress progress={completedProgress} />);
    
    // For completed status, there should be no progress bar, just the checkmark
    progressBar = document.querySelector('.h-1\\.5');
    expect(progressBar).not.toBeInTheDocument();
  });
});