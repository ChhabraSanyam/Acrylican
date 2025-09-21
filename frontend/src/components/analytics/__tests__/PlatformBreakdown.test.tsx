import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import PlatformBreakdown from '../PlatformBreakdown';
import analyticsService from '../../../services/analytics';

// Mock the analytics service
jest.mock('../../../services/analytics', () => ({
  __esModule: true,
  default: {
    getPlatformPerformanceBreakdown: jest.fn(),
    getTopPerformingProducts: jest.fn(),
    getPlatformROIAnalysis: jest.fn(),
  },
}));

// Mock Chart.js components
jest.mock('react-chartjs-2', () => ({
  Doughnut: ({ data, options }: any) => (
    <div data-testid="doughnut-chart" data-chart-data={JSON.stringify(data)} />
  ),
  Bar: ({ data, options }: any) => (
    <div data-testid="bar-chart" data-chart-data={JSON.stringify(data)} />
  ),
  Line: ({ data, options }: any) => (
    <div data-testid="line-chart" data-chart-data={JSON.stringify(data)} />
  ),
}));

// Mock loading and error components
jest.mock('../../common/LoadingSpinner', () => {
  return function LoadingSpinner() {
    return <div data-testid="loading-spinner">Loading...</div>;
  };
});

jest.mock('../../common/ErrorMessage', () => {
  return function ErrorMessage({ message }: { message: string }) {
    return <div data-testid="error-message">{message}</div>;
  };
});

const mockSalesData = [
  {
    platform: 'facebook',
    total_revenue: 1500,
    total_orders: 15,
    average_order_value: 100,
    commission_rate: 0.05,
    total_commission: 75,
    net_revenue: 1425,
    top_products: [
      { id: '1', title: 'Handmade Vase', revenue: 500, orders: 5 }
    ]
  },
  {
    platform: 'instagram',
    total_revenue: 1200,
    total_orders: 12,
    average_order_value: 100,
    commission_rate: 0.03,
    total_commission: 36,
    net_revenue: 1164,
    top_products: [
      { id: '2', title: 'Ceramic Bowl', revenue: 400, orders: 4 }
    ]
  }
];

const mockEngagementData = [
  {
    platform: 'facebook',
    likes: 150,
    shares: 25,
    comments: 30,
    views: 1000,
    reach: 800,
    engagement_rate: 25.6
  },
  {
    platform: 'instagram',
    likes: 200,
    shares: 15,
    comments: 40,
    views: 1200,
    reach: 900,
    engagement_rate: 28.3
  }
];

const mockPerformanceData = {
  platforms: [
    {
      platform: 'facebook',
      sales_metrics: {
        total_revenue: 1500,
        total_orders: 15,
        average_order_value: 100,
        commission_rate: 0.05,
        total_commission: 75,
        net_revenue: 1425,
        conversion_rate: 1.875
      },
      engagement_metrics: {
        likes: 150,
        shares: 25,
        comments: 30,
        views: 1000,
        reach: 800,
        engagement_rate: 25.6,
        total_posts: 5
      },
      roi_metrics: {
        revenue_per_post: 300,
        engagement_per_post: 41,
        cost_per_acquisition: 10,
        return_on_investment: 150
      },
      top_products: [
        { id: '1', title: 'Handmade Vase', revenue: 500, orders: 5 }
      ],
      performance_score: 85,
      trend_direction: 'up' as const,
      trend_percentage: 15.5
    }
  ]
};

const mockTopProducts = {
  products: [
    {
      id: '1',
      title: 'Handmade Vase',
      total_revenue: 900,
      total_orders: 9,
      total_engagement: 150,
      platforms: [
        {
          platform: 'facebook',
          revenue: 500,
          orders: 5,
          engagement: 80,
          performance_score: 85
        },
        {
          platform: 'instagram',
          revenue: 400,
          orders: 4,
          engagement: 70,
          performance_score: 78
        }
      ],
      best_platform: 'facebook',
      performance_score: 85
    }
  ]
};

