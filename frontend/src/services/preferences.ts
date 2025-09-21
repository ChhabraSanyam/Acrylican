import apiClient from '../utils/api';

export interface PlatformPreferences {
  id: string;
  user_id: string;
  platform: string;
  enabled: boolean;
  auto_post: boolean;
  priority: number;
  default_template?: string;
  content_style?: string;
  hashtag_strategy?: string;
  max_hashtags?: number;
  posting_schedule?: { [key: string]: string[] };
  timezone: string;
  auto_schedule: boolean;
  optimal_times_enabled: boolean;
  platform_settings?: { [key: string]: any };
  title_format?: string;
  description_format?: string;
  include_branding: boolean;
  include_call_to_action: boolean;
  image_optimization: boolean;
  watermark_enabled: boolean;
  image_filters?: { [key: string]: number };
  created_at: string;
  updated_at: string;
}

export interface ContentTemplate {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  title_template: string;
  description_template: string;
  hashtag_template?: string;
  platforms: string[];
  category?: string;
  style: string;
  usage_count: number;
  is_default: boolean;
  is_system_template: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreatePlatformPreferences {
  platform: string;
  enabled?: boolean;
  auto_post?: boolean;
  priority?: number;
  default_template?: string;
  content_style?: string;
  hashtag_strategy?: string;
  max_hashtags?: number;
  posting_schedule?: { [key: string]: string[] };
  timezone?: string;
  auto_schedule?: boolean;
  optimal_times_enabled?: boolean;
  platform_settings?: { [key: string]: any };
  title_format?: string;
  description_format?: string;
  include_branding?: boolean;
  include_call_to_action?: boolean;
  image_optimization?: boolean;
  watermark_enabled?: boolean;
  image_filters?: { [key: string]: number };
}

export interface UpdatePlatformPreferences {
  enabled?: boolean;
  auto_post?: boolean;
  priority?: number;
  default_template?: string;
  content_style?: string;
  hashtag_strategy?: string;
  max_hashtags?: number;
  posting_schedule?: { [key: string]: string[] };
  timezone?: string;
  auto_schedule?: boolean;
  optimal_times_enabled?: boolean;
  platform_settings?: { [key: string]: any };
  title_format?: string;
  description_format?: string;
  include_branding?: boolean;
  include_call_to_action?: boolean;
  image_optimization?: boolean;
  watermark_enabled?: boolean;
  image_filters?: { [key: string]: number };
}

export interface CreateContentTemplate {
  name: string;
  description?: string;
  title_template: string;
  description_template: string;
  hashtag_template?: string;
  platforms: string[];
  category?: string;
  style: string;
  is_default?: boolean;
}

export interface UpdateContentTemplate {
  name?: string;
  description?: string;
  title_template?: string;
  description_template?: string;
  hashtag_template?: string;
  platforms?: string[];
  category?: string;
  style?: string;
  is_default?: boolean;
}

export interface TemplateFilters {
  platform?: string;
  category?: string;
  style?: string;
  include_system?: boolean;
}

class PreferencesService {
  private baseUrl = '/preferences';

  // Platform Preferences
  async getAllPlatformPreferences(): Promise<PlatformPreferences[]> {
    const response = await apiClient.get(`${this.baseUrl}/platforms`);
    return response.data;
  }

  async getPlatformPreferences(platform: string): Promise<PlatformPreferences> {
    const response = await apiClient.get(`${this.baseUrl}/platforms/${platform}`);
    return response.data;
  }

  async createPlatformPreferences(
    platform: string,
    preferences: CreatePlatformPreferences
  ): Promise<PlatformPreferences> {
    const response = await apiClient.post(`${this.baseUrl}/platforms/${platform}`, preferences);
    return response.data;
  }

  async updatePlatformPreferences(
    platform: string,
    preferences: UpdatePlatformPreferences
  ): Promise<PlatformPreferences> {
    const response = await apiClient.put(`${this.baseUrl}/platforms/${platform}`, preferences);
    return response.data;
  }

  async resetPlatformPreferences(platform: string): Promise<{ message: string }> {
    const response = await apiClient.delete(`${this.baseUrl}/platforms/${platform}`);
    return response.data;
  }

  // Content Templates
  async getContentTemplates(filters?: TemplateFilters): Promise<ContentTemplate[]> {
    const params = new URLSearchParams();
    
    if (filters?.platform) params.append('platform', filters.platform);
    if (filters?.category) params.append('category', filters.category);
    if (filters?.style) params.append('style', filters.style);
    if (filters?.include_system !== undefined) {
      params.append('include_system', filters.include_system.toString());
    }

    const response = await apiClient.get(`${this.baseUrl}/templates?${params.toString()}`);
    return response.data;
  }

