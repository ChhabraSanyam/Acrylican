import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuthProvider } from '../../../contexts/AuthContext';
import LoginForm from '../LoginForm';
import { authService } from '../../../services/auth';

// Mock the auth service
jest.mock('../../../services/auth', () => ({
  authService: {
    login: jest.fn(),
    getCurrentUser: jest.fn(),
  },
  tokenManager: {
    getAccessToken: jest.fn(),
    isTokenExpired: jest.fn(),
    clearTokens: jest.fn(),
  },
}));

const mockAuthService = authService as jest.Mocked<typeof authService>;

const renderLoginForm = (props = {}) => {
  return render(
    <AuthProvider>
      <LoginForm {...props} />
    </AuthProvider>
  );
};

describe('LoginForm', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders login form with all required fields', () => {
    renderLoginForm();

    expect(screen.getByRole('heading', { name: /sign in/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('shows validation errors for empty fields', async () => {
    const user = userEvent.setup();
    renderLoginForm();

    const submitButton = screen.getByRole('button', { name: /sign in/i });
    await user.click(submitButton);

    expect(screen.getByText('Email is required')).toBeInTheDocument();
    expect(screen.getByText('Password is required')).toBeInTheDocument();
  });

  it('shows validation error for invalid email format', async () => {
    const user = userEvent.setup();
    renderLoginForm();

    const emailInput = screen.getByLabelText(/email address/i);
    await user.type(emailInput, 'invalid-email');

    const submitButton = screen.getByRole('button', { name: /sign in/i });
    await user.click(submitButton);

    expect(screen.getByText('Email is invalid')).toBeInTheDocument();
  });

  it('clears validation errors when user starts typing', async () => {
    const user = userEvent.setup();
    renderLoginForm();

    const emailInput = screen.getByLabelText(/email address/i);
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    // Trigger validation error
    await user.click(submitButton);
    expect(screen.getByText('Email is required')).toBeInTheDocument();

    // Start typing to clear error
    await user.type(emailInput, 'test@example.com');
    expect(screen.queryByText('Email is required')).not.toBeInTheDocument();
  });

  it('calls login function with correct credentials on form submission', async () => {
    const user = userEvent.setup();
    const mockOnSuccess = jest.fn();
    
    mockAuthService.login.mockResolvedValue({
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

    renderLoginForm({ onSuccess: mockOnSuccess });

    const emailInput = screen.getByLabelText(/email address/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    await user.type(emailInput, 'test@example.com');
    await user.type(passwordInput, 'password123');
    await user.click(submitButton);

    await waitFor(() => {
      expect(mockAuthService.login).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password123',
      });
    });

    expect(mockOnSuccess).toHaveBeenCalled();
  });

  it('displays error message when login fails', async () => {
    const user = userEvent.setup();
    
    mockAuthService.login.mockRejectedValue(new Error('Invalid credentials'));

    renderLoginForm();

    const emailInput = screen.getByLabelText(/email address/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    await user.type(emailInput, 'test@example.com');
    await user.type(passwordInput, 'wrongpassword');
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Invalid credentials')).toBeInTheDocument();
    });
  });

  it('disables form inputs and shows loading state during submission', async () => {
    const user = userEvent.setup();
    
    // Mock a delayed response
    mockAuthService.login.mockImplementation(() => 
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

    renderLoginForm();

    const emailInput = screen.getByLabelText(/email address/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    await user.type(emailInput, 'test@example.com');
    await user.type(passwordInput, 'password123');
    await user.click(submitButton);

    // Check loading state
    expect(screen.getByText('Signing In...')).toBeInTheDocument();
    expect(emailInput).toBeDisabled();
    expect(passwordInput).toBeDisabled();
    expect(submitButton).toBeDisabled();

    // Wait for completion
    await waitFor(() => {
      expect(screen.queryByText('Signing In...')).not.toBeInTheDocument();
    });
  });

  it('calls onSwitchToRegister when register link is clicked', async () => {
    const user = userEvent.setup();
    const mockOnSwitchToRegister = jest.fn();

    renderLoginForm({ onSwitchToRegister: mockOnSwitchToRegister });

    const registerLink = screen.getByText('Sign up');
    await user.click(registerLink);

    expect(mockOnSwitchToRegister).toHaveBeenCalled();
  });

  it('does not show register link when onSwitchToRegister is not provided', () => {
    renderLoginForm();

    expect(screen.queryByText('Sign up')).not.toBeInTheDocument();
  });
});