from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, DECIMAL, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base
import uuid


class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    business_name = Column(String, nullable=False)
    business_type = Column(String, nullable=False)
    business_description = Column(Text)
    website = Column(String)
    location = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, business_name={self.business_name})>"


class Product(Base):
    __tablename__ = "products"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    generated_content = Column(JSON)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="products")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Product(id={self.id}, title={self.title}, user_id={self.user_id})>"


class ProductImage(Base):
    __tablename__ = "product_images"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    original_filename = Column(String, nullable=False)
    original_url = Column(String, nullable=False)
    compressed_url = Column(String, nullable=False)
    thumbnail_urls = Column(JSON, nullable=False)  # {"small": "url", "medium": "url", "large": "url"}
    platform_optimized_urls = Column(JSON)  # {"facebook": "url", "instagram": "url", ...}
    storage_paths = Column(JSON, nullable=False)  # {"original": "path", "compressed": "path", ...}
    file_size = Column(Integer, nullable=False)
    dimensions = Column(JSON, nullable=False)  # {"width": 800, "height": 600}
    format = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    product = relationship("Product", back_populates="images")

    def __repr__(self):
        return f"<ProductImage(id={self.id}, filename={self.original_filename}, product_id={self.product_id})>"


class PlatformConnection(Base):
    __tablename__ = "platform_connections"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    platform = Column(String, nullable=False)  # Platform enum value
    integration_type = Column(String, nullable=False)  # IntegrationType enum value
    auth_method = Column(String, nullable=False)  # AuthenticationMethod enum value
    
    # OAuth tokens (encrypted)
    access_token = Column(Text)  # Encrypted access token
    refresh_token = Column(Text)  # Encrypted refresh token
    token_type = Column(String, default="Bearer")
    
    # Token metadata
    expires_at = Column(DateTime)
    scope = Column(String)  # OAuth scopes granted
    
    # Platform-specific data
    platform_user_id = Column(String)  # User ID on the platform
    platform_username = Column(String)  # Username on the platform
    platform_data = Column(JSON)  # Additional platform-specific data
    
    # Connection status
    is_active = Column(Boolean, default=True)
    last_validated_at = Column(DateTime)
    validation_error = Column(Text)  # Last validation error if any
    
    # Timestamps
    connected_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="platform_connections")

    def __repr__(self):
        return f"<PlatformConnection(id={self.id}, user_id={self.user_id}, platform={self.platform}, is_active={self.is_active})>"


class Post(Base):
    __tablename__ = "posts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=True)
    
    # Post content
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    hashtags = Column(JSON, nullable=False)  # List of hashtags
    images = Column(JSON, nullable=False)  # List of image URLs
    product_data = Column(JSON)  # Additional product data for marketplaces
    
    # Platform targeting
    target_platforms = Column(JSON, nullable=False)  # List of platform names
    platform_specific_content = Column(JSON)  # Platform-specific content variations
    
    # Scheduling
    scheduled_at = Column(DateTime)  # When to publish (null for immediate)
    published_at = Column(DateTime)  # When actually published
    
    # Status and results
    status = Column(String, nullable=False, default="draft")  # draft, scheduled, publishing, published, failed
    results = Column(JSON)  # List of PostResult objects per platform
    
    # Priority and retry
    priority = Column(Integer, default=0)  # Higher number = higher priority
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    last_error = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="posts")
    product = relationship("Product", backref="posts")

    def __repr__(self):
        return f"<Post(id={self.id}, title={self.title}, status={self.status}, user_id={self.user_id})>"


class PostQueue(Base):
    __tablename__ = "post_queue"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id = Column(String, ForeignKey("posts.id"), nullable=False)
    platform = Column(String, nullable=False)  # Platform to post to
    
    # Queue management
    status = Column(String, nullable=False, default="pending")  # pending, processing, completed, failed
    priority = Column(Integer, default=0)  # Higher number = higher priority
    scheduled_at = Column(DateTime, nullable=False)  # When to process this queue item
    
    # Processing tracking
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Results
    result = Column(JSON)  # PostResult object
    error_message = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    post = relationship("Post", backref="queue_items")

    def __repr__(self):
        return f"<PostQueue(id={self.id}, post_id={self.post_id}, platform={self.platform}, status={self.status})>"


