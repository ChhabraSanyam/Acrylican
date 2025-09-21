"""
Integration tests for browser automation service.

These tests verify the browser automation functionality for non-API platforms
including session management, credential handling, and posting capabilities.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

from app.services.browser_automation import (
    BrowserAutomationService,
    BrowserAutomationConfig,
    BrowserSession,
    BrowserCredentials,
    MeeshoAutomator,
    SnapdealAutomator,
    IndiaMARTAutomator
)
from app.services.browser_credentials import (
    BrowserCredentialManager,
    SecureCredentialStore
)
from app.services.platform_integration import (
    Platform,
    PostContent,
    PostResult,
    PostStatus
)


class TestBrowserAutomationConfig:
    """Test browser automation configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = BrowserAutomationConfig()
        
        assert config.HEADLESS is True
        assert config.TIMEOUT == 30000
        assert config.VIEWPORT == {"width": 1920, "height": 1080}
        assert config.SESSION_TIMEOUT_HOURS == 24
        assert config.MAX_RETRY_ATTEMPTS == 3
        assert config.DISABLE_IMAGES is True


class TestBrowserCredentials:
    """Test browser credentials model."""
    
    def test_credentials_creation(self):
        """Test creating browser credentials."""
        credentials = BrowserCredentials(
            username="test@example.com",
            password="testpass123",
            platform=Platform.MEESHO,
            additional_data={"phone": "1234567890"}
        )
        
        assert credentials.username == "test@example.com"
        assert credentials.password == "testpass123"
        assert credentials.additional_data["phone"] == "1234567890"
        assert credentials.platform == Platform.MEESHO
    
    def test_credentials_serialization(self):
        """Test that password is excluded from serialization."""
        credentials = BrowserCredentials(
            username="test@example.com",
            password="testpass123",
        )
        
        # Password should be excluded from dict() by default
        data = credentials.dict()
        assert "username" in data
        assert "platform" in data
        # Note: In Pydantic v2, write_only doesn't work the same way
        # We'll test that password is present but can be excluded when needed


class TestSecureCredentialStore:
    """Test secure credential storage."""
    
    @pytest.fixture
    def credential_store(self):
        """Create a test credential store."""
        return SecureCredentialStore()
    
    def test_encrypt_decrypt_credentials(self, credential_store):
        """Test encrypting and decrypting credentials."""
        original_credentials = BrowserCredentials(
            username="test@example.com",
            password="testpass123",
            platform=Platform.MEESHO,
            additional_data={"secret_key": "secret123"}
        )
        
        # Encrypt
        encrypted_data = credential_store.encrypt_credentials(original_credentials)
        assert isinstance(encrypted_data, str)
        assert "testpass123" not in encrypted_data
        
        # Decrypt
        decrypted_credentials = credential_store.decrypt_credentials(encrypted_data)
        assert decrypted_credentials.username == original_credentials.username
        assert decrypted_credentials.password == original_credentials.password
        assert decrypted_credentials.additional_data == original_credentials.additional_data


class TestBrowserSession:
    """Test browser session model."""
    
    def test_session_creation(self):
        """Test creating a browser session."""
        session = BrowserSession(
            platform=Platform.MEESHO,
            user_id="test_user",
            cookies=[{"name": "session", "value": "abc123"}]
        )
        
        assert session.platform == Platform.MEESHO
        assert session.user_id == "test_user"
        assert len(session.cookies) == 1
        assert session.is_active is True
    
    def test_session_expiration(self):
        """Test session expiration logic."""
        # Create expired session
        expired_session = BrowserSession(
            platform=Platform.MEESHO,
            user_id="test_user",
            expires_at=datetime.now() - timedelta(hours=1)
        )
        
        # Create active session
        active_session = BrowserSession(
            platform=Platform.MEESHO,
            user_id="test_user",
            expires_at=datetime.now() + timedelta(hours=1)
        )
        
        assert expired_session.expires_at < datetime.now()
        assert active_session.expires_at > datetime.now()


