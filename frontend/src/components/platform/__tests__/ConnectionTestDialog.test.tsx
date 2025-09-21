import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import ConnectionTestDialog from '../ConnectionTestDialog';
import { ConnectionTestResult } from '../../../types/platform';

const mockSuccessResults: ConnectionTestResult[] = [
  {
    platform: 'facebook',
    success: true,
    message: 'Connection is working properly',
    details: {
      last_validated: '2023-01-01T12:00:00Z',
      platform_username: 'test_user'
    }
  },
  {
    platform: 'instagram',
    success: true,
    message: 'Connection is working properly',
    details: {
      last_validated: '2023-01-01T11:30:00Z',
      platform_username: 'test_instagram'
    }
  }
];

const mockMixedResults: ConnectionTestResult[] = [
  {
    platform: 'facebook',
    success: true,
    message: 'Connection is working properly',
    details: {
      last_validated: '2023-01-01T12:00:00Z',
      platform_username: 'test_user'
    }
  },
  {
    platform: 'etsy',
    success: false,
    message: 'Token expired',
    details: {
      last_validated: '2023-01-01T10:00:00Z'
    }
  },
  {
    platform: 'pinterest',
    success: false,
    message: 'Connection validation failed'
  }
];

describe('ConnectionTestDialog', () => {
  const mockOnClose = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders dialog with test results', () => {
    render(
      <ConnectionTestDialog
        results={mockSuccessResults}
        onClose={mockOnClose}
      />
    );

    expect(screen.getByText('Connection Test Results')).toBeInTheDocument();
    expect(screen.getByText('2 successful, 0 failed out of 2 connections')).toBeInTheDocument();
  });

  it('displays success and failure counts correctly', () => {
    render(
      <ConnectionTestDialog
        results={mockMixedResults}
        onClose={mockOnClose}
      />
    );

    expect(screen.getByText('1 successful, 2 failed out of 3 connections')).toBeInTheDocument();
  });

  it('shows success summary card', () => {
    render(
      <ConnectionTestDialog
        results={mockMixedResults}
        onClose={mockOnClose}
      />
    );

    expect(screen.getByText('Successful')).toBeInTheDocument();
    // Use more specific selector for success count
    const successCard = screen.getByText('Successful').closest('div');
    expect(successCard).toHaveTextContent('1');
  });

  it('shows failure summary card', () => {
    render(
      <ConnectionTestDialog
        results={mockMixedResults}
        onClose={mockOnClose}
      />
    );

    expect(screen.getByText('Failed')).toBeInTheDocument();
    // Use more specific selector for failure count
    const failureCard = screen.getByText('Failed').closest('div');
    expect(failureCard).toHaveTextContent('2');
  });

  it('renders individual platform results', () => {
    render(
      <ConnectionTestDialog
        results={mockMixedResults}
        onClose={mockOnClose}
      />
    );

    expect(screen.getByText('Facebook')).toBeInTheDocument();
    expect(screen.getByText('Etsy')).toBeInTheDocument();
    expect(screen.getByText('Pinterest')).toBeInTheDocument();
  });

  it('shows success messages for successful connections', () => {
    render(
      <ConnectionTestDialog
        results={mockSuccessResults}
        onClose={mockOnClose}
      />
    );

    const successMessages = screen.getAllByText('Connection is working properly');
    expect(successMessages).toHaveLength(2);
  });

  it('shows error messages for failed connections', () => {
    render(
      <ConnectionTestDialog
        results={mockMixedResults}
        onClose={mockOnClose}
      />
    );

    expect(screen.getByText('Token expired')).toBeInTheDocument();
    expect(screen.getByText('Connection validation failed')).toBeInTheDocument();
  });

  it('displays platform icons', () => {
    render(
      <ConnectionTestDialog
        results={mockSuccessResults}
        onClose={mockOnClose}
      />
    );

    expect(screen.getByText('📘')).toBeInTheDocument(); // Facebook icon
    expect(screen.getByText('📷')).toBeInTheDocument(); // Instagram icon
  });

  it('shows success and failure icons', () => {
    render(
      <ConnectionTestDialog
        results={mockMixedResults}
        onClose={mockOnClose}
      />
    );

    // Check for success and failure icons in the DOM
    const successIcons = document.querySelectorAll('svg path[d*="M5 13l4 4L19 7"]');
    const failureIcons = document.querySelectorAll('svg path[d*="M6 18L18 6M6 6l12 12"]');
    
    expect(successIcons.length).toBeGreaterThan(0);
    expect(failureIcons.length).toBeGreaterThan(0);
  });

  it('displays connection details when available', () => {
    render(
      <ConnectionTestDialog
        results={mockSuccessResults}
        onClose={mockOnClose}
      />
    );

    expect(screen.getByText('test_user')).toBeInTheDocument();
    expect(screen.getByText('test_instagram')).toBeInTheDocument();
  });

  it('formats last validated dates correctly', () => {
    render(
      <ConnectionTestDialog
        results={mockSuccessResults}
        onClose={mockOnClose}
      />
    );

    // Check that dates are formatted (exact format may vary by locale)
    const dateElements = screen.getAllByText(/1\/1\/2023|2023-01-01|Jan.*2023/);
    expect(dateElements.length).toBeGreaterThan(0);
  });

  it('handles results without details gracefully', () => {
    const resultsWithoutDetails: ConnectionTestResult[] = [
      {
        platform: 'shopify',
        success: true,
        message: 'Connection successful'
      }
    ];

    render(
      <ConnectionTestDialog
        results={resultsWithoutDetails}
        onClose={mockOnClose}
      />
    );

    expect(screen.getByText('Shopify')).toBeInTheDocument();
    expect(screen.getByText('Connection successful')).toBeInTheDocument();
  });

  it('calls onClose when close button is clicked', () => {
    render(
      <ConnectionTestDialog
        results={mockSuccessResults}
        onClose={mockOnClose}
      />
    );

    const closeButton = screen.getByRole('button', { name: /close/i });
    fireEvent.click(closeButton);
    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it('calls onClose when X button is clicked', () => {
    render(
      <ConnectionTestDialog
        results={mockSuccessResults}
        onClose={mockOnClose}
      />
    );

    // Find the X button (close icon)
    const xButton = document.querySelector('svg path[d*="M6 18L18 6M6 6l12 12"]')?.closest('button');
    expect(xButton).toBeInTheDocument();
    
    if (xButton) {
      fireEvent.click(xButton);
      expect(mockOnClose).toHaveBeenCalledTimes(1);
    }
  });

  it('handles empty results array', () => {
    render(
      <ConnectionTestDialog
        results={[]}
        onClose={mockOnClose}
      />
    );

    expect(screen.getByText('0 successful, 0 failed out of 0 connections')).toBeInTheDocument();
    // Check for success count in the success card specifically
    const successCard = screen.getByText('Successful').closest('div');
    expect(successCard).toHaveTextContent('0');
  });

  it('applies correct styling for success and failure states', () => {
    render(
      <ConnectionTestDialog
        results={mockMixedResults}
        onClose={mockOnClose}
      />
    );

    // Check for success styling (green background) - find the parent container
    const facebookResult = screen.getByText('Facebook');
    const successResultContainer = facebookResult.closest('.border-green-200');
    expect(successResultContainer).toBeInTheDocument();
    expect(successResultContainer).toHaveClass('bg-green-50');

    // Check for failure styling (red background) - find the parent container
    const etsyResult = screen.getByText('Etsy');
    const failureResultContainer = etsyResult.closest('.border-red-200');
    expect(failureResultContainer).toBeInTheDocument();
    expect(failureResultContainer).toHaveClass('bg-red-50');
  });

  it('shows scrollable results when many platforms', () => {
    const manyResults: ConnectionTestResult[] = Array.from({ length: 10 }, (_, i) => ({
      platform: `platform${i}`,
      success: i % 2 === 0,
      message: `Test message ${i}`
    }));

    render(
      <ConnectionTestDialog
        results={manyResults}
        onClose={mockOnClose}
      />
    );

    // Check that the results container has scroll styling
    const resultsContainer = document.querySelector('.max-h-96.overflow-y-auto');
    expect(resultsContainer).toBeInTheDocument();
  });
});