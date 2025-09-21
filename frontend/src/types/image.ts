export interface ProcessedImage {
  id: string;
  original_url: string;
  compressed_url: string;
  thumbnail_url: string;
  file_size: number;
  dimensions: {
    width: number;
    height: number;
  };
  file_name: string;
  created_at: string;
}

export interface ImageUploadProgress {
  file: File;
  progress: number;
  status: 'pending' | 'uploading' | 'processing' | 'completed' | 'error';
  error?: string;
  result?: ProcessedImage;
}

export interface ImageValidationError {
  file: File;
  error: string;
}

export interface ImageUploadConfig {
  maxFileSize: number; // in bytes
  maxFiles: number;
  acceptedFormats: string[];
  maxWidth?: number;
  maxHeight?: number;
}

export const DEFAULT_IMAGE_CONFIG: ImageUploadConfig = {
  maxFileSize: 10 * 1024 * 1024, // 10MB
  maxFiles: 10,
  acceptedFormats: ['image/jpeg', 'image/png', 'image/webp'],
  maxWidth: 4096,
  maxHeight: 4096,
};