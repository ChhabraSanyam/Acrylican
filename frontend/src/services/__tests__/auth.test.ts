import axios from 'axios';
import { authService, tokenManager } from '../auth';

// Mock axios
jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

// Mock window.location
delete (window as any).location;
window.location = { href: '' } as any;

describe('tokenManager', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('getAccessToken', () => {
    it('returns access token from localStorage', () => {
      localStorageMock.getItem.mockReturnValue('test_token');
      
      const token = tokenManager.getAccessToken();
      
      expect(localStorageMock.getItem).toHaveBeenCalledWith('access_token');
      expect(token).toBe('test_token');
    });

    it('returns null when no token exists', () => {
      localStorageMock.getItem.mockReturnValue(null);
      
      const token = tokenManager.getAccessToken();
      
      expect(token).toBeNull();
    });
  });

  describe('getRefreshToken', () => {
    it('returns refresh token from localStorage', () => {
      localStorageMock.getItem.mockReturnValue('refresh_token');
      
      const token = tokenManager.getRefreshToken();
      
      expect(localStorageMock.getItem).toHaveBeenCalledWith('refresh_token');
      expect(token).toBe('refresh_token');
    });
  });

  describe('setTokens', () => {
    it('stores both tokens in localStorage', () => {
      tokenManager.setTokens('access_token', 'refresh_token');
      
      expect(localStorageMock.setItem).toHaveBeenCalledWith('access_token', 'access_token');
      expect(localStorageMock.setItem).toHaveBeenCalledWith('refresh_token', 'refresh_token');
    });
  });

  describe('clearTokens', () => {
    it('removes both tokens from localStorage', () => {
      tokenManager.clearTokens();
      
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('access_token');
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('refresh_token');
    });
  });

  describe('isTokenExpired', () => {
    it('returns true for expired token', () => {
      // Create a token that expired 1 hour ago
      const expiredTime = Math.floor(Date.now() / 1000) - 3600;
      const payload = { exp: expiredTime };
      const token = `header.${btoa(JSON.stringify(payload))}.signature`;
      
      const isExpired = tokenManager.isTokenExpired(token);
      
      expect(isExpired).toBe(true);
    });

    it('returns false for valid token', () => {
      // Create a token that expires in 1 hour
      const futureTime = Math.floor(Date.now() / 1000) + 3600;
      const payload = { exp: futureTime };
      const token = `header.${btoa(JSON.stringify(payload))}.signature`;
      
      const isExpired = tokenManager.isTokenExpired(token);
      
      expect(isExpired).toBe(false);
    });

    it('returns true for malformed token', () => {
      const isExpired = tokenManager.isTokenExpired('invalid_token');
      
      expect(isExpired).toBe(true);
    });
  });
});

