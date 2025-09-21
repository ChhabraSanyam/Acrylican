import React, { useState, useRef, useCallback } from 'react';
import { ImageUploadProgress, ImageValidationError, DEFAULT_IMAGE_CONFIG, ImageUploadConfig } from '../../types/image';
import { ImageService } from '../../services/image';
import ImagePreview from './ImagePreview';
import UploadProgress from './UploadProgress';

interface ImageUploadProps {
  onUploadComplete?: (images: any[]) => void;
  onUploadError?: (error: string) => void;
  config?: Partial<ImageUploadConfig>;
  className?: string;
  multiple?: boolean;
}

const ImageUpload: React.FC<ImageUploadProps> = ({
  onUploadComplete,
  onUploadError,
  config = {},
  className = '',
  multiple = true,
}) => {
  const uploadConfig = { ...DEFAULT_IMAGE_CONFIG, ...config };
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<ImageUploadProgress[]>([]);
  const [validationErrors, setValidationErrors] = useState<ImageValidationError[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  const validateFiles = useCallback(async (files: File[]): Promise<{
    validFiles: File[];
    errors: ImageValidationError[];
  }> => {
    const validFiles: File[] = [];
    const errors: ImageValidationError[] = [];

    // Check total number of files
    if (files.length > uploadConfig.maxFiles) {
      errors.push({
        file: files[0],
        error: `Maximum ${uploadConfig.maxFiles} files allowed`,
      });
      return { validFiles, errors };
    }

    for (const file of files) {
      const validationError = await ImageService.validateImageFile(file, uploadConfig);
      if (validationError) {
        errors.push({ file, error: validationError });
      } else {
        validFiles.push(file);
      }
    }

    return { validFiles, errors };
  }, [uploadConfig]);

  const handleFileUpload = useCallback(async (files: File[]) => {
    if (files.length === 0) return;

    const { validFiles, errors } = await validateFiles(files);
    setValidationErrors(errors);

    if (validFiles.length === 0) {
      return;
    }

    setIsUploading(true);
    
    // Initialize progress tracking
    const progressItems: ImageUploadProgress[] = validFiles.map(file => ({
      file,
      progress: 0,
      status: 'pending',
    }));
    setUploadProgress(progressItems);

    try {
      // Update status to uploading
      setUploadProgress(prev => 
        prev.map(item => ({ ...item, status: 'uploading' as const }))
      );

      const response = await ImageService.uploadImages(
        validFiles,
        (fileIndex, progress) => {
          setUploadProgress(prev => 
            prev.map((item, index) => 
              index === fileIndex 
                ? { ...item, progress, status: progress === 100 ? 'processing' : 'uploading' }
                : item
            )
          );
        }
      );

      if (response.success) {
        // Update progress to completed
        setUploadProgress(prev => 
          prev.map((item, index) => ({
            ...item,
            progress: 100,
            status: 'completed',
            result: response.images[index],
          }))
        );

        onUploadComplete?.(response.images);
        
        // Clear progress after a delay
        setTimeout(() => {
          setUploadProgress([]);
        }, 2000);
      } else {
        throw new Error(response.errors?.join(', ') || 'Upload failed');
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Upload failed';
      
      setUploadProgress(prev => 
        prev.map(item => ({ 
          ...item, 
          status: 'error',
          error: errorMessage,
        }))
      );
      
      onUploadError?.(errorMessage);
    } finally {
      setIsUploading(false);
    }
  }, [validateFiles, onUploadComplete, onUploadError]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    handleFileUpload(files);
  }, [handleFileUpload]);

  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    handleFileUpload(files);
    
    // Reset input value to allow uploading the same file again
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, [handleFileUpload]);

  const handleClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const clearErrors = useCallback(() => {
    setValidationErrors([]);
  }, []);

  const retryUpload = useCallback((fileIndex: number) => {
    const failedItem = uploadProgress[fileIndex];
    if (failedItem && failedItem.status === 'error') {
      handleFileUpload([failedItem.file]);
    }
  }, [uploadProgress, handleFileUpload]);

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Upload Area */}
      <div
        className={`
          relative border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
          transition-colors duration-200 ease-in-out
          ${isDragOver 
            ? 'border-primary-500 bg-primary-50' 
            : 'border-gray-300 hover:border-gray-400'
          }
          ${isUploading ? 'pointer-events-none opacity-50' : ''}
        `}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleClick}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple={multiple}
          accept={uploadConfig.acceptedFormats.join(',')}
          onChange={handleFileInputChange}
          className="hidden"
        />
        
        <div className="space-y-4">
          <div className="mx-auto w-16 h-16 text-gray-400">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
          </div>
          
          <div>
            <p className="text-lg font-medium text-gray-900">
              {isDragOver ? 'Drop images here' : 'Upload product images'}
            </p>
            <p className="text-sm text-gray-500 mt-1">
              Drag and drop images here, or click to select files
            </p>
            <p className="text-xs text-gray-400 mt-2">
              Supports JPEG, PNG, WebP • Max {Math.round(uploadConfig.maxFileSize / (1024 * 1024))}MB per file • Up to {uploadConfig.maxFiles} files
            </p>
          </div>
        </div>
      </div>

      {/* Validation Errors */}
      {validationErrors.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex justify-between items-start">
            <div>
              <h4 className="text-sm font-medium text-red-800 mb-2">
                Upload Errors
              </h4>
              <ul className="text-sm text-red-700 space-y-1">
                {validationErrors.map((error, index) => (
                  <li key={index}>
                    <strong>{error.file.name}:</strong> {error.error}
                  </li>
                ))}
              </ul>
            </div>
            <button
              onClick={clearErrors}
              className="text-red-400 hover:text-red-600"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* Upload Progress */}
      {uploadProgress.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-sm font-medium text-gray-900">Upload Progress</h4>
          {uploadProgress.map((item, index) => (
            <UploadProgress
              key={`${item.file.name}-${index}`}
              progress={item}
              onRetry={() => retryUpload(index)}
            />
          ))}
        </div>
      )}

      {/* Image Previews */}
      {uploadProgress.some(item => item.result) && (
        <div className="space-y-3">
          <h4 className="text-sm font-medium text-gray-900">Uploaded Images</h4>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {uploadProgress
              .filter(item => item.result)
              .map((item, index) => (
                <ImagePreview
                  key={item.result!.id}
                  image={item.result!}
                  showActions={false}
                />
              ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ImageUpload;