  async getContentTemplate(templateId: string): Promise<ContentTemplate> {
    const response = await apiClient.get(`${this.baseUrl}/templates/${templateId}`);
    return response.data;
  }

  async createContentTemplate(template: CreateContentTemplate): Promise<ContentTemplate> {
    const response = await apiClient.post(`${this.baseUrl}/templates`, template);
    return response.data;
  }

  async updateContentTemplate(
    templateId: string,
    template: UpdateContentTemplate
  ): Promise<ContentTemplate> {
    const response = await apiClient.put(`${this.baseUrl}/templates/${templateId}`, template);
    return response.data;
  }

  async deleteContentTemplate(templateId: string): Promise<{ message: string }> {
    const response = await apiClient.delete(`${this.baseUrl}/templates/${templateId}`);
    return response.data;
  }

  async useContentTemplate(templateId: string): Promise<{ message: string }> {
    const response = await apiClient.post(`${this.baseUrl}/templates/${templateId}/use`);
    return response.data;
  }

  // Utility methods
  async getDefaultTemplate(
    platform: string,
    category?: string
  ): Promise<ContentTemplate | null> {
    try {
      const templates = await this.getContentTemplates({
        platform,
        category,
        include_system: true
      });
      
      return templates.find(t => t.is_default) || null;
    } catch (error) {
      console.error('Error getting default template:', error);
      return null;
    }
  }

  async getOptimalPostingTimes(platform: string): Promise<string[]> {
    try {
      const preferences = await this.getPlatformPreferences(platform);
      const today = new Date().toLocaleDateString('en-US', { weekday: 'long' }).toLowerCase();
      
      return preferences.posting_schedule?.[today] || [];
    } catch (error) {
      console.error('Error getting optimal posting times:', error);
      return [];
    }
  }

  async shouldAutoPost(platform: string): Promise<boolean> {
    try {
      const preferences = await this.getPlatformPreferences(platform);
      return preferences.auto_post;
    } catch (error) {
      console.error('Error checking auto-post setting:', error);
      return true; // Default to true
    }
  }

  async isPlatformEnabled(platform: string): Promise<boolean> {
    try {
      const preferences = await this.getPlatformPreferences(platform);
      return preferences.enabled;
    } catch (error) {
      console.error('Error checking platform enabled status:', error);
      return true; // Default to true
    }
  }

  async getPlatformPriority(platform: string): Promise<number> {
    try {
      const preferences = await this.getPlatformPreferences(platform);
      return preferences.priority;
    } catch (error) {
      console.error('Error getting platform priority:', error);
      return 0; // Default priority
    }
  }

  async getContentStyle(platform: string): Promise<string> {
    try {
      const preferences = await this.getPlatformPreferences(platform);
      return preferences.content_style || 'professional';
    } catch (error) {
      console.error('Error getting content style:', error);
      return 'professional'; // Default style
    }
  }

  async getHashtagStrategy(platform: string): Promise<string> {
    try {
      const preferences = await this.getPlatformPreferences(platform);
      return preferences.hashtag_strategy || 'mixed';
    } catch (error) {
      console.error('Error getting hashtag strategy:', error);
      return 'mixed'; // Default strategy
    }
  }

  async getMaxHashtags(platform: string): Promise<number> {
    try {
      const preferences = await this.getPlatformPreferences(platform);
      return preferences.max_hashtags || 10;
    } catch (error) {
      console.error('Error getting max hashtags:', error);
      return 10; // Default max hashtags
    }
  }

  async formatContentForPlatform(
    platform: string,
    title: string,
    description: string
  ): Promise<{ title: string; description: string }> {
    try {
      const preferences = await this.getPlatformPreferences(platform);
      
      // Apply title format
      let formattedTitle = preferences.title_format || '{title}';
      formattedTitle = formattedTitle.replace('{title}', title);
      
      // Apply description format
      let formattedDescription = preferences.description_format || '{description}';
      formattedDescription = formattedDescription.replace('{description}', description);
      
      return {
        title: formattedTitle,
        description: formattedDescription
      };
    } catch (error) {
      console.error('Error formatting content for platform:', error);
      return { title, description }; // Return original content on error
    }
  }
}

export const preferencesService = new PreferencesService();