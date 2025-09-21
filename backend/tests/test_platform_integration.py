"""
Unit tests for platform integration framework
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from typing import Optional

from app.services.platform_integration import (
    BasePlatformIntegration,
    APIBasedIntegration,
    BrowserAutomationIntegration,
    Platform,
    IntegrationType,
    AuthenticationMethod,
    PlatformConfig,
    PlatformCredentials,
    PostContent,
    PostResult,
    PostStatus,
    PlatformMetrics,
    PlatformIntegrationError,
    AuthenticationError,
    PostingError
)


class MockAPIIntegration(APIBasedIntegration):
    """Mock API-based integration for testing"""
    
    def __init__(self, config: PlatformConfig):
        super().__init__(config)
        self.authenticated = False
        self.connection_valid = True
        self.should_fail_post = False
    
    async def authenticate(self, credentials: PlatformCredentials) -> bool:
        if credentials.access_token == "valid_token":
            self.authenticated = True
            return True
        return False
    
    async def validate_connection(self) -> bool:
        return self.authenticated and self.connection_valid
    
    async def post_content(self, content: PostContent) -> PostResult:
        if self.should_fail_post:
            return PostResult(
                platform=self.platform,
                status=PostStatus.FAILED,
                error_message="Mock posting error"
            )
        
        return PostResult(
            platform=self.platform,
            status=PostStatus.SUCCESS,
            post_id="mock_post_123",
            published_at=datetime.now()
        )
    
    async def get_post_metrics(self, post_id: str) -> Optional[PlatformMetrics]:
        if post_id == "mock_post_123":
            return PlatformMetrics(
                platform=self.platform,
                post_id=post_id,
                likes=10,
                shares=5,
                comments=3,
                views=100,
                retrieved_at=datetime.now()
            )
        return None
    
    async def format_content(self, content: PostContent) -> PostContent:
        # Mock formatting - truncate title if too long
        formatted_content = content.copy()
        if self.config.max_title_length and len(content.title) > self.config.max_title_length:
            formatted_content.title = content.title[:self.config.max_title_length]
        return formatted_content


class MockBrowserIntegration(BrowserAutomationIntegration):
    """Mock browser automation integration for testing"""
    
    def __init__(self, config: PlatformConfig):
        super().__init__(config)
        self.authenticated = False
        self.browser_setup = False
    
    async def authenticate(self, credentials: PlatformCredentials) -> bool:
        if credentials.session_data and credentials.session_data.get("username") == "valid_user":
            self.authenticated = True
            return True
        return False
    
    async def validate_connection(self) -> bool:
        return self.authenticated and self.session_active
    
    async def post_content(self, content: PostContent) -> PostResult:
        if not self.authenticated:
            return PostResult(
                platform=self.platform,
                status=PostStatus.FAILED,
                error_message="Not authenticated"
            )
        
        return PostResult(
            platform=self.platform,
            status=PostStatus.SUCCESS,
            post_id="browser_post_456",
            published_at=datetime.now()
        )
    
    async def get_post_metrics(self, post_id: str) -> Optional[PlatformMetrics]:
        # Browser automation platforms typically don't provide metrics
        return None
    
    async def format_content(self, content: PostContent) -> PostContent:
        return content


@pytest.fixture
def api_config():
    """Fixture for API-based platform configuration"""
    return PlatformConfig(
        platform=Platform.FACEBOOK,
        integration_type=IntegrationType.API,
        auth_method=AuthenticationMethod.OAUTH2,
        enabled=True,
        api_base_url="https://graph.facebook.com",
        api_version="v18.0",
        rate_limit_per_minute=200,
        max_title_length=100,
        max_description_length=1000,
        max_hashtags=10,
        supported_image_formats=["jpg", "png"],
        max_retries=3
    )


@pytest.fixture
def browser_config():
    """Fixture for browser automation platform configuration"""
    return PlatformConfig(
        platform=Platform.MEESHO,
        integration_type=IntegrationType.BROWSER_AUTOMATION,
        auth_method=AuthenticationMethod.SESSION_BASED,
        enabled=True,
        login_url="https://supplier.meesho.com/login",
        post_url="https://supplier.meesho.com/products/add",
        rate_limit_per_minute=10,
        max_title_length=200,
        max_description_length=5000,
        selectors={
            "email_input": "input[name='email']",
            "password_input": "input[name='password']",
            "login_button": "button[type='submit']"
        }
    )


@pytest.fixture
def sample_content():
    """Fixture for sample post content"""
    return PostContent(
        title="Test Product",
        description="This is a test product description",
        hashtags=["#test", "#product", "#handmade"],
        images=["https://example.com/image1.jpg", "https://example.com/image2.png"]
    )


@pytest.fixture
def api_credentials():
    """Fixture for API credentials"""
    return PlatformCredentials(
        platform=Platform.FACEBOOK,
        auth_method=AuthenticationMethod.OAUTH2,
        access_token="valid_token",
        refresh_token="refresh_token",
        expires_at=datetime.now() + timedelta(hours=1)
    )


@pytest.fixture
def browser_credentials():
    """Fixture for browser automation credentials"""
    return PlatformCredentials(
        platform=Platform.MEESHO,
        auth_method=AuthenticationMethod.SESSION_BASED,
        session_data={"username": "valid_user", "password": "password123"}
    )


class TestBasePlatformIntegration:
    """Test cases for BasePlatformIntegration abstract class"""
    
    def test_platform_info(self, api_config):
        """Test getting platform information"""
        integration = MockAPIIntegration(api_config)
        
        info = integration.get_platform_info()
        
        assert info["platform"] == Platform.FACEBOOK.value
        assert info["integration_type"] == IntegrationType.API.value
        assert info["auth_method"] == AuthenticationMethod.OAUTH2.value
        assert info["enabled"] is True
        assert info["max_retries"] == 3
    
    @pytest.mark.asyncio
    async def test_disconnect_default_implementation(self, api_config):
        """Test default disconnect implementation"""
        integration = MockAPIIntegration(api_config)
        
        result = await integration.disconnect()
        
        assert result is True


class TestAPIBasedIntegration:
    """Test cases for API-based integrations"""
    
    @pytest.mark.asyncio
    async def test_successful_authentication(self, api_config, api_credentials):
        """Test successful authentication with valid credentials"""
        integration = MockAPIIntegration(api_config)
        
        result = await integration.authenticate(api_credentials)
        
        assert result is True
        assert integration.authenticated is True
    
    @pytest.mark.asyncio
    async def test_failed_authentication(self, api_config):
        """Test failed authentication with invalid credentials"""
        integration = MockAPIIntegration(api_config)
        invalid_credentials = PlatformCredentials(
            platform=Platform.FACEBOOK,
            auth_method=AuthenticationMethod.OAUTH2,
            access_token="invalid_token"
        )
        
        result = await integration.authenticate(invalid_credentials)
        
        assert result is False
        assert integration.authenticated is False
    
    @pytest.mark.asyncio
    async def test_connection_validation(self, api_config, api_credentials):
        """Test connection validation"""
        integration = MockAPIIntegration(api_config)
        
        # Initially not connected
        assert await integration.validate_connection() is False
        
        # After authentication
        await integration.authenticate(api_credentials)
        assert await integration.validate_connection() is True
        
        # After connection becomes invalid
        integration.connection_valid = False
        assert await integration.validate_connection() is False
    
    @pytest.mark.asyncio
    async def test_successful_posting(self, api_config, api_credentials, sample_content):
        """Test successful content posting"""
        integration = MockAPIIntegration(api_config)
        await integration.authenticate(api_credentials)
        
        result = await integration.post_content(sample_content)
        
        assert result.platform == Platform.FACEBOOK
        assert result.status == PostStatus.SUCCESS
        assert result.post_id == "mock_post_123"
        assert result.published_at is not None
    
    @pytest.mark.asyncio
    async def test_failed_posting(self, api_config, api_credentials, sample_content):
        """Test failed content posting"""
        integration = MockAPIIntegration(api_config)
        await integration.authenticate(api_credentials)
        integration.should_fail_post = True
        
        result = await integration.post_content(sample_content)
        
        assert result.platform == Platform.FACEBOOK
        assert result.status == PostStatus.FAILED
        assert result.error_message == "Mock posting error"
    
    @pytest.mark.asyncio
    async def test_get_metrics(self, api_config, api_credentials):
        """Test retrieving post metrics"""
        integration = MockAPIIntegration(api_config)
        await integration.authenticate(api_credentials)
        
        # Valid post ID
        metrics = await integration.get_post_metrics("mock_post_123")
        assert metrics is not None
        assert metrics.platform == Platform.FACEBOOK
        assert metrics.post_id == "mock_post_123"
        assert metrics.likes == 10
        assert metrics.shares == 5
        
        # Invalid post ID
        metrics = await integration.get_post_metrics("invalid_post")
        assert metrics is None
    
    @pytest.mark.asyncio
    async def test_content_formatting(self, api_config, sample_content):
        """Test content formatting for platform requirements"""
        integration = MockAPIIntegration(api_config)
        
        # Content that exceeds title length limit
        long_content = PostContent(
            title="This is a very long title that exceeds the maximum length limit set in the configuration",
            description=sample_content.description,
            hashtags=sample_content.hashtags,
            images=sample_content.images
        )
        
        formatted = await integration.format_content(long_content)
        
        assert len(formatted.title) <= api_config.max_title_length
        assert formatted.title == long_content.title[:api_config.max_title_length]


class TestBrowserAutomationIntegration:
    """Test cases for browser automation integrations"""
    
    @pytest.mark.asyncio
    async def test_successful_authentication(self, browser_config, browser_credentials):
        """Test successful authentication with browser automation"""
        integration = MockBrowserIntegration(browser_config)
        
        result = await integration.authenticate(browser_credentials)
        
        assert result is True
        assert integration.authenticated is True
    
    @pytest.mark.asyncio
    async def test_failed_authentication(self, browser_config):
        """Test failed authentication with invalid credentials"""
        integration = MockBrowserIntegration(browser_config)
        invalid_credentials = PlatformCredentials(
            platform=Platform.MEESHO,
            auth_method=AuthenticationMethod.SESSION_BASED,
            session_data={"username": "invalid_user", "password": "wrong_password"}
        )
        
        result = await integration.authenticate(invalid_credentials)
        
        assert result is False
        assert integration.authenticated is False
    
    @pytest.mark.asyncio
    async def test_posting_without_authentication(self, browser_config, sample_content):
        """Test posting without authentication fails"""
        integration = MockBrowserIntegration(browser_config)
        
        result = await integration.post_content(sample_content)
        
        assert result.status == PostStatus.FAILED
        assert "Not authenticated" in result.error_message
    
    @pytest.mark.asyncio
    async def test_successful_posting(self, browser_config, browser_credentials, sample_content):
        """Test successful posting with browser automation"""
        integration = MockBrowserIntegration(browser_config)
        await integration.authenticate(browser_credentials)
        integration.session_active = True
        
        result = await integration.post_content(sample_content)
        
        assert result.status == PostStatus.SUCCESS
        assert result.post_id == "browser_post_456"
    
    @pytest.mark.asyncio
    async def test_metrics_not_available(self, browser_config, browser_credentials):
        """Test that metrics are typically not available for browser automation"""
        integration = MockBrowserIntegration(browser_config)
        await integration.authenticate(browser_credentials)
        
        metrics = await integration.get_post_metrics("any_post_id")
        
        assert metrics is None


class TestPlatformModels:
    """Test cases for platform integration models"""
    
    def test_platform_config_creation(self):
        """Test creating platform configuration"""
        config = PlatformConfig(
            platform=Platform.FACEBOOK,
            integration_type=IntegrationType.API,
            auth_method=AuthenticationMethod.OAUTH2,
            enabled=True,
            api_base_url="https://graph.facebook.com",
            max_title_length=100
        )
        
        assert config.platform == Platform.FACEBOOK
        assert config.integration_type == IntegrationType.API
        assert config.enabled is True
        assert config.max_retries == 3  # Default value
    
    def test_post_content_creation(self):
        """Test creating post content"""
        content = PostContent(
            title="Test Title",
            description="Test Description",
            hashtags=["#test", "#content"],
            images=["image1.jpg", "image2.png"],
            product_data={"price": 29.99, "category": "handmade"}
        )
        
        assert content.title == "Test Title"
        assert len(content.hashtags) == 2
        assert len(content.images) == 2
        assert content.product_data["price"] == 29.99
    
    def test_post_result_creation(self):
        """Test creating post result"""
        result = PostResult(
            platform=Platform.INSTAGRAM,
            status=PostStatus.SUCCESS,
            post_id="insta_123",
            url="https://instagram.com/p/insta_123",
            published_at=datetime.now()
        )
        
        assert result.platform == Platform.INSTAGRAM
        assert result.status == PostStatus.SUCCESS
        assert result.post_id == "insta_123"
        assert result.retry_count == 0  # Default value
    
    def test_platform_metrics_creation(self):
        """Test creating platform metrics"""
        metrics = PlatformMetrics(
            platform=Platform.PINTEREST,
            post_id="pin_456",
            likes=25,
            shares=10,
            comments=5,
            views=500,
            reach=1000,
            engagement_rate=0.08,
            retrieved_at=datetime.now()
        )
        
        assert metrics.platform == Platform.PINTEREST
        assert metrics.likes == 25
        assert metrics.engagement_rate == 0.08


class TestPlatformIntegrationErrors:
    """Test cases for platform integration exceptions"""
    
    def test_authentication_error(self):
        """Test authentication error creation"""
        error = AuthenticationError(
            "Invalid credentials",
            Platform.FACEBOOK,
            "AUTH_FAILED"
        )
        
        assert str(error) == "Invalid credentials"
        assert error.platform == Platform.FACEBOOK
        assert error.error_code == "AUTH_FAILED"
    
    def test_posting_error(self):
        """Test posting error creation"""
        error = PostingError(
            "Rate limit exceeded",
            Platform.INSTAGRAM,
            "RATE_LIMIT"
        )
        
        assert str(error) == "Rate limit exceeded"
        assert error.platform == Platform.INSTAGRAM
        assert error.error_code == "RATE_LIMIT"
    
    def test_base_integration_error(self):
        """Test base integration error"""
        error = PlatformIntegrationError(
            "Generic error",
            Platform.ETSY
        )
        
        assert str(error) == "Generic error"
        assert error.platform == Platform.ETSY
        assert error.error_code is None