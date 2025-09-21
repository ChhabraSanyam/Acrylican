import React from 'react';
import { Platform } from '../../types/content';

interface PlatformSelectorProps {
  platforms: Record<string, Platform>;
  selectedPlatforms: string[];
  availablePlatforms: string[];
  onPlatformToggle: (platform: string, enabled: boolean) => void;
}

const PlatformSelector: React.FC<PlatformSelectorProps> = ({
  platforms,
  selectedPlatforms,
  availablePlatforms,
  onPlatformToggle
}) => {
  const getPlatformIcon = (platformType: string) => {
    switch (platformType) {
      case 'social_media':
        return (
          <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clipRule="evenodd" />
          </svg>
        );
      case 'marketplace':
        return (
          <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
            <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" />
          </svg>
        );
      case 'ecommerce':
        return (
          <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 2L3 7v11a1 1 0 001 1h12a1 1 0 001-1V7l-7-5zM6 12a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1z" clipRule="evenodd" />
          </svg>
        );
      case 'b2b_marketplace':
        return (
          <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
            <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3z" />
          </svg>
        );
      default:
        return (
          <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M3 5a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 10a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 15a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd" />
          </svg>
        );
    }
  };

  const getPlatformTypeColor = (platformType: string) => {
    switch (platformType) {
      case 'social_media':
        return 'bg-blue-100 text-blue-800';
      case 'marketplace':
        return 'bg-green-100 text-green-800';
      case 'ecommerce':
        return 'bg-purple-100 text-purple-800';
      case 'b2b_marketplace':
        return 'bg-orange-100 text-orange-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div>
      <h3 className="text-lg font-medium text-gray-900 mb-4">Select Platforms</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {availablePlatforms.map(platformKey => {
          const platform = platforms[platformKey];
          if (!platform) return null;

          const isSelected = selectedPlatforms.includes(platformKey);

          return (
            <div
              key={platformKey}
              className={`relative rounded-lg border-2 p-4 cursor-pointer transition-all ${
                isSelected
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 bg-white hover:border-gray-300'
              }`}
              onClick={() => onPlatformToggle(platformKey, !isSelected)}
            >
              {/* Selection Checkbox */}
              <div className="absolute top-3 right-3">
                <input
                  type="checkbox"
                  checked={isSelected}
                  onChange={() => onPlatformToggle(platformKey, !isSelected)}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
              </div>

              {/* Platform Info */}
              <div className="flex items-start space-x-3">
                <div className={`flex-shrink-0 p-2 rounded-lg ${
                  isSelected ? 'bg-blue-100 text-blue-600' : 'bg-gray-100 text-gray-600'
                }`}>
                  {getPlatformIcon(platform.type)}
                </div>
                
                <div className="flex-1 min-w-0">
                  <h4 className="text-sm font-medium text-gray-900">{platform.name}</h4>
                  <div className="mt-1">
                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getPlatformTypeColor(platform.type)}`}>
                      {platform.type.replace('_', ' ')}
                    </span>
                  </div>
                  
                  {/* Platform Limits */}
                  <div className="mt-2 text-xs text-gray-500 space-y-1">
                    <div>Title: {platform.title_max_length} chars</div>
                    <div>Description: {platform.description_max_length} chars</div>
                    {platform.hashtag_limit > 0 && (
                      <div>Hashtags: {platform.hashtag_limit} max</div>
                    )}
                  </div>
                  
                  {/* Platform Features */}
                  <div className="mt-2">
                    <div className="flex flex-wrap gap-1">
                      {platform.features.slice(0, 2).map(feature => (
                        <span
                          key={feature}
                          className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-700"
                        >
                          {feature.replace('_', ' ')}
                        </span>
                      ))}
                      {platform.features.length > 2 && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-700">
                          +{platform.features.length - 2} more
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Selection Summary */}
      <div className="mt-4 p-3 bg-gray-50 rounded-lg">
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-600">
            {selectedPlatforms.length} of {availablePlatforms.length} platforms selected
          </span>
          {selectedPlatforms.length > 0 && (
            <button
              onClick={() => selectedPlatforms.forEach(platform => onPlatformToggle(platform, false))}
              className="text-sm text-red-600 hover:text-red-800"
            >
              Clear all
            </button>
          )}
        </div>
        
        {selectedPlatforms.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-2">
            {selectedPlatforms.map(platformKey => {
              const platform = platforms[platformKey];
              return platform ? (
                <span
                  key={platformKey}
                  className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-blue-100 text-blue-800"
                >
                  {platform.name}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onPlatformToggle(platformKey, false);
                    }}
                    className="ml-1 text-blue-600 hover:text-blue-800"
                  >
                    <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                  </button>
                </span>
              ) : null;
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default PlatformSelector;