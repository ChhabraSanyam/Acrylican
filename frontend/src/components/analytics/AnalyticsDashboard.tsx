import React, { useState, useEffect, useCallback } from "react";
import { format, subDays, startOfDay, endOfDay } from "date-fns";
import {
  SalesDashboardData,
  EngagementDashboardData,
  DashboardFilters,
} from "../../types/analytics";
import { analyticsService } from "../../services/analytics";
import DateRangeSelector from "./DateRangeSelector";
import PlatformFilter from "./PlatformFilter";
import KPICards from "./KPICards";
import SalesChart from "./SalesChart";
import EngagementChart from "./EngagementChart";
import PlatformBreakdown from "./PlatformBreakdown";
import TopProducts from "./TopProducts";
import RecentActivity from "./RecentActivity";
import LoadingSpinner from "../common/LoadingSpinner";
import ErrorMessage from "../common/ErrorMessage";

const AnalyticsDashboard: React.FC = () => {
  const [salesData, setSalesData] = useState<SalesDashboardData | null>(null);
  const [engagementData, setEngagementData] =
    useState<EngagementDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [availablePlatforms, setAvailablePlatforms] = useState<string[]>([]);

  const [filters, setFilters] = useState<DashboardFilters>({
    dateRange: {
      start_date: format(
        startOfDay(subDays(new Date(), 30)),
        "yyyy-MM-dd'T'HH:mm:ss"
      ),
      end_date: format(endOfDay(new Date()), "yyyy-MM-dd'T'HH:mm:ss"),
    },
    platforms: [],
    currency: "INR",
  });

  const fetchDashboardData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Calculate days for the API call
      const startDate = new Date(filters.dateRange.start_date);
      const endDate = new Date(filters.dateRange.end_date);
      const days = Math.ceil(
        (endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24)
      );

      // Fetch sales and engagement data in parallel
      const [salesResponse, engagementResponse] = await Promise.all([
        analyticsService.getSalesDashboard(days, filters.currency),
        analyticsService.getEngagementDashboard(
          filters.dateRange.start_date,
          filters.dateRange.end_date,
          filters.platforms.length > 0 ? filters.platforms : undefined
        ),
      ]);

      setSalesData(salesResponse);
      setEngagementData(engagementResponse);
    } catch (err: any) {
      setError(err.message || "Failed to load dashboard data");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  const fetchAvailablePlatforms = async () => {
    try {
      const [salesPlatforms, engagementPlatforms] = await Promise.all([
        analyticsService.getSalesPlatforms(),
        analyticsService.getEngagementPlatforms(),
      ]);

      // Combine and deduplicate platforms
      const allPlatforms = [
        ...salesPlatforms.platforms,
        ...engagementPlatforms,
      ];
      const uniquePlatforms = Array.from(new Set(allPlatforms));
      setAvailablePlatforms(uniquePlatforms);
    } catch (err) {
      console.error("Failed to fetch available platforms:", err);
    }
  };

  useEffect(() => {
    fetchAvailablePlatforms();
  }, []);

  useEffect(() => {
    fetchDashboardData();
  }, [filters, fetchDashboardData]);

  const handleDateRangeChange = (startDate: Date, endDate: Date) => {
    setFilters((prev) => ({
      ...prev,
      dateRange: {
        start_date: format(startOfDay(startDate), "yyyy-MM-dd'T'HH:mm:ss"),
        end_date: format(endOfDay(endDate), "yyyy-MM-dd'T'HH:mm:ss"),
      },
    }));
  };

  const handlePlatformFilterChange = (platforms: string[]) => {
    setFilters((prev) => ({
      ...prev,
      platforms,
    }));
  };

  const handleCurrencyChange = (currency: string) => {
    setFilters((prev) => ({
      ...prev,
      currency,
    }));
  };

  const handleRefresh = () => {
    fetchDashboardData();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <LoadingSpinner size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-7xl mx-auto">
          <ErrorMessage message={error} onRetry={handleRefresh} />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                Analytics Dashboard
              </h1>
              <p className="text-gray-600 mt-1">
                Track your sales performance and engagement metrics across all
                platforms
              </p>
            </div>
            <button
              onClick={handleRefresh}
              className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              <svg
                className="w-4 h-4 mr-2"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
              Refresh
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <div className="flex flex-wrap items-center gap-4">
            <DateRangeSelector
              startDate={new Date(filters.dateRange.start_date)}
              endDate={new Date(filters.dateRange.end_date)}
              onChange={handleDateRangeChange}
            />
            <PlatformFilter
              availablePlatforms={availablePlatforms}
              selectedPlatforms={filters.platforms}
              onChange={handlePlatformFilterChange}
            />
            <div className="flex items-center space-x-2">
              <label
                htmlFor="currency"
                className="text-sm font-medium text-gray-700"
              >
                Currency:
              </label>
              <select
                id="currency"
                value={filters.currency}
                onChange={(e) => handleCurrencyChange(e.target.value)}
                className="border border-gray-300 rounded-md px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              >
                <option value="USD">USD</option>
                <option value="EUR">EUR</option>
                <option value="INR">INR</option>
                <option value="GBP">GBP</option>
              </select>
            </div>
          </div>
        </div>

        {/* KPI Cards */}
        <KPICards
          salesData={salesData}
          engagementData={engagementData}
          currency={filters.currency}
        />

        {/* Charts Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          <SalesChart
            data={salesData?.sales_trend || []}
            currency={filters.currency}
          />
          <EngagementChart data={engagementData?.engagement_trend || []} />
        </div>

        {/* Platform Breakdown and Top Products */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          <PlatformBreakdown
            salesData={salesData?.platform_breakdown || []}
            engagementData={engagementData?.engagement_by_platform || []}
            currency={filters.currency}
            startDate={filters.dateRange.start_date}
            endDate={filters.dateRange.end_date}
            platforms={
              filters.platforms.length > 0 ? filters.platforms : undefined
            }
          />
          <TopProducts
            products={salesData?.top_products || []}
            currency={filters.currency}
          />
        </div>

        {/* Recent Activity */}
        <RecentActivity
          recentSales={salesData?.recent_sales || []}
          topPosts={engagementData?.top_performing_posts || []}
          currency={filters.currency}
        />
      </div>
    </div>
  );
};

export default AnalyticsDashboard;
