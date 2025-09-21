import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import AnalyticsDashboard from '../AnalyticsDashboard';
import { analyticsService } from '../../../services/analytics';

// Mock the analytics service
jest.mock('../../../services/analytics');
const mockAnalyticsService = analyticsService as jest.Mocked<typeof analyticsService>;

// Mock Chart.js components
jest.mock('react-chartjs-2', () => ({
  Line: () => <div data-testid="line-chart">Line Chart</div>,
  Bar: () => <div data-testid="bar-chart">Bar Chart</div>,
  Doughnut: () => <div data-testid="doughnut-chart">Doughnut Chart</div>,
}));

// Mock date-fns
jest.mock('date-fns', () => ({
  format: jest.fn((date, formatStr) => '2024-01-01T00:00:00'),
  subDays: jest.fn(() => new Date('2024-01-01')),
  startOfDay: jest.fn((date) => date),
  endOfDay: jest.fn((date) => date),
}));

const mockSalesData = {
  overall_metrics: {
    total_revenue: 10000,
    total_orders: 50,
    average_order_value: 200,
    total_commission: 1000,
    net_revenue: 9000,
    currency: 'USD',
    period_start: '2024-01-01T00:00:00',
    period_end: '2024-01-31T23:59:59'
  },
  platform_breakdown: [
    {
      platform: 'facebook',
      total_revenue: 5000,
      total_orders: 25,
      average_order_value: 200,
      total_commission: 500,
      net_revenue: 4500,
      top_products: []
    }
  ],
  top_products: [
    {
      id: '1',
      title: 'Test Product',
      revenue: 1000,
      orders: 5,
      platform: 'facebook'
    }
  ],
  recent_sales: [
    {
      id: '1',
      platform: 'facebook',
      amount: 100,
      currency: 'USD',
      product_title: 'Test Product',
      occurred_at: '2024-01-01T12:00:00',
      order_id: 'order-1',
      status: 'confirmed'
    }
  ],
  sales_trend: [
    {
      date: '2024-01-01',
      revenue: 1000,
      orders: 5
    }
  ]
};

const mockEngagementData = {
  total_engagement: {
    likes: 1000,
    shares: 200,
    comments: 150,
    views: 5000
  },
  engagement_by_platform: [
    {
      platform: 'facebook',
      likes: 500,
      shares: 100,
      comments: 75,
      views: 2500,
      reach: 10000,
      engagement_rate: 5.2
    }
  ],
  engagement_trend: [
    {
      date: '2024-01-01',
      likes: 100,
      shares: 20,
      comments: 15,
      views: 500,
      engagement_rate: 5.0
    }
  ],
  top_performing_posts: [
    {
      id: '1',
      title: 'Test Post',
      platform: 'facebook',
      likes: 100,
      shares: 20,
      comments: 15,
      views: 500,
      engagement_rate: 5.0,
      published_at: '2024-01-01T12:00:00'
    }
  ],
  recent_metrics: [],
  average_engagement_rate: 5.2,
  total_reach: 10000
};

