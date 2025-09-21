export interface ContentVariation {
  title: string;
  focus: string;
}

export interface PlatformContent {
  title: string;
  description: string;
  hashtags: string[];
  call_to_action: string;
  character_count: number;
  optimization_notes: string[];
}

export interface GeneratedContent {
  title: string;
  description: string;
  hashtags: string[];
  variations: ContentVariation[];
  platform_specific: Record<string, PlatformContent>;
}

export interface ContentGenerationInput {
  description: string;
  target_platforms: string[];
  product_category?: string;
  price_range?: string;
  target_audience?: string;
}

export interface ContentGenerationResult {
  success: boolean;
  content?: GeneratedContent;
  error?: string;
  message?: string;
  processing_time?: number;
}

export interface Platform {
  name: string;
  type: string;
  title_max_length: number;
  description_max_length: number;
  hashtag_limit: number;
  features: string[];
}

export interface PlatformsResponse {
  success: boolean;
  platforms: Record<string, Platform>;
  total_count: number;
}

export interface ValidationIssue {
  field: string;
  issue: string;
  current_length?: number;
  max_length?: number;
  current_count?: number;
  max_count?: number;
}

export interface ContentValidationResult {
  success: boolean;
  valid: boolean;
  platform: string;
  issues: ValidationIssue[];
  character_counts: {
    title: number;
    description: number;
    hashtag_count: number;
  };
}

export interface EditableContent {
  title: string;
  description: string;
  hashtags: string[];
  platform: string;
}

export interface ContentReviewState {
  originalContent: GeneratedContent;
  editedContent: Record<string, EditableContent>;
  selectedPlatforms: string[];
  isEditing: boolean;
  validationResults: Record<string, ContentValidationResult>;
}