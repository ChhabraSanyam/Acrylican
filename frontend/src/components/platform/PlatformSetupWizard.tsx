import React, { useState, useEffect } from 'react';
import { SetupWizardInfo, SetupWizardStep } from '../../types/platform';
import { platformService } from '../../services/platform';

interface PlatformSetupWizardProps {
  platform: string;
  onComplete: () => void;
  onCancel: () => void;
}

const PlatformSetupWizard: React.FC<PlatformSetupWizardProps> = ({
  platform,
  onComplete,
  onCancel
}) => {
  const [wizardInfo, setWizardInfo] = useState<SetupWizardInfo | null>(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    loadWizardInfo();
  }, [platform]);

  const loadWizardInfo = async () => {
    try {
      setLoading(true);
      const info = await platformService.getSetupWizardInfo(platform);
      setWizardInfo(info);
    } catch (err) {
      setError('Failed to load setup wizard information');
      console.error('Error loading wizard info:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (fieldName: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      [fieldName]: value
    }));
  };

  const handleNext = async () => {
    if (!wizardInfo) return;

    const step = wizardInfo.steps[currentStep];
    
    try {
      setProcessing(true);
      setError(null);

      if (step.action === 'oauth') {
        // Handle OAuth flow
        const shopDomain = formData.shop_domain;
        const response = await platformService.initiateOAuthFlow(platform, shopDomain);
        
        // Redirect to OAuth URL
        window.location.href = response.authorization_url;
        return;
      }

      if (step.action === 'test') {
        // Test the connection with provided credentials
        const result = await platformService.testConnection(platform);
        if (result.success) {
          onComplete();
        } else {
          setError(result.message);
        }
        return;
      }

      // Move to next step
      if (currentStep < wizardInfo.steps.length - 1) {
        setCurrentStep(currentStep + 1);
      } else {
        onComplete();
      }
    } catch (err) {
      console.error('Error in setup step:', err);
      setError('An error occurred during setup');
    } finally {
      setProcessing(false);
    }
  };

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const isStepValid = () => {
    if (!wizardInfo) return false;
    
    const step = wizardInfo.steps[currentStep];
    
    // Check if all required fields are filled
    for (const field of step.required_fields) {
      if (!formData[field.name] || formData[field.name].trim() === '') {
        return false;
      }
    }
    
    return true;
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
        <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
          <div className="flex justify-center items-center h-32">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" role="status" aria-label="Loading setup wizard">
              <span className="sr-only">Loading...</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!wizardInfo) {
    return (
      <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
        <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
          <div className="text-center">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Setup Error</h3>
            <p className="text-gray-600 mb-4">Failed to load setup wizard information.</p>
            <button
              onClick={onCancel}
              className="bg-gray-600 text-white px-4 py-2 rounded-md hover:bg-gray-700"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    );
  }

  const step = wizardInfo.steps[currentStep];

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 border w-full max-w-md shadow-lg rounded-md bg-white">
        {/* Header */}
        <div className="mb-6">
          <div className="flex justify-between items-center mb-2">
            <h3 className="text-lg font-medium text-gray-900">
              Connect {wizardInfo.platform_name}
            </h3>
            <button
              onClick={onCancel}
              className="text-gray-400 hover:text-gray-600"
              aria-label="Close setup wizard"
            >
              <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          {/* Progress Bar */}
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${((currentStep + 1) / wizardInfo.steps.length) * 100}%` }}
            ></div>
          </div>
          <p className="text-sm text-gray-500 mt-1">
            Step {currentStep + 1} of {wizardInfo.steps.length}
          </p>
        </div>

        {/* Step Content */}
        <div className="mb-6">
          <h4 className="text-md font-medium text-gray-900 mb-2">{step.title}</h4>
          <p className="text-gray-600 mb-4">{step.description}</p>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          {/* Form Fields */}
          {step.action === 'form' && (
            <div className="space-y-4">
              {step.required_fields.map((field) => (
                <div key={field.name}>
                  <label htmlFor={field.name} className="block text-sm font-medium text-gray-700 mb-1">
                    {field.label}
                  </label>
                  <input
                    id={field.name}
                    type={field.type}
                    placeholder={field.placeholder}
                    value={formData[field.name] || ''}
                    onChange={(e) => handleInputChange(field.name, e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  />
                  {field.help && (
                    <p className="text-xs text-gray-500 mt-1">{field.help}</p>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Info Step */}
          {step.action === 'info' && (
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-md">
              <div className="flex">
                <svg className="h-5 w-5 text-blue-400 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                </svg>
                <div className="ml-3">
                  <p className="text-sm text-blue-800">
                    Please ensure you have completed the requirements mentioned above before proceeding.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* OAuth Step */}
          {step.action === 'oauth' && (
            <div className="p-4 bg-green-50 border border-green-200 rounded-md">
              <div className="flex">
                <svg className="h-5 w-5 text-green-400 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <div className="ml-3">
                  <p className="text-sm text-green-800">
                    You will be redirected to {wizardInfo.platform_name} to authorize the connection.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Test Step */}
          {step.action === 'test' && (
            <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-md">
              <div className="flex">
                <svg className="h-5 w-5 text-yellow-400 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                <div className="ml-3">
                  <p className="text-sm text-yellow-800">
                    We will test the connection with the credentials you provided.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex justify-between">
          <button
            onClick={handlePrevious}
            disabled={currentStep === 0}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Previous
          </button>
          
          <div className="flex space-x-2">
            <button
              onClick={onCancel}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              Cancel
            </button>
            <button
              onClick={handleNext}
              disabled={!isStepValid() || processing}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {processing ? (
                <>
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Processing...
                </>
              ) : currentStep === wizardInfo.steps.length - 1 ? (
                'Complete'
              ) : step.action === 'oauth' ? (
                'Authorize'
              ) : step.action === 'test' ? (
                'Test Connection'
              ) : (
                'Next'
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PlatformSetupWizard;