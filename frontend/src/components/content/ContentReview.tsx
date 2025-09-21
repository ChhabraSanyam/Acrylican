import React, { useState, useEffect } from 'react';
import { GeneratedContent, Platform, ContentReviewState, EditableContent } from '../../types/content';
import { contentService } from '../../services/content';
import ContentPreview from './ContentPreview';
import ContentEditor from './ContentEditor';
import PlatformSelector from './PlatformSelector';

interface ContentReviewProps {
  generatedContent: GeneratedContent;
  onApprove: (editedContent: Record<string, EditableContent>) => void;
  onReject: () => void;
  onRegenerate: () => void;
  isLoading?: boolean;
}

const ContentReview: React.FC<ContentReviewProps> = ({
  generatedContent,
  onApprove,
  onReject,
  onRegenerate,
  isLoading = false
}) => {
  const [platforms, setPlatforms] = useState<Record<string, Platform>>({});
  const [reviewState, setReviewState] = useState<ContentReviewState>({
    originalContent: generatedContent,
    editedContent: {},
    selectedPlatforms: Object.keys(generatedContent.platform_specific),
    isEditing: false,
    validationResults: {}
  });
  const [loadingPlatforms, setLoadingPlatforms] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load platforms on component mount
  useEffect(() => {
    loadPlatforms();
  }, []);

  // Initialize edited content when generated content changes
  useEffect(() => {
    initializeEditedContent();
  }, [generatedContent]);

  const loadPlatforms = async () => {
    try {
      setLoadingPlatforms(true);
      const response = await contentService.getSupportedPlatforms();
      setPlatforms(response.platforms);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoadingPlatforms(false);
    }
  };

  const initializeEditedContent = () => {
    const editedContent: Record<string, EditableContent> = {};
    
    Object.keys(generatedContent.platform_specific).forEach(platform => {
      const platformContent = generatedContent.platform_specific[platform];
      editedContent[platform] = {
        title: platformContent.title,
        description: platformContent.description,
        hashtags: [...platformContent.hashtags],
        platform
      };
    });

    setReviewState(prev => ({
      ...prev,
      originalContent: generatedContent,
      editedContent,
      selectedPlatforms: Object.keys(generatedContent.platform_specific)
    }));
  };

  const handlePlatformToggle = (platform: string, enabled: boolean) => {
    setReviewState(prev => ({
      ...prev,
      selectedPlatforms: enabled 
        ? [...prev.selectedPlatforms, platform]
        : prev.selectedPlatforms.filter(p => p !== platform)
    }));
  };

  const handleContentEdit = (platform: string, field: keyof EditableContent, value: any) => {
    setReviewState(prev => ({
      ...prev,
      editedContent: {
        ...prev.editedContent,
        [platform]: {
          ...prev.editedContent[platform],
          [field]: value
        }
      }
    }));
  };

  const handleValidationUpdate = (platform: string, validationResult: any) => {
    setReviewState(prev => ({
      ...prev,
      validationResults: {
        ...prev.validationResults,
        [platform]: validationResult
      }
    }));
  };

  const toggleEditMode = () => {
    setReviewState(prev => ({
      ...prev,
      isEditing: !prev.isEditing
    }));
  };

  const handleApprove = () => {
    // Filter edited content to only include selected platforms
    const approvedContent: Record<string, EditableContent> = {};
    reviewState.selectedPlatforms.forEach(platform => {
      if (reviewState.editedContent[platform]) {
        approvedContent[platform] = reviewState.editedContent[platform];
      }
    });
    
    onApprove(approvedContent);
  };

  const hasValidationErrors = () => {
    return reviewState.selectedPlatforms.some(platform => {
      const validation = reviewState.validationResults[platform];
      return validation && !validation.valid;
    });
  };

  const getValidationSummary = () => {
    const totalIssues = reviewState.selectedPlatforms.reduce((count, platform) => {
      const validation = reviewState.validationResults[platform];
      return count + (validation?.issues?.length || 0);
    }, 0);

    const validPlatforms = reviewState.selectedPlatforms.filter(platform => {
      const validation = reviewState.validationResults[platform];
      return validation && validation.valid;
    }).length;

    return {
      totalIssues,
      validPlatforms,
      totalPlatforms: reviewState.selectedPlatforms.length
    };
  };

  if (loadingPlatforms) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2 text-gray-600">Loading platforms...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">Error loading platforms</h3>
            <p className="mt-1 text-sm text-red-700">{error}</p>
            <button
              onClick={loadPlatforms}
              className="mt-2 text-sm text-red-800 underline hover:text-red-900"
            >
              Try again
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Review Generated Content</h2>
        <p className="text-gray-600">
          Review and edit the AI-generated content before posting to your selected platforms.
        </p>
      </div>

      {/* Platform Selection */}
      <div className="mb-6">
        <PlatformSelector
          platforms={platforms}
          selectedPlatforms={reviewState.selectedPlatforms}
          availablePlatforms={Object.keys(generatedContent.platform_specific)}
          onPlatformToggle={handlePlatformToggle}
        />
      </div>

      {/* Edit Mode Toggle */}
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <button
            onClick={toggleEditMode}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              reviewState.isEditing
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {reviewState.isEditing ? 'Exit Edit Mode' : 'Edit Content'}
          </button>
          
          {reviewState.isEditing && (
            <div className="flex items-center space-x-4">
              {hasValidationErrors() ? (
                <div className="flex items-center text-red-600">
                  <svg className="h-5 w-5 mr-1" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                  <span className="text-sm font-medium">
                    {getValidationSummary().totalIssues} validation issue{getValidationSummary().totalIssues !== 1 ? 's' : ''} found
                  </span>
                </div>
              ) : (
                <div className="flex items-center text-green-600">
                  <svg className="h-5 w-5 mr-1" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <span className="text-sm font-medium">
                    All content is valid ({getValidationSummary().validPlatforms}/{getValidationSummary().totalPlatforms} platforms)
                  </span>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Content Preview/Editor */}
      <div className="space-y-6">
        {reviewState.selectedPlatforms.map(platform => {
          const platformData = platforms[platform];
          const editedContent = reviewState.editedContent[platform];
          
          if (!platformData || !editedContent) return null;

          return (
            <div key={platform} className="border border-gray-200 rounded-lg p-4">
              <div className="flex items-center mb-4">
                <h3 className="text-lg font-semibold text-gray-900">{platformData.name}</h3>
                <span className="ml-2 px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded-full">
                  {platformData.type.replace('_', ' ')}
                </span>
              </div>
              
              {reviewState.isEditing ? (
                <ContentEditor
                  content={editedContent}
                  platform={platformData}
                  onContentChange={(field, value) => handleContentEdit(platform, field, value)}
                  onValidationUpdate={(result) => handleValidationUpdate(platform, result)}
                />
              ) : (
                <ContentPreview
                  content={editedContent}
                  platform={platformData}
                  validationResult={reviewState.validationResults[platform]}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Progress Summary */}
      {reviewState.selectedPlatforms.length > 0 && (
        <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-sm font-medium text-blue-900">Content Review Progress</h4>
            <span className="text-sm text-blue-700">
              {getValidationSummary().validPlatforms}/{getValidationSummary().totalPlatforms} platforms ready
            </span>
          </div>
          <div className="w-full bg-blue-200 rounded-full h-2">
            <div 
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ 
                width: `${(getValidationSummary().validPlatforms / getValidationSummary().totalPlatforms) * 100}%` 
              }}
            ></div>
          </div>
          <div className="mt-2 text-xs text-blue-700">
            {hasValidationErrors() 
              ? `Fix ${getValidationSummary().totalIssues} issue${getValidationSummary().totalIssues !== 1 ? 's' : ''} to continue`
              : 'All content is ready for posting!'
            }
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="mt-8 flex items-center justify-between">
        <div className="flex space-x-3">
          <button
            onClick={onReject}
            disabled={isLoading}
            className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? (
              <div className="flex items-center">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600 mr-2"></div>
                Rejecting...
              </div>
            ) : (
              'Reject'
            )}
          </button>
          <button
            onClick={onRegenerate}
            disabled={isLoading}
            className="px-6 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? (
              <div className="flex items-center">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Regenerating...
              </div>
            ) : (
              'Regenerate'
            )}
          </button>
        </div>
        
        <button
          onClick={handleApprove}
          disabled={isLoading || hasValidationErrors() || reviewState.selectedPlatforms.length === 0}
          className="px-8 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
        >
          {isLoading ? (
            <div className="flex items-center">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
              Processing...
            </div>
          ) : (
            `Approve & Post (${reviewState.selectedPlatforms.length})`
          )}
        </button>
      </div>
    </div>
  );
};

export default ContentReview;