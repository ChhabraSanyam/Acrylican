import React, { useState, useEffect } from 'react';
import { PostCreate, Post } from '../../types/post';
import { GeneratedContent, ContentGenerationInput, EditableContent, Platform } from '../../types/content';
import { ProcessedImage } from '../../types/image';
import { postService } from '../../services/post';
import { contentService } from '../../services/content';
import { ImageService } from '../../services/image';

import ImageUpload from '../image/ImageUpload';
import ImageGallery from '../image/ImageGallery';
import HashtagInput from '../common/HashtagInput';

interface PostCreationWizardProps {
  onPostCreated?: (post: Post) => void;
  onCancel?: () => void;
  initialData?: Partial<PostCreate>;
  generatedContent?: GeneratedContent;
  productId?: string;
}

interface WizardStep {
  id: string;
  title: string;
  description: string;
}

const steps: WizardStep[] = [
  {
    id: 'basic-details',
    title: 'Basic Details',
    description: 'Add your product information and images'
  },
  {
    id: 'platform-selection',
    title: 'Platform Selection',
    description: 'Choose platforms for specialized posts'
  },
  {
    id: 'content-review',
    title: 'Content Review',
    description: 'Review and edit generated content'
  },
  {
    id: 'schedule-post',
    title: 'Schedule & Post',
    description: 'Schedule and publish your posts'
  }
];

