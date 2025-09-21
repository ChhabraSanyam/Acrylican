import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import PlatformDashboard from '../PlatformDashboard';
import { platformService } from '../../../services/platform';
import { PlatformInfo } from '../../../types/platform';

// Mock the platform service
jest.mock('../../../services/platform');
const mockPlatformService = platformService as jest.Mocked<typeof platformService>;

// Mock child components
jest.mock('../PlatformConnectionCard', () => {
  return function MockPlatformConnectionCard({ platform, onConnect, onDisconnect, onToggleEnable, onTest }: any) {
    return (
      <div data-testid={`platform-card-${platform.platform}`}>
        <h3>{platform.name}</h3>
        <span>{platform.connected ? 'Connected' : 'Not Connected'}</span>
        <button onClick={onConnect}>Connect</button>
        <button onClick={() => onDisconnect(platform.platform)}>Disconnect</button>
        <button onClick={() => onToggleEnable(!platform.enabled)}>Toggle Enable</button>
        <button onClick={() => onTest(platform.platform)}>Test</button>
      </div>
    );
  };
});

jest.mock('../PlatformSetupWizard', () => {
  return function MockPlatformSetupWizard({ platform, onComplete, onCancel }: any) {
    return (
      <div data-testid="setup-wizard">
        <h3>Setup {platform}</h3>
        <button onClick={onComplete}>Complete</button>
        <button onClick={onCancel}>Cancel</button>
      </div>
    );
  };
});

jest.mock('../ConnectionTestDialog', () => {
  return function MockConnectionTestDialog({ results, onClose }: any) {
    return (
      <div data-testid="test-dialog">
        <h3>Test Results</h3>
        <div>{results.length} results</div>
        <button onClick={onClose}>Close</button>
      </div>
    );
  };
});

const mockPlatforms: PlatformInfo[] = [
  {
    platform: 'facebook',
    name: 'Facebook',
    description: 'Connect to Facebook for posting',
    integration_type: 'api',
    auth_method: 'oauth2',
    enabled: true,
    connected: true,
    connection_status: 'active',
    platform_username: 'test_user',
    connected_at: '2023-01-01T00:00:00Z',
    last_validated_at: '2023-01-01T00:00:00Z',
    setup_required: false
  },
  {
    platform: 'instagram',
    name: 'Instagram',
    description: 'Connect to Instagram for posting',
    integration_type: 'api',
    auth_method: 'oauth2',
    enabled: true,
    connected: false,
    connection_status: 'not_connected',
    setup_required: true,
    setup_instructions: 'Click Connect to authorize'
  }
];

