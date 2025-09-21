"""
Tests for Platform-Specific OAuth Integrations

This module contains tests for the concrete OAuth integration implementations
for each supported platform.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.services.platform_oauth_integrations import (
    FacebookOAuthIntegration,
    InstagramOAuthIntegration,
    EtsyOAuthIntegration,
    PinterestOAuthIntegration,
    ShopifyOAuthIntegration,
    create_oauth_integration
)
from app.services.oauth_service import OAuthService
from app.services.platform_integration import (
    Platform, 
    PostContent, 
    PostStatus, 
    PlatformCredentials,
    AuthenticationMethod
)
from app.models import PlatformConnection


class TestFacebookOAuthIntegration:
    """Test Facebook OAuth integration"""
    
    @pytest.fixture
    def mock_oauth_service(self):
        """Mock OAuth service"""
        service = Mock(spec=OAuthService)
        service.get_decrypted_credentials.return_value = PlatformCredentials(
            platform=Platform.FACEBOOK,
            auth_method=AuthenticationMethod.OAUTH2,
            access_token="test_access_token"
        )
        return service
    
    @pytest.fixture
    def mock_connection(self):
        """Mock platform connection"""
        return PlatformConnection(
            id="conn123",
            user_id="user123",
            platform=Platform.FACEBOOK.value,
            access_token="encrypted_token",
            is_active=True
        )
    
    @pytest.fixture
    def facebook_integration(self, mock_oauth_service, mock_connection):
        """Facebook integration instance"""
        return FacebookOAuthIntegration(mock_oauth_service, mock_connection)
    
    @pytest.mark.asyncio
    async def test_authenticate(self, facebook_integration):
        """Test Facebook authentication"""
        credentials = PlatformCredentials(
            platform=Platform.FACEBOOK,
            auth_method=AuthenticationMethod.OAUTH2,
            access_token="test_token"
        )
        
        result = await facebook_integration.authenticate(credentials)
        assert result is True
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_validate_connection_success(self, mock_httpx, facebook_integration):
        """Test successful Facebook connection validation"""
        mock_client = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        mock_client.get.return_value.status_code = 200
        
        result = await facebook_integration.validate_connection()
        assert result is True
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_validate_connection_failure(self, mock_httpx, facebook_integration):
        """Test failed Facebook connection validation"""
        mock_client = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        mock_client.get.return_value.status_code = 401
        
        result = await facebook_integration.validate_connection()
        assert result is False
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_post_content_success(self, mock_httpx, facebook_integration):
        """Test successful Facebook content posting"""
        mock_client = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        # Mock pages response
        mock_client.get.return_value.status_code = 200
        mock_client.get.return_value.json.return_value = {
            "data": [
                {
                    "id": "page123",
                    "access_token": "page_token",
                    "name": "Test Page"
                }
            ]
        }
        
        # Mock post response
        mock_client.post.return_value.status_code = 200
        mock_client.post.return_value.json.return_value = {
            "id": "post123"
        }
        
        content = PostContent(
            title="Test Product",
            description="Test description",
            hashtags=["#handmade", "#art"],
            images=["https://example.com/image.jpg"]
        )
        
        result = await facebook_integration.post_content(content)
        
        assert result.status == PostStatus.SUCCESS
        assert result.post_id == "post123"
        assert result.platform == Platform.FACEBOOK
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_post_content_no_pages(self, mock_httpx, facebook_integration):
        """Test Facebook posting with no pages"""
        mock_client = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        mock_client.get.return_value.status_code = 200
        mock_client.get.return_value.json.return_value = {"data": []}
        
        content = PostContent(
            title="Test Product",
            description="Test description",
            hashtags=["#handmade"],
            images=[]
        )
        
        result = await facebook_integration.post_content(content)
        
        assert result.status == PostStatus.FAILED
        assert result.error_code == "NO_PAGES_FOUND"
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_get_post_metrics(self, mock_httpx, facebook_integration):
        """Test getting Facebook post metrics"""
        mock_client = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        mock_client.get.return_value.status_code = 200
        mock_client.get.return_value.json.return_value = {
            "likes": {"summary": {"total_count": 10}},
            "comments": {"summary": {"total_count": 5}},
            "shares": {"count": 3}
        }
        
        metrics = await facebook_integration.get_post_metrics("post123")
        
        assert metrics is not None
        assert metrics.likes == 10
        assert metrics.comments == 5
        assert metrics.shares == 3
        assert metrics.platform == Platform.FACEBOOK
    
    @pytest.mark.asyncio
    async def test_format_content(self, facebook_integration):
        """Test Facebook content formatting"""
        content = PostContent(
            title="Test Product",
            description="Test description",
            hashtags=["handmade", "art"],  # Without # prefix
            images=[]
        )
        
        formatted = await facebook_integration.format_content(content)
        
        assert formatted.hashtags == ["#handmade", "#art"]


class TestInstagramOAuthIntegration:
    """Test Instagram OAuth integration"""
    
    @pytest.fixture
    def mock_oauth_service(self):
        """Mock OAuth service"""
        service = Mock(spec=OAuthService)
        service.get_decrypted_credentials.return_value = PlatformCredentials(
            platform=Platform.INSTAGRAM,
            auth_method=AuthenticationMethod.OAUTH2,
            access_token="test_access_token"
        )
        return service
    
    @pytest.fixture
    def mock_connection(self):
        """Mock platform connection"""
        return PlatformConnection(
            id="conn123",
            user_id="user123",
            platform=Platform.INSTAGRAM.value,
            access_token="encrypted_token",
            is_active=True
        )
    
    @pytest.fixture
    def instagram_integration(self, mock_oauth_service, mock_connection):
        """Instagram integration instance"""
        return InstagramOAuthIntegration(mock_oauth_service, mock_connection)
    
    @patch('httpx.AsyncClient')
    async def test_post_content_success(self, mock_httpx, instagram_integration):
        """Test successful Instagram content posting"""
        mock_client = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        # Mock pages response
        mock_client.get.return_value.status_code = 200
        mock_client.get.return_value.json.return_value = {
            "data": [
                {
                    "instagram_business_account": {"id": "ig_account_123"}
                }
            ]
        }
        
        # Mock container creation
        mock_client.post.return_value.status_code = 200
        mock_client.post.return_value.json.side_effect = [
            {"id": "container123"},  # Media container
            {"id": "post123"}       # Published post
        ]
        
        content = PostContent(
            title="Test Product",
            description="Test description",
            hashtags=["#handmade", "#art"],
            images=["https://example.com/image.jpg"]
        )
        
        result = await instagram_integration.post_content(content)
        
        assert result.status == PostStatus.SUCCESS
        assert result.post_id == "post123"
        assert result.platform == Platform.INSTAGRAM
    
    @patch('httpx.AsyncClient')
    async def test_post_content_no_image(self, mock_httpx, instagram_integration):
        """Test Instagram posting without image"""
        content = PostContent(
            title="Test Product",
            description="Test description",
            hashtags=["#handmade"],
            images=[]  # No images
        )
        
        result = await instagram_integration.post_content(content)
        
        assert result.status == PostStatus.FAILED
        assert result.error_code == "NO_IMAGE_PROVIDED"
    
    async def test_format_content_long_description(self, instagram_integration):
        """Test Instagram content formatting with long description"""
        long_description = "A" * 2500  # Exceeds Instagram limit
        
        content = PostContent(
            title="Test Product",
            description=long_description,
            hashtags=["handmade"] * 35,  # Exceeds hashtag limit
            images=[]
        )
        
        formatted = await instagram_integration.format_content(content)
        
        assert len(formatted.description) <= 2200
        assert formatted.description.endswith("...")
        assert len(formatted.hashtags) <= 30


class TestEtsyOAuthIntegration:
    """Test Etsy OAuth integration wrapper"""
    
    @pytest.fixture
    def mock_oauth_service(self):
        """Mock OAuth service"""
        service = Mock(spec=OAuthService)
        service.get_decrypted_credentials.return_value = PlatformCredentials(
            platform=Platform.ETSY,
            auth_method=AuthenticationMethod.OAUTH2,
            access_token="test_access_token"
        )
        return service
    
    @pytest.fixture
    def mock_connection(self):
        """Mock platform connection"""
        return PlatformConnection(
            id="conn123",
            user_id="user123",
            platform=Platform.ETSY.value,
            access_token="encrypted_token",
            is_active=True
        )
    
    @pytest.fixture
    def etsy_integration(self, mock_oauth_service, mock_connection):
        """Etsy integration instance"""
        return EtsyOAuthIntegration(mock_oauth_service, mock_connection)
    
    @patch('httpx.AsyncClient')
    async def test_post_content_success(self, mock_httpx, etsy_integration):
        """Test successful Etsy listing creation through wrapper"""
        mock_client = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        # Mock user info response
        mock_client.get.side_effect = [
            # User info
            Mock(status_code=200, json=lambda: {"user_id": "user123"}),
            # Shops info
            Mock(status_code=200, json=lambda: {
                "results": [{"shop_id": "shop123"}]
            }),
            # Shipping templates
            Mock(status_code=200, json=lambda: {"results": []})
        ]
        
        # Mock listing creation
        mock_client.post.side_effect = [
            # Listing creation
            Mock(status_code=201, json=lambda: {"listing_id": "listing123"}),
            # Image upload
            Mock(status_code=201, json=lambda: {"listing_image_id": "img1"})
        ]
        
        content = PostContent(
            title="Test Product",
            description="Test description",
            hashtags=["handmade", "art"],
            images=["https://example.com/image.jpg"],
            product_data={"price": "25.00"}
        )
        
        result = await etsy_integration.post_content(content)
        
        assert result.status == PostStatus.SUCCESS
        assert result.post_id == "listing123"
        assert result.platform == Platform.ETSY
        assert "etsy.com/listing/listing123" in result.url
    
    async def test_format_content_long_title(self, etsy_integration):
        """Test Etsy content formatting with long title"""
        long_title = "A" * 150  # Exceeds Etsy limit
        
        content = PostContent(
            title=long_title,
            description="Test description",
            hashtags=["handmade"] * 20,  # Exceeds material limit
            images=[]
        )
        
        formatted = await etsy_integration.format_content(content)
        
        assert len(formatted.title) <= 140
        assert formatted.title.endswith("...")
        assert len(formatted.hashtags) <= 13


class TestPinterestOAuthIntegration:
    """Test Pinterest OAuth integration"""
    
    @pytest.fixture
    def mock_oauth_service(self):
        """Mock OAuth service"""
        service = Mock(spec=OAuthService)
        service.get_decrypted_credentials.return_value = PlatformCredentials(
            platform=Platform.PINTEREST,
            auth_method=AuthenticationMethod.OAUTH2,
            access_token="test_access_token"
        )
        return service
    
    @pytest.fixture
    def mock_connection(self):
        """Mock platform connection"""
        return PlatformConnection(
            id="conn123",
            user_id="user123",
            platform=Platform.PINTEREST.value,
            access_token="encrypted_token",
            is_active=True
        )
    
    @pytest.fixture
    def pinterest_integration(self, mock_oauth_service, mock_connection):
        """Pinterest integration instance"""
        return PinterestOAuthIntegration(mock_oauth_service, mock_connection)
    
    @patch('httpx.AsyncClient')
    async def test_post_content_success(self, mock_httpx, pinterest_integration):
        """Test successful Pinterest pin creation"""
        mock_client = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        # Mock boards response
        mock_client.get.return_value.status_code = 200
        mock_client.get.return_value.json.return_value = {
            "items": [{"id": "board123", "name": "Test Board"}]
        }
        
        # Mock pin creation
        mock_client.post.return_value.status_code = 201
        mock_client.post.return_value.json.return_value = {
            "id": "pin123",
            "url": "https://pinterest.com/pin/pin123"
        }
        
        content = PostContent(
            title="Test Product",
            description="Test description",
            hashtags=["#handmade", "#art"],
            images=["https://example.com/image.jpg"]
        )
        
        result = await pinterest_integration.post_content(content)
        
        assert result.status == PostStatus.SUCCESS
        assert result.post_id == "pin123"
        assert result.platform == Platform.PINTEREST
        assert result.url == "https://pinterest.com/pin/pin123"
    
    async def test_format_content_limits(self, pinterest_integration):
        """Test Pinterest content formatting with limits"""
        long_title = "A" * 150
        long_description = "B" * 600
        
        content = PostContent(
            title=long_title,
            description=long_description,
            hashtags=["tag"] * 25,  # Exceeds limit
            images=[]
        )
        
        formatted = await pinterest_integration.format_content(content)
        
        assert len(formatted.title) <= 100
        assert len(formatted.description) <= 500


class TestShopifyOAuthIntegration:
    """Test Shopify OAuth integration"""
    
    @pytest.fixture
    def mock_oauth_service(self):
        """Mock OAuth service"""
        service = Mock(spec=OAuthService)
        service.get_decrypted_credentials.return_value = PlatformCredentials(
            platform=Platform.SHOPIFY,
            auth_method=AuthenticationMethod.OAUTH2,
            access_token="test_access_token"
        )
        return service
    
    @pytest.fixture
    def mock_connection(self):
        """Mock platform connection"""
        return PlatformConnection(
            id="conn123",
            user_id="user123",
            platform=Platform.SHOPIFY.value,
            access_token="encrypted_token",
            is_active=True,
            platform_data={"shop_domain": "test-shop"}
        )
    
    @pytest.fixture
    def shopify_integration(self, mock_oauth_service, mock_connection):
        """Shopify integration instance"""
        return ShopifyOAuthIntegration(mock_oauth_service, mock_connection)
    
    @patch('httpx.AsyncClient')
    async def test_post_content_success(self, mock_httpx, shopify_integration):
        """Test successful Shopify product creation"""
        mock_client = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        # Mock product creation
        mock_client.post.return_value.status_code = 201
        mock_client.post.return_value.json.return_value = {
            "product": {
                "id": "product123",
                "handle": "test-product"
            }
        }
        
        content = PostContent(
            title="Test Product",
            description="Test description",
            hashtags=["handmade", "art"],
            images=["https://example.com/image.jpg"],
            product_data={"price": "25.00", "quantity": 5}
        )
        
        result = await shopify_integration.post_content(content)
        
        assert result.status == PostStatus.SUCCESS
        assert result.post_id == "product123"
        assert result.platform == Platform.SHOPIFY
        assert "test-shop.myshopify.com/products/test-product" in result.url
    
    async def test_format_content(self, shopify_integration):
        """Test Shopify content formatting"""
        content = PostContent(
            title="Test Product",
            description="Test description",
            hashtags=["handmade", "art"],
            images=[]
        )
        
        formatted = await shopify_integration.format_content(content)
        
        # Shopify is flexible, should return copy
        assert formatted.title == content.title
        assert formatted.description == content.description
        assert formatted.hashtags == content.hashtags


class TestIntegrationFactory:
    """Test integration factory function"""
    
    @pytest.fixture
    def mock_oauth_service(self):
        """Mock OAuth service"""
        return Mock(spec=OAuthService)
    
    @pytest.fixture
    def mock_connection(self):
        """Mock platform connection"""
        return PlatformConnection(
            id="conn123",
            user_id="user123",
            platform=Platform.FACEBOOK.value,
            access_token="encrypted_token",
            is_active=True
        )
    
    def test_create_facebook_integration(self, mock_oauth_service, mock_connection):
        """Test creating Facebook integration"""
        integration = create_oauth_integration(
            Platform.FACEBOOK,
            mock_oauth_service,
            mock_connection
        )
        
        assert isinstance(integration, FacebookOAuthIntegration)
        assert integration.platform == Platform.FACEBOOK
    
    def test_create_instagram_integration(self, mock_oauth_service, mock_connection):
        """Test creating Instagram integration"""
        mock_connection.platform = Platform.INSTAGRAM.value
        
        integration = create_oauth_integration(
            Platform.INSTAGRAM,
            mock_oauth_service,
            mock_connection
        )
        
        assert isinstance(integration, InstagramOAuthIntegration)
        assert integration.platform == Platform.INSTAGRAM
    
    def test_create_etsy_integration(self, mock_oauth_service, mock_connection):
        """Test creating Etsy integration"""
        mock_connection.platform = Platform.ETSY.value
        
        integration = create_oauth_integration(
            Platform.ETSY,
            mock_oauth_service,
            mock_connection
        )
        
        assert isinstance(integration, EtsyOAuthIntegration)
        assert integration.platform == Platform.ETSY
    
    def test_create_pinterest_integration(self, mock_oauth_service, mock_connection):
        """Test creating Pinterest integration"""
        mock_connection.platform = Platform.PINTEREST.value
        
        integration = create_oauth_integration(
            Platform.PINTEREST,
            mock_oauth_service,
            mock_connection
        )
        
        assert isinstance(integration, PinterestOAuthIntegration)
        assert integration.platform == Platform.PINTEREST
    
    def test_create_shopify_integration(self, mock_oauth_service, mock_connection):
        """Test creating Shopify integration"""
        mock_connection.platform = Platform.SHOPIFY.value
        mock_connection.platform_data = {"shop_domain": "test-shop"}
        
        integration = create_oauth_integration(
            Platform.SHOPIFY,
            mock_oauth_service,
            mock_connection
        )
        
        assert isinstance(integration, ShopifyOAuthIntegration)
        assert integration.platform == Platform.SHOPIFY
    
    def test_create_unsupported_integration(self, mock_oauth_service, mock_connection):
        """Test creating integration for unsupported platform"""
        with pytest.raises(ValueError, match="No OAuth integration available"):
            create_oauth_integration(
                Platform.MEESHO,  # Not supported by OAuth
                mock_oauth_service,
                mock_connection
            )


if __name__ == "__main__":
    pytest.main([__file__])