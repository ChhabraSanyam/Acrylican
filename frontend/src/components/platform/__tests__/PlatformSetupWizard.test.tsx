import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import PlatformSetupWizard from '../PlatformSetupWizard';
import { platformService } from '../../../services/platform';
import { SetupWizardInfo } from '../../../types/platform';

// Mock the platform service
jest.mock('../../../services/platform');
const mockPlatformService = platformService as jest.Mocked<typeof platformService>;

const mockWizardInfo: SetupWizardInfo = {
  platform: 'facebook',
  platform_name: 'Facebook',
  integration_type: 'api',
  auth_method: 'oauth2',
  steps: [
    {
      step: 1,
      title: 'Facebook Authorization',
      description: 'Authorize the application to access your Facebook account',
      action: 'oauth',
      required_fields: []
    }
  ]
};

const mockCredentialWizardInfo: SetupWizardInfo = {
  platform: 'meesho',
  platform_name: 'Meesho',
  integration_type: 'browser_automation',
  auth_method: 'credentials',
  steps: [
    {
      step: 1,
      title: 'Meesho Seller Account',
      description: 'Enter your Meesho seller credentials',
      action: 'form',
      required_fields: [
        {
          name: 'email',
          label: 'Email',
          type: 'email',
          placeholder: 'your-email@example.com'
        },
        {
          name: 'password',
          label: 'Password',
          type: 'password',
          placeholder: 'Your Meesho password'
        }
      ]
    },
    {
      step: 2,
      title: 'Connection Test',
      description: 'Test the connection to your Meesho seller dashboard',
      action: 'test',
      required_fields: []
    }
  ]
};

