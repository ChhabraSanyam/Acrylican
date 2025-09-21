import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ProductCard } from '../ProductCard';
import { Product } from '../../../types/product';

const mockProduct: Product = {
  id: '1',
  user_id: 'user1',
  title: 'Test Product',
  description: 'This is a test product with a longer description that should be truncated when displayed in the card view.',
  images: [
    {
      id: 'img1',
      original_filename: 'test.jpg',
      original_url: 'https://example.com/original.jpg',
      compressed_url: 'https://example.com/compressed.jpg',
      thumbnail_urls: {
        small: 'https://example.com/thumb_small.jpg',
        medium: 'https://example.com/thumb_medium.jpg'
      },
      platform_optimized_urls: {},
      storage_paths: { original: 'path/to/original.jpg' },
      file_size: 1024,
      dimensions: { width: 800, height: 600 },
      format: 'JPEG',
      created_at: '2023-01-01T00:00:00Z'
    }
  ],
  generated_content: null,
  created_at: '2023-01-01T00:00:00Z',
  updated_at: '2023-01-02T00:00:00Z'
};

const mockProductNoImages: Product = {
  ...mockProduct,
  images: []
};

describe('ProductCard', () => {
  const mockOnSelect = jest.fn();
  const mockOnEdit = jest.fn();
  const mockOnDelete = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders product information correctly', () => {
    render(<ProductCard product={mockProduct} />);

    expect(screen.getByText('Test Product')).toBeInTheDocument();
    expect(screen.getByText(/This is a test product with a longer description/)).toBeInTheDocument();
    expect(screen.getByText('Created: Jan 1, 2023')).toBeInTheDocument();
    expect(screen.getByText('Updated: Jan 2, 2023')).toBeInTheDocument();
  });

  it('displays image count badge when images exist', () => {
    render(<ProductCard product={mockProduct} />);

    expect(screen.getByText('1 image')).toBeInTheDocument();
  });

  it('displays plural image count correctly', () => {
    const productWithMultipleImages = {
      ...mockProduct,
      images: [mockProduct.images[0], { ...mockProduct.images[0], id: 'img2' }]
    };

    render(<ProductCard product={productWithMultipleImages} />);

    expect(screen.getByText('2 images')).toBeInTheDocument();
  });

  it('shows placeholder when no images exist', () => {
    render(<ProductCard product={mockProductNoImages} />);

    expect(screen.queryByText(/image/)).not.toBeInTheDocument();
    // Should show placeholder SVG
    expect(screen.getByRole('img')).toHaveAttribute('alt', 'Test Product');
  });

  it('truncates long descriptions', () => {
    render(<ProductCard product={mockProduct} />);

    const description = screen.getByText(/This is a test product with a longer description/);
    expect(description.textContent).toMatch(/\.\.\.$/); // Should end with ellipsis
  });

  it('displays product image when available', () => {
    render(<ProductCard product={mockProduct} />);

    const image = screen.getByRole('img');
    expect(image).toHaveAttribute('src', 'https://example.com/compressed.jpg');
    expect(image).toHaveAttribute('alt', 'Test Product');
  });

  it('renders action buttons when callbacks provided', () => {
    render(
      <ProductCard
        product={mockProduct}
        onSelect={mockOnSelect}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
      />
    );

    expect(screen.getByRole('button', { name: /view/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /edit/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /delete/i })).toBeInTheDocument();
  });

  it('does not render action buttons when callbacks not provided', () => {
    render(<ProductCard product={mockProduct} />);

    expect(screen.queryByRole('button', { name: /view/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /edit/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /delete/i })).not.toBeInTheDocument();
  });

  it('calls onSelect when view button is clicked', async () => {
    const user = userEvent.setup();
    render(<ProductCard product={mockProduct} onSelect={mockOnSelect} />);

    await user.click(screen.getByRole('button', { name: /view/i }));

    expect(mockOnSelect).toHaveBeenCalledTimes(1);
  });

  it('calls onEdit when edit button is clicked', async () => {
    const user = userEvent.setup();
    render(<ProductCard product={mockProduct} onEdit={mockOnEdit} />);

    await user.click(screen.getByRole('button', { name: /edit/i }));

    expect(mockOnEdit).toHaveBeenCalledTimes(1);
  });

  it('calls onDelete when delete button is clicked', async () => {
    const user = userEvent.setup();
    render(<ProductCard product={mockProduct} onDelete={mockOnDelete} />);

    await user.click(screen.getByRole('button', { name: /delete/i }));

    expect(mockOnDelete).toHaveBeenCalledTimes(1);
  });

  it('formats dates correctly', () => {
    const productWithDifferentDates = {
      ...mockProduct,
      created_at: '2023-12-25T15:30:00Z',
      updated_at: '2023-12-26T10:15:00Z'
    };

    render(<ProductCard product={productWithDifferentDates} />);

    expect(screen.getByText('Created: Dec 25, 2023')).toBeInTheDocument();
    expect(screen.getByText('Updated: Dec 26, 2023')).toBeInTheDocument();
  });

  it('does not show updated date when same as created date', () => {
    const productSameDates = {
      ...mockProduct,
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-01-01T00:00:00Z'
    };

    render(<ProductCard product={productSameDates} />);

    expect(screen.getByText('Created: Jan 1, 2023')).toBeInTheDocument();
    expect(screen.queryByText(/Updated:/)).not.toBeInTheDocument();
  });

  it('applies hover effects correctly', () => {
    render(<ProductCard product={mockProduct} />);

    const card = screen.getByText('Test Product').closest('div');
    expect(card).toHaveClass('hover:shadow-lg');
  });
});