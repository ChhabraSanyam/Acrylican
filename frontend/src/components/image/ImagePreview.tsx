import React, { useState } from 'react';
import { ProcessedImage } from '../../types/image';

interface ImagePreviewProps {
  image: ProcessedImage;
  onDelete?: (imageId: string) => void;
  onSelect?: (imageId: string) => void;
  isSelected?: boolean;
  showActions?: boolean;
  className?: string;
}

const ImagePreview: React.FC<ImagePreviewProps> = ({
  image,
  onDelete,
  onSelect,
  isSelected = false,
  showActions = true,
  className = '',
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [showFullSize, setShowFullSize] = useState(false);

  const handleDelete = async () => {
    if (!onDelete) return;
    
    const confirmed = window.confirm('Are you sure you want to delete this image?');
    if (!confirmed) return;

    setIsLoading(true);
    try {
      await onDelete(image.id);
    } catch (error) {
      console.error('Failed to delete image:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelect = () => {
    if (onSelect) {
      onSelect(image.id);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <>
      <div
        className={`
          relative group bg-white border-2 rounded-lg overflow-hidden shadow-sm
          transition-all duration-200 hover:shadow-md
          ${isSelected ? 'border-primary-500 ring-2 ring-primary-200' : 'border-gray-200'}
          ${onSelect ? 'cursor-pointer' : ''}
          ${className}
        `}
        onClick={handleSelect}
      >
        {/* Image */}
        <div className="aspect-square relative overflow-hidden bg-gray-100">
          <img
            src={image.thumbnail_url}
            alt={image.file_name}
            className="w-full h-full object-cover transition-transform duration-200 group-hover:scale-105"
            loading="lazy"
          />
          
          {/* Loading Overlay */}
          {isLoading && (
            <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center">
              <div className="w-6 h-6 border-2 border-white border-t-transparent rounded-full animate-spin" />
            </div>
          )}

          {/* Selection Indicator */}
          {isSelected && (
            <div className="absolute top-2 right-2 w-6 h-6 bg-primary-500 rounded-full flex items-center justify-center">
              <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
          )}

          {/* Action Buttons */}
          {showActions && (
            <div className="absolute top-2 left-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex space-x-1">
              {/* View Full Size */}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setShowFullSize(true);
                }}
                className="p-1.5 bg-black bg-opacity-50 text-white rounded-full hover:bg-opacity-70 transition-colors"
                title="View full size"
              >
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
              </button>

              {/* Delete */}
              {onDelete && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDelete();
                  }}
                  disabled={isLoading}
                  className="p-1.5 bg-red-500 bg-opacity-80 text-white rounded-full hover:bg-opacity-100 transition-colors disabled:opacity-50"
                  title="Delete image"
                >
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              )}
            </div>
          )}
        </div>

        {/* Image Info */}
        <div className="p-3">
          <p className="text-sm font-medium text-gray-900 truncate" title={image.file_name}>
            {image.file_name}
          </p>
          <div className="flex items-center justify-between mt-1 text-xs text-gray-500">
            <span>{image.dimensions.width} × {image.dimensions.height}</span>
            <span>{formatFileSize(image.file_size)}</span>
          </div>
          <p className="text-xs text-gray-400 mt-1">
            {formatDate(image.created_at)}
          </p>
        </div>
      </div>

      {/* Full Size Modal */}
      {showFullSize && (
        <div
          className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4"
          onClick={() => setShowFullSize(false)}
        >
          <div className="relative max-w-4xl max-h-full">
            <img
              src={image.compressed_url}
              alt={image.file_name}
              className="max-w-full max-h-full object-contain"
            />
            <button
              onClick={() => setShowFullSize(false)}
              className="absolute top-4 right-4 p-2 bg-black bg-opacity-50 text-white rounded-full hover:bg-opacity-70 transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      )}
    </>
  );
};

export default ImagePreview;