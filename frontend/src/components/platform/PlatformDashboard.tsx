import React, { useState, useEffect } from 'react';
import { PlatformInfo, ConnectionTestResult } from '../../types/platform';
import { platformService } from '../../services/platform';
import PlatformConnectionCard from './PlatformConnectionCard';
import PlatformSetupWizard from './PlatformSetupWizard';
import ConnectionTestDialog from './ConnectionTestDialog';

const PlatformDashboard: React.FC = () => {
  const [platforms, setPlatforms] = useState<PlatformInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPlatform, setSelectedPlatform] = useState<string | null>(null);
  const [showSetupWizard, setShowSetupWizard] = useState(false);
  const [showTestDialog, setShowTestDialog] = useState(false);
  const [testResults, setTestResults] = useState<ConnectionTestResult[]>([]);
  const [testingAll, setTestingAll] = useState(false);

  useEffect(() => {
    loadPlatforms();
  }, []);

  const loadPlatforms = async () => {
    try {
      setLoading(true);
      const data = await platformService.getAllPlatforms();
      setPlatforms(data);
    } catch (err) {
      setError('Failed to load platforms');
      console.error('Error loading platforms:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleConnect = (platform: string) => {
    setSelectedPlatform(platform);
    setShowSetupWizard(true);
  };

  const handleDisconnect = async (platform: string) => {
    try {
      await platformService.disconnectPlatform(platform);
      await loadPlatforms(); // Refresh the list
    } catch (err) {
      console.error('Error disconnecting platform:', err);
      setError('Failed to disconnect platform');
    }
  };

  const handleToggleEnable = async (platform: string, enabled: boolean) => {
    try {
      if (enabled) {
        await platformService.enablePlatform(platform);
      } else {
        await platformService.disablePlatform(platform);
      }
      await loadPlatforms(); // Refresh the list
    } catch (err) {
      console.error('Error toggling platform:', err);
      setError('Failed to update platform status');
    }
  };

  const handleTestConnection = async (platform: string) => {
    try {
      const result = await platformService.testConnection(platform);
      setTestResults([result]);
      setShowTestDialog(true);
    } catch (err) {
      console.error('Error testing connection:', err);
      setError('Failed to test connection');
    }
  };

  const handleTestAllConnections = async () => {
    try {
      setTestingAll(true);
      const response = await platformService.testAllConnections();
      setTestResults(response.results);
      setShowTestDialog(true);
    } catch (err) {
      console.error('Error testing all connections:', err);
      setError('Failed to test connections');
    } finally {
      setTestingAll(false);
    }
  };

  const handleSetupComplete = () => {
    setShowSetupWizard(false);
    setSelectedPlatform(null);
    loadPlatforms(); // Refresh the list
  };

  const connectedPlatforms = platforms.filter(p => p.connected);
  const availablePlatforms = platforms.filter(p => !p.connected);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" role="status" aria-label="Loading platforms">
          <span className="sr-only">Loading...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Platform Connections</h1>
        <p className="text-gray-600">
          Manage your connections to social media and marketplace platforms
        </p>
      </div>

      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-red-800">{error}</p>
            </div>
            <div className="ml-auto pl-3">
              <button
                onClick={() => setError(null)}
                className="inline-flex text-red-400 hover:text-red-600"
              >
                <span className="sr-only">Dismiss</span>
                <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Connected Platforms */}
      {connectedPlatforms.length > 0 && (
        <div className="mb-8">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-900">
              Connected Platforms ({connectedPlatforms.length})
            </h2>
            <button
              onClick={handleTestAllConnections}
              disabled={testingAll}
              className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
            >
              {testingAll ? (
                <>
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-gray-500" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Testing...
                </>
              ) : (
                <>
                  <svg className="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Test All Connections
                </>
              )}
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {connectedPlatforms.map((platform) => (
              <PlatformConnectionCard
                key={platform.platform}
                platform={platform}
                onConnect={() => handleConnect(platform.platform)}
                onDisconnect={() => handleDisconnect(platform.platform)}
                onToggleEnable={(enabled) => handleToggleEnable(platform.platform, enabled)}
                onTest={() => handleTestConnection(platform.platform)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Available Platforms */}
      {availablePlatforms.length > 0 && (
        <div>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Available Platforms ({availablePlatforms.length})
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {availablePlatforms.map((platform) => (
              <PlatformConnectionCard
                key={platform.platform}
                platform={platform}
                onConnect={() => handleConnect(platform.platform)}
                onDisconnect={() => handleDisconnect(platform.platform)}
                onToggleEnable={(enabled) => handleToggleEnable(platform.platform, enabled)}
                onTest={() => handleTestConnection(platform.platform)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Setup Wizard Modal */}
      {showSetupWizard && selectedPlatform && (
        <PlatformSetupWizard
          platform={selectedPlatform}
          onComplete={handleSetupComplete}
          onCancel={() => {
            setShowSetupWizard(false);
            setSelectedPlatform(null);
          }}
        />
      )}

      {/* Test Results Dialog */}
      {showTestDialog && (
        <ConnectionTestDialog
          results={testResults}
          onClose={() => setShowTestDialog(false)}
        />
      )}
    </div>
  );
};

export default PlatformDashboard;