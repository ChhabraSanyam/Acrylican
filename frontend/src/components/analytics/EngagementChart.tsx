import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  BarElement,
} from 'chart.js';
import { Line, Bar } from 'react-chartjs-2';
import { format, parseISO } from 'date-fns';
import { EngagementTrendData } from '../../types/analytics';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend
);

interface EngagementChartProps {
  data: EngagementTrendData[];
}

const EngagementChart: React.FC<EngagementChartProps> = ({ data }) => {
  const [chartType, setChartType] = React.useState<'line' | 'bar'>('line');
  const [metric, setMetric] = React.useState<'all' | 'likes' | 'shares' | 'comments' | 'views'>('all');

  const formatNumber = (num: number) => {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M';
    }
    if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
  };

  const getChartData = () => {
    const labels = data.map(item => {
      try {
        return format(parseISO(item.date), 'MMM dd');
      } catch {
        return item.date;
      }
    });

    if (metric === 'all') {
      return {
        labels,
        datasets: [
          {
            label: 'Likes',
            data: data.map(item => item.likes),
            borderColor: 'rgb(239, 68, 68)',
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            borderWidth: 2,
            fill: false,
            tension: 0.4,
          },
          {
            label: 'Shares',
            data: data.map(item => item.shares),
            borderColor: 'rgb(59, 130, 246)',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            borderWidth: 2,
            fill: false,
            tension: 0.4,
          },
          {
            label: 'Comments',
            data: data.map(item => item.comments),
            borderColor: 'rgb(16, 185, 129)',
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            borderWidth: 2,
            fill: false,
            tension: 0.4,
          },
          {
            label: 'Views',
            data: data.map(item => item.views),
            borderColor: 'rgb(245, 158, 11)',
            backgroundColor: 'rgba(245, 158, 11, 0.1)',
            borderWidth: 2,
            fill: false,
            tension: 0.4,
          }
        ],
      };
    } else {
      const colors = {
        likes: { border: 'rgb(239, 68, 68)', background: 'rgba(239, 68, 68, 0.1)' },
        shares: { border: 'rgb(59, 130, 246)', background: 'rgba(59, 130, 246, 0.1)' },
        comments: { border: 'rgb(16, 185, 129)', background: 'rgba(16, 185, 129, 0.1)' },
        views: { border: 'rgb(245, 158, 11)', background: 'rgba(245, 158, 11, 0.1)' },
      };

      return {
        labels,
        datasets: [
          {
            label: metric.charAt(0).toUpperCase() + metric.slice(1),
            data: data.map(item => item[metric as keyof EngagementTrendData] as number),
            borderColor: colors[metric as keyof typeof colors].border,
            backgroundColor: colors[metric as keyof typeof colors].background,
            borderWidth: 2,
            fill: chartType === 'line',
            tension: 0.4,
          }
        ],
      };
    }
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: true,
        text: 'Engagement Trend',
        font: {
          size: 16,
          weight: 'bold' as const,
        },
      },
      tooltip: {
        callbacks: {
          label: function(context: any) {
            const label = context.dataset.label || '';
            const value = context.parsed.y;
            return `${label}: ${formatNumber(value)}`;
          }
        }
      }
    },
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    scales: {
      x: {
        display: true,
        title: {
          display: true,
          text: 'Date'
        },
        grid: {
          display: false,
        },
      },
      y: {
        display: true,
        title: {
          display: true,
          text: 'Engagement Count'
        },
        ticks: {
          callback: function(value: any) {
            return formatNumber(value);
          }
        },
        grid: {
          color: 'rgba(0, 0, 0, 0.1)',
        },
      },
    },
  };

  const ChartComponent = chartType === 'line' ? Line : Bar;

  if (data.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Engagement Trend</h3>
        </div>
        <div className="h-80 flex items-center justify-center text-gray-500">
          <div className="text-center">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
            </svg>
            <p className="mt-2">No engagement data available</p>
            <p className="text-sm text-gray-400">Start posting to see your engagement metrics</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Engagement Trend</h3>
        <div className="flex space-x-2">
          <select
            value={metric}
            onChange={(e) => setMetric(e.target.value as any)}
            className="text-sm border border-gray-300 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="all">All Metrics</option>
            <option value="likes">Likes</option>
            <option value="shares">Shares</option>
            <option value="comments">Comments</option>
            <option value="views">Views</option>
          </select>
          <button
            onClick={() => setChartType('line')}
            className={`px-3 py-1 text-sm rounded-md ${
              chartType === 'line'
                ? 'bg-indigo-100 text-indigo-700'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            Line
          </button>
          <button
            onClick={() => setChartType('bar')}
            className={`px-3 py-1 text-sm rounded-md ${
              chartType === 'bar'
                ? 'bg-indigo-100 text-indigo-700'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            Bar
          </button>
        </div>
      </div>
      <div className="h-80">
        <ChartComponent data={getChartData()} options={options} />
      </div>
    </div>
  );
};

export default EngagementChart;