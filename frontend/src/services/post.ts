import apiClient from '../utils/api';
import {
  Post,
  PostCreate,
  PostUpdate,
  PostListResponse,
  PostingRequest,
  SchedulePostRequest,
  PostingResult,
  PostQueueItem,
  PostFilters,
  BulkPostingRequest
} from '../types/post';

export const postService = {
  /**
   * Create a new post
   */
  async createPost(postData: PostCreate): Promise<Post> {
    try {
      const response = await apiClient.post('/posts/', postData);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to create post');
    }
  },

  /**
   * Get posts with pagination and filtering
   */
  async getPosts(
    skip: number = 0,
    limit: number = 50,
    filters?: PostFilters
  ): Promise<PostListResponse> {
    try {
      const params = new URLSearchParams({
        skip: skip.toString(),
        limit: limit.toString(),
      });

      if (filters?.status) params.append('status', filters.status);
      if (filters?.product_id) params.append('product_id', filters.product_id);

      const response = await apiClient.get(`/posts/?${params.toString()}`);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to fetch posts');
    }
  },

  /**
   * Get a specific post by ID
   */
  async getPost(postId: string): Promise<Post> {
    try {
      const response = await apiClient.get(`/posts/${postId}`);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to fetch post');
    }
  },

  /**
   * Update a post
   */
  async updatePost(postId: string, updateData: PostUpdate): Promise<Post> {
    try {
      const response = await apiClient.put(`/posts/${postId}`, updateData);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to update post');
    }
  },

  /**
   * Delete a post
   */
  async deletePost(postId: string): Promise<void> {
    try {
      await apiClient.delete(`/posts/${postId}`);
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to delete post');
    }
  },

  /**
   * Publish a post immediately
   */
  async publishPost(request: PostingRequest): Promise<PostingResult> {
    try {
      const response = await apiClient.post('/posts/publish', request);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to publish post');
    }
  },

  /**
   * Schedule a post for later publishing
   */
  async schedulePost(request: SchedulePostRequest): Promise<PostingResult> {
    try {
      const response = await apiClient.post('/posts/schedule', request);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to schedule post');
    }
  },

  /**
   * Get post queue status
   */
  async getPostQueue(
    skip: number = 0,
    limit: number = 50,
    status?: string
  ): Promise<{ items: PostQueueItem[]; total: number }> {
    try {
      const params = new URLSearchParams({
        skip: skip.toString(),
        limit: limit.toString(),
      });

      if (status) params.append('status', status);

      const response = await apiClient.get(`/posts/queue?${params.toString()}`);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to fetch post queue');
    }
  },

  /**
   * Cancel a scheduled post
   */
  async cancelScheduledPost(postId: string): Promise<void> {
    try {
      await apiClient.post(`/posts/${postId}/cancel`);
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to cancel scheduled post');
    }
  },

  /**
   * Retry a failed post
   */
  async retryPost(postId: string, platforms?: string[]): Promise<PostingResult> {
    try {
      const response = await apiClient.post(`/posts/${postId}/retry`, { platforms });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to retry post');
    }
  },

  /**
   * Bulk publish multiple posts
   */
  async bulkPublish(request: BulkPostingRequest): Promise<PostingResult[]> {
    try {
      const response = await apiClient.post('/posts/bulk-publish', request);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to bulk publish posts');
    }
  },

  /**
   * Bulk schedule multiple posts
   */
  async bulkSchedule(request: BulkPostingRequest): Promise<PostingResult[]> {
    try {
      const response = await apiClient.post('/posts/bulk-schedule', request);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to bulk schedule posts');
    }
  },

  /**
   * Get post analytics/metrics
   */
  async getPostMetrics(postId: string): Promise<any> {
    try {
      const response = await apiClient.get(`/posts/${postId}/metrics`);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to fetch post metrics');
    }
  }
};