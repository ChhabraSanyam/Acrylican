import { ProcessedImage } from "../types/image";
import apiClient from "../utils/api";

export interface ImageUploadResponse {
  success: boolean;
  images: ProcessedImage[];
  errors?: string[];
}

export class ImageService {
  static async uploadImages(
    files: File[],
    onProgress?: (fileIndex: number, progress: number) => void
  ): Promise<ImageUploadResponse> {
    const formData = new FormData();

    files.forEach((file, index) => {
      formData.append(`images`, file);
    });

    try {
      const response = await apiClient.post<ImageUploadResponse>(
        "/api/images/upload",
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
              // For simplicity, we'll use the same progress for all files
              // In a real implementation, you might want to track individual file progress
              onProgress(0, progress);
            }
          },
        }
      );

      return response.data;
    } catch (error) {
      console.error("Image upload failed:", error);
      throw new Error("Failed to upload images. Please try again.");
    }
  }

  static async deleteImage(imageId: string): Promise<void> {
    try {
      await apiClient.delete(`/api/images/${imageId}`);
    } catch (error) {
      console.error("Image deletion failed:", error);
      throw new Error("Failed to delete image. Please try again.");
    }
  }

  static async getUserImages(): Promise<ProcessedImage[]> {
    try {
      const response = await apiClient.get<{ images: ProcessedImage[] }>(
        "/api/images"
      );
      return response.data.images;
    } catch (error) {
      console.error("Failed to fetch images:", error);
      throw new Error("Failed to load images. Please try again.");
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
