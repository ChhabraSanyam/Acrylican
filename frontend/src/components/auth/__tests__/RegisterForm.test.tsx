import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuthProvider } from '../../../contexts/AuthContext';
import RegisterForm from '../RegisterForm';
import { authService } from '../../../services/auth';

// Mock the auth service
jest.mock('../../../services/auth', () => ({
  authService: {
    register: jest.fn(),
    getCurrentUser: jest.fn(),
  },
  tokenManager: {
    getAccessToken: jest.fn(),
    isTokenExpired: jest.fn(),
    clearTokens: jest.fn(),
  },
}));

const mockAuthService = authService as jest.Mocked<typeof authService>;

const renderRegisterForm = (props = {}) => {
  return render(
    <AuthProvider>
      <RegisterForm {...props} />
    </AuthProvider>
  );
};

describe('RegisterForm', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders registration form with all required fields', () => {
    renderRegisterForm();

    expect(screen.getByText('Create Account')).toBeInTheDocument();
    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/business name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/business type/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument();
  });

  it('shows validation errors for empty required fields', async () => {
    const user = userEvent.setup();
    renderRegisterForm();

    const submitButton = screen.getByRole('button', { name: /create account/i });
    await user.click(submitButton);

    expect(screen.getByText('Email is required')).toBeInTheDocument();
    expect(screen.getByText('Password is required')).toBeInTheDocument();
    expect(screen.getByText('Business name is required')).toBeInTheDocument();
    expect(screen.getByText('Business type is required')).toBeInTheDocument();
  });

  it('shows validation error for short password', async () => {
    const user = userEvent.setup();
    renderRegisterForm();

    const passwordInput = screen.getByLabelText(/password/i);
    await user.type(passwordInput, '123');

    const submitButton = screen.getByRole('button', { name: /create account/i });
    await user.click(submitButton);

    expect(screen.getByText('Password must be at least 8 characters long')).toBeInTheDocument();
  });

  it('shows validation error for invalid website URL', async () => {
    const user = userEvent.setup();
    renderRegisterForm();

    const websiteInput = screen.getByLabelText(/website/i);
    await user.type(websiteInput, 'invalid-url');

    const submitButton = screen.getByRole('button', { name: /create account/i });
    await user.click(submitButton);

    expect(screen.getByText('Website must be a valid URL (include http:// or https://)')).toBeInTheDocument();
  });

  it('accepts valid website URLs', async () => {
    const user = userEvent.setup();
    renderRegisterForm();

    const websiteInput = screen.getByLabelText(/website/i);
    await user.type(websiteInput, 'https://example.com');

    const submitButton = screen.getByRole('button', { name: /create account/i });
    await user.click(submitButton);

    expect(screen.queryByText('Website must be a valid URL')).not.toBeInTheDocument();
  });

  it('populates business type dropdown with predefined options', () => {
    renderRegisterForm();

    const businessTypeSelect = screen.getByLabelText(/business type/i);
    
    expect(businessTypeSelect).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Handicrafts' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Jewelry' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Textiles' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Other' })).toBeInTheDocument();
  });

  it('calls register function with correct data on form submission', async () => {
    const user = userEvent.setup();
    const mockOnSuccess = jest.fn();
    
    mockAuthService.register.mockResolvedValue({
      success: true,
      user: {
        id: '1',
        email: 'test@example.com',
        business_name: 'Test Business',
        business_type: 'Handicrafts',
        is_active: true,
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T00:00:00Z',
      },
      tokens: {
        access_token: 'access_token',
        refresh_token: 'refresh_token',
        token_type: 'bearer',
      },
    });

    renderRegisterForm({ onSuccess: mockOnSuccess });

    // Fill required fields
    await user.type(screen.getByLabelText(/email address/i), 'test@example.com');
    await user.type(screen.getByLabelText(/password/i), 'password123');
    await user.type(screen.getByLabelText(/business name/i), 'Test Business');
    await user.selectOptions(screen.getByLabelText(/business type/i), 'Handicrafts');

    // Fill optional fields
    await user.type(screen.getByLabelText(/business description/i), 'A test business');
    await user.type(screen.getByLabelText(/website/i), 'https://example.com');
    await user.type(screen.getByLabelText(/location/i), 'Test City');

    const submitButton = screen.getByRole('button', { name: /create account/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(mockAuthService.register).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password123',
        business_name: 'Test Business',
        business_type: 'Handicrafts',
        business_description: 'A test business',
        website: 'https://example.com',
        location: 'Test City',
      });
    });

    expect(mockOnSuccess).toHaveBeenCalled();
  });

  it('removes empty optional fields from registration data', async () => {
    const user = userEvent.setup();
    
    mockAuthService.register.mockResolvedValue({
      success: true,
      user: {
        id: '1',
        email: 'test@example.com',
        business_name: 'Test Business',
        business_type: 'Handicrafts',
        is_active: true,
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T00:00:00Z',
      },
    });

    renderRegisterForm();

    // Fill only required fields
    await user.type(screen.getByLabelText(/email address/i), 'test@example.com');
    await user.type(screen.getByLabelText(/password/i), 'password123');
    await user.type(screen.getByLabelText(/business name/i), 'Test Business');
    await user.selectOptions(screen.getByLabelText(/business type/i), 'Handicrafts');

    const submitButton = screen.getByRole('button', { name: /create account/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(mockAuthService.register).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password123',
        business_name: 'Test Business',
        business_type: 'Handicrafts',
        business_description: undefined,
        website: undefined,
        location: undefined,
      });
    });
  });

  it('displays error message when registration fails', async () => {
    const user = userEvent.setup();
    
    mockAuthService.register.mockRejectedValue(new Error('Email already registered'));

    renderRegisterForm();

    // Fill required fields
    await user.type(screen.getByLabelText(/email address/i), 'test@example.com');
    await user.type(screen.getByLabelText(/password/i), 'password123');
    await user.type(screen.getByLabelText(/business name/i), 'Test Business');
    await user.selectOptions(screen.getByLabelText(/business type/i), 'Handicrafts');

    const submitButton = screen.getByRole('button', { name: /create account/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Email already registered')).toBeInTheDocument();
    });
  });

  it('disables form inputs and shows loading state during submission', async () => {
    const user = userEvent.setup();
    
    // Mock a delayed response
    mockAuthService.register.mockImplementation(() => 
      new Promise(resolve => setTimeout(() => resolve({
        success: true,
        user: {
          id: '1',
          email: 'test@example.com',
          business_name: 'Test Business',
          business_type: 'Handicrafts',
          is_active: true,
          created_at: '2023-01-01T00:00:00Z',
          updated_at: '2023-01-01T00:00:00Z',
        },
      }), 100))
    );

    renderRegisterForm();

    // Fill required fields
    await user.type(screen.getByLabelText(/email address/i), 'test@example.com');
    await user.type(screen.getByLabelText(/password/i), 'password123');
    await user.type(screen.getByLabelText(/business name/i), 'Test Business');
    await user.selectOptions(screen.getByLabelText(/business type/i), 'Handicrafts');

    const submitButton = screen.getByRole('button', { name: /create account/i });
    await user.click(submitButton);

    // Check loading state
    expect(screen.getByText('Creating Account...')).toBeInTheDocument();
    expect(screen.getByLabelText(/email address/i)).toBeDisabled();
    expect(submitButton).toBeDisabled();

    // Wait for completion
    await waitFor(() => {
      expect(screen.queryByText('Creating Account...')).not.toBeInTheDocument();
    });
  });

  it('calls onSwitchToLogin when login link is clicked', async () => {
    const user = userEvent.setup();
    const mockOnSwitchToLogin = jest.fn();

    renderRegisterForm({ onSwitchToLogin: mockOnSwitchToLogin });

    const loginLink = screen.getByText('Sign in');
    await user.click(loginLink);

    expect(mockOnSwitchToLogin).toHaveBeenCalled();
  });

  it('does not show login link when onSwitchToLogin is not provided', () => {
    renderRegisterForm();

    expect(screen.queryByText('Sign in')).not.toBeInTheDocument();
  });
});