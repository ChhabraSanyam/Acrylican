import React, { useState, useEffect, useCallback } from 'react';
import { Post, PostFilters, PostStatus, QueueStatus } from '../../types/post';
import { postService } from '../../services/post';

interface PostStatusDashboardProps {
  onPostSelect?: (post: Post) => void;
  onRefresh?: () => void;
  refreshInterval?: number; // in milliseconds
}

export const PostStatusDashboard: React.FC<PostStatusDashboardProps> = ({
  onPostSelect,
  onRefresh,
  refreshInterval = 30000 // 30 seconds default
}) => {
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<PostFilters>({});
  const [selectedPosts, setSelectedPosts] = useState<Set<string>>(new Set());
  const [sortBy, setSortBy] = useState<'created_at' | 'scheduled_at' | 'status'>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [pagination, setPagination] = useState({ skip: 0, limit: 20, total: 0 });

  // Real-time updates
  useEffect(() => {
    const interval = setInterval(() => {
      loadPosts(true); // Silent refresh
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [refreshInterval, filters, pagination.skip, pagination.limit]);

  useEffect(() => {
    loadPosts();
  }, [filters, pagination.skip, pagination.limit]);

  const loadPosts = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    setError(null);

    try {
      const response = await postService.getPosts(
        pagination.skip,
        pagination.limit,
        filters
      );
      
      setPosts(response.posts);
      setPagination(prev => ({ ...prev, total: response.total }));
      onRefresh?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load posts');
    } finally {
      if (!silent) setLoading(false);
    }
  }, [filters, pagination.skip, pagination.limit, onRefresh]);

  const handleFilterChange = (newFilters: Partial<PostFilters>) => {
    setFilters(prev => ({ ...prev, ...newFilters }));
    setPagination(prev => ({ ...prev, skip: 0 })); // Reset to first page
  };

  const handleSort = (field: typeof sortBy) => {
    if (sortBy === field) {
      setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
  };

  const handleSelectPost = (postId: string) => {
    setSelectedPosts(prev => {
      const newSet = new Set(prev);
      if (newSet.has(postId)) {
        newSet.delete(postId);
      } else {
        newSet.add(postId);
      }
      return newSet;
    });
  };

  const handleSelectAll = () => {
    if (selectedPosts.size === posts.length) {
      setSelectedPosts(new Set());
    } else {
      setSelectedPosts(new Set(posts.map(post => post.id)));
    }
  };

  const handleRetryPost = async (post: Post) => {
    try {
      await postService.retryPost(post.id);
      loadPosts();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to retry post');
    }
  };

  const handleCancelPost = async (post: Post) => {
    try {
      await postService.cancelScheduledPost(post.id);
      loadPosts();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to cancel post');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case PostStatus.DRAFT:
        return 'bg-gray-100 text-gray-800';
      case PostStatus.SCHEDULED:
        return 'bg-blue-100 text-blue-800';
      case PostStatus.PUBLISHING:
        return 'bg-yellow-100 text-yellow-800';
      case PostStatus.PUBLISHED:
        return 'bg-green-100 text-green-800';
      case PostStatus.FAILED:
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case PostStatus.DRAFT:
        return '📝';
      case PostStatus.SCHEDULED:
        return '⏰';
      case PostStatus.PUBLISHING:
        return '🔄';
      case PostStatus.PUBLISHED:
        return '✅';
      case PostStatus.FAILED:
        return '❌';
      default:
        return '❓';
    }
  };

  const sortedPosts = [...posts].sort((a, b) => {
    let aValue: any, bValue: any;
    
    switch (sortBy) {
      case 'created_at':
        aValue = new Date(a.created_at);
        bValue = new Date(b.created_at);
        break;
      case 'scheduled_at':
        aValue = a.scheduled_at ? new Date(a.scheduled_at) : new Date(0);
        bValue = b.scheduled_at ? new Date(b.scheduled_at) : new Date(0);
        break;
      case 'status':
        aValue = a.status;
        bValue = b.status;
        break;
      default:
        return 0;
    }
    
    if (sortOrder === 'asc') {
      return aValue < bValue ? -1 : aValue > bValue ? 1 : 0;
    } else {
      return aValue > bValue ? -1 : aValue < bValue ? 1 : 0;
    }
  });

  if (loading && posts.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-gray-200 rounded w-1/4"></div>
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-16 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-lg">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900">
            Post Status Dashboard
          </h2>
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2 text-sm text-gray-500">
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
              <span>Live updates</span>
            </div>
            <button
              onClick={() => loadPosts()}
              className="px-3 py-1 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              Refresh
            </button>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
        <div className="flex flex-wrap items-center gap-4">
          <div>
            <select
              value={filters.status || ''}
              onChange={(e) => handleFilterChange({ status: e.target.value || undefined })}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Statuses</option>
              <option value={PostStatus.DRAFT}>Draft</option>
              <option value={PostStatus.SCHEDULED}>Scheduled</option>
              <option value={PostStatus.PUBLISHING}>Publishing</option>
              <option value={PostStatus.PUBLISHED}>Published</option>
              <option value={PostStatus.FAILED}>Failed</option>
            </select>
          </div>
          
          <div className="flex items-center space-x-2">
            <input
              type="date"
              value={filters.date_from || ''}
              onChange={(e) => handleFilterChange({ date_from: e.target.value || undefined })}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <span className="text-gray-500">to</span>
            <input
              type="date"
              value={filters.date_to || ''}
              onChange={(e) => handleFilterChange({ date_to: e.target.value || undefined })}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {selectedPosts.size > 0 && (
            <div className="flex items-center space-x-2 ml-auto">
              <span className="text-sm text-gray-600">
                {selectedPosts.size} selected
              </span>
              <button
                onClick={() => {
                  // Handle bulk actions
                }}
                className="px-3 py-1 text-sm bg-gray-600 text-white rounded-md hover:bg-gray-700"
              >
                Bulk Actions
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="px-6 py-4 bg-red-50 border-b border-red-200">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {/* Posts Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left">
                <input
                  type="checkbox"
                  checked={selectedPosts.size === posts.length && posts.length > 0}
                  onChange={handleSelectAll}
                  className="rounded border-gray-300"
                />
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th 
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('created_at')}
              >
                <div className="flex items-center">
                  Post
                  {sortBy === 'created_at' && (
                    <span className="ml-1">{sortOrder === 'asc' ? '↑' : '↓'}</span>
                  )}
                </div>
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Platforms
              </th>
              <th 
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('scheduled_at')}
              >
                <div className="flex items-center">
                  Schedule
                  {sortBy === 'scheduled_at' && (
                    <span className="ml-1">{sortOrder === 'asc' ? '↑' : '↓'}</span>
                  )}
                </div>
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Results
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {sortedPosts.map((post) => (
              <tr 
                key={post.id} 
                className={`hover:bg-gray-50 ${selectedPosts.has(post.id) ? 'bg-blue-50' : ''}`}
              >
                <td className="px-6 py-4">
                  <input
                    type="checkbox"
                    checked={selectedPosts.has(post.id)}
                    onChange={() => handleSelectPost(post.id)}
                    className="rounded border-gray-300"
                  />
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center">
                    <span className="mr-2">{getStatusIcon(post.status)}</span>
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(post.status)}`}>
                      {post.status}
                    </span>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="max-w-xs">
                    <p className="font-medium text-gray-900 truncate">{post.title}</p>
                    <p className="text-sm text-gray-500 truncate">{post.description}</p>
                    <p className="text-xs text-gray-400">
                      Created: {new Date(post.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="flex flex-wrap gap-1">
                    {post.target_platforms.slice(0, 3).map(platform => (
                      <span
                        key={platform}
                        className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded"
                      >
                        {platform}
                      </span>
                    ))}
                    {post.target_platforms.length > 3 && (
                      <span className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded">
                        +{post.target_platforms.length - 3}
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-6 py-4">
                  {post.scheduled_at ? (
                    <div className="text-sm">
                      <p className="text-gray-900">
                        {new Date(post.scheduled_at).toLocaleDateString()}
                      </p>
                      <p className="text-gray-500">
                        {new Date(post.scheduled_at).toLocaleTimeString([], { 
                          hour: '2-digit', 
                          minute: '2-digit' 
                        })}
                      </p>
                    </div>
                  ) : (
                    <span className="text-gray-400">Not scheduled</span>
                  )}
                </td>
                <td className="px-6 py-4">
                  {post.results && post.results.length > 0 ? (
                    <div className="space-y-1">
                      {post.results.slice(0, 2).map((result, index) => (
                        <div key={index} className="flex items-center text-xs">
                          <span className="w-16 truncate">{result.platform}</span>
                          <span className={`ml-2 px-1 py-0.5 rounded ${
                            result.status === 'published' ? 'bg-green-100 text-green-800' :
                            result.status === 'failed' ? 'bg-red-100 text-red-800' :
                            'bg-yellow-100 text-yellow-800'
                          }`}>
                            {result.status}
                          </span>
                        </div>
                      ))}
                      {post.results.length > 2 && (
                        <p className="text-xs text-gray-500">+{post.results.length - 2} more</p>
                      )}
                    </div>
                  ) : (
                    <span className="text-gray-400">No results</span>
                  )}
                </td>
                <td className="px-6 py-4">
                  <div className="flex space-x-2">
                    <button
                      onClick={() => onPostSelect?.(post)}
                      className="text-blue-600 hover:text-blue-800 text-sm"
                    >
                      View
                    </button>
                    {post.status === PostStatus.FAILED && (
                      <button
                        onClick={() => handleRetryPost(post)}
                        className="text-green-600 hover:text-green-800 text-sm"
                      >
                        Retry
                      </button>
                    )}
                    {post.status === PostStatus.SCHEDULED && (
                      <button
                        onClick={() => handleCancelPost(post)}
                        className="text-red-600 hover:text-red-800 text-sm"
                      >
                        Cancel
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {pagination.total > pagination.limit && (
        <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between">
          <div className="text-sm text-gray-700">
            Showing {pagination.skip + 1} to {Math.min(pagination.skip + pagination.limit, pagination.total)} of {pagination.total} posts
          </div>
          <div className="flex space-x-2">
            <button
              onClick={() => setPagination(prev => ({ ...prev, skip: Math.max(0, prev.skip - prev.limit) }))}
              disabled={pagination.skip === 0}
              className="px-3 py-1 text-sm border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <button
              onClick={() => setPagination(prev => ({ ...prev, skip: prev.skip + prev.limit }))}
              disabled={pagination.skip + pagination.limit >= pagination.total}
              className="px-3 py-1 text-sm border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default PostStatusDashboard;