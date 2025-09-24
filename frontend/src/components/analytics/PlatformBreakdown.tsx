import React, { useState, useEffect } from 'react';
import { Chart as ChartJS, ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement, LineElement, PointElement } from 'chart.js';
import { Doughnut, Bar } from 'react-chartjs-2';
import { PlatformSalesBreakdown, PlatformEngagementData, PlatformPerformanceMetrics, TopPerformingProduct, PlatformROIAnalysis } from '../../types/analytics';
import analyticsService from '../../services/analytics';
import LoadingSpinner from '../common/LoadingSpinner';
import ErrorMessage from '../common/ErrorMessage';

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement, LineElement, PointElement);

interface PlatformBreakdownProps {
  salesData: PlatformSalesBreakdown[];
  engagementData: PlatformEngagementData[];
  currency: string;
  startDate?: string;
  endDate?: string;
  platforms?: string[];
}

const PlatformBreakdown: React.FC<PlatformBreakdownProps> = ({
  salesData,
  engagementData,
  currency,
  startDate,
  endDate,
  platforms
}) => {
  const [activeTab, setActiveTab] = useState<'sales' | 'engagement' | 'performance' | 'roi'>('sales');
  const [performanceData, setPerformanceData] = useState<PlatformPerformanceMetrics[]>([]);
  const [topProducts, setTopProducts] = useState<TopPerformingProduct[]>([]);
  const [roiAnalysis, setROIAnalysis] = useState<PlatformROIAnalysis[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (activeTab === 'performance' || activeTab === 'roi') {
      fetchPerformanceData();
    }
  }, [activeTab, startDate, endDate, platforms, currency]);

  const fetchPerformanceData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const [performanceResponse, topProductsResponse, roiResponse] = await Promise.all([
        analyticsService.getPlatformPerformanceBreakdown(startDate, endDate, platforms, currency),
        analyticsService.getTopPerformingProducts(startDate, endDate, platforms, 10, currency),
        analyticsService.getPlatformROIAnalysis(startDate, endDate, platforms, currency)
      ]);

      setPerformanceData(performanceResponse.platforms || []);
      setTopProducts(topProductsResponse.products || []);
      setROIAnalysis(roiResponse.roi_analysis || []);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch performance data');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatNumber = (num: number) => {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M';
    }
    if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
  };

  const formatPlatformName = (platform: string) => {
    return platform
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const platformColors = [
    '#3B82F6', // Blue
    '#EF4444', // Red
    '#10B981', // Green
    '#F59E0B', // Yellow
    '#8B5CF6', // Purple
    '#EC4899', // Pink
    '#6B7280', // Gray
    '#14B8A6', // Teal
    '#F97316', // Orange
    '#84CC16', // Lime
  ];

  const getSalesChartData = () => {
    if (salesData.length === 0) return null;

    return {
      labels: salesData.map(item => formatPlatformName(item.platform)),
      datasets: [
        {
          data: salesData.map(item => item.total_revenue),
          backgroundColor: platformColors.slice(0, salesData.length),
          borderWidth: 2,
          borderColor: '#ffffff',
        },
      ],
    };
  };

  const getEngagementChartData = () => {
    if (engagementData.length === 0) return null;

    const totalEngagement = engagementData.map(item => 
      item.likes + item.shares + item.comments
    );

    return {
      labels: engagementData.map(item => formatPlatformName(item.platform)),
      datasets: [
        {
          data: totalEngagement,
          backgroundColor: platformColors.slice(0, engagementData.length),
          borderWidth: 2,
          borderColor: '#ffffff',
        },
      ],
    };
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom' as const,
        labels: {
          padding: 20,
          usePointStyle: true,
        },
      },
      tooltip: {
        callbacks: {
          label: function(context: any) {
            const label = context.label || '';
            const value = context.parsed;
            
            if (activeTab === 'sales') {
              return `${label}: ${formatCurrency(value)}`;
            } else {
              return `${label}: ${formatNumber(value)} interactions`;
            }
          }
        }
      }
    },
  };

  const renderSalesTable = () => (
    <div className="mt-6">
      <div className="overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Platform
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Revenue
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Orders
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                AOV
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {salesData.map((item, index) => (
              <tr key={item.platform}>
                <td className="px-4 py-3 whitespace-nowrap">
                  <div className="flex items-center">
                    <div
                      className="w-3 h-3 rounded-full mr-3"
                      style={{ backgroundColor: platformColors[index] }}
                    />
                    <span className="text-sm font-medium text-gray-900">
                      {formatPlatformName(item.platform)}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                  {formatCurrency(item.total_revenue)}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                  {item.total_orders.toLocaleString()}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                  {formatCurrency(item.average_order_value)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );

  const renderEngagementTable = () => (
    <div className="mt-6">
      <div className="overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Platform
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Likes
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Shares
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Comments
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Views
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {engagementData.map((item, index) => (
              <tr key={item.platform}>
                <td className="px-4 py-3 whitespace-nowrap">
                  <div className="flex items-center">
                    <div
                      className="w-3 h-3 rounded-full mr-3"
                      style={{ backgroundColor: platformColors[index] }}
                    />
                    <span className="text-sm font-medium text-gray-900">
                      {formatPlatformName(item.platform)}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                  {formatNumber(item.likes)}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                  {formatNumber(item.shares)}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                  {formatNumber(item.comments)}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                  {formatNumber(item.views)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );

  const getPerformanceScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600 bg-green-100';
    if (score >= 60) return 'text-yellow-600 bg-yellow-100';
    if (score >= 40) return 'text-orange-600 bg-orange-100';
    return 'text-red-600 bg-red-100';
  };

  const getTrendIcon = (direction: 'up' | 'down' | 'stable') => {
    switch (direction) {
      case 'up':
        return (
          <svg className="w-4 h-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 17l9.2-9.2M17 17V7H7" />
          </svg>
        );
      case 'down':
        return (
          <svg className="w-4 h-4 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 7l-9.2 9.2M7 7v10h10" />
          </svg>
        );
      default:
        return (
          <svg className="w-4 h-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
          </svg>
        );
    }
  };

  const getROICategoryColor = (category: string) => {
    switch (category) {
      case 'excellent': return 'text-green-700 bg-green-100';
      case 'good': return 'text-blue-700 bg-blue-100';
      case 'average': return 'text-yellow-700 bg-yellow-100';
      case 'poor': return 'text-red-700 bg-red-100';
      default: return 'text-gray-700 bg-gray-100';
    }
  };

  const renderPerformanceAnalysis = () => (
    <div className="space-y-6">
      {/* Performance Comparison Chart */}
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="text-md font-medium text-gray-900 mb-4">Platform Performance Comparison</h4>
        {performanceData.length > 0 ? (
          <div className="h-64">
            <Bar
              data={{
                labels: performanceData.map(p => formatPlatformName(p.platform)),
                datasets: [
                  {
                    label: 'Performance Score',
                    data: performanceData.map(p => p.performance_score),
                    backgroundColor: 'rgba(59, 130, 246, 0.6)',
                    borderColor: 'rgba(59, 130, 246, 1)',
                    borderWidth: 1,
                  },
                  {
                    label: 'Revenue per Post',
                    data: performanceData.map(p => p.roi_metrics.revenue_per_post),
                    backgroundColor: 'rgba(16, 185, 129, 0.6)',
                    borderColor: 'rgba(16, 185, 129, 1)',
                    borderWidth: 1,
                    yAxisID: 'y1',
                  }
                ]
              }}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                  y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: { display: true, text: 'Performance Score' }
                  },
                  y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: { display: true, text: 'Revenue per Post ($)' },
                    grid: { drawOnChartArea: false }
                  }
                }
              }}
            />
          </div>
        ) : (
          <div className="h-32 flex items-center justify-center text-gray-500">
            No performance data available
          </div>
        )}
      </div>

      {/* Platform Performance Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {performanceData.map((platform, index) => (
          <div key={platform.platform} className="bg-white border rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center">
                <div
                  className="w-3 h-3 rounded-full mr-2"
                  style={{ backgroundColor: platformColors[index] }}
                />
                <h5 className="font-medium text-gray-900">
                  {formatPlatformName(platform.platform)}
                </h5>
              </div>
              <div className="flex items-center space-x-2">
                {getTrendIcon(platform.trend_direction)}
                <span className={`text-xs px-2 py-1 rounded-full ${getPerformanceScoreColor(platform.performance_score)}`}>
                  {platform.performance_score}
                </span>
              </div>
            </div>
            
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Revenue:</span>
                <span className="font-medium">{formatCurrency(platform.sales_metrics.total_revenue)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Orders:</span>
                <span className="font-medium">{platform.sales_metrics.total_orders}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Engagement Rate:</span>
                <span className="font-medium">{platform.engagement_metrics.engagement_rate.toFixed(1)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Revenue/Post:</span>
                <span className="font-medium">{formatCurrency(platform.roi_metrics.revenue_per_post)}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Top Products by Platform */}
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="text-md font-medium text-gray-900 mb-4">Top Performing Products</h4>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Product</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Revenue</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Orders</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Best Platform</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Score</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {topProducts.slice(0, 5).map((product) => (
                <tr key={product.id}>
                  <td className="px-4 py-3 text-sm font-medium text-gray-900">{product.title}</td>
                  <td className="px-4 py-3 text-sm text-gray-900">{formatCurrency(product.total_revenue)}</td>
                  <td className="px-4 py-3 text-sm text-gray-900">{product.total_orders}</td>
                  <td className="px-4 py-3 text-sm text-gray-900">{formatPlatformName(product.best_platform)}</td>
                  <td className="px-4 py-3 text-sm">
                    <span className={`px-2 py-1 rounded-full text-xs ${getPerformanceScoreColor(product.performance_score)}`}>
                      {product.performance_score}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );

  const renderROIAnalysis = () => (
    <div className="space-y-6">
      {/* ROI Overview Chart */}
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="text-md font-medium text-gray-900 mb-4">ROI by Platform</h4>
        {roiAnalysis.length > 0 ? (
          <div className="h-64">
            <Bar
              data={{
                labels: roiAnalysis.map(roi => formatPlatformName(roi.platform)),
                datasets: [
                  {
                    label: 'ROI %',
                    data: roiAnalysis.map(roi => roi.roi_percentage),
                    backgroundColor: roiAnalysis.map(roi => {
                      if (roi.roi_percentage >= 200) return 'rgba(16, 185, 129, 0.6)';
                      if (roi.roi_percentage >= 100) return 'rgba(59, 130, 246, 0.6)';
                      if (roi.roi_percentage >= 50) return 'rgba(245, 158, 11, 0.6)';
                      return 'rgba(239, 68, 68, 0.6)';
                    }),
                    borderColor: roiAnalysis.map(roi => {
                      if (roi.roi_percentage >= 200) return 'rgba(16, 185, 129, 1)';
                      if (roi.roi_percentage >= 100) return 'rgba(59, 130, 246, 1)';
                      if (roi.roi_percentage >= 50) return 'rgba(245, 158, 11, 1)';
                      return 'rgba(239, 68, 68, 1)';
                    }),
                    borderWidth: 1,
                  }
                ]
              }}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                  y: {
                    beginAtZero: true,
                    title: { display: true, text: 'ROI Percentage (%)' }
                  }
                },
                plugins: {
                  tooltip: {
                    callbacks: {
                      label: function(context: any) {
                        return `ROI: ${context.parsed.y.toFixed(1)}%`;
                      }
                    }
                  }
                }
              }}
            />
          </div>
        ) : (
          <div className="h-32 flex items-center justify-center text-gray-500">
            No ROI data available
          </div>
        )}
      </div>

      {/* ROI Analysis Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {roiAnalysis.map((roi, index) => (
          <div key={roi.platform} className="bg-white border rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center">
                <div
                  className="w-3 h-3 rounded-full mr-2"
                  style={{ backgroundColor: platformColors[index] }}
                />
                <h5 className="font-medium text-gray-900">
                  {formatPlatformName(roi.platform)}
                </h5>
              </div>
              <span className={`text-xs px-2 py-1 rounded-full ${getROICategoryColor(roi.roi_category)}`}>
                {roi.roi_category}
              </span>
            </div>
            
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-gray-600">ROI:</span>
                <span className={`font-bold text-lg ${roi.roi_percentage >= 100 ? 'text-green-600' : roi.roi_percentage >= 50 ? 'text-yellow-600' : 'text-red-600'}`}>
                  {roi.roi_percentage.toFixed(1)}%
                </span>
              </div>
              
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Investment:</span>
                  <span className="font-medium">{formatCurrency(roi.investment_metrics.total_investment)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Return:</span>
                  <span className="font-medium">{formatCurrency(roi.return_metrics.total_return)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Net Revenue:</span>
                  <span className="font-medium">{formatCurrency(roi.return_metrics.net_revenue)}</span>
                </div>
              </div>

              {roi.recommendations.length > 0 && (
                <div className="mt-3 pt-3 border-t border-gray-200">
                  <p className="text-xs text-gray-600 mb-1">Recommendations:</p>
                  <ul className="text-xs text-gray-700 space-y-1">
                    {roi.recommendations.slice(0, 2).map((rec, idx) => (
                      <li key={idx} className="flex items-start">
                        <span className="text-blue-500 mr-1">•</span>
                        <span>{rec}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  const salesChartData = getSalesChartData();
  const engagementChartData = getEngagementChartData();

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900">Platform Performance Analysis</h3>
        <div className="flex space-x-1 bg-gray-100 rounded-lg p-1">
          <button
            onClick={() => setActiveTab('sales')}
            className={`px-3 py-1 text-sm rounded-md transition-colors ${
              activeTab === 'sales'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Sales
          </button>
          <button
            onClick={() => setActiveTab('engagement')}
            className={`px-3 py-1 text-sm rounded-md transition-colors ${
              activeTab === 'engagement'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Engagement
          </button>
          <button
            onClick={() => setActiveTab('performance')}
            className={`px-3 py-1 text-sm rounded-md transition-colors ${
              activeTab === 'performance'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Performance
          </button>
          <button
            onClick={() => setActiveTab('roi')}
            className={`px-3 py-1 text-sm rounded-md transition-colors ${
              activeTab === 'roi'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            ROI Analysis
          </button>
        </div>
      </div>

      {activeTab === 'sales' && (
        <>
          {salesChartData ? (
            <>
              <div className="h-64 mb-4">
                <Doughnut data={salesChartData} options={chartOptions} />
              </div>
              {renderSalesTable()}
            </>
          ) : (
            <div className="h-64 flex items-center justify-center text-gray-500">
              <div className="text-center">
                <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                <p className="mt-2">No sales data by platform</p>
              </div>
            </div>
          )}
        </>
      )}

      {activeTab === 'engagement' && (
        <>
          {engagementChartData ? (
            <>
              <div className="h-64 mb-4">
                <Doughnut data={engagementChartData} options={chartOptions} />
              </div>
              {renderEngagementTable()}
            </>
          ) : (
            <div className="h-64 flex items-center justify-center text-gray-500">
              <div className="text-center">
                <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                </svg>
                <p className="mt-2">No engagement data by platform</p>
              </div>
            </div>
          )}
        </>
      )}

      {activeTab === 'performance' && (
        <>
          {loading ? (
            <div className="h-64 flex items-center justify-center">
              <LoadingSpinner />
            </div>
          ) : error ? (
            <div className="h-64 flex items-center justify-center">
              <ErrorMessage message={error} />
            </div>
          ) : (
            renderPerformanceAnalysis()
          )}
        </>
      )}

      {activeTab === 'roi' && (
        <>
          {loading ? (
            <div className="h-64 flex items-center justify-center">
              <LoadingSpinner />
            </div>
          ) : error ? (
            <div className="h-64 flex items-center justify-center">
              <ErrorMessage message={error} />
            </div>
          ) : (
            renderROIAnalysis()
          )}
        </>
      )}
    </div>
  );
};

export default PlatformBreakdown;