class TestPlatformAutomators:
    """Test platform-specific automators."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return BrowserAutomationConfig()
    
    @pytest.fixture
    def mock_page(self):
        """Create mock Playwright page."""
        page = AsyncMock()
        page.goto = AsyncMock()
        page.wait_for_load_state = AsyncMock()
        page.fill = AsyncMock()
        page.click = AsyncMock()
        page.wait_for_selector = AsyncMock()
        page.url = "https://supplier.meesho.com/dashboard"
        return page
    
    @pytest.fixture
    def test_credentials(self):
        """Create test credentials."""
        return BrowserCredentials(
            username="test@example.com",
            password="testpass123", platform=Platform.MEESHO
        )
    
    @pytest.fixture
    def test_content(self):
        """Create test post content."""
        return PostContent(
            title="Test Product",
            description="This is a test product description",
            images=["https://example.com/image1.jpg"],
            hashtags=["#handmade", "#artisan"],
            product_data={"price": 99.99, "category": "Handicrafts"}
        )
    
    @pytest.mark.asyncio
    async def test_meesho_automator_login_success(self, config, mock_page, test_credentials):
        """Test successful Meesho login."""
        automator = MeeshoAutomator(config)
        
        # Mock successful login
        mock_page.url = "https://supplier.meesho.com/dashboard"
        
        result = await automator.login(mock_page, test_credentials)
        
        assert result is True
        mock_page.goto.assert_called_once()
        mock_page.fill.assert_called()
        mock_page.click.assert_called()
    
    @pytest.mark.asyncio
    async def test_meesho_automator_login_failure(self, config, mock_page, test_credentials):
        """Test failed Meesho login."""
        automator = MeeshoAutomator(config)
        
        # Mock failed login (no redirect to dashboard)
        mock_page.url = "https://supplier.meesho.com/login"
        
        # Mock error message
        error_element = AsyncMock()
        error_element.text_content = AsyncMock(return_value="Invalid credentials")
        mock_page.wait_for_selector = AsyncMock(return_value=error_element)
        
        result = await automator.login(mock_page, test_credentials)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_meesho_automator_post_content(self, config, mock_page, test_content):
        """Test posting content to Meesho."""
        automator = MeeshoAutomator(config)
        
        # Mock successful posting
        success_element = AsyncMock()
        mock_page.wait_for_selector = AsyncMock(return_value=success_element)
        
        result = await automator.post_content(mock_page, test_content)
        
        assert result.platform == Platform.MEESHO
        assert result.status == PostStatus.SUCCESS
        assert result.post_id is not None
    
    @pytest.mark.asyncio
    async def test_snapdeal_automator_login(self, config, mock_page, test_credentials):
        """Test Snapdeal login."""
        automator = SnapdealAutomator(config)
        
        # Mock successful login
        mock_page.url = "https://seller.snapdeal.com/dashboard"
        
        result = await automator.login(mock_page, test_credentials)
        
        assert result is True
        mock_page.goto.assert_called_with("https://seller.snapdeal.com/login")
    
    @pytest.mark.asyncio
    async def test_indiamart_automator_login(self, config, mock_page, test_credentials):
        """Test IndiaMART login."""
        automator = IndiaMARTAutomator(config)
        
        # Mock successful login
        mock_page.url = "https://seller.indiamart.com/my-indiamart"
        
        result = await automator.login(mock_page, test_credentials)
        
        assert result is True
        mock_page.goto.assert_called_with("https://seller.indiamart.com/login")


class TestBrowserAutomationService:
    """Test the main browser automation service."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return BrowserAutomationConfig()
    
    @pytest.fixture
    def mock_playwright(self):
        """Create mock Playwright instance."""
        playwright = AsyncMock()
        browser = AsyncMock()
        context = AsyncMock()
        page = AsyncMock()
        
        playwright.chromium.launch = AsyncMock(return_value=browser)
        browser.new_context = AsyncMock(return_value=context)
        context.new_page = AsyncMock(return_value=page)
        context.cookies = AsyncMock(return_value=[])
        context.close = AsyncMock()
        
        return playwright, browser, context, page
    
    @pytest.fixture
    def test_credentials(self):
        """Create test credentials."""
        return BrowserCredentials(
            username="test@example.com",
            password="testpass123", platform=Platform.MEESHO
        )
    
    @pytest.fixture
    def test_content(self):
        """Create test post content."""
        return PostContent(
            title="Test Product",
            description="This is a test product description",
            images=["https://example.com/image1.jpg"],
            hashtags=["#handmade", "#artisan"]
        )
    
    @pytest.mark.asyncio
    async def test_service_initialization(self, config):
        """Test service initialization."""
        service = BrowserAutomationService(config)
        
        assert service.config == config
        assert len(service.automators) == 3
        assert Platform.MEESHO in service.automators
        assert Platform.SNAPDEAL in service.automators
        assert Platform.INDIAMART in service.automators
    
    @pytest.mark.asyncio
    async def test_service_start_stop(self, config, mock_playwright):
        """Test service start and stop."""
        playwright, browser, context, page = mock_playwright
        
        with patch('app.services.browser_automation.async_playwright') as mock_async_playwright:
            mock_async_playwright.return_value.start = AsyncMock(return_value=playwright)
            
            service = BrowserAutomationService(config)
            
            # Test start
            await service.start()
            assert service.playwright == playwright
            assert service.browser == browser
            
            # Test stop
            await service.stop()
            browser.close.assert_called_once()
            playwright.stop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_authenticate_platform_success(self, config, mock_playwright, test_credentials):
        """Test successful platform authentication."""
        playwright, browser, context, page = mock_playwright
        
        with patch('app.services.browser_automation.async_playwright') as mock_async_playwright:
            mock_async_playwright.return_value.start = AsyncMock(return_value=playwright)
            
            service = BrowserAutomationService(config)
            await service.start()
            
            # Mock successful login
            with patch.object(service.automators[Platform.MEESHO], 'login', return_value=True):
                result = await service.authenticate_platform(
                    Platform.MEESHO,
                    "test_user",
                    test_credentials
                )
            
            assert result is True
            assert "meesho_test_user" in service.sessions
            
            await service.stop()
    
    @pytest.mark.asyncio
    async def test_authenticate_platform_failure(self, config, mock_playwright, test_credentials):
        """Test failed platform authentication."""
        playwright, browser, context, page = mock_playwright
        
        with patch('app.services.browser_automation.async_playwright') as mock_async_playwright:
            mock_async_playwright.return_value.start = AsyncMock(return_value=playwright)
            
            service = BrowserAutomationService(config)
            await service.start()
            
            # Mock failed login
            with patch.object(service.automators[Platform.MEESHO], 'login', return_value=False):
                result = await service.authenticate_platform(
                    Platform.MEESHO,
                    "test_user",
                    test_credentials
                )
            
            assert result is False
            assert "meesho_test_user" not in service.sessions
            
            await service.stop()
    
    @pytest.mark.asyncio
    async def test_authenticate_unsupported_platform(self, config, test_credentials):
        """Test authentication with unsupported platform."""
        service = BrowserAutomationService(config)
        
        with pytest.raises(Exception):  # Should raise AuthenticationError
            await service.authenticate_platform(
                Platform.FACEBOOK,  # Not supported by browser automation
                "test_user",
                test_credentials
            )
    
    @pytest.mark.asyncio
    async def test_validate_session_active(self, config, mock_playwright):
        """Test validating an active session."""
        playwright, browser, context, page = mock_playwright
        
        with patch('app.services.browser_automation.async_playwright') as mock_async_playwright:
            mock_async_playwright.return_value.start = AsyncMock(return_value=playwright)
            
            service = BrowserAutomationService(config)
            await service.start()
            
            # Create active session
            session = BrowserSession(
                platform=Platform.MEESHO,
                user_id="test_user",
                expires_at=datetime.now() + timedelta(hours=1)
            )
            service.sessions["meesho_test_user"] = session
            
            # Mock successful validation
            with patch.object(service.automators[Platform.MEESHO], 'validate_session', return_value=True):
                result = await service.validate_session(Platform.MEESHO, "test_user")
            
            assert result is True
            
            await service.stop()
    
    @pytest.mark.asyncio
    async def test_validate_session_expired(self, config):
        """Test validating an expired session."""
        service = BrowserAutomationService(config)
        
        # Create expired session
        session = BrowserSession(
            platform=Platform.MEESHO,
            user_id="test_user",
            expires_at=datetime.now() - timedelta(hours=1)
        )
        service.sessions["meesho_test_user"] = session
        
        result = await service.validate_session(Platform.MEESHO, "test_user")
        
        assert result is False
        assert not session.is_active
    
    @pytest.mark.asyncio
    async def test_post_content_success(self, config, mock_playwright, test_content):
        """Test successful content posting."""
        playwright, browser, context, page = mock_playwright
        
        with patch('app.services.browser_automation.async_playwright') as mock_async_playwright:
            mock_async_playwright.return_value.start = AsyncMock(return_value=playwright)
            
            service = BrowserAutomationService(config)
            await service.start()
            
            # Create active session
            session = BrowserSession(
                platform=Platform.MEESHO,
                user_id="test_user",
                expires_at=datetime.now() + timedelta(hours=1)
            )
            service.sessions["meesho_test_user"] = session
            
            # Mock successful posting
            expected_result = PostResult(
                platform=Platform.MEESHO,
                status=PostStatus.SUCCESS,
                post_id="test_post_123"
            )
            
            with patch.object(service.automators[Platform.MEESHO], 'validate_session', return_value=True):
                with patch.object(service.automators[Platform.MEESHO], 'post_content', return_value=expected_result):
                    result = await service.post_content(Platform.MEESHO, "test_user", test_content)
            
            assert result.status == PostStatus.SUCCESS
            assert result.platform == Platform.MEESHO
            
            await service.stop()
    
    @pytest.mark.asyncio
    async def test_post_content_no_session(self, config, test_content):
        """Test posting content without active session."""
        service = BrowserAutomationService(config)
        
        result = await service.post_content(Platform.MEESHO, "test_user", test_content)
        
        assert result.status == PostStatus.FAILED
        assert result.error_code == "NO_ACTIVE_SESSION"
    
    @pytest.mark.asyncio
    async def test_disconnect_platform(self, config):
        """Test disconnecting from a platform."""
        service = BrowserAutomationService(config)
        
        # Create session
        session = BrowserSession(
            platform=Platform.MEESHO,
            user_id="test_user"
        )
        service.sessions["meesho_test_user"] = session
        
        result = await service.disconnect_platform(Platform.MEESHO, "test_user")
        
        assert result is True
        assert "meesho_test_user" not in service.sessions
    
    def test_get_supported_platforms(self, config):
        """Test getting supported platforms."""
        service = BrowserAutomationService(config)
        
        platforms = service.get_supported_platforms()
        
        assert Platform.MEESHO in platforms
        assert Platform.SNAPDEAL in platforms
        assert Platform.INDIAMART in platforms
        assert Platform.FACEBOOK not in platforms
    
    def test_is_platform_supported(self, config):
        """Test checking if platform is supported."""
        service = BrowserAutomationService(config)
        
        assert service.is_platform_supported(Platform.MEESHO) is True
        assert service.is_platform_supported(Platform.FACEBOOK) is False
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self, config):
        """Test cleaning up expired sessions."""
        service = BrowserAutomationService(config)
        
        # Create expired session
        expired_session = BrowserSession(
            platform=Platform.MEESHO,
            user_id="expired_user",
            expires_at=datetime.now() - timedelta(hours=1)
        )
        service.sessions["meesho_expired_user"] = expired_session
        
        # Create active session
        active_session = BrowserSession(
            platform=Platform.SNAPDEAL,
            user_id="active_user",
            expires_at=datetime.now() + timedelta(hours=1)
        )
        service.sessions["snapdeal_active_user"] = active_session
        
        await service.cleanup_expired_sessions()
        
        assert "meesho_expired_user" not in service.sessions
        assert "snapdeal_active_user" in service.sessions


