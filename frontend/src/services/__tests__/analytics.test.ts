import { analyticsService } from '../analytics';
import { api } from '../../utils/api';

// Mock the api utility
jest.mock('../../utils/api');
const mockedApi = api as jest.Mocked<typeof api>;

describe('Analytics Service', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('getDashboardData', () => {
    it('should fetch dashboard data successfully', async () => {
      const mockDashboardData = {
        total_revenue: 1250.50,
        total_orders: 25,
        average_order_value: 50.02,
        platform_breakdown: {
          facebook: { revenue: 750.00, orders: 15 },
          instagram: { revenue: 500.50, orders: 10 }
        },
        top_products: [
          { id: '1', title: 'Product 1', revenue: 300.00, orders: 6 },
          { id: '2', title: 'Product 2', revenue: 250.00, orders: 5 }
        ]
      };

      mockedApi.get.mockResolvedValue({ data: mockDashboardData });

      const result = await analyticsService.getDashboardData(30);

      expect(mockedApi.get).toHaveBeenCalledWith('/analytics/dashboard', {
        params: { days: 30 }
      });
      expect(result).toEqual(mockDashboardData);
    });

    it('should handle API errors', async () => {
      const errorMessage = 'Failed to fetch dashboard data';
      mockedApi.get.mockRejectedValue(new Error(errorMessage));

      await expect(analyticsService.getDashboardData(30)).rejects.toThrow(errorMessage);
    });

    it('should use default days parameter when not provided', async () => {
      const mockData = { total_revenue: 0, total_orders: 0 };
      mockedApi.get.mockResolvedValue({ data: mockData });

      await analyticsService.getDashboardData();

      expect(mockedApi.get).toHaveBeenCalledWith('/analytics/dashboard', {
        params: { days: 30 }
      });
    });
  });

  describe('getPlatformBreakdown', () => {
    it('should fetch platform breakdown data', async () => {
      const mockBreakdown = {
        facebook: { revenue: 750.00, orders: 15, engagement: { likes: 120, shares: 25 } },
        instagram: { revenue: 500.50, orders: 10, engagement: { likes: 200, shares: 40 } },
        etsy: { revenue: 300.00, orders: 8, engagement: { views: 1500, favorites: 75 } }
      };

      mockedApi.get.mockResolvedValue({ data: mockBreakdown });

      const result = await analyticsService.getPlatformBreakdown(30, ['facebook', 'instagram', 'etsy']);

      expect(mockedApi.get).toHaveBeenCalledWith('/analytics/platform-breakdown', {
        params: { days: 30, platforms: 'facebook,instagram,etsy' }
      });
      expect(result).toEqual(mockBreakdown);
    });

    it('should handle empty platforms array', async () => {
      const mockData = {};
      mockedApi.get.mockResolvedValue({ data: mockData });

      const result = await analyticsService.getPlatformBreakdown(30, []);

      expect(mockedApi.get).toHaveBeenCalledWith('/analytics/platform-breakdown', {
        params: { days: 30, platforms: '' }
      });
      expect(result).toEqual(mockData);
    });
  });

  describe('getTopProducts', () => {
    it('should fetch top products with default limit', async () => {
      const mockProducts = [
        { id: '1', title: 'Handmade Vase', revenue: 450.00, orders: 9, conversion_rate: 0.15 },
        { id: '2', title: 'Ceramic Bowl', revenue: 320.00, orders: 8, conversion_rate: 0.12 },
        { id: '3', title: 'Pottery Set', revenue: 280.00, orders: 4, conversion_rate: 0.18 }
      ];

      mockedApi.get.mockResolvedValue({ data: mockProducts });

      const result = await analyticsService.getTopProducts();

      expect(mockedApi.get).toHaveBeenCalledWith('/analytics/top-products', {
        params: { limit: 10 }
      });
      expect(result).toEqual(mockProducts);
    });

    it('should fetch top products with custom limit', async () => {
      const mockProducts = [
        { id: '1', title: 'Product 1', revenue: 450.00, orders: 9 }
      ];

      mockedApi.get.mockResolvedValue({ data: mockProducts });

      const result = await analyticsService.getTopProducts(5);

      expect(mockedApi.get).toHaveBeenCalledWith('/analytics/top-products', {
        params: { limit: 5 }
      });
      expect(result).toEqual(mockProducts);
    });
  });

  describe('getEngagementMetrics', () => {
    it('should fetch engagement metrics for date range', async () => {
      const mockMetrics = {
        total_likes: 1250,
        total_shares: 340,
        total_comments: 180,
        total_reach: 15000,
        engagement_rate: 0.12,
        platform_metrics: {
          facebook: { likes: 600, shares: 150, comments: 80, reach: 7500 },
          instagram: { likes: 650, shares: 190, comments: 100, reach: 7500 }
        }
      };

      mockedApi.get.mockResolvedValue({ data: mockMetrics });

      const startDate = '2024-01-01';
      const endDate = '2024-01-31';
      const result = await analyticsService.getEngagementMetrics(startDate, endDate);

      expect(mockedApi.get).toHaveBeenCalledWith('/analytics/engagement', {
        params: { start_date: startDate, end_date: endDate }
      });
      expect(result).toEqual(mockMetrics);
    });

    it('should fetch engagement metrics with platform filter', async () => {
      const mockMetrics = {
        total_likes: 600,
        total_shares: 150,
        platform_metrics: {
          facebook: { likes: 600, shares: 150, comments: 80 }
        }
      };

      mockedApi.get.mockResolvedValue({ data: mockMetrics });

      const result = await analyticsService.getEngagementMetrics('2024-01-01', '2024-01-31', ['facebook']);

      expect(mockedApi.get).toHaveBeenCalledWith('/analytics/engagement', {
        params: { 
          start_date: '2024-01-01', 
          end_date: '2024-01-31',
          platforms: 'facebook'
        }
      });
      expect(result).toEqual(mockMetrics);
    });
  });

  describe('getRevenueMetrics', () => {
    it('should fetch revenue metrics', async () => {
      const mockRevenue = {
        total_revenue: 2500.75,
        total_orders: 45,
        average_order_value: 55.57,
        revenue_by_period: [
          { date: '2024-01-01', revenue: 125.50, orders: 3 },
          { date: '2024-01-02', revenue: 200.25, orders: 4 },
          { date: '2024-01-03', revenue: 175.00, orders: 2 }
        ],
        revenue_by_platform: {
          facebook: 1200.50,
          instagram: 800.25,
          etsy: 500.00
        }
      };

      mockedApi.get.mockResolvedValue({ data: mockRevenue });

      const result = await analyticsService.getRevenueMetrics(30, 'USD');

      expect(mockedApi.get).toHaveBeenCalledWith('/analytics/revenue', {
        params: { days: 30, currency: 'USD' }
      });
      expect(result).toEqual(mockRevenue);
    });

    it('should use default currency when not provided', async () => {
      const mockData = { total_revenue: 0 };
      mockedApi.get.mockResolvedValue({ data: mockData });

      await analyticsService.getRevenueMetrics(30);

      expect(mockedApi.get).toHaveBeenCalledWith('/analytics/revenue', {
        params: { days: 30, currency: 'USD' }
      });
    });
  });

  describe('getPerformanceTrends', () => {
    it('should fetch performance trends', async () => {
      const mockTrends = {
        revenue_trend: [
          { period: '2024-01', value: 1200.50, change: 0.15 },
          { period: '2024-02', value: 1380.75, change: 0.12 },
          { period: '2024-03', value: 1550.25, change: 0.08 }
        ],
        engagement_trend: [
          { period: '2024-01', likes: 450, shares: 120, comments: 80 },
          { period: '2024-02', likes: 520, shares: 140, comments: 95 },
          { period: '2024-03', likes: 580, shares: 160, comments: 110 }
        ],
        growth_metrics: {
          revenue_growth: 0.29,
          engagement_growth: 0.22,
          customer_growth: 0.18
        }
      };

      mockedApi.get.mockResolvedValue({ data: mockTrends });

      const result = await analyticsService.getPerformanceTrends('monthly', 6);

      expect(mockedApi.get).toHaveBeenCalledWith('/analytics/trends', {
        params: { period: 'monthly', periods: 6 }
      });
      expect(result).toEqual(mockTrends);
    });

    it('should handle different period types', async () => {
      const mockData = { revenue_trend: [] };
      mockedApi.get.mockResolvedValue({ data: mockData });

      await analyticsService.getPerformanceTrends('weekly', 12);

      expect(mockedApi.get).toHaveBeenCalledWith('/analytics/trends', {
        params: { period: 'weekly', periods: 12 }
      });
    });
  });

  describe('exportAnalyticsData', () => {
    it('should export analytics data', async () => {
      const mockExportData = {
        export_id: 'export-123',
        download_url: 'https://example.com/exports/analytics-export-123.csv',
        expires_at: '2024-02-01T12:00:00Z'
      };

      mockedApi.post.mockResolvedValue({ data: mockExportData });

      const exportParams = {
        start_date: '2024-01-01',
        end_date: '2024-01-31',
        format: 'csv' as const,
        include_engagement: true,
        include_revenue: true
      };

      const result = await analyticsService.exportAnalyticsData(exportParams);

      expect(mockedApi.post).toHaveBeenCalledWith('/analytics/export', exportParams);
      expect(result).toEqual(mockExportData);
    });

    it('should handle export with minimal parameters', async () => {
      const mockData = { export_id: 'export-456' };
      mockedApi.post.mockResolvedValue({ data: mockData });

      const result = await analyticsService.exportAnalyticsData({
        start_date: '2024-01-01',
        end_date: '2024-01-31',
        format: 'json'
      });

      expect(mockedApi.post).toHaveBeenCalledWith('/analytics/export', {
        start_date: '2024-01-01',
        end_date: '2024-01-31',
        format: 'json'
      });
      expect(result).toEqual(mockData);
    });
  });

  describe('Error handling', () => {
    it('should handle network errors consistently', async () => {
      const networkError = new Error('Network Error');
      mockedApi.get.mockRejectedValue(networkError);

      await expect(analyticsService.getDashboardData()).rejects.toThrow('Network Error');
      await expect(analyticsService.getTopProducts()).rejects.toThrow('Network Error');
      await expect(analyticsService.getPlatformBreakdown(30, [])).rejects.toThrow('Network Error');
    });

    it('should handle API response errors', async () => {
      const apiError = {
        response: {
          status: 400,
          data: { message: 'Invalid date range' }
        }
      };
      mockedApi.get.mockRejectedValue(apiError);

      await expect(analyticsService.getEngagementMetrics('invalid', 'dates')).rejects.toEqual(apiError);
    });
  });
});