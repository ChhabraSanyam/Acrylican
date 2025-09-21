import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ProductForm } from '../ProductForm';
import { ProductFormData } from '../../../types/product';

describe('ProductForm', () => {
  const mockOnSubmit = jest.fn();
  const mockOnCancel = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders form fields correctly', () => {
    render(<ProductForm onSubmit={mockOnSubmit} />);

    expect(screen.getByLabelText(/product title/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/product description/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /create product/i })).toBeInTheDocument();
  });

  it('displays initial data when provided', () => {
    const initialData = {
      title: 'Test Product',
      description: 'Test Description'
    };

    render(<ProductForm onSubmit={mockOnSubmit} initialData={initialData} />);

    expect(screen.getByDisplayValue('Test Product')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Test Description')).toBeInTheDocument();
  });

  it('shows cancel button when onCancel is provided', () => {
    render(<ProductForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);

    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
  });

  it('validates required fields', async () => {
    const user = userEvent.setup();
    render(<ProductForm onSubmit={mockOnSubmit} />);

    const submitButton = screen.getByRole('button', { name: /create product/i });
    await user.click(submitButton);

    expect(screen.getByText(/title is required/i)).toBeInTheDocument();
    expect(screen.getByText(/description is required/i)).toBeInTheDocument();
    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('validates field lengths', async () => {
    const user = userEvent.setup();
    render(<ProductForm onSubmit={mockOnSubmit} />);

    const titleInput = screen.getByLabelText(/product title/i);
    const descriptionInput = screen.getByLabelText(/product description/i);

    // Test title too long
    await user.type(titleInput, 'x'.repeat(256));
    await user.click(screen.getByRole('button', { name: /create product/i }));

    expect(screen.getByText(/title must be less than 255 characters/i)).toBeInTheDocument();

    // Clear and test description too long
    await user.clear(titleInput);
    await user.type(titleInput, 'Valid Title');
    await user.type(descriptionInput, 'x'.repeat(5001));
    await user.click(screen.getByRole('button', { name: /create product/i }));

    expect(screen.getByText(/description must be less than 5000 characters/i)).toBeInTheDocument();
  });

  it('shows character counts', async () => {
    const user = userEvent.setup();
    render(<ProductForm onSubmit={mockOnSubmit} />);

    const titleInput = screen.getByLabelText(/product title/i);
    await user.type(titleInput, 'Test');

    expect(screen.getByText('4/255 characters')).toBeInTheDocument();
  });

  it('submits form with valid data', async () => {
    const user = userEvent.setup();
    const mockSubmit = jest.fn().mockResolvedValue(undefined);
    
    render(<ProductForm onSubmit={mockSubmit} />);

    const titleInput = screen.getByLabelText(/product title/i);
    const descriptionInput = screen.getByLabelText(/product description/i);

    await user.type(titleInput, 'Test Product');
    await user.type(descriptionInput, 'Test Description');
    await user.click(screen.getByRole('button', { name: /create product/i }));

    await waitFor(() => {
      expect(mockSubmit).toHaveBeenCalledWith({
        title: 'Test Product',
        description: 'Test Description'
      });
    });
  });

  it('handles submission errors', async () => {
    const user = userEvent.setup();
    const mockSubmit = jest.fn().mockRejectedValue(new Error('Submission failed'));
    
    render(<ProductForm onSubmit={mockSubmit} />);

    const titleInput = screen.getByLabelText(/product title/i);
    const descriptionInput = screen.getByLabelText(/product description/i);

    await user.type(titleInput, 'Test Product');
    await user.type(descriptionInput, 'Test Description');
    await user.click(screen.getByRole('button', { name: /create product/i }));

    await waitFor(() => {
      expect(screen.getByText(/submission failed/i)).toBeInTheDocument();
    });
  });

  it('disables form when loading', () => {
    render(<ProductForm onSubmit={mockOnSubmit} isLoading={true} />);

    expect(screen.getByLabelText(/product title/i)).toBeDisabled();
    expect(screen.getByLabelText(/product description/i)).toBeDisabled();
    expect(screen.getByRole('button', { name: /saving/i })).toBeDisabled();
  });

  it('calls onCancel when cancel button is clicked', async () => {
    const user = userEvent.setup();
    render(<ProductForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);

    await user.click(screen.getByRole('button', { name: /cancel/i }));

    expect(mockOnCancel).toHaveBeenCalled();
  });

  it('clears errors when user starts typing', async () => {
    const user = userEvent.setup();
    render(<ProductForm onSubmit={mockOnSubmit} />);

    // Trigger validation error
    await user.click(screen.getByRole('button', { name: /create product/i }));
    expect(screen.getByText(/title is required/i)).toBeInTheDocument();

    // Start typing to clear error
    const titleInput = screen.getByLabelText(/product title/i);
    await user.type(titleInput, 'T');

    expect(screen.queryByText(/title is required/i)).not.toBeInTheDocument();
  });

  it('uses custom submit label', () => {
    render(<ProductForm onSubmit={mockOnSubmit} submitLabel="Update Product" />);

    expect(screen.getByRole('button', { name: /update product/i })).toBeInTheDocument();
  });
});