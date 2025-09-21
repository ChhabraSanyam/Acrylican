"""
Platform-Specific OAuth Integrations

This module contains concrete implementations of OAuth integrations for
each supported platform, extending the base OAuth functionality with
platform-specific features and API calls.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
import httpx
from sqlalchemy.orm import Session

from .oauth_service import OAuthService
from .platform_integration import (
    APIBasedIntegration, 
    Platform, 
    PlatformConfig, 
    PostContent, 
    PostResult, 
    PostStatus,
    PlatformMetrics,
    PlatformCredentials,
    AuthenticationMethod,
    IntegrationType
)
from .facebook_instagram_integration import (
    FacebookIntegration,
    InstagramIntegration,
    create_facebook_integration,
    create_instagram_integration
)
from ..models import PlatformConnection
import logging

logger = logging.getLogger(__name__)


class FacebookOAuthIntegration(APIBasedIntegration):
    """Facebook OAuth integration with Graph API"""
    
    def __init__(self, oauth_service: OAuthService, connection: PlatformConnection):
        config = PlatformConfig(
            platform=Platform.FACEBOOK,
            integration_type=IntegrationType.API,
            auth_method=AuthenticationMethod.OAUTH2,
            api_base_url="https://graph.facebook.com/v18.0",
            max_title_length=2200,
            max_description_length=63206,
            max_hashtags=30,
            supported_image_formats=["jpg", "jpeg", "png", "gif", "webp"]
        )
        super().__init__(config)
        self.oauth_service = oauth_service
        self.connection = connection
        self._credentials = None
    
    async def authenticate(self, credentials: PlatformCredentials) -> bool:
        """Facebook authentication is handled by OAuth service"""
        self._credentials = credentials
        return True
    
    async def validate_connection(self) -> bool:
        """Validate Facebook connection"""
        if not self.connection:
            return False
        
        try:
            credentials = self.oauth_service.get_decrypted_credentials(self.connection)
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.api_base_url}/me",
                    headers={"Authorization": f"Bearer {credentials.access_token}"},
                    params={"fields": "id,name"}
                )
                
                return response.status_code == 200
                
        except Exception as e:
            self.logger.error(f"Facebook connection validation failed: {e}")
            return False
    
    async def post_content(self, content: PostContent) -> PostResult:
        """Post content to Facebook"""
        try:
            credentials = self.oauth_service.get_decrypted_credentials(self.connection)
            
            # Get user's pages
            async with httpx.AsyncClient() as client:
                pages_response = await client.get(
                    f"{self.config.api_base_url}/me/accounts",
                    headers={"Authorization": f"Bearer {credentials.access_token}"}
                )
                
                if pages_response.status_code != 200:
                    return PostResult(
                        platform=self.platform,
                        status=PostStatus.FAILED,
                        error_message="Failed to get Facebook pages",
                        error_code="PAGES_ACCESS_FAILED"
                    )
                
                pages_data = pages_response.json()
                pages = pages_data.get("data", [])
                
                if not pages:
                    return PostResult(
                        platform=self.platform,
                        status=PostStatus.FAILED,
                        error_message="No Facebook pages found",
                        error_code="NO_PAGES_FOUND"
                    )
                
                # Use the first page for posting
                page = pages[0]
                page_access_token = page["access_token"]
                page_id = page["id"]
                
                # Prepare post data
                post_data = {
                    "message": f"{content.title}\n\n{content.description}\n\n{' '.join(content.hashtags)}",
                    "access_token": page_access_token
                }
                
                # Add images if provided
                if content.images:
                    # For multiple images, create a photo album
                    if len(content.images) > 1:
                        # Create album first
                        album_data = {
                            "name": content.title,
                            "message": content.description,
                            "access_token": page_access_token
                        }
                        
                        album_response = await client.post(
                            f"{self.config.api_base_url}/{page_id}/albums",
                            data=album_data
                        )
                        
                        if album_response.status_code == 200:
                            album_id = album_response.json()["id"]
                            
                            # Upload photos to album
                            for image_url in content.images:
                                photo_data = {
                                    "url": image_url,
                                    "access_token": page_access_token
                                }
                                
                                await client.post(
                                    f"{self.config.api_base_url}/{album_id}/photos",
                                    data=photo_data
                                )
                    else:
                        # Single image post
                        post_data["link"] = content.images[0]
                
                # Create the post
                response = await client.post(
                    f"{self.config.api_base_url}/{page_id}/feed",
                    data=post_data
                )
                
                if response.status_code == 200:
                    result_data = response.json()
                    return PostResult(
                        platform=self.platform,
                        status=PostStatus.SUCCESS,
                        post_id=result_data.get("id"),
                        published_at=datetime.utcnow()
                    )
                else:
                    return PostResult(
                        platform=self.platform,
                        status=PostStatus.FAILED,
                        error_message=f"Facebook API error: {response.text}",
                        error_code="API_ERROR"
                    )
                    
        except Exception as e:
            self.logger.error(f"Facebook posting failed: {e}")
            return PostResult(
                platform=self.platform,
                status=PostStatus.FAILED,
                error_message=str(e),
                error_code="POSTING_EXCEPTION"
            )
    
    async def get_post_metrics(self, post_id: str) -> Optional[PlatformMetrics]:
        """Get Facebook post metrics"""
        try:
            credentials = self.oauth_service.get_decrypted_credentials(self.connection)
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.api_base_url}/{post_id}",
                    headers={"Authorization": f"Bearer {credentials.access_token}"},
                    params={
                        "fields": "likes.summary(true),comments.summary(true),shares"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    return PlatformMetrics(
                        platform=self.platform,
                        post_id=post_id,
                        likes=data.get("likes", {}).get("summary", {}).get("total_count", 0),
                        comments=data.get("comments", {}).get("summary", {}).get("total_count", 0),
                        shares=data.get("shares", {}).get("count", 0),
                        retrieved_at=datetime.utcnow()
                    )
                    
        except Exception as e:
            self.logger.error(f"Facebook metrics retrieval failed: {e}")
            
        return None
    
    async def format_content(self, content: PostContent) -> PostContent:
        """Format content for Facebook"""
        # Facebook allows long content, minimal formatting needed
        formatted_content = content.copy()
        
        # Ensure hashtags are properly formatted
        formatted_hashtags = []
        for tag in content.hashtags:
            if not tag.startswith("#"):
                tag = f"#{tag}"
            formatted_hashtags.append(tag)
        
        formatted_content.hashtags = formatted_hashtags
        return formatted_content


class InstagramOAuthIntegration(APIBasedIntegration):
    """Instagram OAuth integration with Graph API"""
    
    def __init__(self, oauth_service: OAuthService, connection: PlatformConnection):
        config = PlatformConfig(
            platform=Platform.INSTAGRAM,
            integration_type=IntegrationType.API,
            auth_method=AuthenticationMethod.OAUTH2,
            api_base_url="https://graph.facebook.com/v18.0",
            max_title_length=2200,
            max_description_length=2200,
            max_hashtags=30,
            supported_image_formats=["jpg", "jpeg", "png"]
        )
        super().__init__(config)
        self.oauth_service = oauth_service
        self.connection = connection
    
    async def authenticate(self, credentials: PlatformCredentials) -> bool:
        """Instagram authentication is handled by OAuth service"""
        return True
    
    async def validate_connection(self) -> bool:
        """Validate Instagram connection"""
        if not self.connection:
            return False
        
        try:
            credentials = self.oauth_service.get_decrypted_credentials(self.connection)
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.api_base_url}/me/accounts",
                    headers={"Authorization": f"Bearer {credentials.access_token}"},
                    params={"fields": "instagram_business_account"}
                )
                
                return response.status_code == 200
                
        except Exception as e:
            self.logger.error(f"Instagram connection validation failed: {e}")
            return False
    
    async def post_content(self, content: PostContent) -> PostResult:
        """Post content to Instagram"""
        try:
            credentials = self.oauth_service.get_decrypted_credentials(self.connection)
            
            async with httpx.AsyncClient() as client:
                # Get Instagram Business Account
                pages_response = await client.get(
                    f"{self.config.api_base_url}/me/accounts",
                    headers={"Authorization": f"Bearer {credentials.access_token}"},
                    params={"fields": "instagram_business_account"}
                )
                
                if pages_response.status_code != 200:
                    return PostResult(
                        platform=self.platform,
                        status=PostStatus.FAILED,
                        error_message="Failed to get Instagram business account",
                        error_code="ACCOUNT_ACCESS_FAILED"
                    )
                
                pages_data = pages_response.json()
                instagram_account = None
                
                for page in pages_data.get("data", []):
                    if "instagram_business_account" in page:
                        instagram_account = page["instagram_business_account"]["id"]
                        break
                
                if not instagram_account:
                    return PostResult(
                        platform=self.platform,
                        status=PostStatus.FAILED,
                        error_message="No Instagram business account found",
                        error_code="NO_INSTAGRAM_ACCOUNT"
                    )
                
                # Create media container
                caption = f"{content.title}\n\n{content.description}\n\n{' '.join(content.hashtags)}"
                
                container_data = {
                    "image_url": content.images[0] if content.images else None,
                    "caption": caption,
                    "access_token": credentials.access_token
                }
                
                if not container_data["image_url"]:
                    return PostResult(
                        platform=self.platform,
                        status=PostStatus.FAILED,
                        error_message="Instagram requires at least one image",
                        error_code="NO_IMAGE_PROVIDED"
                    )
                
                container_response = await client.post(
                    f"{self.config.api_base_url}/{instagram_account}/media",
                    data=container_data
                )
                
                if container_response.status_code != 200:
                    return PostResult(
                        platform=self.platform,
                        status=PostStatus.FAILED,
                        error_message=f"Failed to create media container: {container_response.text}",
                        error_code="CONTAINER_CREATION_FAILED"
                    )
                
                container_id = container_response.json()["id"]
                
                # Publish the media
                publish_data = {
                    "creation_id": container_id,
                    "access_token": credentials.access_token
                }
                
                publish_response = await client.post(
                    f"{self.config.api_base_url}/{instagram_account}/media_publish",
                    data=publish_data
                )
                
                if publish_response.status_code == 200:
                    result_data = publish_response.json()
                    return PostResult(
                        platform=self.platform,
                        status=PostStatus.SUCCESS,
                        post_id=result_data.get("id"),
                        published_at=datetime.utcnow()
                    )
                else:
                    return PostResult(
                        platform=self.platform,
                        status=PostStatus.FAILED,
                        error_message=f"Instagram publish failed: {publish_response.text}",
                        error_code="PUBLISH_FAILED"
                    )
                    
        except Exception as e:
            self.logger.error(f"Instagram posting failed: {e}")
            return PostResult(
                platform=self.platform,
                status=PostStatus.FAILED,
                error_message=str(e),
                error_code="POSTING_EXCEPTION"
            )
    
    async def get_post_metrics(self, post_id: str) -> Optional[PlatformMetrics]:
        """Get Instagram post metrics"""
        try:
            credentials = self.oauth_service.get_decrypted_credentials(self.connection)
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.api_base_url}/{post_id}/insights",
                    headers={"Authorization": f"Bearer {credentials.access_token}"},
                    params={
                        "metric": "likes,comments,shares,reach,impressions"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    metrics_data = {}
                    
                    for metric in data.get("data", []):
                        metrics_data[metric["name"]] = metric["values"][0]["value"]
                    
                    return PlatformMetrics(
                        platform=self.platform,
                        post_id=post_id,
                        likes=metrics_data.get("likes", 0),
                        comments=metrics_data.get("comments", 0),
                        shares=metrics_data.get("shares", 0),
                        reach=metrics_data.get("reach", 0),
                        views=metrics_data.get("impressions", 0),
                        retrieved_at=datetime.utcnow()
                    )
                    
        except Exception as e:
            self.logger.error(f"Instagram metrics retrieval failed: {e}")
            
        return None
    
    async def format_content(self, content: PostContent) -> PostContent:
        """Format content for Instagram"""
        formatted_content = content.copy()
        
        # Instagram has character limits
        if len(formatted_content.description) > 2200:
            formatted_content.description = formatted_content.description[:2197] + "..."
        
        # Format hashtags
        formatted_hashtags = []
        for tag in content.hashtags[:30]:  # Instagram allows up to 30 hashtags
            if not tag.startswith("#"):
                tag = f"#{tag}"
            formatted_hashtags.append(tag)
        
        formatted_content.hashtags = formatted_hashtags
        return formatted_content


class EtsyOAuthIntegration(APIBasedIntegration):
    """
    Etsy OAuth integration with comprehensive marketplace functionality.
    
    This class provides a wrapper around the full EtsyIntegration to maintain
    compatibility with the existing platform integration framework while
    providing access to enhanced Etsy-specific features.
    """
    
    def __init__(self, oauth_service: OAuthService, connection: PlatformConnection):
        config = PlatformConfig(
            platform=Platform.ETSY,
            integration_type=IntegrationType.API,
            auth_method=AuthenticationMethod.OAUTH2,
            api_base_url="https://openapi.etsy.com/v3",
            max_title_length=140,
            max_description_length=13000,
            max_hashtags=13,
            supported_image_formats=["jpg", "jpeg", "png", "gif", "webp"],
            rate_limit_per_minute=100,
            max_retries=3
        )
        super().__init__(config)
        self.oauth_service = oauth_service
        self.connection = connection
        
        # Import and initialize the comprehensive Etsy integration
        from .etsy_integration import EtsyIntegration
        self._etsy_integration = EtsyIntegration(oauth_service, connection)
    
    async def authenticate(self, credentials: PlatformCredentials) -> bool:
        """Authenticate with Etsy using OAuth 2.0"""
        return await self._etsy_integration.authenticate(credentials)
    
    async def validate_connection(self) -> bool:
        """Validate Etsy connection"""
        return await self._etsy_integration.validate_connection()
    
    async def post_content(self, content: PostContent) -> PostResult:
        """Create Etsy listing with comprehensive functionality"""
        return await self._etsy_integration.post_content(content)
    
    async def get_post_metrics(self, post_id: str) -> Optional[PlatformMetrics]:
        """Get Etsy listing metrics"""
        return await self._etsy_integration.get_post_metrics(post_id)
    
    async def format_content(self, content: PostContent) -> PostContent:
        """Format content for Etsy"""
        return await self._etsy_integration.format_content(content)
    
    # Additional Etsy-specific methods
    async def update_listing(
        self,
        listing_id: str,
        content: PostContent,
        price: Optional[float] = None,
        quantity: Optional[int] = None
    ) -> PostResult:
        """Update an existing Etsy listing"""
        from decimal import Decimal
        price_decimal = Decimal(str(price)) if price is not None else None
        return await self._etsy_integration.update_listing(listing_id, content, price_decimal, quantity)
    
    async def get_shop_listings(
        self,
        state: str = "active",
        limit: int = 25,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get listings from the connected Etsy shop"""
        listings = await self._etsy_integration.get_shop_listings(state, limit, offset)
        return [listing.__dict__ for listing in listings]
    
    async def sync_inventory(self, listings_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Synchronize inventory data with Etsy listings"""
        return await self._etsy_integration.sync_inventory(listings_data)


class PinterestOAuthIntegration(APIBasedIntegration):
    """
    Pinterest OAuth integration with comprehensive marketplace functionality.
    
    This class provides a wrapper around the full PinterestIntegration to maintain
    compatibility with the existing platform integration framework while
    providing access to enhanced Pinterest-specific features.
    """
    
    def __init__(self, oauth_service: OAuthService, connection: PlatformConnection):
        config = PlatformConfig(
            platform=Platform.PINTEREST,
            integration_type=IntegrationType.API,
            auth_method=AuthenticationMethod.OAUTH2,
            api_base_url="https://api.pinterest.com/v5",
            max_title_length=100,
            max_description_length=500,
            max_hashtags=20,
            supported_image_formats=["jpg", "jpeg", "png", "gif", "webp"],
            rate_limit_per_minute=1000,
            max_retries=3,
            custom_settings={
                "supports_rich_pins": True,
                "supports_video": True,
                "supports_story_pins": True,
                "min_image_width": 236,
                "min_image_height": 236,
                "max_image_size_mb": 32
            }
        )
        super().__init__(config)
        self.oauth_service = oauth_service
        self.connection = connection
        
        # Import and initialize the comprehensive Pinterest integration
        from .pinterest_integration import PinterestIntegration
        self._pinterest_integration = PinterestIntegration(oauth_service, connection)
    
    async def authenticate(self, credentials: PlatformCredentials) -> bool:
        """Authenticate with Pinterest using OAuth 2.0"""
        return await self._pinterest_integration.authenticate(credentials)
    
    async def validate_connection(self) -> bool:
        """Validate Pinterest connection"""
        return await self._pinterest_integration.validate_connection()
    
    async def post_content(self, content: PostContent) -> PostResult:
        """Create Pinterest pin with comprehensive functionality"""
        return await self._pinterest_integration.post_content(content)
    
    async def get_post_metrics(self, post_id: str) -> Optional[PlatformMetrics]:
        """Get Pinterest pin metrics"""
        return await self._pinterest_integration.get_post_metrics(post_id)
    
    async def format_content(self, content: PostContent) -> PostContent:
        """Format content for Pinterest"""
        return await self._pinterest_integration.format_content(content)
    
    # Additional Pinterest-specific methods
    async def create_board(
        self,
        name: str,
        description: str = "",
        privacy: str = "PUBLIC"
    ) -> Optional[Dict[str, Any]]:
        """Create a new Pinterest board"""
        board = await self._pinterest_integration.create_board(name, description, privacy)
        return board.__dict__ if board else None
    
    async def get_user_boards(self, refresh_cache: bool = False) -> List[Dict[str, Any]]:
        """Get user's Pinterest boards"""
        boards = await self._pinterest_integration.get_user_boards(refresh_cache)
        return [board.__dict__ for board in boards]
    
    async def update_pin(
        self,
        pin_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        alt_text: Optional[str] = None,
        board_id: Optional[str] = None,
        note: Optional[str] = None
    ) -> PostResult:
        """Update an existing Pinterest pin"""
        return await self._pinterest_integration.update_pin(
            pin_id, title, description, alt_text, board_id, note
        )
    
    async def get_pin_analytics_detailed(
        self,
        pin_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Optional[Dict[str, Any]]:
        """Get detailed analytics for a Pinterest pin"""
        return await self._pinterest_integration.get_pin_analytics_detailed(
            pin_id, start_date, end_date
        )
    
    async def search_pins(
        self,
        query: str,
        limit: int = 25
    ) -> List[Dict[str, Any]]:
        """Search for pins"""
        pins = await self._pinterest_integration.search_pins(query, limit)
        return [pin.__dict__ for pin in pins]


class ShopifyOAuthIntegration(APIBasedIntegration):
    """
    Shopify OAuth integration with comprehensive e-commerce functionality.
    
    This class provides a wrapper around the full ShopifyIntegration to maintain
    compatibility with the existing platform integration framework while
    providing access to enhanced Shopify-specific features.
    """
    
    def __init__(self, oauth_service: OAuthService, connection: PlatformConnection):
        shop_domain = connection.platform_data.get("shop_domain") if connection.platform_data else "example"
        
        config = PlatformConfig(
            platform=Platform.SHOPIFY,
            integration_type=IntegrationType.API,
            auth_method=AuthenticationMethod.OAUTH2,
            api_base_url=f"https://{shop_domain}.myshopify.com/admin/api/2023-10",
            max_title_length=255,
            max_description_length=65535,
            max_hashtags=250,
            supported_image_formats=["jpg", "jpeg", "png", "gif", "webp"],
            rate_limit_per_minute=40,
            max_retries=3
        )
        super().__init__(config)
        self.oauth_service = oauth_service
        self.connection = connection
        
        # Import and initialize the comprehensive Shopify integration
        from .shopify_integration import ShopifyIntegration
        self._shopify_integration = ShopifyIntegration(oauth_service, connection)
    
    async def authenticate(self, credentials: PlatformCredentials) -> bool:
        """Authenticate with Shopify using OAuth 2.0"""
        return await self._shopify_integration.authenticate(credentials)
    
    async def validate_connection(self) -> bool:
        """Validate Shopify connection"""
        return await self._shopify_integration.validate_connection()
    
    async def post_content(self, content: PostContent) -> PostResult:
        """Create Shopify product with comprehensive functionality"""
        return await self._shopify_integration.post_content(content)
    
    async def get_post_metrics(self, post_id: str) -> Optional[PlatformMetrics]:
        """Get Shopify product metrics"""
        return await self._shopify_integration.get_post_metrics(post_id)
    
    async def format_content(self, content: PostContent) -> PostContent:
        """Format content for Shopify"""
        return await self._shopify_integration.format_content(content)
    
    # Additional Shopify-specific methods
    async def update_product(
        self,
        product_id: str,
        content: PostContent,
        price: Optional[float] = None,
        inventory_quantity: Optional[int] = None
    ) -> PostResult:
        """Update an existing Shopify product"""
        from decimal import Decimal
        price_decimal = Decimal(str(price)) if price is not None else None
        return await self._shopify_integration.update_product(product_id, content, price_decimal, inventory_quantity)
    
    async def get_products(
        self,
        status: str = "active",
        limit: int = 50,
        since_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get products from the Shopify store"""
        products = await self._shopify_integration.get_products(status, limit, since_id)
        return [product.__dict__ for product in products]
    
    async def sync_inventory(self, products_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Synchronize inventory data with Shopify products"""
        return await self._shopify_integration.sync_inventory(products_data)
    
    async def get_orders(
        self,
        status: str = "any",
        financial_status: str = "any",
        fulfillment_status: str = "any",
        created_at_min: Optional[datetime] = None,
        created_at_max: Optional[datetime] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get orders from the Shopify store"""
        orders = await self._shopify_integration.get_orders(
            status, financial_status, fulfillment_status, 
            created_at_min, created_at_max, limit
        )
        return [order.__dict__ for order in orders]
    
    async def get_post_metrics(self, post_id: str) -> Optional[PlatformMetrics]:
        """Get Shopify product metrics"""
        try:
            credentials = self.oauth_service.get_decrypted_credentials(self.connection)
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.api_base_url}/products/{post_id}.json",
                    headers={"X-Shopify-Access-Token": credentials.access_token}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    product = data["product"]
                    
                    return PlatformMetrics(
                        platform=self.platform,
                        post_id=post_id,
                        views=0,  # Shopify doesn't provide view metrics via API
                        retrieved_at=datetime.utcnow()
                    )
                    
        except Exception as e:
            self.logger.error(f"Shopify metrics retrieval failed: {e}")
            
        return None
    
    async def format_content(self, content: PostContent) -> PostContent:
        """Format content for Shopify"""
        # Shopify is flexible with content formatting
        return content.copy()


# Integration factory
def create_oauth_integration(
    platform: Platform,
    oauth_service: OAuthService,
    connection: PlatformConnection
) -> APIBasedIntegration:
    """Factory function to create platform-specific OAuth integrations"""
    
    # Use the new comprehensive Facebook and Instagram integrations
    if platform == Platform.FACEBOOK:
        return create_facebook_integration(oauth_service, connection)
    elif platform == Platform.INSTAGRAM:
        return create_instagram_integration(oauth_service, connection)
    
    # Legacy integrations for other platforms
    integration_classes = {
        Platform.ETSY: EtsyOAuthIntegration,
        Platform.PINTEREST: PinterestOAuthIntegration,
        Platform.SHOPIFY: ShopifyOAuthIntegration
    }
    
    integration_class = integration_classes.get(platform)
    if not integration_class:
        raise ValueError(f"No OAuth integration available for platform: {platform.value}")
    
    return integration_class(oauth_service, connection)