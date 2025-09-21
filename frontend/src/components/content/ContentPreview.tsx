import React from 'react';
import { EditableContent, Platform, ContentValidationResult } from '../../types/content';

interface ContentPreviewProps {
  content: EditableContent;
  platform: Platform;
  validationResult?: ContentValidationResult;
}

const ContentPreview: React.FC<ContentPreviewProps> = ({
  content,
  platform,
  validationResult
}) => {
  const getCharacterCountColor = (current: number, max: number) => {
    const percentage = (current / max) * 100;
    if (percentage >= 100) return 'text-red-600 font-semibold';
    if (percentage >= 90) return 'text-yellow-600 font-medium';
    if (percentage >= 80) return 'text-orange-500';
    return 'text-gray-500';
  };

  const getFieldBorderColor = (field: string) => {
    if (!validationResult) return 'border-gray-200';
    
    const hasError = validationResult.issues.some(issue => issue.field === field);
    if (hasError) return 'border-red-300 bg-red-50';
    
    return 'border-green-300 bg-green-50';
  };

  const formatHashtags = (hashtags: string[]) => {
    return hashtags.map(tag => tag.startsWith('#') ? tag : `#${tag}`).join(' ');
  };

  return (
    <div className="space-y-4">
      {/* Title Section */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm font-medium text-gray-700">Title</label>
          <span className={`text-xs ${getCharacterCountColor(content.title.length, platform.title_max_length)}`}>
            {content.title.length}/{platform.title_max_length}
          </span>
        </div>
        <div className={`rounded-lg p-3 border ${getFieldBorderColor('title')}`}>
          <p className="text-gray-900 font-medium">{content.title || 'No title provided'}</p>
        </div>
        {validationResult?.issues.some(issue => issue.field === 'title') && (
          <div className="mt-1 text-sm text-red-600">
            {validationResult.issues.find(issue => issue.field === 'title')?.issue}
          </div>
        )}
      </div>

      {/* Description Section */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm font-medium text-gray-700">Description</label>
          <span className={`text-xs ${getCharacterCountColor(content.description.length, platform.description_max_length)}`}>
            {content.description.length}/{platform.description_max_length}
          </span>
        </div>
        <div className={`rounded-lg p-3 border min-h-[100px] ${getFieldBorderColor('description')}`}>
          <p className="text-gray-900 whitespace-pre-wrap">{content.description || 'No description provided'}</p>
        </div>
        {validationResult?.issues.some(issue => issue.field === 'description') && (
          <div className="mt-1 text-sm text-red-600">
            {validationResult.issues.find(issue => issue.field === 'description')?.issue}
          </div>
        )}
      </div>

      {/* Hashtags Section */}
      {platform.hashtag_limit > 0 && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium text-gray-700">Hashtags</label>
            <span className={`text-xs ${getCharacterCountColor(content.hashtags.length, platform.hashtag_limit)}`}>
              {content.hashtags.length}/{platform.hashtag_limit}
            </span>
          </div>
          <div className={`rounded-lg p-3 border ${getFieldBorderColor('hashtags')}`}>
            {content.hashtags.length > 0 ? (
              <p className="text-blue-600">{formatHashtags(content.hashtags)}</p>
            ) : (
              <p className="text-gray-500 italic">No hashtags provided</p>
            )}
          </div>
          {validationResult?.issues.some(issue => issue.field === 'hashtags') && (
            <div className="mt-1 text-sm text-red-600">
              {validationResult.issues.find(issue => issue.field === 'hashtags')?.issue}
            </div>
          )}
        </div>
      )}

      {/* Platform-specific Preview */}
      <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
        <h4 className="text-sm font-medium text-blue-900 mb-2">Platform Preview</h4>
        <div className="bg-white rounded-lg p-3 border">
          <div className="space-y-2">
            <h5 className="font-semibold text-gray-900 text-sm">{content.title}</h5>
            <p className="text-gray-700 text-sm leading-relaxed">{content.description}</p>
            {content.hashtags.length > 0 && platform.hashtag_limit > 0 && (
              <p className="text-blue-600 text-sm">{formatHashtags(content.hashtags)}</p>
            )}
          </div>
        </div>
      </div>

      {/* Validation Status */}
      {validationResult && (
        <div className={`rounded-lg p-3 border ${
          validationResult.valid 
            ? 'bg-green-50 border-green-200' 
            : 'bg-red-50 border-red-200'
        }`}>
          <div className="flex items-center">
            {validationResult.valid ? (
              <>
                <svg className="h-5 w-5 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <span className="text-sm font-medium text-green-800">Content is valid for {platform.name}</span>
              </>
            ) : (
              <>
                <svg className="h-5 w-5 text-red-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                <span className="text-sm font-medium text-red-800">
                  {validationResult.issues.length} validation issue{validationResult.issues.length !== 1 ? 's' : ''}
                </span>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ContentPreview;