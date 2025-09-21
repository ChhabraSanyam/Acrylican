import React, { useState, useEffect, useCallback } from 'react';
import { EditableContent, Platform, ContentValidationResult } from '../../types/content';
import { contentService } from '../../services/content';
import { debounce } from 'lodash';

interface ContentEditorProps {
  content: EditableContent;
  platform: Platform;
  onContentChange: (field: keyof EditableContent, value: any) => void;
  onValidationUpdate: (result: ContentValidationResult) => void;
}

const ContentEditor: React.FC<ContentEditorProps> = ({
  content,
  platform,
  onContentChange,
  onValidationUpdate
}) => {
  const [validationResult, setValidationResult] = useState<ContentValidationResult | null>(null);
  const [isValidating, setIsValidating] = useState(false);
  const [hashtagInput, setHashtagInput] = useState(content.hashtags.join(', '));

  // Debounced validation function
  const debouncedValidate = useCallback(
    debounce(async (contentToValidate: EditableContent) => {
      try {
        setIsValidating(true);
        const result = await contentService.validateContent(contentToValidate);
        setValidationResult(result);
        onValidationUpdate(result);
      } catch (error) {
        console.error('Validation error:', error);
      } finally {
        setIsValidating(false);
      }
    }, 500),
    [onValidationUpdate]
  );

  // Validate content when it changes
  useEffect(() => {
    debouncedValidate(content);
  }, [content, debouncedValidate]);

  const handleTitleChange = (value: string) => {
    onContentChange('title', value);
  };

  const handleDescriptionChange = (value: string) => {
    onContentChange('description', value);
  };

  const handleHashtagsChange = (value: string) => {
    setHashtagInput(value);
    
    // Parse hashtags from comma-separated string
    const hashtags = value
      .split(',')
      .map(tag => tag.trim())
      .filter(tag => tag.length > 0)
      .map(tag => tag.startsWith('#') ? tag.slice(1) : tag);
    
    onContentChange('hashtags', hashtags);
  };

  const addHashtag = (hashtag: string) => {
    const cleanTag = hashtag.replace('#', '');
    if (cleanTag && !content.hashtags.includes(cleanTag)) {
      const newHashtags = [...content.hashtags, cleanTag];
      onContentChange('hashtags', newHashtags);
      setHashtagInput(newHashtags.join(', '));
    }
  };

  const removeHashtag = (index: number) => {
    const newHashtags = content.hashtags.filter((_, i) => i !== index);
    onContentChange('hashtags', newHashtags);
    setHashtagInput(newHashtags.join(', '));
  };

  const getCharacterCountColor = (current: number, max: number) => {
    const percentage = (current / max) * 100;
    if (percentage >= 100) return 'text-red-600 font-semibold';
    if (percentage >= 90) return 'text-yellow-600 font-medium';
    if (percentage >= 80) return 'text-orange-500';
    return 'text-gray-500';
  };

  const getCharacterCountIcon = (current: number, max: number) => {
    const percentage = (current / max) * 100;
    if (percentage >= 100) {
      return (
        <svg className="h-4 w-4 text-red-600" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
        </svg>
      );
    }
    if (percentage >= 90) {
      return (
        <svg className="h-4 w-4 text-yellow-600" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
        </svg>
      );
    }
    return null;
  };

  const getInputBorderColor = (field: string) => {
    if (!validationResult) return 'border-gray-300 focus:border-blue-500';
    
    const hasError = validationResult.issues.some(issue => issue.field === field);
    if (hasError) return 'border-red-300 focus:border-red-500';
    
    return 'border-green-300 focus:border-green-500';
  };

  return (
    <div className="space-y-6">
      {/* Title Editor */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm font-medium text-gray-700">Title</label>
          <div className="flex items-center space-x-2">
            {isValidating && (
              <div 
                className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"
                data-testid="validation-spinner"
                aria-label="Validating content"
              ></div>
            )}
            {getCharacterCountIcon(content.title.length, platform.title_max_length)}
            <span className={`text-xs ${getCharacterCountColor(content.title.length, platform.title_max_length)}`}>
              {content.title.length}/{platform.title_max_length}
            </span>
          </div>
        </div>
        <input
          type="text"
          value={content.title}
          onChange={(e) => handleTitleChange(e.target.value)}
          className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50 transition-colors ${getInputBorderColor('title')}`}
          placeholder="Enter post title..."
          maxLength={platform.title_max_length}
          aria-describedby="title-help title-count"
          aria-invalid={validationResult?.issues.some(issue => issue.field === 'title')}
        />
        <div id="title-help" className="sr-only">
          Enter a compelling title for your post. Maximum {platform.title_max_length} characters.
        </div>
        {validationResult?.issues.some(issue => issue.field === 'title') && (
          <div className="mt-1 text-sm text-red-600">
            {validationResult.issues.find(issue => issue.field === 'title')?.issue}
          </div>
        )}
      </div>

      {/* Description Editor */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm font-medium text-gray-700">Description</label>
          <div className="flex items-center space-x-2">
            {getCharacterCountIcon(content.description.length, platform.description_max_length)}
            <span className={`text-xs ${getCharacterCountColor(content.description.length, platform.description_max_length)}`}>
              {content.description.length}/{platform.description_max_length}
            </span>
          </div>
        </div>
        <textarea
          value={content.description}
          onChange={(e) => handleDescriptionChange(e.target.value)}
          className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50 resize-vertical transition-colors ${getInputBorderColor('description')}`}
          placeholder="Enter post description..."
          rows={6}
          maxLength={platform.description_max_length}
          aria-describedby="description-help description-count"
          aria-invalid={validationResult?.issues.some(issue => issue.field === 'description')}
        />
        <div id="description-help" className="sr-only">
          Enter a detailed description of your product. Maximum {platform.description_max_length} characters.
        </div>
        {validationResult?.issues.some(issue => issue.field === 'description') && (
          <div className="mt-1 text-sm text-red-600">
            {validationResult.issues.find(issue => issue.field === 'description')?.issue}
          </div>
        )}
      </div>

      {/* Hashtags Editor */}
      {platform.hashtag_limit > 0 && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium text-gray-700">Hashtags</label>
            <div className="flex items-center space-x-2">
              {getCharacterCountIcon(content.hashtags.length, platform.hashtag_limit)}
              <span className={`text-xs ${getCharacterCountColor(content.hashtags.length, platform.hashtag_limit)}`}>
                {content.hashtags.length}/{platform.hashtag_limit}
              </span>
            </div>
          </div>
          
          {/* Hashtag Input */}
          <input
            type="text"
            value={hashtagInput}
            onChange={(e) => handleHashtagsChange(e.target.value)}
            className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50 transition-colors ${getInputBorderColor('hashtags')}`}
            placeholder="Enter hashtags separated by commas (e.g., handmade, artisan, craft)"
            aria-describedby="hashtags-help hashtags-count"
            aria-invalid={validationResult?.issues.some(issue => issue.field === 'hashtags')}
          />
          <div id="hashtags-help" className="sr-only">
            Enter relevant hashtags for your post. Maximum {platform.hashtag_limit} hashtags allowed.
          </div>
          
          {/* Hashtag Tags Display */}
          {content.hashtags.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {content.hashtags.map((hashtag, index) => (
                <span
                  key={index}
                  className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-blue-100 text-blue-800"
                >
                  #{hashtag}
                  <button
                    onClick={() => removeHashtag(index)}
                    className="ml-2 text-blue-600 hover:text-blue-800 focus:outline-none"
                    aria-label={`Remove hashtag ${hashtag}`}
                  >
                    <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                  </button>
                </span>
              ))}
            </div>
          )}
          
          {validationResult?.issues.some(issue => issue.field === 'hashtags') && (
            <div className="mt-1 text-sm text-red-600">
              {validationResult.issues.find(issue => issue.field === 'hashtags')?.issue}
            </div>
          )}
          
          <div className="mt-2 text-xs text-gray-500">
            Tip: Enter hashtags without the # symbol. They will be added automatically.
          </div>
        </div>
      )}

      {/* Suggested Hashtags */}
      {platform.hashtag_limit > 0 && content.hashtags.length < platform.hashtag_limit && (
        <div>
          <label className="text-sm font-medium text-gray-700 mb-2 block">Suggested Hashtags</label>
          <div className="flex flex-wrap gap-2">
            {['handmade', 'artisan', 'craft', 'unique', 'handcrafted', 'local', 'smallbusiness', 'creative'].map((suggestion) => (
              <button
                key={suggestion}
                onClick={() => addHashtag(suggestion)}
                disabled={content.hashtags.includes(suggestion) || content.hashtags.length >= platform.hashtag_limit}
                className="px-3 py-1 text-sm border border-gray-300 rounded-full hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                #{suggestion}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Live Preview */}
      <div className="bg-gray-50 rounded-lg p-4 border">
        <h4 className="text-sm font-medium text-gray-700 mb-3">Live Preview</h4>
        <div className="bg-white rounded-lg p-3 border">
          <div className="space-y-2">
            <h5 className="font-semibold text-gray-900 text-sm">{content.title || 'Title will appear here'}</h5>
            <p className="text-gray-700 text-sm leading-relaxed whitespace-pre-wrap">
              {content.description || 'Description will appear here'}
            </p>
            {content.hashtags.length > 0 && platform.hashtag_limit > 0 && (
              <p className="text-blue-600 text-sm">
                {content.hashtags.map(tag => `#${tag}`).join(' ')}
              </p>
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
                <div>
                  <span className="text-sm font-medium text-red-800">
                    {validationResult.issues.length} validation issue{validationResult.issues.length !== 1 ? 's' : ''}:
                  </span>
                  <ul className="mt-1 text-sm text-red-700 list-disc list-inside">
                    {validationResult.issues.map((issue, index) => (
                      <li key={index}>{issue.issue}</li>
                    ))}
                  </ul>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ContentEditor;