import apiClient from '../utils/api';
import {
  ContentGenerationInput,
  ContentGenerationResult,
  PlatformsResponse,
  ContentValidationResult,
  EditableContent
} from '../types/content';

export const contentService = {
  /**
   * Generate content using AI
   */
  async generateContent(input: ContentGenerationInput): Promise<ContentGenerationResult> {
    try {
      // Use longer timeout for content generation (60 seconds)
      const response = await apiClient.post('/content/generate', input, {
        timeout: 60000
      });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to generate content');
    }
  },

  /**
   * Get supported platforms and their specifications
   */
  async getSupportedPlatforms(): Promise<PlatformsResponse> {
    try {
      const response = await apiClient.get('/content/platforms');
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to fetch platforms');
    }
  },

  /**
   * Validate content against platform requirements
   */
  async validateContent(content: EditableContent): Promise<ContentValidationResult> {
    try {
      const response = await apiClient.post('/content/validate', {
        platform: content.platform,
        title: content.title,
        description: content.description,
        hashtags: content.hashtags
      });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to validate content');
    }
  },

  /**
   * Check content service health
   */
  async checkHealth(): Promise<any> {
    try {
      const response = await apiClient.get('/content/health');
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to check service health');
    }
  }
};