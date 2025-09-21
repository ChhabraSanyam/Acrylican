"""
Platform Integration Framework

This module provides the core architecture for integrating with various social media
and marketplace platforms. It supports both API-based integrations and browser
automation approaches through a unified interface.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pydantic import BaseModel
import asyncio
import logging

logger = logging.getLogger(__name__)


class IntegrationType(str, Enum):
    """Types of platform integration methods"""
    API = "api"
    BROWSER_AUTOMATION = "browser_automation"
    HYBRID = "hybrid"


class Platform(str, Enum):
    """Supported platforms"""
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    FACEBOOK_MARKETPLACE = "facebook_marketplace"
    ETSY = "etsy"
    PINTEREST = "pinterest"
    MEESHO = "meesho"
    SNAPDEAL = "snapdeal"
    INDIAMART = "indiamart"
    SHOPIFY = "shopify"


class PostStatus(str, Enum):
    """Status of a post operation"""
    PENDING = "pending"
    PUBLISHING = "publishing"
    SUCCESS = "success"
    FAILED = "failed"
    RETRY = "retry"


class AuthenticationMethod(str, Enum):
    """Authentication methods for platforms"""
    OAUTH2 = "oauth2"
    OAUTH1 = "oauth1"
    API_KEY = "api_key"
    SESSION_BASED = "session_based"
    CREDENTIALS = "credentials"


class PlatformCredentials(BaseModel):
    """Base model for platform credentials"""
    platform: Platform
    auth_method: AuthenticationMethod
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    expires_at: Optional[datetime] = None
    session_data: Optional[Dict[str, Any]] = None


class PostContent(BaseModel):
    """Content to be posted to platforms"""
    title: str
    description: str
    hashtags: List[str]
    images: List[str]  # URLs to images
    product_data: Optional[Dict[str, Any]] = None
    platform_specific: Optional[Dict[str, Any]] = None


class PostResult(BaseModel):
    """Result of a post operation"""
    platform: Platform
    status: PostStatus
    post_id: Optional[str] = None
    url: Optional[str] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    published_at: Optional[datetime] = None
    retry_count: int = 0
    metadata: Optional[Dict[str, Any]] = None


class PlatformMetrics(BaseModel):
    """Metrics retrieved from a platform"""
    platform: Platform
    post_id: str
    likes: Optional[int] = None
    shares: Optional[int] = None
    comments: Optional[int] = None
    views: Optional[int] = None
    reach: Optional[int] = None
    engagement_rate: Optional[float] = None
    retrieved_at: datetime


class PlatformConfig(BaseModel):
    """Configuration for a platform integration"""
    platform: Platform
    integration_type: IntegrationType
    auth_method: AuthenticationMethod
    enabled: bool = True
    
    # API Configuration
    api_base_url: Optional[str] = None
    api_version: Optional[str] = None
    rate_limit_per_minute: Optional[int] = None
    
    # Browser Automation Configuration
    login_url: Optional[str] = None
    post_url: Optional[str] = None
    selectors: Optional[Dict[str, str]] = None
    
    # Content Formatting
    max_title_length: Optional[int] = None
    max_description_length: Optional[int] = None
    max_hashtags: Optional[int] = None
    supported_image_formats: Optional[List[str]] = None
    
    # Retry Configuration
    max_retries: int = 3
    retry_delay_seconds: int = 5
    
    # Custom settings
    custom_settings: Optional[Dict[str, Any]] = None


class BasePlatformIntegration(ABC):
    """
    Abstract base class for all platform integrations.
    
    This class defines the common interface that all platform integrations
    must implement, regardless of whether they use APIs or browser automation.
    """
    
    def __init__(self, config: PlatformConfig):
        self.config = config
        self.platform = config.platform
        self.integration_type = config.integration_type
        self.logger = logging.getLogger(f"{__name__}.{self.platform.value}")
    
    @abstractmethod
    async def authenticate(self, credentials: PlatformCredentials) -> bool:
        """
        Authenticate with the platform using provided credentials.
        
        Args:
            credentials: Platform-specific authentication credentials
            
        Returns:
            bool: True if authentication successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def validate_connection(self) -> bool:
        """
        Validate that the current connection/authentication is still valid.
        
        Returns:
            bool: True if connection is valid, False otherwise
        """
        pass
    
    @abstractmethod
    async def post_content(self, content: PostContent) -> PostResult:
        """
        Post content to the platform.
        
        Args:
            content: Content to be posted
            
        Returns:
            PostResult: Result of the post operation
        """
        pass
    
    @abstractmethod
    async def get_post_metrics(self, post_id: str) -> Optional[PlatformMetrics]:
        """
        Retrieve metrics for a specific post.
        
        Args:
            post_id: Platform-specific post identifier
            
        Returns:
            PlatformMetrics: Metrics data or None if not available
        """
        pass
    
    @abstractmethod
    async def format_content(self, content: PostContent) -> PostContent:
        """
        Format content according to platform-specific requirements.
        
        Args:
            content: Original content
            
        Returns:
            PostContent: Formatted content for this platform
        """
        pass
    
    async def disconnect(self) -> bool:
        """
        Disconnect from the platform and clean up resources.
        
        Returns:
            bool: True if disconnection successful
        """
        try:
            # Default implementation - can be overridden by subclasses
            self.logger.info(f"Disconnecting from {self.platform.value}")
            return True
        except Exception as e:
            self.logger.error(f"Error disconnecting from {self.platform.value}: {e}")
            return False
    
    def get_platform_info(self) -> Dict[str, Any]:
        """
        Get information about this platform integration.
        
        Returns:
            Dict containing platform information
        """
        return {
            "platform": self.platform.value,
            "integration_type": self.integration_type.value,
            "auth_method": self.config.auth_method.value,
            "enabled": self.config.enabled,
            "max_retries": self.config.max_retries
        }


