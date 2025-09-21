import React, { useState, useEffect } from 'react';
import { PostCreate, Post } from '../../types/post';
import { GeneratedContent } from '../../types/content';
import { postService } from '../../services/post';
import { contentService } from '../../services/content';
import PlatformSelector from '../content/PlatformSelector';

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
    id: 'content',
    title: 'Content',
    description: 'Add your post content and images'
  },
  {
    id: 'platforms',
    title: 'Platforms',
    description: 'Select target platforms'
  },
  {
    id: 'schedule',
    title: 'Schedule',
    description: 'Choose when to publish'
  },
  {
    id: 'review',
    title: 'Review',
    description: 'Review and create post'
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
  const [platforms, setPlatforms] = useState<Record<string, any>>({});

  const [postData, setPostData] = useState<PostCreate>({
    title: initialData?.title || generatedContent?.title || '',
    description: initialData?.description || generatedContent?.description || '',
    hashtags: initialData?.hashtags || generatedContent?.hashtags || [],
    images: initialData?.images || [],
    target_platforms: initialData?.target_platforms || [],
    product_id: productId || initialData?.product_id,
    scheduled_at: initialData?.scheduled_at,
    priority: initialData?.priority || 0,
    platform_specific_content: generatedContent?.platform_specific || {}
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

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleCreatePost = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const post = await postService.createPost(postData);
      onPostCreated?.(post);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create post');
    } finally {
      setIsLoading(false);
    }
  };

  const updatePostData = (updates: Partial<PostCreate>) => {
    setPostData(prev => ({ ...prev, ...updates }));
  };

  const renderStepContent = () => {
    switch (steps[currentStep].id) {
      case 'content':
        return (
          <ContentStep
            postData={postData}
            onUpdate={updatePostData}
            generatedContent={generatedContent}
          />
        );
      case 'platforms':
        return (
          <PlatformStep
            postData={postData}
            onUpdate={updatePostData}
            platforms={platforms}
          />
        );
      case 'schedule':
        return (
          <ScheduleStep
            postData={postData}
            onUpdate={updatePostData}
          />
        );
      case 'review':
        return (
          <ReviewStep
            postData={postData}
            onUpdate={updatePostData}
            platforms={platforms}
          />
        );
      default:
        return null;
    }
  };

  const isStepValid = () => {
    switch (steps[currentStep].id) {
      case 'content':
        return postData.title.trim() && postData.description.trim() && postData.images.length > 0;
      case 'platforms':
        return postData.target_platforms.length > 0;
      case 'schedule':
        return true; // Optional step
      case 'review':
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
              disabled={!isStepValid()}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          ) : (
            <button
              onClick={handleCreatePost}
              disabled={!isStepValid() || isLoading}
              className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? 'Creating...' : 'Create Post'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

// Step Components
interface StepProps {
  postData: PostCreate;
  onUpdate: (updates: Partial<PostCreate>) => void;
}

const ContentStep: React.FC<StepProps & { generatedContent?: GeneratedContent }> = ({
  postData,
  onUpdate,
  generatedContent
}) => {
  return (
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Title
        </label>
        <input
          type="text"
          value={postData.title}
          onChange={(e) => onUpdate({ title: e.target.value })}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Enter post title..."
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Description
        </label>
        <textarea
          value={postData.description}
          onChange={(e) => onUpdate({ description: e.target.value })}
          rows={6}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Enter post description..."
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Hashtags
        </label>
        <input
          type="text"
          value={postData.hashtags.join(' ')}
          onChange={(e) => onUpdate({ hashtags: e.target.value.split(' ').filter(tag => tag.trim()) })}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Enter hashtags separated by spaces..."
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Images
        </label>
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
          <p className="text-gray-500">Image upload functionality will be integrated here</p>
          <p className="text-sm text-gray-400 mt-1">
            Current images: {postData.images.length}
          </p>
        </div>
      </div>
    </div>
  );
};

const PlatformStep: React.FC<StepProps & { platforms: Record<string, any> }> = ({
  postData,
  onUpdate,
  platforms
}) => {
  const handlePlatformToggle = (platform: string, enabled: boolean) => {
    const currentPlatforms = postData.target_platforms;
    if (enabled) {
      onUpdate({ target_platforms: [...currentPlatforms, platform] });
    } else {
      onUpdate({ target_platforms: currentPlatforms.filter(p => p !== platform) });
    }
  };

  return (
    <div>
      <PlatformSelector
        platforms={platforms}
        selectedPlatforms={postData.target_platforms}
        availablePlatforms={Object.keys(platforms)}
        onPlatformToggle={handlePlatformToggle}
      />
    </div>
  );
};

const ScheduleStep: React.FC<StepProps> = ({ postData, onUpdate }) => {
  const [scheduleType, setScheduleType] = useState<'now' | 'later'>('now');

  return (
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-4">
          When would you like to publish this post?
        </label>
        <div className="space-y-3">
          <label className="flex items-center">
            <input
              type="radio"
              name="schedule"
              value="now"
              checked={scheduleType === 'now'}
              onChange={(e) => {
                setScheduleType('now');
                onUpdate({ scheduled_at: undefined });
              }}
              className="mr-3"
            />
            <span>Publish immediately after creation</span>
          </label>
          <label className="flex items-center">
            <input
              type="radio"
              name="schedule"
              value="later"
              checked={scheduleType === 'later'}
              onChange={(e) => setScheduleType('later')}
              className="mr-3"
            />
            <span>Schedule for later</span>
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
  );
};

const ReviewStep: React.FC<StepProps & { platforms: Record<string, any> }> = ({
  postData,
  platforms
}) => {
  return (
    <div className="space-y-6">
      <div className="bg-gray-50 p-4 rounded-lg">
        <h3 className="font-medium text-gray-900 mb-3">Post Summary</h3>
        
        <div className="space-y-3">
          <div>
            <span className="text-sm font-medium text-gray-600">Title:</span>
            <p className="text-gray-900">{postData.title}</p>
          </div>
          
          <div>
            <span className="text-sm font-medium text-gray-600">Description:</span>
            <p className="text-gray-900 text-sm">{postData.description}</p>
          </div>
          
          <div>
            <span className="text-sm font-medium text-gray-600">Hashtags:</span>
            <p className="text-gray-900">{postData.hashtags.join(' ')}</p>
          </div>
          
          <div>
            <span className="text-sm font-medium text-gray-600">Platforms:</span>
            <div className="flex flex-wrap gap-2 mt-1">
              {postData.target_platforms.map(platform => (
                <span
                  key={platform}
                  className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full"
                >
                  {platforms[platform]?.name || platform}
                </span>
              ))}
            </div>
          </div>
          
          <div>
            <span className="text-sm font-medium text-gray-600">Images:</span>
            <p className="text-gray-900">{postData.images.length} image(s)</p>
          </div>
          
          {postData.scheduled_at && (
            <div>
              <span className="text-sm font-medium text-gray-600">Scheduled for:</span>
              <p className="text-gray-900">
                {new Date(postData.scheduled_at).toLocaleString()}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PostCreationWizard;