import React, { useState } from 'react';

interface PlatformFilterProps {
  availablePlatforms: string[];
  selectedPlatforms: string[];
  onChange: (platforms: string[]) => void;
}

const PlatformFilter: React.FC<PlatformFilterProps> = ({
  availablePlatforms,
  selectedPlatforms,
  onChange
}) => {
  const [isOpen, setIsOpen] = useState(false);

  const handlePlatformToggle = (platform: string) => {
    const newSelection = selectedPlatforms.includes(platform)
      ? selectedPlatforms.filter(p => p !== platform)
      : [...selectedPlatforms, platform];
    
    onChange(newSelection);
  };

  const handleSelectAll = () => {
    onChange(availablePlatforms);
  };

  const handleClearAll = () => {
    onChange([]);
  };

  const formatPlatformName = (platform: string) => {
    return platform
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const getDisplayText = () => {
    if (selectedPlatforms.length === 0) {
      return 'All Platforms';
    }
    if (selectedPlatforms.length === 1) {
      return formatPlatformName(selectedPlatforms[0]);
    }
    if (selectedPlatforms.length === availablePlatforms.length) {
      return 'All Platforms';
    }
    return `${selectedPlatforms.length} Platforms`;
  };

  return (
    <div className="relative">
      <div className="flex items-center space-x-2">
        <label className="text-sm font-medium text-gray-700">
          Platforms:
        </label>
        <div className="relative">
          <button
            type="button"
            onClick={() => setIsOpen(!isOpen)}
            className="relative w-48 bg-white border border-gray-300 rounded-md pl-3 pr-10 py-1 text-left cursor-default focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
          >
            <span className="block truncate">{getDisplayText()}</span>
            <span className="absolute inset-y-0 right-0 flex items-center pr-2 pointer-events-none">
              <svg
                className={`h-4 w-4 text-gray-400 transform transition-transform ${
                  isOpen ? 'rotate-180' : ''
                }`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </span>
          </button>

          {isOpen && (
            <div className="absolute z-10 mt-1 w-full bg-white shadow-lg max-h-60 rounded-md py-1 text-base ring-1 ring-black ring-opacity-5 overflow-auto focus:outline-none sm:text-sm">
              {/* Select All / Clear All */}
              <div className="px-3 py-2 border-b border-gray-200">
                <div className="flex justify-between">
                  <button
                    type="button"
                    onClick={handleSelectAll}
                    className="text-xs text-indigo-600 hover:text-indigo-800 font-medium"
                  >
                    Select All
                  </button>
                  <button
                    type="button"
                    onClick={handleClearAll}
                    className="text-xs text-gray-600 hover:text-gray-800 font-medium"
                  >
                    Clear All
                  </button>
                </div>
              </div>

              {/* Platform Options */}
              {availablePlatforms.map((platform) => (
                <div
                  key={platform}
                  className="relative cursor-pointer select-none py-2 pl-3 pr-9 hover:bg-gray-50"
                  onClick={() => handlePlatformToggle(platform)}
                >
                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      checked={selectedPlatforms.includes(platform)}
                      onChange={() => handlePlatformToggle(platform)}
                      className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                    />
                    <span className="ml-3 block truncate text-sm">
                      {formatPlatformName(platform)}
                    </span>
                  </div>
                </div>
              ))}

              {availablePlatforms.length === 0 && (
                <div className="px-3 py-2 text-sm text-gray-500">
                  No platforms available
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Overlay to close dropdown when clicking outside */}
      {isOpen && (
        <div
          className="fixed inset-0 z-0"
          onClick={() => setIsOpen(false)}
        />
      )}
    </div>
  );
};

export default PlatformFilter;