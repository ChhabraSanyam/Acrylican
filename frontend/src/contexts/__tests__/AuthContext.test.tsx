import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuthProvider, useAuth } from '../AuthContext';
import { authService, tokenManager } from '../../services/auth';

// Mock the auth service and token manager
jest.mock('../../services/auth', () => ({
  authService: {
    login: jest.fn(),
    register: jest.fn(),
    getCurrentUser: jest.fn(),
    logout: jest.fn(),
    refreshToken: jest.fn(),
  },
  tokenManager: {
    getAccessToken: jest.fn(),
    isTokenExpired: jest.fn(),
    clearTokens: jest.fn(),
    setTokens: jest.fn(),
    getRefreshToken: jest.fn(),
  },
}));

const mockAuthService = authService as jest.Mocked<typeof authService>;
const mockTokenManager = tokenManager as jest.Mocked<typeof tokenManager>;

// Test component that uses the auth context
const TestComponent = () => {
  const { user, isAuthenticated, isLoading, login, register, logout, refreshToken } = useAuth();

  return (
    <div>
      <div data-testid="loading">{isLoading ? 'Loading' : 'Not Loading'}</div>
      <div data-testid="authenticated">{isAuthenticated ? 'Authenticated' : 'Not Authenticated'}</div>
      <div data-testid="user">{user ? user.business_name : 'No User'}</div>
      <button onClick={() => login({ email: 'test@example.com', password: 'password' })}>
        Login
      </button>
      <button onClick={() => register({ 
        email: 'test@example.com', 
        password: 'password',
        business_name: 'Test Business',
        business_type: 'Handicrafts'
      })}>
        Register
      </button>
      <button onClick={logout}>Logout</button>
      <button onClick={() => refreshToken()}>Refresh Token</button>
    </div>
  );
};

const renderWithAuthProvider = () => {
  return render(
    <AuthProvider>
      <TestComponent />
    </AuthProvider>
  );
};

