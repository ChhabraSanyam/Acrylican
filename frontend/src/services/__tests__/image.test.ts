import { imageService } from '../image';
import { api } from '../../utils/api';

// Mock the api utility
jest.mock('../../utils/api');
const mockedApi = api as jest.Mocked<typeof api>;

describe('Image Service', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('uploadImage', () => {
    it('should upload image successfully', async () => {
      const mockUploadResult = {
        id: 'image-123',
        original_url: 'https://storage.example.com/original/image.jpg',
        compressed_url: 'https://storage.example.com/compressed/image.jpg',
        thumbnail_urls: {
          small: 'https://storage.example.com/thumb_small/image.jpg',
          medium: 'https://storage.example.com/thumb_medium/image.jpg',
          large: 'https://storage.example.com/thumb_large/image.jpg'
        },
        platform_optimized_urls: {
          facebook: 'https://storage.example.com/facebook/image.jpg',
          instagram: 'https://storage.example.com/instagram/image.jpg',
          pinterest: 'https://storage.example.com/pinterest/image.jpg'
        },
        file_size: 1024000,
        dimensions: { width: 1920, height: 1080 },
        format: 'JPEG',
        created_at: '2024-01-15T10:00:00Z'
      };

      mockedApi.post.mockResolvedValue({ data: mockUploadResult });

      const file = new File(['test'], 'test.jpg', { type: 'image/jpeg' });
      const uploadData = {
        file,
        product_id: 'product-123',
        platforms: ['facebook', 'instagram']
      };

      const result = await imageService.uploadImage(uploadData);

      expect(mockedApi.post).toHaveBeenCalledWith(
        '/images/upload',
        expect.any(FormData),
        {
          headers: {
            'Content-Type': 'multipart/form-data'
          },
          onUploadProgress: expect.any(Function)
        }
      );
      expect(result).toEqual(mockUploadResult);
    });

    it('should handle upload progress', async () => {
      const mockUploadResult = { id: 'image-123' };
      mockedApi.post.mockResolvedValue({ data: mockUploadResult });

      const file = new File(['test'], 'test.jpg', { type: 'image/jpeg' });
      const onProgress = jest.fn();

      await imageService.uploadImage({
        file,
        product_id: 'product-123',
        platforms: ['facebook']
      }, onProgress);

      // Verify that onUploadProgress was set up
      expect(mockedApi.post).toHaveBeenCalledWith(
        '/images/upload',
        expect.any(FormData),
        expect.objectContaining({
          onUploadProgress: expect.any(Function)
        })
      );
    });

    it('should handle upload errors', async () => {
      const error = new Error('Upload failed');
      mockedApi.post.mockRejectedValue(error);

      const file = new File(['test'], 'test.jpg', { type: 'image/jpeg' });

      await expect(imageService.uploadImage({
        file,
        product_id: 'product-123',
        platforms: ['facebook']
      })).rejects.toThrow('Upload failed');
    });

    it('should validate file type before upload', async () => {
      const invalidFile = new File(['test'], 'test.txt', { type: 'text/plain' });

      await expect(imageService.uploadImage({
        file: invalidFile,
        product_id: 'product-123',
        platforms: ['facebook']
      })).rejects.toThrow('Invalid file type');
    });

    it('should validate file size before upload', async () => {
      // Create a mock file that's too large (>10MB)
      const largeFile = new File(['x'.repeat(11 * 1024 * 1024)], 'large.jpg', { 
        type: 'image/jpeg' 
      });

      await expect(imageService.uploadImage({
        file: largeFile,
        product_id: 'product-123',
        platforms: ['facebook']
      })).rejects.toThrow('File too large');
    });
  });

  describe('getImages', () => {
    it('should fetch images for a product', async () => {
      const mockImages = [
        {
          id: 'image-1',
          original_url: 'https://example.com/image1.jpg',
          thumbnail_urls: { small: 'https://example.com/thumb1.jpg' },
          created_at: '2024-01-15T10:00:00Z'
        },
        {
          id: 'image-2',
          original_url: 'https://example.com/image2.jpg',
          thumbnail_urls: { small: 'https://example.com/thumb2.jpg' },
          created_at: '2024-01-14T09:00:00Z'
        }
      ];

      mockedApi.get.mockResolvedValue({ data: mockImages });

      const result = await imageService.getImages('product-123');

      expect(mockedApi.get).toHaveBeenCalledWith('/images/product/product-123');
      expect(result).toEqual(mockImages);
    });

    it('should handle empty image list', async () => {
      mockedApi.get.mockResolvedValue({ data: [] });

      const result = await imageService.getImages('product-123');

      expect(result).toEqual([]);
    });
  });

  describe('deleteImage', () => {
    it('should delete image successfully', async () => {
      mockedApi.delete.mockResolvedValue({ data: { success: true } });

      const result = await imageService.deleteImage('image-123');

      expect(mockedApi.delete).toHaveBeenCalledWith('/images/image-123');
      expect(result).toEqual({ success: true });
    });

    it('should handle delete errors', async () => {
      const error = new Error('Image not found');
      mockedApi.delete.mockRejectedValue(error);

      await expect(imageService.deleteImage('nonexistent')).rejects.toThrow('Image not found');
    });
  });

  describe('optimizeForPlatform', () => {
    it('should optimize image for specific platform', async () => {
      const mockOptimizedImage = {
        id: 'optimized-123',
        url: 'https://storage.example.com/optimized/facebook/image.jpg',
        dimensions: { width: 1200, height: 630 },
        file_size: 512000
      };

      mockedApi.post.mockResolvedValue({ data: mockOptimizedImage });

      const result = await imageService.optimizeForPlatform('image-123', 'facebook');

      expect(mockedApi.post).toHaveBeenCalledWith('/images/image-123/optimize', {
        platform: 'facebook'
      });
      expect(result).toEqual(mockOptimizedImage);
    });

    it('should handle optimization errors', async () => {
      const error = new Error('Optimization failed');
      mockedApi.post.mockRejectedValue(error);

      await expect(
        imageService.optimizeForPlatform('image-123', 'facebook')
      ).rejects.toThrow('Optimization failed');
    });
  });

  describe('generateThumbnails', () => {
    it('should generate thumbnails for image', async () => {
      const mockThumbnails = {
        small: 'https://storage.example.com/thumb_small/image.jpg',
        medium: 'https://storage.example.com/thumb_medium/image.jpg',
        large: 'https://storage.example.com/thumb_large/image.jpg'
      };

      mockedApi.post.mockResolvedValue({ data: mockThumbnails });

      const result = await imageService.generateThumbnails('image-123', [150, 300, 600]);

      expect(mockedApi.post).toHaveBeenCalledWith('/images/image-123/thumbnails', {
        sizes: [150, 300, 600]
      });
      expect(result).toEqual(mockThumbnails);
    });
  });

  describe('getImageMetadata', () => {
    it('should fetch image metadata', async () => {
      const mockMetadata = {
        id: 'image-123',
        filename: 'test.jpg',
        file_size: 1024000,
        dimensions: { width: 1920, height: 1080 },
        format: 'JPEG',
        color_profile: 'sRGB',
        created_at: '2024-01-15T10:00:00Z',
        updated_at: '2024-01-15T10:00:00Z'
      };

      mockedApi.get.mockResolvedValue({ data: mockMetadata });

      const result = await imageService.getImageMetadata('image-123');

      expect(mockedApi.get).toHaveBeenCalledWith('/images/image-123/metadata');
      expect(result).toEqual(mockMetadata);
    });
  });

  describe('bulkUpload', () => {
    it('should upload multiple images', async () => {
      const mockResults = [
        { id: 'image-1', original_url: 'https://example.com/image1.jpg' },
        { id: 'image-2', original_url: 'https://example.com/image2.jpg' }
      ];

      mockedApi.post.mockResolvedValue({ data: mockResults });

      const files = [
        new File(['test1'], 'test1.jpg', { type: 'image/jpeg' }),
        new File(['test2'], 'test2.jpg', { type: 'image/jpeg' })
      ];

      const result = await imageService.bulkUpload({
        files,
        product_id: 'product-123',
        platforms: ['facebook', 'instagram']
      });

      expect(mockedApi.post).toHaveBeenCalledWith(
        '/images/bulk-upload',
        expect.any(FormData),
        expect.objectContaining({
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        })
      );
      expect(result).toEqual(mockResults);
    });

    it('should handle bulk upload with progress tracking', async () => {
      const mockResults = [{ id: 'image-1' }];
      mockedApi.post.mockResolvedValue({ data: mockResults });

      const files = [new File(['test'], 'test.jpg', { type: 'image/jpeg' })];
      const onProgress = jest.fn();

      await imageService.bulkUpload({
        files,
        product_id: 'product-123',
        platforms: ['facebook']
      }, onProgress);

      expect(onProgress).toBeDefined();
    });
  });

  describe('Error handling', () => {
    it('should handle network errors consistently', async () => {
      const networkError = new Error('Network Error');
      mockedApi.get.mockRejectedValue(networkError);

      await expect(imageService.getImages('product-123')).rejects.toThrow('Network Error');
    });

    it('should handle API response errors with status codes', async () => {
      const apiError = {
        response: {
          status: 413,
          data: { message: 'File too large' }
        }
      };
      mockedApi.post.mockRejectedValue(apiError);

      const file = new File(['test'], 'test.jpg', { type: 'image/jpeg' });

      await expect(imageService.uploadImage({
        file,
        product_id: 'product-123',
        platforms: ['facebook']
      })).rejects.toEqual(apiError);
    });
  });
});