import React, { useState } from 'react';
import { format, parseISO } from 'date-fns';
import { SaleEvent, TopPerformingPost } from '../../types/analytics';

interface RecentActivityProps {
  recentSales: SaleEvent[];
  topPosts: TopPerformingPost[];
  currency: string;
}

const RecentActivity: React.FC<RecentActivityProps> = ({
  recentSales,
  topPosts,
  currency
}) => {
  const [activeTab, setActiveTab] = useState<'sales' | 'posts'>('sales');

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

  const formatDate = (dateString: string) => {
    try {
      return format(parseISO(dateString), 'MMM dd, yyyy HH:mm');
    } catch {
      return dateString;
    }
  };

  const getPlatformColor = (platform: string) => {
    const colors: { [key: string]: string } = {
      facebook: 'bg-blue-100 text-blue-800',
      instagram: 'bg-pink-100 text-pink-800',
      facebook_marketplace: 'bg-blue-100 text-blue-800',
      etsy: 'bg-orange-100 text-orange-800',
      pinterest: 'bg-red-100 text-red-800',
      shopify: 'bg-green-100 text-green-800',
      meesho: 'bg-purple-100 text-purple-800',
      snapdeal: 'bg-yellow-100 text-yellow-800',
      indiamart: 'bg-indigo-100 text-indigo-800',
    };
    return colors[platform] || 'bg-gray-100 text-gray-800';
  };

  const getStatusColor = (status: string) => {
    const colors: { [key: string]: string } = {
      confirmed: 'bg-green-100 text-green-800',
      pending: 'bg-yellow-100 text-yellow-800',
      cancelled: 'bg-red-100 text-red-800',
      refunded: 'bg-gray-100 text-gray-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const renderRecentSales = () => {
    if (recentSales.length === 0) {
      return (
        <div className="text-center py-12">
          <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
          </svg>
          <p className="mt-2 text-gray-500">No recent sales</p>
          <p className="text-sm text-gray-400">Sales will appear here once you start selling</p>
        </div>
      );
    }

    return (
      <div className="space-y-4">
        {recentSales.slice(0, 10).map((sale) => (
          <div
            key={sale.id}
            className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <div className="flex items-center space-x-4 flex-1">
              <div className="flex-shrink-0">
                <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
                  <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
                  </svg>
                </div>
              </div>
              
              <div className="flex-1 min-w-0">
                <div className="flex items-center space-x-2">
                  <h4 className="text-sm font-medium text-gray-900 truncate">
                    {sale.product_title || `Order #${sale.order_id}`}
                  </h4>
                  <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getPlatformColor(sale.platform)}`}>
                    {formatPlatformName(sale.platform)}
                  </span>
                  <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(sale.status)}`}>
                    {sale.status.charAt(0).toUpperCase() + sale.status.slice(1)}
                  </span>
                </div>
                <p className="text-sm text-gray-500 mt-1">
                  {formatDate(sale.occurred_at)}
                </p>
              </div>
            </div>

            <div className="text-right">
              <p className="text-lg font-semibold text-gray-900">
                {formatCurrency(sale.amount)}
              </p>
              <p className="text-sm text-gray-500">
                {sale.currency}
              </p>
            </div>
          </div>
        ))}
      </div>
    );
  };

  const renderTopPosts = () => {
    if (topPosts.length === 0) {
      return (
        <div className="text-center py-12">
          <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
          </svg>
          <p className="mt-2 text-gray-500">No top performing posts</p>
          <p className="text-sm text-gray-400">Posts will appear here once you start getting engagement</p>
        </div>
      );
    }

    return (
      <div className="space-y-4">
        {topPosts.slice(0, 10).map((post, index) => (
          <div
            key={post.id}
            className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <div className="flex items-center space-x-4 flex-1">
              <div className="flex-shrink-0">
                <div className="w-10 h-10 bg-pink-100 rounded-full flex items-center justify-center">
                  <svg className="w-5 h-5 text-pink-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                  </svg>
                </div>
              </div>
              
              <div className="flex-1 min-w-0">
                <div className="flex items-center space-x-2">
                  <h4 className="text-sm font-medium text-gray-900 truncate">
                    {post.title}
                  </h4>
                  <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getPlatformColor(post.platform)}`}>
                    {formatPlatformName(post.platform)}
                  </span>
                </div>
                <div className="flex items-center space-x-4 mt-1 text-sm text-gray-500">
                  <span>{formatNumber(post.likes)} likes</span>
                  <span>{formatNumber(post.shares)} shares</span>
                  <span>{formatNumber(post.comments)} comments</span>
                  {post.engagement_rate && (
                    <span>{post.engagement_rate.toFixed(1)}% engagement</span>
                  )}
                </div>
                <p className="text-sm text-gray-500 mt-1">
                  {formatDate(post.published_at)}
                </p>
              </div>
            </div>

            <div className="text-right">
              <p className="text-lg font-semibold text-gray-900">
                {formatNumber(post.views)}
              </p>
              <p className="text-sm text-gray-500">
                Views
              </p>
            </div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900">Recent Activity</h3>
        <div className="flex space-x-1 bg-gray-100 rounded-lg p-1">
          <button
            onClick={() => setActiveTab('sales')}
            className={`px-3 py-1 text-sm rounded-md transition-colors ${
              activeTab === 'sales'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Recent Sales ({recentSales.length})
          </button>
          <button
            onClick={() => setActiveTab('posts')}
            className={`px-3 py-1 text-sm rounded-md transition-colors ${
              activeTab === 'posts'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Top Posts ({topPosts.length})
          </button>
        </div>
      </div>

      {activeTab === 'sales' && renderRecentSales()}
      {activeTab === 'posts' && renderTopPosts()}
    </div>
  );
};

export default RecentActivity;