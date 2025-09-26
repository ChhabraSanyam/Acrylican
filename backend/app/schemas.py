from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class UserRegistration(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128, description="Password must be between 8-128 characters long")
    business_name: str = Field(..., min_length=1, max_length=255)
    business_type: str = Field(..., min_length=1, max_length=100)
    business_description: Optional[str] = Field(None, max_length=5000)
    website: Optional[str] = None
    location: Optional[str] = Field(None, max_length=255)


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str = Field(..., max_length=128, description="Password cannot exceed 128 characters")


class UserResponse(BaseModel):
    """Schema for user data in responses."""
    id: str
    email: str
    business_name: str
    business_type: str
    business_description: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """Schema for token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessTokenResponse(BaseModel):
    """Schema for access token only response (used in refresh)."""
    access_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    """Schema for token refresh request."""
    refresh_token: str


class AuthResult(BaseModel):
    """Schema for authentication result."""
    success: bool
    user: Optional[UserResponse] = None
    tokens: Optional[TokenResponse] = None
    message: Optional[str] = None


# Product and Image schemas
class ProductImageResponse(BaseModel):
    """Schema for product image response."""
    id: str
    original_filename: str
    original_url: str
    compressed_url: str
    thumbnail_urls: Dict[str, str]  # {"small": "url", "medium": "url", "large": "url"}
    platform_optimized_urls: Optional[Dict[str, str]] = None  # {"facebook": "url", "instagram": "url"}
    storage_paths: Dict[str, str]  # {"original": "path", "compressed": "path", ...}
    file_size: int
    dimensions: Dict[str, int]
    format: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    """Schema for creating a product."""
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1, max_length=5000)


class ProductUpdate(BaseModel):
    """Schema for updating a product."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1, max_length=5000)


