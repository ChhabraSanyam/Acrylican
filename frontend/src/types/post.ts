export interface PostCreate {
  product_id?: string;
  title: string;
  description: string;
  hashtags: string[];
  images: string[];
  target_platforms: string[];
  product_data?: Record<string, any>;
  platform_specific_content?: Record<string, any>;
  scheduled_at?: string;
  priority?: number;
}

export interface PostUpdate {
  title?: string;
  description?: string;
  hashtags?: string[];
  images?: string[];
  target_platforms?: string[];
  product_data?: Record<string, any>;
  platform_specific_content?: Record<string, any>;
  scheduled_at?: string;
  priority?: number;
}

export interface PostResult {
  platform: string;
  status: string;
  post_id?: string;
  url?: string;
  error_message?: string;
  error_code?: string;
  published_at?: string;
  retry_count: number;
  metadata?: Record<string, any>;
}

export interface Post {
  id: string;
  user_id: string;
  product_id?: string;
  title: string;
  description: string;
  hashtags: string[];
  images: string[];
  target_platforms: string[];
  product_data?: Record<string, any>;
  platform_specific_content?: Record<string, any>;
  scheduled_at?: string;
  published_at?: string;
  status: string;
  results?: PostResult[];
  priority: number;
  retry_count: number;
  max_retries: number;
  last_error?: string;
  created_at: string;
  updated_at: string;
}

export interface PostListResponse {
  posts: Post[];
  total: number;
  skip: number;
  limit: number;
}

export interface PostQueueItem {
  id: string;
  post_id: string;
  platform: string;
  status: string;
  priority: number;
  scheduled_at: string;
  started_at?: string;
  completed_at?: string;
  retry_count: number;
  max_retries: number;
  result?: PostResult;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface PostingRequest {
  post_id: string;
  platforms?: string[];
}

export interface SchedulePostRequest {
  post_id: string;
  scheduled_at: string;
  platforms?: string[];
}

export interface PostingResult {
  success: boolean;
  post_id: string;
  results: PostResult[];
  queued_items: string[];
  message?: string;
}

export enum PostStatus {
  DRAFT = 'draft',
  SCHEDULED = 'scheduled',
  PUBLISHING = 'publishing',
  PUBLISHED = 'published',
  FAILED = 'failed'
}

export enum QueueStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed',
  RETRYING = 'retrying'
}

export interface PostFilters {
  status?: string;
  product_id?: string;
  platform?: string;
  date_from?: string;
  date_to?: string;
}

export interface BulkPostingRequest {
  post_ids: string[];
  scheduled_at?: string;
  platforms?: string[];
}