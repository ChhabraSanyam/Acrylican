import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ImagePreview from '../ImagePreview';
import { ProcessedImage } from '../../../types/image';

const mockImage: ProcessedImage = {
  id: '1',
  original_url: 'http://example.com/original.jpg',
  compressed_url: 'http://example.com/compressed.jpg',
  thumbnail_url: 'http://example.com/thumb.jpg',
  file_size: 1024000, // 1MB
  dimensions: { width: 800, height: 600 },
  file_name: 'test-image.jpg',
  created_at: '2023-01-01T00:00:00Z',
};

// Mock window.confirm
const mockConfirm = jest.fn();
Object.defineProperty(window, 'confirm', { value: mockConfirm });

describe('ImagePreview', () => {
  const mockOnDelete = jest.fn();
  const mockOnSelect = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    mockConfirm.mockReturnValue(true);
  });

  it('renders image with correct information', () => {
    render(<ImagePreview image={mockImage} />);
    
    expect(screen.getByAltText('test-image.jpg')).toBeInTheDocument();
    expect(screen.getByText('test-image.jpg')).toBeInTheDocument();
    expect(screen.getByText('800 × 600')).toBeInTheDocument();
    expect(screen.getByText('1000 KB')).toBeInTheDocument();
    expect(screen.getByText('Jan 1, 2023')).toBeInTheDocument();
  });

  it('shows selection indicator when selected', () => {
    render(<ImagePreview image={mockImage} isSelected={true} />);
    
    const checkIcon = screen.getByRole('img', { name: 'test-image.jpg' })
      .closest('div')
      ?.querySelector('svg');
    
    expect(checkIcon).toBeInTheDocument();
  });

  it('calls onSelect when clicked', async () => {
    const user = userEvent.setup();
    render(<ImagePreview image={mockImage} onSelect={mockOnSelect} />);
    
    const imageContainer = screen.getByAltText('test-image.jpg').closest('div');
    await user.click(imageContainer!);
    
    expect(mockOnSelect).toHaveBeenCalledWith('1');
  });

  it('shows action buttons on hover when showActions is true', () => {
    render(<ImagePreview image={mockImage} onDelete={mockOnDelete} showActions={true} />);
    
    const imageContainer = screen.getByAltText('test-image.jpg').closest('div');
    fireEvent.mouseEnter(imageContainer!);
    
    expect(screen.getByTitle('View full size')).toBeInTheDocument();
    expect(screen.getByTitle('Delete image')).toBeInTheDocument();
  });

  it('hides action buttons when showActions is false', () => {
    render(<ImagePreview image={mockImage} onDelete={mockOnDelete} showActions={false} />);
    
    expect(screen.queryByTitle('View full size')).not.toBeInTheDocument();
    expect(screen.queryByTitle('Delete image')).not.toBeInTheDocument();
  });

  it('opens full size modal when view button is clicked', async () => {
    const user = userEvent.setup();
    render(<ImagePreview image={mockImage} showActions={true} />);
    
    const viewButton = screen.getByTitle('View full size');
    await user.click(viewButton);
    
    // Check if modal is opened (full size image should be visible)
    const fullSizeImage = screen.getAllByAltText('test-image.jpg')[1]; // Second instance in modal
    expect(fullSizeImage).toBeInTheDocument();
    expect(fullSizeImage).toHaveAttribute('src', mockImage.compressed_url);
  });

  it('closes full size modal when close button is clicked', async () => {
    const user = userEvent.setup();
    render(<ImagePreview image={mockImage} showActions={true} />);
    
    // Open modal
    const viewButton = screen.getByTitle('View full size');
    await user.click(viewButton);
    
    // Close modal
    const closeButton = screen.getByRole('button');
    await user.click(closeButton);
    
    // Modal should be closed (only one image instance should remain)
    const images = screen.getAllByAltText('test-image.jpg');
    expect(images).toHaveLength(1);
  });

  it('closes full size modal when backdrop is clicked', async () => {
    const user = userEvent.setup();
    render(<ImagePreview image={mockImage} showActions={true} />);
    
    // Open modal
    const viewButton = screen.getByTitle('View full size');
    await user.click(viewButton);
    
    // Click backdrop (modal container)
    const modal = screen.getByRole('img', { name: 'test-image.jpg' }).closest('.fixed');
    await user.click(modal!);
    
    // Modal should be closed
    await waitFor(() => {
      const images = screen.getAllByAltText('test-image.jpg');
      expect(images).toHaveLength(1);
    });
  });

  it('calls onDelete with confirmation when delete button is clicked', async () => {
    const user = userEvent.setup();
    render(<ImagePreview image={mockImage} onDelete={mockOnDelete} showActions={true} />);
    
    const deleteButton = screen.getByTitle('Delete image');
    await user.click(deleteButton);
    
    expect(mockConfirm).toHaveBeenCalledWith('Are you sure you want to delete this image?');
    expect(mockOnDelete).toHaveBeenCalledWith('1');
  });

  it('does not call onDelete when confirmation is cancelled', async () => {
    mockConfirm.mockReturnValue(false);
    const user = userEvent.setup();
    render(<ImagePreview image={mockImage} onDelete={mockOnDelete} showActions={true} />);
    
    const deleteButton = screen.getByTitle('Delete image');
    await user.click(deleteButton);
    
    expect(mockConfirm).toHaveBeenCalled();
    expect(mockOnDelete).not.toHaveBeenCalled();
  });

  it('shows loading state during delete operation', async () => {
    const user = userEvent.setup();
    const slowDelete = jest.fn(() => new Promise(resolve => setTimeout(resolve, 100)));
    
    render(<ImagePreview image={mockImage} onDelete={slowDelete} showActions={true} />);
    
    const deleteButton = screen.getByTitle('Delete image');
    await user.click(deleteButton);
    
    // Should show loading spinner
    expect(screen.getByRole('img', { name: 'test-image.jpg' }).closest('div')?.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('formats file sizes correctly', () => {
    const largeImage = { ...mockImage, file_size: 5 * 1024 * 1024 }; // 5MB
    render(<ImagePreview image={largeImage} />);
    
    expect(screen.getByText('5 MB')).toBeInTheDocument();
  });

  it('formats dates correctly', () => {
    const imageWithDate = { ...mockImage, created_at: '2023-12-25T10:30:00Z' };
    render(<ImagePreview image={imageWithDate} />);
    
    expect(screen.getByText('Dec 25, 2023')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(<ImagePreview image={mockImage} className="custom-class" />);
    
    expect(container.firstChild).toHaveClass('custom-class');
  });

  it('shows selected state styling', () => {
    const { container } = render(<ImagePreview image={mockImage} isSelected={true} />);
    
    expect(container.firstChild).toHaveClass('border-primary-500', 'ring-2', 'ring-primary-200');
  });

  it('prevents event propagation when action buttons are clicked', async () => {
    const user = userEvent.setup();
    render(<ImagePreview image={mockImage} onSelect={mockOnSelect} onDelete={mockOnDelete} showActions={true} />);
    
    const deleteButton = screen.getByTitle('Delete image');
    await user.click(deleteButton);
    
    // onSelect should not be called when delete button is clicked
    expect(mockOnSelect).not.toHaveBeenCalled();
  });
});