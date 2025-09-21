"""
Meesho Platform Integration

Browser automation integration for Meesho seller dashboard.
Handles product listing, inventory management, and order tracking.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from .platform_integration import (
    BrowserAutomationIntegration,
    Platform,
    PostContent,
    PostResult,
    PostStatus,
    PlatformCredentials,
    PlatformMetrics,
    AuthenticationError,
    PostingError,
    PlatformConfig,
    IntegrationType,
    AuthenticationMethod
)
from .browser_automation import BrowserCredentials, get_browser_automation_service
from .browser_error_handling import (
    with_error_handling,
    get_retry_manager,
    get_circuit_breaker,
    get_error_reporter
)

logger = logging.getLogger(__name__)


class MeeshoIntegration(BrowserAutomationIntegration):
    """Meesho platform integration using browser automation."""
    
    def __init__(self, config: PlatformConfig):
        super().__init__(config)
        self.base_url = "https://supplier.meesho.com"
        self.login_url = f"{self.base_url}/login"
        self.dashboard_url = f"{self.base_url}/dashboard"
        self.add_product_url = f"{self.base_url}/products/add"
        
        # Meesho-specific selectors
        self.selectors = {
            # Login page
            "email_input": 'input[type="email"], input[name="email"], input[placeholder*="email"]',
            "password_input": 'input[type="password"], input[name="password"]',
            "login_button": 'button[type="submit"], .login-button, button:has-text("Login")',
            "login_error": '.error-message, .alert-danger, .error-text',
            
            # Dashboard
            "dashboard_indicator": '.dashboard, [data-testid="dashboard"], .supplier-dashboard',
            "add_product_button": '.add-product, button:has-text("Add Product"), [data-testid="add-product"]',
            
            # Product form
            "product_title": 'input[name="title"], input[name="product_name"], [data-testid="product-title"]',
            "product_description": 'textarea[name="description"], [data-testid="product-description"]',
            "product_price": 'input[name="price"], input[name="selling_price"], [data-testid="price"]',
            "product_category": '.category-dropdown, select[name="category"], [data-testid="category"]',
            "image_upload": 'input[type="file"], [data-testid="image-upload"]',
            "submit_button": 'button[type="submit"], .submit-button, button:has-text("Submit")',
            
            # Success/Error indicators
            "success_message": '.success-message, .alert-success, .success-text',
            "error_message": '.error-message, .alert-danger, .error-text',
            
            # Session validation
            "logout_button": 'a[href*="logout"], button:has-text("Logout"), [data-testid="logout"]',
            "profile_menu": '.profile-menu, .user-menu, [data-testid="profile"]'
        }
    
    @with_error_handling(Platform.MEESHO, "authenticate")
    async def authenticate(self, credentials: PlatformCredentials) -> bool:
        """Authenticate with Meesho using browser automation."""
        if not isinstance(credentials, BrowserCredentials):
            # Convert to BrowserCredentials if needed
            browser_creds = BrowserCredentials(
                username=getattr(credentials, 'username', ''),
                password=getattr(credentials, 'password', ''),
                platform=Platform.MEESHO
            )
        else:
            browser_creds = credentials
        
        automation_service = await get_browser_automation_service()
        success = await automation_service.authenticate_platform(
            Platform.MEESHO,
            getattr(credentials, 'user_id', 'default'),
            browser_creds
        )
        
        if success:
            self.session_active = True
            self.logger.info("Successfully authenticated with Meesho")
        else:
            self.logger.error("Failed to authenticate with Meesho")
            raise AuthenticationError("Failed to authenticate with Meesho", Platform.MEESHO)
        
        return success
    
    async def validate_connection(self) -> bool:
        """Validate that the Meesho session is still active."""
        try:
            automation_service = await get_browser_automation_service()
            is_valid = await automation_service.validate_session(
                Platform.MEESHO,
                getattr(self, 'user_id', 'default')
            )
            
            self.session_active = is_valid
            return is_valid
            
        except Exception as e:
            self.logger.error(f"Meesho connection validation error: {e}")
            self.session_active = False
            return False
    
    @with_error_handling(Platform.MEESHO, "post_content")
    async def post_content(self, content: PostContent) -> PostResult:
        """Post product content to Meesho."""
        # Validate session first
        if not await self.validate_connection():
            return PostResult(
                platform=Platform.MEESHO,
                status=PostStatus.FAILED,
                error_message="Session not valid. Please re-authenticate.",
                error_code="SESSION_INVALID"
            )
        
        # Format content for Meesho
        formatted_content = await self.format_content(content)
        
        # Use browser automation service to post
        automation_service = await get_browser_automation_service()
        result = await automation_service.post_content(
            Platform.MEESHO,
            getattr(self, 'user_id', 'default'),
            formatted_content
        )
        
        return result
    
    async def format_content(self, content: PostContent) -> PostContent:
        """Format content according to Meesho requirements."""
        try:
            # Meesho content formatting rules
            max_title_length = 100
            max_description_length = 2000
            
            # Format title
            formatted_title = content.title[:max_title_length] if len(content.title) > max_title_length else content.title
            
            # Format description
            description = content.description
            if content.hashtags:
                # Add hashtags to description for Meesho
                hashtag_text = " ".join([f"#{tag.strip('#')}" for tag in content.hashtags[:10]])
                description = f"{description}\n\n{hashtag_text}"
            
            formatted_description = description[:max_description_length] if len(description) > max_description_length else description
            
            # Create Meesho-specific product data
            meesho_data = {
                "category": content.product_data.get("category", "Fashion") if content.product_data else "Fashion",
                "price": content.product_data.get("price", 0) if content.product_data else 0,
                "discount": content.product_data.get("discount", 0) if content.product_data else 0,
                "stock_quantity": content.product_data.get("stock_quantity", 1) if content.product_data else 1,
                "brand": content.product_data.get("brand", "") if content.product_data else "",
                "color": content.product_data.get("color", "") if content.product_data else "",
                "size": content.product_data.get("size", "") if content.product_data else "",
            }
            
            return PostContent(
                title=formatted_title,
                description=formatted_description,
                hashtags=content.hashtags[:10],  # Limit hashtags
                images=content.images[:5],  # Limit to 5 images
                product_data=meesho_data,
                platform_specific={
                    "meesho_category": meesho_data["category"],
                    "meesho_price": meesho_data["price"],
                    "meesho_discount": meesho_data["discount"]
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error formatting content for Meesho: {e}")
            return content  # Return original content if formatting fails
    
    async def get_post_metrics(self, post_id: str) -> Optional[PlatformMetrics]:
        """Get metrics for a Meesho post/product."""
        try:
            # Meesho doesn't provide detailed engagement metrics like social platforms
            # But we can track basic product performance
            return PlatformMetrics(
                platform=Platform.MEESHO,
                post_id=post_id,
                views=None,  # Not available through automation
                likes=None,  # Not applicable for marketplace
                shares=None,  # Not applicable for marketplace
                comments=None,  # Not applicable for marketplace
                reach=None,  # Not available through automation
                engagement_rate=None,  # Not applicable for marketplace
                retrieved_at=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Error getting Meesho metrics: {e}")
            return None
    
    async def disconnect(self) -> bool:
        """Disconnect from Meesho by clearing session."""
        try:
            automation_service = await get_browser_automation_service()
            success = await automation_service.disconnect_platform(
                Platform.MEESHO,
                getattr(self, 'user_id', 'default')
            )
            
            self.session_active = False
            return success
            
        except Exception as e:
            self.logger.error(f"Error disconnecting from Meesho: {e}")
            return False


# Configuration for Meesho integration
MEESHO_CONFIG = PlatformConfig(
    platform=Platform.MEESHO,
    integration_type=IntegrationType.BROWSER_AUTOMATION,
    auth_method=AuthenticationMethod.CREDENTIALS,
    enabled=True,
    
    # URLs
    login_url="https://supplier.meesho.com/login",
    post_url="https://supplier.meesho.com/products/add",
    
    # Content limits
    max_title_length=100,
    max_description_length=2000,
    max_hashtags=10,
    supported_image_formats=["jpg", "jpeg", "png", "webp"],
    
    # Retry configuration
    max_retries=3,
    retry_delay_seconds=5,
    
    # Rate limiting (conservative for browser automation)
    rate_limit_per_minute=10,
    
    # Custom settings
    custom_settings={
        "requires_category": True,
        "requires_price": True,
        "supports_bulk_upload": False,
        "max_images": 5,
        "session_timeout_hours": 24
    }
)