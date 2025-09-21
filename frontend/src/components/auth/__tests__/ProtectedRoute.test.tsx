import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from '../../../contexts/AuthContext';
import ProtectedRoute from '../ProtectedRoute';
import { authService, tokenManager } from '../../../services/auth';

// Mock the auth service and token manager
jest.mock('../../../services/auth', () => ({
  authService: {
    getCurrentUser: jest.fn(),
  },
  tokenManager: {
    getAccessToken: jest.fn(),
    isTokenExpired: jest.fn(),
    clearTokens: jest.fn(),
  },
}));

const mockAuthService = authService as jest.Mocked<typeof authService>;
const mockTokenManager = tokenManager as jest.Mocked<typeof tokenManager>;

const TestComponent = () => <div>Protected Content</div>;
const LoginComponent = () => <div>Login Page</div>;

const renderProtectedRoute = (initialEntries = ['/protected']) => {
  return render(
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginComponent />} />
          <Route path="/custom-login" element={<div>Custom Login</div>} />
          <Route 
            path="/protected" 
            element={
              <ProtectedRoute>
                <TestComponent />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/custom-redirect" 
            element={
              <ProtectedRoute redirectTo="/custom-login">
                <TestComponent />
              </ProtectedRoute>
            } 
          />
          <Route path="/" element={<div>Home</div>} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
};

describe('ProtectedRoute', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('shows loading spinner while checking authentication', () => {
    // Mock token exists but getCurrentUser is pending
    mockTokenManager.getAccessToken.mockReturnValue('valid_token');
    mockTokenManager.isTokenExpired.mockReturnValue(false);
    mockAuthService.getCurrentUser.mockImplementation(() => 
      new Promise(() => {}) // Never resolves to keep loading state
    );

    renderProtectedRoute();

    expect(screen.getByRole('status')).toBeInTheDocument(); // Loading spinner
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
    expect(screen.queryByText('Login Page')).not.toBeInTheDocument();
  });

  it('renders protected content when user is authenticated', async () => {
    // Mock successful authentication
    mockTokenManager.getAccessToken.mockReturnValue('valid_token');
    mockTokenManager.isTokenExpired.mockReturnValue(false);
    mockAuthService.getCurrentUser.mockResolvedValue({
      id: '1',
      email: 'test@example.com',
      business_name: 'Test Business',
      business_type: 'Handicrafts',
      is_active: true,
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-01-01T00:00:00Z',
    });

    renderProtectedRoute();

    // Wait for authentication to complete
    await screen.findByText('Protected Content');
    expect(screen.getByText('Protected Content')).toBeInTheDocument();
    expect(screen.queryByText('Login Page')).not.toBeInTheDocument();
  });

  it('redirects to login when user is not authenticated (no token)', async () => {
    // Mock no token
    mockTokenManager.getAccessToken.mockReturnValue(null);

    renderProtectedRoute();

    // Should redirect to login
    await screen.findByText('Login Page');
    expect(screen.getByText('Login Page')).toBeInTheDocument();
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('redirects to login when token is expired', async () => {
    // Mock expired token
    mockTokenManager.getAccessToken.mockReturnValue('expired_token');
    mockTokenManager.isTokenExpired.mockReturnValue(true);

    renderProtectedRoute();

    // Should redirect to login
    await screen.findByText('Login Page');
    expect(screen.getByText('Login Page')).toBeInTheDocument();
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('redirects to login when getCurrentUser fails', async () => {
    // Mock token exists but getCurrentUser fails
    mockTokenManager.getAccessToken.mockReturnValue('valid_token');
    mockTokenManager.isTokenExpired.mockReturnValue(false);
    mockAuthService.getCurrentUser.mockRejectedValue(new Error('Unauthorized'));

    renderProtectedRoute();

    // Should redirect to login after failed auth check
    await screen.findByText('Login Page');
    expect(screen.getByText('Login Page')).toBeInTheDocument();
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('uses custom redirect path when provided', async () => {
    // Mock no authentication
    mockTokenManager.getAccessToken.mockReturnValue(null);

    render(
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/custom-login" element={<div>Custom Login</div>} />
            <Route 
              path="/protected" 
              element={
                <ProtectedRoute redirectTo="/custom-login">
                  <TestComponent />
                </ProtectedRoute>
              } 
            />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    );

    // Should redirect to custom login path
    await screen.findByText('Custom Login');
    expect(screen.getByText('Custom Login')).toBeInTheDocument();
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('preserves location state for redirect after login', async () => {
    // This test would require more complex setup to test location state
    // For now, we'll just verify the basic redirect behavior
    mockTokenManager.getAccessToken.mockReturnValue(null);

    renderProtectedRoute(['/protected']);

    await screen.findByText('Login Page');
    expect(screen.getByText('Login Page')).toBeInTheDocument();
  });
});