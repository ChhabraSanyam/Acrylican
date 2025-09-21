"""
Tests for Pinterest Business API Integration

This module contains comprehensive tests for the Pinterest integration,
including pin creation, board management, Rich Pins functionality,
and analytics retrieval.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
import httpx

from app.services.pinterest_integration import (
    PinterestIntegration,
    PinterestBoardData,
    PinterestPinData,
    PinterestAPIError
)
from app.services.platform_integration import (
    PostContent,
    PostResult,
    PostStatus,
    PlatformMetrics,
    PlatformCredentials,
    Platform
)
from app.models import PlatformConnection


@pytest.fixture
def mock_oauth_service():
    """Mock OAuth service"""
    service = Mock()
    service.get_decrypted_credentials.return_value = PlatformCredentials(
        platform=Platform.PINTEREST,
        auth_method="oauth2",
        access_token="test_access_token",
        refresh_token="test_refresh_token"
    )
    return service


@pytest.fixture
def mock_connection():
    """Mock platform connection"""
    connection = Mock(spec=PlatformConnection)
    connection.platform = "pinterest"
    connection.is_active = True
    return connection


@pytest.fixture
def pinterest_integration(mock_oauth_service, mock_connection):
    """Pinterest integration instance"""
    return PinterestIntegration(mock_oauth_service, mock_connection)


@pytest.fixture
def sample_content():
    """Sample content for testing"""
    return PostContent(
        title="Beautiful Handmade Jewelry",
        description="Stunning artisan jewelry crafted with love and attention to detail. Perfect for special occasions or everyday wear.",
        hashtags=["handmade", "jewelry", "artisan", "unique", "gift"],
        images=["https://example.com/image1.jpg"],
        product_data={
            "price": "49.99",
            "currency": "USD",
            "category": "jewelry",
            "availability": "in stock",
            "brand": "Artisan Crafts"
        }
    )


@pytest.fixture
def sample_boards_response():
    """Sample Pinterest boards API response"""
    return {
        "items": [
            {
                "id": "board123",
                "name": "Jewelry Collection",
                "description": "My handmade jewelry pieces",
                "privacy": "PUBLIC",
                "pin_count": 25,
                "follower_count": 150,
                "created_at": "2023-01-01T00:00:00Z",
                "board_url": "https://pinterest.com/user/jewelry-collection"
            },
            {
                "id": "board456",
                "name": "Art & Crafts",
                "description": "Various art and craft projects",
                "privacy": "PUBLIC",
                "pin_count": 40,
                "follower_count": 200,
                "created_at": "2023-01-01T00:00:00Z",
                "board_url": "https://pinterest.com/user/art-crafts"
            }
        ]
    }


@pytest.fixture
def sample_pin_response():
    """Sample Pinterest pin creation response"""
    return {
        "id": "pin123456",
        "title": "Beautiful Handmade Jewelry",
        "description": "Stunning artisan jewelry crafted with love...",
        "url": "https://pinterest.com/pin/123456",
        "board_id": "board123",
        "created_at": "2023-12-01T10:00:00Z"
    }


@pytest.fixture
def sample_analytics_response():
    """Sample Pinterest analytics response"""
    return {
        "all_time": {
            "IMPRESSION": [{"value": 1250}],
            "OUTBOUND_CLICK": [{"value": 45}],
            "PIN_CLICK": [{"value": 78}],
            "SAVE": [{"value": 32}]
        }
    }


class TestPinterestIntegration:
    """Test Pinterest integration functionality"""
    
    @pytest.mark.asyncio
    async def test_validate_connection_success(self, pinterest_integration):
        """Test successful connection validation"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "username": "test_user",
                "id": "user123"
            }
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await pinterest_integration.validate_connection()
            
            assert result is True
            assert pinterest_integration._user_data is not None
    
    @pytest.mark.asyncio
    async def test_validate_connection_failure(self, pinterest_integration):
        """Test connection validation failure"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 401
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await pinterest_integration.validate_connection()
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_post_content_success(self, pinterest_integration, sample_content, sample_boards_response, sample_pin_response):
        """Test successful pin creation"""
        with patch('httpx.AsyncClient') as mock_client:
            # Mock boards response
            mock_boards_response = Mock()
            mock_boards_response.status_code = 200
            mock_boards_response.json.return_value = sample_boards_response
            
            # Mock pin creation response
            mock_pin_response = Mock()
            mock_pin_response.status_code = 201
            mock_pin_response.json.return_value = sample_pin_response
            
            mock_client_instance = mock_client.return_value.__aenter__.return_value
            mock_client_instance.get = AsyncMock(return_value=mock_boards_response)
            mock_client_instance.post = AsyncMock(return_value=mock_pin_response)
            
            result = await pinterest_integration.post_content(sample_content)
            
            assert result.status == PostStatus.SUCCESS
            assert result.post_id == "pin123456"
            assert result.url == "https://pinterest.com/pin/123456"
            assert result.metadata["board_id"] == "board123"
            assert result.metadata["rich_pin_enabled"] is True
    
    @pytest.mark.asyncio
    async def test_post_content_no_images(self, pinterest_integration):
        """Test pin creation failure when no images provided"""
        content = PostContent(
            title="Test Title",
            description="Test Description",
            hashtags=["test"],
            images=[],  # No images
            product_data={}
        )
        
        result = await pinterest_integration.post_content(content)
        
        assert result.status == PostStatus.FAILED
        assert "At least one image is required" in result.error_message
    
    @pytest.mark.asyncio
    async def test_post_content_multiple_images(self, pinterest_integration):
        """Test pin creation failure when multiple images provided"""
        content = PostContent(
            title="Test Title",
            description="Test Description",
            hashtags=["test"],
            images=["image1.jpg", "image2.jpg"],  # Multiple images
            product_data={}
        )
        
        result = await pinterest_integration.post_content(content)
        
        assert result.status == PostStatus.FAILED
        assert "Pinterest pins support only one image per pin" in result.error_message
    
    @pytest.mark.asyncio
    async def test_get_post_metrics_success(self, pinterest_integration, sample_analytics_response):
        """Test successful metrics retrieval"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = sample_analytics_response
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await pinterest_integration.get_post_metrics("pin123456")
            
            assert result is not None
            assert result.platform == Platform.PINTEREST
            assert result.post_id == "pin123456"
            assert result.views == 1250
            assert result.shares == 32
    
    @pytest.mark.asyncio
    async def test_format_content(self, pinterest_integration, sample_content):
        """Test content formatting for Pinterest"""
        formatted = await pinterest_integration.format_content(sample_content)
        
        # Check that hashtags are moved to description
        assert "#handmade" in formatted.description
        assert "#jewelry" in formatted.description
        assert len(formatted.hashtags) == 0
        
        # Check length limits
        assert len(formatted.title) <= 100
        assert len(formatted.description) <= 500
    
    @pytest.mark.asyncio
    async def test_format_content_long_title(self, pinterest_integration):
        """Test content formatting with long title"""
        content = PostContent(
            title="A" * 150,  # Very long title
            description="Test description",
            hashtags=["test"],
            images=["image.jpg"]
        )
        
        formatted = await pinterest_integration.format_content(content)
        
        assert len(formatted.title) <= 100
        assert formatted.title.endswith("...")
    
    @pytest.mark.asyncio
    async def test_create_board_success(self, pinterest_integration):
        """Test successful board creation"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 201
            mock_response.json.return_value = {
                "id": "new_board123",
                "name": "New Board",
                "description": "A new board for testing",
                "privacy": "PUBLIC"
            }
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await pinterest_integration.create_board(
                name="New Board",
                description="A new board for testing",
                privacy="PUBLIC"
            )
            
            assert result is not None
            assert result.id == "new_board123"
            assert result.name == "New Board"
            assert result.privacy == "PUBLIC"
    
    @pytest.mark.asyncio
    async def test_get_user_boards_success(self, pinterest_integration, sample_boards_response):
        """Test successful boards retrieval"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = sample_boards_response
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await pinterest_integration.get_user_boards()
            
            assert len(result) == 2
            assert result[0].id == "board123"
            assert result[0].name == "Jewelry Collection"
            assert result[1].id == "board456"
            assert result[1].name == "Art & Crafts"
    
    @pytest.mark.asyncio
    async def test_get_user_boards_caching(self, pinterest_integration, sample_boards_response):
        """Test boards caching functionality"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = sample_boards_response
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            # First call
            result1 = await pinterest_integration.get_user_boards()
            
            # Second call should use cache
            result2 = await pinterest_integration.get_user_boards()
            
            # Should only make one API call due to caching
            mock_client.return_value.__aenter__.return_value.get.assert_called_once()
            
            assert len(result1) == len(result2) == 2
    
    @pytest.mark.asyncio
    async def test_update_pin_success(self, pinterest_integration):
        """Test successful pin update"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"id": "pin123456"}
            
            mock_client.return_value.__aenter__.return_value.patch = AsyncMock(return_value=mock_response)
            
            result = await pinterest_integration.update_pin(
                pin_id="pin123456",
                title="Updated Title",
                description="Updated Description"
            )
            
            assert result.status == PostStatus.SUCCESS
            assert result.post_id == "pin123456"
            assert "update" in result.metadata["action"]
    
    @pytest.mark.asyncio
    async def test_search_pins_success(self, pinterest_integration):
        """Test successful pin search"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "items": [
                    {
                        "id": "search_pin1",
                        "title": "Search Result 1",
                        "description": "First search result"
                    },
                    {
                        "id": "search_pin2",
                        "title": "Search Result 2",
                        "description": "Second search result"
                    }
                ]
            }
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await pinterest_integration.search_pins("handmade jewelry", limit=10)
            
            assert len(result) == 2
            assert result[0].id == "search_pin1"
            assert result[1].id == "search_pin2"


class TestPinterestBoardData:
    """Test Pinterest board data structure"""
    
    def test_board_data_initialization(self):
        """Test board data initialization"""
        data = {
            "id": "board123",
            "name": "Test Board",
            "description": "A test board",
            "privacy": "PUBLIC",
            "pin_count": 50,
            "follower_count": 100
        }
        
        board = PinterestBoardData(data)
        
        assert board.id == "board123"
        assert board.name == "Test Board"
        assert board.description == "A test board"
        assert board.privacy == "PUBLIC"
        assert board.pin_count == 50
        assert board.follower_count == 100


class TestPinterestPinData:
    """Test Pinterest pin data structure"""
    
    def test_pin_data_initialization(self):
        """Test pin data initialization"""
        data = {
            "id": "pin123",
            "title": "Test Pin",
            "description": "A test pin",
            "board_id": "board123",
            "created_at": "2023-12-01T10:00:00Z",
            "is_owner": True
        }
        
        pin = PinterestPinData(data)
        
        assert pin.id == "pin123"
        assert pin.title == "Test Pin"
        assert pin.description == "A test pin"
        assert pin.board_id == "board123"
        assert pin.is_owner is True


class TestPinterestAPIError:
    """Test Pinterest API error handling"""
    
    def test_api_error_creation(self):
        """Test API error creation"""
        error = PinterestAPIError("Test error", status_code=400, error_code="INVALID_REQUEST")
        
        assert str(error) == "Test error"
        assert error.platform == Platform.PINTEREST
        assert error.status_code == 400
        assert error.error_code == "INVALID_REQUEST"


@pytest.mark.integration
class TestPinterestIntegrationWithTestAccount:
    """
    Integration tests with Pinterest test account.
    
    These tests require actual Pinterest API credentials and should be run
    against a test account. They are marked as integration tests and can be
    skipped in regular unit test runs.
    """
    
    @pytest.mark.skip(reason="Requires Pinterest test account credentials")
    @pytest.mark.asyncio
    async def test_real_connection_validation(self):
        """Test connection validation with real Pinterest API"""
        # This would require real Pinterest API credentials
        # Implementation would depend on test environment setup
        pass
    
    @pytest.mark.skip(reason="Requires Pinterest test account credentials")
    @pytest.mark.asyncio
    async def test_real_pin_creation(self):
        """Test pin creation with real Pinterest API"""
        # This would require real Pinterest API credentials
        # Implementation would depend on test environment setup
        pass
    
    @pytest.mark.skip(reason="Requires Pinterest test account credentials")
    @pytest.mark.asyncio
    async def test_real_board_management(self):
        """Test board management with real Pinterest API"""
        # This would require real Pinterest API credentials
        # Implementation would depend on test environment setup
        pass
    
    @pytest.mark.skip(reason="Requires Pinterest test account credentials")
    @pytest.mark.asyncio
    async def test_real_analytics_retrieval(self):
        """Test analytics retrieval with real Pinterest API"""
        # This would require real Pinterest API credentials
        # Implementation would depend on test environment setup
        pass


if __name__ == "__main__":
    pytest.main([__file__])