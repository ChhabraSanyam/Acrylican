import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { PlatformPreferences } from '../PlatformPreferences';
import { preferencesService } from '../../../services/preferences';

// Mock the preferences service
jest.mock('../../../services/preferences');
const mockPreferencesService = preferencesService as jest.Mocked<typeof preferencesService>;

const mockPreferences = {
  id: '1',
  user_id: 'user1',
  platform: 'facebook',
  enabled: true,
  auto_post: true,
  priority: 0,
  content_style: 'professional',
  hashtag_strategy: 'branded',
  max_hashtags: 5,
  posting_schedule: {
    monday: ['09:00', '15:00'],
    tuesday: ['09:00', '15:00'],
    wednesday: ['09:00', '15:00'],
    thursday: ['09:00', '15:00'],
    friday: ['09:00', '15:00'],
    saturday: ['10:00'],
    sunday: ['10:00']
  },
  timezone: 'UTC',
  auto_schedule: false,
  optimal_times_enabled: true,
  platform_settings: {},
  title_format: '{title}',
  description_format: '{description}',
  include_branding: true,
  include_call_to_action: true,
  image_optimization: true,
  watermark_enabled: false,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z'
};

const mockTemplates = [
  {
    id: '1',
    user_id: 'user1',
    name: 'Professional Template',
    description: 'A professional template',
    title_template: '✨ {title} ✨',
    description_template: '{description}\n\n🔹 High Quality',
    hashtag_template: '#handmade #quality',
    platforms: ['facebook'],
    category: 'general',
    style: 'professional',
    usage_count: 5,
    is_default: true,
    is_system_template: false,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z'
  }
];

