import api from './auth';

export interface SalesMetrics {
  total_revenue: number;
  total_orders: number;
  average_order_value: number;
  total_commission: number;
  net_revenue: number;
  currency: string;
  period_start: string;
  period_end: string;
}

export interface PlatformSalesBreakdown {
  platform: string;
  total_revenue: number;
  total_orders: number;
  average_order_value: number;
  commission_rate?: number;
  total_commission: number;
  net_revenue: number;
  top_products: Array<{
    id: string;
    title: string;
    revenue: number;
    orders: number;
  }>;
}

export interface SalesDashboardData {
  overall_metrics: SalesMetrics;
  platform_breakdown: PlatformSalesBreakdown[];
  top_products: Array<{
    id: string;
    title: string;
    revenue: number;
    orders: number;
    platform: string;
  }>;
  recent_sales: Array<{
    id: string;
    platform: string;
    amount: number;
    currency: string;
    product_title?: string;
    occurred_at: string;
    order_id: string;
    status: string;
  }>;
  sales_trend: Array<{
    date: string;
    revenue: number;
    orders: number;
  }>;
}

export interface EngagementDashboardData {
  total_engagement: {
    likes: number;
    shares: number;
    comments: number;
    views: number;
  };
  engagement_by_platform: Array<{
    platform: string;
    likes: number;
    shares: number;
    comments: number;
    views: number;
    reach: number;
    engagement_rate?: number;
  }>;
  engagement_trend: Array<{
    date: string;
    likes: number;
    shares: number;
    comments: number;
    views: number;
    engagement_rate?: number;
  }>;
  top_performing_posts: Array<{
    id: string;
    title: string;
    platform: string;
    likes: number;
    shares: number;
    comments: number;
    views: number;
    engagement_rate?: number;
    published_at: string;
  }>;
  recent_metrics: Array<{
    id: string;
    post_id: string;
    platform: string;
    likes: number;
    shares: number;
    comments: number;
    views: number;
    reach: number;
    engagement_rate?: number;
    metrics_date: string;
  }>;
  average_engagement_rate?: number;
  total_reach: number;
}

export interface DateRange {
  start_date: string;
  end_date: string;
}

export const analyticsService = {
  async getSalesDashboard(days: number = 30, currency: string = 'USD'): Promise<SalesDashboardData> {
    try {
      const response = await api.get('/sales/dashboard', {
        params: { days, currency }
      });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to fetch sales dashboard data');
    }
  },

  async getSalesMetrics(
    startDate?: string,
    endDate?: string,
    platforms?: string[],
    currency: string = 'USD'
  ): Promise<SalesMetrics> {
    try {
      const params: any = { currency };
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;
      if (platforms && platforms.length > 0) params.platforms = platforms;

      const response = await api.get('/sales/metrics', { params });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to fetch sales metrics');
    }
  },

  async getEngagementDashboard(
    startDate?: string,
    endDate?: string,
    platforms?: string[]
  ): Promise<EngagementDashboardData> {
    try {
      const params: any = {};
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;
      if (platforms && platforms.length > 0) params.platforms = platforms;

      const response = await api.get('/engagement/dashboard', { params });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to fetch engagement dashboard data');
    }
  },

  async getEngagementSummary(days: number = 30): Promise<{
    period_days: number;
    start_date: string;
    end_date: string;
    total_posts: number;
    total_likes: number;
    total_shares: number;
    total_comments: number;
    total_views: number;
    total_reach: number;
    average_engagement_rate: number;
    active_platforms: number;
    total_engagement: number;
  }> {
    try {
      const response = await api.get('/engagement/summary', {
        params: { days }
      });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to fetch engagement summary');
    }
  },

  async getSalesPlatforms(): Promise<{ platforms: string[]; total_platforms: number }> {
    try {
      const response = await api.get('/sales/platforms');
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to fetch sales platforms');
    }
  },

  async getEngagementPlatforms(): Promise<string[]> {
    try {
      const response = await api.get('/engagement/platforms');
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to fetch engagement platforms');
    }
  },

  async getPlatformPerformanceBreakdown(
    startDate?: string,
    endDate?: string,
    platforms?: string[],
    currency: string = 'USD'
  ): Promise<any> {
    try {
      const params: any = { currency };
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;
      if (platforms && platforms.length > 0) params.platforms = platforms;

      const response = await api.get('/analytics/platform-performance', { params });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to fetch platform performance breakdown');
    }
  },

  async getPlatformComparison(
    platformA: string,
    platformB: string,
    startDate?: string,
    endDate?: string,
    currency: string = 'USD'
  ): Promise<any> {
    try {
      const params: any = { 
        platform_a: platformA, 
        platform_b: platformB, 
        currency 
      };
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;

      const response = await api.get('/analytics/platform-comparison', { params });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to fetch platform comparison');
    }
  },

  async getTopPerformingProducts(
    startDate?: string,
    endDate?: string,
    platforms?: string[],
    limit: number = 10,
    currency: string = 'USD'
  ): Promise<any> {
    try {
      const params: any = { limit, currency };
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;
      if (platforms && platforms.length > 0) params.platforms = platforms;

      const response = await api.get('/analytics/top-products', { params });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to fetch top performing products');
    }
  },

  async getPlatformROIAnalysis(
    startDate?: string,
    endDate?: string,
    platforms?: string[],
    currency: string = 'USD'
  ): Promise<any> {
    try {
      const params: any = { currency };
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;
      if (platforms && platforms.length > 0) params.platforms = platforms;

      const response = await api.get('/analytics/platform-roi', { params });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to fetch platform ROI analysis');
    }
  }
};

export default analyticsService;