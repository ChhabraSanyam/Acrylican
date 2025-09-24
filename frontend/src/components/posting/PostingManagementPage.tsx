import React, { useState, useEffect } from 'react';
import { Post } from '../../types/post';
import { postService } from '../../services/post';
import PostCreationWizard from './PostCreationWizard';
import SchedulingInterface from './SchedulingInterface';
import PostStatusDashboard from './PostStatusDashboard';
import BulkPostingInterface from './BulkPostingInterface';
import PostDraftViewer from './PostDraftViewer';

type ViewMode = 'dashboard' | 'create' | 'schedule' | 'bulk';

export const PostingManagementPage: React.FC = () => {
  const [currentView, setCurrentView] = useState<ViewMode>('dashboard');
  const [posts, setPosts] = useState<Post[]>([]);
  const [selectedPost, setSelectedPost] = useState<Post | null>(null);
  const [viewingDraft, setViewingDraft] = useState<Post | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    loadPosts();
  }, [refreshKey]);

  const loadPosts = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await postService.getPosts(0, 100); // Load more posts for management
      setPosts(response.posts);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load posts');
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = () => {
    setRefreshKey(prev => prev + 1);
  };

  const handlePostCreated = (post: Post) => {
    setPosts(prev => [post, ...prev]);
    setCurrentView('dashboard');
  };

  const handlePostScheduled = (post: Post) => {
    setPosts(prev => prev.map(p => p.id === post.id ? post : p));
  };

  const handleBulkAction = () => {
    handleRefresh();
    setCurrentView('dashboard');
  };

  const handlePostSelect = (post: Post) => {
    if (post.status === 'draft' && post.platform_specific_content && Object.keys(post.platform_specific_content).length > 0) {
      setViewingDraft(post);
    } else {
      setSelectedPost(post);
    }
  };

  const handlePublishDraft = async (post: Post) => {
    try {
      await postService.publishPost({ post_id: post.id });
      setViewingDraft(null);
      handleRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to publish post');
    }
  };

  const getViewTitle = () => {
    switch (currentView) {
      case 'dashboard':
        return 'Post Management Dashboard';
      case 'create':
        return 'Create New Post';
      case 'schedule':
        return 'Post Scheduling';
      case 'bulk':
        return 'Bulk Post Management';
      default:
        return 'Post Management';
    }
  };

  const renderCurrentView = () => {
    switch (currentView) {
      case 'create':
        return (
          <PostCreationWizard
            onPostCreated={handlePostCreated}
            onCancel={() => setCurrentView('dashboard')}
          />
        );
      case 'schedule':
        return (
          <SchedulingInterface
            posts={posts}
            onPostScheduled={handlePostScheduled}
            onRefresh={handleRefresh}
          />
        );
      case 'bulk':
        return (
          <BulkPostingInterface
            posts={posts}
            onBulkAction={handleBulkAction}
            onClose={() => setCurrentView('dashboard')}
          />
        );
      case 'dashboard':
      default:
        return (
          <PostStatusDashboard
            onPostSelect={handlePostSelect}
            onRefresh={handleRefresh}
          />
        );
    }
  };

  if (loading && posts.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading posts...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation Header */}
      <div className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-8">
              <h1 className="text-xl font-semibold text-gray-900">
                {getViewTitle()}
              </h1>
              
              {/* View Navigation */}
              <nav className="flex space-x-4">
                <button
                  onClick={() => setCurrentView('dashboard')}
                  className={`px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                    currentView === 'dashboard'
                      ? 'bg-blue-100 text-blue-700'
                      : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  Dashboard
                </button>
                <button
                  onClick={() => setCurrentView('create')}
                  className={`px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                    currentView === 'create'
                      ? 'bg-blue-100 text-blue-700'
                      : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  Create Post
                </button>
                <button
                  onClick={() => setCurrentView('schedule')}
                  className={`px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                    currentView === 'schedule'
                      ? 'bg-blue-100 text-blue-700'
                      : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  Schedule
                </button>
                <button
                  onClick={() => setCurrentView('bulk')}
                  className={`px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                    currentView === 'bulk'
                      ? 'bg-blue-100 text-blue-700'
                      : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  Bulk Actions
                </button>
              </nav>
            </div>

            {/* Action Buttons */}
            <div className="flex items-center space-x-3">
              {currentView === 'dashboard' && (
                <>
                  <button
                    onClick={() => setCurrentView('create')}
                    className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 transition-colors"
                  >
                    Create Post
                  </button>
                  <button
                    onClick={() => setCurrentView('bulk')}
                    className="px-4 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-md hover:bg-gray-50 transition-colors"
                  >
                    Bulk Actions
                  </button>
                </>
              )}
              
              <button
                onClick={handleRefresh}
                className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
                title="Refresh"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-md">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">Error</h3>
                <p className="text-sm text-red-700 mt-1">{error}</p>
              </div>
              <div className="ml-auto pl-3">
                <button
                  onClick={() => setError(null)}
                  className="text-red-400 hover:text-red-600"
                >
                  <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Statistics Cards */}
        {currentView === 'dashboard' && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <div className="w-8 h-8 bg-blue-100 rounded-md flex items-center justify-center">
                    <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Total Posts</p>
                  <p className="text-2xl font-semibold text-gray-900">{posts.length}</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <div className="w-8 h-8 bg-green-100 rounded-md flex items-center justify-center">
                    <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Published</p>
                  <p className="text-2xl font-semibold text-gray-900">
                    {posts.filter(p => p.status === 'published').length}
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <div className="w-8 h-8 bg-yellow-100 rounded-md flex items-center justify-center">
                    <svg className="w-5 h-5 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Scheduled</p>
                  <p className="text-2xl font-semibold text-gray-900">
                    {posts.filter(p => p.status === 'scheduled').length}
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <div className="w-8 h-8 bg-red-100 rounded-md flex items-center justify-center">
                    <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                    </svg>
                  </div>
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Failed</p>
                  <p className="text-2xl font-semibold text-gray-900">
                    {posts.filter(p => p.status === 'failed').length}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Main View Content */}
        {renderCurrentView()}
      </div>

      {/* Post Detail Modal */}
      {selectedPost && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium text-gray-900">Post Details</h3>
                <button
                  onClick={() => setSelectedPost(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
            
            <div className="px-6 py-4 space-y-4">
              <div>
                <h4 className="font-medium text-gray-900">{selectedPost.title}</h4>
                <p className="text-gray-600 mt-1">{selectedPost.description}</p>
              </div>
              
              <div>
                <span className="text-sm font-medium text-gray-500">Status:</span>
                <span className={`ml-2 px-2 py-1 text-xs rounded-full ${
                  selectedPost.status === 'published' ? 'bg-green-100 text-green-800' :
                  selectedPost.status === 'scheduled' ? 'bg-blue-100 text-blue-800' :
                  selectedPost.status === 'failed' ? 'bg-red-100 text-red-800' :
                  'bg-gray-100 text-gray-800'
                }`}>
                  {selectedPost.status}
                </span>
              </div>
              
              <div>
                <span className="text-sm font-medium text-gray-500">Platforms:</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {selectedPost.target_platforms.map(platform => (
                    <span key={platform} className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded">
                      {platform}
                    </span>
                  ))}
                </div>
              </div>
              
              {selectedPost.scheduled_at && (
                <div>
                  <span className="text-sm font-medium text-gray-500">Scheduled for:</span>
                  <p className="text-gray-900">
                    {new Date(selectedPost.scheduled_at).toLocaleString()}
                  </p>
                </div>
              )}
              
              {selectedPost.results && selectedPost.results.length > 0 && (
                <div>
                  <span className="text-sm font-medium text-gray-500">Platform Results:</span>
                  <div className="mt-2 space-y-2">
                    {selectedPost.results.map((result, index) => (
                      <div key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                        <span className="text-sm">{result.platform}</span>
                        <span className={`px-2 py-1 text-xs rounded ${
                          result.status === 'published' ? 'bg-green-100 text-green-800' :
                          result.status === 'failed' ? 'bg-red-100 text-red-800' :
                          'bg-yellow-100 text-yellow-800'
                        }`}>
                          {result.status}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Draft Viewer Modal */}
      {viewingDraft && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="w-full max-w-6xl max-h-[90vh] overflow-y-auto">
            <PostDraftViewer
              post={viewingDraft}
              onEdit={(post) => {
                setViewingDraft(null);
                setSelectedPost(post);
              }}
              onPublish={handlePublishDraft}
              onClose={() => setViewingDraft(null)}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default PostingManagementPage;