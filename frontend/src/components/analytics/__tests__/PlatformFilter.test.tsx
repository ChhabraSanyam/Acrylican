import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import PlatformFilter from '../PlatformFilter';

describe('PlatformFilter', () => {
  const mockOnChange = jest.fn();
  const availablePlatforms = ['facebook', 'instagram', 'etsy', 'pinterest'];

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders platform filter with default state', () => {
    render(
      <PlatformFilter
        availablePlatforms={availablePlatforms}
        selectedPlatforms={[]}
        onChange={mockOnChange}
      />
    );

    expect(screen.getByText('Platforms:')).toBeInTheDocument();
    expect(screen.getByText('All Platforms')).toBeInTheDocument();
  });

  it('displays correct text when platforms are selected', () => {
    render(
      <PlatformFilter
        availablePlatforms={availablePlatforms}
        selectedPlatforms={['facebook']}
        onChange={mockOnChange}
      />
    );

    expect(screen.getByText('Facebook')).toBeInTheDocument();
  });

  it('displays count when multiple platforms are selected', () => {
    render(
      <PlatformFilter
        availablePlatforms={availablePlatforms}
        selectedPlatforms={['facebook', 'instagram']}
        onChange={mockOnChange}
      />
    );

    expect(screen.getByText('2 Platforms')).toBeInTheDocument();
  });

  it('displays "All Platforms" when all platforms are selected', () => {
    render(
      <PlatformFilter
        availablePlatforms={availablePlatforms}
        selectedPlatforms={availablePlatforms}
        onChange={mockOnChange}
      />
    );

    expect(screen.getByText('All Platforms')).toBeInTheDocument();
  });

  it('opens dropdown when button is clicked', () => {
    render(
      <PlatformFilter
        availablePlatforms={availablePlatforms}
        selectedPlatforms={[]}
        onChange={mockOnChange}
      />
    );

    const button = screen.getByText('All Platforms');
    fireEvent.click(button);

    expect(screen.getByText('Select All')).toBeInTheDocument();
    expect(screen.getByText('Clear All')).toBeInTheDocument();
    expect(screen.getByText('Facebook')).toBeInTheDocument();
    expect(screen.getByText('Instagram')).toBeInTheDocument();
    expect(screen.getByText('Etsy')).toBeInTheDocument();
    expect(screen.getByText('Pinterest')).toBeInTheDocument();
  });

  it('formats platform names correctly', () => {
    const platformsWithUnderscores = ['facebook_marketplace', 'facebook', 'instagram'];
    
    render(
      <PlatformFilter
        availablePlatforms={platformsWithUnderscores}
        selectedPlatforms={[]}
        onChange={mockOnChange}
      />
    );

    const button = screen.getByText('All Platforms');
    fireEvent.click(button);

    expect(screen.getByText('Facebook Marketplace')).toBeInTheDocument();
    expect(screen.getByText('Facebook')).toBeInTheDocument();
    expect(screen.getByText('Instagram')).toBeInTheDocument();
  });

  it('handles platform selection', () => {
    render(
      <PlatformFilter
        availablePlatforms={availablePlatforms}
        selectedPlatforms={[]}
        onChange={mockOnChange}
      />
    );

    // Open dropdown
    const button = screen.getByText('All Platforms');
    fireEvent.click(button);

    // Click on Facebook
    const facebookOption = screen.getByText('Facebook');
    fireEvent.click(facebookOption);

    expect(mockOnChange).toHaveBeenCalledWith(['facebook']);
  });

  it('handles platform deselection', () => {
    render(
      <PlatformFilter
        availablePlatforms={availablePlatforms}
        selectedPlatforms={['facebook']}
        onChange={mockOnChange}
      />
    );

    // Open dropdown
    const button = screen.getByText('Facebook');
    fireEvent.click(button);

    // Click on Facebook to deselect
    const facebookOption = screen.getByText('Facebook');
    fireEvent.click(facebookOption);

    expect(mockOnChange).toHaveBeenCalledWith([]);
  });

  it('handles select all functionality', () => {
    render(
      <PlatformFilter
        availablePlatforms={availablePlatforms}
        selectedPlatforms={[]}
        onChange={mockOnChange}
      />
    );

    // Open dropdown
    const button = screen.getByText('All Platforms');
    fireEvent.click(button);

    // Click Select All
    const selectAllButton = screen.getByText('Select All');
    fireEvent.click(selectAllButton);

    expect(mockOnChange).toHaveBeenCalledWith(availablePlatforms);
  });

  it('handles clear all functionality', () => {
    render(
      <PlatformFilter
        availablePlatforms={availablePlatforms}
        selectedPlatforms={availablePlatforms}
        onChange={mockOnChange}
      />
    );

    // Open dropdown
    const button = screen.getByText('All Platforms');
    fireEvent.click(button);

    // Click Clear All
    const clearAllButton = screen.getByText('Clear All');
    fireEvent.click(clearAllButton);

    expect(mockOnChange).toHaveBeenCalledWith([]);
  });

  it('shows checkboxes with correct states', () => {
    render(
      <PlatformFilter
        availablePlatforms={availablePlatforms}
        selectedPlatforms={['facebook', 'instagram']}
        onChange={mockOnChange}
      />
    );

    // Open dropdown
    const button = screen.getByText('2 Platforms');
    fireEvent.click(button);

    const checkboxes = screen.getAllByRole('checkbox');
    
    // Facebook and Instagram should be checked
    expect(checkboxes[0]).toBeChecked(); // Facebook
    expect(checkboxes[1]).toBeChecked(); // Instagram
    expect(checkboxes[2]).not.toBeChecked(); // Etsy
    expect(checkboxes[3]).not.toBeChecked(); // Pinterest
  });

  it('handles empty platforms list', () => {
    render(
      <PlatformFilter
        availablePlatforms={[]}
        selectedPlatforms={[]}
        onChange={mockOnChange}
      />
    );

    // Open dropdown
    const button = screen.getByText('All Platforms');
    fireEvent.click(button);

    expect(screen.getByText('No platforms available')).toBeInTheDocument();
  });

  it('closes dropdown when clicking outside', () => {
    render(
      <div>
        <PlatformFilter
          availablePlatforms={availablePlatforms}
          selectedPlatforms={[]}
          onChange={mockOnChange}
        />
        <div data-testid="outside">Outside element</div>
      </div>
    );

    // Open dropdown
    const button = screen.getByText('All Platforms');
    fireEvent.click(button);

    expect(screen.getByText('Select All')).toBeInTheDocument();

    // Click outside
    const outsideElement = screen.getByTestId('outside');
    fireEvent.click(outsideElement);

    // Dropdown should be closed (Select All should not be visible)
    expect(screen.queryByText('Select All')).not.toBeInTheDocument();
  });

  it('toggles dropdown arrow icon', () => {
    const { container } = render(
      <PlatformFilter
        availablePlatforms={availablePlatforms}
        selectedPlatforms={[]}
        onChange={mockOnChange}
      />
    );

    const button = screen.getByText('All Platforms');
    const arrow = container.querySelector('svg');

    // Initially not rotated
    expect(arrow).not.toHaveClass('rotate-180');

    // Click to open
    fireEvent.click(button);

    // Should be rotated
    expect(arrow).toHaveClass('rotate-180');
  });
});