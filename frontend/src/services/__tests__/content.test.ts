import { contentService } from '../content';
import { api } from '../../utils/api';

// Mock the api utility
jest.mock('../../utils/api');
const mockedApi = api as jest.Mocked<typeof api>;

describe('Content Service', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('generateContent', () => {
    it('should generate content successfully', async () => {
      const mockGeneratedContent = {
        title: 'Beautiful Handmade Ceramic Vase',
        description: 'Discover the perfect blend of artistry and functionality with this stunning handmade ceramic vase.',
        hashtags: ['#handmade', '#ceramic', '#vase', '#artisan', '#homedecor'],
        platform_variations: {
          facebook: {
            title: 'Beautiful Handmade Ceramic Vase - Perfect for Your Home',
            description: 'Discover the perfect blend of artistry and functionality...'
          },
          instagram: {
            title: 'Beautiful Handmade Ceramic Vase ✨',
            description: 'Perfect blend of artistry and functionality 🏺✨'
          }
        }
      };

      mockedApi.post.mockResolvedValue({ data: mockGeneratedContent });

      const contentRequest = {
        product_id: 'product-123',
        platforms: ['facebook', 'instagram'],
        tone: 'elegant' as const,
        target_audience: 'home_decorators'
      };

      const result = await contentService.generateContent(contentRequest);

      expect(mockedApi.post).toHaveBeenCalledWith('/content/generate', contentRequest);
      expect(result).toEqual(mockGeneratedContent);
    });

    it('should handle generation errors', async () => {
      const errorMessage = 'Content generation failed';
      mockedApi.post.mockRejectedValue(new Error(errorMessage));

      const contentRequest = {
        product_id: 'product-123',
        platforms: ['facebook']
      };

      await expect(contentService.generateContent(contentRequest)).rejects.toThrow(errorMessage);
    });

    it('should generate content with minimal parameters', async () => {
      const mockContent = {
        title: 'Test Product',
        description: 'Test description',
        hashtags: ['#test']
      };

      mockedApi.post.mockResolvedValue({ data: mockContent });

      const result = await contentService.generateContent({
        product_id: 'product-123',
        platforms: ['facebook']
      });

      expect(mockedApi.post).toHaveBeenCalledWith('/content/generate', {
        product_id: 'product-123',
        platforms: ['facebook']
      });
      expect(result).toEqual(mockContent);
    });
  });

  describe('saveContentTemplate', () => {
    it('should save content template successfully', async () => {
      const mockTemplate = {
        id: 'template-123',
        name: 'Jewelry Template',
        content: {
          title_template: '✨ {product_title} - Handcrafted with Love ✨',
          description_template: 'Discover the beauty of {product_description}. Perfect for {target_audience}.',
          hashtags: ['#handmade', '#jewelry', '#artisan']
        },
        platforms: ['facebook', 'instagram'],
        category: 'jewelry',
        created_at: '2024-01-15T10:00:00Z'
      };

      mockedApi.post.mockResolvedValue({ data: mockTemplate });

      const templateData = {
        name: 'Jewelry Template',
        content: {
          title_template: '✨ {product_title} - Handcrafted with Love ✨',
          description_template: 'Discover the beauty of {product_description}. Perfect for {target_audience}.',
          hashtags: ['#handmade', '#jewelry', '#artisan']
        },
        platforms: ['facebook', 'instagram'],
        category: 'jewelry'
      };

      const result = await contentService.saveContentTemplate(templateData);

      expect(mockedApi.post).toHaveBeenCalledWith('/content/templates', templateData);
      expect(result).toEqual(mockTemplate);
    });

    it('should handle template save errors', async () => {
      const error = new Error('Template save failed');
      mockedApi.post.mockRejectedValue(error);

      const templateData = {
        name: 'Test Template',
        content: { title_template: 'Test' },
        platforms: ['facebook']
      };

      await expect(contentService.saveContentTemplate(templateData)).rejects.toThrow('Template save failed');
    });
  });

  describe('getContentTemplates', () => {
    it('should fetch content templates', async () => {
      const mockTemplates = [
        {
          id: 'template-1',
          name: 'Jewelry Template',
          category: 'jewelry',
          platforms: ['facebook', 'instagram'],
          created_at: '2024-01-15T10:00:00Z'
        },
        {
          id: 'template-2',
          name: 'Pottery Template',
          category: 'pottery',
          platforms: ['facebook', 'pinterest'],
          created_at: '2024-01-14T09:00:00Z'
        }
      ];

      mockedApi.get.mockResolvedValue({ data: mockTemplates });

      const result = await contentService.getContentTemplates();

      expect(mockedApi.get).toHaveBeenCalledWith('/content/templates');
      expect(result).toEqual(mockTemplates);
    });

    it('should fetch templates with category filter', async () => {
      const mockTemplates = [
        {
          id: 'template-1',
          name: 'Jewelry Template',
          category: 'jewelry'
        }
      ];

      mockedApi.get.mockResolvedValue({ data: mockTemplates });

      const result = await contentService.getContentTemplates('jewelry');

      expect(mockedApi.get).toHaveBeenCalledWith('/content/templates', {
        params: { category: 'jewelry' }
      });
      expect(result).toEqual(mockTemplates);
    });
  });

  describe('updateContentTemplate', () => {
    it('should update content template successfully', async () => {
      const mockUpdatedTemplate = {
        id: 'template-123',
        name: 'Updated Jewelry Template',
        content: {
          title_template: '✨ Updated {product_title} ✨',
          description_template: 'Updated description template'
        },
        platforms: ['facebook', 'instagram', 'pinterest'],
        updated_at: '2024-01-16T11:00:00Z'
      };

      mockedApi.put.mockResolvedValue({ data: mockUpdatedTemplate });

      const updateData = {
        name: 'Updated Jewelry Template',
        content: {
          title_template: '✨ Updated {product_title} ✨',
          description_template: 'Updated description template'
        },
        platforms: ['facebook', 'instagram', 'pinterest']
      };

      const result = await contentService.updateContentTemplate('template-123', updateData);

      expect(mockedApi.put).toHaveBeenCalledWith('/content/templates/template-123', updateData);
      expect(result).toEqual(mockUpdatedTemplate);
    });

    it('should handle template update errors', async () => {
      const error = new Error('Template not found');
      mockedApi.put.mockRejectedValue(error);

      await expect(
        contentService.updateContentTemplate('nonexistent', { name: 'Test' })
      ).rejects.toThrow('Template not found');
    });
  });

  describe('deleteContentTemplate', () => {
    it('should delete content template successfully', async () => {
      mockedApi.delete.mockResolvedValue({ data: { success: true } });

      const result = await contentService.deleteContentTemplate('template-123');

      expect(mockedApi.delete).toHaveBeenCalledWith('/content/templates/template-123');
      expect(result).toEqual({ success: true });
    });

    it('should handle template deletion errors', async () => {
      const error = new Error('Template not found');
      mockedApi.delete.mockRejectedValue(error);

      await expect(contentService.deleteContentTemplate('nonexistent')).rejects.toThrow('Template not found');
    });
  });

  describe('previewContent', () => {
    it('should preview content for platforms', async () => {
      const mockPreview = {
        facebook: {
          title: 'Beautiful Handmade Ceramic Vase - Perfect for Your Home',
          description: 'Discover the perfect blend of artistry and functionality with this stunning handmade ceramic vase. Each piece is carefully crafted by skilled artisans.',
          hashtags_text: '#handmade #ceramic #vase #artisan #homedecor',
          character_count: 145,
          within_limits: true
        },
        instagram: {
          title: 'Beautiful Handmade Ceramic Vase ✨',
          description: 'Perfect blend of artistry and functionality 🏺✨\n\nEach piece carefully crafted by skilled artisans 👨‍🎨',
          hashtags_text: '#handmade #ceramic #vase #artisan #homedecor #pottery #art #handcrafted #unique #design',
          character_count: 98,
          within_limits: true
        }
      };

      mockedApi.post.mockResolvedValue({ data: mockPreview });

      const previewRequest = {
        content: {
          title: 'Beautiful Handmade Ceramic Vase',
          description: 'Discover the perfect blend of artistry and functionality',
          hashtags: ['#handmade', '#ceramic', '#vase']
        },
        platforms: ['facebook', 'instagram']
      };

      const result = await contentService.previewContent(previewRequest);

      expect(mockedApi.post).toHaveBeenCalledWith('/content/preview', previewRequest);
      expect(result).toEqual(mockPreview);
    });

    it('should handle preview errors', async () => {
      const error = new Error('Preview generation failed');
      mockedApi.post.mockRejectedValue(error);

      const previewRequest = {
        content: { title: 'Test' },
        platforms: ['facebook']
      };

      await expect(contentService.previewContent(previewRequest)).rejects.toThrow('Preview generation failed');
    });
  });

  describe('validateContent', () => {
    it('should validate content successfully', async () => {
      const mockValidation = {
        facebook: {
          valid: true,
          title_length: 45,
          description_length: 120,
          hashtags_count: 5,
          warnings: [],
          errors: []
        },
        instagram: {
          valid: false,
          title_length: 150,
          description_length: 2200,
          hashtags_count: 35,
          warnings: ['Title is quite long for Instagram'],
          errors: ['Description exceeds Instagram limit', 'Too many hashtags (max 30)']
        }
      };

      mockedApi.post.mockResolvedValue({ data: mockValidation });

      const validationRequest = {
        content: {
          title: 'Very long title that might exceed platform limits',
          description: 'Very long description...',
          hashtags: Array(35).fill('#tag')
        },
        platforms: ['facebook', 'instagram']
      };

      const result = await contentService.validateContent(validationRequest);

      expect(mockedApi.post).toHaveBeenCalledWith('/content/validate', validationRequest);
      expect(result).toEqual(mockValidation);
    });

    it('should handle validation errors', async () => {
      const error = new Error('Validation failed');
      mockedApi.post.mockRejectedValue(error);

      await expect(
        contentService.validateContent({
          content: { title: 'Test' },
          platforms: ['facebook']
        })
      ).rejects.toThrow('Validation failed');
    });
  });

  describe('getContentHistory', () => {
    it('should fetch content history', async () => {
      const mockHistory = [
        {
          id: 'content-1',
          product_id: 'product-123',
          generated_content: {
            title: 'Beautiful Ceramic Vase',
            description: 'Handcrafted with care'
          },
          platforms: ['facebook', 'instagram'],
          created_at: '2024-01-15T10:00:00Z',
          used_in_posts: 2
        },
        {
          id: 'content-2',
          product_id: 'product-124',
          generated_content: {
            title: 'Elegant Pottery Bowl',
            description: 'Perfect for your kitchen'
          },
          platforms: ['facebook'],
          created_at: '2024-01-14T09:00:00Z',
          used_in_posts: 1
        }
      ];

      mockedApi.get.mockResolvedValue({ data: mockHistory });

      const result = await contentService.getContentHistory();

      expect(mockedApi.get).toHaveBeenCalledWith('/content/history', {
        params: { limit: 50, offset: 0 }
      });
      expect(result).toEqual(mockHistory);
    });

    it('should fetch content history with pagination', async () => {
      const mockHistory = [];
      mockedApi.get.mockResolvedValue({ data: mockHistory });

      const result = await contentService.getContentHistory(20, 40);

      expect(mockedApi.get).toHaveBeenCalledWith('/content/history', {
        params: { limit: 20, offset: 40 }
      });
      expect(result).toEqual(mockHistory);
    });

    it('should fetch content history with product filter', async () => {
      const mockHistory = [];
      mockedApi.get.mockResolvedValue({ data: mockHistory });

      const result = await contentService.getContentHistory(50, 0, 'product-123');

      expect(mockedApi.get).toHaveBeenCalledWith('/content/history', {
        params: { limit: 50, offset: 0, product_id: 'product-123' }
      });
      expect(result).toEqual(mockHistory);
    });
  });

  describe('Error handling', () => {
    it('should handle network errors consistently', async () => {
      const networkError = new Error('Network Error');
      mockedApi.post.mockRejectedValue(networkError);

      await expect(contentService.generateContent({
        product_id: 'test',
        platforms: ['facebook']
      })).rejects.toThrow('Network Error');

      await expect(contentService.previewContent({
        content: { title: 'Test' },
        platforms: ['facebook']
      })).rejects.toThrow('Network Error');
    });

    it('should handle API response errors with status codes', async () => {
      const apiError = {
        response: {
          status: 422,
          data: { 
            message: 'Validation error',
            errors: { platforms: ['At least one platform is required'] }
          }
        }
      };
      mockedApi.post.mockRejectedValue(apiError);

      await expect(contentService.generateContent({
        product_id: 'test',
        platforms: []
      })).rejects.toEqual(apiError);
    });
  });
});