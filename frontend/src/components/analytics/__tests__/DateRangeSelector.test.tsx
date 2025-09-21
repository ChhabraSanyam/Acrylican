import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import DateRangeSelector from '../DateRangeSelector';

// Mock date-fns functions
jest.mock('date-fns', () => ({
  format: jest.fn((date, formatStr) => {
    if (formatStr === 'yyyy-MM-dd') {
      return '2024-01-01';
    }
    return 'Jan 1, 2024';
  }),
  subDays: jest.fn((date, days) => new Date('2024-01-01')),
  startOfWeek: jest.fn(() => new Date('2024-01-01')),
  startOfMonth: jest.fn(() => new Date('2024-01-01')),
  startOfYear: jest.fn(() => new Date('2024-01-01')),
}));

describe('DateRangeSelector', () => {
  const mockOnChange = jest.fn();
  const startDate = new Date('2024-01-01');
  const endDate = new Date('2024-01-31');

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders date range selector with default preset', () => {
    render(
      <DateRangeSelector
        startDate={startDate}
        endDate={endDate}
        onChange={mockOnChange}
      />
    );

    expect(screen.getByText('Date Range:')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Last 30 days')).toBeInTheDocument();
    expect(screen.getByText('Jan 1, 2024 - Jan 1, 2024')).toBeInTheDocument();
  });

  it('renders all preset options', () => {
    render(
      <DateRangeSelector
        startDate={startDate}
        endDate={endDate}
        onChange={mockOnChange}
      />
    );

    const select = screen.getByDisplayValue('Last 30 days');
    
    // Check that all options are present
    expect(screen.getByText('Last 7 days')).toBeInTheDocument();
    expect(screen.getByText('Last 30 days')).toBeInTheDocument();
    expect(screen.getByText('Last 90 days')).toBeInTheDocument();
    expect(screen.getByText('This week')).toBeInTheDocument();
    expect(screen.getByText('This month')).toBeInTheDocument();
    expect(screen.getByText('This year')).toBeInTheDocument();
    expect(screen.getByText('Custom Range')).toBeInTheDocument();
  });

  it('calls onChange when preset is selected', () => {
    render(
      <DateRangeSelector
        startDate={startDate}
        endDate={endDate}
        onChange={mockOnChange}
      />
    );

    const select = screen.getByDisplayValue('Last 30 days');
    fireEvent.change(select, { target: { value: '7d' } });

    expect(mockOnChange).toHaveBeenCalledWith(
      expect.any(Date),
      expect.any(Date)
    );
  });

  it('shows custom date inputs when custom range is selected', () => {
    render(
      <DateRangeSelector
        startDate={startDate}
        endDate={endDate}
        onChange={mockOnChange}
      />
    );

    const select = screen.getByDisplayValue('Last 30 days');
    fireEvent.change(select, { target: { value: 'custom' } });

    expect(screen.getByDisplayValue('2024-01-01')).toBeInTheDocument();
    expect(screen.getByText('to')).toBeInTheDocument();
    expect(screen.getByText('Apply')).toBeInTheDocument();
    expect(screen.getByText('Cancel')).toBeInTheDocument();
  });

  it('handles custom date input changes', () => {
    render(
      <DateRangeSelector
        startDate={startDate}
        endDate={endDate}
        onChange={mockOnChange}
      />
    );

    // Switch to custom range
    const select = screen.getByDisplayValue('Last 30 days');
    fireEvent.change(select, { target: { value: 'custom' } });

    // Change start date
    const startDateInput = screen.getAllByDisplayValue('2024-01-01')[0];
    fireEvent.change(startDateInput, { target: { value: '2024-01-15' } });

    // Change end date
    const endDateInput = screen.getAllByDisplayValue('2024-01-01')[1];
    fireEvent.change(endDateInput, { target: { value: '2024-01-31' } });

    // Apply changes
    const applyButton = screen.getByText('Apply');
    fireEvent.click(applyButton);

    expect(mockOnChange).toHaveBeenCalledWith(
      new Date('2024-01-15'),
      new Date('2024-01-31')
    );
  });

  it('cancels custom date selection', () => {
    render(
      <DateRangeSelector
        startDate={startDate}
        endDate={endDate}
        onChange={mockOnChange}
      />
    );

    // Switch to custom range
    const select = screen.getByDisplayValue('Last 30 days');
    fireEvent.change(select, { target: { value: 'custom' } });

    expect(screen.getByText('Apply')).toBeInTheDocument();

    // Cancel custom selection
    const cancelButton = screen.getByText('Cancel');
    fireEvent.click(cancelButton);

    expect(screen.queryByText('Apply')).not.toBeInTheDocument();
  });

  it('does not call onChange for invalid date range', () => {
    render(
      <DateRangeSelector
        startDate={startDate}
        endDate={endDate}
        onChange={mockOnChange}
      />
    );

    // Switch to custom range
    const select = screen.getByDisplayValue('Last 30 days');
    fireEvent.change(select, { target: { value: 'custom' } });

    // Set end date before start date (invalid)
    const startDateInput = screen.getAllByDisplayValue('2024-01-01')[0];
    fireEvent.change(startDateInput, { target: { value: '2024-01-31' } });

    const endDateInput = screen.getAllByDisplayValue('2024-01-01')[1];
    fireEvent.change(endDateInput, { target: { value: '2024-01-15' } });

    // Try to apply invalid range
    const applyButton = screen.getByText('Apply');
    fireEvent.click(applyButton);

    // Should not call onChange for invalid range
    expect(mockOnChange).not.toHaveBeenCalled();
  });

  it('displays formatted date range when not in custom mode', () => {
    render(
      <DateRangeSelector
        startDate={startDate}
        endDate={endDate}
        onChange={mockOnChange}
      />
    );

    expect(screen.getByText('Jan 1, 2024 - Jan 1, 2024')).toBeInTheDocument();
  });

  it('hides date range display when in custom mode', () => {
    render(
      <DateRangeSelector
        startDate={startDate}
        endDate={endDate}
        onChange={mockOnChange}
      />
    );

    // Switch to custom range
    const select = screen.getByDisplayValue('Last 30 days');
    fireEvent.change(select, { target: { value: 'custom' } });

    // Date range display should be hidden
    expect(screen.queryByText('Jan 1, 2024 - Jan 1, 2024')).not.toBeInTheDocument();
  });
});