describe('AnalyticsDashboard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockAnalyticsService.getSalesDashboard.mockResolvedValue(mockSalesData);
    mockAnalyticsService.getEngagementDashboard.mockResolvedValue(mockEngagementData);
    mockAnalyticsService.getSalesPlatforms.mockResolvedValue({
      platforms: ['facebook', 'instagram'],
      total_platforms: 2
    });
    mockAnalyticsService.getEngagementPlatforms.mockResolvedValue(['facebook', 'instagram']);
  });

  it('renders loading state initially', () => {
    render(<AnalyticsDashboard />);
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
  });

  it('renders dashboard content after loading', async () => {
    render(<AnalyticsDashboard />);

    await waitFor(() => {
      expect(screen.getByText('Analytics Dashboard')).toBeInTheDocument();
    });

    expect(screen.getByText('Track your sales performance and engagement metrics across all platforms')).toBeInTheDocument();
    expect(screen.getByText('Total Revenue')).toBeInTheDocument();
    expect(screen.getByText('Total Orders')).toBeInTheDocument();
    expect(screen.getByText('Total Engagement')).toBeInTheDocument();
  });

  it('displays KPI cards with correct values', async () => {
    render(<AnalyticsDashboard />);

    await waitFor(() => {
      expect(screen.getByText('$10,000')).toBeInTheDocument(); // Total Revenue
      expect(screen.getByText('50')).toBeInTheDocument(); // Total Orders
      expect(screen.getByText('$200')).toBeInTheDocument(); // Average Order Value
    });
  });

  it('handles refresh button click', async () => {
    render(<AnalyticsDashboard />);

    await waitFor(() => {
      expect(screen.getByText('Analytics Dashboard')).toBeInTheDocument();
    });

    const refreshButton = screen.getByText('Refresh');
    fireEvent.click(refreshButton);

    expect(mockAnalyticsService.getSalesDashboard).toHaveBeenCalledTimes(2);
    expect(mockAnalyticsService.getEngagementDashboard).toHaveBeenCalledTimes(2);
  });

  it('handles date range change', async () => {
    render(<AnalyticsDashboard />);

    await waitFor(() => {
      expect(screen.getByText('Analytics Dashboard')).toBeInTheDocument();
    });

    // Test date range selector
    const dateRangeSelect = screen.getByDisplayValue('Last 30 days');
    fireEvent.change(dateRangeSelect, { target: { value: '7d' } });

    await waitFor(() => {
      expect(mockAnalyticsService.getSalesDashboard).toHaveBeenCalledWith(7, 'USD');
    });
  });

  it('handles currency change', async () => {
    render(<AnalyticsDashboard />);

    await waitFor(() => {
      expect(screen.getByText('Analytics Dashboard')).toBeInTheDocument();
    });

    const currencySelect = screen.getByDisplayValue('USD');
    fireEvent.change(currencySelect, { target: { value: 'EUR' } });

    await waitFor(() => {
      expect(mockAnalyticsService.getSalesDashboard).toHaveBeenCalledWith(30, 'EUR');
    });
  });

  it('displays error message when API calls fail', async () => {
    mockAnalyticsService.getSalesDashboard.mockRejectedValue(new Error('API Error'));
    mockAnalyticsService.getEngagementDashboard.mockRejectedValue(new Error('API Error'));

    render(<AnalyticsDashboard />);

    await waitFor(() => {
      expect(screen.getByText('API Error')).toBeInTheDocument();
    });

    const retryButton = screen.getByText('Try Again');
    expect(retryButton).toBeInTheDocument();
  });

  it('renders charts when data is available', async () => {
    render(<AnalyticsDashboard />);

    await waitFor(() => {
      expect(screen.getByTestId('line-chart')).toBeInTheDocument();
    });
  });

  it('renders platform breakdown and top products sections', async () => {
    render(<AnalyticsDashboard />);

    await waitFor(() => {
      expect(screen.getByText('Platform Breakdown')).toBeInTheDocument();
      expect(screen.getByText('Top Products')).toBeInTheDocument();
      expect(screen.getByText('Recent Activity')).toBeInTheDocument();
    });
  });

  it('handles platform filter changes', async () => {
    render(<AnalyticsDashboard />);

    await waitFor(() => {
      expect(screen.getByText('Analytics Dashboard')).toBeInTheDocument();
    });

    // Click on platform filter dropdown
    const platformButton = screen.getByText('All Platforms');
    fireEvent.click(platformButton);

    // Select Facebook
    const facebookOption = screen.getByText('Facebook');
    fireEvent.click(facebookOption);

    await waitFor(() => {
      expect(mockAnalyticsService.getEngagementDashboard).toHaveBeenCalledWith(
        expect.any(String),
        expect.any(String),
        ['facebook']
      );
    });
  });
});