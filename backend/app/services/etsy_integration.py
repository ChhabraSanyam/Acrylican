"""
Etsy Marketplace Integration

This module provides comprehensive integration with Etsy's API for creating and managing
product listings, handling inventory synchronization, and retrieving marketplace metrics.
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Union
import httpx
from sqlalchemy.orm import Session

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
    IntegrationType,
    PlatformIntegrationError
)
from .oauth_service import OAuthService
from ..models import PlatformConnection
import logging

logger = logging.getLogger(__name__)


class EtsyAPIError(PlatformIntegrationError):
    """Etsy-specific API error"""
    
    def __init__(self, message: str, status_code: Optional[int] = None, error_code: Optional[str] = None):
        super().__init__(message, Platform.ETSY, error_code)
        self.status_code = status_code


class EtsyListingData:
    """Data structure for Etsy listing information"""
    
    def __init__(self, data: Dict[str, Any]):
        self.listing_id = data.get("listing_id")
        self.title = data.get("title")
        self.description = data.get("description")
        self.price = data.get("price", {}).get("amount")
        self.currency_code = data.get("price", {}).get("currency_code")
        self.quantity = data.get("quantity")
        self.state = data.get("state")  # active, inactive, draft, etc.
        self.url = data.get("url")
        self.views = data.get("views", 0)
        self.num_favorers = data.get("num_favorers", 0)
        self.creation_timestamp = data.get("creation_timestamp")
        self.last_modified_timestamp = data.get("last_modified_timestamp")
        self.materials = data.get("materials", [])
        self.tags = data.get("tags", [])
        self.taxonomy_id = data.get("taxonomy_id")
        self.shop_section_id = data.get("shop_section_id")
        self.images = data.get("images", [])


class EtsyShopData:
    """Data structure for Etsy shop information"""
    
    def __init__(self, data: Dict[str, Any]):
        self.shop_id = data.get("shop_id")
        self.shop_name = data.get("shop_name")
        self.user_id = data.get("user_id")
        self.currency_code = data.get("currency_code")
        self.is_vacation = data.get("is_vacation", False)
        self.vacation_message = data.get("vacation_message")
        self.sale_message = data.get("sale_message")
        self.digital_sale_message = data.get("digital_sale_message")
        self.listing_active_count = data.get("listing_active_count", 0)
        self.digital_listing_count = data.get("digital_listing_count", 0)


class EtsyIntegration(APIBasedIntegration):
    """
    Comprehensive Etsy marketplace integration.
    
    Provides full functionality for:
    - OAuth 2.0 authentication
    - Product listing creation and management
    - Inventory and pricing synchronization
    - Content formatting and validation
    - Metrics retrieval
    """
    
    # Etsy API constants
    API_VERSION = "v3"
    BASE_URL = "https://openapi.etsy.com/v3"
    
    # Etsy listing limits and constraints
    MAX_TITLE_LENGTH = 140
    MAX_DESCRIPTION_LENGTH = 13000
    MAX_MATERIALS = 13
    MAX_TAGS = 13
    MAX_IMAGES = 10
    MIN_PRICE = Decimal("0.20")
    MAX_PRICE = Decimal("50000.00")
    
    # Etsy taxonomy categories (common ones)
    DEFAULT_TAXONOMY_CATEGORIES = {
        "handmade": 1001,
        "art": 69150467,
        "jewelry": 69150425,
        "clothing": 69150429,
        "home_living": 69150433,
        "craft_supplies": 69150467,
        "vintage": 1001
    }
    
    def __init__(self, oauth_service: OAuthService, connection: PlatformConnection):
        config = PlatformConfig(
            platform=Platform.ETSY,
            integration_type=IntegrationType.API,
            auth_method=AuthenticationMethod.OAUTH2,
            api_base_url=self.BASE_URL,
            api_version=self.API_VERSION,
            max_title_length=self.MAX_TITLE_LENGTH,
            max_description_length=self.MAX_DESCRIPTION_LENGTH,
            max_hashtags=self.MAX_TAGS,
            supported_image_formats=["jpg", "jpeg", "png", "gif", "webp"],
            rate_limit_per_minute=100,  # Etsy rate limit
            max_retries=3,
            retry_delay_seconds=2
        )
        super().__init__(config)
        self.oauth_service = oauth_service
        self.connection = connection
        self._shop_data: Optional[EtsyShopData] = None
        self._shipping_templates: List[Dict[str, Any]] = []
    
    async def authenticate(self, credentials: PlatformCredentials) -> bool:
        """
        Authenticate with Etsy using OAuth 2.0.
        
        Args:
            credentials: OAuth credentials
            
        Returns:
            True if authentication successful
        """
        try:
            # Validate connection by making a test API call
            return await self.validate_connection()
        except Exception as e:
            self.logger.error(f"Etsy authentication failed: {e}")
            return False
    
    async def validate_connection(self) -> bool:
        """
        Validate Etsy connection by testing API access.
        
        Returns:
            True if connection is valid
        """
        if not self.connection:
            return False
        
        try:
            credentials = self.oauth_service.get_decrypted_credentials(self.connection)
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.api_base_url}/application/users/me",
                    headers=self._get_auth_headers(credentials.access_token),
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    # Cache user and shop data for later use
                    await self._load_shop_data(credentials.access_token)
                    return True
                else:
                    self.logger.warning(f"Etsy connection validation failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Etsy connection validation failed: {e}")
            return False
    
    async def post_content(self, content: PostContent) -> PostResult:
        """
        Create a new Etsy listing from content.
        
        Args:
            content: Content to post as listing
            
        Returns:
            PostResult with listing creation status
        """
        try:
            credentials = self.oauth_service.get_decrypted_credentials(self.connection)
            
            # Ensure we have shop data
            if not self._shop_data:
                await self._load_shop_data(credentials.access_token)
            
            if not self._shop_data:
                return PostResult(
                    platform=self.platform,
                    status=PostStatus.FAILED,
                    error_message="Unable to load Etsy shop data",
                    error_code="SHOP_DATA_UNAVAILABLE"
                )
            
            # Format content for Etsy
            formatted_content = await self.format_content(content)
            
            # Validate content
            validation_errors = await self._validate_listing_content(formatted_content)
            if validation_errors:
                return PostResult(
                    platform=self.platform,
                    status=PostStatus.FAILED,
                    error_message=f"Content validation failed: {'; '.join(validation_errors)}",
                    error_code="CONTENT_VALIDATION_FAILED"
                )
            
            # Create the listing
            listing_data = await self._prepare_listing_data(formatted_content)
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.config.api_base_url}/application/shops/{self._shop_data.shop_id}/listings",
                    headers=self._get_auth_headers(credentials.access_token),
                    json=listing_data,
                    timeout=60.0
                )
                
                if response.status_code == 201:
                    result_data = response.json()
                    listing_id = result_data["listing_id"]
                    
                    # Upload images if provided
                    image_upload_results = []
                    if formatted_content.images:
                        image_upload_results = await self._upload_listing_images(
                            credentials.access_token,
                            listing_id,
                            formatted_content.images
                        )
                    
                    # Activate the listing if it was created as draft
                    if listing_data.get("state") == "draft":
                        await self._activate_listing(credentials.access_token, listing_id)
                    
                    return PostResult(
                        platform=self.platform,
                        status=PostStatus.SUCCESS,
                        post_id=str(listing_id),
                        url=f"https://www.etsy.com/listing/{listing_id}",
                        published_at=datetime.utcnow(),
                        metadata={
                            "shop_id": self._shop_data.shop_id,
                            "shop_name": self._shop_data.shop_name,
                            "images_uploaded": len(image_upload_results),
                            "listing_state": "active"
                        }
                    )
                else:
                    error_data = response.json() if response.content else {}
                    return PostResult(
                        platform=self.platform,
                        status=PostStatus.FAILED,
                        error_message=f"Etsy listing creation failed: {error_data.get('error', response.text)}",
                        error_code="LISTING_CREATION_FAILED"
                    )
                    
        except Exception as e:
            self.logger.error(f"Etsy listing creation failed: {e}")
            return PostResult(
                platform=self.platform,
                status=PostStatus.FAILED,
                error_message=str(e),
                error_code="POSTING_EXCEPTION"
            )
    
    async def get_post_metrics(self, post_id: str) -> Optional[PlatformMetrics]:
        """
        Get metrics for an Etsy listing.
        
        Args:
            post_id: Etsy listing ID
            
        Returns:
            PlatformMetrics with listing performance data
        """
        try:
            credentials = self.oauth_service.get_decrypted_credentials(self.connection)
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.api_base_url}/application/listings/{post_id}",
                    headers=self._get_auth_headers(credentials.access_token),
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    listing = EtsyListingData(data)
                    
                    return PlatformMetrics(
                        platform=self.platform,
                        post_id=post_id,
                        views=listing.views,
                        likes=listing.num_favorers,  # Etsy favorites as likes
                        retrieved_at=datetime.utcnow()
                    )
                else:
                    self.logger.warning(f"Failed to get Etsy listing metrics: {response.status_code}")
                    
        except Exception as e:
            self.logger.error(f"Etsy metrics retrieval failed: {e}")
            
        return None
    
    async def format_content(self, content: PostContent) -> PostContent:
        """
        Format content according to Etsy requirements.
        
        Args:
            content: Original content
            
        Returns:
            Formatted content for Etsy
        """
        formatted_content = content.copy()
        
        # Format title (max 140 characters)
        if len(formatted_content.title) > self.MAX_TITLE_LENGTH:
            formatted_content.title = formatted_content.title[:137] + "..."
        
        # Format description (max 13,000 characters)
        if len(formatted_content.description) > self.MAX_DESCRIPTION_LENGTH:
            formatted_content.description = formatted_content.description[:12997] + "..."
        
        # Format materials/tags (max 13 each)
        formatted_content.hashtags = content.hashtags[:self.MAX_TAGS]
        
        # Ensure hashtags don't have # symbol (Etsy doesn't use hashtags)
        formatted_content.hashtags = [
            tag.lstrip('#').lower() for tag in formatted_content.hashtags
        ]
        
        # Limit images to max 10
        if len(formatted_content.images) > self.MAX_IMAGES:
            formatted_content.images = formatted_content.images[:self.MAX_IMAGES]
        
        return formatted_content
    
    async def update_listing(
        self,
        listing_id: str,
        content: PostContent,
        price: Optional[Decimal] = None,
        quantity: Optional[int] = None
    ) -> PostResult:
        """
        Update an existing Etsy listing.
        
        Args:
            listing_id: Etsy listing ID to update
            content: Updated content
            price: New price (optional)
            quantity: New quantity (optional)
            
        Returns:
            PostResult with update status
        """
        try:
            credentials = self.oauth_service.get_decrypted_credentials(self.connection)
            
            # Format content
            formatted_content = await self.format_content(content)
            
            # Prepare update data
            update_data = {
                "title": formatted_content.title,
                "description": formatted_content.description,
                "materials": formatted_content.hashtags,
                "tags": formatted_content.hashtags
            }
            
            if price is not None:
                update_data["price"] = str(price)
            
            if quantity is not None:
                update_data["quantity"] = quantity
            
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{self.config.api_base_url}/application/shops/{self._shop_data.shop_id}/listings/{listing_id}",
                    headers=self._get_auth_headers(credentials.access_token),
                    json=update_data,
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    return PostResult(
                        platform=self.platform,
                        status=PostStatus.SUCCESS,
                        post_id=listing_id,
                        url=f"https://www.etsy.com/listing/{listing_id}",
                        published_at=datetime.utcnow(),
                        metadata={"action": "update"}
                    )
                else:
                    error_data = response.json() if response.content else {}
                    return PostResult(
                        platform=self.platform,
                        status=PostStatus.FAILED,
                        error_message=f"Listing update failed: {error_data.get('error', response.text)}",
                        error_code="LISTING_UPDATE_FAILED"
                    )
                    
        except Exception as e:
            self.logger.error(f"Etsy listing update failed: {e}")
            return PostResult(
                platform=self.platform,
                status=PostStatus.FAILED,
                error_message=str(e),
                error_code="UPDATE_EXCEPTION"
            )
    
    async def get_shop_listings(
        self,
        state: str = "active",
        limit: int = 25,
        offset: int = 0
    ) -> List[EtsyListingData]:
        """
        Get listings from the connected Etsy shop.
        
        Args:
            state: Listing state (active, inactive, draft, etc.)
            limit: Number of listings to retrieve
            offset: Offset for pagination
            
        Returns:
            List of EtsyListingData objects
        """
        try:
            credentials = self.oauth_service.get_decrypted_credentials(self.connection)
            
            if not self._shop_data:
                await self._load_shop_data(credentials.access_token)
            
            if not self._shop_data:
                return []
            
            async with httpx.AsyncClient() as client:
                params = {
                    "state": state,
                    "limit": limit,
                    "offset": offset
                }
                
                response = await client.get(
                    f"{self.config.api_base_url}/application/shops/{self._shop_data.shop_id}/listings",
                    headers=self._get_auth_headers(credentials.access_token),
                    params=params,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return [EtsyListingData(listing) for listing in data.get("results", [])]
                else:
                    self.logger.warning(f"Failed to get shop listings: {response.status_code}")
                    return []
                    
        except Exception as e:
            self.logger.error(f"Failed to get shop listings: {e}")
            return []
    
    async def sync_inventory(self, listings_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Synchronize inventory data with Etsy listings.
        
        Args:
            listings_data: List of listing data with inventory updates
            
        Returns:
            Dictionary with sync results
        """
        results = {
            "updated": 0,
            "failed": 0,
            "errors": []
        }
        
        try:
            credentials = self.oauth_service.get_decrypted_credentials(self.connection)
            
            for listing_data in listings_data:
                listing_id = listing_data.get("listing_id")
                quantity = listing_data.get("quantity")
                price = listing_data.get("price")
                
                if not listing_id:
                    results["failed"] += 1
                    results["errors"].append("Missing listing_id")
                    continue
                
                try:
                    update_data = {}
                    
                    if quantity is not None:
                        update_data["quantity"] = quantity
                    
                    if price is not None:
                        update_data["price"] = str(price)
                    
                    if update_data:
                        async with httpx.AsyncClient() as client:
                            response = await client.put(
                                f"{self.config.api_base_url}/application/shops/{self._shop_data.shop_id}/listings/{listing_id}",
                                headers=self._get_auth_headers(credentials.access_token),
                                json=update_data,
                                timeout=30.0
                            )
                            
                            if response.status_code == 200:
                                results["updated"] += 1
                            else:
                                results["failed"] += 1
                                results["errors"].append(f"Listing {listing_id}: {response.status_code}")
                    
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append(f"Listing {listing_id}: {str(e)}")
                    
        except Exception as e:
            self.logger.error(f"Inventory sync failed: {e}")
            results["errors"].append(f"General error: {str(e)}")
        
        return results
    
    def _get_auth_headers(self, access_token: str) -> Dict[str, str]:
        """Get authentication headers for Etsy API requests"""
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "x-api-key": access_token  # Etsy also requires API key in header
        }
    
    async def _load_shop_data(self, access_token: str) -> None:
        """Load and cache shop data"""
        try:
            async with httpx.AsyncClient() as client:
                # Get user info first
                user_response = await client.get(
                    f"{self.config.api_base_url}/application/users/me",
                    headers=self._get_auth_headers(access_token),
                    timeout=30.0
                )
                
                if user_response.status_code != 200:
                    raise EtsyAPIError("Failed to get user info", user_response.status_code)
                
                user_data = user_response.json()
                user_id = user_data["user_id"]
                
                # Get user's shops
                shops_response = await client.get(
                    f"{self.config.api_base_url}/application/users/{user_id}/shops",
                    headers=self._get_auth_headers(access_token),
                    timeout=30.0
                )
                
                if shops_response.status_code != 200:
                    raise EtsyAPIError("Failed to get shops", shops_response.status_code)
                
                shops_data = shops_response.json()
                shops = shops_data.get("results", [])
                
                if not shops:
                    raise EtsyAPIError("No Etsy shops found")
                
                # Use the first shop
                self._shop_data = EtsyShopData(shops[0])
                
                # Load shipping templates
                await self._load_shipping_templates(access_token)
                
        except Exception as e:
            self.logger.error(f"Failed to load shop data: {e}")
            raise
    
    async def _load_shipping_templates(self, access_token: str) -> None:
        """Load shipping templates for the shop"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.api_base_url}/application/shops/{self._shop_data.shop_id}/shipping-templates",
                    headers=self._get_auth_headers(access_token),
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self._shipping_templates = data.get("results", [])
                
        except Exception as e:
            self.logger.warning(f"Failed to load shipping templates: {e}")
            self._shipping_templates = []
    
    async def _validate_listing_content(self, content: PostContent) -> List[str]:
        """Validate listing content against Etsy requirements"""
        errors = []
        
        # Title validation
        if not content.title or len(content.title.strip()) == 0:
            errors.append("Title is required")
        elif len(content.title) > self.MAX_TITLE_LENGTH:
            errors.append(f"Title exceeds {self.MAX_TITLE_LENGTH} characters")
        
        # Description validation
        if not content.description or len(content.description.strip()) == 0:
            errors.append("Description is required")
        elif len(content.description) > self.MAX_DESCRIPTION_LENGTH:
            errors.append(f"Description exceeds {self.MAX_DESCRIPTION_LENGTH} characters")
        
        # Price validation
        if content.product_data:
            price_str = content.product_data.get("price")
            if price_str:
                try:
                    price = Decimal(str(price_str))
                    if price < self.MIN_PRICE:
                        errors.append(f"Price must be at least ${self.MIN_PRICE}")
                    elif price > self.MAX_PRICE:
                        errors.append(f"Price cannot exceed ${self.MAX_PRICE}")
                except (ValueError, TypeError):
                    errors.append("Invalid price format")
        
        # Materials/tags validation
        if len(content.hashtags) > self.MAX_MATERIALS:
            errors.append(f"Too many materials/tags (max {self.MAX_MATERIALS})")
        
        # Images validation
        if len(content.images) > self.MAX_IMAGES:
            errors.append(f"Too many images (max {self.MAX_IMAGES})")
        
        return errors
    
    async def _prepare_listing_data(self, content: PostContent) -> Dict[str, Any]:
        """Prepare listing data for Etsy API"""
        # Get price from product data or use default
        price = "10.00"  # Default price
        if content.product_data and content.product_data.get("price"):
            price = str(content.product_data["price"])
        
        # Get quantity from product data or use default
        quantity = 1
        if content.product_data and content.product_data.get("quantity"):
            quantity = int(content.product_data["quantity"])
        
        # Determine taxonomy ID (category)
        taxonomy_id = self._determine_taxonomy_id(content)
        
        # Get shipping template ID
        shipping_template_id = None
        if self._shipping_templates:
            shipping_template_id = self._shipping_templates[0]["shipping_template_id"]
        
        listing_data = {
            "title": content.title,
            "description": content.description,
            "price": price,
            "quantity": quantity,
            "who_made": "i_did",
            "when_made": "2020_2024",
            "taxonomy_id": taxonomy_id,
            "materials": content.hashtags,
            "tags": content.hashtags,
            "state": "active"  # Create as active listing
        }
        
        # Add shipping template if available
        if shipping_template_id:
            listing_data["shipping_template_id"] = shipping_template_id
        
        # Add shop section if specified in product data
        if content.product_data and content.product_data.get("shop_section_id"):
            listing_data["shop_section_id"] = content.product_data["shop_section_id"]
        
        return listing_data
    
    def _determine_taxonomy_id(self, content: PostContent) -> int:
        """Determine appropriate taxonomy ID based on content"""
        # Check product data for category hint
        if content.product_data and content.product_data.get("category"):
            category = content.product_data["category"].lower()
            if category in self.DEFAULT_TAXONOMY_CATEGORIES:
                return self.DEFAULT_TAXONOMY_CATEGORIES[category]
        
        # Check hashtags for category hints
        for tag in content.hashtags:
            tag_lower = tag.lower().strip('#')
            if tag_lower in self.DEFAULT_TAXONOMY_CATEGORIES:
                return self.DEFAULT_TAXONOMY_CATEGORIES[tag_lower]
        
        # Default to handmade category
        return self.DEFAULT_TAXONOMY_CATEGORIES["handmade"]
    
    async def _upload_listing_images(
        self,
        access_token: str,
        listing_id: str,
        image_urls: List[str]
    ) -> List[Dict[str, Any]]:
        """Upload images to an Etsy listing"""
        results = []
        
        async with httpx.AsyncClient() as client:
            for i, image_url in enumerate(image_urls[:self.MAX_IMAGES]):
                try:
                    image_data = {
                        "image_url": image_url,
                        "rank": i + 1,  # Image order
                        "is_watermarked": False
                    }
                    
                    response = await client.post(
                        f"{self.config.api_base_url}/application/shops/{self._shop_data.shop_id}/listings/{listing_id}/images",
                        headers=self._get_auth_headers(access_token),
                        json=image_data,
                        timeout=60.0
                    )
                    
                    if response.status_code == 201:
                        results.append({
                            "success": True,
                            "image_url": image_url,
                            "rank": i + 1
                        })
                    else:
                        results.append({
                            "success": False,
                            "image_url": image_url,
                            "error": f"HTTP {response.status_code}"
                        })
                        
                except Exception as e:
                    results.append({
                        "success": False,
                        "image_url": image_url,
                        "error": str(e)
                    })
        
        return results
    
    async def _activate_listing(self, access_token: str, listing_id: str) -> bool:
        """Activate a draft listing"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{self.config.api_base_url}/application/shops/{self._shop_data.shop_id}/listings/{listing_id}",
                    headers=self._get_auth_headers(access_token),
                    json={"state": "active"},
                    timeout=30.0
                )
                
                return response.status_code == 200
                
        except Exception as e:
            self.logger.error(f"Failed to activate listing {listing_id}: {e}")
            return False


def create_etsy_integration(
    oauth_service: OAuthService,
    connection: PlatformConnection
) -> EtsyIntegration:
    """
    Factory function to create an Etsy integration instance.
    
    Args:
        oauth_service: OAuth service instance
        connection: Platform connection
        
    Returns:
        EtsyIntegration instance
    """
    return EtsyIntegration(oauth_service, connection)