class APIBasedIntegration(BasePlatformIntegration):
    """
    Base class for API-based platform integrations.
    
    Provides common functionality for platforms that offer REST APIs,
    including OAuth handling, rate limiting, and HTTP client management.
    """
    
    def __init__(self, config: PlatformConfig):
        super().__init__(config)
        self.http_client = None
        self.rate_limiter = None
        self._setup_http_client()
    
    def _setup_http_client(self):
        """Setup HTTP client with appropriate configuration"""
        # This would be implemented with actual HTTP client setup
        # For now, it's a placeholder
        pass
    
    async def _make_api_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make an authenticated API request with rate limiting and error handling.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            **kwargs: Additional request parameters
            
        Returns:
            Dict: API response data
        """
        # This would be implemented with actual HTTP client
        # For now, it's a placeholder
        pass
    
    async def refresh_access_token(self, refresh_token: str) -> Optional[PlatformCredentials]:
        """
        Refresh the access token using the refresh token.
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            Updated credentials or None if refresh failed
        """
        # This would be implemented per platform's OAuth flow
        pass


class BrowserAutomationIntegration(BasePlatformIntegration):
    """
    Base class for browser automation-based platform integrations.
    
    Provides common functionality for platforms that don't offer APIs,
    using browser automation with Playwright.
    """
    
    def __init__(self, config: PlatformConfig):
        super().__init__(config)
        self.browser = None
        self.page = None
        self.session_active = False
    
    async def _setup_browser(self):
        """Setup browser instance for automation"""
        # This would be implemented with Playwright setup
        pass
    
    async def _navigate_to_login(self):
        """Navigate to platform login page"""
        if not self.config.login_url:
            raise ValueError(f"Login URL not configured for {self.platform.value}")
        # Browser navigation implementation
        pass
    
    async def _perform_login(self, credentials: PlatformCredentials):
        """Perform login using browser automation"""
        # Platform-specific login automation
        pass
    
    async def _navigate_to_post_page(self):
        """Navigate to the posting page"""
        if not self.config.post_url:
            raise ValueError(f"Post URL not configured for {self.platform.value}")
        # Browser navigation implementation
        pass
    
    async def cleanup_browser(self):
        """Clean up browser resources"""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            self.session_active = False
        except Exception as e:
            self.logger.error(f"Error cleaning up browser: {e}")


class PlatformIntegrationError(Exception):
    """Base exception for platform integration errors"""
    
    def __init__(self, message: str, platform: Platform, error_code: Optional[str] = None):
        self.platform = platform
        self.error_code = error_code
        super().__init__(message)


class AuthenticationError(PlatformIntegrationError):
    """Raised when authentication fails"""
    pass


class PostingError(PlatformIntegrationError):
    """Raised when posting content fails"""
    pass


class RateLimitError(PlatformIntegrationError):
    """Raised when rate limit is exceeded"""
    pass


class ConfigurationError(PlatformIntegrationError):
    """Raised when platform configuration is invalid"""
    pass