import React from 'react';
import { ImageUploadProgress } from '../../types/image';

interface UploadProgressProps {
  progress: ImageUploadProgress;
  onRetry?: () => void;
}

const UploadProgress: React.FC<UploadProgressProps> = ({ progress, onRetry }) => {
  const getStatusIcon = () => {
    switch (progress.status) {
      case 'pending':
        return (
          <div className="w-4 h-4 border-2 border-gray-300 border-t-transparent rounded-full animate-spin" />
        );
      case 'uploading':
      case 'processing':
        return (
          <div className="w-4 h-4 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
        );
      case 'completed':
        return (
          <svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        );
      case 'error':
        return (
          <svg className="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        );
      default:
        return null;
    }
  };

  const getStatusText = () => {
    switch (progress.status) {
      case 'pending':
        return 'Waiting...';
      case 'uploading':
        return `Uploading... ${progress.progress}%`;
      case 'processing':
        return 'Processing...';
      case 'completed':
        return 'Completed';
      case 'error':
        return progress.error || 'Upload failed';
      default:
        return '';
    }
  };

  const getProgressBarColor = () => {
    switch (progress.status) {
      case 'uploading':
      case 'processing':
        return 'bg-primary-500';
      case 'completed':
        return 'bg-green-500';
      case 'error':
        return 'bg-red-500';
      default:
        return 'bg-gray-300';
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
      <div className="flex items-center space-x-3">
        {/* Status Icon */}
        <div className="flex-shrink-0">
          {getStatusIcon()}
        </div>

        {/* File Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-gray-900 truncate">
              {progress.file.name}
            </p>
            <span className="text-xs text-gray-500 ml-2">
              {formatFileSize(progress.file.size)}
            </span>
          </div>
          
          <p className="text-xs text-gray-500 mt-1">
            {getStatusText()}
          </p>

          {/* Progress Bar */}
          {(progress.status === 'uploading' || progress.status === 'processing') && (
            <div className="mt-2">
              <div className="w-full bg-gray-200 rounded-full h-1.5">
                <div
                  className={`h-1.5 rounded-full transition-all duration-300 ${getProgressBarColor()}`}
                  style={{ width: `${progress.progress}%` }}
                />
              </div>
            </div>
          )}
        </div>

        {/* Retry Button */}
        {progress.status === 'error' && onRetry && (
          <button
            onClick={onRetry}
            className="flex-shrink-0 text-xs bg-red-100 text-red-700 px-2 py-1 rounded hover:bg-red-200 transition-colors"
          >
            Retry
          </button>
        )}
      </div>
    </div>
  );
};

export default UploadProgress;