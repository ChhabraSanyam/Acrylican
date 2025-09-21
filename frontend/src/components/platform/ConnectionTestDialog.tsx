import React from 'react';
import { ConnectionTestResult } from '../../types/platform';

interface ConnectionTestDialogProps {
  results: ConnectionTestResult[];
  onClose: () => void;
}

const ConnectionTestDialog: React.FC<ConnectionTestDialogProps> = ({
  results,
  onClose
}) => {
  const successCount = results.filter(r => r.success).length;
  const failureCount = results.length - successCount;

  const getPlatformIcon = (platformName: string) => {
    const icons: Record<string, string> = {
      facebook: '📘',
      instagram: '📷',
      facebook_marketplace: '🛒',
      etsy: '🎨',
      pinterest: '📌',
      meesho: '🛍️',
      snapdeal: '💼',
      indiamart: '🏭',
      shopify: '🛒'
    };
    return icons[platformName] || '🔗';
  };

  const getPlatformName = (platformName: string) => {
    const names: Record<string, string> = {
      facebook: 'Facebook',
      instagram: 'Instagram',
      facebook_marketplace: 'Facebook Marketplace',
      etsy: 'Etsy',
      pinterest: 'Pinterest',
      meesho: 'Meesho',
      snapdeal: 'Snapdeal',
      indiamart: 'IndiaMART',
      shopify: 'Shopify'
    };
    return names[platformName] || platformName;
  };

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 border w-full max-w-2xl shadow-lg rounded-md bg-white">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <h3 className="text-lg font-medium text-gray-900">Connection Test Results</h3>
            <p className="text-sm text-gray-600">
              {successCount} successful, {failureCount} failed out of {results.length} connections
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Summary */}
        <div className="mb-6 grid grid-cols-2 gap-4">
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <div className="flex items-center">
              <svg className="h-8 w-8 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div className="ml-3">
                <p className="text-sm font-medium text-green-800">Successful</p>
                <p className="text-2xl font-bold text-green-900">{successCount}</p>
              </div>
            </div>
          </div>
          
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-center">
              <svg className="h-8 w-8 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
              <div className="ml-3">
                <p className="text-sm font-medium text-red-800">Failed</p>
                <p className="text-2xl font-bold text-red-900">{failureCount}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Results List */}
        <div className="space-y-3 max-h-96 overflow-y-auto">
          {results.map((result, index) => (
            <div
              key={index}
              className={`border rounded-lg p-4 ${
                result.success
                  ? 'border-green-200 bg-green-50'
                  : 'border-red-200 bg-red-50'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center">
                  <span className="text-xl mr-3">{getPlatformIcon(result.platform)}</span>
                  <div>
                    <h4 className="font-medium text-gray-900">
                      {getPlatformName(result.platform)}
                    </h4>
                    <p className={`text-sm ${
                      result.success ? 'text-green-800' : 'text-red-800'
                    }`}>
                      {result.message}
                    </p>
                  </div>
                </div>
                
                <div className="flex items-center">
                  {result.success ? (
                    <svg className="h-5 w-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  ) : (
                    <svg className="h-5 w-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  )}
                </div>
              </div>

              {/* Additional Details */}
              {result.details && (
                <div className="mt-3 pt-3 border-t border-gray-200">
                  <div className="grid grid-cols-1 gap-2 text-sm">
                    {result.details.last_validated && (
                      <div className="flex justify-between">
                        <span className="text-gray-500">Last Validated:</span>
                        <span className="text-gray-900">
                          {new Date(result.details.last_validated).toLocaleString()}
                        </span>
                      </div>
                    )}
                    {result.details.platform_username && (
                      <div className="flex justify-between">
                        <span className="text-gray-500">Account:</span>
                        <span className="text-gray-900">{result.details.platform_username}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Actions */}
        <div className="mt-6 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default ConnectionTestDialog;