import { preferencesService } from '../preferences';
import { apiClient } from '../../utils/api';

// Mock the API client
jest.mock('../../utils/api');
const mockApiClient = apiClient as jest.Mocked<typeof apiClient>;

const mockPreferences = {
  id: '1',
  user_id: 'user1',
  platform: 'facebook',
  enabled: true,
  auto_post: true,
  priority: 0,
  content_style: 'professional',
  hashtag_strategy: 'branded',
  max_hashtags: 5,
  posting_schedule: {
    monday: ['09:00', '15:00'],
    tuesday: ['09:00', '15:00']
  },
  timezone: 'UTC',
  auto_schedule: false,
  optimal_times_enabled: true,
  platform_settings: {},
  title_format: '{title}',
  description_format: '{description}',
  include_branding: true,
  include_call_to_action: true,
  image_optimization: true,
  watermark_enabled: false,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z'
};

const mockTemplate = {
  id: '1',
  user_id: 'user1',
  name: 'Test Template',
  description: 'A test template',
  title_template: '✨ {title} ✨',
  description_template: '{description}\n\nTest footer',
  hashtag_template: '#test #template',
  platforms: ['facebook', 'instagram'],
  category: 'general',
  style: 'professional',
  usage_count: 5,
  is_default: true,
  is_system_template: false,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z'
};

