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
  top_products: ProductSalesData[];
}

export interface ProductSalesData {
  id: string;
  title: string;
  revenue: number;
  orders: number;
  platform?: string;
}

export interface SaleEvent {
  id: string;
  platform: string;
  amount: number;
  currency: string;
  product_title?: string;
  occurred_at: string;
  order_id: string;
  status: string;
}

export interface SalesTrendData {
  date: string;
  revenue: number;
  orders: number;
}

export interface SalesDashboardData {
  overall_metrics: SalesMetrics;
  platform_breakdown: PlatformSalesBreakdown[];
  top_products: ProductSalesData[];
  recent_sales: SaleEvent[];
  sales_trend: SalesTrendData[];
}

export interface EngagementMetrics {
  likes: number;
  shares: number;
  comments: number;
  views: number;
  reach?: number;
  engagement_rate?: number;
}

export interface PlatformEngagementData {
  platform: string;
  likes: number;
  shares: number;
  comments: number;
  views: number;
  reach: number;
  engagement_rate?: number;
}

export interface EngagementTrendData {
  date: string;
  likes: number;
  shares: number;
  comments: number;
  views: number;
  engagement_rate?: number;
}

export interface TopPerformingPost {
  id: string;
  title: string;
  platform: string;
  likes: number;
  shares: number;
  comments: number;
  views: number;
  engagement_rate?: number;
  published_at: string;
}

export interface RecentEngagementMetric {
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
}

export interface EngagementDashboardData {
  total_engagement: EngagementMetrics;
  engagement_by_platform: PlatformEngagementData[];
  engagement_trend: EngagementTrendData[];
  top_performing_posts: TopPerformingPost[];
  recent_metrics: RecentEngagementMetric[];
  average_engagement_rate?: number;
  total_reach: number;
}

export interface DateRange {
  start_date: string;
  end_date: string;
}

export interface DashboardFilters {
  dateRange: DateRange;
  platforms: string[];
  currency: string;
}

export interface AnalyticsSummary {
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
}

export interface ChartDataPoint {
  x: string | number;
  y: number;
  label?: string;
}

export interface ChartData {
  labels: string[];
  datasets: Array<{
    label: string;
    data: number[];
    backgroundColor?: string | string[];
    borderColor?: string | string[];
    borderWidth?: number;
    fill?: boolean;
    tension?: number;
  }>;
}

export interface KPICard {
  title: string;
  value: string | number;
  change?: {
    value: number;
    type: 'increase' | 'decrease' | 'neutral';
    period: string;
  };
  icon?: string;
  color?: 'blue' | 'green' | 'yellow' | 'red' | 'purple' | 'indigo';
}

// Platform Performance Analysis Types
export interface PlatformPerformanceMetrics {
  platform: string;
  sales_metrics: {
    total_revenue: number;
    total_orders: number;
    average_order_value: number;
    commission_rate?: number;
    total_commission: number;
    net_revenue: number;
    conversion_rate?: number;
  };
  engagement_metrics: {
    likes: number;
    shares: number;
    comments: number;
    views: number;
    reach: number;
    engagement_rate: number;
    total_posts: number;
  };
  roi_metrics: {
    revenue_per_post: number;
    engagement_per_post: number;
    cost_per_acquisition?: number;
    return_on_investment?: number;
  };
  top_products: ProductSalesData[];
  performance_score: number;
  trend_direction: 'up' | 'down' | 'stable';
  trend_percentage: number;
}

export interface PlatformComparison {
  platform_a: string;
  platform_b: string;
  revenue_difference: number;
  revenue_difference_percentage: number;
  engagement_difference: number;
  engagement_difference_percentage: number;
  roi_difference: number;
  roi_difference_percentage: number;
  better_platform: string;
  recommendation: string;
}

export interface TopPerformingProduct {
  id: string;
  title: string;
  total_revenue: number;
  total_orders: number;
  total_engagement: number;
  platforms: Array<{
    platform: string;
    revenue: number;
    orders: number;
    engagement: number;
    performance_score: number;
  }>;
  best_platform: string;
  performance_score: number;
}

export interface PlatformROIAnalysis {
  platform: string;
  investment_metrics: {
    time_spent_hours?: number;
    advertising_cost?: number;
    content_creation_cost?: number;
    total_investment: number;
  };
  return_metrics: {
    gross_revenue: number;
    net_revenue: number;
    engagement_value: number;
    brand_awareness_value?: number;
    total_return: number;
  };
  roi_percentage: number;
  roi_category: 'excellent' | 'good' | 'average' | 'poor';
  recommendations: string[];
}

export interface PlatformPerformanceBreakdown {
  period_start: string;
  period_end: string;
  platforms: PlatformPerformanceMetrics[];
  comparisons: PlatformComparison[];
  top_products: TopPerformingProduct[];
  roi_analysis: PlatformROIAnalysis[];
  overall_insights: {
    best_performing_platform: string;
    highest_roi_platform: string;
    most_engaging_platform: string;
    recommendations: string[];
  };
}