class ProductResponse(BaseModel):
    """Schema for product response."""
    id: str
    user_id: str
    title: str
    description: str
    generated_content: Optional[Dict] = None
    images: List[ProductImageResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductListResponse(BaseModel):
    """Schema for product list response with pagination."""
    products: List[ProductResponse]
    total: int
    skip: int
    limit: int


class ImageUploadResponse(BaseModel):
    """Schema for image upload response."""
    success: bool
    image_id: str
    message: str
    urls: Dict  # {"original": "url", "compressed": "url", "thumbnails": {...}, "platform_optimized": {...}}


class ImageProcessingResult(BaseModel):
    """Schema for image processing result."""
    id: str
    original_filename: str
    file_size: int
    dimensions: Dict[str, int]
    format: str
    processing_time: Optional[float] = None
    platform_optimizations: List[str] = []
    urls: Optional[Dict] = None  # {"original": "url", "compressed": "url", "thumbnails": {...}, "platform_optimized": {...}}


# Content Generation schemas
class ContentGenerationInput(BaseModel):
    """Schema for content generation input."""
    description: str = Field(..., min_length=10, max_length=5000, description="Product description")
    target_platforms: List[str] = Field(..., min_length=1, description="List of target platforms")
    product_category: Optional[str] = Field(None, max_length=100, description="Product category")
    price_range: Optional[str] = Field(None, max_length=50, description="Price range")
    target_audience: Optional[str] = Field(None, max_length=200, description="Target audience description")


class ContentVariation(BaseModel):
    """Schema for content variation."""
    title: str
    focus: str


class PlatformContent(BaseModel):
    """Schema for platform-specific content."""
    title: str
    description: str
    hashtags: List[str]
    call_to_action: str
    character_count: Dict[str, int]
    optimization_notes: str


class GeneratedContentResponse(BaseModel):
    """Schema for generated content response."""
    title: str
    description: str
    hashtags: List[str]
    variations: List[ContentVariation]
    platform_specific: Dict[str, PlatformContent]


class ContentGenerationResult(BaseModel):
    """Schema for content generation result."""
    success: bool
    content: Optional[GeneratedContentResponse] = None
    message: Optional[str] = None
    processing_time: Optional[float] = None


# Posting System schemas
class PostCreate(BaseModel):
    """Schema for creating a post."""
    product_id: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(..., min_length=1, max_length=5000)
    hashtags: List[str] = Field(default_factory=list, max_length=50)
    images: List[str] = Field(default_factory=list, description="List of image URLs")
    target_platforms: List[str] = Field(..., min_length=1, description="List of platform names")
    product_data: Optional[Dict[str, Any]] = None
    platform_specific_content: Optional[Dict[str, Any]] = None
    scheduled_at: Optional[datetime] = None
    priority: int = Field(default=0, ge=0, le=10)


class PostUpdate(BaseModel):
    """Schema for updating a post."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = Field(None, min_length=1, max_length=5000)
    hashtags: Optional[List[str]] = Field(None, max_length=50)
    images: Optional[List[str]] = None
    target_platforms: Optional[List[str]] = None
    product_data: Optional[Dict[str, Any]] = None
    platform_specific_content: Optional[Dict[str, Any]] = None
    scheduled_at: Optional[datetime] = None
    priority: Optional[int] = Field(None, ge=0, le=10)


class PostResultResponse(BaseModel):
    """Schema for post result response."""
    platform: str
    status: str
    post_id: Optional[str] = None
    url: Optional[str] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    published_at: Optional[datetime] = None
    retry_count: int = 0
    metadata: Optional[Dict[str, Any]] = None


class PostResponse(BaseModel):
    """Schema for post response."""
    id: str
    user_id: str
    product_id: Optional[str] = None
    title: str
    description: str
    hashtags: List[str]
    images: List[str]
    target_platforms: List[str]
    product_data: Optional[Dict[str, Any]] = None
    platform_specific_content: Optional[Dict[str, Any]] = None
    scheduled_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    status: str
    results: Optional[List[PostResultResponse]] = None
    priority: int
    retry_count: int
    max_retries: int
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PostListResponse(BaseModel):
    """Schema for post list response with pagination."""
    posts: List[PostResponse]
    total: int
    skip: int
    limit: int


class PostQueueResponse(BaseModel):
    """Schema for post queue item response."""
    id: str
    post_id: str
    platform: str
    status: str
    priority: int
    scheduled_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int
    max_retries: int
    result: Optional[PostResultResponse] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PostingRequest(BaseModel):
    """Schema for immediate posting request."""
    post_id: str
    platforms: Optional[List[str]] = None  # If None, use post's target_platforms


class SchedulePostRequest(BaseModel):
    """Schema for scheduling a post."""
    post_id: str
    scheduled_at: datetime
    platforms: Optional[List[str]] = None  # If None, use post's target_platforms


class PostingResult(BaseModel):
    """Schema for posting operation result."""
    success: bool
    post_id: str
    results: List[PostResultResponse]
    queued_items: List[str]  # Queue item IDs
    message: Optional[str] = None


# Platform Preferences schemas
class PlatformPreferencesCreate(BaseModel):
    """Schema for creating platform preferences."""
    platform: str = Field(..., description="Platform identifier")
    enabled: bool = Field(default=True, description="Whether platform is enabled for posting")
    auto_post: bool = Field(default=True, description="Whether to auto-post to this platform")
    priority: int = Field(default=0, ge=0, le=10, description="Posting priority (0-10)")
    default_template: Optional[str] = Field(None, description="Default content template name")
    content_style: Optional[str] = Field(None, description="Content style preference")
    hashtag_strategy: Optional[str] = Field(None, description="Hashtag strategy")
    max_hashtags: Optional[int] = Field(None, ge=0, le=50, description="Maximum hashtags override")
    posting_schedule: Optional[Dict[str, List[str]]] = Field(None, description="Weekly posting schedule")
    timezone: str = Field(default="UTC", description="User timezone")
    auto_schedule: bool = Field(default=False, description="Enable automatic scheduling")
    optimal_times_enabled: bool = Field(default=True, description="Use optimal posting times")
    platform_settings: Optional[Dict[str, Any]] = Field(None, description="Platform-specific settings")
    title_format: Optional[str] = Field(None, description="Title formatting template")
    description_format: Optional[str] = Field(None, description="Description formatting template")
    include_branding: bool = Field(default=True, description="Include branding in posts")
    include_call_to_action: bool = Field(default=True, description="Include call-to-action")
    image_optimization: bool = Field(default=True, description="Enable image optimization")
    watermark_enabled: bool = Field(default=False, description="Enable watermark on images")
    image_filters: Optional[Dict[str, float]] = Field(None, description="Image filter settings")


class PlatformPreferencesUpdate(BaseModel):
    """Schema for updating platform preferences."""
    enabled: Optional[bool] = None
    auto_post: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=0, le=10)
    default_template: Optional[str] = None
    content_style: Optional[str] = None
    hashtag_strategy: Optional[str] = None
    max_hashtags: Optional[int] = Field(None, ge=0, le=50)
    posting_schedule: Optional[Dict[str, List[str]]] = None
    timezone: Optional[str] = None
    auto_schedule: Optional[bool] = None
    optimal_times_enabled: Optional[bool] = None
    platform_settings: Optional[Dict[str, Any]] = None
    title_format: Optional[str] = None
    description_format: Optional[str] = None
    include_branding: Optional[bool] = None
    include_call_to_action: Optional[bool] = None
    image_optimization: Optional[bool] = None
    watermark_enabled: Optional[bool] = None
    image_filters: Optional[Dict[str, float]] = None


class PlatformPreferencesResponse(BaseModel):
    """Schema for platform preferences response."""
    id: str
    user_id: str
    platform: str
    enabled: bool
    auto_post: bool
    priority: int
    default_template: Optional[str] = None
    content_style: Optional[str] = None
    hashtag_strategy: Optional[str] = None
    max_hashtags: Optional[int] = None
    posting_schedule: Optional[Dict[str, List[str]]] = None
    timezone: str
    auto_schedule: bool
    optimal_times_enabled: bool
    platform_settings: Optional[Dict[str, Any]] = None
    title_format: Optional[str] = None
    description_format: Optional[str] = None
    include_branding: bool
    include_call_to_action: bool
    image_optimization: bool
    watermark_enabled: bool
    image_filters: Optional[Dict[str, float]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# Content Template schemas
class ContentTemplateCreate(BaseModel):
    """Schema for creating content templates."""
    name: str = Field(..., min_length=1, max_length=100, description="Template name")
    description: Optional[str] = Field(None, max_length=500, description="Template description")
    title_template: str = Field(..., min_length=1, max_length=1000, description="Title template")
    description_template: str = Field(..., min_length=1, max_length=5000, description="Description template")
    hashtag_template: Optional[str] = Field(None, max_length=1000, description="Hashtag template")
    platforms: List[str] = Field(..., min_length=1, description="Applicable platforms")
    category: Optional[str] = Field(None, max_length=100, description="Product category")
    style: str = Field(..., description="Content style")
    is_default: bool = Field(default=False, description="Set as default template")


class ContentTemplateUpdate(BaseModel):
    """Schema for updating content templates."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    title_template: Optional[str] = Field(None, min_length=1, max_length=1000)
    description_template: Optional[str] = Field(None, min_length=1, max_length=5000)
    hashtag_template: Optional[str] = Field(None, max_length=1000)
    platforms: Optional[List[str]] = Field(None, min_length=1)
    category: Optional[str] = Field(None, max_length=100)
    style: Optional[str] = None
    is_default: Optional[bool] = None


class ContentTemplateResponse(BaseModel):
    """Schema for content template response."""
    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    title_template: str
    description_template: str
    hashtag_template: Optional[str] = None
    platforms: List[str]
    category: Optional[str] = None
    style: str
    usage_count: int
    is_default: bool
    is_system_template: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# Sales Tracking schemas
class SaleEventCreate(BaseModel):
    """Schema for creating a sale event."""
    product_id: Optional[str] = None
    platform: str = Field(..., description="Platform where the sale occurred")
    order_id: str = Field(..., description="Platform-specific order ID")
    amount: float = Field(..., gt=0, description="Sale amount")
    currency: str = Field(default="INR", description="Currency code")
    product_title: Optional[str] = Field(None, max_length=500)
    product_sku: Optional[str] = Field(None, max_length=100)
    quantity: int = Field(default=1, gt=0)
    customer_location: Optional[str] = Field(None, max_length=200)
    customer_type: Optional[str] = Field(None, max_length=50)
    sale_source: Optional[str] = Field(None, max_length=100)
    commission_rate: Optional[float] = Field(None, ge=0, le=1)
    commission_amount: Optional[float] = Field(None, ge=0)
    net_amount: Optional[float] = Field(None, ge=0)
    post_id: Optional[str] = None
    referral_source: Optional[str] = Field(None, max_length=200)
    campaign_id: Optional[str] = Field(None, max_length=100)
    occurred_at: datetime = Field(..., description="When the sale occurred")
    status: str = Field(default="confirmed", description="Sale status")
    platform_data: Optional[Dict[str, Any]] = None


class SaleEventUpdate(BaseModel):
    """Schema for updating a sale event."""
    product_id: Optional[str] = None
    amount: Optional[float] = Field(None, gt=0)
    currency: Optional[str] = None
    product_title: Optional[str] = Field(None, max_length=500)
    product_sku: Optional[str] = Field(None, max_length=100)
    quantity: Optional[int] = Field(None, gt=0)
    customer_location: Optional[str] = Field(None, max_length=200)
    customer_type: Optional[str] = Field(None, max_length=50)
    sale_source: Optional[str] = Field(None, max_length=100)
    commission_rate: Optional[float] = Field(None, ge=0, le=1)
    commission_amount: Optional[float] = Field(None, ge=0)
    net_amount: Optional[float] = Field(None, ge=0)
    post_id: Optional[str] = None
    referral_source: Optional[str] = Field(None, max_length=200)
    campaign_id: Optional[str] = Field(None, max_length=100)
    occurred_at: Optional[datetime] = None
    status: Optional[str] = None
    platform_data: Optional[Dict[str, Any]] = None


class SaleEventResponse(BaseModel):
    """Schema for sale event response."""
    id: str
    user_id: str
    product_id: Optional[str] = None
    platform: str
    order_id: str
    amount: float
    currency: str
    product_title: Optional[str] = None
    product_sku: Optional[str] = None
    quantity: int
    customer_location: Optional[str] = None
    customer_type: Optional[str] = None
    sale_source: Optional[str] = None
    commission_rate: Optional[float] = None
    commission_amount: Optional[float] = None
    net_amount: Optional[float] = None
    post_id: Optional[str] = None
    referral_source: Optional[str] = None
    campaign_id: Optional[str] = None
    occurred_at: datetime
    recorded_at: datetime
    updated_at: datetime
    status: str
    sync_status: str
    platform_data: Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}


