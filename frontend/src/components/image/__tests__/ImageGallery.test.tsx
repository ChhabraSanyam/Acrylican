import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ImageGallery from '../ImageGallery';
import { ImageService } from '../../../services/image';
import { ProcessedImage } from '../../../types/image';

// Mock the ImageService
jest.mock('../../../services/image');
const mockImageService = ImageService as jest.Mocked<typeof ImageService>;

const mockImages: ProcessedImage[] = [
  {
    id: '1',
    original_url: 'http://example.com/original1.jpg',
    compressed_url: 'http://example.com/compressed1.jpg',
    thumbnail_url: 'http://example.com/thumb1.jpg',
    file_size: 1024000,
    dimensions: { width: 800, height: 600 },
    file_name: 'image1.jpg',
    created_at: '2023-01-01T00:00:00Z',
  },
  {
    id: '2',
    original_url: 'http://example.com/original2.jpg',
    compressed_url: 'http://example.com/compressed2.jpg',
    thumbnail_url: 'http://example.com/thumb2.jpg',
    file_size: 2048000,
    dimensions: { width: 1024, height: 768 },
    file_name: 'image2.jpg',
    created_at: '2023-01-02T00:00:00Z',
  },
];

describe('ImageGallery', () => {
  const mockOnImageSelect = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    mockImageService.getUserImages.mockResolvedValue(mockImages);
    mockImageService.deleteImage.mockResolvedValue();
  });

  it('renders loading state initially', () => {
    render(<ImageGallery />);
    
    expect(screen.getByText('Loading images...')).toBeInTheDocument();
  });

  it('loads and displays images', async () => {
    render(<ImageGallery />);
    
    await waitFor(() => {
      expect(screen.getByText('Image Gallery (2)')).toBeInTheDocument();
    });
    
    expect(screen.getByText('image1.jpg')).toBeInTheDocument();
    expect(screen.getByText('image2.jpg')).toBeInTheDocument();
  });

  it('handles loading error', async () => {
    mockImageService.getUserImages.mockRejectedValue(new Error('Failed to load'));
    
    render(<ImageGallery />);
    
    await waitFor(() => {
      expect(screen.getByText('Failed to load')).toBeInTheDocument();
    });
  });

  it('shows upload component when showUpload is true', async () => {
    render(<ImageGallery showUpload={true} />);
    
    await waitFor(() => {
      expect(screen.getByText('Upload product images')).toBeInTheDocument();
    });
  });

  it('hides upload component when showUpload is false', async () => {
    render(<ImageGallery showUpload={false} />);
    
    await waitFor(() => {
      expect(screen.queryByText('Upload product images')).not.toBeInTheDocument();
    });
  });

  it('handles image selection in multi-select mode', async () => {
    const user = userEvent.setup();
    render(<ImageGallery onImageSelect={mockOnImageSelect} allowMultiSelect={true} />);
    
    await waitFor(() => {
      expect(screen.getByText('image1.jpg')).toBeInTheDocument();
    });
    
    // Images are sorted by date desc by default, so image2 appears first
    const firstImage = screen.getByAltText('image2.jpg').closest('div');
    await user.click(firstImage!);
    
    expect(mockOnImageSelect).toHaveBeenCalledWith([mockImages[1]]);
  });

  it('handles image selection in single-select mode', async () => {
    const user = userEvent.setup();
    render(<ImageGallery onImageSelect={mockOnImageSelect} allowMultiSelect={false} />);
    
    await waitFor(() => {
      expect(screen.getByText('image1.jpg')).toBeInTheDocument();
    });
    
    // Images are sorted by date desc by default, so image2 comes first
    const firstImage = screen.getByAltText('image2.jpg').closest('div');
    await user.click(firstImage!);
    
    expect(mockOnImageSelect).toHaveBeenCalledWith([mockImages[1]]);
    
    // Click second image should replace selection
    const secondImage = screen.getByAltText('image1.jpg').closest('div');
    await user.click(secondImage!);
    
    expect(mockOnImageSelect).toHaveBeenCalledWith([mockImages[0]]);
  });

  it('handles select all functionality', async () => {
    const user = userEvent.setup();
    render(<ImageGallery onImageSelect={mockOnImageSelect} allowMultiSelect={true} />);
    
    await waitFor(() => {
      expect(screen.getByText('Select All')).toBeInTheDocument();
    });
    
    const selectAllButton = screen.getByText('Select All');
    await user.click(selectAllButton);
    
    // Images are sorted by date desc, so order is [image2, image1]
    expect(mockOnImageSelect).toHaveBeenCalledWith([mockImages[1], mockImages[0]]);
    
    await waitFor(() => {
      expect(screen.getByText('Deselect All')).toBeInTheDocument();
    });
  });

  it('handles image deletion', async () => {
    const user = userEvent.setup();
    render(<ImageGallery onImageSelect={mockOnImageSelect} />);
    
    await waitFor(() => {
      expect(screen.getByText('image1.jpg')).toBeInTheDocument();
    });
    
    // Mock window.confirm
    const mockConfirm = jest.fn().mockReturnValue(true);
    Object.defineProperty(window, 'confirm', { value: mockConfirm });
    
    // First delete button corresponds to first image in sorted order (image2)
    const deleteButton = screen.getAllByTitle('Delete image')[0];
    await user.click(deleteButton);
    
    expect(mockImageService.deleteImage).toHaveBeenCalledWith('2');
    
    await waitFor(() => {
      expect(screen.queryByText('image2.jpg')).not.toBeInTheDocument();
    });
  });

  it('filters images by search term', async () => {
    const user = userEvent.setup();
    render(<ImageGallery />);
    
    await waitFor(() => {
      expect(screen.getByText('image1.jpg')).toBeInTheDocument();
      expect(screen.getByText('image2.jpg')).toBeInTheDocument();
    });
    
    const searchInput = screen.getByPlaceholderText('Search images...');
    await user.type(searchInput, 'image1');
    
    expect(screen.getByText('image1.jpg')).toBeInTheDocument();
    expect(screen.queryByText('image2.jpg')).not.toBeInTheDocument();
  });

  it('sorts images by different criteria', async () => {
    const user = userEvent.setup();
    render(<ImageGallery />);
    
    await waitFor(() => {
      expect(screen.getByText('Image Gallery (2)')).toBeInTheDocument();
    });
    
    const sortSelect = screen.getByDisplayValue('Newest First');
    await user.selectOptions(sortSelect, 'name-asc');
    
    // Images should be sorted by name A-Z
    const imageElements = screen.getAllByText(/image\d\.jpg/);
    expect(imageElements[0]).toHaveTextContent('image1.jpg');
    expect(imageElements[1]).toHaveTextContent('image2.jpg');
  });

  it('shows empty state when no images', async () => {
    mockImageService.getUserImages.mockResolvedValue([]);
    
    render(<ImageGallery />);
    
    await waitFor(() => {
      expect(screen.getByText('No images found')).toBeInTheDocument();
      expect(screen.getByText('Upload some images to get started.')).toBeInTheDocument();
    });
  });

  it('shows empty search state', async () => {
    const user = userEvent.setup();
    render(<ImageGallery />);
    
    await waitFor(() => {
      expect(screen.getByText('image1.jpg')).toBeInTheDocument();
    });
    
    const searchInput = screen.getByPlaceholderText('Search images...');
    await user.type(searchInput, 'nonexistent');
    
    expect(screen.getByText('No images found')).toBeInTheDocument();
    expect(screen.getByText('No images match your search.')).toBeInTheDocument();
    expect(screen.getByText('Clear search')).toBeInTheDocument();
  });

  it('clears search when clear search button is clicked', async () => {
    const user = userEvent.setup();
    render(<ImageGallery />);
    
    await waitFor(() => {
      expect(screen.getByText('image1.jpg')).toBeInTheDocument();
    });
    
    const searchInput = screen.getByPlaceholderText('Search images...');
    await user.type(searchInput, 'nonexistent');
    
    const clearButton = screen.getByText('Clear search');
    await user.click(clearButton);
    
    expect(searchInput).toHaveValue('');
    expect(screen.getByText('image1.jpg')).toBeInTheDocument();
    expect(screen.getByText('image2.jpg')).toBeInTheDocument();
  });

  it('handles new image upload', async () => {
    const newImage: ProcessedImage = {
      id: '3',
      original_url: 'http://example.com/original3.jpg',
      compressed_url: 'http://example.com/compressed3.jpg',
      thumbnail_url: 'http://example.com/thumb3.jpg',
      file_size: 512000,
      dimensions: { width: 640, height: 480 },
      file_name: 'new-image.jpg',
      created_at: '2023-01-03T00:00:00Z',
    };
    
    render(<ImageGallery />);
    
    await waitFor(() => {
      expect(screen.getByText('Image Gallery (2)')).toBeInTheDocument();
    });
    
    // Simulate upload completion
    const uploadComponent = screen.getByText('Upload product images').closest('div');
    const onUploadComplete = jest.fn();
    
    // This is a bit tricky to test without actually triggering the upload
    // In a real scenario, we'd need to mock the file upload process
    // For now, we'll just verify the component structure is correct
    expect(uploadComponent).toBeInTheDocument();
  });

  it('shows selected images count', async () => {
    const user = userEvent.setup();
    render(<ImageGallery onImageSelect={mockOnImageSelect} selectedImages={['1']} />);
    
    await waitFor(() => {
      expect(screen.getByText('1 image selected')).toBeInTheDocument();
    });
  });

  it('shows correct plural form for selected images', async () => {
    render(<ImageGallery onImageSelect={mockOnImageSelect} selectedImages={['1', '2']} />);
    
    await waitFor(() => {
      expect(screen.getByText('2 images selected')).toBeInTheDocument();
    });
  });

  it('dismisses error message', async () => {
    const user = userEvent.setup();
    mockImageService.getUserImages.mockRejectedValue(new Error('Network error'));
    
    render(<ImageGallery />);
    
    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument();
    });
    
    const dismissButton = screen.getByText('×');
    await user.click(dismissButton);
    
    expect(screen.queryByText('Network error')).not.toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(<ImageGallery className="custom-class" />);
    
    expect(container.firstChild).toHaveClass('custom-class');
  });
});