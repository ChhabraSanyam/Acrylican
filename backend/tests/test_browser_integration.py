"""
Simple integration test for browser automation functionality.

This test verifies that the browser automation service can be initialized
and basic operations work without requiring actual browser interaction.
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock

from app.services.browser_automation import (
    BrowserAutomationService,
    BrowserAutomationConfig,
    BrowserCredentials
)
from app.services.browser_credentials import BrowserCredentialManager
from app.services.platform_integration import Platform


class TestBrowserAutomationIntegration:
    """Integration tests for browser automation."""
    
    @pytest.mark.asyncio
    async def test_service_can_be_initialized(self):
        """Test that the browser automation service can be initialized."""
        config = BrowserAutomationConfig()
        service = BrowserAutomationService(config)
        
        # Verify service properties
        assert service.config == config
        assert len(service.automators) == 3
        assert Platform.MEESHO in service.automators
        assert Platform.SNAPDEAL in service.automators
        assert Platform.INDIAMART in service.automators
        
        # Verify supported platforms
        supported = service.get_supported_platforms()
        assert Platform.MEESHO in supported
        assert Platform.SNAPDEAL in supported
        assert Platform.INDIAMART in supported
        assert Platform.FACEBOOK not in supported
    
    def test_credential_manager_initialization(self):
        """Test that the credential manager can be initialized."""
        manager = BrowserCredentialManager()
        
        # Verify browser platforms
        assert manager.is_browser_platform(Platform.MEESHO)
        assert manager.is_browser_platform(Platform.SNAPDEAL)
        assert manager.is_browser_platform(Platform.INDIAMART)
        assert not manager.is_browser_platform(Platform.FACEBOOK)
    
    @pytest.mark.asyncio
    async def test_credential_validation(self):
        """Test credential validation."""
        manager = BrowserCredentialManager()
        
        # Valid credentials
        valid_creds = BrowserCredentials(
            username="test@example.com",
            password="testpass123",
            platform=Platform.MEESHO
        )
        
        is_valid = await manager.validate_credentials(Platform.MEESHO, valid_creds)
        assert is_valid
        
        # Invalid credentials (no password)
        invalid_creds = BrowserCredentials(
            username="test@example.com",
            password="",
            platform=Platform.MEESHO
        )
        
        is_valid = await manager.validate_credentials(Platform.MEESHO, invalid_creds)
        assert not is_valid
    
    @pytest.mark.asyncio
    async def test_service_lifecycle_with_mocks(self):
        """Test service lifecycle with mocked Playwright."""
        config = BrowserAutomationConfig()
        
        # Mock Playwright components
        mock_playwright = AsyncMock()
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.cookies = AsyncMock(return_value=[])
        
        with patch('app.services.browser_automation.async_playwright') as mock_async_playwright:
            mock_async_playwright.return_value.start = AsyncMock(return_value=mock_playwright)
            
            service = BrowserAutomationService(config)
            
            # Test start
            await service.start()
            assert service.playwright == mock_playwright
            assert service.browser == mock_browser
            
            # Test stop
            await service.stop()
            mock_browser.close.assert_called_once()
            mock_playwright.stop.assert_called_once()
    
    def test_platform_configuration(self):
        """Test platform-specific configuration."""
        from app.services.browser_config import PlatformBrowserConfig
        
        config = PlatformBrowserConfig()
        
        # Test platform timeouts
        meesho_timeout = config.get_platform_timeout("meesho")
        assert meesho_timeout == 45000
        
        snapdeal_timeout = config.get_platform_timeout("snapdeal")
        assert snapdeal_timeout == 30000
        
        # Test platform selectors
        meesho_selectors = config.get_platform_selectors("meesho")
        assert "login" in meesho_selectors
        assert "posting" in meesho_selectors
        
        # Test platform URLs
        meesho_urls = config.get_platform_urls("meesho")
        assert meesho_urls["base"] == "https://supplier.meesho.com"
        assert meesho_urls["login"] == "https://supplier.meesho.com/login"
    
    def test_error_handling_configuration(self):
        """Test error handling configuration."""
        from app.services.browser_config import ErrorHandlingConfig
        
        config = ErrorHandlingConfig()
        
        # Test error classification
        network_error = config.classify_error("net::ERR_CONNECTION_REFUSED")
        assert network_error == "network_error"
        
        auth_error = config.classify_error("Invalid credentials provided")
        assert auth_error == "authentication_error"
        
        # Test error strategies
        network_strategy = config.get_error_strategy("network_error")
        assert network_strategy["max_retries"] == 3
        assert network_strategy["exponential_backoff"] is True
        
        auth_strategy = config.get_error_strategy("authentication_error")
        assert auth_strategy["max_retries"] == 1
        assert auth_strategy["exponential_backoff"] is False
    
    @pytest.mark.asyncio
    async def test_browser_automation_in_platform_service(self):
        """Test that browser automation is properly integrated in platform service."""
        from app.services.platform_service import PlatformService
        
        service = PlatformService()
        
        # Verify browser credential manager is initialized
        assert service.browser_credential_manager is not None
        assert service.browser_credential_manager.is_browser_platform(Platform.MEESHO)
        
        # Test platform info includes browser automation platforms
        all_info = service.get_all_platform_info()
        
        # Should include configured platforms (from platform_config)
        # Note: The actual platforms depend on the configuration
        assert isinstance(all_info, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])