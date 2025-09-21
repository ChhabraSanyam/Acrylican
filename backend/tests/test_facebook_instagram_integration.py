"""
Tests for Facebook and Instagram Integration

This module contains comprehensive tests for the Facebook and Instagram
platform integrations, including authentication, posting, metrics retrieval,
and error handling scenarios.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import httpx
from sqlalchemy.orm import Session

from app.services.facebook_instagram_integration import (
    FacebookIntegration,
    InstagramIntegration,
    create_facebook_integration,
    create_instagram_integration
)
from app.services.oauth_service import OAuthService
from app.services.platform_integration import (
    Platform,
    PostContent,
    PostResult,
    PostStatus,
    PlatformMetrics,
    PlatformCredentials,
    AuthenticationMethod,
    AuthenticationError,
    PostingError
)
from app.models import PlatformConnection


class TestFacebookIntegration:
    """Test cases for Facebook integration"""
    
    @pytest.fixture
    def mock_oauth_service(self):
        """Mock OAuth service"""
        service = Mock(spec=OAuthService)
        service.get_decrypted_credentials.return_value = PlatformCredentials(
            platform=Platform.FACEBOOK,
            auth_method=AuthenticationMethod.OAUTH2,
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        return service
    
    @pytest.fixture
    def mock_connection(self):
        """Mock platform connection"""
        connection = Mock(spec=PlatformConnection)
        connection.platform = Platform.FACEBOOK.value
        connection.user_id = "test_user_id"
        connection.access_token = "encrypted_token"
        connection.is_active = True
        return connection
    
    @pytest.fixture
    def facebook_integration(self, mock_oauth_service, mock_connection):
        """Facebook integration instance"""
        return FacebookIntegration(mock_oauth_service, mock_connection)
    
    @pytest.fixture
    def sample_content(self):
        """Sample post content"""
        return PostContent(
            title="Test Product",
            description="This is a test product description with great features.",
            hashtags=["#handmade", "#artisan", "#craft"],
            images=["https://example.com/image1.jpg", "https://example.com/image2.jpg"],
            product_data={
                "price": "29.99",
                "currency": "USD",
                "condition": "NEW",
                "category": "ARTS_AND_CRAFTS"
            }
        )
    
    @pytest.mark.asyncio
    async def test_authenticate_success(self, facebook_integration):
        """Test successful Facebook authentication"""
        credentials = PlatformCredentials(
            platform=Platform.FACEBOOK,
            auth_method=AuthenticationMethod.OAUTH2,
            access_token="test_token"
        )
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"id": "123", "name": "Test User"}
            
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await facebook_integration.authenticate(credentials)
            
            assert result is True
            assert facebook_integration._credentials == credentials
    
    @pytest.mark.asyncio
    async def test_authenticate_failure(self, facebook_integration):
        """Test Facebook authentication failure"""
        credentials = PlatformCredentials(
            platform=Platform.FACEBOOK,
            auth_method=AuthenticationMethod.OAUTH2,
            access_token="invalid_token"
        )
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 401
            
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await facebook_integration.authenticate(credentials)
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_validate_connection_success(self, facebook_integration):
        """Test successful connection validation"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"id": "123", "name": "Test User"}
            
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await facebook_integration.validate_connection()
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_connection_expired_token(self, facebook_integration):
        """Test connection validation with expired token"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 401
            
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await facebook_integration.validate_connection()
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_get_user_pages_success(self, facebook_integration):
        """Test getting user pages"""
        mock_pages_data = {
            "data": [
                {
                    "id": "page123",
                    "name": "Test Page",
                    "access_token": "page_token",
                    "category": "Business",
                    "tasks": ["MANAGE", "CREATE_CONTENT"]
                }
            ]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_pages_data
            
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            pages = await facebook_integration._get_user_pages("test_token")
            
            assert len(pages) == 1
            assert pages[0]["id"] == "page123"
            assert pages[0]["name"] == "Test Page"
    
    @pytest.mark.asyncio
    async def test_post_single_content_success(self, facebook_integration, sample_content):
        """Test successful single post to Facebook feed"""
        # Mock pages response
        mock_pages_data = {
            "data": [
                {
                    "id": "page123",
                    "name": "Test Page",
                    "access_token": "page_token"
                }
            ]
        }
        
        # Mock post response
        mock_post_response = {
            "id": "page123_post456"
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client_instance = mock_client.return_value.__aenter__.return_value
            
            # Mock pages call
            mock_pages_response = Mock()
            mock_pages_response.status_code = 200
            mock_pages_response.json.return_value = mock_pages_data
            
            # Mock post call
            mock_post_response_obj = Mock()
            mock_post_response_obj.status_code = 200
            mock_post_response_obj.json.return_value = mock_post_response
            
            mock_client_instance.get.return_value = mock_pages_response
            mock_client_instance.post.return_value = mock_post_response_obj
            
            # Test with single image
            single_image_content = sample_content.model_copy()
            single_image_content.images = ["https://example.com/image1.jpg"]
            
            result = await facebook_integration.post_content(single_image_content)
            
            assert result.status == PostStatus.SUCCESS
            assert result.post_id == "page123_post456"
            assert result.platform == Platform.FACEBOOK
            assert "facebook.com" in result.url
    
    @pytest.mark.asyncio
    async def test_post_album_content_success(self, facebook_integration, sample_content):
        """Test successful album post to Facebook"""
        # Mock pages response
        mock_pages_data = {
            "data": [
                {
                    "id": "page123",
                    "name": "Test Page",
                    "access_token": "page_token"
                }
            ]
        }
        
        # Mock album creation response
        mock_album_response = {
            "id": "album789"
        }
        
        # Mock photo upload responses
        mock_photo_response = {
            "id": "photo123"
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client_instance = mock_client.return_value.__aenter__.return_value
            
            # Mock pages call
            mock_pages_response = Mock()
            mock_pages_response.status_code = 200
            mock_pages_response.json.return_value = mock_pages_data
            
            # Mock album creation
            mock_album_response_obj = Mock()
            mock_album_response_obj.status_code = 200
            mock_album_response_obj.json.return_value = mock_album_response
            
            # Mock photo uploads
            mock_photo_response_obj = Mock()
            mock_photo_response_obj.status_code = 200
            mock_photo_response_obj.json.return_value = mock_photo_response
            
            mock_client_instance.get.return_value = mock_pages_response
            mock_client_instance.post.side_effect = [mock_album_response_obj, mock_photo_response_obj, mock_photo_response_obj]
            
            result = await facebook_integration.post_content(sample_content)
            
            assert result.status == PostStatus.SUCCESS
            assert result.post_id == "album789"
            assert result.metadata["album_id"] == "album789"
            assert result.metadata["photos_uploaded"] == 2
    
    @pytest.mark.asyncio
    async def test_post_marketplace_success(self, facebook_integration, sample_content):
        """Test successful marketplace posting"""
        # Set marketplace-specific content
        marketplace_content = sample_content.model_copy()
        marketplace_content.platform_specific = {"post_type": "marketplace"}
        
        # Mock pages response
        mock_pages_data = {
            "data": [
                {
                    "id": "page123",
                    "name": "Test Page",
                    "access_token": "page_token"
                }
            ]
        }
        
        # Mock marketplace listing response
        mock_listing_response = {
            "id": "listing456"
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client_instance = mock_client.return_value.__aenter__.return_value
            
            # Mock pages call
            mock_pages_response = Mock()
            mock_pages_response.status_code = 200
            mock_pages_response.json.return_value = mock_pages_data
            
            # Mock marketplace listing
            mock_listing_response_obj = Mock()
            mock_listing_response_obj.status_code = 200
            mock_listing_response_obj.json.return_value = mock_listing_response
            
            mock_client_instance.get.return_value = mock_pages_response
            mock_client_instance.post.return_value = mock_listing_response_obj
            
            result = await facebook_integration.post_content(marketplace_content)
            
            assert result.status == PostStatus.SUCCESS
            assert result.post_id == "listing456"
            assert "marketplace" in result.url
            assert result.metadata["listing_type"] == "marketplace"
    
    @pytest.mark.asyncio
    async def test_post_no_pages_error(self, facebook_integration, sample_content):
        """Test posting when no pages are available"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": []}
            
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await facebook_integration.post_content(sample_content)
            
            assert result.status == PostStatus.FAILED
            assert result.error_code == "NO_PAGES_FOUND"
    
    @pytest.mark.asyncio
    async def test_get_post_metrics_success(self, facebook_integration):
        """Test successful metrics retrieval"""
        mock_insights_data = {
            "data": [
                {"name": "post_impressions", "values": [{"value": 1000}]},
                {"name": "post_engaged_users", "values": [{"value": 50}]}
            ]
        }
        
        mock_post_data = {
            "likes": {"summary": {"total_count": 25}},
            "comments": {"summary": {"total_count": 5}},
            "shares": {"count": 3}
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client_instance = mock_client.return_value.__aenter__.return_value
            
            # Mock insights response
            mock_insights_response = Mock()
            mock_insights_response.status_code = 200
            mock_insights_response.json.return_value = mock_insights_data
            
            # Mock post response
            mock_post_response = Mock()
            mock_post_response.status_code = 200
            mock_post_response.json.return_value = mock_post_data
            
            mock_client_instance.get.side_effect = [mock_insights_response, mock_post_response]
            
            metrics = await facebook_integration.get_post_metrics("test_post_id")
            
            assert metrics is not None
            assert metrics.platform == Platform.FACEBOOK
            assert metrics.likes == 25
            assert metrics.comments == 5
            assert metrics.shares == 3
            assert metrics.views == 1000
            assert metrics.reach == 50
            assert metrics.engagement_rate == 5.0  # 50/1000 * 100
    
    @pytest.mark.asyncio
    async def test_format_content(self, facebook_integration, sample_content):
        """Test content formatting for Facebook"""
        formatted = await facebook_integration.format_content(sample_content)
        
        assert formatted.title == sample_content.title
        assert formatted.description == sample_content.description
        assert all(tag.startswith("#") for tag in formatted.hashtags)
        assert len(formatted.hashtags) <= 30
    
    def test_calculate_engagement_rate(self, facebook_integration):
        """Test engagement rate calculation"""
        metrics_data = {
            "post_impressions": 1000,
            "post_engaged_users": 50
        }
        
        rate = facebook_integration._calculate_engagement_rate(metrics_data)
        assert rate == 5.0
        
        # Test with zero impressions
        metrics_data["post_impressions"] = 0
        rate = facebook_integration._calculate_engagement_rate(metrics_data)
        assert rate is None


class TestInstagramIntegration:
    """Test cases for Instagram integration"""
    
    @pytest.fixture
    def mock_oauth_service(self):
        """Mock OAuth service"""
        service = Mock(spec=OAuthService)
        service.get_decrypted_credentials.return_value = PlatformCredentials(
            platform=Platform.INSTAGRAM,
            auth_method=AuthenticationMethod.OAUTH2,
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        return service
    
    @pytest.fixture
    def mock_connection(self):
        """Mock platform connection"""
        connection = Mock(spec=PlatformConnection)
        connection.platform = Platform.INSTAGRAM.value
        connection.user_id = "test_user_id"
        connection.access_token = "encrypted_token"
        connection.is_active = True
        return connection
    
    @pytest.fixture
    def instagram_integration(self, mock_oauth_service, mock_connection):
        """Instagram integration instance"""
        return InstagramIntegration(mock_oauth_service, mock_connection)
    
    @pytest.fixture
    def sample_content(self):
        """Sample post content"""
        return PostContent(
            title="Beautiful Handmade Jewelry",
            description="Check out this amazing handcrafted piece! Perfect for any occasion.",
            hashtags=["#handmade", "#jewelry", "#artisan", "#craft"],
            images=["https://example.com/jewelry1.jpg"],
            platform_specific={
                "location_id": "123456789"
            }
        )
    
    @pytest.mark.asyncio
    async def test_authenticate_success(self, instagram_integration):
        """Test successful Instagram authentication"""
        credentials = PlatformCredentials(
            platform=Platform.INSTAGRAM,
            auth_method=AuthenticationMethod.OAUTH2,
            access_token="test_token"
        )
        
        mock_accounts_data = {
            "data": [
                {
                    "id": "page123",
                    "name": "Test Page",
                    "instagram_business_account": {"id": "ig123"}
                }
            ]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_accounts_data
            
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await instagram_integration.authenticate(credentials)
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_connection_success(self, instagram_integration):
        """Test successful connection validation"""
        mock_accounts_data = {
            "data": [
                {
                    "id": "page123",
                    "instagram_business_account": {"id": "ig123"}
                }
            ]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_accounts_data
            
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await instagram_integration.validate_connection()
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_get_instagram_accounts(self, instagram_integration):
        """Test getting Instagram business accounts"""
        mock_accounts_data = {
            "data": [
                {
                    "id": "page123",
                    "name": "Test Page",
                    "instagram_business_account": {"id": "ig123"}
                },
                {
                    "id": "page456",
                    "name": "Another Page",
                    "instagram_business_account": {"id": "ig456"}
                }
            ]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_accounts_data
            
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            accounts = await instagram_integration._get_instagram_accounts("test_token")
            
            assert len(accounts) == 2
            assert accounts[0]["instagram_account_id"] == "ig123"
            assert accounts[1]["instagram_account_id"] == "ig456"
    
    @pytest.mark.asyncio
    async def test_post_single_content_success(self, instagram_integration, sample_content):
        """Test successful single post to Instagram"""
        # Mock Instagram accounts
        mock_accounts_data = {
            "data": [
                {
                    "id": "page123",
                    "name": "Test Page",
                    "instagram_business_account": {"id": "ig123"}
                }
            ]
        }
        
        # Mock container creation response
        mock_container_response = {
            "id": "container123"
        }
        
        # Mock publish response
        mock_publish_response = {
            "id": "media456"
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client_instance = mock_client.return_value.__aenter__.return_value
            
            # Mock accounts call
            mock_accounts_response = Mock()
            mock_accounts_response.status_code = 200
            mock_accounts_response.json.return_value = mock_accounts_data
            
            # Mock container creation
            mock_container_response_obj = Mock()
            mock_container_response_obj.status_code = 200
            mock_container_response_obj.json.return_value = mock_container_response
            
            # Mock publish
            mock_publish_response_obj = Mock()
            mock_publish_response_obj.status_code = 200
            mock_publish_response_obj.json.return_value = mock_publish_response
            
            mock_client_instance.get.return_value = mock_accounts_response
            mock_client_instance.post.side_effect = [mock_container_response_obj, mock_publish_response_obj]
            
            result = await instagram_integration.post_content(sample_content)
            
            assert result.status == PostStatus.SUCCESS
            assert result.post_id == "media456"
            assert result.platform == Platform.INSTAGRAM
            assert "instagram.com" in result.url
            assert result.metadata["media_type"] == "IMAGE"
    
    @pytest.mark.asyncio
    async def test_post_carousel_success(self, instagram_integration, sample_content):
        """Test successful carousel post to Instagram"""
        # Set up carousel content
        carousel_content = sample_content.model_copy()
        carousel_content.images = [
            "https://example.com/image1.jpg",
            "https://example.com/image2.jpg",
            "https://example.com/image3.jpg"
        ]
        
        # Mock Instagram accounts
        mock_accounts_data = {
            "data": [
                {
                    "id": "page123",
                    "name": "Test Page",
                    "instagram_business_account": {"id": "ig123"}
                }
            ]
        }
        
        # Mock container responses
        mock_container_response = {"id": "container123"}
        mock_carousel_response = {"id": "carousel456"}
        mock_publish_response = {"id": "media789"}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client_instance = mock_client.return_value.__aenter__.return_value
            
            # Mock accounts call
            mock_accounts_response = Mock()
            mock_accounts_response.status_code = 200
            mock_accounts_response.json.return_value = mock_accounts_data
            
            # Mock container creation (3 images + 1 carousel)
            mock_container_response_obj = Mock()
            mock_container_response_obj.status_code = 200
            mock_container_response_obj.json.return_value = mock_container_response
            
            mock_carousel_response_obj = Mock()
            mock_carousel_response_obj.status_code = 200
            mock_carousel_response_obj.json.return_value = mock_carousel_response
            
            # Mock publish
            mock_publish_response_obj = Mock()
            mock_publish_response_obj.status_code = 200
            mock_publish_response_obj.json.return_value = mock_publish_response
            
            mock_client_instance.get.return_value = mock_accounts_response
            mock_client_instance.post.side_effect = [
                mock_container_response_obj,  # Image 1
                mock_container_response_obj,  # Image 2
                mock_container_response_obj,  # Image 3
                mock_carousel_response_obj,   # Carousel
                mock_publish_response_obj     # Publish
            ]
            
            result = await instagram_integration.post_content(carousel_content)
            
            assert result.status == PostStatus.SUCCESS
            assert result.post_id == "media789"
            assert result.metadata["media_type"] == "CAROUSEL"
            assert result.metadata["media_count"] == 3
    
    @pytest.mark.asyncio
    async def test_post_no_image_error(self, instagram_integration, sample_content):
        """Test posting without images fails"""
        no_image_content = sample_content.model_copy()
        no_image_content.images = []
        
        # Mock Instagram accounts
        mock_accounts_data = {
            "data": [
                {
                    "id": "page123",
                    "name": "Test Page",
                    "instagram_business_account": {"id": "ig123"}
                }
            ]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_accounts_data
            
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await instagram_integration.post_content(no_image_content)
            
            assert result.status == PostStatus.FAILED
            assert result.error_code == "NO_IMAGE_PROVIDED"
    
    @pytest.mark.asyncio
    async def test_get_post_metrics_success(self, instagram_integration):
        """Test successful metrics retrieval"""
        mock_insights_data = {
            "data": [
                {"name": "likes", "values": [{"value": 45}]},
                {"name": "comments", "values": [{"value": 8}]},
                {"name": "shares", "values": [{"value": 2}]},
                {"name": "reach", "values": [{"value": 500}]},
                {"name": "impressions", "values": [{"value": 750}]},
                {"name": "saved", "values": [{"value": 12}]}
            ]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_insights_data
            
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            metrics = await instagram_integration.get_post_metrics("test_post_id")
            
            assert metrics is not None
            assert metrics.platform == Platform.INSTAGRAM
            assert metrics.likes == 45
            assert metrics.comments == 8
            assert metrics.shares == 2
            assert metrics.reach == 500
            assert metrics.views == 750
            assert metrics.engagement_rate == 8.93  # (45+8+2+12)/750 * 100
    
    @pytest.mark.asyncio
    async def test_format_content(self, instagram_integration, sample_content):
        """Test content formatting for Instagram"""
        # Test with long description
        long_content = sample_content.model_copy()
        long_content.description = "A" * 2500  # Exceeds Instagram limit
        
        formatted = await instagram_integration.format_content(long_content)
        
        assert len(formatted.description) <= 2200
        assert formatted.description.endswith("...")
        assert all(tag.startswith("#") for tag in formatted.hashtags)
        assert len(formatted.hashtags) <= 30
    
    def test_calculate_engagement_rate(self, instagram_integration):
        """Test engagement rate calculation"""
        metrics_data = {
            "impressions": 1000,
            "likes": 50,
            "comments": 10,
            "shares": 5,
            "saved": 15
        }
        
        rate = instagram_integration._calculate_engagement_rate(metrics_data)
        assert rate == 8.0  # (50+10+5+15)/1000 * 100
        
        # Test with zero impressions
        metrics_data["impressions"] = 0
        rate = instagram_integration._calculate_engagement_rate(metrics_data)
        assert rate is None


class TestIntegrationFactories:
    """Test factory functions"""
    
    def test_create_facebook_integration(self):
        """Test Facebook integration factory"""
        oauth_service = Mock(spec=OAuthService)
        connection = Mock(spec=PlatformConnection)
        
        integration = create_facebook_integration(oauth_service, connection)
        
        assert isinstance(integration, FacebookIntegration)
        assert integration.oauth_service == oauth_service
        assert integration.connection == connection
        assert integration.platform == Platform.FACEBOOK
    
    def test_create_instagram_integration(self):
        """Test Instagram integration factory"""
        oauth_service = Mock(spec=OAuthService)
        connection = Mock(spec=PlatformConnection)
        
        integration = create_instagram_integration(oauth_service, connection)
        
        assert isinstance(integration, InstagramIntegration)
        assert integration.oauth_service == oauth_service
        assert integration.connection == connection
        assert integration.platform == Platform.INSTAGRAM


class TestErrorHandling:
    """Test error handling scenarios"""
    
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
        connection = Mock(spec=PlatformConnection)
        connection.platform = Platform.FACEBOOK.value
        connection.user_id = "test_user_id"
        return connection
    
    @pytest.mark.asyncio
    async def test_authentication_error_handling(self, mock_oauth_service, mock_connection):
        """Test authentication error handling"""
        integration = FacebookIntegration(mock_oauth_service, mock_connection)
        
        credentials = PlatformCredentials(
            platform=Platform.FACEBOOK,
            auth_method=AuthenticationMethod.OAUTH2,
            access_token="invalid_token"
        )
        
        with patch('httpx.AsyncClient') as mock_client:
            # Simulate network error
            mock_client.return_value.__aenter__.return_value.get.side_effect = Exception("Network error")
            
            with pytest.raises(AuthenticationError):
                await integration.authenticate(credentials)
    
    @pytest.mark.asyncio
    async def test_posting_error_handling(self, mock_oauth_service, mock_connection):
        """Test posting error handling"""
        integration = FacebookIntegration(mock_oauth_service, mock_connection)
        
        content = PostContent(
            title="Test",
            description="Test description",
            hashtags=["#test"],
            images=["https://example.com/image.jpg"]
        )
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client_instance = mock_client.return_value.__aenter__.return_value
            
            # Mock successful pages response first
            mock_pages_response = Mock()
            mock_pages_response.status_code = 200
            mock_pages_response.json.return_value = {
                "data": [
                    {
                        "id": "page123",
                        "name": "Test Page",
                        "access_token": "page_token"
                    }
                ]
            }
            
            # Mock failed post response
            mock_post_response = Mock()
            mock_post_response.status_code = 400
            mock_post_response.json.return_value = {
                "error": {
                    "message": "Invalid image URL",
                    "code": "INVALID_IMAGE"
                }
            }
            mock_post_response.headers = {"content-type": "application/json"}
            
            mock_client_instance.get.return_value = mock_pages_response
            mock_client_instance.post.return_value = mock_post_response
            
            result = await integration.post_content(content)
            
            assert result.status == PostStatus.FAILED
            assert "Invalid image URL" in result.error_message
            assert result.error_code == "INVALID_IMAGE"
    
    @pytest.mark.asyncio
    async def test_metrics_error_handling(self, mock_oauth_service, mock_connection):
        """Test metrics retrieval error handling"""
        integration = FacebookIntegration(mock_oauth_service, mock_connection)
        
        with patch('httpx.AsyncClient') as mock_client:
            # Simulate API error
            mock_client.return_value.__aenter__.return_value.get.side_effect = Exception("API error")
            
            metrics = await integration.get_post_metrics("test_post_id")
            
            assert metrics is None


if __name__ == "__main__":
    pytest.main([__file__])