const mockROIAnalysis = {
  roi_analysis: [
    {
      platform: 'facebook',
      investment_metrics: {
        time_spent_hours: 10,
        advertising_cost: 0,
        content_creation_cost: 50,
        total_investment: 300
      },
      return_metrics: {
        gross_revenue: 1500,
        net_revenue: 1425,
        engagement_value: 25,
        total_return: 1450
      },
      roi_percentage: 383.3,
      roi_category: 'excellent' as const,
      recommendations: [
        'Excellent ROI on facebook! Consider increasing investment here.',
        'Scale successful content strategies to maximize returns.'
      ]
    }
  ]
};

describe('PlatformBreakdown', () => {
  const defaultProps = {
    salesData: mockSalesData,
    engagementData: mockEngagementData,
    currency: 'USD',
    startDate: '2024-01-01T00:00:00',
    endDate: '2024-01-31T23:59:59',
    platforms: ['facebook', 'instagram']
  };

  beforeEach(() => {
    jest.clearAllMocks();
    (analyticsService.getPlatformPerformanceBreakdown as jest.Mock).mockResolvedValue(mockPerformanceData);
    (analyticsService.getTopPerformingProducts as jest.Mock).mockResolvedValue(mockTopProducts);
    (analyticsService.getPlatformROIAnalysis as jest.Mock).mockResolvedValue(mockROIAnalysis);
  });

  it('renders with sales tab active by default', () => {
    render(<PlatformBreakdown {...defaultProps} />);
    
    expect(screen.getByText('Platform Performance Analysis')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Sales' })).toHaveClass('bg-white');
    expect(screen.getByTestId('doughnut-chart')).toBeInTheDocument();
  });

  it('switches between tabs correctly', async () => {
    render(<PlatformBreakdown {...defaultProps} />);
    
    // Switch to engagement tab
    fireEvent.click(screen.getByRole('button', { name: 'Engagement' }));
    expect(screen.getByRole('button', { name: 'Engagement' })).toHaveClass('bg-white');
    
    // Switch to performance tab
    fireEvent.click(screen.getByRole('button', { name: 'Performance' }));
    expect(screen.getByRole('button', { name: 'Performance' })).toHaveClass('bg-white');
    
    // Should show loading initially
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
    
    // Wait for data to load
    await waitFor(() => {
      expect(screen.getByText('Platform Performance Comparison')).toBeInTheDocument();
    });
  });

  it('displays sales data correctly', () => {
    render(<PlatformBreakdown {...defaultProps} />);
    
    // Check if platform names are displayed
    expect(screen.getByText('Facebook')).toBeInTheDocument();
    expect(screen.getByText('Instagram')).toBeInTheDocument();
    
    // Check if revenue values are displayed
    expect(screen.getByText('$1,500')).toBeInTheDocument();
    expect(screen.getByText('$1,200')).toBeInTheDocument();
  });

  it('displays engagement data when engagement tab is selected', () => {
    render(<PlatformBreakdown {...defaultProps} />);
    
    fireEvent.click(screen.getByRole('button', { name: 'Engagement' }));
    
    // Check if engagement metrics are displayed
    expect(screen.getByText('150')).toBeInTheDocument(); // Facebook likes
    expect(screen.getByText('200')).toBeInTheDocument(); // Instagram likes
  });

  it('fetches and displays performance data when performance tab is selected', async () => {
    render(<PlatformBreakdown {...defaultProps} />);
    
    fireEvent.click(screen.getByRole('button', { name: 'Performance' }));
    
    await waitFor(() => {
      expect(analyticsService.getPlatformPerformanceBreakdown).toHaveBeenCalledWith(
        '2024-01-01T00:00:00',
        '2024-01-31T23:59:59',
        ['facebook', 'instagram'],
        'USD'
      );
    });
    
    await waitFor(() => {
      expect(screen.getByText('Platform Performance Comparison')).toBeInTheDocument();
      expect(screen.getByText('Top Performing Products')).toBeInTheDocument();
    });
  });

  it('fetches and displays ROI data when ROI tab is selected', async () => {
    render(<PlatformBreakdown {...defaultProps} />);
    
    fireEvent.click(screen.getByRole('button', { name: 'ROI Analysis' }));
    
    await waitFor(() => {
      expect(analyticsService.getPlatformROIAnalysis).toHaveBeenCalledWith(
        '2024-01-01T00:00:00',
        '2024-01-31T23:59:59',
        ['facebook', 'instagram'],
        'USD'
      );
    });
    
    await waitFor(() => {
      expect(screen.getByText('ROI by Platform')).toBeInTheDocument();
    });
  });

  it('handles API errors gracefully', async () => {
    const errorMessage = 'Failed to fetch performance data';
    (analyticsService.getPlatformPerformanceBreakdown as jest.Mock).mockRejectedValue(new Error(errorMessage));
    
    render(<PlatformBreakdown {...defaultProps} />);
    
    fireEvent.click(screen.getByRole('button', { name: 'Performance' }));
    
    await waitFor(() => {
      expect(screen.getByTestId('error-message')).toBeInTheDocument();
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });
  });

  it('displays empty state when no data is available', () => {
    const emptyProps = {
      ...defaultProps,
      salesData: [],
      engagementData: []
    };
    
    render(<PlatformBreakdown {...emptyProps} />);
    
    expect(screen.getByText('No sales data by platform')).toBeInTheDocument();
  });

  it('formats currency correctly', () => {
    const euroProps = {
      ...defaultProps,
      currency: 'EUR'
    };
    
    render(<PlatformBreakdown {...euroProps} />);
    
    // Should format as EUR - the component uses Intl.NumberFormat
    expect(screen.getByText('€1,500')).toBeInTheDocument();
  });

  it('displays performance scores and trends correctly', async () => {
    render(<PlatformBreakdown {...defaultProps} />);
    
    fireEvent.click(screen.getByRole('button', { name: 'Performance' }));
    
    await waitFor(() => {
      expect(screen.getAllByText('85')).toHaveLength(2); // Performance score appears in multiple places
      expect(screen.getByText('$300')).toBeInTheDocument(); // Revenue per post
    });
  });

  it('displays ROI categories and recommendations', async () => {
    render(<PlatformBreakdown {...defaultProps} />);
    
    fireEvent.click(screen.getByRole('button', { name: 'ROI Analysis' }));
    
    await waitFor(() => {
      expect(screen.getByText('excellent')).toBeInTheDocument(); // ROI category
      expect(screen.getByText('383.3%')).toBeInTheDocument(); // ROI percentage
      expect(screen.getByText('Recommendations:')).toBeInTheDocument();
    });
  });

  it('displays top products table correctly', async () => {
    render(<PlatformBreakdown {...defaultProps} />);
    
    fireEvent.click(screen.getByRole('button', { name: 'Performance' }));
    
    await waitFor(() => {
      expect(screen.getByText('Handmade Vase')).toBeInTheDocument();
      expect(screen.getAllByText('Facebook')).toHaveLength(2); // Appears in platform card and table
    });
  });

  it('handles platform name formatting correctly', () => {
    const platformWithUnderscore = {
      ...defaultProps,
      salesData: [
        {
          ...mockSalesData[0],
          platform: 'facebook_marketplace'
        }
      ]
    };
    
    render(<PlatformBreakdown {...platformWithUnderscore} />);
    
    expect(screen.getByText('Facebook Marketplace')).toBeInTheDocument();
  });

  it('refetches data when props change', async () => {
    const { rerender } = render(<PlatformBreakdown {...defaultProps} />);
    
    fireEvent.click(screen.getByRole('button', { name: 'Performance' }));
    
    await waitFor(() => {
      expect(analyticsService.getPlatformPerformanceBreakdown).toHaveBeenCalledTimes(1);
    });
    
    // Change props
    const newProps = {
      ...defaultProps,
      startDate: '2024-02-01T00:00:00',
      endDate: '2024-02-29T23:59:59'
    };
    
    rerender(<PlatformBreakdown {...newProps} />);
    
    await waitFor(() => {
      expect(analyticsService.getPlatformPerformanceBreakdown).toHaveBeenCalledTimes(2);
      expect(analyticsService.getPlatformPerformanceBreakdown).toHaveBeenLastCalledWith(
        '2024-02-01T00:00:00',
        '2024-02-29T23:59:59',
        ['facebook', 'instagram'],
        'USD'
      );
    });
  });
});