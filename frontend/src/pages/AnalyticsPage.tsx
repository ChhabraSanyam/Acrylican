import React from 'react';
import AnalyticsDashboard from '../components/analytics/AnalyticsDashboard';

const AnalyticsPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
        <p className="text-gray-600">Track your performance across all platforms</p>
      </div>

      <AnalyticsDashboard />
    </div>
  );
};

export default AnalyticsPage;