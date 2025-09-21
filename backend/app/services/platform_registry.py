"""
Platform Registry and Plugin System

This module provides a registry system for managing platform integrations,
allowing dynamic loading and management of platform plugins.
"""

from typing import Dict, List, Type, Optional, Any
import importlib
import inspect
from pathlib import Path
import logging

from .platform_integration import (
    BasePlatformIntegration,
    Platform,
    PlatformConfig,
    IntegrationType,
    PlatformIntegrationError
)

logger = logging.getLogger(__name__)


class PlatformRegistry:
    """
    Registry for managing platform integration plugins.
    
    This class handles the registration, loading, and management of platform
    integration classes, providing a centralized way to access all available
    platform integrations.
    """
    
    def __init__(self):
        self._integrations: Dict[Platform, Type[BasePlatformIntegration]] = {}
        self._configs: Dict[Platform, PlatformConfig] = {}
        self._instances: Dict[str, BasePlatformIntegration] = {}  # user_id:platform -> instance
    
    def register_platform(
        self, 
        platform: Platform, 
        integration_class: Type[BasePlatformIntegration],
        config: PlatformConfig
    ) -> None:
        """
        Register a platform integration class.
        
        Args:
            platform: Platform enum value
            integration_class: Class implementing BasePlatformIntegration
            config: Platform configuration
        """
        if not issubclass(integration_class, BasePlatformIntegration):
            raise ValueError(
                f"Integration class must inherit from BasePlatformIntegration"
            )
        
        if config.platform != platform:
            raise ValueError(
                f"Config platform {config.platform} doesn't match {platform}"
            )
        
        self._integrations[platform] = integration_class
        self._configs[platform] = config
        
        logger.info(f"Registered platform integration: {platform.value}")
    
    def unregister_platform(self, platform: Platform) -> None:
        """
        Unregister a platform integration.
        
        Args:
            platform: Platform to unregister
        """
        if platform in self._integrations:
            del self._integrations[platform]
            del self._configs[platform]
            
            # Clean up any active instances
            keys_to_remove = [
                key for key in self._instances.keys() 
                if key.endswith(f":{platform.value}")
            ]
            for key in keys_to_remove:
                del self._instances[key]
            
            logger.info(f"Unregistered platform integration: {platform.value}")
    
    def get_platform_integration(
        self, 
        platform: Platform, 
        user_id: str
    ) -> Optional[BasePlatformIntegration]:
        """
        Get a platform integration instance for a specific user.
        
        Args:
            platform: Platform to get integration for
            user_id: User identifier
            
        Returns:
            Platform integration instance or None if not available
        """
        instance_key = f"{user_id}:{platform.value}"
        
        # Return existing instance if available
        if instance_key in self._instances:
            return self._instances[instance_key]
        
        # Create new instance if platform is registered
        if platform in self._integrations:
            integration_class = self._integrations[platform]
            config = self._configs[platform]
            
            try:
                instance = integration_class(config)
                self._instances[instance_key] = instance
                return instance
            except Exception as e:
                logger.error(f"Failed to create integration for {platform.value}: {e}")
                return None
        
        return None
    
    def get_available_platforms(self) -> List[Platform]:
        """
        Get list of all registered platforms.
        
        Returns:
            List of available platforms
        """
        return list(self._integrations.keys())
    
    def get_enabled_platforms(self) -> List[Platform]:
        """
        Get list of enabled platforms.
        
        Returns:
            List of enabled platforms
        """
        return [
            platform for platform, config in self._configs.items()
            if config.enabled
        ]
    
    def get_platform_config(self, platform: Platform) -> Optional[PlatformConfig]:
        """
        Get configuration for a specific platform.
        
        Args:
            platform: Platform to get config for
            
        Returns:
            Platform configuration or None if not registered
        """
        return self._configs.get(platform)
    
    def update_platform_config(self, platform: Platform, config: PlatformConfig) -> None:
        """
        Update configuration for a registered platform.
        
        Args:
            platform: Platform to update
            config: New configuration
        """
        if platform not in self._integrations:
            raise ValueError(f"Platform {platform.value} is not registered")
        
        if config.platform != platform:
            raise ValueError(
                f"Config platform {config.platform} doesn't match {platform}"
            )
        
        self._configs[platform] = config
        
        # Invalidate existing instances to force recreation with new config
        keys_to_remove = [
            key for key in self._instances.keys() 
            if key.endswith(f":{platform.value}")
        ]
        for key in keys_to_remove:
            del self._instances[key]
        
        logger.info(f"Updated configuration for platform: {platform.value}")
    
    def get_platforms_by_type(self, integration_type: IntegrationType) -> List[Platform]:
        """
        Get platforms filtered by integration type.
        
        Args:
            integration_type: Type of integration to filter by
            
        Returns:
            List of platforms matching the integration type
        """
        return [
            platform for platform, config in self._configs.items()
            if config.integration_type == integration_type
        ]
    
    def cleanup_user_instances(self, user_id: str) -> None:
        """
        Clean up all platform instances for a specific user.
        
        Args:
            user_id: User identifier
        """
        keys_to_remove = [
            key for key in self._instances.keys() 
            if key.startswith(f"{user_id}:")
        ]
        
        for key in keys_to_remove:
            instance = self._instances[key]
            try:
                # Attempt to disconnect gracefully
                if hasattr(instance, 'disconnect'):
                    asyncio.create_task(instance.disconnect())
            except Exception as e:
                logger.error(f"Error disconnecting instance {key}: {e}")
            finally:
                del self._instances[key]
        
        logger.info(f"Cleaned up {len(keys_to_remove)} instances for user {user_id}")
    
    def get_platform_info(self) -> Dict[str, Any]:
        """
        Get information about all registered platforms.
        
        Returns:
            Dictionary containing platform information
        """
        return {
            platform.value: {
                "integration_type": config.integration_type.value,
                "auth_method": config.auth_method.value,
                "enabled": config.enabled,
                "rate_limit": config.rate_limit_per_minute,
                "max_retries": config.max_retries
            }
            for platform, config in self._configs.items()
        }