describe('AuthContext', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('initializes with loading state and no user', () => {
    mockTokenManager.getAccessToken.mockReturnValue(null);
    
    renderWithAuthProvider();

    expect(screen.getByTestId('loading')).toHaveTextContent('Loading');
    expect(screen.getByTestId('authenticated')).toHaveTextContent('Not Authenticated');
    expect(screen.getByTestId('user')).toHaveTextContent('No User');
  });

  it('initializes user when valid token exists', async () => {
    const mockUser = {
      id: '1',
      email: 'test@example.com',
      business_name: 'Test Business',
      business_type: 'Handicrafts',
      is_active: true,
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-01-01T00:00:00Z',
    };

    mockTokenManager.getAccessToken.mockReturnValue('valid_token');
    mockTokenManager.isTokenExpired.mockReturnValue(false);
    mockAuthService.getCurrentUser.mockResolvedValue(mockUser);

    renderWithAuthProvider();

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('Not Loading');
    });

    expect(screen.getByTestId('authenticated')).toHaveTextContent('Authenticated');
    expect(screen.getByTestId('user')).toHaveTextContent('Test Business');
  });

  it('clears tokens when getCurrentUser fails during initialization', async () => {
    mockTokenManager.getAccessToken.mockReturnValue('invalid_token');
    mockTokenManager.isTokenExpired.mockReturnValue(false);
    mockAuthService.getCurrentUser.mockRejectedValue(new Error('Unauthorized'));

    renderWithAuthProvider();

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('Not Loading');
    });

    expect(mockTokenManager.clearTokens).toHaveBeenCalled();
    expect(screen.getByTestId('authenticated')).toHaveTextContent('Not Authenticated');
  });

  it('handles successful login', async () => {
    const user = userEvent.setup();
    const mockUser = {
      id: '1',
      email: 'test@example.com',
      business_name: 'Test Business',
      business_type: 'Handicrafts',
      is_active: true,
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-01-01T00:00:00Z',
    };

    mockTokenManager.getAccessToken.mockReturnValue(null);
    mockAuthService.login.mockResolvedValue({
      success: true,
      user: mockUser,
      tokens: {
        access_token: 'access_token',
        refresh_token: 'refresh_token',
        token_type: 'bearer',
      },
    });

    renderWithAuthProvider();

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('Not Loading');
    });

    const loginButton = screen.getByText('Login');
    await user.click(loginButton);

    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toHaveTextContent('Authenticated');
    });

    expect(screen.getByTestId('user')).toHaveTextContent('Test Business');
    expect(mockAuthService.login).toHaveBeenCalledWith({
      email: 'test@example.com',
      password: 'password',
    });
  });

  it('handles login failure', async () => {
    const user = userEvent.setup();

    mockTokenManager.getAccessToken.mockReturnValue(null);
    mockAuthService.login.mockRejectedValue(new Error('Invalid credentials'));

    renderWithAuthProvider();

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('Not Loading');
    });

    const loginButton = screen.getByText('Login');
    
    await expect(async () => {
      await user.click(loginButton);
    }).rejects.toThrow('Invalid credentials');

    expect(screen.getByTestId('authenticated')).toHaveTextContent('Not Authenticated');
  });

  it('handles successful registration', async () => {
    const user = userEvent.setup();
    const mockUser = {
      id: '1',
      email: 'test@example.com',
      business_name: 'Test Business',
      business_type: 'Handicrafts',
      is_active: true,
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-01-01T00:00:00Z',
    };

    mockTokenManager.getAccessToken.mockReturnValue(null);
    mockAuthService.register.mockResolvedValue({
      success: true,
      user: mockUser,
      tokens: {
        access_token: 'access_token',
        refresh_token: 'refresh_token',
        token_type: 'bearer',
      },
    });

    renderWithAuthProvider();

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('Not Loading');
    });

    const registerButton = screen.getByText('Register');
    await user.click(registerButton);

    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toHaveTextContent('Authenticated');
    });

    expect(screen.getByTestId('user')).toHaveTextContent('Test Business');
    expect(mockAuthService.register).toHaveBeenCalledWith({
      email: 'test@example.com',
      password: 'password',
      business_name: 'Test Business',
      business_type: 'Handicrafts',
    });
  });

  it('handles logout', async () => {
    const user = userEvent.setup();
    const mockUser = {
      id: '1',
      email: 'test@example.com',
      business_name: 'Test Business',
      business_type: 'Handicrafts',
      is_active: true,
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-01-01T00:00:00Z',
    };

    // Start with authenticated user
    mockTokenManager.getAccessToken.mockReturnValue('valid_token');
    mockTokenManager.isTokenExpired.mockReturnValue(false);
    mockAuthService.getCurrentUser.mockResolvedValue(mockUser);

    renderWithAuthProvider();

    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toHaveTextContent('Authenticated');
    });

    const logoutButton = screen.getByText('Logout');
    await user.click(logoutButton);

    expect(mockAuthService.logout).toHaveBeenCalled();
    expect(screen.getByTestId('authenticated')).toHaveTextContent('Not Authenticated');
    expect(screen.getByTestId('user')).toHaveTextContent('No User');
  });

  it('handles successful token refresh', async () => {
    const user = userEvent.setup();

    mockTokenManager.getAccessToken.mockReturnValue(null);
    mockTokenManager.getRefreshToken.mockReturnValue('refresh_token');
    mockAuthService.refreshToken.mockResolvedValue({
      access_token: 'new_access_token',
      token_type: 'bearer',
    });

    renderWithAuthProvider();

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('Not Loading');
    });

    const refreshButton = screen.getByText('Refresh Token');
    await user.click(refreshButton);

    await waitFor(() => {
      expect(mockAuthService.refreshToken).toHaveBeenCalled();
    });

    expect(mockTokenManager.setTokens).toHaveBeenCalledWith('new_access_token', 'refresh_token');
  });

  it('handles token refresh failure by logging out', async () => {
    const user = userEvent.setup();

    mockTokenManager.getAccessToken.mockReturnValue(null);
    mockAuthService.refreshToken.mockRejectedValue(new Error('Refresh failed'));

    renderWithAuthProvider();

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('Not Loading');
    });

    const refreshButton = screen.getByText('Refresh Token');
    await user.click(refreshButton);

    await waitFor(() => {
      expect(mockAuthService.refreshToken).toHaveBeenCalled();
    });

    // Should logout on refresh failure
    expect(mockAuthService.logout).toHaveBeenCalled();
  });

  it('throws error when useAuth is used outside AuthProvider', () => {
    // Suppress console.error for this test
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => {
      render(<TestComponent />);
    }).toThrow('useAuth must be used within an AuthProvider');

    consoleSpy.mockRestore();
  });
});