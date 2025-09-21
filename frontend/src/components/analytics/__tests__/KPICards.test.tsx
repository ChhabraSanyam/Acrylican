import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import KPICards from '../KPICards';
import { SalesDashboardData, EngagementDashboardData } from '../../../types/analytics';

const mockSalesData: SalesDashboardData = {
  overall_metrics: {
    total_revenue: 15000,
    total_orders: 75,
    average_order_value: 200,
    total_commission: 1500,
    net_revenue: 13500,
    currency: 'USD',
    period_start: '2024-01-01T00:00:00',
    period_end: '2024-01-31T23:59:59'
  },
  platform_breakdown: [],
  top_products: [],
  recent_sales: [],
  sales_trend: []
};

const mockEngagementData: EngagementDashboardData = {
  total_engagement: {
    likes: 2500,
    shares: 500,
    comments: 300,
    views: 12000
  },
  engagement_by_platform: [],
  engagement_trend: [],
  top_performing_posts: [],
  recent_metrics: [],
  average_engagement_rate: 6.8,
  total_reach: 25000
};

describe('KPICards', () => {
  it('renders all KPI cards with correct titles', () => {
    render(<KPICards salesData={mockSalesData} engagementData={mockEngagementData} currency="USD" />);

    expect(screen.getByText('Total Revenue')).toBeInTheDocument();
    expect(screen.getByText('Total Orders')).toBeInTheDocument();
    expect(screen.getByText('Average Order Value')).toBeInTheDocument();
    expect(screen.getByText('Total Engagement')).toBeInTheDocument();
    expect(screen.getByText('Total Reach')).toBeInTheDocument();
    expect(screen.getByText('Engagement Rate')).toBeInTheDocument();
  });

  it('displays correct sales values', () => {
    render(<KPICards salesData={mockSalesData} engagementData={mockEngagementData} currency="USD" />);

    expect(screen.getByText('$15,000')).toBeInTheDocument(); // Total Revenue
    expect(screen.getByText('75')).toBeInTheDocument(); // Total Orders
    expect(screen.getByText('$200')).toBeInTheDocument(); // Average Order Value
  });

  it('displays correct engagement values', () => {
    render(<KPICards salesData={mockSalesData} engagementData={mockEngagementData} currency="USD" />);

    expect(screen.getByText('3.3K')).toBeInTheDocument(); // Total Engagement (2500 + 500 + 300 = 3300)
    expect(screen.getByText('25K')).toBeInTheDocument(); // Total Reach
    expect(screen.getByText('6.8%')).toBeInTheDocument(); // Engagement Rate
  });

  it('handles null sales data gracefully', () => {
    render(<KPICards salesData={null} engagementData={mockEngagementData} currency="USD" />);

    expect(screen.getByText('$0')).toBeInTheDocument(); // Total Revenue fallback
    expect(screen.getByText('0')).toBeInTheDocument(); // Total Orders fallback
  });

  it('handles null engagement data gracefully', () => {
    render(<KPICards salesData={mockSalesData} engagementData={null} currency="USD" />);

    expect(screen.getByText('0')).toBeInTheDocument(); // Total Engagement fallback
    expect(screen.getByText('0%')).toBeInTheDocument(); // Engagement Rate fallback
  });

  it('formats currency correctly for different currencies', () => {
    render(<KPICards salesData={mockSalesData} engagementData={mockEngagementData} currency="EUR" />);

    expect(screen.getByText('€15,000')).toBeInTheDocument(); // Total Revenue in EUR
    expect(screen.getByText('€200')).toBeInTheDocument(); // Average Order Value in EUR
  });

  it('formats large numbers correctly', () => {
    const largeSalesData: SalesDashboardData = {
      ...mockSalesData,
      overall_metrics: {
        ...mockSalesData.overall_metrics,
        total_revenue: 1500000, // 1.5M
        total_orders: 7500
      }
    };

    const largeEngagementData: EngagementDashboardData = {
      ...mockEngagementData,
      total_engagement: {
        likes: 1200000, // 1.2M
        shares: 300000, // 300K
        comments: 150000, // 150K
        views: 5000000 // 5M
      },
      total_reach: 2500000 // 2.5M
    };

    render(<KPICards salesData={largeSalesData} engagementData={largeEngagementData} currency="USD" />);

    expect(screen.getByText('$1,500,000')).toBeInTheDocument(); // Total Revenue
    expect(screen.getByText('1.7M')).toBeInTheDocument(); // Total Engagement (1.2M + 300K + 150K = 1.65M)
    expect(screen.getByText('2.5M')).toBeInTheDocument(); // Total Reach
  });

  it('renders all KPI card icons', () => {
    const { container } = render(<KPICards salesData={mockSalesData} engagementData={mockEngagementData} currency="USD" />);

    // Check that SVG icons are present (by checking for SVG elements)
    const svgElements = container.querySelectorAll('svg');
    expect(svgElements.length).toBeGreaterThan(0);
  });

  it('applies correct color classes to KPI cards', () => {
    const { container } = render(
      <KPICards salesData={mockSalesData} engagementData={mockEngagementData} currency="USD" />
    );

    // Check for color classes
    expect(container.querySelector('.bg-green-500')).toBeInTheDocument(); // Total Revenue
    expect(container.querySelector('.bg-blue-500')).toBeInTheDocument(); // Total Orders
    expect(container.querySelector('.bg-purple-500')).toBeInTheDocument(); // Average Order Value
    expect(container.querySelector('.bg-pink-500')).toBeInTheDocument(); // Total Engagement
    expect(container.querySelector('.bg-indigo-500')).toBeInTheDocument(); // Total Reach
    expect(container.querySelector('.bg-yellow-500')).toBeInTheDocument(); // Engagement Rate
  });

  it('handles zero values correctly', () => {
    const zeroSalesData: SalesDashboardData = {
      ...mockSalesData,
      overall_metrics: {
        ...mockSalesData.overall_metrics,
        total_revenue: 0,
        total_orders: 0,
        average_order_value: 0
      }
    };

    const zeroEngagementData: EngagementDashboardData = {
      ...mockEngagementData,
      total_engagement: {
        likes: 0,
        shares: 0,
        comments: 0,
        views: 0
      },
      total_reach: 0,
      average_engagement_rate: 0
    };

    render(<KPICards salesData={zeroSalesData} engagementData={zeroEngagementData} currency="USD" />);

    expect(screen.getAllByText('$0')).toHaveLength(2); // Total Revenue and Average Order Value
    expect(screen.getAllByText('0')).toHaveLength(2); // Total Orders and Total Engagement
    expect(screen.getByText('0%')).toBeInTheDocument(); // Engagement Rate
  });
});