describe('PlatformPreferences', () => {
  const mockOnClose = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    mockPreferencesService.getPlatformPreferences.mockResolvedValue(mockPreferences);
    mockPreferencesService.getContentTemplates.mockResolvedValue(mockTemplates);
  });

  it('renders platform preferences modal', async () => {
    render(<PlatformPreferences platform="facebook" onClose={mockOnClose} />);

    await waitFor(() => {
      expect(screen.getByText('Facebook Preferences')).toBeInTheDocument();
    });

    expect(screen.getByText('General')).toBeInTheDocument();
    expect(screen.getByText('Content')).toBeInTheDocument();
    expect(screen.getByText('Schedule')).toBeInTheDocument();
    expect(screen.getByText('Advanced')).toBeInTheDocument();
  });

  it('loads and displays preferences', async () => {
    render(<PlatformPreferences platform="facebook" onClose={mockOnClose} />);

    await waitFor(() => {
      expect(mockPreferencesService.getPlatformPreferences).toHaveBeenCalledWith('facebook');
    });

    // Check that preferences are loaded and displayed
    expect(screen.getByDisplayValue('professional')).toBeInTheDocument();
    expect(screen.getByDisplayValue('branded')).toBeInTheDocument();
  });

  it('switches between tabs', async () => {
    render(<PlatformPreferences platform="facebook" onClose={mockOnClose} />);

    await waitFor(() => {
      expect(screen.getByText('Enable platform for posting')).toBeInTheDocument();
    });

    // Switch to Content tab
    fireEvent.click(screen.getByText('Content'));
    expect(screen.getByText('Content Style')).toBeInTheDocument();
    expect(screen.getByText('Hashtag Strategy')).toBeInTheDocument();

    // Switch to Schedule tab
    fireEvent.click(screen.getByText('Schedule'));
    expect(screen.getByText('Weekly Schedule')).toBeInTheDocument();

    // Switch to Advanced tab
    fireEvent.click(screen.getByText('Advanced'));
    expect(screen.getByText('Platform-Specific Settings')).toBeInTheDocument();
  });

  it('updates preferences when form fields change', async () => {
    render(<PlatformPreferences platform="facebook" onClose={mockOnClose} />);

    await waitFor(() => {
      expect(screen.getByText('Enable platform for posting')).toBeInTheDocument();
    });

    // Toggle enabled checkbox
    const enabledCheckbox = screen.getByLabelText('Enable platform for posting');
    fireEvent.click(enabledCheckbox);

    // Change priority slider
    const prioritySlider = screen.getByDisplayValue('0');
    fireEvent.change(prioritySlider, { target: { value: '5' } });

    // Verify the values are updated in the UI
    expect(screen.getByText('Current: 5')).toBeInTheDocument();
  });

  it('saves preferences when save button is clicked', async () => {
    mockPreferencesService.updatePlatformPreferences.mockResolvedValue(mockPreferences);

    render(<PlatformPreferences platform="facebook" onClose={mockOnClose} />);

    await waitFor(() => {
      expect(screen.getByText('Save Preferences')).toBeInTheDocument();
    });

    // Click save button
    fireEvent.click(screen.getByText('Save Preferences'));

    await waitFor(() => {
      expect(mockPreferencesService.updatePlatformPreferences).toHaveBeenCalledWith(
        'facebook',
        expect.any(Object)
      );
    });
  });

  it('resets preferences when reset button is clicked', async () => {
    // Mock window.confirm
    window.confirm = jest.fn(() => true);
    mockPreferencesService.resetPlatformPreferences.mockResolvedValue({ message: 'Reset successful' });

    render(<PlatformPreferences platform="facebook" onClose={mockOnClose} />);

    await waitFor(() => {
      expect(screen.getByText('Reset to Defaults')).toBeInTheDocument();
    });

    // Click reset button
    fireEvent.click(screen.getByText('Reset to Defaults'));

    await waitFor(() => {
      expect(mockPreferencesService.resetPlatformPreferences).toHaveBeenCalledWith('facebook');
    });
  });

  it('manages posting schedule', async () => {
    render(<PlatformPreferences platform="facebook" onClose={mockOnClose} />);

    await waitFor(() => {
      expect(screen.getByText('Schedule')).toBeInTheDocument();
    });

    // Switch to Schedule tab
    fireEvent.click(screen.getByText('Schedule'));

    await waitFor(() => {
      expect(screen.getByText('Weekly Schedule')).toBeInTheDocument();
    });

    // Add time slot for Monday
    const addTimeButtons = screen.getAllByText('+ Add Time');
    fireEvent.click(addTimeButtons[0]); // Click first "Add Time" button (Monday)

    // Remove time slot
    const removeButtons = screen.getAllByRole('button', { name: /remove/i });
    if (removeButtons.length > 0) {
      fireEvent.click(removeButtons[0]);
    }
  });

  it('handles content tab settings', async () => {
    render(<PlatformPreferences platform="facebook" onClose={mockOnClose} />);

    await waitFor(() => {
      expect(screen.getByText('Content')).toBeInTheDocument();
    });

    // Switch to Content tab
    fireEvent.click(screen.getByText('Content'));

    await waitFor(() => {
      expect(screen.getByText('Content Style')).toBeInTheDocument();
    });

    // Change content style
    const contentStyleSelect = screen.getByDisplayValue('professional');
    fireEvent.change(contentStyleSelect, { target: { value: 'casual' } });

    // Change hashtag strategy
    const hashtagStrategySelect = screen.getByDisplayValue('branded');
    fireEvent.change(hashtagStrategySelect, { target: { value: 'trending' } });

    // Toggle branding checkbox
    const brandingCheckbox = screen.getByLabelText('Include branding');
    fireEvent.click(brandingCheckbox);
  });

  it('displays error message when loading fails', async () => {
    mockPreferencesService.getPlatformPreferences.mockRejectedValue(new Error('Failed to load'));

    render(<PlatformPreferences platform="facebook" onClose={mockOnClose} />);

    await waitFor(() => {
      expect(screen.getByText('Failed to load preferences')).toBeInTheDocument();
    });
  });

  it('displays error message when saving fails', async () => {
    mockPreferencesService.updatePlatformPreferences.mockRejectedValue(new Error('Failed to save'));

    render(<PlatformPreferences platform="facebook" onClose={mockOnClose} />);

    await waitFor(() => {
      expect(screen.getByText('Save Preferences')).toBeInTheDocument();
    });

    // Click save button
    fireEvent.click(screen.getByText('Save Preferences'));

    await waitFor(() => {
      expect(screen.getByText('Failed to save preferences')).toBeInTheDocument();
    });
  });

  it('closes modal when close button is clicked', async () => {
    render(<PlatformPreferences platform="facebook" onClose={mockOnClose} />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /close/i })).toBeInTheDocument();
    });

    // Click close button (X)
    const closeButton = screen.getByRole('button', { name: /close/i });
    fireEvent.click(closeButton);

    expect(mockOnClose).toHaveBeenCalled();
  });

  it('closes modal when cancel button is clicked', async () => {
    render(<PlatformPreferences platform="facebook" onClose={mockOnClose} />);

    await waitFor(() => {
      expect(screen.getByText('Cancel')).toBeInTheDocument();
    });

    // Click cancel button
    fireEvent.click(screen.getByText('Cancel'));

    expect(mockOnClose).toHaveBeenCalled();
  });

  it('handles timezone selection', async () => {
    render(<PlatformPreferences platform="facebook" onClose={mockOnClose} />);

    await waitFor(() => {
      expect(screen.getByText('Timezone')).toBeInTheDocument();
    });

    // Change timezone
    const timezoneSelect = screen.getByDisplayValue('UTC');
    fireEvent.change(timezoneSelect, { target: { value: 'America/New_York' } });

    expect(timezoneSelect).toHaveValue('America/New_York');
  });

  it('handles template format inputs', async () => {
    render(<PlatformPreferences platform="facebook" onClose={mockOnClose} />);

    // Switch to Content tab
    fireEvent.click(screen.getByText('Content'));

    await waitFor(() => {
      expect(screen.getByText('Title Format Template')).toBeInTheDocument();
    });

    // Update title format
    const titleFormatInput = screen.getByPlaceholderText('{title}');
    fireEvent.change(titleFormatInput, { target: { value: '✨ {title} ✨' } });

    expect(titleFormatInput).toHaveValue('✨ {title} ✨');

    // Update description format
    const descriptionFormatTextarea = screen.getByPlaceholderText('{description}');
    fireEvent.change(descriptionFormatTextarea, { 
      target: { value: '{description}\n\nCustom footer' } 
    });

    expect(descriptionFormatTextarea).toHaveValue('{description}\n\nCustom footer');
  });
});