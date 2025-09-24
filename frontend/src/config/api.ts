// API Configuration
export const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

// Validate required environment variables in production
if (process.env.NODE_ENV === 'production' && !process.env.REACT_APP_API_BASE_URL) {
  throw new Error('REACT_APP_API_BASE_URL is required in production');
}

export const API_ENDPOINTS = {
  // Authentication
  LOGIN: '/auth/login',
  REGISTER: '/auth/register',
  REFRESH: '/auth/refresh',
  LOGOUT: '/auth/logout',
  ME: '/auth/me',
  
  // Health
  HEALTH: '/health',
  
  // Products
  PRODUCTS: '/products',
  
  // Platforms
  PLATFORMS: '/platforms',
  
  // Analytics
  SALES_DASHBOARD: '/sales/dashboard',
  ENGAGEMENT_DASHBOARD: '/engagement/dashboard',
  SALES_PLATFORMS: '/sales/platforms',
  ENGAGEMENT_PLATFORMS: '/engagement/platforms',
  
  // Posts
  POSTS: '/posts',
  
  // Images
  IMAGES: '/images',
  
  // OAuth
  OAUTH: '/auth',
} as const;

export const HTTP_STATUS = {
  OK: 200,
  CREATED: 201,
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  INTERNAL_SERVER_ERROR: 500,
} as const;

export const APP_CONFIG = {
  ENVIRONMENT: process.env.REACT_APP_ENVIRONMENT || 'development',
  ENABLE_ANALYTICS: process.env.REACT_APP_ENABLE_ANALYTICS === 'true',
  ENABLE_PLATFORM_INTEGRATION: process.env.REACT_APP_ENABLE_PLATFORM_INTEGRATION === 'true',
} as const;