export const PostCreationWizard: React.FC<PostCreationWizardProps> = ({
  onPostCreated,
  onCancel,
  initialData,
  generatedContent,
  productId
}) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [platforms, setPlatforms] = useState<Record<string, Platform>>({});
  const [generatedContentData, setGeneratedContentData] = useState<GeneratedContent | null>(generatedContent || null);
  const [editedContent, setEditedContent] = useState<Record<string, EditableContent>>({});

  // Basic details state
  const [basicDetails, setBasicDetails] = useState({
    title: initialData?.title || '',
    description: initialData?.description || '',
    images: initialData?.images || [],
    product_category: '',
    price_range: '',
    target_audience: ''
  });

  // Selected platforms for content generation
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>(initialData?.target_platforms || []);

  // Schedule type for the final step
  const [scheduleType, setScheduleType] = useState<'draft' | 'now' | 'later'>('draft');

  // Final post data
  const [postData, setPostData] = useState<PostCreate>({
    title: '',
    description: '',
    hashtags: [],
    images: [],
    target_platforms: [],
    product_id: productId || initialData?.product_id,
    scheduled_at: initialData?.scheduled_at,
    priority: initialData?.priority || 0,
    platform_specific_content: {}
  });

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

  const handleNext = async () => {
    if (currentStep === 1 && selectedPlatforms.length > 0) {
      // Generate content for selected platforms
      await generatePlatformContent();
    }
    
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const generatePlatformContent = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const input: ContentGenerationInput = {
        description: basicDetails.description,
        target_platforms: selectedPlatforms,
        product_category: basicDetails.product_category,
        price_range: basicDetails.price_range,
        target_audience: basicDetails.target_audience
      };

      const result = await contentService.generateContent(input);
      if (result.success && result.content) {
        setGeneratedContentData(result.content);
        
        // Initialize edited content with generated content
        const initialEditedContent: Record<string, EditableContent> = {};
        selectedPlatforms.forEach(platform => {
          const platformContent = result.content!.platform_specific[platform];
          if (platformContent) {
            initialEditedContent[platform] = {
              title: platformContent.title,
              description: platformContent.description,
              hashtags: platformContent.hashtags,
              platform: platform
            };
          }
        });
        setEditedContent(initialEditedContent);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate content');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreatePost = async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Convert image IDs to URLs
      let imageUrls: string[] = [];
      if (basicDetails.images.length > 0) {
        const images = await ImageService.getImagesByIds(basicDetails.images);
        imageUrls = images.map(img => img.compressed_url || img.original_url);
      }

      // Prepare final post data with edited content
      const finalPostData: PostCreate = {
        ...postData,
        title: basicDetails.title,
        description: basicDetails.description,
        images: imageUrls,
        target_platforms: selectedPlatforms,
        platform_specific_content: editedContent
      };

      if (scheduleType === 'draft') {
        // Create post as draft
        const post = await postService.createPost(finalPostData);
        onPostCreated?.(post);
      } else if (scheduleType === 'now') {
        // Create and publish immediately
        const post = await postService.createPost(finalPostData);
        await postService.publishPost({ post_id: post.id });
        onPostCreated?.(post);
      } else if (scheduleType === 'later') {
        // Create and schedule for later
        const post = await postService.createPost(finalPostData);
        if (postData.scheduled_at) {
          await postService.schedulePost({
            post_id: post.id,
            scheduled_at: postData.scheduled_at
          });
        }
        onPostCreated?.(post);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create post');
    } finally {
      setIsLoading(false);
    }
  };

  const renderStepContent = () => {
    switch (steps[currentStep].id) {
      case 'basic-details':
        return (
          <BasicDetailsStep
            basicDetails={basicDetails}
            onUpdate={setBasicDetails}
          />
        );
      case 'platform-selection':
        return (
          <PlatformSelectionStep
            platforms={platforms}
            selectedPlatforms={selectedPlatforms}
            onUpdate={setSelectedPlatforms}
          />
        );
      case 'content-review':
        return (
          <ContentReviewStep
            platforms={platforms}
            selectedPlatforms={selectedPlatforms}
            generatedContent={generatedContentData}
            editedContent={editedContent}
            onUpdate={setEditedContent}
            isLoading={isLoading}
          />
        );
      case 'schedule-post':
        return (
          <SchedulePostStep
            postData={postData}
            onUpdate={(updates) => setPostData(prev => ({ ...prev, ...updates }))}
            basicDetails={basicDetails}
            selectedPlatforms={selectedPlatforms}
            editedContent={editedContent}
            scheduleType={scheduleType}
            onScheduleTypeChange={setScheduleType}
          />
        );
      default:
        return null;
    }
  };

  const isStepValid = () => {
    if (!steps[currentStep]) return false;
    
    switch (steps[currentStep].id) {
      case 'basic-details':
        return basicDetails.title.trim() && basicDetails.description.trim();
      case 'platform-selection':
        return selectedPlatforms.length > 0;
      case 'content-review':
        return generatedContentData !== null && Object.keys(editedContent).length > 0;
      case 'schedule-post':
        return true;
      default:
        return false;
    }
  };

  return (
    <div className="max-w-4xl mx-auto bg-white rounded-lg shadow-lg">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <h2 className="text-2xl font-bold text-gray-900">Create New Post</h2>
        <p className="text-gray-600 mt-1">Follow the steps to create and schedule your post</p>
      </div>

      {/* Progress Steps */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          {steps.map((step, index) => (
            <div
              key={step.id}
              className={`flex items-center ${index < steps.length - 1 ? 'flex-1' : ''}`}
            >
              <div className="flex items-center">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                    index <= currentStep
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-200 text-gray-600'
                  }`}
                >
                  {index + 1}
                </div>
                <div className="ml-3">
                  <p className={`text-sm font-medium ${
                    index <= currentStep ? 'text-blue-600' : 'text-gray-500'
                  }`}>
                    {step.title}
                  </p>
                  <p className="text-xs text-gray-500">{step.description}</p>
                </div>
              </div>
              {index < steps.length - 1 && (
                <div className={`flex-1 h-0.5 mx-4 ${
                  index < currentStep ? 'bg-blue-600' : 'bg-gray-200'
                }`} />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Step Content */}
      <div className="px-6 py-6 min-h-96">
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md">
            <p className="text-red-800">{error}</p>
          </div>
        )}
        {renderStepContent()}
      </div>

      {/* Footer */}
      <div className="px-6 py-4 border-t border-gray-200 flex justify-between">
        <div>
          {onCancel && (
            <button
              onClick={onCancel}
              className="px-4 py-2 text-gray-600 hover:text-gray-800"
            >
              Cancel
            </button>
          )}
        </div>
        <div className="flex space-x-3">
          {currentStep > 0 && (
            <button
              onClick={handlePrevious}
              className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
            >
              Previous
            </button>
          )}
          {currentStep < steps.length - 1 ? (
            <button
              onClick={handleNext}
              disabled={!isStepValid() || isLoading}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading && currentStep === 1 ? 'Generating Content...' : 'Next'}
            </button>
          ) : (
            <button
              onClick={handleCreatePost}
              disabled={!isStepValid() || isLoading}
              className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? 'Creating Post...' : 
                scheduleType === 'draft' ? 'Save as Draft' :
                scheduleType === 'now' ? 'Create & Publish Now' :
                'Create & Schedule Post'
              }
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

// Step Components
interface BasicDetailsStepProps {
  basicDetails: {
    title: string;
    description: string;
    images: string[];
    product_category: string;
    price_range: string;
    target_audience: string;
  };
  onUpdate: (updates: any) => void;
}

const BasicDetailsStep: React.FC<BasicDetailsStepProps> = ({
  basicDetails,
  onUpdate,
}) => {
  const [showImageGallery, setShowImageGallery] = useState(false);

  const handleImageUpload = (images: ProcessedImage[]) => {
    const currentImages = basicDetails.images || [];
    const newImages = [...currentImages, ...images.map(img => img.id)];
    onUpdate({ ...basicDetails, images: newImages });
  };

  const handleImageSelect = (images: ProcessedImage[]) => {
    const imageIds = images.map(img => img.id);
    onUpdate({ ...basicDetails, images: imageIds });
  };

  const handleRemoveImage = (imageId: string) => {
    const currentImages = basicDetails.images || [];
    const updatedImages = currentImages.filter(id => id !== imageId);
    onUpdate({ ...basicDetails, images: updatedImages });
  };

  return (
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Product Title *
        </label>
        <input
          type="text"
          value={basicDetails.title}
          onChange={(e) => onUpdate({ ...basicDetails, title: e.target.value })}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Enter your product title..."
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Product Description *
        </label>
        <textarea
          value={basicDetails.description}
          onChange={(e) => onUpdate({ ...basicDetails, description: e.target.value })}
          rows={6}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Describe your product in detail. This will be used to generate platform-specific content..."
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Product Category
          </label>
          <input
            type="text"
            value={basicDetails.product_category}
            onChange={(e) => onUpdate({ ...basicDetails, product_category: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="e.g., Handmade Jewelry"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Price Range
          </label>
          <input
            type="text"
            value={basicDetails.price_range}
            onChange={(e) => onUpdate({ ...basicDetails, price_range: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="e.g., $25-50"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Target Audience
          </label>
          <input
            type="text"
            value={basicDetails.target_audience}
            onChange={(e) => onUpdate({ ...basicDetails, target_audience: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="e.g., Young professionals"
          />
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between mb-4">
          <label className="block text-sm font-medium text-gray-700">
            Product Images ({basicDetails.images.length} selected)
          </label>
          <button
            type="button"
            onClick={() => setShowImageGallery(!showImageGallery)}
            className="text-sm text-blue-600 hover:text-blue-700"
          >
            {showImageGallery ? 'Hide Gallery' : 'Browse Gallery'}
          </button>
        </div>

        {/* Image Upload */}
        <ImageUpload
          onUploadComplete={handleImageUpload}
          onUploadError={(error) => console.error('Upload error:', error)}
          multiple={true}
          className="mb-4"
        />

        {/* Image Gallery */}
        {showImageGallery && (
          <div className="mt-4 p-4 border border-gray-200 rounded-lg bg-gray-50">
            <ImageGallery
              onImageSelect={handleImageSelect}
              selectedImages={basicDetails.images}
              allowMultiSelect={true}
              showUpload={false}
            />
          </div>
        )}

        {/* Selected Images Preview */}
        {basicDetails.images.length > 0 && (
          <SelectedImagesPreview
            imageIds={basicDetails.images}
            onRemoveImage={handleRemoveImage}
          />
        )}
      </div>
    </div>
  );
};

interface PlatformSelectionStepProps {
  platforms: Record<string, Platform>;
  selectedPlatforms: string[];
  onUpdate: (platforms: string[]) => void;
}

const PlatformSelectionStep: React.FC<PlatformSelectionStepProps> = ({
  platforms,
  selectedPlatforms,
  onUpdate
}) => {
  const handlePlatformToggle = (platform: string, enabled: boolean) => {
    if (enabled) {
      onUpdate([...selectedPlatforms, platform]);
    } else {
      onUpdate(selectedPlatforms.filter(p => p !== platform));
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          Select Platforms for Specialized Posts
        </h3>
        <p className="text-gray-600 mb-6">
          Choose the platforms where you want to create specialized posts. AI will generate optimized content for each selected platform.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Object.entries(platforms).map(([platformKey, platform]) => {
          const isSelected = selectedPlatforms.includes(platformKey);
          return (
            <div
              key={platformKey}
              className={`border rounded-lg p-4 cursor-pointer transition-all ${
                isSelected
                  ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-200'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
              onClick={() => handlePlatformToggle(platformKey, !isSelected)}
            >
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-medium text-gray-900">{platform.name}</h4>
                <input
                  type="checkbox"
                  checked={isSelected}
                  onChange={() => {}} // Handled by div onClick
                  className="h-4 w-4 text-blue-600 rounded"
                />
              </div>
              <p className="text-sm text-gray-600 mb-2">
                Type: {platform.type.replace('_', ' ')}
              </p>
              <div className="text-xs text-gray-500">
                <p>Title: {platform.title_max_length} chars</p>
                <p>Description: {platform.description_max_length} chars</p>
                <p>Hashtags: {platform.hashtag_limit} max</p>
              </div>
            </div>
          );
        })}
      </div>

      {selectedPlatforms.length > 0 && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <h4 className="font-medium text-green-800 mb-2">
            Selected Platforms ({selectedPlatforms.length})
          </h4>
          <div className="flex flex-wrap gap-2">
            {selectedPlatforms.map(platformKey => (
              <span
                key={platformKey}
                className="px-2 py-1 bg-green-100 text-green-800 text-sm rounded-full"
              >
                {platforms[platformKey]?.name || platformKey}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

interface ContentReviewStepProps {
  platforms: Record<string, Platform>;
  selectedPlatforms: string[];
  generatedContent: GeneratedContent | null;
  editedContent: Record<string, EditableContent>;
  onUpdate: (content: Record<string, EditableContent>) => void;
  isLoading: boolean;
}

const ContentReviewStep: React.FC<ContentReviewStepProps> = ({
  platforms,
  selectedPlatforms,
  generatedContent,
  editedContent,
  onUpdate,
  isLoading
}) => {
  const handleContentEdit = (platform: string, field: keyof EditableContent, value: any) => {
    const updatedContent = {
      ...editedContent,
      [platform]: {
        ...editedContent[platform],
        [field]: value
      }
    };
    onUpdate(updatedContent);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Generating specialized content for your platforms...</p>
        </div>
      </div>
    );
  }

  if (!generatedContent) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600">No content generated yet. Please go back and select platforms.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          Review & Edit Generated Content
        </h3>
        <p className="text-gray-600 mb-6">
          AI has generated specialized content for each platform. Review and edit as needed before posting.
        </p>
      </div>

      <div className="space-y-8">
        {selectedPlatforms.map(platformKey => {
          const platform = platforms[platformKey];
          const content = editedContent[platformKey];
          
          if (!content) return null;

          return (
            <div key={platformKey} className="border border-gray-200 rounded-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <h4 className="text-lg font-medium text-gray-900">
                  {platform?.name || platformKey}
                </h4>
                <span className="px-2 py-1 bg-gray-100 text-gray-600 text-sm rounded">
                  {platform?.type.replace('_', ' ')}
                </span>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Title ({content.title.length}/{platform?.title_max_length})
                  </label>
                  <input
                    type="text"
                    value={content.title}
                    onChange={(e) => handleContentEdit(platformKey, 'title', e.target.value)}
                    className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                      content.title.length > (platform?.title_max_length || 0)
                        ? 'border-red-300 bg-red-50'
                        : 'border-gray-300'
                    }`}
                  />
                  {content.title.length > (platform?.title_max_length || 0) && (
                    <p className="text-red-600 text-sm mt-1">
                      Title exceeds maximum length of {platform?.title_max_length} characters
                    </p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Description ({content.description.length}/{platform?.description_max_length})
                  </label>
                  <textarea
                    value={content.description}
                    onChange={(e) => handleContentEdit(platformKey, 'description', e.target.value)}
                    rows={6}
                    className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                      content.description.length > (platform?.description_max_length || 0)
                        ? 'border-red-300 bg-red-50'
                        : 'border-gray-300'
                    }`}
                  />
                  {content.description.length > (platform?.description_max_length || 0) && (
                    <p className="text-red-600 text-sm mt-1">
                      Description exceeds maximum length of {platform?.description_max_length} characters
                    </p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Hashtags ({content.hashtags.length}/{platform?.hashtag_limit})
                  </label>
                  <HashtagInput
                    hashtags={content.hashtags}
                    onChange={(hashtags) => handleContentEdit(platformKey, 'hashtags', hashtags)}
                  />
                  {content.hashtags.length > (platform?.hashtag_limit || 0) && platform?.hashtag_limit > 0 && (
                    <p className="text-red-600 text-sm mt-1">
                      Too many hashtags. Maximum allowed: {platform?.hashtag_limit}
                    </p>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

interface SchedulePostStepProps {
  postData: PostCreate;
  onUpdate: (updates: Partial<PostCreate>) => void;
  basicDetails: any;
  selectedPlatforms: string[];
  editedContent: Record<string, EditableContent>;
  scheduleType: 'draft' | 'now' | 'later';
  onScheduleTypeChange: (type: 'draft' | 'now' | 'later') => void;
}

const SchedulePostStep: React.FC<SchedulePostStepProps> = ({
  postData,
  onUpdate,
  basicDetails,
  selectedPlatforms,
  editedContent,
  scheduleType,
  onScheduleTypeChange
}) => {

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          Schedule & Post
        </h3>
        <p className="text-gray-600 mb-6">
          Review your post summary and choose when to publish.
        </p>
      </div>

      {/* Post Summary */}
      <div className="bg-gray-50 p-6 rounded-lg">
        <h4 className="font-medium text-gray-900 mb-4">Post Summary</h4>
        
        <div className="space-y-3">
          <div>
            <span className="text-sm font-medium text-gray-600">Product:</span>
            <p className="text-gray-900">{basicDetails.title}</p>
          </div>
          
          <div>
            <span className="text-sm font-medium text-gray-600">Images:</span>
            <p className="text-gray-900">{basicDetails.images.length} image(s)</p>
          </div>
          
          <div>
            <span className="text-sm font-medium text-gray-600">Platforms:</span>
            <div className="flex flex-wrap gap-2 mt-1">
              {selectedPlatforms.map(platform => (
                <span
                  key={platform}
                  className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full"
                >
                  {platform}
                </span>
              ))}
            </div>
          </div>

          <div>
            <span className="text-sm font-medium text-gray-600">Specialized Content:</span>
            <p className="text-gray-900">{Object.keys(editedContent).length} platform-specific posts ready</p>
          </div>
        </div>
      </div>

      {/* Scheduling Options */}
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-4">
            What would you like to do with this post?
          </label>
          <div className="space-y-3">
            <label className="flex items-center">
              <input
                type="radio"
                name="schedule"
                value="draft"
                checked={scheduleType === 'draft'}
                onChange={() => {
                  onScheduleTypeChange('draft');
                  onUpdate({ scheduled_at: undefined });
                }}
                className="mr-3"
              />
              <div>
                <span className="font-medium">Save as Draft</span>
                <p className="text-sm text-gray-500">Save the post without publishing. You can publish it later from the posts dashboard.</p>
              </div>
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                name="schedule"
                value="now"
                checked={scheduleType === 'now'}
                onChange={() => {
                  onScheduleTypeChange('now');
                  onUpdate({ scheduled_at: undefined });
                }}
                className="mr-3"
              />
              <div>
                <span className="font-medium">Publish Immediately</span>
                <p className="text-sm text-gray-500">Post to all selected platforms right after creation.</p>
              </div>
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                name="schedule"
                value="later"
                checked={scheduleType === 'later'}
                onChange={() => onScheduleTypeChange('later')}
                className="mr-3"
              />
              <div>
                <span className="font-medium">Schedule for Later</span>
                <p className="text-sm text-gray-500">Choose a specific date and time to publish the post.</p>
              </div>
            </label>
          </div>
        </div>

        {scheduleType === 'later' && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Schedule Date & Time
            </label>
            <input
              type="datetime-local"
              value={postData.scheduled_at || ''}
              onChange={(e) => onUpdate({ scheduled_at: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Priority (0-10)
          </label>
          <input
            type="number"
            min="0"
            max="10"
            value={postData.priority || 0}
            onChange={(e) => onUpdate({ priority: parseInt(e.target.value) || 0 })}
            className="w-32 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <p className="text-sm text-gray-500 mt-1">
            Higher priority posts are processed first
          </p>
        </div>
      </div>
    </div>
  );
};

// Selected Images Preview Component
interface SelectedImagesPreviewProps {
  imageIds: string[];
  onRemoveImage: (imageId: string) => void;
}

const SelectedImagesPreview: React.FC<SelectedImagesPreviewProps> = ({
  imageIds,
  onRemoveImage
}) => {
  const [images, setImages] = useState<ProcessedImage[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadImages = async () => {
      if (imageIds.length === 0) {
        setImages([]);
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        const selectedImages = await ImageService.getImagesByIds(imageIds);
        setImages(selectedImages);
      } catch (error) {
        console.error('Failed to load selected images:', error);
        setImages([]);
      } finally {
        setLoading(false);
      }
    };

    loadImages();
  }, [imageIds]);

  if (loading) {
    return (
      <div className="mt-4">
        <h4 className="text-sm font-medium text-gray-700 mb-2">Selected Images</h4>
        <div className="grid grid-cols-4 gap-2">
          {imageIds.map((imageId) => (
            <div key={imageId} className="aspect-square bg-gray-200 rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="mt-4">
      <h4 className="text-sm font-medium text-gray-700 mb-2">Selected Images ({images.length})</h4>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
        {images.map((image) => (
          <div key={image.id} className="relative group">
            <div className="aspect-square rounded-lg overflow-hidden bg-gray-100">
              <img
                src={image.thumbnail_url}
                alt={image.file_name}
                className="w-full h-full object-cover"
              />
            </div>
            <button
              type="button"
              onClick={() => onRemoveImage(image.id)}
              className="absolute -top-2 -right-2 w-6 h-6 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center text-sm font-medium hover:bg-red-600"
              title="Remove image"
            >
              ×
            </button>
            <div className="absolute bottom-0 left-0 right-0 bg-black bg-opacity-50 text-white text-xs p-1 rounded-b-lg opacity-0 group-hover:opacity-100 transition-opacity">
              <p className="truncate">{image.file_name}</p>
            </div>
          </div>
        ))}
        
        {/* Show placeholders for images that couldn't be loaded */}
        {imageIds.filter(id => !images.find(img => img.id === id)).map((imageId) => (
          <div key={imageId} className="relative group">
            <div className="aspect-square bg-gray-200 rounded-lg flex items-center justify-center">
              <div className="text-center">
                <svg className="w-8 h-8 text-gray-400 mx-auto mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                <span className="text-xs text-gray-500">Image not found</span>
              </div>
            </div>
            <button
              type="button"
              onClick={() => onRemoveImage(imageId)}
              className="absolute -top-2 -right-2 w-6 h-6 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center text-sm font-medium hover:bg-red-600"
              title="Remove image"
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default PostCreationWizard;