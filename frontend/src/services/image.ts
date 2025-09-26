import { ProcessedImage } from "../types/image";
import apiClient from "../utils/api";

export interface ImageUploadResponse {
  success: boolean;
  image_id: string;
  message: string;
  urls: {
    original: string;
    compressed: string;
    thumbnails: Record<string, string>;
    platform_optimized: Record<string, string>;
  };
}

export class ImageService {
  static async uploadImages(
    files: File[],
    onProgress?: (fileIndex: number, progress: number) => void
  ): Promise<ProcessedImage[]> {
    const uploadedImages: ProcessedImage[] = [];

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const formData = new FormData();
      formData.append('file', file);

      try {
        const response = await apiClient.post<ImageUploadResponse>(
          "/images/upload",
          formData,
          {
            headers: {
              "Content-Type": "multipart/form-data",
            },
            onUploadProgress: (progressEvent) => {
              if (onProgress && progressEvent.total) {
                const progress = Math.round(
                  (progressEvent.loaded * 100) / progressEvent.total
                );
                onProgress(i, progress);
              }
            },
          }
        );

        // Convert response to ProcessedImage format
        const processedImage: ProcessedImage = {
          id: response.data.image_id,
          original_url: response.data.urls.original,
          compressed_url: response.data.urls.compressed,
          thumbnail_url: response.data.urls.thumbnails?.small || response.data.urls.compressed,
          file_size: file.size, // Use actual file size
          dimensions: { width: 0, height: 0 }, // Will be updated by backend
          file_name: file.name,
          created_at: new Date().toISOString()
        };

        uploadedImages.push(processedImage);
      } catch (error) {
        console.error(`Image upload failed for ${file.name}:`, error);
        
        // Handle different types of errors
        if (error instanceof Error) {
          throw error;
        }
        
        // Handle axios errors
        if (error && typeof error === 'object' && 'response' in error) {
          const axiosError = error as any;
          if (axiosError.response?.data?.detail) {
            throw new Error(axiosError.response.data.detail);
          }
          if (axiosError.response?.status === 413) {
            throw new Error("File size too large. Please choose smaller images.");
          }
          if (axiosError.response?.status === 400) {
            throw new Error("Invalid file format. Please upload JPEG, PNG, or WebP images.");
          }
        }
        
        throw new Error(`Failed to upload ${file.name}. Please try again.`);
      }
    }

    return uploadedImages;
  }

  static async deleteImage(imageId: string): Promise<void> {
    try {
      await apiClient.delete(`/images/${imageId}`);
    } catch (error) {
      console.error("Image deletion failed:", error);
      throw new Error("Failed to delete image. Please try again.");
    }
  }

  static async getUserImages(): Promise<ProcessedImage[]> {
    try {
      const response = await apiClient.get<{ images: ProcessedImage[] }>(
        "/images/user/images"
      );
      return response.data.images;
    } catch (error) {
      console.error("Failed to fetch images:", error);
      throw new Error("Failed to load images. Please try again.");
    }
  }

  static async getImagesByIds(imageIds: string[]): Promise<ProcessedImage[]> {
    if (imageIds.length === 0) {
      return [];
    }

    try {
      const response = await apiClient.post<{ images: ProcessedImage[] }>(
        "/images/by-ids",
        { image_ids: imageIds }
      );
      return response.data.images;
    } catch (error) {
      console.error("Failed to fetch images by IDs:", error);
      // Fallback to getting all images and filtering
      try {
        const allImages = await this.getUserImages();
        return allImages.filter(img => imageIds.includes(img.id));
      } catch (fallbackError) {
        console.error("Fallback image fetch also failed:", fallbackError);
        throw new Error("Failed to load selected images. Please try again.");
      }
    }
  }

  static validateImageFile(
    file: File,
    config: {
      maxFileSize: number;
      acceptedFormats: string[];
      maxWidth?: number;
      maxHeight?: number;
    }
  ): Promise<string | null> {
    return new Promise((resolve) => {
      // Check file size
      if (file.size > config.maxFileSize) {
        resolve(
          `File size must be less than ${Math.round(
            config.maxFileSize / (1024 * 1024)
          )}MB`
        );
        return;
      }

      // Check file type
      if (!config.acceptedFormats.includes(file.type)) {
        resolve(
          `File type must be one of: ${config.acceptedFormats.join(", ")}`
        );
        return;
      }

      // Check image dimensions if specified
      if (config.maxWidth || config.maxHeight) {
        const img = new Image();
        img.onload = () => {
          if (config.maxWidth && img.width > config.maxWidth) {
            resolve(`Image width must be less than ${config.maxWidth}px`);
            return;
          }
          if (config.maxHeight && img.height > config.maxHeight) {
            resolve(`Image height must be less than ${config.maxHeight}px`);
            return;
          }
          resolve(null);
        };
        img.onerror = () => {
          resolve("Invalid image file");
        };
        img.src = URL.createObjectURL(file);
      } else {
        resolve(null);
      }
    });
  }
}
