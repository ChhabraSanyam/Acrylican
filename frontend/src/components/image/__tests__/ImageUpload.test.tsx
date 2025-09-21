import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ImageUpload from '../ImageUpload';
import { ImageService } from '../../../services/image';

// Mock the ImageService
jest.mock('../../../services/image');
const mockImageService = ImageService as jest.Mocked<typeof ImageService>;

// Mock file for testing
const createMockFile = (name: string, size: number, type: string): File => {
  const file = new File([''], name, { type });
  Object.defineProperty(file, 'size', { value: size });
  return file;
};

describe('ImageUpload', () => {
  const mockOnUploadComplete = jest.fn();
  const mockOnUploadError = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    mockImageService.validateImageFile.mockResolvedValue(null);
    mockImageService.uploadImages.mockResolvedValue({
      success: true,
      images: [
        {
          id: '1',
          original_url: 'http://example.com/original.jpg',
          compressed_url: 'http://example.com/compressed.jpg',
          thumbnail_url: 'http://example.com/thumb.jpg',
          file_size: 1024,
          dimensions: { width: 800, height: 600 },
          file_name: 'test.jpg',
          created_at: '2023-01-01T00:00:00Z',
        },
      ],
    });
  });

  it('renders upload area with correct text', () => {
    render(<ImageUpload />);
    
    expect(screen.getByText('Upload product images')).toBeInTheDocument();
    expect(screen.getByText('Drag and drop images here, or click to select files')).toBeInTheDocument();
  });

  it('shows drag over state when files are dragged over', () => {
    render(<ImageUpload />);
    
    const uploadArea = screen.getByText('Upload product images').closest('div');
    
    fireEvent.dragOver(uploadArea!);
    expect(screen.getByText('Drop images here')).toBeInTheDocument();
    
    fireEvent.dragLeave(uploadArea!);
    expect(screen.getByText('Upload product images')).toBeInTheDocument();
  });

  it('handles file selection through input', async () => {
    const user = userEvent.setup();
    render(<ImageUpload onUploadComplete={mockOnUploadComplete} />);
    
    const file = createMockFile('test.jpg', 1024, 'image/jpeg');
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    
    await user.upload(input, file);
    
    await waitFor(() => {
      expect(mockImageService.validateImageFile).toHaveBeenCalledWith(file, expect.any(Object));
    });
  });

  it('handles drag and drop file upload', async () => {
    render(<ImageUpload onUploadComplete={mockOnUploadComplete} />);
    
    const file = createMockFile('test.jpg', 1024, 'image/jpeg');
    const uploadArea = screen.getByText('Upload product images').closest('div');
    
    const dropEvent = new Event('drop', { bubbles: true });
    Object.defineProperty(dropEvent, 'dataTransfer', {
      value: { files: [file] },
    });
    
    fireEvent(uploadArea!, dropEvent);
    
    await waitFor(() => {
      expect(mockImageService.validateImageFile).toHaveBeenCalledWith(file, expect.any(Object));
    });
  });

  it('validates file size and shows error for oversized files', async () => {
    const oversizedFile = createMockFile('large.jpg', 20 * 1024 * 1024, 'image/jpeg'); // 20MB
    mockImageService.validateImageFile.mockResolvedValue('File size must be less than 10MB');
    
    render(<ImageUpload />);
    
    const uploadArea = screen.getByText('Upload product images').closest('div');
    const dropEvent = new Event('drop', { bubbles: true });
    Object.defineProperty(dropEvent, 'dataTransfer', {
      value: { files: [oversizedFile] },
    });
    
    fireEvent(uploadArea!, dropEvent);
    
    await waitFor(() => {
      expect(screen.getByText('Upload Errors')).toBeInTheDocument();
      expect(screen.getByText(/File size must be less than 10MB/)).toBeInTheDocument();
    });
  });

  it('validates file type and shows error for unsupported formats', async () => {
    const unsupportedFile = createMockFile('document.pdf', 1024, 'application/pdf');
    mockImageService.validateImageFile.mockResolvedValue('File type must be one of: image/jpeg, image/png, image/webp');
    
    render(<ImageUpload />);
    
    const uploadArea = screen.getByText('Upload product images').closest('div');
    const dropEvent = new Event('drop', { bubbles: true });
    Object.defineProperty(dropEvent, 'dataTransfer', {
      value: { files: [unsupportedFile] },
    });
    
    fireEvent(uploadArea!, dropEvent);
    
    await waitFor(() => {
      expect(screen.getByText('Upload Errors')).toBeInTheDocument();
      expect(screen.getByText(/File type must be one of/)).toBeInTheDocument();
    });
  });

  it('shows upload progress during file upload', async () => {
    const file = createMockFile('test.jpg', 1024, 'image/jpeg');
    
    render(<ImageUpload onUploadComplete={mockOnUploadComplete} />);
    
    const uploadArea = screen.getByText('Upload product images').closest('div');
    const dropEvent = new Event('drop', { bubbles: true });
    Object.defineProperty(dropEvent, 'dataTransfer', {
      value: { files: [file] },
    });
    
    fireEvent(uploadArea!, dropEvent);
    
    await waitFor(() => {
      expect(screen.getByText('Upload Progress')).toBeInTheDocument();
      expect(screen.getAllByText('test.jpg')).toHaveLength(2); // One in progress, one in preview
    });
  });

  it('calls onUploadComplete when upload succeeds', async () => {
    const file = createMockFile('test.jpg', 1024, 'image/jpeg');
    
    render(<ImageUpload onUploadComplete={mockOnUploadComplete} />);
    
    const uploadArea = screen.getByText('Upload product images').closest('div');
    const dropEvent = new Event('drop', { bubbles: true });
    Object.defineProperty(dropEvent, 'dataTransfer', {
      value: { files: [file] },
    });
    
    fireEvent(uploadArea!, dropEvent);
    
    await waitFor(() => {
      expect(mockOnUploadComplete).toHaveBeenCalledWith([
        expect.objectContaining({
          id: '1',
          file_name: 'test.jpg',
        }),
      ]);
    });
  });

  it('calls onUploadError when upload fails', async () => {
    const file = createMockFile('test.jpg', 1024, 'image/jpeg');
    mockImageService.uploadImages.mockRejectedValue(new Error('Upload failed'));
    
    render(<ImageUpload onUploadError={mockOnUploadError} />);
    
    const uploadArea = screen.getByText('Upload product images').closest('div');
    const dropEvent = new Event('drop', { bubbles: true });
    Object.defineProperty(dropEvent, 'dataTransfer', {
      value: { files: [file] },
    });
    
    fireEvent(uploadArea!, dropEvent);
    
    await waitFor(() => {
      expect(mockOnUploadError).toHaveBeenCalledWith('Upload failed');
    });
  });

  it('allows clearing validation errors', async () => {
    const invalidFile = createMockFile('large.jpg', 20 * 1024 * 1024, 'image/jpeg');
    mockImageService.validateImageFile.mockResolvedValue('File size must be less than 10MB');
    
    render(<ImageUpload />);
    
    const uploadArea = screen.getByText('Upload product images').closest('div');
    const dropEvent = new Event('drop', { bubbles: true });
    Object.defineProperty(dropEvent, 'dataTransfer', {
      value: { files: [invalidFile] },
    });
    
    fireEvent(uploadArea!, dropEvent);
    
    await waitFor(() => {
      expect(screen.getByText('Upload Errors')).toBeInTheDocument();
    });
    
    const clearButton = screen.getByRole('button', { name: '' }); // X button
    fireEvent.click(clearButton);
    
    expect(screen.queryByText('Upload Errors')).not.toBeInTheDocument();
  });

  it('respects single file mode when multiple=false', () => {
    render(<ImageUpload multiple={false} />);
    
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    
    expect(input.multiple).toBe(false);
  });

  it('applies custom className', () => {
    const { container } = render(<ImageUpload className="custom-class" />);
    
    expect(container.firstChild).toHaveClass('custom-class');
  });
});