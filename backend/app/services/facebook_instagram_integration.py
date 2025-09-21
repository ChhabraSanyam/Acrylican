"""
Facebook and Instagram Integration

This module provides comprehensive integration with Facebook and Instagram
platforms using the Facebook Graph API. It handles both regular posts and
Facebook Marketplace listings, with proper content formatting and error handling.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
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
    IntegrationType,
    PostingError,
    AuthenticationError
)
from ..models import PlatformConnection
import logging

logger = logging.getLogger(__name__)


class FacebookIntegration(APIBasedIntegration):
    """Facebook integration with Graph API for posts and marketplace"""
    
    def __init__(self, oauth_service: OAuthService, connection: PlatformConnection):
        config = PlatformConfig(
            platform=Platform.FACEBOOK,
            integration_type=IntegrationType.API,
            auth_method=AuthenticationMethod.OAUTH2,
            api_base_url="https://graph.facebook.com/v18.0",
            api_version="v18.0",
            rate_limit_per_minute=200,
            max_title_length=2200,
            max_description_length=63206,
            max_hashtags=30,
            supported_image_formats=["jpg", "jpeg", "png", "gif", "webp"],
            max_retries=3,
            retry_delay_seconds=5,
            custom_settings={
                "supports_marketplace": True,
                "supports_albums": True,
                "supports_video": True,
                "max_images_per_post": 10
            }
        )
        super().__init__(config)
        self.oauth_service = oauth_service
        self.connection = connection
        self._credentials = None
        self._pages_cache = None
        self._cache_expiry = None
    
    async def authenticate(self, credentials: PlatformCredentials) -> bool:
        """Facebook authentication is handled by OAuth service"""
        try:
            self._credentials = credentials
            
            # Validate the credentials by making a test API call
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.api_base_url}/me",
                    headers={"Authorization": f"Bearer {credentials.access_token}"},
                    params={"fields": "id,name,email"}
                )
                
                if response.status_code == 200:
                    self.logger.info("Facebook authentication successful")
                    return True
                else:
                    self.logger.error(f"Facebook authentication failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Facebook authentication error: {e}")
            raise AuthenticationError(f"Facebook authentication failed: {str(e)}", self.platform)
    
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
                
                if response.status_code == 200:
                    self.logger.debug("Facebook connection validation successful")
                    return True
                elif response.status_code == 401:
                    self.logger.warning("Facebook token expired or invalid")
                    return False
                else:
                    self.logger.warning(f"Facebook validation failed with status: {response.status_code}")
                    return False
                
        except Exception as e:
            self.logger.error(f"Facebook connection validation failed: {e}")
            return False
    
    async def _get_user_pages(self, access_token: str) -> List[Dict[str, Any]]:
        """Get user's Facebook pages with caching"""
        current_time = datetime.utcnow()
        
        # Return cached pages if still valid (cache for 5 minutes)
        if (self._pages_cache and self._cache_expiry and 
            current_time < self._cache_expiry):
            return self._pages_cache
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.api_base_url}/me/accounts",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={"fields": "id,name,access_token,category,tasks"}
                )
                
                if response.status_code == 200:
                    pages_data = response.json()
                    pages = pages_data.get("data", [])
                    
                    # Cache the results
                    self._pages_cache = pages
                    self._cache_expiry = current_time.replace(minute=current_time.minute + 5)
                    
                    return pages
                else:
                    self.logger.error(f"Failed to get Facebook pages: {response.status_code}")
                    return []
                    
        except Exception as e:
            self.logger.error(f"Error getting Facebook pages: {e}")
            return []
    
    async def post_content(self, content: PostContent) -> PostResult:
        """Post content to Facebook"""
        try:
            credentials = self.oauth_service.get_decrypted_credentials(self.connection)
            
            # Check if this is a marketplace post
            is_marketplace = (content.platform_specific and 
                            content.platform_specific.get("post_type") == "marketplace")
            
            if is_marketplace:
                return await self._post_to_marketplace(content, credentials.access_token)
            else:
                return await self._post_to_feed(content, credentials.access_token)
                
        except Exception as e:
            self.logger.error(f"Facebook posting failed: {e}")
            return PostResult(
                platform=self.platform,
                status=PostStatus.FAILED,
                error_message=str(e),
                error_code="POSTING_EXCEPTION"
            )
    
    async def _post_to_feed(self, content: PostContent, access_token: str) -> PostResult:
        """Post content to Facebook feed"""
        try:
            pages = await self._get_user_pages(access_token)
            
            if not pages:
                return PostResult(
                    platform=self.platform,
                    status=PostStatus.FAILED,
                    error_message="No Facebook pages found",
                    error_code="NO_PAGES_FOUND"
                )
            
            # Use the first page or find a specific page if specified
            target_page = pages[0]
            if content.platform_specific and content.platform_specific.get("page_id"):
                page_id = content.platform_specific["page_id"]
                target_page = next((p for p in pages if p["id"] == page_id), pages[0])
            
            page_access_token = target_page["access_token"]
            page_id = target_page["id"]
            
            async with httpx.AsyncClient() as client:
                # Handle multiple images vs single image/text post
                if content.images and len(content.images) > 1:
                    return await self._create_photo_album(
                        client, page_id, page_access_token, content
                    )
                else:
                    return await self._create_single_post(
                        client, page_id, page_access_token, content
                    )
                    
        except Exception as e:
            self.logger.error(f"Facebook feed posting failed: {e}")
            raise PostingError(f"Facebook feed posting failed: {str(e)}", self.platform)
    
    async def _create_single_post(
        self, 
        client: httpx.AsyncClient, 
        page_id: str, 
        page_access_token: str, 
        content: PostContent
    ) -> PostResult:
        """Create a single Facebook post"""
        
        # Prepare post message
        message_parts = []
        if content.title:
            message_parts.append(content.title)
        if content.description:
            message_parts.append(content.description)
        if content.hashtags:
            message_parts.append(" ".join(content.hashtags))
        
        post_data = {
            "message": "\n\n".join(message_parts),
            "access_token": page_access_token
        }
        
        # Add image if provided
        if content.images:
            # For single image, we can use the link parameter or upload directly
            post_data["link"] = content.images[0]
        
        # Add any custom Facebook-specific parameters
        if content.platform_specific:
            if content.platform_specific.get("link"):
                post_data["link"] = content.platform_specific["link"]
            if content.platform_specific.get("scheduled_publish_time"):
                post_data["scheduled_publish_time"] = content.platform_specific["scheduled_publish_time"]
                post_data["published"] = False
        
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
                url=f"https://www.facebook.com/{result_data.get('id')}",
                published_at=datetime.utcnow(),
                metadata={
                    "page_id": page_id,
                    "page_name": await self._get_page_name(page_id, page_access_token)
                }
            )
        else:
            error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            return PostResult(
                platform=self.platform,
                status=PostStatus.FAILED,
                error_message=f"Facebook API error: {error_data.get('error', {}).get('message', response.text)}",
                error_code=error_data.get('error', {}).get('code', 'API_ERROR')
            )
    
    async def _create_photo_album(
        self, 
        client: httpx.AsyncClient, 
        page_id: str, 
        page_access_token: str, 
        content: PostContent
    ) -> PostResult:
        """Create a Facebook photo album with multiple images"""
        
        try:
            # Create album first
            album_data = {
                "name": content.title or "Product Photos",
                "message": content.description or "",
                "access_token": page_access_token
            }
            
            album_response = await client.post(
                f"{self.config.api_base_url}/{page_id}/albums",
                data=album_data
            )
            
            if album_response.status_code != 200:
                # Fallback to single post if album creation fails
                self.logger.warning("Album creation failed, falling back to single post")
                return await self._create_single_post(client, page_id, page_access_token, content)
            
            album_data = album_response.json()
            album_id = album_data["id"]
            
            # Upload photos to album
            uploaded_photos = []
            for i, image_url in enumerate(content.images[:10]):  # Facebook allows max 10 images
                photo_data = {
                    "url": image_url,
                    "message": f"Photo {i+1}" + (f" - {content.hashtags[i]}" if i < len(content.hashtags) else ""),
                    "access_token": page_access_token
                }
                
                photo_response = await client.post(
                    f"{self.config.api_base_url}/{album_id}/photos",
                    data=photo_data
                )
                
                if photo_response.status_code == 200:
                    uploaded_photos.append(photo_response.json())
                else:
                    self.logger.warning(f"Failed to upload photo {i+1}: {photo_response.text}")
            
            if uploaded_photos:
                return PostResult(
                    platform=self.platform,
                    status=PostStatus.SUCCESS,
                    post_id=album_id,
                    url=f"https://www.facebook.com/media/set/?set=a.{album_id}",
                    published_at=datetime.utcnow(),
                    metadata={
                        "album_id": album_id,
                        "photos_uploaded": len(uploaded_photos),
                        "page_id": page_id
                    }
                )
            else:
                return PostResult(
                    platform=self.platform,
                    status=PostStatus.FAILED,
                    error_message="No photos could be uploaded to album",
                    error_code="PHOTO_UPLOAD_FAILED"
                )
                
        except Exception as e:
            self.logger.error(f"Photo album creation failed: {e}")
            # Fallback to single post
            return await self._create_single_post(client, page_id, page_access_token, content)
    
    async def _post_to_marketplace(self, content: PostContent, access_token: str) -> PostResult:
        """Post product to Facebook Marketplace"""
        try:
            if not content.product_data:
                return PostResult(
                    platform=self.platform,
                    status=PostStatus.FAILED,
                    error_message="Product data is required for Facebook Marketplace",
                    error_code="MISSING_PRODUCT_DATA"
                )
            
            pages = await self._get_user_pages(access_token)
            if not pages:
                return PostResult(
                    platform=self.platform,
                    status=PostStatus.FAILED,
                    error_message="No Facebook pages found for marketplace posting",
                    error_code="NO_PAGES_FOUND"
                )
            
            # Use first page for marketplace
            page = pages[0]
            page_access_token = page["access_token"]
            page_id = page["id"]
            
            # Prepare marketplace listing data
            listing_data = {
                "title": content.title,
                "description": content.description,
                "price": int(float(content.product_data.get("price", 0)) * 100),  # Price in cents
                "currency": content.product_data.get("currency", "USD"),
                "condition": content.product_data.get("condition", "NEW"),
                "availability": content.product_data.get("availability", "IN_STOCK"),
                "category": content.product_data.get("category", "OTHER"),
                "access_token": page_access_token
            }
            
            # Add images
            if content.images:
                listing_data["images"] = content.images[:10]  # Max 10 images
            
            # Add location if provided
            if content.product_data.get("location"):
                listing_data["location"] = content.product_data["location"]
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.config.api_base_url}/{page_id}/marketplace_listings",
                    data=listing_data
                )
                
                if response.status_code == 200:
                    result_data = response.json()
                    return PostResult(
                        platform=self.platform,
                        status=PostStatus.SUCCESS,
                        post_id=result_data.get("id"),
                        url=f"https://www.facebook.com/marketplace/item/{result_data.get('id')}",
                        published_at=datetime.utcnow(),
                        metadata={
                            "listing_type": "marketplace",
                            "page_id": page_id,
                            "price": listing_data["price"],
                            "currency": listing_data["currency"]
                        }
                    )
                else:
                    error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                    return PostResult(
                        platform=self.platform,
                        status=PostStatus.FAILED,
                        error_message=f"Marketplace listing failed: {error_data.get('error', {}).get('message', response.text)}",
                        error_code=error_data.get('error', {}).get('code', 'MARKETPLACE_ERROR')
                    )
                    
        except Exception as e:
            self.logger.error(f"Facebook Marketplace posting failed: {e}")
            return PostResult(
                platform=self.platform,
                status=PostStatus.FAILED,
                error_message=str(e),
                error_code="MARKETPLACE_EXCEPTION"
            )
    
    async def _get_page_name(self, page_id: str, page_access_token: str) -> str:
        """Get page name for metadata"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.api_base_url}/{page_id}",
                    headers={"Authorization": f"Bearer {page_access_token}"},
                    params={"fields": "name"}
                )
                
                if response.status_code == 200:
                    return response.json().get("name", "Unknown Page")
                    
        except Exception:
            pass
        
        return "Unknown Page"
    
    async def get_post_metrics(self, post_id: str) -> Optional[PlatformMetrics]:
        """Get Facebook post metrics"""
        try:
            credentials = self.oauth_service.get_decrypted_credentials(self.connection)
            
            async with httpx.AsyncClient() as client:
                # Try to get post insights
                insights_response = await client.get(
                    f"{self.config.api_base_url}/{post_id}/insights",
                    headers={"Authorization": f"Bearer {credentials.access_token}"},
                    params={
                        "metric": "post_impressions,post_engaged_users,post_clicks,post_reactions_like_total,post_reactions_love_total,post_reactions_wow_total,post_reactions_haha_total,post_reactions_sorry_total,post_reactions_anger_total"
                    }
                )
                
                # Also get basic post data
                post_response = await client.get(
                    f"{self.config.api_base_url}/{post_id}",
                    headers={"Authorization": f"Bearer {credentials.access_token}"},
                    params={
                        "fields": "likes.summary(true),comments.summary(true),shares"
                    }
                )
                
                metrics_data = {}
                
                # Process insights data
                if insights_response.status_code == 200:
                    insights_data = insights_response.json()
                    for metric in insights_data.get("data", []):
                        metric_name = metric["name"]
                        metric_value = metric["values"][0]["value"] if metric["values"] else 0
                        metrics_data[metric_name] = metric_value
                
                # Process basic post data
                if post_response.status_code == 200:
                    post_data = post_response.json()
                    metrics_data.update({
                        "likes": post_data.get("likes", {}).get("summary", {}).get("total_count", 0),
                        "comments": post_data.get("comments", {}).get("summary", {}).get("total_count", 0),
                        "shares": post_data.get("shares", {}).get("count", 0)
                    })
                
                if metrics_data:
                    return PlatformMetrics(
                        platform=self.platform,
                        post_id=post_id,
                        likes=metrics_data.get("likes", 0),
                        comments=metrics_data.get("comments", 0),
                        shares=metrics_data.get("shares", 0),
                        views=metrics_data.get("post_impressions", 0),
                        reach=metrics_data.get("post_engaged_users", 0),
                        engagement_rate=self._calculate_engagement_rate(metrics_data),
                        retrieved_at=datetime.utcnow()
                    )
                    
        except Exception as e:
            self.logger.error(f"Facebook metrics retrieval failed: {e}")
            
        return None
    
    def _calculate_engagement_rate(self, metrics_data: Dict[str, Any]) -> Optional[float]:
        """Calculate engagement rate from metrics data"""
        try:
            impressions = metrics_data.get("post_impressions", 0)
            engaged_users = metrics_data.get("post_engaged_users", 0)
            
            if impressions > 0:
                return round((engaged_users / impressions) * 100, 2)
                
        except Exception:
            pass
        
        return None
    
    async def format_content(self, content: PostContent) -> PostContent:
        """Format content for Facebook"""
        formatted_content = content.model_copy()
        
        # Facebook allows long content, but let's ensure hashtags are properly formatted
        formatted_hashtags = []
        for tag in content.hashtags[:30]:  # Facebook allows up to 30 hashtags
            if not tag.startswith("#"):
                tag = f"#{tag}"
            formatted_hashtags.append(tag)
        
        formatted_content.hashtags = formatted_hashtags
        
        # Ensure title and description fit within limits
        if len(formatted_content.title) > self.config.max_title_length:
            formatted_content.title = formatted_content.title[:self.config.max_title_length-3] + "..."
        
        if len(formatted_content.description) > self.config.max_description_length:
            formatted_content.description = formatted_content.description[:self.config.max_description_length-3] + "..."
        
        return formatted_content


class InstagramIntegration(APIBasedIntegration):
    """Instagram integration with Graph API"""
    
    def __init__(self, oauth_service: OAuthService, connection: PlatformConnection):
        config = PlatformConfig(
            platform=Platform.INSTAGRAM,
            integration_type=IntegrationType.API,
            auth_method=AuthenticationMethod.OAUTH2,
            api_base_url="https://graph.facebook.com/v18.0",
            api_version="v18.0",
            rate_limit_per_minute=200,
            max_title_length=2200,
            max_description_length=2200,
            max_hashtags=30,
            supported_image_formats=["jpg", "jpeg", "png"],
            max_retries=3,
            retry_delay_seconds=5,
            custom_settings={
                "supports_carousel": True,
                "supports_video": True,
                "supports_stories": True,
                "max_images_per_carousel": 10
            }
        )
        super().__init__(config)
        self.oauth_service = oauth_service
        self.connection = connection
        self._instagram_accounts_cache = None
        self._cache_expiry = None
    
    async def authenticate(self, credentials: PlatformCredentials) -> bool:
        """Instagram authentication is handled by OAuth service"""
        try:
            # Validate by getting Instagram business accounts
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.api_base_url}/me/accounts",
                    headers={"Authorization": f"Bearer {credentials.access_token}"},
                    params={"fields": "instagram_business_account"}
                )
                
                if response.status_code == 200:
                    self.logger.info("Instagram authentication successful")
                    return True
                else:
                    self.logger.error(f"Instagram authentication failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Instagram authentication error: {e}")
            raise AuthenticationError(f"Instagram authentication failed: {str(e)}", self.platform)
    
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
                
                if response.status_code == 200:
                    # Check if we have at least one Instagram business account
                    data = response.json()
                    has_instagram = any(
                        "instagram_business_account" in page 
                        for page in data.get("data", [])
                    )
                    
                    if has_instagram:
                        self.logger.debug("Instagram connection validation successful")
                        return True
                    else:
                        self.logger.warning("No Instagram business accounts found")
                        return False
                elif response.status_code == 401:
                    self.logger.warning("Instagram token expired or invalid")
                    return False
                else:
                    self.logger.warning(f"Instagram validation failed with status: {response.status_code}")
                    return False
                
        except Exception as e:
            self.logger.error(f"Instagram connection validation failed: {e}")
            return False
    
    async def _get_instagram_accounts(self, access_token: str) -> List[Dict[str, Any]]:
        """Get Instagram business accounts with caching"""
        current_time = datetime.utcnow()
        
        # Return cached accounts if still valid (cache for 5 minutes)
        if (self._instagram_accounts_cache and self._cache_expiry and 
            current_time < self._cache_expiry):
            return self._instagram_accounts_cache
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.api_base_url}/me/accounts",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={"fields": "instagram_business_account,name,id"}
                )
                
                if response.status_code == 200:
                    pages_data = response.json()
                    instagram_accounts = []
                    
                    for page in pages_data.get("data", []):
                        if "instagram_business_account" in page:
                            instagram_accounts.append({
                                "page_id": page["id"],
                                "page_name": page["name"],
                                "instagram_account_id": page["instagram_business_account"]["id"]
                            })
                    
                    # Cache the results
                    self._instagram_accounts_cache = instagram_accounts
                    self._cache_expiry = current_time.replace(minute=current_time.minute + 5)
                    
                    return instagram_accounts
                else:
                    self.logger.error(f"Failed to get Instagram accounts: {response.status_code}")
                    return []
                    
        except Exception as e:
            self.logger.error(f"Error getting Instagram accounts: {e}")
            return []
    
    async def post_content(self, content: PostContent) -> PostResult:
        """Post content to Instagram"""
        try:
            credentials = self.oauth_service.get_decrypted_credentials(self.connection)
            
            instagram_accounts = await self._get_instagram_accounts(credentials.access_token)
            
            if not instagram_accounts:
                return PostResult(
                    platform=self.platform,
                    status=PostStatus.FAILED,
                    error_message="No Instagram business accounts found",
                    error_code="NO_INSTAGRAM_ACCOUNT"
                )
            
            # Use the first Instagram account or find a specific one if specified
            target_account = instagram_accounts[0]
            if content.platform_specific and content.platform_specific.get("instagram_account_id"):
                account_id = content.platform_specific["instagram_account_id"]
                target_account = next(
                    (acc for acc in instagram_accounts if acc["instagram_account_id"] == account_id), 
                    instagram_accounts[0]
                )
            
            instagram_account_id = target_account["instagram_account_id"]
            
            # Check if this is a carousel post (multiple images)
            if content.images and len(content.images) > 1:
                return await self._create_carousel_post(
                    instagram_account_id, credentials.access_token, content
                )
            else:
                return await self._create_single_post(
                    instagram_account_id, credentials.access_token, content
                )
                
        except Exception as e:
            self.logger.error(f"Instagram posting failed: {e}")
            return PostResult(
                platform=self.platform,
                status=PostStatus.FAILED,
                error_message=str(e),
                error_code="POSTING_EXCEPTION"
            )
    
    async def _create_single_post(
        self, 
        instagram_account_id: str, 
        access_token: str, 
        content: PostContent
    ) -> PostResult:
        """Create a single Instagram post"""
        
        if not content.images:
            return PostResult(
                platform=self.platform,
                status=PostStatus.FAILED,
                error_message="Instagram requires at least one image",
                error_code="NO_IMAGE_PROVIDED"
            )
        
        try:
            async with httpx.AsyncClient() as client:
                # Prepare caption
                caption_parts = []
                if content.title:
                    caption_parts.append(content.title)
                if content.description:
                    caption_parts.append(content.description)
                if content.hashtags:
                    caption_parts.append(" ".join(content.hashtags))
                
                caption = "\n\n".join(caption_parts)
                
                # Create media container
                container_data = {
                    "image_url": content.images[0],
                    "caption": caption[:2200],  # Instagram caption limit
                    "access_token": access_token
                }
                
                # Add location if provided
                if content.platform_specific and content.platform_specific.get("location_id"):
                    container_data["location_id"] = content.platform_specific["location_id"]
                
                container_response = await client.post(
                    f"{self.config.api_base_url}/{instagram_account_id}/media",
                    data=container_data
                )
                
                if container_response.status_code != 200:
                    error_data = container_response.json() if container_response.headers.get("content-type", "").startswith("application/json") else {}
                    return PostResult(
                        platform=self.platform,
                        status=PostStatus.FAILED,
                        error_message=f"Failed to create media container: {error_data.get('error', {}).get('message', container_response.text)}",
                        error_code=error_data.get('error', {}).get('code', 'CONTAINER_CREATION_FAILED')
                    )
                
                container_id = container_response.json()["id"]
                
                # Publish the media
                publish_data = {
                    "creation_id": container_id,
                    "access_token": access_token
                }
                
                publish_response = await client.post(
                    f"{self.config.api_base_url}/{instagram_account_id}/media_publish",
                    data=publish_data
                )
                
                if publish_response.status_code == 200:
                    result_data = publish_response.json()
                    return PostResult(
                        platform=self.platform,
                        status=PostStatus.SUCCESS,
                        post_id=result_data.get("id"),
                        url=f"https://www.instagram.com/p/{result_data.get('id')}",
                        published_at=datetime.utcnow(),
                        metadata={
                            "instagram_account_id": instagram_account_id,
                            "media_type": "IMAGE"
                        }
                    )
                else:
                    error_data = publish_response.json() if publish_response.headers.get("content-type", "").startswith("application/json") else {}
                    return PostResult(
                        platform=self.platform,
                        status=PostStatus.FAILED,
                        error_message=f"Instagram publish failed: {error_data.get('error', {}).get('message', publish_response.text)}",
                        error_code=error_data.get('error', {}).get('code', 'PUBLISH_FAILED')
                    )
                    
        except Exception as e:
            self.logger.error(f"Instagram single post creation failed: {e}")
            raise PostingError(f"Instagram single post creation failed: {str(e)}", self.platform)
    
    async def _create_carousel_post(
        self, 
        instagram_account_id: str, 
        access_token: str, 
        content: PostContent
    ) -> PostResult:
        """Create an Instagram carousel post with multiple images"""
        
        try:
            async with httpx.AsyncClient() as client:
                # Create media containers for each image
                media_containers = []
                
                for i, image_url in enumerate(content.images[:10]):  # Instagram allows max 10 images in carousel
                    container_data = {
                        "image_url": image_url,
                        "is_carousel_item": True,
                        "access_token": access_token
                    }
                    
                    container_response = await client.post(
                        f"{self.config.api_base_url}/{instagram_account_id}/media",
                        data=container_data
                    )
                    
                    if container_response.status_code == 200:
                        container_id = container_response.json()["id"]
                        media_containers.append(container_id)
                    else:
                        self.logger.warning(f"Failed to create container for image {i+1}: {container_response.text}")
                
                if not media_containers:
                    return PostResult(
                        platform=self.platform,
                        status=PostStatus.FAILED,
                        error_message="Failed to create any media containers for carousel",
                        error_code="CAROUSEL_CONTAINER_FAILED"
                    )
                
                # Create carousel container
                caption_parts = []
                if content.title:
                    caption_parts.append(content.title)
                if content.description:
                    caption_parts.append(content.description)
                if content.hashtags:
                    caption_parts.append(" ".join(content.hashtags))
                
                caption = "\n\n".join(caption_parts)
                
                carousel_data = {
                    "media_type": "CAROUSEL",
                    "children": ",".join(media_containers),
                    "caption": caption[:2200],  # Instagram caption limit
                    "access_token": access_token
                }
                
                # Add location if provided
                if content.platform_specific and content.platform_specific.get("location_id"):
                    carousel_data["location_id"] = content.platform_specific["location_id"]
                
                carousel_response = await client.post(
                    f"{self.config.api_base_url}/{instagram_account_id}/media",
                    data=carousel_data
                )
                
                if carousel_response.status_code != 200:
                    error_data = carousel_response.json() if carousel_response.headers.get("content-type", "").startswith("application/json") else {}
                    return PostResult(
                        platform=self.platform,
                        status=PostStatus.FAILED,
                        error_message=f"Failed to create carousel: {error_data.get('error', {}).get('message', carousel_response.text)}",
                        error_code=error_data.get('error', {}).get('code', 'CAROUSEL_CREATION_FAILED')
                    )
                
                carousel_id = carousel_response.json()["id"]
                
                # Publish the carousel
                publish_data = {
                    "creation_id": carousel_id,
                    "access_token": access_token
                }
                
                publish_response = await client.post(
                    f"{self.config.api_base_url}/{instagram_account_id}/media_publish",
                    data=publish_data
                )
                
                if publish_response.status_code == 200:
                    result_data = publish_response.json()
                    return PostResult(
                        platform=self.platform,
                        status=PostStatus.SUCCESS,
                        post_id=result_data.get("id"),
                        url=f"https://www.instagram.com/p/{result_data.get('id')}",
                        published_at=datetime.utcnow(),
                        metadata={
                            "instagram_account_id": instagram_account_id,
                            "media_type": "CAROUSEL",
                            "media_count": len(media_containers)
                        }
                    )
                else:
                    error_data = publish_response.json() if publish_response.headers.get("content-type", "").startswith("application/json") else {}
                    return PostResult(
                        platform=self.platform,
                        status=PostStatus.FAILED,
                        error_message=f"Carousel publish failed: {error_data.get('error', {}).get('message', publish_response.text)}",
                        error_code=error_data.get('error', {}).get('code', 'CAROUSEL_PUBLISH_FAILED')
                    )
                    
        except Exception as e:
            self.logger.error(f"Instagram carousel creation failed: {e}")
            raise PostingError(f"Instagram carousel creation failed: {str(e)}", self.platform)
    
    async def get_post_metrics(self, post_id: str) -> Optional[PlatformMetrics]:
        """Get Instagram post metrics"""
        try:
            credentials = self.oauth_service.get_decrypted_credentials(self.connection)
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.api_base_url}/{post_id}/insights",
                    headers={"Authorization": f"Bearer {credentials.access_token}"},
                    params={
                        "metric": "likes,comments,shares,reach,impressions,saved"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    metrics_data = {}
                    
                    for metric in data.get("data", []):
                        metric_name = metric["name"]
                        metric_value = metric["values"][0]["value"] if metric["values"] else 0
                        metrics_data[metric_name] = metric_value
                    
                    return PlatformMetrics(
                        platform=self.platform,
                        post_id=post_id,
                        likes=metrics_data.get("likes", 0),
                        comments=metrics_data.get("comments", 0),
                        shares=metrics_data.get("shares", 0),
                        reach=metrics_data.get("reach", 0),
                        views=metrics_data.get("impressions", 0),
                        engagement_rate=self._calculate_engagement_rate(metrics_data),
                        retrieved_at=datetime.utcnow()
                    )
                    
        except Exception as e:
            self.logger.error(f"Instagram metrics retrieval failed: {e}")
            
        return None
    
    def _calculate_engagement_rate(self, metrics_data: Dict[str, Any]) -> Optional[float]:
        """Calculate engagement rate from metrics data"""
        try:
            impressions = metrics_data.get("impressions", 0)
            likes = metrics_data.get("likes", 0)
            comments = metrics_data.get("comments", 0)
            shares = metrics_data.get("shares", 0)
            saved = metrics_data.get("saved", 0)
            
            total_engagement = likes + comments + shares + saved
            
            if impressions > 0:
                return round((total_engagement / impressions) * 100, 2)
                
        except Exception:
            pass
        
        return None
    
    async def format_content(self, content: PostContent) -> PostContent:
        """Format content for Instagram"""
        formatted_content = content.model_copy()
        
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


# Factory functions for creating integrations
def create_facebook_integration(oauth_service: OAuthService, connection: PlatformConnection) -> FacebookIntegration:
    """Create a Facebook integration instance"""
    return FacebookIntegration(oauth_service, connection)


def create_instagram_integration(oauth_service: OAuthService, connection: PlatformConnection) -> InstagramIntegration:
    """Create an Instagram integration instance"""
    return InstagramIntegration(oauth_service, connection)