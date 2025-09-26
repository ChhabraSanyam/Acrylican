"""
Pinterest Business API Integration

This module provides comprehensive integration with Pinterest's Business API for creating
pins, managing boards, implementing Rich Pins functionality, and retrieving analytics.
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


class PinterestAPIError(PlatformIntegrationError):
    """Pinterest-specific API error"""
    
    def __init__(self, message: str, status_code: Optional[int] = None, error_code: Optional[str] = None):
        super().__init__(message, Platform.PINTEREST, error_code)
        self.status_code = status_code


class PinterestBoardData:
    """Data structure for Pinterest board information"""
    
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get("id")
        self.name = data.get("name")
        self.description = data.get("description")
        self.privacy = data.get("privacy")  # PUBLIC, PROTECTED, SECRET
        self.pin_count = data.get("pin_count", 0)
        self.follower_count = data.get("follower_count", 0)
        self.created_at = data.get("created_at")
        self.board_url = data.get("board_url")


class PinterestPinData:
    """Data structure for Pinterest pin information"""
    
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get("id")
        self.title = data.get("title")
        self.description = data.get("description")
        self.alt_text = data.get("alt_text")
        self.board_id = data.get("board_id")
        self.board_section_id = data.get("board_section_id")
        self.created_at = data.get("created_at")
        self.note = data.get("note")
        self.link = data.get("link")
        self.media = data.get("media", {})
        self.pin_metrics = data.get("pin_metrics", {})
        self.is_owner = data.get("is_owner", False)
        self.is_standard = data.get("is_standard", True)
        self.has_been_promoted = data.get("has_been_promoted", False)


class PinterestIntegration(APIBasedIntegration):
    """
    Comprehensive Pinterest Business API integration.
    
    Provides full functionality for:
    - OAuth 2.0 authentication
    - Pin creation with proper board management
    - Pinterest-specific image optimization
    - Rich Pins functionality for product information
    - Analytics and metrics retrieval
    """
    
    # Pinterest API constants
    API_VERSION = "v5"
    BASE_URL = "https://api.pinterest.com/v5"
    
    # Pinterest content limits and constraints
    MAX_TITLE_LENGTH = 100
    MAX_DESCRIPTION_LENGTH = 500
    MAX_ALT_TEXT_LENGTH = 500
    MAX_BOARDS_PER_USER = 2000
    MAX_PINS_PER_BOARD = 200000
    
    # Pinterest image requirements
    MIN_IMAGE_WIDTH = 236
    MIN_IMAGE_HEIGHT = 236
    MAX_IMAGE_SIZE_MB = 32
    RECOMMENDED_ASPECT_RATIOS = ["2:3", "1:1", "3:4", "4:5", "1:2.1"]
    
    # Rich Pins types
    RICH_PIN_TYPES = {
        "product": "product",
        "recipe": "recipe", 
        "article": "article",
        "app": "app"
    }
    
    def __init__(self, oauth_service: OAuthService, connection: PlatformConnection):
        config = PlatformConfig(
            platform=Platform.PINTEREST,
            integration_type=IntegrationType.API,
            auth_method=AuthenticationMethod.OAUTH2,
            api_base_url=self.BASE_URL,
            api_version=self.API_VERSION,
            max_title_length=self.MAX_TITLE_LENGTH,
            max_description_length=self.MAX_DESCRIPTION_LENGTH,
            max_hashtags=20,  # Pinterest doesn't have a strict hashtag limit, but 20 is reasonable
            supported_image_formats=["jpg", "jpeg", "png", "gif", "webp"],
            rate_limit_per_minute=1000,  # Pinterest rate limit (1000 requests per hour)
            max_retries=3,
            retry_delay_seconds=2,
            custom_settings={
                "supports_rich_pins": True,
                "supports_video": True,
                "supports_story_pins": True,
                "min_image_width": self.MIN_IMAGE_WIDTH,
                "min_image_height": self.MIN_IMAGE_HEIGHT,
                "max_image_size_mb": self.MAX_IMAGE_SIZE_MB,
                "recommended_aspect_ratios": self.RECOMMENDED_ASPECT_RATIOS
            }
        )
        super().__init__(config)
        self.oauth_service = oauth_service
        self.connection = connection
        self._user_data: Optional[Dict[str, Any]] = None
        self._boards_cache: List[PinterestBoardData] = []
        self._cache_expiry: Optional[datetime] = None
    
    async def authenticate(self, credentials: PlatformCredentials) -> bool:
        """
        Authenticate with Pinterest using OAuth 2.0.
        
        Args:
            credentials: OAuth credentials
            
        Returns:
            True if authentication successful
        """
        try:
            # Validate connection by making a test API call
            return await self.validate_connection()
        except Exception as e:
            self.logger.error(f"Pinterest authentication failed: {e}")
            return False
    
    async def validate_connection(self) -> bool:
        """
        Validate Pinterest connection by testing API access.
        
        Returns:
            True if connection is valid
        """
        if not self.connection:
            return False
        
        try:
            credentials = self.oauth_service.get_decrypted_credentials(self.connection)
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.api_base_url}/user_account",
                    headers=self._get_auth_headers(credentials.access_token),
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    # Cache user data for later use
                    self._user_data = response.json()
                    return True
                else:
                    self.logger.warning(f"Pinterest connection validation failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Pinterest connection validation failed: {e}")
            return False
    
    async def post_content(self, content: PostContent) -> PostResult:
        """
        Create a new Pinterest pin from content.
        
        Args:
            content: Content to post as pin
            
        Returns:
            PostResult with pin creation status
        """
        try:
            credentials = self.oauth_service.get_decrypted_credentials(self.connection)
            
            # Ensure we have user data
            if not self._user_data:
                await self.validate_connection()
            
            # Format content for Pinterest
            formatted_content = await self.format_content(content)
            
            # Validate content
            validation_errors = await self._validate_pin_content(formatted_content)
            if validation_errors:
                return PostResult(
                    platform=self.platform,
                    status=PostStatus.FAILED,
                    error_message=f"Content validation failed: {'; '.join(validation_errors)}",
                    error_code="CONTENT_VALIDATION_FAILED"
                )
            
            # Get or create appropriate board
            board_id = await self._get_target_board(credentials.access_token, formatted_content)
            if not board_id:
                return PostResult(
                    platform=self.platform,
                    status=PostStatus.FAILED,
                    error_message="Unable to find or create appropriate board",
                    error_code="BOARD_UNAVAILABLE"
                )
            
            # Create the pin
            pin_data = await self._prepare_pin_data(formatted_content, board_id)
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.config.api_base_url}/pins",
                    headers=self._get_auth_headers(credentials.access_token),
                    json=pin_data,
                    timeout=60.0
                )
                
                if response.status_code == 201:
                    result_data = response.json()
                    pin_id = result_data["id"]
                    
                    # Set up Rich Pins if product data is provided
                    rich_pin_result = None
                    if formatted_content.product_data:
                        rich_pin_result = await self._setup_rich_pin(
                            credentials.access_token,
                            pin_id,
                            formatted_content
                        )
                    
                    return PostResult(
                        platform=self.platform,
                        status=PostStatus.SUCCESS,
                        post_id=pin_id,
                        url=result_data.get("url"),
                        published_at=datetime.utcnow(),
                        metadata={
                            "board_id": board_id,
                            "pin_type": "standard",
                            "rich_pin_enabled": rich_pin_result is not None,
                            "image_optimized": True
                        }
                    )
                else:
                    error_data = response.json() if response.content else {}
                    return PostResult(
                        platform=self.platform,
                        status=PostStatus.FAILED,
                        error_message=f"Pinterest pin creation failed: {error_data.get('message', response.text)}",
                        error_code=error_data.get('code', 'PIN_CREATION_FAILED')
                    )
                    
        except Exception as e:
            self.logger.error(f"Pinterest pin creation failed: {e}")
            return PostResult(
                platform=self.platform,
                status=PostStatus.FAILED,
                error_message=str(e),
                error_code="POSTING_EXCEPTION"
            )
    
    async def get_post_metrics(self, post_id: str) -> Optional[PlatformMetrics]:
        """
        Get metrics for a Pinterest pin.
        
        Args:
            post_id: Pinterest pin ID
            
        Returns:
            PlatformMetrics with pin performance data
        """
        try:
            credentials = self.oauth_service.get_decrypted_credentials(self.connection)
            
            async with httpx.AsyncClient() as client:
                # Get pin analytics
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=30)
                
                analytics_response = await client.get(
                    f"{self.config.api_base_url}/pins/{post_id}/analytics",
                    headers=self._get_auth_headers(credentials.access_token),
                    params={
                        "start_date": start_date.strftime("%Y-%m-%d"),
                        "end_date": end_date.strftime("%Y-%m-%d"),
                        "metric_types": "IMPRESSION,OUTBOUND_CLICK,PIN_CLICK,SAVE"
                    },
                    timeout=30.0
                )
                
                if analytics_response.status_code == 200:
                    analytics_data = analytics_response.json()
                    
                    # Extract metrics from the response
                    metrics = {}
                    for metric_type, data in analytics_data.get("all_time", {}).items():
                        if isinstance(data, list) and data:
                            metrics[metric_type] = data[0].get("value", 0)
                        elif isinstance(data, dict):
                            metrics[metric_type] = data.get("value", 0)
                    
                    return PlatformMetrics(
                        platform=self.platform,
                        post_id=post_id,
                        views=metrics.get("IMPRESSION", 0),
                        shares=metrics.get("SAVE", 0),  # Pinterest saves are like shares
                        comments=0,  # Pinterest doesn't provide comment metrics in basic analytics
                        likes=0,  # Pinterest doesn't have likes, uses saves instead
                        reach=metrics.get("IMPRESSION", 0),  # Use impressions as reach
                        retrieved_at=datetime.utcnow()
                    )
                else:
                    self.logger.warning(f"Failed to get Pinterest pin analytics: {analytics_response.status_code}")
                    
        except Exception as e:
            self.logger.error(f"Pinterest metrics retrieval failed: {e}")
            
        return None
    
    async def format_content(self, content: PostContent) -> PostContent:
        """
        Format content according to Pinterest requirements.
        
        Args:
            content: Original content
            
        Returns:
            Formatted content for Pinterest
        """
        formatted_content = content.model_copy()
        
        # Format title (max 100 characters)
        if len(formatted_content.title) > self.MAX_TITLE_LENGTH:
            formatted_content.title = formatted_content.title[:97] + "..."
        
        # Format description with hashtags (max 500 characters total)
        description_parts = [formatted_content.description]
        
        # Add hashtags to description (Pinterest doesn't have separate hashtag field)
        if formatted_content.hashtags:
            hashtag_text = " ".join(f"#{tag.lstrip('#')}" for tag in formatted_content.hashtags[:20])
            description_parts.append(hashtag_text)
        
        combined_description = "\n\n".join(description_parts)
        if len(combined_description) > self.MAX_DESCRIPTION_LENGTH:
            # Truncate description to fit hashtags
            available_space = self.MAX_DESCRIPTION_LENGTH - len(hashtag_text) - 4  # 4 for "\n\n"
            if available_space > 0:
                truncated_desc = formatted_content.description[:available_space-3] + "..."
                formatted_content.description = f"{truncated_desc}\n\n{hashtag_text}"
            else:
                formatted_content.description = combined_description[:497] + "..."
        else:
            formatted_content.description = combined_description
        
        # Clear hashtags since they're now in description
        formatted_content.hashtags = []
        
        # Optimize images for Pinterest (ensure minimum dimensions)
        formatted_content.images = await self._optimize_images_for_pinterest(formatted_content.images)
        
        return formatted_content
    
    async def create_board(
        self,
        name: str,
        description: str = "",
        privacy: str = "PUBLIC"
    ) -> Optional[PinterestBoardData]:
        """
        Create a new Pinterest board.
        
        Args:
            name: Board name
            description: Board description
            privacy: Board privacy (PUBLIC, PROTECTED, SECRET)
            
        Returns:
            PinterestBoardData object or None if creation failed
        """
        try:
            credentials = self.oauth_service.get_decrypted_credentials(self.connection)
            
            board_data = {
                "name": name[:180],  # Pinterest board name limit
                "description": description[:500],  # Pinterest board description limit
                "privacy": privacy
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.config.api_base_url}/boards",
                    headers=self._get_auth_headers(credentials.access_token),
                    json=board_data,
                    timeout=30.0
                )
                
                if response.status_code == 201:
                    result_data = response.json()
                    board = PinterestBoardData(result_data)
                    
                    # Invalidate boards cache
                    self._cache_expiry = None
                    
                    self.logger.info(f"Created Pinterest board: {name}")
                    return board
                else:
                    self.logger.error(f"Failed to create Pinterest board: {response.status_code}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"Pinterest board creation failed: {e}")
            return None
    
    async def get_user_boards(self, refresh_cache: bool = False) -> List[PinterestBoardData]:
        """
        Get user's Pinterest boards with caching.
        
        Args:
            refresh_cache: Force refresh of cached boards
            
        Returns:
            List of PinterestBoardData objects
        """
        current_time = datetime.utcnow()
        
        # Return cached boards if still valid (cache for 10 minutes)
        if (not refresh_cache and self._boards_cache and self._cache_expiry and 
            current_time < self._cache_expiry):
            return self._boards_cache
        
        try:
            credentials = self.oauth_service.get_decrypted_credentials(self.connection)
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.api_base_url}/boards",
                    headers=self._get_auth_headers(credentials.access_token),
                    params={
                        "page_size": 100,  # Get up to 100 boards
                        "privacy": "all"
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    boards = [PinterestBoardData(board) for board in data.get("items", [])]
                    
                    # Cache the results
                    self._boards_cache = boards
                    self._cache_expiry = current_time + timedelta(minutes=10)
                    
                    return boards
                else:
                    self.logger.error(f"Failed to get Pinterest boards: {response.status_code}")
                    return []
                    
        except Exception as e:
            self.logger.error(f"Error getting Pinterest boards: {e}")
            return []
    
    async def update_pin(
        self,
        pin_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        alt_text: Optional[str] = None,
        board_id: Optional[str] = None,
        note: Optional[str] = None
    ) -> PostResult:
        """
        Update an existing Pinterest pin.
        
        Args:
            pin_id: Pinterest pin ID to update
            title: New title (optional)
            description: New description (optional)
            alt_text: New alt text (optional)
            board_id: New board ID to move pin to (optional)
            note: New note (optional)
            
        Returns:
            PostResult with update status
        """
        try:
            credentials = self.oauth_service.get_decrypted_credentials(self.connection)
            
            # Prepare update data
            update_data = {}
            
            if title is not None:
                update_data["title"] = title[:self.MAX_TITLE_LENGTH]
            
            if description is not None:
                update_data["description"] = description[:self.MAX_DESCRIPTION_LENGTH]
            
            if alt_text is not None:
                update_data["alt_text"] = alt_text[:self.MAX_ALT_TEXT_LENGTH]
            
            if board_id is not None:
                update_data["board_id"] = board_id
            
            if note is not None:
                update_data["note"] = note[:500]  # Pinterest note limit
            
            if not update_data:
                return PostResult(
                    platform=self.platform,
                    status=PostStatus.FAILED,
                    error_message="No update data provided",
                    error_code="NO_UPDATE_DATA"
                )
            
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.config.api_base_url}/pins/{pin_id}",
                    headers=self._get_auth_headers(credentials.access_token),
                    json=update_data,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return PostResult(
                        platform=self.platform,
                        status=PostStatus.SUCCESS,
                        post_id=pin_id,
                        published_at=datetime.utcnow(),
                        metadata={"action": "update", "updated_fields": list(update_data.keys())}
                    )
                else:
                    error_data = response.json() if response.content else {}
                    return PostResult(
                        platform=self.platform,
                        status=PostStatus.FAILED,
                        error_message=f"Pin update failed: {error_data.get('message', response.text)}",
                        error_code=error_data.get('code', 'PIN_UPDATE_FAILED')
                    )
                    
        except Exception as e:
            self.logger.error(f"Pinterest pin update failed: {e}")
            return PostResult(
                platform=self.platform,
                status=PostStatus.FAILED,
                error_message=str(e),
                error_code="UPDATE_EXCEPTION"
            )
    
    def _get_auth_headers(self, access_token: str) -> Dict[str, str]:
        """Get authentication headers for Pinterest API requests"""
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    async def _validate_pin_content(self, content: PostContent) -> List[str]:
        """Validate pin content against Pinterest requirements"""
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
        
        # Image validation
        if not content.images:
            errors.append("At least one image is required")
        elif len(content.images) > 1:
            errors.append("Pinterest pins support only one image per pin")
        
        return errors
    
    async def _get_target_board(self, access_token: str, content: PostContent) -> Optional[str]:
        """Get or create appropriate board for the pin"""
        try:
            # Check if specific board is requested
            if content.platform_specific and content.platform_specific.get("board_id"):
                return content.platform_specific["board_id"]
            
            # Get user's boards
            boards = await self.get_user_boards()
            
            if not boards:
                # Create a default board if none exist
                default_board = await self.create_board(
                    name="My Products",
                    description="Products from my artisan business",
                    privacy="PUBLIC"
                )
                return default_board.id if default_board else None
            
            # Try to find an appropriate board based on content
            board_name_hint = None
            if content.product_data and content.product_data.get("category"):
                board_name_hint = content.product_data["category"].lower()
            
            # Look for matching board
            if board_name_hint:
                for board in boards:
                    if board_name_hint in board.name.lower():
                        return board.id
            
            # Use the first public board
            for board in boards:
                if board.privacy == "PUBLIC":
                    return board.id
            
            # Use any board as fallback
            return boards[0].id if boards else None
            
        except Exception as e:
            self.logger.error(f"Error getting target board: {e}")
            return None
    
    async def _prepare_pin_data(self, content: PostContent, board_id: str) -> Dict[str, Any]:
        """Prepare pin data for Pinterest API"""
        pin_data = {
            "title": content.title,
            "description": content.description,
            "board_id": board_id,
            "media_source": {
                "source_type": "image_url",
                "url": content.images[0]
            }
        }
        
        # Add alt text if available
        if content.platform_specific and content.platform_specific.get("alt_text"):
            pin_data["alt_text"] = content.platform_specific["alt_text"][:self.MAX_ALT_TEXT_LENGTH]
        
        # Add link if available
        if content.platform_specific and content.platform_specific.get("link"):
            pin_data["link"] = content.platform_specific["link"]
        elif content.product_data and content.product_data.get("url"):
            pin_data["link"] = content.product_data["url"]
        
        # Add note if available
        if content.platform_specific and content.platform_specific.get("note"):
            pin_data["note"] = content.platform_specific["note"][:500]
        
        return pin_data
    
    async def _setup_rich_pin(
        self,
        access_token: str,
        pin_id: str,
        content: PostContent
    ) -> Optional[Dict[str, Any]]:
        """
        Set up Rich Pin functionality for product information.
        
        Note: Rich Pins require domain verification and meta tags on the linked website.
        This method prepares the pin for Rich Pin functionality.
        """
        try:
            if not content.product_data:
                return None
            
            # Rich Pins are primarily set up through meta tags on the destination website
            # The API doesn't directly create Rich Pins, but we can ensure the pin has
            # the necessary product information in its description and link
            
            rich_pin_data = {
                "type": "product",
                "product_data": {
                    "price": content.product_data.get("price"),
                    "currency": content.product_data.get("currency", "INR"),
                    "availability": content.product_data.get("availability", "in stock"),
                    "brand": content.product_data.get("brand"),
                    "category": content.product_data.get("category")
                }
            }
            
            # For Rich Pins to work, the destination URL needs proper meta tags
            # This is handled on the website side, not through the API
            
            self.logger.info(f"Rich Pin data prepared for pin {pin_id}")
            return rich_pin_data
            
        except Exception as e:
            self.logger.error(f"Rich Pin setup failed: {e}")
            return None
    
    async def _optimize_images_for_pinterest(self, image_urls: List[str]) -> List[str]:
        """
        Optimize images for Pinterest requirements.
        
        Note: This is a placeholder for image optimization logic.
        In a real implementation, you would:
        1. Check image dimensions
        2. Resize if necessary
        3. Optimize for Pinterest's preferred aspect ratios
        4. Ensure images meet minimum size requirements
        """
        # For now, just return the original URLs
        # In a full implementation, you would process each image
        optimized_urls = []
        
        for url in image_urls:
            # Placeholder for image optimization
            # You could integrate with your image processing service here
            optimized_urls.append(url)
        
        return optimized_urls
    
    async def get_pin_analytics_detailed(
        self,
        pin_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed analytics for a Pinterest pin.
        
        Args:
            pin_id: Pinterest pin ID
            start_date: Start date for analytics (defaults to 30 days ago)
            end_date: End date for analytics (defaults to today)
            
        Returns:
            Detailed analytics data or None if unavailable
        """
        try:
            credentials = self.oauth_service.get_decrypted_credentials(self.connection)
            
            if not start_date:
                start_date = datetime.utcnow() - timedelta(days=30)
            if not end_date:
                end_date = datetime.utcnow()
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.api_base_url}/pins/{pin_id}/analytics",
                    headers=self._get_auth_headers(credentials.access_token),
                    params={
                        "start_date": start_date.strftime("%Y-%m-%d"),
                        "end_date": end_date.strftime("%Y-%m-%d"),
                        "metric_types": "IMPRESSION,OUTBOUND_CLICK,PIN_CLICK,SAVE,SAVE_RATE,CLOSEUP,CLOSEUP_RATE"
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    self.logger.warning(f"Failed to get detailed pin analytics: {response.status_code}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"Detailed analytics retrieval failed: {e}")
            return None
    
    async def search_pins(
        self,
        query: str,
        limit: int = 25
    ) -> List[PinterestPinData]:
        """
        Search for pins (for inspiration or competitive analysis).
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of PinterestPinData objects
        """
        try:
            credentials = self.oauth_service.get_decrypted_credentials(self.connection)
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.api_base_url}/search/pins",
                    headers=self._get_auth_headers(credentials.access_token),
                    params={
                        "query": query,
                        "limit": min(limit, 50)  # Pinterest API limit
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return [PinterestPinData(pin) for pin in data.get("items", [])]
                else:
                    self.logger.warning(f"Pin search failed: {response.status_code}")
                    return []
                    
        except Exception as e:
            self.logger.error(f"Pin search failed: {e}")
            return []