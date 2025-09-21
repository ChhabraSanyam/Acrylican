import React from 'react';
import { PlatformInfo } from '../../types/platform';

interface PlatformConnectionCardProps {
  platform: PlatformInfo;
  onConnect: () => void;
  onDisconnect: () => void;
  onToggleEnable: (enabled: boolean) => void;
  onTest: () => void;
}

const PlatformConnectionCard: React.FC<PlatformConnectionCardProps> = ({
  platform,
  onConnect,
  onDisconnect,
  onToggleEnable,
  onTest
}) => {
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

  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'active':
        return 'text-green-600 bg-green-100';
      case 'inactive':
        return 'text-yellow-600 bg-yellow-100';
      case 'not_connected':
        return 'text-gray-600 bg-gray-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getStatusText = (status?: string) => {
    switch (status) {
      case 'active':
        return 'Connected';
      case 'inactive':
        return 'Inactive';
      case 'not_connected':
        return 'Not Connected';
      default:
        return 'Unknown';
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleDateString();
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-shadow">
      <div className="p-6">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center">
            <span className="text-2xl mr-3">{getPlatformIcon(platform.platform)}</span>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">{platform.name}</h3>
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(platform.connection_status)}`}>
                {getStatusText(platform.connection_status)}
              </span>
            </div>
          </div>
          
          {platform.connected && (
            <div className="flex items-center">
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={platform.enabled}
                  onChange={(e) => onToggleEnable(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                <span className="ml-2 text-sm text-gray-600">Enabled</span>
              </label>
            </div>
          )}
        </div>

        {/* Description */}
        <p className="text-gray-600 text-sm mb-4">{platform.description}</p>

        {/* Connection Details */}
        {platform.connected && (
          <div className="space-y-2 mb-4">
            {platform.platform_username && (
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Account:</span>
                <span className="text-gray-900">{platform.platform_username}</span>
              </div>
            )}
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Connected:</span>
              <span className="text-gray-900">{formatDate(platform.connected_at)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Last Validated:</span>
              <span className="text-gray-900">{formatDate(platform.last_validated_at)}</span>
            </div>
            {platform.expires_at && (
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Expires:</span>
                <span className="text-gray-900">{formatDate(platform.expires_at)}</span>
              </div>
            )}
          </div>
        )}

        {/* Validation Error */}
        {platform.validation_error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
            <p className="text-sm text-red-800">{platform.validation_error}</p>
          </div>
        )}

        {/* Setup Instructions */}
        {platform.setup_required && platform.setup_instructions && (
          <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-md">
            <p className="text-sm text-blue-800">{platform.setup_instructions}</p>
          </div>
        )}

        {/* Actions */}
        <div className="flex space-x-2">
          {!platform.connected ? (
            <button
              onClick={onConnect}
              className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              Connect
            </button>
          ) : (
            <>
              <button
                onClick={onTest}
                className="flex-1 bg-green-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
              >
                Test
              </button>
              <button
                onClick={onDisconnect}
                className="flex-1 bg-red-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
              >
                Disconnect
              </button>
            </>
          )}
        </div>

        {/* Integration Type Badge */}
        <div className="mt-3 flex justify-between items-center">
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
            {platform.integration_type === 'api' ? '🔗 API' : '🤖 Browser Automation'}
          </span>
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
            {platform.auth_method === 'oauth2' ? '🔐 OAuth' : '🔑 Credentials'}
          </span>
        </div>
      </div>
    </div>
  );
};

export default PlatformConnectionCard;