describe('PlatformSetupWizard', () => {
  const mockHandlers = {
    onComplete: jest.fn(),
    onCancel: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders loading state initially', () => {
    mockPlatformService.getSetupWizardInfo.mockImplementation(() => new Promise(() => {}));
    
    render(
      <PlatformSetupWizard
        platform="facebook"
        {...mockHandlers}
      />
    );

    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('renders wizard info after loading', async () => {
    mockPlatformService.getSetupWizardInfo.mockResolvedValue(mockWizardInfo);
    
    render(
      <PlatformSetupWizard
        platform="facebook"
        {...mockHandlers}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Connect Facebook')).toBeInTheDocument();
    });

    expect(screen.getByText('Facebook Authorization')).toBeInTheDocument();
    expect(screen.getByText('Step 1 of 1')).toBeInTheDocument();
  });

  it('handles error loading wizard info', async () => {
    mockPlatformService.getSetupWizardInfo.mockRejectedValue(new Error('Failed to load'));
    
    render(
      <PlatformSetupWizard
        platform="facebook"
        {...mockHandlers}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Setup Error')).toBeInTheDocument();
    });

    expect(screen.getByText('Failed to load setup wizard information.')).toBeInTheDocument();
  });

  it('renders form fields for credential-based setup', async () => {
    mockPlatformService.getSetupWizardInfo.mockResolvedValue(mockCredentialWizardInfo);
    
    render(
      <PlatformSetupWizard
        platform="meesho"
        {...mockHandlers}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Connect Meesho')).toBeInTheDocument();
    });

    expect(screen.getByLabelText('Email')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
  });

  it('validates required fields before proceeding', async () => {
    mockPlatformService.getSetupWizardInfo.mockResolvedValue(mockCredentialWizardInfo);
    
    render(
      <PlatformSetupWizard
        platform="meesho"
        {...mockHandlers}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Connect Meesho')).toBeInTheDocument();
    });

    const nextButton = screen.getByText('Next');
    expect(nextButton).toBeDisabled();

    // Fill in required fields
    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'test@example.com' }
    });
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'password123' }
    });

    expect(nextButton).not.toBeDisabled();
  });

  it('proceeds to next step when form is valid', async () => {
    mockPlatformService.getSetupWizardInfo.mockResolvedValue(mockCredentialWizardInfo);
    
    render(
      <PlatformSetupWizard
        platform="meesho"
        {...mockHandlers}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Connect Meesho')).toBeInTheDocument();
    });

    // Fill in required fields
    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'test@example.com' }
    });
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'password123' }
    });

    // Click next
    fireEvent.click(screen.getByText('Next'));

    await waitFor(() => {
      expect(screen.getByText('Step 2 of 2')).toBeInTheDocument();
    });

    expect(screen.getByText('Connection Test')).toBeInTheDocument();
  });

  it('handles OAuth flow initiation', async () => {
    mockPlatformService.getSetupWizardInfo.mockResolvedValue(mockWizardInfo);
    mockPlatformService.initiateOAuthFlow.mockResolvedValue({
      authorization_url: 'https://facebook.com/oauth',
      state: 'test-state'
    });

    // Mock window.location.href
    delete (window as any).location;
    window.location = { href: '' } as any;

    render(
      <PlatformSetupWizard
        platform="facebook"
        {...mockHandlers}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Connect Facebook')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Complete'));

    await waitFor(() => {
      expect(mockPlatformService.initiateOAuthFlow).toHaveBeenCalledWith('facebook', undefined);
    });
  });

  it('handles connection test', async () => {
    mockPlatformService.getSetupWizardInfo.mockResolvedValue(mockCredentialWizardInfo);
    mockPlatformService.testConnection.mockResolvedValue({
      platform: 'meesho',
      success: true,
      message: 'Connection successful'
    });
    
    render(
      <PlatformSetupWizard
        platform="meesho"
        {...mockHandlers}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Connect Meesho')).toBeInTheDocument();
    });

    // Fill in required fields and proceed to test step
    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'test@example.com' }
    });
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'password123' }
    });
    fireEvent.click(screen.getByText('Next'));

    await waitFor(() => {
      expect(screen.getByText('Connection Test')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Complete'));

    await waitFor(() => {
      expect(mockPlatformService.testConnection).toHaveBeenCalledWith('meesho');
      expect(mockHandlers.onComplete).toHaveBeenCalled();
    });
  });

  it('handles connection test failure', async () => {
    mockPlatformService.getSetupWizardInfo.mockResolvedValue(mockCredentialWizardInfo);
    mockPlatformService.testConnection.mockResolvedValue({
      platform: 'meesho',
      success: false,
      message: 'Invalid credentials'
    });
    
    render(
      <PlatformSetupWizard
        platform="meesho"
        {...mockHandlers}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Connect Meesho')).toBeInTheDocument();
    });

    // Fill in required fields and proceed to test step
    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'test@example.com' }
    });
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'password123' }
    });
    fireEvent.click(screen.getByText('Next'));

    await waitFor(() => {
      expect(screen.getByText('Connection Test')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Complete'));

    await waitFor(() => {
      expect(screen.getByText('Invalid credentials')).toBeInTheDocument();
    });

    expect(mockHandlers.onComplete).not.toHaveBeenCalled();
  });

  it('allows going back to previous step', async () => {
    mockPlatformService.getSetupWizardInfo.mockResolvedValue(mockCredentialWizardInfo);
    
    render(
      <PlatformSetupWizard
        platform="meesho"
        {...mockHandlers}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Connect Meesho')).toBeInTheDocument();
    });

    // Fill in required fields and proceed to next step
    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'test@example.com' }
    });
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'password123' }
    });
    fireEvent.click(screen.getByText('Next'));

    await waitFor(() => {
      expect(screen.getByText('Step 2 of 2')).toBeInTheDocument();
    });

    // Go back
    fireEvent.click(screen.getByText('Previous'));

    await waitFor(() => {
      expect(screen.getByText('Step 1 of 2')).toBeInTheDocument();
    });
  });

  it('calls onCancel when cancel button is clicked', async () => {
    mockPlatformService.getSetupWizardInfo.mockResolvedValue(mockWizardInfo);
    
    render(
      <PlatformSetupWizard
        platform="facebook"
        {...mockHandlers}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Connect Facebook')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Cancel'));
    expect(mockHandlers.onCancel).toHaveBeenCalled();
  });

  it('calls onCancel when close button is clicked', async () => {
    mockPlatformService.getSetupWizardInfo.mockResolvedValue(mockWizardInfo);
    
    render(
      <PlatformSetupWizard
        platform="facebook"
        {...mockHandlers}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Connect Facebook')).toBeInTheDocument();
    });

    const closeButton = screen.getByRole('button', { name: /close setup wizard/i });
    fireEvent.click(closeButton);
    expect(mockHandlers.onCancel).toHaveBeenCalled();
  });

  it('updates progress bar correctly', async () => {
    mockPlatformService.getSetupWizardInfo.mockResolvedValue(mockCredentialWizardInfo);
    
    render(
      <PlatformSetupWizard
        platform="meesho"
        {...mockHandlers}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Step 1 of 2')).toBeInTheDocument();
    });

    // Progress should be 50% on step 1 of 2
    const progressBar = document.querySelector('.bg-blue-600');
    expect(progressBar).toHaveStyle('width: 50%');
  });
});