class SaleEventListResponse(BaseModel):
    """Schema for sale event list response with pagination."""
    sales: List[SaleEventResponse]
    total: int
    skip: int
    limit: int


class SalesMetrics(BaseModel):
    """Schema for sales metrics."""
    total_revenue: float
    total_orders: int
    average_order_value: float
    total_commission: float
    net_revenue: float
    currency: str
    period_start: datetime
    period_end: datetime


class PlatformSalesBreakdown(BaseModel):
    """Schema for platform-specific sales breakdown."""
    platform: str
    total_revenue: float
    total_orders: int
    average_order_value: float
    commission_rate: Optional[float] = None
    total_commission: float
    net_revenue: float
    top_products: List[Dict[str, Any]] = []


class SalesDashboardData(BaseModel):
    """Schema for sales dashboard data."""
    overall_metrics: SalesMetrics
    platform_breakdown: List[PlatformSalesBreakdown]
    top_products: List[Dict[str, Any]]
    recent_sales: List[SaleEventResponse]
    sales_trend: List[Dict[str, Any]]  # Daily/weekly sales data for charts


class SalesReportRequest(BaseModel):
    """Schema for sales report request."""
    start_date: datetime
    end_date: datetime
    platforms: Optional[List[str]] = None
    product_ids: Optional[List[str]] = None
    group_by: str = Field(default="day", description="Group by: day, week, month")
    include_details: bool = Field(default=False, description="Include detailed sale events")


