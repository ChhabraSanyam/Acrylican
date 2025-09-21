import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import PlatformConnectionCard from '../PlatformConnectionCard';
import { PlatformInfo } from '../../../types/platform';

const mockConnectedPlatform: PlatformInfo = {
  platform: 'facebook',
  name: 'Facebook',
  description: 'Connect to Facebook for posting and engagement metrics',
  integration_type: 'api',
  auth_method: 'oauth2',
  enabled: true,
  connected: true,
  connection_status: 'active',
  platform_username: 'test_user',
  connected_at: '2023-01-01T00:00:00Z',
  last_validated_at: '2023-01-01T00:00:00Z',
  setup_required: false
};

const mockDisconnectedPlatform: PlatformInfo = {
  platform: 'instagram',
  name: 'Instagram',
  description: 'Connect to Instagram Business for content publishing',
  integration_type: 'api',
  auth_method: 'oauth2',
  enabled: false,
  connected: false,
  connection_status: 'not_connected',
  setup_required: true,
  setup_instructions: 'Click Connect to authorize'
};

const mockPlatformWithError: PlatformInfo = {
  platform: 'etsy',
  name: 'Etsy',
  description: 'Connect to Etsy for marketplace listings',
  integration_type: 'api',
  auth_method: 'oauth1',
  enabled: true,
  connected: true,
  connection_status: 'inactive',
  validation_error: 'Token expired',
  setup_required: true
};

describe('PlatformConnectionCard', () => {
  const mockHandlers = {
    onConnect: jest.fn(),
    onDisconnect: jest.fn(),
    onToggleEnable: jest.fn(),
    onTest: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders connected platform correctly', () => {
    render(
      <PlatformConnectionCard
        platform={mockConnectedPlatform}
        {...mockHandlers}
      />
    );

    expect(screen.getByText('Facebook')).toBeInTheDocument();
    expect(screen.getByText('Connected')).toBeInTheDocument();
    expect(screen.getByText('test_user')).toBeInTheDocument();
    expect(screen.getByText('Test')).toBeInTheDocument();
    expect(screen.getByText('Disconnect')).toBeInTheDocument();
    expect(screen.queryByText('Connect')).not.toBeInTheDocument();
  });

  it('renders disconnected platform correctly', () => {
    render(
      <PlatformConnectionCard
        platform={mockDisconnectedPlatform}
        {...mockHandlers}
      />
    );

    expect(screen.getByText('Instagram')).toBeInTheDocument();
    expect(screen.getByText('Not Connected')).toBeInTheDocument();
    expect(screen.getByText('Connect')).toBeInTheDocument();
    expect(screen.queryByText('Test')).not.toBeInTheDocument();
    expect(screen.queryByText('Disconnect')).not.toBeInTheDocument();
  });

  it('shows validation error when present', () => {
    render(
      <PlatformConnectionCard
        platform={mockPlatformWithError}
        {...mockHandlers}
      />
    );

    expect(screen.getByText('Token expired')).toBeInTheDocument();
  });

  it('shows setup instructions when required', () => {
    render(
      <PlatformConnectionCard
        platform={mockDisconnectedPlatform}
        {...mockHandlers}
      />
    );

    expect(screen.getByText('Click Connect to authorize')).toBeInTheDocument();
  });

  it('calls onConnect when connect button is clicked', () => {
    render(
      <PlatformConnectionCard
        platform={mockDisconnectedPlatform}
        {...mockHandlers}
      />
    );

    fireEvent.click(screen.getByText('Connect'));
    expect(mockHandlers.onConnect).toHaveBeenCalledTimes(1);
  });

  it('calls onDisconnect when disconnect button is clicked', () => {
    render(
      <PlatformConnectionCard
        platform={mockConnectedPlatform}
        {...mockHandlers}
      />
    );

    fireEvent.click(screen.getByText('Disconnect'));
    expect(mockHandlers.onDisconnect).toHaveBeenCalledTimes(1);
  });

  it('calls onTest when test button is clicked', () => {
    render(
      <PlatformConnectionCard
        platform={mockConnectedPlatform}
        {...mockHandlers}
      />
    );

    fireEvent.click(screen.getByText('Test'));
    expect(mockHandlers.onTest).toHaveBeenCalledTimes(1);
  });

  it('calls onToggleEnable when enable toggle is changed', () => {
    render(
      <PlatformConnectionCard
        platform={mockConnectedPlatform}
        {...mockHandlers}
      />
    );

    const enableToggle = screen.getByRole('checkbox');
    fireEvent.click(enableToggle);
    expect(mockHandlers.onToggleEnable).toHaveBeenCalledWith(false);
  });

  it('displays correct integration type badge', () => {
    render(
      <PlatformConnectionCard
        platform={mockConnectedPlatform}
        {...mockHandlers}
      />
    );

    expect(screen.getByText('🔗 API')).toBeInTheDocument();
    expect(screen.getByText('🔐 OAuth')).toBeInTheDocument();
  });

  it('displays browser automation badge for automation platforms', () => {
    const automationPlatform: PlatformInfo = {
      ...mockConnectedPlatform,
      platform: 'meesho',
      name: 'Meesho',
      integration_type: 'browser_automation',
      auth_method: 'credentials'
    };

    render(
      <PlatformConnectionCard
        platform={automationPlatform}
        {...mockHandlers}
      />
    );

    expect(screen.getByText('🤖 Browser Automation')).toBeInTheDocument();
    expect(screen.getByText('🔑 Credentials')).toBeInTheDocument();
  });

  it('formats dates correctly', () => {
    render(
      <PlatformConnectionCard
        platform={mockConnectedPlatform}
        {...mockHandlers}
      />
    );

    // Check that dates are formatted (exact format may vary by locale)
    const dateElements = screen.getAllByText(/1\/1\/2023|2023-01-01|Jan.*2023/);
    expect(dateElements.length).toBeGreaterThan(0);
  });

  it('shows platform icon', () => {
    render(
      <PlatformConnectionCard
        platform={mockConnectedPlatform}
        {...mockHandlers}
      />
    );

    // Facebook icon should be present (📘)
    expect(screen.getByText('📘')).toBeInTheDocument();
  });

  it('disables actions when platform is not connected', () => {
    render(
      <PlatformConnectionCard
        platform={mockDisconnectedPlatform}
        {...mockHandlers}
      />
    );

    // Only connect button should be available
    expect(screen.getByText('Connect')).toBeInTheDocument();
    expect(screen.queryByText('Test')).not.toBeInTheDocument();
    expect(screen.queryByText('Disconnect')).not.toBeInTheDocument();
  });
});