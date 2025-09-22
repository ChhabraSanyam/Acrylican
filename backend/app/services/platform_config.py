"""
Platform Configuration System

This module provides configuration management for platform integrations,
including default configurations, validation, and dynamic updates.
"""

from typing import Dict, List, Optional, Any, Union
import json
from pathlib import Path
from pydantic import BaseModel, validator
import logging

from .platform_integration import (
    Platform,
    IntegrationType,
    AuthenticationMethod,
    PlatformConfig
)

logger = logging.getLogger(__name__)


class PlatformConfigManager:
    """
    Manager for platform configurations.
    
    Handles loading, validation, and management of platform-specific
    configurations from various sources (files, database, environment).
    """
    
    def __init__(self):
        self._configs: Dict[Platform, PlatformConfig] = {}
        self._default_configs: Dict[Platform, PlatformConfig] = {}
        self._load_default_configs()
    
    def _load_default_configs(self) -> None:
        """Load default configurations for all supported platforms"""
        
        # Facebook configuration
        self._default_configs[Platform.FACEBOOK] = PlatformConfig(
            platform=Platform.FACEBOOK,
            integration_type=IntegrationType.API,
            auth_method=AuthenticationMethod.OAUTH2,
            enabled=True,
            api_base_url="https://graph.facebook.com",
            api_version="v18.0",
            rate_limit_per_minute=200,
            max_title_length=255,
            max_description_length=63206,
            max_hashtags=30,
            supported_image_formats=["jpg", "jpeg", "png", "gif", "webp"],
            max_retries=3,
            retry_delay_seconds=5,
            custom_settings={
                "page_access_required": True,
                "supports_scheduling": True,
                "supports_video": True,
                "max_images_per_post": 10
            }
        )
        
        # Instagram configuration
        self._default_configs[Platform.INSTAGRAM] = PlatformConfig(
            platform=Platform.INSTAGRAM,
            integration_type=IntegrationType.API,
            auth_method=AuthenticationMethod.OAUTH2,
            enabled=True,
            api_base_url="https://graph.facebook.com",
            api_version="v18.0",
            rate_limit_per_minute=200,
            max_title_length=2200,
            max_description_length=2200,
            max_hashtags=30,
            supported_image_formats=["jpg", "jpeg", "png"],
            max_retries=3,
            retry_delay_seconds=5,
            custom_settings={
                "business_account_required": True,
                "supports_carousel": True,
                "supports_stories": True,
                "aspect_ratio_requirements": {
                    "min": 0.8,
                    "max": 1.91
                }
            }
        )
        
        # Facebook Marketplace configuration
        self._default_configs[Platform.FACEBOOK_MARKETPLACE] = PlatformConfig(
            platform=Platform.FACEBOOK_MARKETPLACE,
            integration_type=IntegrationType.API,
            auth_method=AuthenticationMethod.OAUTH2,
            enabled=True,
            api_base_url="https://graph.facebook.com",
            api_version="v18.0",
            rate_limit_per_minute=100,
            max_title_length=100,
            max_description_length=9999,
            max_hashtags=0,  # Marketplace doesn't use hashtags
            supported_image_formats=["jpg", "jpeg", "png"],
            max_retries=3,
            retry_delay_seconds=10,
            custom_settings={
                "requires_price": True,
                "requires_category": True,
                "requires_location": True,
                "max_images": 10,
                "commerce_account_required": True
            }
        )
        
        # Etsy configuration
        self._default_configs[Platform.ETSY] = PlatformConfig(
            platform=Platform.ETSY,
            integration_type=IntegrationType.API,
            auth_method=AuthenticationMethod.OAUTH2,
            enabled=True,
            api_base_url="https://openapi.etsy.com",
            api_version="v3",
            rate_limit_per_minute=100,
            max_title_length=140,
            max_description_length=13000,
            max_hashtags=13,
            supported_image_formats=["jpg", "jpeg", "png", "gif"],
            max_retries=3,
            retry_delay_seconds=5,
            custom_settings={
                "requires_shop": True,
                "supports_variations": True,
                "max_images": 10,
                "requires_shipping_profile": True,
                "supports_digital_products": True
            }
        )
        
        # Pinterest configuration
        self._default_configs[Platform.PINTEREST] = PlatformConfig(
            platform=Platform.PINTEREST,
            integration_type=IntegrationType.API,
            auth_method=AuthenticationMethod.OAUTH2,
            enabled=True,
            api_base_url="https://api.pinterest.com",
            api_version="v5",
            rate_limit_per_minute=1000,
            max_title_length=100,
            max_description_length=500,
            max_hashtags=20,
            supported_image_formats=["jpg", "jpeg", "png"],
            max_retries=3,
            retry_delay_seconds=5,
            custom_settings={
                "business_account_required": True,
                "supports_rich_pins": True,
                "requires_board": True,
                "min_image_size": {"width": 236, "height": 236},
                "max_image_size": {"width": 2340, "height": 2340}
            }
        )
        
        # Shopify configuration
        self._default_configs[Platform.SHOPIFY] = PlatformConfig(
            platform=Platform.SHOPIFY,
            integration_type=IntegrationType.API,
            auth_method=AuthenticationMethod.OAUTH2,
            enabled=True,
            api_base_url="https://{shop}.myshopify.com/admin/api",
            api_version="2023-10",
            rate_limit_per_minute=40,
            max_title_length=255,
            max_description_length=65535,
            max_hashtags=250,  # Via tags
            supported_image_formats=["jpg", "jpeg", "png", "gif", "webp"],
            max_retries=3,
            retry_delay_seconds=10,
            custom_settings={
                "requires_shop_domain": True,
                "supports_variants": True,
                "supports_inventory_tracking": True,
                "max_images": 250,
                "supports_seo": True
            }
        )



    
    def get_config(self, platform: Platform) -> Optional[PlatformConfig]:
        """
        Get configuration for a platform.
        
        Args:
            platform: Platform to get config for
            
        Returns:
            Platform configuration or None if not found
        """
        # Return custom config if available, otherwise default
        return self._configs.get(platform, self._default_configs.get(platform))
    
    def get_default_config(self, platform: Platform) -> Optional[PlatformConfig]:
        """
        Get default configuration for a platform.
        
        Args:
            platform: Platform to get default config for
            
        Returns:
            Default platform configuration or None if not found
        """
        return self._default_configs.get(platform)
    
    def set_config(self, platform: Platform, config: PlatformConfig) -> None:
        """
        Set custom configuration for a platform.
        
        Args:
            platform: Platform to set config for
            config: Configuration to set
        """
        if config.platform != platform:
            raise ValueError(f"Config platform {config.platform} doesn't match {platform}")
        
        self._configs[platform] = config
        logger.info(f"Updated configuration for platform: {platform.value}")
    
    def reset_to_default(self, platform: Platform) -> None:
        """
        Reset platform configuration to default.
        
        Args:
            platform: Platform to reset
        """
        if platform in self._configs:
            del self._configs[platform]
            logger.info(f"Reset configuration to default for platform: {platform.value}")
    
    def get_all_configs(self) -> Dict[Platform, PlatformConfig]:
        """
        Get all platform configurations.
        
        Returns:
            Dictionary of all platform configurations
        """
        all_configs = {}
        
        # Start with defaults
        all_configs.update(self._default_configs)
        
        # Override with custom configs
        all_configs.update(self._configs)
        
        return all_configs
    
    def get_enabled_platforms(self) -> List[Platform]:
        """
        Get list of enabled platforms.
        
        Returns:
            List of enabled platforms
        """
        all_configs = self.get_all_configs()
        return [platform for platform, config in all_configs.items() if config.enabled]
    
    def get_platforms_by_type(self, integration_type: IntegrationType) -> List[Platform]:
        """
        Get platforms by integration type.
        
        Args:
            integration_type: Type of integration to filter by
            
        Returns:
            List of platforms with the specified integration type
        """
        all_configs = self.get_all_configs()
        return [
            platform for platform, config in all_configs.items()
            if config.integration_type == integration_type
        ]
    
    def validate_config(self, config: PlatformConfig) -> List[str]:
        """
        Validate a platform configuration.
        
        Args:
            config: Configuration to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Basic validation
        if not config.platform or config.platform == "":
            errors.append("Platform is required")
        
        if not config.integration_type or config.integration_type == "":
            errors.append("Integration type is required")
        
        if not config.auth_method or config.auth_method == "":
            errors.append("Authentication method is required")
        
        # API-specific validation
        if config.integration_type == IntegrationType.API:
            if not config.api_base_url:
                errors.append("API base URL is required for API integrations")
            
            if config.auth_method == AuthenticationMethod.OAUTH2:
                # OAuth2 specific validation would go here
                pass

        
        # Content limits validation - check for 0 specifically since it's invalid
        if config.max_title_length is not None and config.max_title_length <= 0:
            errors.append("Max title length must be positive")
        
        if config.max_description_length is not None and config.max_description_length <= 0:
            errors.append("Max description length must be positive")
        
        if config.max_hashtags is not None and config.max_hashtags < 0:
            errors.append("Max hashtags cannot be negative")
        
        # Rate limiting validation
        if config.rate_limit_per_minute is not None and config.rate_limit_per_minute <= 0:
            errors.append("Rate limit must be positive")
        
        return errors
    
    def load_from_file(self, file_path: str) -> int:
        """
        Load platform configurations from a JSON file.
        
        Args:
            file_path: Path to JSON configuration file
            
        Returns:
            Number of configurations loaded
        """
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            loaded_count = 0
            
            for platform_name, config_data in data.items():
                try:
                    platform = Platform(platform_name)
                    config = PlatformConfig(**config_data)
                    
                    # Validate configuration
                    errors = self.validate_config(config)
                    if errors:
                        logger.error(f"Invalid config for {platform_name}: {errors}")
                        continue
                    
                    self.set_config(platform, config)
                    loaded_count += 1
                    
                except (ValueError, TypeError) as e:
                    logger.error(f"Error loading config for {platform_name}: {e}")
            
            logger.info(f"Loaded {loaded_count} platform configurations from {file_path}")
            return loaded_count
            
        except Exception as e:
            logger.error(f"Failed to load configurations from {file_path}: {e}")
            return 0
    
    def save_to_file(self, file_path: str) -> bool:
        """
        Save current configurations to a JSON file.
        
        Args:
            file_path: Path to save configurations to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Only save custom configurations (not defaults)
            data = {}
            for platform, config in self._configs.items():
                data[platform.value] = config.model_dump()
            
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.info(f"Saved {len(data)} configurations to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save configurations to {file_path}: {e}")
            return False


# Global configuration manager instance
config_manager = PlatformConfigManager()


def get_platform_config(platform: Platform) -> Optional[PlatformConfig]:
    """
    Convenience function to get platform configuration.
    
    Args:
        platform: Platform to get config for
        
    Returns:
        Platform configuration or None
    """
    return config_manager.get_config(platform)


def get_config_manager() -> PlatformConfigManager:
    """
    Get the global configuration manager instance.
    
    Returns:
        Global PlatformConfigManager instance
    """
    return config_manager