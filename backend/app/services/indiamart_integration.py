"""
IndiaMART Platform Integration

Browser automation integration for IndiaMART seller account.
Handles product catalog management, inquiry responses, and business profile updates.
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


class IndiaMARTIntegration(BrowserAutomationIntegration):
    """IndiaMART platform integration using browser automation."""
    
    def __init__(self, config: PlatformConfig):
        super().__init__(config)
        self.base_url = "https://seller.indiamart.com"
        self.login_url = "https://my.indiamart.com/login"
        self.dashboard_url = "https://my.indiamart.com/dashboard"
        self.add_product_url = "https://my.indiamart.com/products/add"
        
        # IndiaMART-specific selectors
        self.selectors = {
            # Login page
            "email_input": 'input[name="email"], input[type="email"], input[placeholder*="email"]',
            "password_input": 'input[name="password"], input[type="password"]',
            "login_button": 'input[type="submit"], .login-button, button:has-text("Login")',
            "login_error": '.error-message, .alert-danger, .login-error',
            
            # Dashboard
            "dashboard_indicator": '.dashboard, .my-indiamart, [data-testid="dashboard"]',
            "add_product_link": 'a[href*="add"], .add-product, button:has-text("Add Product")',
            "product_catalog": '.product-catalog, .my-products, [data-testid="products"]',
            
            # Product form
            "product_name": 'input[name="product_name"], input[name="title"], [data-testid="product-name"]',
            "product_description": 'textarea[name="product_description"], textarea[name="description"]',
            "product_price": 'input[name="price"], input[name="unit_price"], [data-testid="price"]',
            "product_category": 'select[name="category"], .category-select, [data-testid="category"]',
            "product_unit": 'select[name="unit"], .unit-select, [data-testid="unit"]',
            "minimum_order": 'input[name="minimum_order"], [data-testid="min-order"]',
            "image_upload": 'input[type="file"], [data-testid="image-upload"]',
            "submit_button": 'input[type="submit"], .add-product-btn, button:has-text("Add Product")',
            
            # Success/Error indicators
            "success_message": '.success-msg, .alert-success, .product-added',
            "error_message": '.error-msg, .alert-danger, .form-error',
            
            # Session validation
            "logout_link": 'a[href*="logout"], .logout, [data-testid="logout"]',
            "user_menu": '.user-menu, .profile-menu, [data-testid="user-menu"]'
        }
    
    @with_error_handling(Platform.INDIAMART, "authenticate")
    async def authenticate(self, credentials: PlatformCredentials) -> bool:
        """Authenticate with IndiaMART using browser automation."""
        if not isinstance(credentials, BrowserCredentials):
            # Convert to BrowserCredentials if needed
            browser_creds = BrowserCredentials(
                username=getattr(credentials, 'username', ''),
                password=getattr(credentials, 'password', ''),
                platform=Platform.INDIAMART
            )
        else:
            browser_creds = credentials
        
        automation_service = await get_browser_automation_service()
        success = await automation_service.authenticate_platform(
            Platform.INDIAMART,
            getattr(credentials, 'user_id', 'default'),
            browser_creds
        )
        
        if success:
            self.session_active = True
            self.logger.info("Successfully authenticated with IndiaMART")
        else:
            self.logger.error("Failed to authenticate with IndiaMART")
            raise AuthenticationError("Failed to authenticate with IndiaMART", Platform.INDIAMART)
        
        return success
    
    async def validate_connection(self) -> bool:
        """Validate that the IndiaMART session is still active."""
        try:
            automation_service = await get_browser_automation_service()
            is_valid = await automation_service.validate_session(
                Platform.INDIAMART,
                getattr(self, 'user_id', 'default')
            )
            
            self.session_active = is_valid
            return is_valid
            
        except Exception as e:
            self.logger.error(f"IndiaMART connection validation error: {e}")
            self.session_active = False
            return False
    
    @with_error_handling(Platform.INDIAMART, "post_content")
    async def post_content(self, content: PostContent) -> PostResult:
        """Post product content to IndiaMART."""
        # Validate session first
        if not await self.validate_connection():
            return PostResult(
                platform=Platform.INDIAMART,
                status=PostStatus.FAILED,
                error_message="Session not valid. Please re-authenticate.",
                error_code="SESSION_INVALID"
            )
        
        # Format content for IndiaMART
        formatted_content = await self.format_content(content)
        
        # Use browser automation service to post
        automation_service = await get_browser_automation_service()
        result = await automation_service.post_content(
            Platform.INDIAMART,
            getattr(self, 'user_id', 'default'),
            formatted_content
        )
        
        return result
    
    async def format_content(self, content: PostContent) -> PostContent:
        """Format content according to IndiaMART requirements."""
        try:
            # IndiaMART content formatting rules
            max_title_length = 200
            max_description_length = 5000
            
            # Format title - IndiaMART prefers business-focused titles
            formatted_title = content.title[:max_title_length] if len(content.title) > max_title_length else content.title
            
            # Format description with business details
            description = content.description
            
            # Add business-focused information
            if content.product_data:
                business_info = []
                
                # Add specifications
                if content.product_data.get("specifications"):
                    business_info.append("Specifications:")
                    for spec, value in content.product_data["specifications"].items():
                        business_info.append(f"• {spec}: {value}")
                
                # Add business terms
                if content.product_data.get("minimum_order"):
                    business_info.append(f"Minimum Order Quantity: {content.product_data['minimum_order']}")
                
                if content.product_data.get("payment_terms"):
                    business_info.append(f"Payment Terms: {content.product_data['payment_terms']}")
                
                if content.product_data.get("delivery_time"):
                    business_info.append(f"Delivery Time: {content.product_data['delivery_time']}")
                
                if business_info:
                    description += "\n\n" + "\n".join(business_info)
            
            # Add contact information encouragement
            description += "\n\nFor bulk orders and business inquiries, please contact us for competitive pricing and customization options."
            
            formatted_description = description[:max_description_length] if len(description) > max_description_length else description
            
            # Create IndiaMART-specific product data
            indiamart_data = {
                "category": content.product_data.get("category", "Industrial Supplies") if content.product_data else "Industrial Supplies",
                "subcategory": content.product_data.get("subcategory", "") if content.product_data else "",
                "price": content.product_data.get("price", 0) if content.product_data else 0,
                "unit": content.product_data.get("unit", "Piece") if content.product_data else "Piece",
                "minimum_order": content.product_data.get("minimum_order", 1) if content.product_data else 1,
                "brand": content.product_data.get("brand", "") if content.product_data else "",
                "model": content.product_data.get("model", "") if content.product_data else "",
                "material": content.product_data.get("material", "") if content.product_data else "",
                "color": content.product_data.get("color", "") if content.product_data else "",
                "size": content.product_data.get("size", "") if content.product_data else "",
                "weight": content.product_data.get("weight", "") if content.product_data else "",
                "country_of_origin": content.product_data.get("country_of_origin", "India") if content.product_data else "India",
                "payment_terms": content.product_data.get("payment_terms", "Advance Payment") if content.product_data else "Advance Payment",
                "delivery_time": content.product_data.get("delivery_time", "7-15 days") if content.product_data else "7-15 days",
            }
            
            return PostContent(
                title=formatted_title,
                description=formatted_description,
                hashtags=content.hashtags[:20],  # IndiaMART allows more keywords
                images=content.images[:10],  # IndiaMART allows up to 10 images
                product_data=indiamart_data,
                platform_specific={
                    "indiamart_category": indiamart_data["category"],
                    "indiamart_unit": indiamart_data["unit"],
                    "indiamart_minimum_order": indiamart_data["minimum_order"],
                    "indiamart_payment_terms": indiamart_data["payment_terms"],
                    "indiamart_delivery_time": indiamart_data["delivery_time"]
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error formatting content for IndiaMART: {e}")
            return content  # Return original content if formatting fails
    
    async def get_post_metrics(self, post_id: str) -> Optional[PlatformMetrics]:
        """Get metrics for an IndiaMART product."""
        try:
            # IndiaMART provides business-focused metrics
            # These would need to be scraped from the seller dashboard
            return PlatformMetrics(
                platform=Platform.INDIAMART,
                post_id=post_id,
                views=None,  # Product views available in dashboard
                likes=None,  # Not applicable for B2B platform
                shares=None,  # Not applicable for B2B platform
                comments=None,  # Inquiry count could be tracked
                reach=None,  # Not available through automation
                engagement_rate=None,  # Inquiry-to-view ratio could be calculated
                retrieved_at=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Error getting IndiaMART metrics: {e}")
            return None
    
    async def disconnect(self) -> bool:
        """Disconnect from IndiaMART by clearing session."""
        try:
            automation_service = await get_browser_automation_service()
            success = await automation_service.disconnect_platform(
                Platform.INDIAMART,
                getattr(self, 'user_id', 'default')
            )
            
            self.session_active = False
            return success
            
        except Exception as e:
            self.logger.error(f"Error disconnecting from IndiaMART: {e}")
            return False


# Configuration for IndiaMART integration
INDIAMART_CONFIG = PlatformConfig(
    platform=Platform.INDIAMART,
    integration_type=IntegrationType.BROWSER_AUTOMATION,
    auth_method=AuthenticationMethod.CREDENTIALS,
    enabled=True,
    
    # URLs
    login_url="https://my.indiamart.com/login",
    post_url="https://my.indiamart.com/products/add",
    
    # Content limits
    max_title_length=200,
    max_description_length=5000,
    max_hashtags=20,
    supported_image_formats=["jpg", "jpeg", "png", "gif"],
    
    # Retry configuration
    max_retries=3,
    retry_delay_seconds=5,
    
    # Rate limiting (conservative for browser automation)
    rate_limit_per_minute=6,
    
    # Custom settings
    custom_settings={
        "requires_category": True,
        "requires_price": True,
        "requires_unit": True,
        "requires_minimum_order": True,
        "supports_bulk_upload": True,
        "max_images": 10,
        "session_timeout_hours": 24,
        "supports_specifications": True,
        "supports_business_terms": True,
        "b2b_focused": True,
        "supports_inquiries": True
    }
)