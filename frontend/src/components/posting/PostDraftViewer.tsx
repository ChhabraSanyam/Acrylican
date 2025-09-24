import React, { useState, useEffect } from 'react';
import { Post } from '../../types/post';
import { Platform, EditableContent } from '../../types/content';
import { contentService } from '../../services/content';
import ContentPreview from '../content/ContentPreview';

interface PostDraftViewerProps {
  post: Post;
  onEdit?: (post: Post) => void;
  onPublish?: (post: Post) => void;
  onClose?: () => void;
}

export const PostDraftViewer: React.FC<PostDraftViewerProps> = ({
  post,
  onEdit,
  onPublish,
  onClose
}) => {
  const [platforms, setPlatforms] = useState<Record<string, Platform>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPlatform, setSelectedPlatform] = useState<string>('');

  useEffect(() => {
    loadPlatforms();
  }, []);

  useEffect(() => {
    // Set the first platform as selected by default
    if (post.target_platforms.length > 0 && !selectedPlatform) {
      setSelectedPlatform(post.target_platforms[0]);
    }
  }, [post.target_platforms, selectedPlatform]);

  const loadPlatforms = async () => {
    try {
      setLoading(true);
      const response = await contentService.getSupportedPlatforms();
      setPlatforms(response.platforms);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load platforms');
    } finally {
      setLoading(false);
    }
  };

  const getPlatformContent = (platformKey: string): EditableContent | null => {
    if (!post.platform_specific_content || !post.platform_specific_content[platformKey]) {
      return null;
    }

    const content = post.platform_specific_content[platformKey];
    return {
      title: content.title || post.title,
      description: content.description || post.description,
      hashtags: content.hashtags || post.hashtags,
      platform: platformKey
    };
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const getStatusColor = (status: string) => {
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

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-200 rounded w-1/3"></div>
          <div className="h-4 bg-gray-200 rounded w-1/2"></div>
          <div className="space-y-3">
            <div className="h-32 bg-gray-200 rounded"></div>
            <div className="h-32 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="text-center">
          <div className="text-red-600 mb-4">
            <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">Error Loading Post</h3>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
          >
            Close
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-lg max-w-6xl mx-auto">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">{post.title}</h2>
            <div className="flex items-center space-x-4 mt-2">
              <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(post.status)}`}>
                {post.status.charAt(0).toUpperCase() + post.status.slice(1)}
              </span>
              <span className="text-sm text-gray-500">
                Created: {formatDate(post.created_at)}
              </span>
              {post.scheduled_at && (
                <span className="text-sm text-gray-500">
                  Scheduled: {formatDate(post.scheduled_at)}
                </span>
              )}
            </div>
          </div>
          <div className="flex items-center space-x-3">
            {onEdit && (
              <button
                onClick={() => onEdit(post)}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
              >
                Edit Post
              </button>
            )}
            {onPublish && post.status === 'draft' && (
              <button
                onClick={() => onPublish(post)}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                Publish Now
              </button>
            )}
            {onClose && (
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Post Overview */}
          <div className="lg:col-span-1">
            <div className="bg-gray-50 rounded-lg p-4 space-y-4">
              <h3 className="text-lg font-medium text-gray-900">Post Overview</h3>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Original Description
                </label>
                <p className="text-sm text-gray-600 bg-white p-3 rounded border">
                  {post.description}
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Target Platforms ({post.target_platforms.length})
                </label>
                <div className="flex flex-wrap gap-2">
                  {post.target_platforms.map(platform => (
                    <button
                      key={platform}
                      onClick={() => setSelectedPlatform(platform)}
                      className={`px-3 py-1 text-sm rounded-full transition-colors ${
                        selectedPlatform === platform
                          ? 'bg-blue-100 text-blue-800 ring-2 ring-blue-200'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      {platforms[platform]?.name || platform}
                    </button>
                  ))}
                </div>
              </div>

              {post.hashtags.length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Original Hashtags
                  </label>
                  <div className="text-sm text-blue-600 bg-white p-3 rounded border">
                    {post.hashtags.map(tag => tag.startsWith('#') ? tag : `#${tag}`).join(' ')}
                  </div>
                </div>
              )}

              {post.images.length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Images ({post.images.length})
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    {post.images.slice(0, 4).map((imageUrl, index) => (
                      <div key={index} className="aspect-square bg-gray-200 rounded overflow-hidden">
                        <img
                          src={imageUrl}
                          alt={`Product ${index + 1}`}
                          className="w-full h-full object-cover"
                          onError={(e) => {
                            const target = e.target as HTMLImageElement;
                            target.style.display = 'none';
                          }}
                        />
                      </div>
                    ))}
                    {post.images.length > 4 && (
                      <div className="aspect-square bg-gray-100 rounded flex items-center justify-center">
                        <span className="text-sm text-gray-500">+{post.images.length - 4} more</span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Platform-Specific Content */}
          <div className="lg:col-span-2">
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium text-gray-900">
                  Platform-Specific Content
                </h3>
                {post.platform_specific_content && Object.keys(post.platform_specific_content).length > 0 ? (
                  <span className="text-sm text-green-600 bg-green-50 px-2 py-1 rounded">
                    ✓ AI-Generated Content Available
                  </span>
                ) : (
                  <span className="text-sm text-gray-500 bg-gray-50 px-2 py-1 rounded">
                    No specialized content
                  </span>
                )}
              </div>

              {selectedPlatform && (
                <div className="bg-white border border-gray-200 rounded-lg">
                  <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
                    <div className="flex items-center justify-between">
                      <h4 className="font-medium text-gray-900">
                        {platforms[selectedPlatform]?.name || selectedPlatform}
                      </h4>
                      <span className="text-xs text-gray-500 bg-white px-2 py-1 rounded">
                        {platforms[selectedPlatform]?.type.replace('_', ' ') || 'Platform'}
                      </span>
                    </div>
                  </div>
                  
                  <div className="p-4">
                    {getPlatformContent(selectedPlatform) ? (
                      <ContentPreview
                        content={getPlatformContent(selectedPlatform)!}
                        platform={platforms[selectedPlatform]}
                      />
                    ) : (
                      <div className="text-center py-8">
                        <div className="text-gray-400 mb-4">
                          <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                          </svg>
                        </div>
                        <h4 className="text-lg font-medium text-gray-900 mb-2">
                          No Specialized Content
                        </h4>
                        <p className="text-gray-600 mb-4">
                          This platform will use the original post content (title, description, and hashtags).
                        </p>
                        <div className="bg-gray-50 rounded-lg p-4 text-left">
                          <div className="space-y-3">
                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
                              <p className="text-gray-900">{post.title}</p>
                            </div>
                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                              <p className="text-gray-900 whitespace-pre-wrap">{post.description}</p>
                            </div>
                            {post.hashtags.length > 0 && (
                              <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Hashtags</label>
                                <p className="text-blue-600">
                                  {post.hashtags.map(tag => tag.startsWith('#') ? tag : `#${tag}`).join(' ')}
                                </p>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Platform Tabs for Quick Navigation */}
              {post.target_platforms.length > 1 && (
                <div className="bg-gray-50 rounded-lg p-4">
                  <h4 className="text-sm font-medium text-gray-700 mb-3">Quick Platform Navigation</h4>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                    {post.target_platforms.map(platform => {
                      const hasSpecializedContent = post.platform_specific_content && 
                        post.platform_specific_content[platform];
                      
                      return (
                        <button
                          key={platform}
                          onClick={() => setSelectedPlatform(platform)}
                          className={`p-3 text-left rounded-lg border transition-colors ${
                            selectedPlatform === platform
                              ? 'border-blue-300 bg-blue-50'
                              : 'border-gray-200 bg-white hover:bg-gray-50'
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-medium text-gray-900">
                              {platforms[platform]?.name || platform}
                            </span>
                            {hasSpecializedContent ? (
                              <span className="w-2 h-2 bg-green-400 rounded-full" title="Has specialized content"></span>
                            ) : (
                              <span className="w-2 h-2 bg-gray-300 rounded-full" title="Uses original content"></span>
                            )}
                          </div>
                          <span className="text-xs text-gray-500">
                            {platforms[platform]?.type.replace('_', ' ') || 'Platform'}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PostDraftViewer;