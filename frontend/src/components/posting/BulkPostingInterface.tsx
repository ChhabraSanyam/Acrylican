import React, { useState, useEffect } from 'react';
import { Post, BulkPostingRequest, PostingResult } from '../../types/post';
import { postService } from '../../services/post';
import { contentService } from '../../services/content';

interface BulkPostingInterfaceProps {
  posts: Post[];
  onBulkAction?: (results: PostingResult[]) => void;
  onClose?: () => void;
}

interface BulkAction {
  type: 'publish' | 'schedule' | 'delete' | 'duplicate';
  label: string;
  description: string;
  icon: string;
}

const bulkActions: BulkAction[] = [
  {
    type: 'publish',
    label: 'Publish Now',
    description: 'Publish selected posts immediately',
    icon: '🚀'
  },
  {
    type: 'schedule',
    label: 'Schedule',
    description: 'Schedule selected posts for later',
    icon: '⏰'
  },
  {
    type: 'delete',
    label: 'Delete',
    description: 'Delete selected posts',
    icon: '🗑️'
  },
  {
    type: 'duplicate',
    label: 'Duplicate',
    description: 'Create copies of selected posts',
    icon: '📋'
  }
];

export const BulkPostingInterface: React.FC<BulkPostingInterfaceProps> = ({
  posts,
  onBulkAction,
  onClose
}) => {
  const [selectedPosts, setSelectedPosts] = useState<Set<string>>(new Set());
  const [selectedAction, setSelectedAction] = useState<BulkAction | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<PostingResult[]>([]);
  const [platforms, setPlatforms] = useState<Record<string, any>>({});
  
  // Schedule settings
  const [scheduleDate, setScheduleDate] = useState('');
  const [scheduleTime, setScheduleTime] = useState('');
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>([]);
  const [staggerPosts, setStaggerPosts] = useState(false);
  const [staggerInterval, setStaggerInterval] = useState(15); // minutes

  useEffect(() => {
    loadPlatforms();
  }, []);

  const loadPlatforms = async () => {
    try {
      const response = await contentService.getSupportedPlatforms();
      setPlatforms(response.platforms);
    } catch (err) {
      console.error('Failed to load platforms:', err);
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

  const handleActionSelect = (action: BulkAction) => {
    setSelectedAction(action);
    setError(null);
    setResults([]);
  };

  const handleExecuteAction = async () => {
    if (!selectedAction || selectedPosts.size === 0) return;

    setIsProcessing(true);
    setError(null);
    setResults([]);

    try {
      const postIds = Array.from(selectedPosts);
      let actionResults: PostingResult[] = [];

      switch (selectedAction.type) {
        case 'publish':
          actionResults = await handleBulkPublish(postIds);
          break;
        case 'schedule':
          actionResults = await handleBulkSchedule(postIds);
          break;
        case 'delete':
          await handleBulkDelete(postIds);
          break;
        case 'duplicate':
          await handleBulkDuplicate(postIds);
          break;
      }

      setResults(actionResults);
      onBulkAction?.(actionResults);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to execute bulk action');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleBulkPublish = async (postIds: string[]): Promise<PostingResult[]> => {
    const request: BulkPostingRequest = {
      post_ids: postIds,
      platforms: selectedPlatforms.length > 0 ? selectedPlatforms : undefined
    };

    return await postService.bulkPublish(request);
  };

  const handleBulkSchedule = async (postIds: string[]): Promise<PostingResult[]> => {
    if (!scheduleDate || !scheduleTime) {
      throw new Error('Please select a date and time for scheduling');
    }

    const baseDateTime = new Date(`${scheduleDate}T${scheduleTime}`);
    const results: PostingResult[] = [];

    for (let i = 0; i < postIds.length; i++) {
      const scheduledAt = new Date(baseDateTime);
      
      if (staggerPosts) {
        scheduledAt.setMinutes(scheduledAt.getMinutes() + (i * staggerInterval));
      }

      const request: BulkPostingRequest = {
        post_ids: [postIds[i]],
        scheduled_at: scheduledAt.toISOString(),
        platforms: selectedPlatforms.length > 0 ? selectedPlatforms : undefined
      };

      const result = await postService.bulkSchedule(request);
      results.push(...result);
    }

    return results;
  };

  const handleBulkDelete = async (postIds: string[]): Promise<void> => {
    for (const postId of postIds) {
      await postService.deletePost(postId);
    }
  };

  const handleBulkDuplicate = async (postIds: string[]): Promise<void> => {
    for (const postId of postIds) {
      const originalPost = posts.find(p => p.id === postId);
      if (originalPost) {
        const duplicateData = {
          title: `${originalPost.title} (Copy)`,
          description: originalPost.description,
          hashtags: originalPost.hashtags,
          images: originalPost.images,
          target_platforms: originalPost.target_platforms,
          product_data: originalPost.product_data,
          platform_specific_content: originalPost.platform_specific_content
        };
        await postService.createPost(duplicateData);
      }
    }
  };

  const getPostStatusColor = (status: string) => {
    switch (status) {
      case 'draft':
        return 'bg-gray-100 text-gray-800';
      case 'scheduled':
        return 'bg-blue-100 text-blue-800';
      case 'published':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const renderActionForm = () => {
    if (!selectedAction) return null;

    switch (selectedAction.type) {
      case 'publish':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Target Platforms (optional)
              </label>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(platforms).map(([key, platform]) => (
                  <label key={key} className="flex items-center">
                    <input
                      type="checkbox"
                      checked={selectedPlatforms.includes(key)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedPlatforms(prev => [...prev, key]);
                        } else {
                          setSelectedPlatforms(prev => prev.filter(p => p !== key));
                        }
                      }}
                      className="mr-2"
                    />
                    <span className="text-sm">{platform.name}</span>
                  </label>
                ))}
              </div>
              <p className="text-xs text-gray-500 mt-1">
                Leave empty to use each post's original platform selection
              </p>
            </div>
          </div>
        );

      case 'schedule':
        return (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Date
                </label>
                <input
                  type="date"
                  value={scheduleDate}
                  onChange={(e) => setScheduleDate(e.target.value)}
                  min={new Date().toISOString().split('T')[0]}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Time
                </label>
                <input
                  type="time"
                  value={scheduleTime}
                  onChange={(e) => setScheduleTime(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div>
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={staggerPosts}
                  onChange={(e) => setStaggerPosts(e.target.checked)}
                  className="mr-2"
                />
                <span className="text-sm font-medium text-gray-700">
                  Stagger posts over time
                </span>
              </label>
              {staggerPosts && (
                <div className="mt-2 ml-6">
                  <label className="block text-sm text-gray-600 mb-1">
                    Interval between posts (minutes)
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="1440"
                    value={staggerInterval}
                    onChange={(e) => setStaggerInterval(parseInt(e.target.value) || 15)}
                    className="w-24 px-2 py-1 border border-gray-300 rounded text-sm"
                  />
                </div>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Target Platforms (optional)
              </label>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(platforms).map(([key, platform]) => (
                  <label key={key} className="flex items-center">
                    <input
                      type="checkbox"
                      checked={selectedPlatforms.includes(key)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedPlatforms(prev => [...prev, key]);
                        } else {
                          setSelectedPlatforms(prev => prev.filter(p => p !== key));
                        }
                      }}
                      className="mr-2"
                    />
                    <span className="text-sm">{platform.name}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>
        );

      case 'delete':
        return (
          <div className="bg-red-50 border border-red-200 rounded-md p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">
                  Confirm Deletion
                </h3>
                <p className="text-sm text-red-700 mt-1">
                  This action cannot be undone. {selectedPosts.size} post(s) will be permanently deleted.
                </p>
              </div>
            </div>
          </div>
        );

      case 'duplicate':
        return (
          <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
            <p className="text-sm text-blue-700">
              {selectedPosts.size} post(s) will be duplicated with "(Copy)" added to their titles.
              The duplicated posts will be created as drafts.
            </p>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900">
              Bulk Post Management
            </h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <div className="flex h-[calc(90vh-80px)]">
          {/* Post Selection Panel */}
          <div className="w-1/2 border-r border-gray-200 overflow-y-auto">
            <div className="p-4 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <h3 className="font-medium text-gray-900">
                  Select Posts ({selectedPosts.size} selected)
                </h3>
                <button
                  onClick={handleSelectAll}
                  className="text-sm text-blue-600 hover:text-blue-800"
                >
                  {selectedPosts.size === posts.length ? 'Deselect All' : 'Select All'}
                </button>
              </div>
            </div>

            <div className="p-4 space-y-3">
              {posts.map(post => (
                <div
                  key={post.id}
                  className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                    selectedPosts.has(post.id)
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                  onClick={() => handleSelectPost(post.id)}
                >
                  <div className="flex items-start space-x-3">
                    <input
                      type="checkbox"
                      checked={selectedPosts.has(post.id)}
                      onChange={() => handleSelectPost(post.id)}
                      className="mt-1"
                    />
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-gray-900 truncate">{post.title}</p>
                      <p className="text-sm text-gray-500 truncate">{post.description}</p>
                      <div className="flex items-center space-x-2 mt-2">
                        <span className={`px-2 py-1 text-xs rounded-full ${getPostStatusColor(post.status)}`}>
                          {post.status}
                        </span>
                        <span className="text-xs text-gray-500">
                          {post.target_platforms.length} platform(s)
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Action Panel */}
          <div className="w-1/2 flex flex-col">
            <div className="p-4 border-b border-gray-200">
              <h3 className="font-medium text-gray-900 mb-4">Choose Action</h3>
              <div className="grid grid-cols-2 gap-3">
                {bulkActions.map(action => (
                  <button
                    key={action.type}
                    onClick={() => handleActionSelect(action)}
                    disabled={selectedPosts.size === 0}
                    className={`p-3 text-left border rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
                      selectedAction?.type === action.type
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="flex items-center space-x-2">
                      <span className="text-lg">{action.icon}</span>
                      <div>
                        <p className="font-medium text-gray-900">{action.label}</p>
                        <p className="text-xs text-gray-500">{action.description}</p>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Action Form */}
            <div className="flex-1 p-4 overflow-y-auto">
              {selectedAction && (
                <div>
                  <h4 className="font-medium text-gray-900 mb-4">
                    {selectedAction.icon} {selectedAction.label} Settings
                  </h4>
                  {renderActionForm()}
                </div>
              )}

              {error && (
                <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-md">
                  <p className="text-red-800">{error}</p>
                </div>
              )}

              {results.length > 0 && (
                <div className="mt-4">
                  <h4 className="font-medium text-gray-900 mb-2">Results</h4>
                  <div className="space-y-2">
                    {results.map((result, index) => (
                      <div key={index} className="p-2 bg-gray-50 rounded text-sm">
                        <p className="font-medium">Post {result.post_id}</p>
                        <p className={result.success ? 'text-green-600' : 'text-red-600'}>
                          {result.success ? 'Success' : 'Failed'}: {result.message}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-gray-200">
              <div className="flex justify-end space-x-3">
                <button
                  onClick={onClose}
                  className="px-4 py-2 text-gray-600 hover:text-gray-800"
                >
                  Cancel
                </button>
                <button
                  onClick={handleExecuteAction}
                  disabled={!selectedAction || selectedPosts.size === 0 || isProcessing}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isProcessing ? 'Processing...' : `Execute ${selectedAction?.label || 'Action'}`}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BulkPostingInterface;