class PlatformLoader:
    """
    Utility class for dynamically loading platform integration plugins.
    
    This class can discover and load platform integrations from specified
    directories, enabling a plugin-based architecture.
    """
    
    def __init__(self, registry: PlatformRegistry):
        self.registry = registry
    
    def load_from_directory(self, directory_path: str) -> int:
        """
        Load platform integrations from a directory.
        
        Args:
            directory_path: Path to directory containing platform modules
            
        Returns:
            Number of platforms loaded
        """
        directory = Path(directory_path)
        if not directory.exists() or not directory.is_dir():
            logger.warning(f"Platform directory not found: {directory_path}")
            return 0
        
        loaded_count = 0
        
        for file_path in directory.glob("*.py"):
            if file_path.name.startswith("__"):
                continue
            
            try:
                loaded_count += self._load_from_file(file_path)
            except Exception as e:
                logger.error(f"Failed to load platform from {file_path}: {e}")
        
        logger.info(f"Loaded {loaded_count} platform integrations from {directory_path}")
        return loaded_count
    
    def _load_from_file(self, file_path: Path) -> int:
        """
        Load platform integrations from a single Python file.
        
        Args:
            file_path: Path to Python file
            
        Returns:
            Number of platforms loaded from this file
        """
        module_name = file_path.stem
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        
        if spec is None or spec.loader is None:
            logger.warning(f"Could not load spec for {file_path}")
            return 0
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        loaded_count = 0
        
        # Look for classes that inherit from BasePlatformIntegration
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if (issubclass(obj, BasePlatformIntegration) and 
                obj != BasePlatformIntegration):
                
                # Look for associated configuration
                config_name = f"{name.upper()}_CONFIG"
                if hasattr(module, config_name):
                    config = getattr(module, config_name)
                    if isinstance(config, PlatformConfig):
                        self.registry.register_platform(
                            config.platform, obj, config
                        )
                        loaded_count += 1
                    else:
                        logger.warning(
                            f"Invalid config type for {name}: {type(config)}"
                        )
                else:
                    logger.warning(f"No configuration found for {name}")
        
        return loaded_count
    
    def load_builtin_platforms(self) -> int:
        """
        Load built-in platform integrations.
        
        Returns:
            Number of built-in platforms loaded
        """
        # This would load platform integrations that are part of the core system
        # For now, it's a placeholder that would be implemented with actual
        # platform integration classes
        
        builtin_platforms = []  # Would contain actual platform configs
        
        for platform_config in builtin_platforms:
            # Register each built-in platform
            pass
        
        return len(builtin_platforms)


# Global registry instance
platform_registry = PlatformRegistry()


def get_platform_registry() -> PlatformRegistry:
    """
    Get the global platform registry instance.
    
    Returns:
        Global PlatformRegistry instance
    """
    return platform_registry


def register_platform(
    platform: Platform,
    integration_class: Type[BasePlatformIntegration],
    config: PlatformConfig
) -> None:
    """
    Convenience function to register a platform integration.
    
    Args:
        platform: Platform enum value
        integration_class: Integration class
        config: Platform configuration
    """
    platform_registry.register_platform(platform, integration_class, config)


def get_platform_integration(
    platform: Platform, 
    user_id: str
) -> Optional[BasePlatformIntegration]:
    """
    Convenience function to get a platform integration instance.
    
    Args:
        platform: Platform to get integration for
        user_id: User identifier
        
    Returns:
        Platform integration instance or None
    """
    return platform_registry.get_platform_integration(platform, user_id)