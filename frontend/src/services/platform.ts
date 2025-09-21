import apiClient from '../utils/api';
import { PlatformInfo, ConnectionTestResult, SetupWizardInfo } from '../types/platform';

export const platformService = {
  // Get all platforms
  async getAllPlatforms(): Promise<PlatformInfo[]> {
    const response = await apiClient.get('/platforms/');
    return response.data;
  },

  // Get specific platform info
  async getPlatformInfo(platform: string): Promise<PlatformInfo> {
    const response = await apiClient.get(`/platforms/${platform}`);
    return response.data;
  },

  // Test platform connection
  async testConnection(platform: string): Promise<ConnectionTestResult> {
    const response = await apiClient.post(`/platforms/${platform}/test`);
    return response.data;
  },

  // Test all connections
  async testAllConnections(): Promise<{ results: ConnectionTestResult[] }> {
    const response = await apiClient.post('/platforms/test-all');
    return response.data;
  },

  // Enable platform
  async enablePlatform(platform: string): Promise<{ message: string }> {
    const response = await apiClient.post(`/platforms/${platform}/enable`);
    return response.data;
  },

  // Disable platform
  async disablePlatform(platform: string): Promise<{ message: string }> {
    const response = await apiClient.post(`/platforms/${platform}/disable`);
    return response.data;
  },

  // Get setup wizard info
  async getSetupWizardInfo(platform: string): Promise<SetupWizardInfo> {
    const response = await apiClient.get(`/platforms/${platform}/setup-wizard`);
    return response.data;
  },

  // OAuth flow initiation
  async initiateOAuthFlow(platform: string, shopDomain?: string): Promise<{ authorization_url: string; state: string }> {
    const params = shopDomain ? `?shop_domain=${encodeURIComponent(shopDomain)}` : '';
    const response = await apiClient.post(`/auth/${platform}/connect${params}`);
    return response.data;
  },

  // Disconnect platform
  async disconnectPlatform(platform: string): Promise<{ message: string }> {
    const response = await apiClient.post(`/auth/${platform}/disconnect`);
    return response.data;
  },

  // Validate platform connection
  async validateConnection(platform: string): Promise<{
    platform: string;
    is_valid: boolean;
    last_validated_at?: string;
    validation_error?: string;
  }> {
    const response = await apiClient.post(`/auth/${platform}/validate`);
    return response.data;
  }
};