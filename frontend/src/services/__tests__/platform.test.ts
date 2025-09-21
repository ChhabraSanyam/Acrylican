import { platformService } from '../platform';
import { api } from '../../utils/api';

// Mock the api utility
jest.mock('../../utils/api');
const mockedApi = api as jest.Mocked<typeof api>;

describe('Platform Service', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('getConnections', () => {
    it('should fetch user platform connections', async () => {
      const mockConnections = [
        {
          id: 'conn-1',
          platform: 'facebook',
          is_active: true,
          connected_at: '2024-01-15T10:00:00Z',
          expires_at: '2024-07-15T10:00:00Z',
          user_info: {
            id: 'fb_user_123',
            name: 'Test User',
            profile_picture: 'https://facebook.com/profile.jpg'
          }
        },
        {
          id: 'conn-2',
          platform: 'instagram',
          is_active: true,
          connected_at: '2024-01-14T09:00:00Z',
          expires_at: '2024-07-14T09:00:00Z',
          user_info: {
            id: 'ig_user_456',
            username: 'testuser',
            profile_picture: 'https://instagram.com/profile.jpg'
          }
        }
      ];

      mockedApi.get.mockResolvedValue({ data: mockConnections });

      const result = await platformService.getConnections();

      expect(mockedApi.get).toHaveBeenCalledWith('/oauth/connections');
      expect(result).toEqual(mockConnections);
    });

    it('should handle empty connections list', async () => {
      mockedApi.get.mockResolvedValue({ data: [] });

      const result = await platformService.getConnections();

      expect(result).toEqual([]);
    });
  });

  describe('connectPlatform', () => {
    it('should initiate platform connection', async () => {
      const mockConnectionData = {
        authorization_url: 'https://facebook.com/oauth/authorize?client_id=123&redirect_uri=...',
        state: 'random_state_123',
        platform: 'facebook'
      };

      mockedApi.post.mockResolvedValue({ data: mockConnectionData });

      const result = await platformService.connectPlatform('facebook');

      expect(mockedApi.post).toHaveBeenCalledWith('/oauth/facebook/connect');
      expect(result).toEqual(mockConnectionData);
    });

    it('should handle connection initiation errors', async () => {
      const error = new Error('Platform not supported');
      mockedApi.post.mockRejectedValue(error);

      await expect(platformService.connectPlatform('unsupported')).rejects.toThrow('Platform not supported');
    });

    it('should handle Shopify connection with domain', async () => {
      const mockShopifyData = {
        authorization_url: 'https://testshop.myshopify.com/admin/oauth/authorize?...',
        state: 'shopify_state_456'
      };

      mockedApi.post.mockResolvedValue({ data: mockShopifyData });

      const result = await platformService.connectPlatform('shopify', { shop_domain: 'testshop' });

      expect(mockedApi.post).toHaveBeenCalledWith('/oauth/shopify/connect', {
        shop_domain: 'testshop'
      });
      expect(result).toEqual(mockShopifyData);
    });
  });

  describe('disconnectPlatform', () => {
    it('should disconnect platform successfully', async () => {
      mockedApi.delete.mockResolvedValue({ data: { success: true } });

      const result = await platformService.disconnectPlatform('facebook');

      expect(mockedApi.delete).toHaveBeenCalledWith('/oauth/facebook/disconnect');
      expect(result).toEqual({ success: true });
    });

    it('should handle disconnection errors', async () => {
      const error = new Error('Platform not connected');
      mockedApi.delete.mockRejectedValue(error);

      await expect(platformService.disconnectPlatform('facebook')).rejects.toThrow('Platform not connected');
    });
  });

  describe('getPlatformStatus', () => {
    it('should get platform connection status', async () => {
      const mockStatus = {
        platform: 'facebook',
        connected: true,
        expires_at: '2024-07-15T10:00:00Z',
        user_info: {
          id: 'fb_user_123',
          name: 'Test User'
        },
        permissions: ['pages_manage_posts', 'pages_read_engagement'],
        last_sync: '2024-01-15T10:00:00Z'
      };

      mockedApi.get.mockResolvedValue({ data: mockStatus });

      const result = await platformService.getPlatformStatus('facebook');

      expect(mockedApi.get).toHaveBeenCalledWith('/oauth/facebook/status');
      expect(result).toEqual(mockStatus);
    });

    it('should handle status check for disconnected platform', async () => {
      const mockStatus = {
        platform: 'instagram',
        connected: false
      };

      mockedApi.get.mockResolvedValue({ data: mockStatus });

      const result = await platformService.getPlatformStatus('instagram');

      expect(result.connected).toBe(false);
    });
  });

  describe('validateConnection', () => {
    it('should validate platform connection', async () => {
      const mockValidation = {
        platform: 'facebook',
        valid: true,
        last_checked: '2024-01-15T10:00:00Z',
        permissions_valid: true,
        token_expires_at: '2024-07-15T10:00:00Z'
      };

      mockedApi.post.mockResolvedValue({ data: mockValidation });

      const result = await platformService.validateConnection('facebook');

      expect(mockedApi.post).toHaveBeenCalledWith('/oauth/facebook/validate');
      expect(result).toEqual(mockValidation);
    });

    it('should handle invalid connection validation', async () => {
      const mockValidation = {
        platform: 'instagram',
        valid: false,
        error: 'Token expired',
        last_checked: '2024-01-15T10:00:00Z'
      };

      mockedApi.post.mockResolvedValue({ data: mockValidation });

      const result = await platformService.validateConnection('instagram');

      expect(result.valid).toBe(false);
      expect(result.error).toBe('Token expired');
    });
  });

  describe('getSupportedPlatforms', () => {
    it('should fetch supported platforms', async () => {
      const mockPlatforms = [
        {
          id: 'facebook',
          name: 'Facebook',
          description: 'Connect to Facebook Pages and Marketplace',
          icon: 'facebook-icon.svg',
          features: ['posting', 'analytics', 'marketplace'],
          oauth_type: 'oauth2',
          requires_approval: false
        },
        {
          id: 'instagram',
          name: 'Instagram',
          description: 'Connect to Instagram Business accounts',
          icon: 'instagram-icon.svg',
          features: ['posting', 'analytics'],
          oauth_type: 'oauth2',
          requires_approval: false
        },
        {
          id: 'etsy',
          name: 'Etsy',
          description: 'Connect to your Etsy shop',
          icon: 'etsy-icon.svg',
          features: ['posting', 'inventory_sync'],
          oauth_type: 'oauth1',
          requires_approval: true
        }
      ];

      mockedApi.get.mockResolvedValue({ data: mockPlatforms });

      const result = await platformService.getSupportedPlatforms();

      expect(mockedApi.get).toHaveBeenCalledWith('/platforms/supported');
      expect(result).toEqual(mockPlatforms);
    });
  });

  describe('getPlatformCapabilities', () => {
    it('should fetch platform capabilities', async () => {
      const mockCapabilities = {
        platform: 'facebook',
        posting: {
          supported: true,
          formats: ['text', 'image', 'video'],
          max_images: 10,
          character_limits: {
            title: 255,
            description: 2000
          }
        },
        analytics: {
          supported: true,
          metrics: ['likes', 'shares', 'comments', 'reach', 'impressions']
        },
        marketplace: {
          supported: true,
          categories: ['handmade', 'vintage', 'supplies']
        }
      };

      mockedApi.get.mockResolvedValue({ data: mockCapabilities });

      const result = await platformService.getPlatformCapabilities('facebook');

      expect(mockedApi.get).toHaveBeenCalledWith('/platforms/facebook/capabilities');
      expect(result).toEqual(mockCapabilities);
    });
  });

  describe('testConnection', () => {
    it('should test platform connection', async () => {
      const mockTestResult = {
        platform: 'facebook',
        success: true,
        response_time: 245,
        permissions_valid: true,
        api_version: 'v18.0',
        tested_at: '2024-01-15T10:00:00Z'
      };

      mockedApi.post.mockResolvedValue({ data: mockTestResult });

      const result = await platformService.testConnection('facebook');

      expect(mockedApi.post).toHaveBeenCalledWith('/oauth/facebook/test');
      expect(result).toEqual(mockTestResult);
    });

    it('should handle failed connection test', async () => {
      const mockTestResult = {
        platform: 'instagram',
        success: false,
        error: 'Invalid access token',
        tested_at: '2024-01-15T10:00:00Z'
      };

      mockedApi.post.mockResolvedValue({ data: mockTestResult });

      const result = await platformService.testConnection('instagram');

      expect(result.success).toBe(false);
      expect(result.error).toBe('Invalid access token');
    });
  });

  describe('refreshConnection', () => {
    it('should refresh platform connection', async () => {
      const mockRefreshResult = {
        platform: 'facebook',
        success: true,
        new_expires_at: '2024-07-15T10:00:00Z',
        refreshed_at: '2024-01-15T10:00:00Z'
      };

      mockedApi.post.mockResolvedValue({ data: mockRefreshResult });

      const result = await platformService.refreshConnection('facebook');

      expect(mockedApi.post).toHaveBeenCalledWith('/oauth/facebook/refresh');
      expect(result).toEqual(mockRefreshResult);
    });

    it('should handle refresh failures', async () => {
      const error = new Error('Refresh token expired');
      mockedApi.post.mockRejectedValue(error);

      await expect(platformService.refreshConnection('facebook')).rejects.toThrow('Refresh token expired');
    });
  });

  describe('getPlatformMetrics', () => {
    it('should fetch platform metrics', async () => {
      const mockMetrics = {
        platform: 'facebook',
        period: '30d',
        posts_count: 25,
        total_reach: 15000,
        total_engagement: 1250,
        engagement_rate: 0.083,
        top_performing_post: {
          id: 'post-123',
          title: 'Best Performing Post',
          engagement: 150
        },
        metrics_by_day: [
          { date: '2024-01-01', reach: 500, engagement: 42 },
          { date: '2024-01-02', reach: 650, engagement: 58 }
        ]
      };

      mockedApi.get.mockResolvedValue({ data: mockMetrics });

      const result = await platformService.getPlatformMetrics('facebook', '30d');

      expect(mockedApi.get).toHaveBeenCalledWith('/platforms/facebook/metrics', {
        params: { period: '30d' }
      });
      expect(result).toEqual(mockMetrics);
    });
  });

  describe('Error handling', () => {
    it('should handle network errors consistently', async () => {
      const networkError = new Error('Network Error');
      mockedApi.get.mockRejectedValue(networkError);

      await expect(platformService.getConnections()).rejects.toThrow('Network Error');
      await expect(platformService.getSupportedPlatforms()).rejects.toThrow('Network Error');
    });

    it('should handle API response errors with status codes', async () => {
      const apiError = {
        response: {
          status: 403,
          data: { message: 'Platform connection not authorized' }
        }
      };
      mockedApi.post.mockRejectedValue(apiError);

      await expect(platformService.connectPlatform('facebook')).rejects.toEqual(apiError);
    });

    it('should handle platform-specific errors', async () => {
      const platformError = {
        response: {
          status: 400,
          data: { 
            message: 'Invalid shop domain',
            platform: 'shopify',
            error_code: 'INVALID_DOMAIN'
          }
        }
      };
      mockedApi.post.mockRejectedValue(platformError);

      await expect(
        platformService.connectPlatform('shopify', { shop_domain: 'invalid' })
      ).rejects.toEqual(platformError);
    });
  });
});