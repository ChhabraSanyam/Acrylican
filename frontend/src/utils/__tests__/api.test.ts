import { API_BASE_URL, API_ENDPOINTS, HTTP_STATUS } from '../../config/api';

describe('API Configuration', () => {
  test('should have correct base URL', () => {
    expect(API_BASE_URL).toBe('http://localhost:8000');
  });

  test('should have all required endpoints', () => {
    expect(API_ENDPOINTS.LOGIN).toBe('/auth/login');
    expect(API_ENDPOINTS.REGISTER).toBe('/auth/register');
    expect(API_ENDPOINTS.REFRESH).toBe('/auth/refresh');
    expect(API_ENDPOINTS.HEALTH).toBe('/health');
    expect(API_ENDPOINTS.PROFILE).toBe('/users/profile');
    expect(API_ENDPOINTS.PRODUCTS).toBe('/products');
    expect(API_ENDPOINTS.PLATFORMS).toBe('/platforms');
    expect(API_ENDPOINTS.ANALYTICS).toBe('/analytics');
  });

  test('should have correct HTTP status codes', () => {
    expect(HTTP_STATUS.OK).toBe(200);
    expect(HTTP_STATUS.CREATED).toBe(201);
    expect(HTTP_STATUS.BAD_REQUEST).toBe(400);
    expect(HTTP_STATUS.UNAUTHORIZED).toBe(401);
    expect(HTTP_STATUS.FORBIDDEN).toBe(403);
    expect(HTTP_STATUS.NOT_FOUND).toBe(404);
    expect(HTTP_STATUS.INTERNAL_SERVER_ERROR).toBe(500);
  });

  test('localStorage token management', () => {
    // Clear localStorage before test
    localStorage.clear();
    
    // Test setting and getting tokens
    localStorage.setItem('access_token', 'test-access-token');
    localStorage.setItem('refresh_token', 'test-refresh-token');
    
    expect(localStorage.getItem('access_token')).toBe('test-access-token');
    expect(localStorage.getItem('refresh_token')).toBe('test-refresh-token');
    
    // Test removing tokens
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    
    expect(localStorage.getItem('access_token')).toBeNull();
    expect(localStorage.getItem('refresh_token')).toBeNull();
  });
});