# Engagement Metrics schemas
class EngagementMetricsCreate(BaseModel):
    """Schema for creating engagement metrics."""
    post_id: str = Field(..., description="Internal post ID")
    platform: str = Field(..., description="Platform identifier")
    platform_post_id: str = Field(..., description="Platform-specific post ID")
    likes: int = Field(default=0, ge=0, description="Number of likes")
    shares: int = Field(default=0, ge=0, description="Number of shares")
    comments: int = Field(default=0, ge=0, description="Number of comments")
    views: int = Field(default=0, ge=0, description="Number of views")
    reach: int = Field(default=0, ge=0, description="Number of people reached")
    engagement_rate: Optional[float] = Field(None, ge=0, le=100, description="Engagement rate percentage")
    click_through_rate: Optional[float] = Field(None, ge=0, le=100, description="Click-through rate percentage")
    platform_specific_metrics: Optional[Dict[str, Any]] = Field(None, description="Platform-specific metrics")
    collection_method: str = Field(default="api", description="How metrics were collected")
    data_quality: str = Field(default="complete", description="Quality of the data")
    metrics_date: datetime = Field(..., description="Date the metrics represent")


class EngagementMetricsUpdate(BaseModel):
    """Schema for updating engagement metrics."""
    likes: Optional[int] = Field(None, ge=0)
    shares: Optional[int] = Field(None, ge=0)
    comments: Optional[int] = Field(None, ge=0)
    views: Optional[int] = Field(None, ge=0)
    reach: Optional[int] = Field(None, ge=0)
    engagement_rate: Optional[float] = Field(None, ge=0, le=100)
    click_through_rate: Optional[float] = Field(None, ge=0, le=100)
    platform_specific_metrics: Optional[Dict[str, Any]] = None
    collection_method: Optional[str] = None
    data_quality: Optional[str] = None
    status: Optional[str] = None


