import React from 'react';
import { ProductSalesData } from '../../types/analytics';

interface TopProductsProps {
  products: ProductSalesData[];
  currency: string;
}

const TopProducts: React.FC<TopProductsProps> = ({ products, currency }) => {
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatPlatformName = (platform: string) => {
    return platform
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
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

  const getRankIcon = (index: number) => {
    const icons = [
      // 1st place - Gold trophy
      <svg className="w-5 h-5 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M10 2L7.5 7H2l4.5 3.5L5 16l5-3.5L15 16l-1.5-5.5L18 7h-5.5L10 2z" clipRule="evenodd" />
      </svg>,
      // 2nd place - Silver medal
      <svg className="w-5 h-5 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-8.293l-3-3a1 1 0 00-1.414 0l-3 3a1 1 0 001.414 1.414L9 9.414V13a1 1 0 102 0V9.414l1.293 1.293a1 1 0 001.414-1.414z" clipRule="evenodd" />
      </svg>,
      // 3rd place - Bronze medal
      <svg className="w-5 h-5 text-amber-600" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-8.293l-3-3a1 1 0 00-1.414 0l-3 3a1 1 0 001.414 1.414L9 9.414V13a1 1 0 102 0V9.414l1.293 1.293a1 1 0 001.414-1.414z" clipRule="evenodd" />
      </svg>
    ];
    
    return icons[index] || (
      <span className="w-5 h-5 flex items-center justify-center text-xs font-semibold text-gray-500 bg-gray-200 rounded-full">
        {index + 1}
      </span>
    );
  };

  if (products.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-6">Top Products</h3>
        <div className="text-center py-12">
          <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
          </svg>
          <p className="mt-2 text-gray-500">No product sales data available</p>
          <p className="text-sm text-gray-400">Start selling products to see top performers</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900">Top Products</h3>
        <span className="text-sm text-gray-500">By Revenue</span>
      </div>

      <div className="space-y-4">
        {products.slice(0, 10).map((product, index) => (
          <div
            key={product.id}
            className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <div className="flex items-center space-x-4 flex-1">
              <div className="flex-shrink-0">
                {getRankIcon(index)}
              </div>
              
              <div className="flex-1 min-w-0">
                <h4 className="text-sm font-medium text-gray-900 truncate">
                  {product.title}
                </h4>
                {product.platform && (
                  <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium mt-1 ${getPlatformColor(product.platform)}`}>
                    {formatPlatformName(product.platform)}
                  </span>
                )}
              </div>
            </div>

            <div className="flex items-center space-x-6 text-sm">
              <div className="text-right">
                <p className="font-semibold text-gray-900">
                  {formatCurrency(product.revenue)}
                </p>
                <p className="text-gray-500">Revenue</p>
              </div>
              
              <div className="text-right">
                <p className="font-semibold text-gray-900">
                  {product.orders.toLocaleString()}
                </p>
                <p className="text-gray-500">Orders</p>
              </div>

              <div className="text-right">
                <p className="font-semibold text-gray-900">
                  {formatCurrency(product.revenue / product.orders)}
                </p>
                <p className="text-gray-500">AOV</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {products.length > 10 && (
        <div className="mt-6 text-center">
          <button className="text-indigo-600 hover:text-indigo-800 text-sm font-medium">
            View All Products ({products.length})
          </button>
        </div>
      )}

      {/* Summary Stats */}
      <div className="mt-6 pt-6 border-t border-gray-200">
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <p className="text-2xl font-semibold text-gray-900">
              {products.length}
            </p>
            <p className="text-sm text-gray-500">Products Sold</p>
          </div>
          <div>
            <p className="text-2xl font-semibold text-gray-900">
              {formatCurrency(products.reduce((sum, product) => sum + product.revenue, 0))}
            </p>
            <p className="text-sm text-gray-500">Total Revenue</p>
          </div>
          <div>
            <p className="text-2xl font-semibold text-gray-900">
              {products.reduce((sum, product) => sum + product.orders, 0).toLocaleString()}
            </p>
            <p className="text-sm text-gray-500">Total Orders</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TopProducts;