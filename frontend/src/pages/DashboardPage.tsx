import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { ProductService } from "../services/product";
import { platformService } from "../services/platform";
import { analyticsService } from "../services/analytics";
import {
  CubeIcon,
  LinkIcon,
  PencilSquareIcon,
  ChartBarIcon,
  ArrowTrendingUpIcon,
  UserGroupIcon,
  CurrencyDollarIcon,
} from "@heroicons/react/24/outline";

interface DashboardStats {
  totalProducts: number;
  connectedPlatforms: number;
  totalPosts: number;
  totalRevenue: number;
  recentActivity: Array<{ id: string; action: string; time: string }>;
}

const DashboardPage: React.FC = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState<DashboardStats>({
    totalProducts: 0,
    connectedPlatforms: 0,
    totalPosts: 0,
    totalRevenue: 0,
    recentActivity: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadDashboardData = async () => {
      try {
        setLoading(true);
        setError(null);

        // Load data in parallel
        const [products, platforms, salesData] = await Promise.allSettled([
          ProductService.getProducts(),
          platformService.getAllPlatforms(),
          analyticsService.getSalesDashboard(30, "INR"),
        ]);

        const newStats: DashboardStats = {
          totalProducts:
            products.status === "fulfilled" ? products.value.length : 0,
          connectedPlatforms:
            platforms.status === "fulfilled"
              ? platforms.value.filter((p) => p.connected).length
              : 0,
          totalPosts: 0, // This would come from a posts API
          totalRevenue:
            salesData.status === "fulfilled"
              ? salesData.value.overall_metrics.total_revenue
              : 0,
          recentActivity:
            salesData.status === "fulfilled"
              ? salesData.value.recent_sales.map((sale) => ({
                  id: sale.id,
                  action: `New sale: ${sale.product_title} on ${sale.platform}`,
                  time: new Date(sale.occurred_at).toLocaleString(),
                }))
              : [],
        };

        setStats(newStats);
      } catch (err) {
        setError("Failed to load dashboard data");
        console.error("Dashboard error:", err);
      } finally {
        setLoading(false);
      }
    };

    loadDashboardData();
  }, []);

  const quickActions = [
    {
      title: "Add New Product",
      description: "Upload and manage your products",
      icon: CubeIcon,
      link: "/products",
      color: "bg-blue-500",
    },
    {
      title: "Connect Platforms",
      description: "Link your social media accounts",
      icon: LinkIcon,
      link: "/platforms",
      color: "bg-green-500",
    },
    {
      title: "Create Post",
      description: "Generate and schedule content",
      icon: PencilSquareIcon,
      link: "/posting",
      color: "bg-purple-500",
    },
    {
      title: "View Analytics",
      description: "Track your performance",
      icon: ChartBarIcon,
      link: "/analytics",
      color: "bg-orange-500",
    },
  ];

  const statCards = [
    {
      title: "Total Products",
      value: stats.totalProducts,
      icon: CubeIcon,
      color: "text-blue-600",
      bgColor: "bg-blue-100",
    },
    {
      title: "Connected Platforms",
      value: stats.connectedPlatforms,
      icon: LinkIcon,
      color: "text-green-600",
      bgColor: "bg-green-100",
    },
    {
      title: "Total Posts",
      value: stats.totalPosts,
      icon: UserGroupIcon,
      color: "text-purple-600",
      bgColor: "bg-purple-100",
    },
    {
      title: "Revenue (30d)",
      value: `$${stats.totalRevenue}`,
      icon: CurrencyDollarIcon,
      color: "text-orange-600",
      bgColor: "bg-orange-100",
    },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
        <span className="ml-3 text-gray-600">Loading dashboard...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-md p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg
              className="h-5 w-5 text-red-400"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clipRule="evenodd"
              />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">
              Error loading dashboard
            </h3>
            <p className="text-sm text-red-700 mt-1">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Welcome Section */}
      <div className="bg-gradient-to-r from-indigo-500 to-purple-600 rounded-lg shadow-lg p-6 text-white">
        <h1 className="text-2xl font-bold mb-2">
          Welcome back, {user?.business_name}!
        </h1>
        <p className="text-indigo-100">
          Here's what's happening with your business today
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((stat, index) => (
          <div key={index} className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className={`p-3 rounded-lg ${stat.bgColor}`}>
                <stat.icon className={`w-6 h-6 ${stat.color}`} />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">
                  {stat.title}
                </p>
                <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-lg font-medium text-gray-900">Quick Actions</h2>
          <p className="text-sm text-gray-600">
            Get started with these common tasks
          </p>
        </div>
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {quickActions.map((action, index) => (
              <Link
                key={index}
                to={action.link}
                className="group relative bg-white border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow"
              >
                <div className="flex items-center space-x-3">
                  <div className={`p-2 rounded-lg ${action.color}`}>
                    <action.icon className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h3 className="text-sm font-medium text-gray-900 group-hover:text-indigo-600">
                      {action.title}
                    </h3>
                    <p className="text-xs text-gray-500">
                      {action.description}
                    </p>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-lg font-medium text-gray-900">Recent Activity</h2>
        </div>
        <div className="p-6">
          {stats.recentActivity.length > 0 ? (
            <div className="space-y-4">
              {stats.recentActivity.map((activity: any) => (
                <div key={activity.id} className="flex items-start space-x-3">
                  <div className="flex-shrink-0">
                    <ArrowTrendingUpIcon className="w-5 h-5 text-gray-400" />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm text-gray-900">{activity.action}</p>
                    <p className="text-xs text-gray-500">{activity.time}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-4">No recent activity</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