class EngagementMetricsResponse(BaseModel):
    """Schema for engagement metrics response."""
    id: str
    user_id: str
    post_id: str
    platform: str
    platform_post_id: str
    likes: int
    shares: int
    comments: int
    views: int
    reach: int
    engagement_rate: Optional[float] = None
    click_through_rate: Optional[float] = None
    platform_specific_metrics: Optional[Dict[str, Any]] = None
    collection_method: str
    data_quality: str
    metrics_date: datetime
    collected_at: datetime
    updated_at: datetime
    status: str
    sync_status: str

    model_config = {"from_attributes": True}


class EngagementMetricsListResponse(BaseModel):
    """Schema for engagement metrics list response with pagination."""
    metrics: List[EngagementMetricsResponse]
    total: int
    skip: int
    limit: int


class MetricsAggregationResponse(BaseModel):
    """Schema for metrics aggregation response."""
    id: str
    user_id: str
    aggregation_type: str
    aggregation_key: str
    period_start: datetime
    period_end: datetime
    total_posts: int
    total_likes: int
    total_shares: int
    total_comments: int
    total_views: int
    total_reach: int
    average_engagement_rate: Optional[float] = None
    best_performing_post_id: Optional[str] = None
    worst_performing_post_id: Optional[str] = None
    platforms_included: Optional[List[str]] = None
    products_included: Optional[List[str]] = None
    aggregation_metadata: Optional[Dict[str, Any]] = None
    calculated_at: datetime
    updated_at: datetime
    status: str

    model_config = {"from_attributes": True}


class EngagementDashboardData(BaseModel):
    """Schema for engagement dashboard data."""
    total_engagement: Dict[str, int]  # {"likes": 1000, "shares": 200, "comments": 150, "views": 5000}
    engagement_by_platform: List[Dict[str, Any]]  # Platform breakdown
    engagement_trend: List[Dict[str, Any]]  # Time series data
    top_performing_posts: List[Dict[str, Any]]  # Best posts by engagement
    recent_metrics: List[EngagementMetricsResponse]  # Latest collected metrics
    average_engagement_rate: Optional[float] = None
    total_reach: int = 0


class MetricsCollectionRequest(BaseModel):
    """Schema for requesting metrics collection."""
    post_ids: Optional[List[str]] = Field(None, description="Specific post IDs to collect metrics for")
    platforms: Optional[List[str]] = Field(None, description="Specific platforms to collect from")
    start_date: Optional[datetime] = Field(None, description="Start date for historical collection")
    end_date: Optional[datetime] = Field(None, description="End date for historical collection")
    force_refresh: bool = Field(default=False, description="Force refresh of existing metrics")


class MetricsCollectionResult(BaseModel):
    """Schema for metrics collection result."""
    success: bool
    collected_count: int
    failed_count: int
    skipped_count: int
    errors: List[str] = []
    collected_metrics: List[str] = []  # List of metric IDs that were collected
    message: Optional[str] = None