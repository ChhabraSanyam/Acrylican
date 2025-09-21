"""
Snapdeal Platform Integration

Browser automation integration for Snapdeal seller panel.
Handles product listing, inventory management, and order processing.
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


class SnapdealIntegration(BrowserAutomationIntegration):
    """Snapdeal platform integration using browser automation."""
    
    def __init__(self, config: PlatformConfig):
        super().__init__(config)
        self.base_url = "https://seller.snapdeal.com"
        self.login_url = f"{self.base_url}/login"
        self.dashboard_url = f"{self.base_url}/dashboard"
        self.add_product_url = f"{self.base_url}/products/add"
        
        # Snapdeal-specific selectors
        self.selectors = {
            # Login page
            "username_input": 'input[name="username"], input[type="email"], input[placeholder*="email"]',
            "password_input": 'input[name="password"], input[type="password"]',
            "login_button": 'button[type="submit"], .login-btn, button:has-text("Login")',
            "login_error": '.error-message, .alert-danger, .login-error',
            
            # Dashboard
            "dashboard_indicator": '.dashboard, .seller-dashboard, [data-testid="dashboard"]',
            "add_product_link": 'a[href*="add"], .add-product-btn, button:has-text("Add Product")',
            
            # Product form
            "product_name": 'input[name="productName"], input[name="title"], [data-testid="product-name"]',
            "product_description": 'textarea[name="description"], [data-testid="description"]',
            "product_price": 'input[name="price"], input[name="mrp"], [data-testid="price"]',
            "product_category": 'select[name="category"], .category-dropdown, [data-testid="category"]',
            "brand_input": 'input[name="brand"], [data-testid="brand"]',
            "image_upload": 'input[type="file"], [data-testid="image-upload"]',
            "submit_product": 'button[type="submit"], .submit-product, button:has-text("Submit")',
            
            # Success/Error indicators
            "success_message": '.success-message, .alert-success, .product-added-success',
            "error_message": '.error-message, .alert-danger, .form-error',
            
            # Session validation
            "logout_link": 'a[href*="logout"], .logout-link, [data-testid="logout"]',
            "user_profile": '.user-profile, .seller-info, [data-testid="profile"]'
        }
    
    @with_error_handling(Platform.SNAPDEAL, "authenticate")
    async def authenticate(self, credentials: PlatformCredentials) -> bool:
        """Authenticate with Snapdeal using browser automation."""
        if not isinstance(credentials, BrowserCredentials):
            # Convert to BrowserCredentials if needed
            browser_creds = BrowserCredentials(
                username=getattr(credentials, 'username', ''),
                password=getattr(credentials, 'password', ''),
                platform=Platform.SNAPDEAL
            )
        else:
            browser_creds = credentials
        
        automation_service = await get_browser_automation_service()
        success = await automation_service.authenticate_platform(
            Platform.SNAPDEAL,
            getattr(credentials, 'user_id', 'default'),
            browser_creds
        )
        
        if success:
            self.session_active = True
            self.logger.info("Successfully authenticated with Snapdeal")
        else:
            self.logger.error("Failed to authenticate with Snapdeal")
            raise AuthenticationError("Failed to authenticate with Snapdeal", Platform.SNAPDEAL)
        
        return success
    
    async def validate_connection(self) -> bool:
        """Validate that the Snapdeal session is still active."""
        try:
            automation_service = await get_browser_automation_service()
            is_valid = await automation_service.validate_session(
                Platform.SNAPDEAL,
                getattr(self, 'user_id', 'default')
            )
            
            self.session_active = is_valid
            return is_valid
            
        except Exception as e:
            self.logger.error(f"Snapdeal connection validation error: {e}")
            self.session_active = False
            return False
    
    @with_error_handling(Platform.SNAPDEAL, "post_content")
    async def post_content(self, content: PostContent) -> PostResult:
        """Post product content to Snapdeal."""
        # Validate session first
        if not await self.validate_connection():
            return PostResult(
                platform=Platform.SNAPDEAL,
                status=PostStatus.FAILED,
                error_message="Session not valid. Please re-authenticate.",
                error_code="SESSION_INVALID"
            )
        
        # Format content for Snapdeal
        formatted_content = await self.format_content(content)
        
        # Use browser automation service to post
        automation_service = await get_browser_automation_service()
        result = await automation_service.post_content(
            Platform.SNAPDEAL,
            getattr(self, 'user_id', 'default'),
            formatted_content
        )
        
        return result
    
    async def format_content(self, content: PostContent) -> PostContent:
        """Format content according to Snapdeal requirements."""
        try:
            # Snapdeal content formatting rules
            max_title_length = 150
            max_description_length = 3000
            
            # Format title - Snapdeal prefers descriptive titles
            formatted_title = content.title[:max_title_length] if len(content.title) > max_title_length else content.title
            
            # Format description with key features
            description = content.description
            
            # Add key features section if product data is available
            if content.product_data:
                features = []
                if content.product_data.get("brand"):
                    features.append(f"Brand: {content.product_data['brand']}")
                if content.product_data.get("color"):
                    features.append(f"Color: {content.product_data['color']}")
                if content.product_data.get("size"):
                    features.append(f"Size: {content.product_data['size']}")
                if content.product_data.get("material"):
                    features.append(f"Material: {content.product_data['material']}")
                
                if features:
                    description += "\n\nKey Features:\n" + "\n".join([f"• {feature}" for feature in features])
            
            # Add hashtags as keywords
            if content.hashtags:
                keywords = [tag.strip('#') for tag in content.hashtags[:15]]
                description += f"\n\nKeywords: {', '.join(keywords)}"
            
            formatted_description = description[:max_description_length] if len(description) > max_description_length else description
            
            # Create Snapdeal-specific product data
            snapdeal_data = {
                "category": content.product_data.get("category", "Fashion & Accessories") if content.product_data else "Fashion & Accessories",
                "subcategory": content.product_data.get("subcategory", "") if content.product_data else "",
                "brand": content.product_data.get("brand", "Generic") if content.product_data else "Generic",
                "mrp": content.product_data.get("mrp", content.product_data.get("price", 0)) if content.product_data else 0,
                "selling_price": content.product_data.get("price", 0) if content.product_data else 0,
                "stock_quantity": content.product_data.get("stock_quantity", 1) if content.product_data else 1,
                "color": content.product_data.get("color", "") if content.product_data else "",
                "size": content.product_data.get("size", "") if content.product_data else "",
                "weight": content.product_data.get("weight", "") if content.product_data else "",
                "dimensions": content.product_data.get("dimensions", "") if content.product_data else "",
            }
            
            return PostContent(
                title=formatted_title,
                description=formatted_description,
                hashtags=content.hashtags[:15],  # Limit hashtags
                images=content.images[:8],  # Snapdeal allows up to 8 images
                product_data=snapdeal_data,
                platform_specific={
                    "snapdeal_category": snapdeal_data["category"],
                    "snapdeal_subcategory": snapdeal_data["subcategory"],
                    "snapdeal_brand": snapdeal_data["brand"],
                    "snapdeal_mrp": snapdeal_data["mrp"],
                    "snapdeal_selling_price": snapdeal_data["selling_price"]
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error formatting content for Snapdeal: {e}")
            return content  # Return original content if formatting fails
    
    async def get_post_metrics(self, post_id: str) -> Optional[PlatformMetrics]:
        """Get metrics for a Snapdeal product."""
        try:
            # Snapdeal provides basic product performance metrics
            # These would need to be scraped from the seller dashboard
            return PlatformMetrics(
                platform=Platform.SNAPDEAL,
                post_id=post_id,
                views=None,  # Available in seller dashboard
                likes=None,  # Not applicable for marketplace
                shares=None,  # Not applicable for marketplace
                comments=None,  # Customer reviews count could be tracked
                reach=None,  # Not available through automation
                engagement_rate=None,  # Not applicable for marketplace
                retrieved_at=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Error getting Snapdeal metrics: {e}")
            return None
    
    async def disconnect(self) -> bool:
        """Disconnect from Snapdeal by clearing session."""
        try:
            automation_service = await get_browser_automation_service()
            success = await automation_service.disconnect_platform(
                Platform.SNAPDEAL,
                getattr(self, 'user_id', 'default')
            )
            
            self.session_active = False
            return success
            
        except Exception as e:
            self.logger.error(f"Error disconnecting from Snapdeal: {e}")
            return False


# Configuration for Snapdeal integration
SNAPDEAL_CONFIG = PlatformConfig(
    platform=Platform.SNAPDEAL,
    integration_type=IntegrationType.BROWSER_AUTOMATION,
    auth_method=AuthenticationMethod.CREDENTIALS,
    enabled=True,
    
    # URLs
    login_url="https://seller.snapdeal.com/login",
    post_url="https://seller.snapdeal.com/products/add",
    
    # Content limits
    max_title_length=150,
    max_description_length=3000,
    max_hashtags=15,
    supported_image_formats=["jpg", "jpeg", "png", "gif"],
    
    # Retry configuration
    max_retries=3,
    retry_delay_seconds=5,
    
    # Rate limiting (conservative for browser automation)
    rate_limit_per_minute=8,
    
    # Custom settings
    custom_settings={
        "requires_category": True,
        "requires_brand": True,
        "requires_price": True,
        "requires_mrp": True,
        "supports_bulk_upload": True,
        "max_images": 8,
        "session_timeout_hours": 24,
        "supports_variants": True,
        "requires_weight": False,
        "requires_dimensions": False
    }
)