import React from 'react';
import PlatformDashboard from '../components/platform/PlatformDashboard';

const PlatformsPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Platform Connections</h1>
        <p className="text-gray-600">Connect and manage your social media and marketplace accounts</p>
      </div>

      <PlatformDashboard />
    </div>
  );
};

export default PlatformsPage;