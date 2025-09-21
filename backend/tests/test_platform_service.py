"""
Unit tests for unified platform service
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import asyncio

from app.services.platform_service import (
    PlatformService,
    get_platform_service
)
from app.services.platform_integration import (
    Platform,
    IntegrationType,
    AuthenticationMethod,
    PlatformConfig,
    PlatformCredentials,
    PostContent,
    PostResult,
    PostStatus,
    PlatformMetrics,
    AuthenticationError,
    PostingError
)


@pytest.fixture
def mock_registry():
    """Fixture for mock platform registry"""
    return Mock()


@pytest.fixture
def mock_config_manager():
    """Fixture for mock configuration manager"""
    return Mock()


@pytest.fixture
def mock_integration():
    """Fixture for mock platform integration"""
    integration = Mock()
    integration.authenticate = AsyncMock(return_value=True)
    integration.validate_connection = AsyncMock(return_value=True)
    integration.post_content = AsyncMock()
    integration.get_post_metrics = AsyncMock()
    integration.format_content = AsyncMock()
    integration.disconnect = AsyncMock(return_value=True)
    return integration


@pytest.fixture
def platform_service(mock_registry, mock_config_manager):
    """Fixture for platform service with mocked dependencies"""
    return PlatformService(mock_registry, mock_config_manager)


@pytest.fixture
def sample_credentials():
    """Fixture for sample credentials"""
    return PlatformCredentials(
        platform=Platform.FACEBOOK,
        auth_method=AuthenticationMethod.OAUTH2,
        access_token="test_token"
    )


@pytest.fixture
def sample_content():
    """Fixture for sample post content"""
    return PostContent(
        title="Test Product",
        description="Test description",
        hashtags=["#test", "#product"],
        images=["https://example.com/image.jpg"]
    )


@pytest.fixture
def sample_config():
    """Fixture for sample platform configuration"""
    return PlatformConfig(
        platform=Platform.FACEBOOK,
        integration_type=IntegrationType.API,
        auth_method=AuthenticationMethod.OAUTH2,
        enabled=True,
        max_title_length=100,
        max_description_length=1000,
        max_hashtags=10,
        supported_image_formats=["jpg", "png"]
    )


class TestPlatformService:
    """Test cases for PlatformService class"""
    
    @pytest.mark.asyncio
    async def test_authenticate_platform_success(
        self, 
        platform_service, 
        mock_registry, 
        mock_integration, 
        sample_credentials
    ):
        """Test successful platform authentication"""
        mock_registry.get_platform_integration.return_value = mock_integration
        
        result = await platform_service.authenticate_platform(
            Platform.FACEBOOK, 
            "user123", 
            sample_credentials
        )
        
        assert result is True
        mock_integration.authenticate.assert_called_once_with(sample_credentials)
    
    @pytest.mark.asyncio
    async def test_authenticate_platform_not_available(
        self, 
        platform_service, 
        mock_registry, 
        sample_credentials
    ):
        """Test authentication when platform is not available"""
        mock_registry.get_platform_integration.return_value = None
        
        with pytest.raises(AuthenticationError, match="is not available"):
            await platform_service.authenticate_platform(
                Platform.FACEBOOK, 
                "user123", 
                sample_credentials
            )
    
    @pytest.mark.asyncio
    async def test_authenticate_platform_failure(
        self, 
        platform_service, 
        mock_registry, 
        mock_integration, 
        sample_credentials
    ):
        """Test authentication failure"""
        mock_registry.get_platform_integration.return_value = mock_integration
        mock_integration.authenticate.return_value = False
        
        result = await platform_service.authenticate_platform(
            Platform.FACEBOOK, 
            "user123", 
            sample_credentials
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_authenticate_platform_exception(
        self, 
        platform_service, 
        mock_registry, 
        mock_integration, 
        sample_credentials
    ):
        """Test authentication with exception"""
        mock_registry.get_platform_integration.return_value = mock_integration
        mock_integration.authenticate.side_effect = Exception("Auth error")
        
        with pytest.raises(AuthenticationError, match="Failed to authenticate"):
            await platform_service.authenticate_platform(
                Platform.FACEBOOK, 
                "user123", 
                sample_credentials
            )
    
    @pytest.mark.asyncio
    async def test_validate_platform_connection_success(
        self, 
        platform_service, 
        mock_registry, 
        mock_integration
    ):
        """Test successful connection validation"""
        mock_registry.get_platform_integration.return_value = mock_integration
        
        result = await platform_service.validate_platform_connection(
            Platform.FACEBOOK, 
            "user123"
        )
        
        assert result is True
        mock_integration.validate_connection.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_platform_connection_not_available(
        self, 
        platform_service, 
        mock_registry
    ):
        """Test connection validation when platform not available"""
        mock_registry.get_platform_integration.return_value = None
        
        result = await platform_service.validate_platform_connection(
            Platform.FACEBOOK, 
            "user123"
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_validate_platform_connection_exception(
        self, 
        platform_service, 
        mock_registry, 
        mock_integration
    ):
        """Test connection validation with exception"""
        mock_registry.get_platform_integration.return_value = mock_integration
        mock_integration.validate_connection.side_effect = Exception("Connection error")
        
        result = await platform_service.validate_platform_connection(
            Platform.FACEBOOK, 
            "user123"
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_post_to_platform_success(
        self, 
        platform_service, 
        mock_registry, 
        mock_integration, 
        sample_content
    ):
        """Test successful posting to platform"""
        mock_registry.get_platform_integration.return_value = mock_integration
        mock_integration.format_content.return_value = sample_content
        mock_integration.post_content.return_value = PostResult(
            platform=Platform.FACEBOOK,
            status=PostStatus.SUCCESS,
            post_id="post123"
        )
        
        result = await platform_service.post_to_platform(
            Platform.FACEBOOK, 
            "user123", 
            sample_content
        )
        
        assert result.status == PostStatus.SUCCESS
        assert result.post_id == "post123"
        mock_integration.format_content.assert_called_once_with(sample_content)
        mock_integration.post_content.assert_called_once_with(sample_content)
    
    @pytest.mark.asyncio
    async def test_post_to_platform_not_available(
        self, 
        platform_service, 
        mock_registry, 
        sample_content
    ):
        """Test posting when platform not available"""
        mock_registry.get_platform_integration.return_value = None
        
        result = await platform_service.post_to_platform(
            Platform.FACEBOOK, 
            "user123", 
            sample_content
        )
        
        assert result.status == PostStatus.FAILED
        assert result.error_code == "PLATFORM_NOT_AVAILABLE"
    
    @pytest.mark.asyncio
    async def test_post_to_platform_exception(
        self, 
        platform_service, 
        mock_registry, 
        mock_integration, 
        sample_content
    ):
        """Test posting with exception"""
        mock_registry.get_platform_integration.return_value = mock_integration
        mock_integration.format_content.side_effect = Exception("Format error")
        
        result = await platform_service.post_to_platform(
            Platform.FACEBOOK, 
            "user123", 
            sample_content
        )
        
        assert result.status == PostStatus.FAILED
        assert result.error_code == "POSTING_ERROR"
    
    @pytest.mark.asyncio
    async def test_post_to_multiple_platforms_success(
        self, 
        platform_service, 
        mock_registry, 
        sample_content
    ):
        """Test posting to multiple platforms successfully"""
        # Mock integrations for different platforms
        facebook_integration = Mock()
        facebook_integration.format_content = AsyncMock(return_value=sample_content)
        facebook_integration.post_content = AsyncMock(return_value=PostResult(
            platform=Platform.FACEBOOK,
            status=PostStatus.SUCCESS,
            post_id="fb_post123"
        ))
        
        instagram_integration = Mock()
        instagram_integration.format_content = AsyncMock(return_value=sample_content)
        instagram_integration.post_content = AsyncMock(return_value=PostResult(
            platform=Platform.INSTAGRAM,
            status=PostStatus.SUCCESS,
            post_id="ig_post456"
        ))
        
        def get_integration(platform, user_id):
            if platform == Platform.FACEBOOK:
                return facebook_integration
            elif platform == Platform.INSTAGRAM:
                return instagram_integration
            return None
        
        mock_registry.get_platform_integration.side_effect = get_integration
        
        results = await platform_service.post_to_multiple_platforms(
            [Platform.FACEBOOK, Platform.INSTAGRAM],
            "user123",
            sample_content
        )
        
        assert len(results) == 2
        assert results[0].status == PostStatus.SUCCESS
        assert results[0].post_id == "fb_post123"
        assert results[1].status == PostStatus.SUCCESS
        assert results[1].post_id == "ig_post456"
    
    @pytest.mark.asyncio
    async def test_post_to_multiple_platforms_partial_failure(
        self, 
        platform_service, 
        mock_registry, 
        sample_content
    ):
        """Test posting to multiple platforms with partial failure"""
        # Mock successful Facebook integration
        facebook_integration = Mock()
        facebook_integration.format_content = AsyncMock(return_value=sample_content)
        facebook_integration.post_content = AsyncMock(return_value=PostResult(
            platform=Platform.FACEBOOK,
            status=PostStatus.SUCCESS,
            post_id="fb_post123"
        ))
        
        def get_integration(platform, user_id):
            if platform == Platform.FACEBOOK:
                return facebook_integration
            return None  # Instagram not available
        
        mock_registry.get_platform_integration.side_effect = get_integration
        
        results = await platform_service.post_to_multiple_platforms(
            [Platform.FACEBOOK, Platform.INSTAGRAM],
            "user123",
            sample_content
        )
        
        assert len(results) == 2
        assert results[0].status == PostStatus.SUCCESS
        assert results[1].status == PostStatus.FAILED
        assert results[1].error_code == "PLATFORM_NOT_AVAILABLE"
    
    @pytest.mark.asyncio
    async def test_get_platform_metrics_success(
        self, 
        platform_service, 
        mock_registry, 
        mock_integration
    ):
        """Test successful metrics retrieval"""
        mock_registry.get_platform_integration.return_value = mock_integration
        mock_integration.get_post_metrics.return_value = PlatformMetrics(
            platform=Platform.FACEBOOK,
            post_id="post123",
            likes=10,
            shares=5,
            retrieved_at=datetime.now()
        )
        
        metrics = await platform_service.get_platform_metrics(
            Platform.FACEBOOK,
            "user123",
            "post123"
        )
        
        assert metrics is not None
        assert metrics.platform == Platform.FACEBOOK
        assert metrics.likes == 10
        mock_integration.get_post_metrics.assert_called_once_with("post123")
    
    @pytest.mark.asyncio
    async def test_get_platform_metrics_not_available(
        self, 
        platform_service, 
        mock_registry
    ):
        """Test metrics retrieval when platform not available"""
        mock_registry.get_platform_integration.return_value = None
        
        metrics = await platform_service.get_platform_metrics(
            Platform.FACEBOOK,
            "user123",
            "post123"
        )
        
        assert metrics is None
    
    @pytest.mark.asyncio
    async def test_get_metrics_for_multiple_posts(
        self, 
        platform_service, 
        mock_registry
    ):
        """Test getting metrics for multiple posts"""
        # Mock integrations
        facebook_integration = Mock()
        facebook_integration.get_post_metrics = AsyncMock(return_value=PlatformMetrics(
            platform=Platform.FACEBOOK,
            post_id="fb_post123",
            likes=10,
            retrieved_at=datetime.now()
        ))
        
        instagram_integration = Mock()
        instagram_integration.get_post_metrics = AsyncMock(return_value=PlatformMetrics(
            platform=Platform.INSTAGRAM,
            post_id="ig_post456",
            likes=20,
            retrieved_at=datetime.now()
        ))
        
        def get_integration(platform, user_id):
            if platform == Platform.FACEBOOK:
                return facebook_integration
            elif platform == Platform.INSTAGRAM:
                return instagram_integration
            return None
        
        mock_registry.get_platform_integration.side_effect = get_integration
        
        post_data = [
            {"platform": Platform.FACEBOOK, "user_id": "user123", "post_id": "fb_post123"},
            {"platform": Platform.INSTAGRAM, "user_id": "user123", "post_id": "ig_post456"}
        ]
        
        results = await platform_service.get_metrics_for_multiple_posts(post_data)
        
        assert len(results) == 2
        assert results[0].likes == 10
        assert results[1].likes == 20
    
    def test_get_available_platforms(self, platform_service, mock_registry):
        """Test getting available platforms"""
        mock_registry.get_available_platforms.return_value = [
            Platform.FACEBOOK, 
            Platform.INSTAGRAM
        ]
        
        platforms = platform_service.get_available_platforms()
        
        assert Platform.FACEBOOK in platforms
        assert Platform.INSTAGRAM in platforms
        mock_registry.get_available_platforms.assert_called_once()
    
    def test_get_enabled_platforms(self, platform_service, mock_config_manager):
        """Test getting enabled platforms"""
        mock_config_manager.get_enabled_platforms.return_value = [Platform.FACEBOOK]
        
        platforms = platform_service.get_enabled_platforms()
        
        assert Platform.FACEBOOK in platforms
        mock_config_manager.get_enabled_platforms.assert_called_once()
    
    def test_get_platform_info(self, platform_service, mock_config_manager, sample_config):
        """Test getting platform information"""
        mock_config_manager.get_config.return_value = sample_config
        
        info = platform_service.get_platform_info(Platform.FACEBOOK)
        
        assert info is not None
        assert info["platform"] == Platform.FACEBOOK.value
        assert info["integration_type"] == IntegrationType.API.value
        assert info["enabled"] is True
        assert info["max_title_length"] == 100
    
    def test_get_platform_info_not_configured(self, platform_service, mock_config_manager):
        """Test getting info for unconfigured platform"""
        mock_config_manager.get_config.return_value = None
        
        info = platform_service.get_platform_info(Platform.FACEBOOK)
        
        assert info is None
    
    def test_get_all_platform_info(self, platform_service, mock_config_manager, sample_config):
        """Test getting all platform information"""
        def get_config(platform):
            if platform == Platform.FACEBOOK:
                return sample_config
            return None
        
        mock_config_manager.get_config.side_effect = get_config
        
        with patch('app.services.platform_service.Platform') as mock_platform_enum:
            mock_platform_enum.__iter__ = Mock(return_value=iter([Platform.FACEBOOK, Platform.INSTAGRAM]))
            
            all_info = platform_service.get_all_platform_info()
            
            assert "facebook" in all_info
            assert "instagram" not in all_info  # Not configured
    
    @pytest.mark.asyncio
    async def test_disconnect_platform_success(
        self, 
        platform_service, 
        mock_registry, 
        mock_integration
    ):
        """Test successful platform disconnection"""
        mock_registry.get_platform_integration.return_value = mock_integration
        
        result = await platform_service.disconnect_platform(Platform.FACEBOOK, "user123")
        
        assert result is True
        mock_integration.disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_disconnect_platform_not_connected(
        self, 
        platform_service, 
        mock_registry
    ):
        """Test disconnecting when not connected"""
        mock_registry.get_platform_integration.return_value = None
        
        result = await platform_service.disconnect_platform(Platform.FACEBOOK, "user123")
        
        assert result is True  # Already disconnected
    
    @pytest.mark.asyncio
    async def test_disconnect_all_platforms(
        self, 
        platform_service, 
        mock_registry
    ):
        """Test disconnecting from all platforms"""
        mock_registry.get_available_platforms.return_value = [
            Platform.FACEBOOK, 
            Platform.INSTAGRAM
        ]
        
        # Mock integrations
        facebook_integration = Mock()
        facebook_integration.disconnect = AsyncMock(return_value=True)
        
        instagram_integration = Mock()
        instagram_integration.disconnect = AsyncMock(return_value=False)
        
        def get_integration(platform, user_id):
            if platform == Platform.FACEBOOK:
                return facebook_integration
            elif platform == Platform.INSTAGRAM:
                return instagram_integration
            return None
        
        mock_registry.get_platform_integration.side_effect = get_integration
        
        results = await platform_service.disconnect_all_platforms("user123")
        
        assert results[Platform.FACEBOOK] is True
        assert results[Platform.INSTAGRAM] is False
        mock_registry.cleanup_user_instances.assert_called_once_with("user123")
    
    def test_validate_content_for_platform_valid(
        self, 
        platform_service, 
        mock_config_manager, 
        sample_config, 
        sample_content
    ):
        """Test content validation for platform - valid content"""
        mock_config_manager.get_config.return_value = sample_config
        
        errors = platform_service.validate_content_for_platform(
            Platform.FACEBOOK, 
            sample_content
        )
        
        assert len(errors) == 0
    
    def test_validate_content_for_platform_title_too_long(
        self, 
        platform_service, 
        mock_config_manager, 
        sample_config
    ):
        """Test content validation - title too long"""
        mock_config_manager.get_config.return_value = sample_config
        
        long_content = PostContent(
            title="x" * 150,  # Exceeds max_title_length of 100
            description="Test description",
            hashtags=["#test"],
            images=["https://example.com/image.jpg"]
        )
        
        errors = platform_service.validate_content_for_platform(
            Platform.FACEBOOK, 
            long_content
        )
        
        assert len(errors) > 0
        assert any("Title exceeds maximum length" in error for error in errors)
    
    def test_validate_content_for_platform_too_many_hashtags(
        self, 
        platform_service, 
        mock_config_manager, 
        sample_config
    ):
        """Test content validation - too many hashtags"""
        mock_config_manager.get_config.return_value = sample_config
        
        hashtag_content = PostContent(
            title="Test title",
            description="Test description",
            hashtags=["#tag" + str(i) for i in range(15)],  # Exceeds max_hashtags of 10
            images=["https://example.com/image.jpg"]
        )
        
        errors = platform_service.validate_content_for_platform(
            Platform.FACEBOOK, 
            hashtag_content
        )
        
        assert len(errors) > 0
        assert any("hashtags exceeds maximum" in error for error in errors)
    
    def test_validate_content_for_platform_unsupported_image_format(
        self, 
        platform_service, 
        mock_config_manager, 
        sample_config
    ):
        """Test content validation - unsupported image format"""
        mock_config_manager.get_config.return_value = sample_config
        
        image_content = PostContent(
            title="Test title",
            description="Test description",
            hashtags=["#test"],
            images=["https://example.com/image.gif"]  # gif not in supported_image_formats
        )
        
        errors = platform_service.validate_content_for_platform(
            Platform.FACEBOOK, 
            image_content
        )
        
        assert len(errors) > 0
        assert any("Image format 'gif' is not supported" in error for error in errors)
    
    def test_validate_content_for_platform_not_configured(
        self, 
        platform_service, 
        mock_config_manager, 
        sample_content
    ):
        """Test content validation for unconfigured platform"""
        mock_config_manager.get_config.return_value = None
        
        errors = platform_service.validate_content_for_platform(
            Platform.FACEBOOK, 
            sample_content
        )
        
        assert len(errors) > 0
        assert any("is not configured" in error for error in errors)


class TestGlobalFunctions:
    """Test cases for global convenience functions"""
    
    def test_get_platform_service(self):
        """Test getting global platform service instance"""
        service = get_platform_service()
        
        assert isinstance(service, PlatformService)
        
        # Should return same instance
        service2 = get_platform_service()
        assert service is service2


class TestPlatformServiceErrorHandling:
    """Test error handling in platform service"""
    
    @pytest.mark.asyncio
    async def test_post_to_multiple_platforms_with_exception(
        self, 
        platform_service, 
        mock_registry, 
        sample_content
    ):
        """Test posting to multiple platforms when one raises exception"""
        # Mock successful Facebook integration
        facebook_integration = Mock()
        facebook_integration.format_content = AsyncMock(return_value=sample_content)
        facebook_integration.post_content = AsyncMock(return_value=PostResult(
            platform=Platform.FACEBOOK,
            status=PostStatus.SUCCESS,
            post_id="fb_post123"
        ))
        
        # Mock Instagram integration that raises exception
        instagram_integration = Mock()
        instagram_integration.format_content = AsyncMock(side_effect=Exception("Format error"))
        
        def get_integration(platform, user_id):
            if platform == Platform.FACEBOOK:
                return facebook_integration
            elif platform == Platform.INSTAGRAM:
                return instagram_integration
            return None
        
        mock_registry.get_platform_integration.side_effect = get_integration
        
        results = await platform_service.post_to_multiple_platforms(
            [Platform.FACEBOOK, Platform.INSTAGRAM],
            "user123",
            sample_content
        )
        
        assert len(results) == 2
        assert results[0].status == PostStatus.SUCCESS
        assert results[1].status == PostStatus.FAILED
        assert results[1].error_code == "POSTING_ERROR"
    
    @pytest.mark.asyncio
    async def test_get_metrics_for_multiple_posts_with_exception(
        self, 
        platform_service, 
        mock_registry
    ):
        """Test getting metrics when one platform raises exception"""
        # Mock successful Facebook integration
        facebook_integration = Mock()
        facebook_integration.get_post_metrics = AsyncMock(return_value=PlatformMetrics(
            platform=Platform.FACEBOOK,
            post_id="fb_post123",
            likes=10,
            retrieved_at=datetime.now()
        ))
        
        # Mock Instagram integration that raises exception
        instagram_integration = Mock()
        instagram_integration.get_post_metrics = AsyncMock(side_effect=Exception("Metrics error"))
        
        def get_integration(platform, user_id):
            if platform == Platform.FACEBOOK:
                return facebook_integration
            elif platform == Platform.INSTAGRAM:
                return instagram_integration
            return None
        
        mock_registry.get_platform_integration.side_effect = get_integration
        
        post_data = [
            {"platform": Platform.FACEBOOK, "user_id": "user123", "post_id": "fb_post123"},
            {"platform": Platform.INSTAGRAM, "user_id": "user123", "post_id": "ig_post456"}
        ]
        
        results = await platform_service.get_metrics_for_multiple_posts(post_data)
        
        assert len(results) == 2
        assert results[0] is not None
        assert results[0].likes == 10
        assert results[1] is None  # Exception converted to None