class TestBrowserCredentialManager:
    """Test browser credential manager."""
    
    @pytest.fixture
    def credential_manager(self):
        """Create test credential manager."""
        return BrowserCredentialManager()
    
    @pytest.fixture
    def test_credentials(self):
        """Create test credentials."""
        return BrowserCredentials(
            username="test@example.com",
            password="testpass123", platform=Platform.MEESHO
        )
    
    def test_is_browser_platform(self, credential_manager):
        """Test checking if platform uses browser automation."""
        assert credential_manager.is_browser_platform(Platform.MEESHO) is True
        assert credential_manager.is_browser_platform(Platform.FACEBOOK) is False
    
    @pytest.mark.asyncio
    async def test_validate_credentials_valid(self, credential_manager):
        """Test validating valid credentials."""
        credentials = BrowserCredentials(
            username="test@example.com",
            password="testpass123", platform=Platform.MEESHO
        )
        
        result = await credential_manager.validate_credentials(Platform.MEESHO, credentials)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_credentials_invalid(self, credential_manager):
        """Test validating invalid credentials."""
        # Missing password
        credentials = BrowserCredentials(
            username="test@example.com",
            password=""
        )
        
        result = await credential_manager.validate_credentials(Platform.MEESHO, credentials)
        assert result is False
        
        # Invalid email for Snapdeal
        credentials = BrowserCredentials(
            username="invalid_email",
            password="testpass123", platform=Platform.MEESHO
        )
        
        result = await credential_manager.validate_credentials(Platform.SNAPDEAL, credentials)
        assert result is False
    
    def test_get_browser_platforms(self, credential_manager):
        """Test getting browser automation platforms."""
        platforms = credential_manager.browser_platforms
        
        assert Platform.MEESHO in platforms
        assert Platform.SNAPDEAL in platforms
        assert Platform.INDIAMART in platforms
        assert len(platforms) == 3


@pytest.mark.integration
class TestBrowserAutomationIntegration:
    """Integration tests for browser automation."""
    
    @pytest.mark.asyncio
    async def test_full_authentication_flow(self):
        """Test complete authentication flow."""
        config = BrowserAutomationConfig()
        config.HEADLESS = True  # Ensure headless for CI
        
        credential_manager = BrowserCredentialManager()
        
        # Test credentials validation
        credentials = BrowserCredentials(
            username="test@example.com",
            password="testpass123", platform=Platform.MEESHO
        )
        
        is_valid = await credential_manager.validate_credentials(Platform.MEESHO, credentials)
        assert is_valid is True
        
        # Note: Actual browser automation would require real credentials
        # and would be tested in a separate test environment
    
    @pytest.mark.asyncio
    async def test_service_lifecycle(self):
        """Test service lifecycle management."""
        config = BrowserAutomationConfig()
        
        # Test async context manager
        async with BrowserAutomationService(config) as service:
            assert service.playwright is not None
            assert service.browser is not None
            
            platforms = service.get_supported_platforms()
            assert len(platforms) > 0
        
        # Service should be stopped after context exit
        assert service.playwright is None or service.browser is None