class PlatformPreferences(Base):
    __tablename__ = "platform_preferences"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    platform = Column(String, nullable=False)  # Platform enum value
    
    # Basic preferences
    enabled = Column(Boolean, default=True)
    auto_post = Column(Boolean, default=True)
    priority = Column(Integer, default=0)  # Posting priority (0-10)
    
    # Content preferences
    default_template = Column(String)  # Template name for content generation
    content_style = Column(String)  # casual, professional, promotional, storytelling
    hashtag_strategy = Column(String)  # trending, branded, category, mixed
    max_hashtags = Column(Integer)  # Override platform default
    
    # Posting schedule preferences
    posting_schedule = Column(JSON)  # {"monday": ["09:00", "15:00"], "tuesday": [...]}
    timezone = Column(String, default="UTC")
    auto_schedule = Column(Boolean, default=False)
    optimal_times_enabled = Column(Boolean, default=True)
    
    # Platform-specific settings
    platform_settings = Column(JSON)  # Platform-specific configuration
    
    # Content formatting preferences
    title_format = Column(String)  # Template for title formatting
    description_format = Column(String)  # Template for description formatting
    include_branding = Column(Boolean, default=True)
    include_call_to_action = Column(Boolean, default=True)
    
    # Image preferences
    image_optimization = Column(Boolean, default=True)
    watermark_enabled = Column(Boolean, default=False)
    image_filters = Column(JSON)  # {"brightness": 1.1, "contrast": 1.0, ...}
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="platform_preferences")

    def __repr__(self):
        return f"<PlatformPreferences(id={self.id}, user_id={self.user_id}, platform={self.platform}, enabled={self.enabled})>"


class ContentTemplate(Base):
    __tablename__ = "content_templates"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    
    # Template content
    title_template = Column(Text, nullable=False)
    description_template = Column(Text, nullable=False)
    hashtag_template = Column(Text)
    
    # Template settings
    platforms = Column(JSON, nullable=False)  # List of platforms this template applies to
    category = Column(String)  # product_category this template is for
    style = Column(String, nullable=False)  # casual, professional, promotional, storytelling
    
    # Usage tracking
    usage_count = Column(Integer, default=0)
    is_default = Column(Boolean, default=False)
    is_system_template = Column(Boolean, default=False)  # System-provided templates
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="content_templates")

    def __repr__(self):
        return f"<ContentTemplate(id={self.id}, name={self.name}, user_id={self.user_id}, style={self.style})>"


class SaleEvent(Base):
    __tablename__ = "sale_events"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=True)  # Optional - may not be linked to a specific product
    
    # Sale details
    platform = Column(String, nullable=False)  # Platform where the sale occurred
    order_id = Column(String, nullable=False)  # Platform-specific order ID
    amount = Column(DECIMAL(10, 2), nullable=False)  # Sale amount
    currency = Column(String, nullable=False, default="USD")  # Currency code (USD, EUR, INR, etc.)
    
    # Product information (may be different from linked product)
    product_title = Column(String)  # Product title at time of sale
    product_sku = Column(String)  # Product SKU if available
    quantity = Column(Integer, default=1)  # Quantity sold
    
    # Customer information (anonymized)
    customer_location = Column(String)  # City/State/Country
    customer_type = Column(String)  # new, returning, etc.
    
    # Sale metadata
    sale_source = Column(String)  # organic, promoted, referral, etc.
    commission_rate = Column(DECIMAL(5, 4))  # Platform commission rate (0.0000 to 1.0000)
    commission_amount = Column(DECIMAL(10, 2))  # Actual commission paid
    net_amount = Column(DECIMAL(10, 2))  # Amount after commission
    
    # Tracking and attribution
    post_id = Column(String, ForeignKey("posts.id"), nullable=True)  # If sale can be attributed to a specific post
    referral_source = Column(String)  # UTM source or referral information
    campaign_id = Column(String)  # Marketing campaign ID if applicable
    
    # Timestamps
    occurred_at = Column(DateTime, nullable=False)  # When the sale actually occurred
    recorded_at = Column(DateTime, default=func.now())  # When we recorded this sale
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Status and processing
    status = Column(String, nullable=False, default="confirmed")  # confirmed, pending, cancelled, refunded
    sync_status = Column(String, nullable=False, default="synced")  # synced, pending, failed
    platform_data = Column(JSON)  # Raw platform data for debugging
    
    # Relationships
    user = relationship("User", backref="sale_events")
    product = relationship("Product", backref="sale_events")
    post = relationship("Post", backref="sale_events")

    def __repr__(self):
        return f"<SaleEvent(id={self.id}, platform={self.platform}, amount={self.amount}, user_id={self.user_id})>"