describe('authService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('login', () => {
    it('successfully logs in user and stores tokens', async () => {
      const mockResponse = {
        data: {
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
        },
      };

      mockedAxios.create.mockReturnValue({
        post: jest.fn().mockResolvedValue(mockResponse),
        interceptors: {
          request: { use: jest.fn() },
          response: { use: jest.fn() },
        },
      } as any);

      const credentials = { email: 'test@example.com', password: 'password' };
      const result = await authService.login(credentials);

      expect(result).toEqual(mockResponse.data);
      expect(localStorageMock.setItem).toHaveBeenCalledWith('access_token', 'access_token');
      expect(localStorageMock.setItem).toHaveBeenCalledWith('refresh_token', 'refresh_token');
    });

    it('throws error when login fails', async () => {
      const mockError = {
        response: {
          data: {
            detail: 'Invalid credentials',
          },
        },
      };

      mockedAxios.create.mockReturnValue({
        post: jest.fn().mockRejectedValue(mockError),
        interceptors: {
          request: { use: jest.fn() },
          response: { use: jest.fn() },
        },
      } as any);

      const credentials = { email: 'test@example.com', password: 'wrong_password' };

      await expect(authService.login(credentials)).rejects.toThrow('Invalid credentials');
    });
  });

  describe('register', () => {
    it('successfully registers user and stores tokens', async () => {
      const mockResponse = {
        data: {
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
        },
      };

      mockedAxios.create.mockReturnValue({
        post: jest.fn().mockResolvedValue(mockResponse),
        interceptors: {
          request: { use: jest.fn() },
          response: { use: jest.fn() },
        },
      } as any);

      const userData = {
        email: 'test@example.com',
        password: 'password',
        business_name: 'Test Business',
        business_type: 'Handicrafts',
      };

      const result = await authService.register(userData);

      expect(result).toEqual(mockResponse.data);
      expect(localStorageMock.setItem).toHaveBeenCalledWith('access_token', 'access_token');
      expect(localStorageMock.setItem).toHaveBeenCalledWith('refresh_token', 'refresh_token');
    });

    it('throws error when registration fails', async () => {
      const mockError = {
        response: {
          data: {
            detail: 'Email already registered',
          },
        },
      };

      mockedAxios.create.mockReturnValue({
        post: jest.fn().mockRejectedValue(mockError),
        interceptors: {
          request: { use: jest.fn() },
          response: { use: jest.fn() },
        },
      } as any);

      const userData = {
        email: 'existing@example.com',
        password: 'password',
        business_name: 'Test Business',
        business_type: 'Handicrafts',
      };

      await expect(authService.register(userData)).rejects.toThrow('Email already registered');
    });
  });

  describe('getCurrentUser', () => {
    it('successfully gets current user', async () => {
      const mockUser = {
        id: '1',
        email: 'test@example.com',
        business_name: 'Test Business',
        business_type: 'Handicrafts',
        is_active: true,
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T00:00:00Z',
      };

      mockedAxios.create.mockReturnValue({
        get: jest.fn().mockResolvedValue({ data: mockUser }),
        interceptors: {
          request: { use: jest.fn() },
          response: { use: jest.fn() },
        },
      } as any);

      const result = await authService.getCurrentUser();

      expect(result).toEqual(mockUser);
    });

    it('throws error when getting user fails', async () => {
      const mockError = {
        response: {
          data: {
            detail: 'Unauthorized',
          },
        },
      };

      mockedAxios.create.mockReturnValue({
        get: jest.fn().mockRejectedValue(mockError),
        interceptors: {
          request: { use: jest.fn() },
          response: { use: jest.fn() },
        },
      } as any);

      await expect(authService.getCurrentUser()).rejects.toThrow('Unauthorized');
    });
  });

  describe('refreshToken', () => {
    it('successfully refreshes token', async () => {
      const mockResponse = {
        data: {
          access_token: 'new_access_token',
          token_type: 'bearer',
        },
      };

      localStorageMock.getItem.mockReturnValue('refresh_token');
      mockedAxios.post.mockResolvedValue(mockResponse);

      const result = await authService.refreshToken();

      expect(result).toEqual(mockResponse.data);
      expect(mockedAxios.post).toHaveBeenCalledWith(
        'http://localhost:8000/auth/refresh',
        { refresh_token: 'refresh_token' }
      );
    });

    it('throws error when no refresh token available', async () => {
      localStorageMock.getItem.mockReturnValue(null);

      await expect(authService.refreshToken()).rejects.toThrow('No refresh token available');
    });

    it('throws error when refresh fails', async () => {
      const mockError = {
        response: {
          data: {
            detail: 'Invalid refresh token',
          },
        },
      };

      localStorageMock.getItem.mockReturnValue('invalid_refresh_token');
      mockedAxios.post.mockRejectedValue(mockError);

      await expect(authService.refreshToken()).rejects.toThrow('Invalid refresh token');
    });
  });

  describe('logout', () => {
    it('successfully logs out and clears tokens', async () => {
      mockedAxios.create.mockReturnValue({
        post: jest.fn().mockResolvedValue({}),
        interceptors: {
          request: { use: jest.fn() },
          response: { use: jest.fn() },
        },
      } as any);

      await authService.logout();

      expect(localStorageMock.removeItem).toHaveBeenCalledWith('access_token');
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('refresh_token');
    });

    it('clears tokens even when logout request fails', async () => {
      mockedAxios.create.mockReturnValue({
        post: jest.fn().mockRejectedValue(new Error('Network error')),
        interceptors: {
          request: { use: jest.fn() },
          response: { use: jest.fn() },
        },
      } as any);

      await authService.logout();

      expect(localStorageMock.removeItem).toHaveBeenCalledWith('access_token');
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('refresh_token');
    });
  });
});