describe('PlatformDashboard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders loading state initially', () => {
    mockPlatformService.getAllPlatforms.mockImplementation(() => new Promise(() => {}));
    
    render(<PlatformDashboard />);
    
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('renders platforms after loading', async () => {
    mockPlatformService.getAllPlatforms.mockResolvedValue(mockPlatforms);
    
    render(<PlatformDashboard />);
    
    await waitFor(() => {
      expect(screen.getByText('Platform Connections')).toBeInTheDocument();
    });
    
    expect(screen.getByText('Connected Platforms (1)')).toBeInTheDocument();
    expect(screen.getByText('Available Platforms (1)')).toBeInTheDocument();
    expect(screen.getByTestId('platform-card-facebook')).toBeInTheDocument();
    expect(screen.getByTestId('platform-card-instagram')).toBeInTheDocument();
  });

  it('handles error state', async () => {
    mockPlatformService.getAllPlatforms.mockRejectedValue(new Error('Failed to load'));
    
    render(<PlatformDashboard />);
    
    await waitFor(() => {
      expect(screen.getByText('Failed to load platforms')).toBeInTheDocument();
    });
  });

  it('opens setup wizard when connect is clicked', async () => {
    mockPlatformService.getAllPlatforms.mockResolvedValue(mockPlatforms);
    
    render(<PlatformDashboard />);
    
    await waitFor(() => {
      expect(screen.getByTestId('platform-card-instagram')).toBeInTheDocument();
    });
    
    const connectButton = screen.getAllByText('Connect')[0];
    fireEvent.click(connectButton);
    
    expect(screen.getByTestId('setup-wizard')).toBeInTheDocument();
  });

  it('handles disconnect platform', async () => {
    mockPlatformService.getAllPlatforms.mockResolvedValue(mockPlatforms);
    mockPlatformService.disconnectPlatform.mockResolvedValue({ message: 'Disconnected' });
    
    render(<PlatformDashboard />);
    
    await waitFor(() => {
      expect(screen.getByTestId('platform-card-facebook')).toBeInTheDocument();
    });
    
    const disconnectButtons = screen.getAllByText('Disconnect');
    fireEvent.click(disconnectButtons[0]); // Click the first disconnect button
    
    await waitFor(() => {
      expect(mockPlatformService.disconnectPlatform).toHaveBeenCalledWith('facebook');
    });
  });

  it('handles toggle enable platform', async () => {
    mockPlatformService.getAllPlatforms.mockResolvedValue(mockPlatforms);
    mockPlatformService.disablePlatform.mockResolvedValue({ message: 'Disabled' });
    
    render(<PlatformDashboard />);
    
    await waitFor(() => {
      expect(screen.getByTestId('platform-card-facebook')).toBeInTheDocument();
    });
    
    const toggleButton = screen.getAllByText('Toggle Enable')[0];
    fireEvent.click(toggleButton);
    
    await waitFor(() => {
      expect(mockPlatformService.disablePlatform).toHaveBeenCalledWith('facebook');
    });
  });

  it('handles test connection', async () => {
    mockPlatformService.getAllPlatforms.mockResolvedValue(mockPlatforms);
    mockPlatformService.testConnection.mockResolvedValue({
      platform: 'facebook',
      success: true,
      message: 'Connection successful'
    });
    
    render(<PlatformDashboard />);
    
    await waitFor(() => {
      expect(screen.getByTestId('platform-card-facebook')).toBeInTheDocument();
    });
    
    const testButton = screen.getAllByText('Test')[0];
    fireEvent.click(testButton);
    
    await waitFor(() => {
      expect(mockPlatformService.testConnection).toHaveBeenCalledWith('facebook');
      expect(screen.getByTestId('test-dialog')).toBeInTheDocument();
    });
  });

  it('handles test all connections', async () => {
    mockPlatformService.getAllPlatforms.mockResolvedValue(mockPlatforms);
    mockPlatformService.testAllConnections.mockResolvedValue({
      results: [
        { platform: 'facebook', success: true, message: 'Success' }
      ]
    });
    
    render(<PlatformDashboard />);
    
    await waitFor(() => {
      expect(screen.getByText('Test All Connections')).toBeInTheDocument();
    });
    
    const testAllButton = screen.getByText('Test All Connections');
    fireEvent.click(testAllButton);
    
    await waitFor(() => {
      expect(mockPlatformService.testAllConnections).toHaveBeenCalled();
      expect(screen.getByTestId('test-dialog')).toBeInTheDocument();
    });
  });

  it('handles setup wizard completion', async () => {
    mockPlatformService.getAllPlatforms.mockResolvedValue(mockPlatforms);
    
    render(<PlatformDashboard />);
    
    await waitFor(() => {
      expect(screen.getByTestId('platform-card-instagram')).toBeInTheDocument();
    });
    
    // Open setup wizard
    const connectButton = screen.getAllByText('Connect')[0];
    fireEvent.click(connectButton);
    
    expect(screen.getByTestId('setup-wizard')).toBeInTheDocument();
    
    // Complete setup
    const completeButton = screen.getByText('Complete');
    fireEvent.click(completeButton);
    
    expect(screen.queryByTestId('setup-wizard')).not.toBeInTheDocument();
  });

  it('dismisses error message', async () => {
    mockPlatformService.getAllPlatforms.mockRejectedValue(new Error('Failed to load'));
    
    render(<PlatformDashboard />);
    
    await waitFor(() => {
      expect(screen.getByText('Failed to load platforms')).toBeInTheDocument();
    });
    
    const dismissButton = screen.getByRole('button', { name: /dismiss/i });
    fireEvent.click(dismissButton);
    
    expect(screen.queryByText('Failed to load platforms')).not.toBeInTheDocument();
  });
});