class EngagementMetrics(Base):
    __tablename__ = "engagement_metrics"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    post_id = Column(String, ForeignKey("posts.id"), nullable=False)
    platform = Column(String, nullable=False)  # Platform where the metrics were collected
    platform_post_id = Column(String, nullable=False)  # Platform-specific post ID
    
    # Core engagement metrics
    likes = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    views = Column(Integer, default=0)
    reach = Column(Integer, default=0)
    
    # Calculated metrics
    engagement_rate = Column(DECIMAL(5, 2))  # Percentage (0.00 to 100.00)
    click_through_rate = Column(DECIMAL(5, 2))  # Percentage for platforms that support it
    
    # Platform-specific metrics (stored as JSON)
    platform_specific_metrics = Column(JSON)  # Additional platform-specific data
    
    # Collection metadata
    collection_method = Column(String, nullable=False, default="api")  # api, scraping, manual
    data_quality = Column(String, nullable=False, default="complete")  # complete, partial, estimated
    
    # Timestamps
    metrics_date = Column(DateTime, nullable=False)  # Date the metrics represent (for historical data)
    collected_at = Column(DateTime, default=func.now())  # When we collected this data
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Status and processing
    status = Column(String, nullable=False, default="active")  # active, archived, invalid
    sync_status = Column(String, nullable=False, default="synced")  # synced, pending, failed
    
    # Relationships
    user = relationship("User", backref="engagement_metrics")
    post = relationship("Post", backref="engagement_metrics")

    def __repr__(self):
        return f"<EngagementMetrics(id={self.id}, platform={self.platform}, post_id={self.post_id}, likes={self.likes})>"


class MetricsAggregation(Base):
    __tablename__ = "metrics_aggregations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Aggregation parameters
    aggregation_type = Column(String, nullable=False)  # daily, weekly, monthly, platform, product
    aggregation_key = Column(String, nullable=False)  # Date string, platform name, product ID, etc.
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Aggregated metrics
    total_posts = Column(Integer, default=0)
    total_likes = Column(Integer, default=0)
    total_shares = Column(Integer, default=0)
    total_comments = Column(Integer, default=0)
    total_views = Column(Integer, default=0)
    total_reach = Column(Integer, default=0)
    
    # Calculated aggregated metrics
    average_engagement_rate = Column(DECIMAL(5, 2))
    best_performing_post_id = Column(String)
    worst_performing_post_id = Column(String)
    
    # Additional aggregated data
    platforms_included = Column(JSON)  # List of platforms included in aggregation
    products_included = Column(JSON)  # List of product IDs included in aggregation
    aggregation_metadata = Column(JSON)  # Additional metadata about the aggregation
    
    # Timestamps
    calculated_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Status
    status = Column(String, nullable=False, default="current")  # current, outdated, recalculating
    
    # Relationships
    user = relationship("User", backref="metrics_aggregations")

    def __repr__(self):
        return f"<MetricsAggregation(id={self.id}, type={self.aggregation_type}, key={self.aggregation_key}, user_id={self.user_id})>"


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=True)  # Nullable for system actions
    
    # Action details
    action = Column(String, nullable=False)  # data_export, data_deletion, data_access, etc.
    resource_type = Column(String, nullable=False)  # user, product, post, etc.
    resource_id = Column(String, nullable=True)  # ID of the resource being accessed
    
    # Request details
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    request_method = Column(String, nullable=True)  # GET, POST, DELETE, etc.
    request_path = Column(String, nullable=True)
    
    # Action metadata
    details = Column(Text, nullable=True)  # Additional details about the action
    action_metadata = Column(JSON, nullable=True)  # Structured metadata
    
    # Results
    success = Column(Boolean, nullable=False, default=True)
    error_message = Column(Text, nullable=True)
    
    # Data sensitivity
    sensitivity_level = Column(String, nullable=False, default="normal")  # low, normal, high, critical
    
    # Timestamps
    timestamp = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", backref="audit_logs")

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action}, user_id={self.user_id}, timestamp={self.timestamp})>"


class DataDeletionRequest(Base):
    __tablename__ = "data_deletion_requests"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Request details
    deletion_type = Column(String, nullable=False)  # full_deletion, anonymization
    reason = Column(String, nullable=False)  # user_request, account_closure, gdpr_request, etc.
    requested_by = Column(String, nullable=False)  # user_id or 'system' or 'admin'
    
    # Scheduling
    requested_at = Column(DateTime, default=func.now(), nullable=False)
    scheduled_for = Column(DateTime, nullable=False)  # When deletion should occur
    retention_period_days = Column(Integer, nullable=False, default=30)
    
    # Status tracking
    status = Column(String, nullable=False, default="scheduled")  # scheduled, in_progress, completed, failed, cancelled
    
    # Processing details
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Data export (if requested before deletion)
    export_requested = Column(Boolean, default=False)
    export_completed = Column(Boolean, default=False)
    export_download_url = Column(String, nullable=True)
    export_expires_at = Column(DateTime, nullable=True)
    
    # Verification
    verification_token = Column(String, nullable=True)  # For user verification
    verified_at = Column(DateTime, nullable=True)
    
    # Metadata
    request_metadata = Column(JSON, nullable=True)  # Additional request metadata
    
    # Relationships
    user = relationship("User", backref="deletion_requests")

    def __repr__(self):
        return f"<DataDeletionRequest(id={self.id}, user_id={self.user_id}, status={self.status}, scheduled_for={self.scheduled_for})>"