describe('PreferencesService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Platform Preferences', () => {
    it('gets all platform preferences', async () => {
      mockApiClient.get.mockResolvedValue({ data: [mockPreferences] });

      const result = await preferencesService.getAllPlatformPreferences();

      expect(mockApiClient.get).toHaveBeenCalledWith('/preferences/platforms');
      expect(result).toEqual([mockPreferences]);
    });

    it('gets platform preferences for specific platform', async () => {
      mockApiClient.get.mockResolvedValue({ data: mockPreferences });

      const result = await preferencesService.getPlatformPreferences('facebook');

      expect(mockApiClient.get).toHaveBeenCalledWith('/preferences/platforms/facebook');
      expect(result).toEqual(mockPreferences);
    });

    it('creates platform preferences', async () => {
      const createData = {
        platform: 'facebook',
        enabled: true,
        auto_post: false,
        priority: 5
      };
      mockApiClient.post.mockResolvedValue({ data: mockPreferences });

      const result = await preferencesService.createPlatformPreferences('facebook', createData);

      expect(mockApiClient.post).toHaveBeenCalledWith('/preferences/platforms/facebook', createData);
      expect(result).toEqual(mockPreferences);
    });

    it('updates platform preferences', async () => {
      const updateData = {
        enabled: false,
        priority: 8
      };
      mockApiClient.put.mockResolvedValue({ data: { ...mockPreferences, ...updateData } });

      const result = await preferencesService.updatePlatformPreferences('facebook', updateData);

      expect(mockApiClient.put).toHaveBeenCalledWith('/preferences/platforms/facebook', updateData);
      expect(result.enabled).toBe(false);
      expect(result.priority).toBe(8);
    });

    it('resets platform preferences', async () => {
      const resetResponse = { message: 'Preferences reset successfully' };
      mockApiClient.delete.mockResolvedValue({ data: resetResponse });

      const result = await preferencesService.resetPlatformPreferences('facebook');

      expect(mockApiClient.delete).toHaveBeenCalledWith('/preferences/platforms/facebook');
      expect(result).toEqual(resetResponse);
    });
  });

  describe('Content Templates', () => {
    it('gets content templates without filters', async () => {
      mockApiClient.get.mockResolvedValue({ data: [mockTemplate] });

      const result = await preferencesService.getContentTemplates();

      expect(mockApiClient.get).toHaveBeenCalledWith('/preferences/templates?');
      expect(result).toEqual([mockTemplate]);
    });

    it('gets content templates with filters', async () => {
      mockApiClient.get.mockResolvedValue({ data: [mockTemplate] });

      const filters = {
        platform: 'facebook',
        category: 'jewelry',
        style: 'professional',
        include_system: false
      };

      const result = await preferencesService.getContentTemplates(filters);

      expect(mockApiClient.get).toHaveBeenCalledWith(
        '/preferences/templates?platform=facebook&category=jewelry&style=professional&include_system=false'
      );
      expect(result).toEqual([mockTemplate]);
    });

    it('gets specific content template', async () => {
      mockApiClient.get.mockResolvedValue({ data: mockTemplate });

      const result = await preferencesService.getContentTemplate('1');

      expect(mockApiClient.get).toHaveBeenCalledWith('/preferences/templates/1');
      expect(result).toEqual(mockTemplate);
    });

    it('creates content template', async () => {
      const createData = {
        name: 'New Template',
        title_template: '{title}',
        description_template: '{description}',
        platforms: ['facebook'],
        style: 'professional'
      };
      mockApiClient.post.mockResolvedValue({ data: mockTemplate });

      const result = await preferencesService.createContentTemplate(createData);

      expect(mockApiClient.post).toHaveBeenCalledWith('/preferences/templates', createData);
      expect(result).toEqual(mockTemplate);
    });

    it('updates content template', async () => {
      const updateData = {
        name: 'Updated Template',
        style: 'casual'
      };
      mockApiClient.put.mockResolvedValue({ data: { ...mockTemplate, ...updateData } });

      const result = await preferencesService.updateContentTemplate('1', updateData);

      expect(mockApiClient.put).toHaveBeenCalledWith('/preferences/templates/1', updateData);
      expect(result.name).toBe('Updated Template');
      expect(result.style).toBe('casual');
    });

    it('deletes content template', async () => {
      const deleteResponse = { message: 'Template deleted successfully' };
      mockApiClient.delete.mockResolvedValue({ data: deleteResponse });

      const result = await preferencesService.deleteContentTemplate('1');

      expect(mockApiClient.delete).toHaveBeenCalledWith('/preferences/templates/1');
      expect(result).toEqual(deleteResponse);
    });

    it('marks template as used', async () => {
      const useResponse = { message: 'Template usage recorded' };
      mockApiClient.post.mockResolvedValue({ data: useResponse });

      const result = await preferencesService.useContentTemplate('1');

      expect(mockApiClient.post).toHaveBeenCalledWith('/preferences/templates/1/use');
      expect(result).toEqual(useResponse);
    });
  });

  describe('Utility Methods', () => {
    it('gets default template for platform', async () => {
      const templates = [
        { ...mockTemplate, is_default: false },
        { ...mockTemplate, id: '2', is_default: true }
      ];
      mockApiClient.get.mockResolvedValue({ data: templates });

      const result = await preferencesService.getDefaultTemplate('facebook');

      expect(result).toEqual(templates[1]);
    });

    it('returns null when no default template found', async () => {
      mockApiClient.get.mockResolvedValue({ data: [] });

      const result = await preferencesService.getDefaultTemplate('facebook');

      expect(result).toBeNull();
    });

    it('gets optimal posting times for platform', async () => {
      mockApiClient.get.mockResolvedValue({ data: mockPreferences });

      const result = await preferencesService.getOptimalPostingTimes('facebook');

      // Should return today's schedule (mocked as Monday)
      const today = new Date().toLocaleDateString('en-US', { weekday: 'long' }).toLowerCase();
      const expectedTimes = mockPreferences.posting_schedule[today] || [];
      
      expect(result).toEqual(expectedTimes);
    });

    it('checks if auto-post is enabled', async () => {
      mockApiClient.get.mockResolvedValue({ data: mockPreferences });

      const result = await preferencesService.shouldAutoPost('facebook');

      expect(result).toBe(true);
    });

    it('checks if platform is enabled', async () => {
      mockApiClient.get.mockResolvedValue({ data: mockPreferences });

      const result = await preferencesService.isPlatformEnabled('facebook');

      expect(result).toBe(true);
    });

    it('gets platform priority', async () => {
      mockApiClient.get.mockResolvedValue({ data: mockPreferences });

      const result = await preferencesService.getPlatformPriority('facebook');

      expect(result).toBe(0);
    });

    it('gets content style', async () => {
      mockApiClient.get.mockResolvedValue({ data: mockPreferences });

      const result = await preferencesService.getContentStyle('facebook');

      expect(result).toBe('professional');
    });

    it('gets hashtag strategy', async () => {
      mockApiClient.get.mockResolvedValue({ data: mockPreferences });

      const result = await preferencesService.getHashtagStrategy('facebook');

      expect(result).toBe('branded');
    });

    it('gets max hashtags', async () => {
      mockApiClient.get.mockResolvedValue({ data: mockPreferences });

      const result = await preferencesService.getMaxHashtags('facebook');

      expect(result).toBe(5);
    });

    it('formats content for platform', async () => {
      const preferencesWithFormat = {
        ...mockPreferences,
        title_format: '✨ {title} ✨',
        description_format: '{description}\n\nVisit our store!'
      };
      mockApiClient.get.mockResolvedValue({ data: preferencesWithFormat });

      const result = await preferencesService.formatContentForPlatform(
        'facebook',
        'Test Product',
        'This is a test product.'
      );

      expect(result.title).toBe('✨ Test Product ✨');
      expect(result.description).toBe('This is a test product.\n\nVisit our store!');
    });

    it('handles errors gracefully in utility methods', async () => {
      mockApiClient.get.mockRejectedValue(new Error('API Error'));

      // Should return defaults when API fails
      expect(await preferencesService.shouldAutoPost('facebook')).toBe(true);
      expect(await preferencesService.isPlatformEnabled('facebook')).toBe(true);
      expect(await preferencesService.getPlatformPriority('facebook')).toBe(0);
      expect(await preferencesService.getContentStyle('facebook')).toBe('professional');
      expect(await preferencesService.getHashtagStrategy('facebook')).toBe('mixed');
      expect(await preferencesService.getMaxHashtags('facebook')).toBe(10);

      const formatResult = await preferencesService.formatContentForPlatform(
        'facebook',
        'Test',
        'Description'
      );
      expect(formatResult).toEqual({ title: 'Test', description: 'Description' });
    });
  });
});