"""
Unified Platform Service

This module provides a high-level service interface for managing platform
integrations, combining the registry, configuration, and integration components
into a unified API.
"""

from typing import Dict, List, Optional, Any, Union
import asyncio
from datetime import datetime
import logging

from .platform_integration import (
    BasePlatformIntegration,
    Platform,
    PostContent,
    PostResult,
    PlatformMetrics,
    PlatformCredentials,
    PostStatus,
    PlatformIntegrationError,
    AuthenticationError,
    PostingError
)
from .platform_registry import PlatformRegistry, get_platform_registry
from .platform_config import PlatformConfigManager, get_config_manager
from .oauth_service import get_oauth_service, OAuthService
from .platform_oauth_integrations import create_oauth_integration
from ..models import PlatformConnection
from ..database import get_db

logger = logging.getLogger(__name__)


class PlatformService:
    """
    Unified service for managing platform integrations.
    
    This service provides a high-level interface for all platform-related
    operations, including authentication, posting, metrics collection,
    and platform management.
    """
    
    def __init__(
        self,
        registry: Optional[PlatformRegistry] = None,
        config_manager: Optional[PlatformConfigManager] = None,
        oauth_service: Optional[OAuthService] = None
    ):
        self.registry = registry or get_platform_registry()
        self.config_manager = config_manager or get_config_manager()
        self.oauth_service = oauth_service or get_oauth_service()
        self.logger = logging.getLogger(__name__)
    
    def _get_oauth_integration(self, platform: Platform, user_id: str) -> Optional[BasePlatformIntegration]:
        """
        Get OAuth-enabled platform integration for a user.
        
        Args:
            platform: Platform to get integration for
            user_id: User identifier
            
        Returns:
            Platform integration instance or None
        """
        # Check if platform supports OAuth
        oauth_platforms = [Platform.FACEBOOK, Platform.INSTAGRAM, Platform.ETSY, Platform.PINTEREST, Platform.SHOPIFY]
        
        if platform not in oauth_platforms:
            return None
        
        # Get user's platform connection
        db = next(get_db())
        try:
            connection = db.query(PlatformConnection).filter(
                PlatformConnection.user_id == user_id,
                PlatformConnection.platform == platform.value,
                PlatformConnection.is_active == True
            ).first()
            
            if not connection:
                return None
            
            # Create OAuth integration
            return create_oauth_integration(platform, self.oauth_service, connection)
            
        except Exception as e:
            self.logger.error(f"Failed to get OAuth integration for {platform.value}: {e}")
            return None
        finally:
            db.close()

    async def authenticate_platform(
        self,
        platform: Platform,
        user_id: str,
        credentials: PlatformCredentials
    ) -> bool:
        """
        Authenticate with a platform for a specific user.
        
        Args:
            platform: Platform to authenticate with
            user_id: User identifier
            credentials: Authentication credentials
            
        Returns:
            True if authentication successful, False otherwise
            
        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            # Try OAuth integration
            oauth_integration = self._get_oauth_integration(platform, user_id)
            if oauth_integration:
                success = await oauth_integration.authenticate(credentials)
                
                if success:
                    self.logger.info(f"Successfully authenticated {user_id} with {platform.value} via OAuth")
                else:
                    self.logger.warning(f"OAuth authentication failed for {user_id} with {platform.value}")
                
                return success
            
            # Fall back to registry integration
            integration = self.registry.get_platform_integration(platform, user_id)
            if not integration:
                raise AuthenticationError(
                    f"Platform {platform.value} is not available",
                    platform
                )
            
            success = await integration.authenticate(credentials)
            
            if success:
                self.logger.info(f"Successfully authenticated {user_id} with {platform.value}")
            else:
                self.logger.warning(f"Authentication failed for {user_id} with {platform.value}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Authentication error for {platform.value}: {e}")
            raise AuthenticationError(
                f"Failed to authenticate with {platform.value}: {str(e)}",
                platform
            )
    
    async def validate_platform_connection(
        self,
        platform: Platform,
        user_id: str
    ) -> bool:
        """
        Validate that a platform connection is still active.
        
        Args:
            platform: Platform to validate
            user_id: User identifier
            
        Returns:
            True if connection is valid, False otherwise
        """
        try:
            # Try OAuth integration
            oauth_integration = self._get_oauth_integration(platform, user_id)
            if oauth_integration:
                return await oauth_integration.validate_connection()
            
            # Fall back to registry integration
            integration = self.registry.get_platform_integration(platform, user_id)
            if not integration:
                return False
            
            return await integration.validate_connection()
            
        except Exception as e:
            self.logger.error(f"Connection validation error for {platform.value}: {e}")
            return False
    
    async def post_to_platform(
        self,
        platform: Platform,
        user_id: str,
        content: PostContent
    ) -> PostResult:
        """
        Post content to a specific platform.
        
        Args:
            platform: Platform to post to
            user_id: User identifier
            content: Content to post
            
        Returns:
            Result of the post operation
            
        Raises:
            PostingError: If posting fails
        """
        try:
            # Try OAuth integration
            oauth_integration = self._get_oauth_integration(platform, user_id)
            if oauth_integration:
                # Format content for the specific platform
                formatted_content = await oauth_integration.format_content(content)
                
                # Post the content
                result = await oauth_integration.post_content(formatted_content)
                
                self.logger.info(
                    f"Posted to {platform.value} for user {user_id} via OAuth: {result.status.value}"
                )
                
                return result
            
            # Fall back to registry integration
            integration = self.registry.get_platform_integration(platform, user_id)
            if not integration:
                return PostResult(
                    platform=platform,
                    status=PostStatus.FAILED,
                    error_message=f"Platform {platform.value} is not available",
                    error_code="PLATFORM_NOT_AVAILABLE"
                )
            
            # Format content for the specific platform
            formatted_content = await integration.format_content(content)
            
            # Post the content
            result = await integration.post_content(formatted_content)
            
            self.logger.info(
                f"Posted to {platform.value} for user {user_id}: {result.status.value}"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Posting error for {platform.value}: {e}")
            return PostResult(
                platform=platform,
                status=PostStatus.FAILED,
                error_message=str(e),
                error_code="POSTING_ERROR"
            )
    
    async def post_to_multiple_platforms(
        self,
        platforms: List[Platform],
        user_id: str,
        content: PostContent
    ) -> List[PostResult]:
        """
        Post content to multiple platforms simultaneously.
        
        Args:
            platforms: List of platforms to post to
            user_id: User identifier
            content: Content to post
            
        Returns:
            List of post results for each platform
        """
        tasks = []
        
        for platform in platforms:
            task = self.post_to_platform(platform, user_id, content)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to failed results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(PostResult(
                    platform=platforms[i],
                    status=PostStatus.FAILED,
                    error_message=str(result),
                    error_code="EXCEPTION_OCCURRED"
                ))
            else:
                final_results.append(result)
        
        # Log summary
        successful = sum(1 for r in final_results if r.status == PostStatus.SUCCESS)
        self.logger.info(
            f"Posted to {successful}/{len(platforms)} platforms for user {user_id}"
        )
        
        return final_results
    
    async def get_platform_metrics(
        self,
        platform: Platform,
        user_id: str,
        post_id: str
    ) -> Optional[PlatformMetrics]:
        """
        Get metrics for a specific post on a platform.
        
        Args:
            platform: Platform to get metrics from
            user_id: User identifier
            post_id: Platform-specific post identifier
            
        Returns:
            Platform metrics or None if not available
        """
        try:
            integration = self.registry.get_platform_integration(platform, user_id)
            if not integration:
                return None
            
            metrics = await integration.get_post_metrics(post_id)
            
            if metrics:
                self.logger.debug(f"Retrieved metrics for post {post_id} on {platform.value}")
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Metrics retrieval error for {platform.value}: {e}")
            return None
    
    async def get_metrics_for_multiple_posts(
        self,
        post_data: List[Dict[str, Any]],  # [{"platform": Platform, "user_id": str, "post_id": str}]
    ) -> List[Optional[PlatformMetrics]]:
        """
        Get metrics for multiple posts across platforms.
        
        Args:
            post_data: List of dictionaries containing platform, user_id, and post_id
            
        Returns:
            List of metrics (None for failed retrievals)
        """
        tasks = []
        
        for data in post_data:
            task = self.get_platform_metrics(
                data["platform"],
                data["user_id"],
                data["post_id"]
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to None
        final_results = []
        for result in results:
            if isinstance(result, Exception):
                final_results.append(None)
            else:
                final_results.append(result)
        
        return final_results
    
    def get_available_platforms(self) -> List[Platform]:
        """
        Get list of all available platforms.
        
        Returns:
            List of available platforms
        """
        return self.registry.get_available_platforms()
    
    def get_enabled_platforms(self) -> List[Platform]:
        """
        Get list of enabled platforms.
        
        Returns:
            List of enabled platforms
        """
        return self.config_manager.get_enabled_platforms()
    
    def get_platform_info(self, platform: Platform) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific platform.
        
        Args:
            platform: Platform to get info for
            
        Returns:
            Platform information dictionary or None
        """
        config = self.config_manager.get_config(platform)
        if not config:
            return None
        
        return {
            "platform": platform.value,
            "integration_type": config.integration_type.value,
            "auth_method": config.auth_method.value,
            "enabled": config.enabled,
            "rate_limit_per_minute": config.rate_limit_per_minute,
            "max_title_length": config.max_title_length,
            "max_description_length": config.max_description_length,
            "max_hashtags": config.max_hashtags,
            "supported_image_formats": config.supported_image_formats,
            "max_retries": config.max_retries,
            "custom_settings": config.custom_settings
        }
    
    def get_all_platform_info(self) -> Dict[str, Any]:
        """
        Get information about all platforms.
        
        Returns:
            Dictionary containing information for all platforms
        """
        all_info = {}
        
        for platform in Platform:
            info = self.get_platform_info(platform)
            if info:
                all_info[platform.value] = info
        
        return all_info
    
    async def disconnect_platform(
        self,
        platform: Platform,
        user_id: str
    ) -> bool:
        """
        Disconnect from a platform for a specific user.
        
        Args:
            platform: Platform to disconnect from
            user_id: User identifier
            
        Returns:
            True if disconnection successful, False otherwise
        """
        try:
            # Handle platforms
            integration = self.registry.get_platform_integration(platform, user_id)
            if not integration:
                return True  # Already disconnected
            
            success = await integration.disconnect()
            
            if success:
                self.logger.info(f"Disconnected {user_id} from {platform.value}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Disconnection error for {platform.value}: {e}")
            return False
    
    async def disconnect_all_platforms(self, user_id: str) -> Dict[Platform, bool]:
        """
        Disconnect from all platforms for a specific user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary mapping platforms to disconnection success status
        """
        available_platforms = self.get_available_platforms()
        results = {}
        
        for platform in available_platforms:
            results[platform] = await self.disconnect_platform(platform, user_id)
        
        # Clean up registry instances
        self.registry.cleanup_user_instances(user_id)
        
        successful_disconnects = sum(1 for success in results.values() if success)
        self.logger.info(
            f"Disconnected from {successful_disconnects}/{len(available_platforms)} "
            f"platforms for user {user_id}"
        )
        
        return results
    
    def validate_content_for_platform(
        self,
        platform: Platform,
        content: PostContent
    ) -> List[str]:
        """
        Validate content against platform-specific requirements.
        
        Args:
            platform: Platform to validate for
            content: Content to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        config = self.config_manager.get_config(platform)
        if not config:
            return [f"Platform {platform.value} is not configured"]
        
        errors = []
        
        # Title validation
        if config.max_title_length and len(content.title) > config.max_title_length:
            errors.append(
                f"Title exceeds maximum length of {config.max_title_length} characters"
            )
        
        # Description validation
        if config.max_description_length and len(content.description) > config.max_description_length:
            errors.append(
                f"Description exceeds maximum length of {config.max_description_length} characters"
            )
        
        # Hashtags validation
        if config.max_hashtags and len(content.hashtags) > config.max_hashtags:
            errors.append(
                f"Number of hashtags exceeds maximum of {config.max_hashtags}"
            )
        
        # Image format validation
        if config.supported_image_formats:
            for image_url in content.images:
                # Extract file extension from URL
                extension = image_url.split('.')[-1].lower()
                if extension not in config.supported_image_formats:
                    errors.append(
                        f"Image format '{extension}' is not supported. "
                        f"Supported formats: {', '.join(config.supported_image_formats)}"
                    )
        
        # Platform-specific validation
        if config.custom_settings:
            # Facebook Marketplace specific validation
            if platform == Platform.FACEBOOK_MARKETPLACE:
                if not content.product_data:
                    errors.append("Product data is required for Facebook Marketplace")
                elif not content.product_data.get("price"):
                    errors.append("Price is required for Facebook Marketplace")
        
        return errors


# Global service instance
platform_service = PlatformService()


def get_platform_service() -> PlatformService:
    """
    Get the global platform service instance.
    
    Returns:
        Global PlatformService instance
    """
    return platform_service