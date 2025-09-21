"""
Tests for Etsy Integration

This module contains comprehensive tests for the Etsy marketplace integration,
including OAuth authentication, listing creation and management, inventory
synchronization, and content formatting.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from decimal import Decimal
from datetime import datetime
from typing import Dict, Any

from app.services.etsy_integration import (
    EtsyIntegration,
    EtsyAPIError,
    EtsyListingData,
    EtsyShopData,
    create_etsy_integration
)
from app.services.oauth_service import OAuthService
from app.services.platform_integration import (
    Platform,
    PostContent,
    PostResult,
    PostStatus,
    PlatformMetrics,
    PlatformCredentials,
    AuthenticationMethod
)
from app.models import PlatformConnection


class TestEtsyIntegration:
    """Test Etsy integration functionality"""
    
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
        return EtsyIntegration(mock_oauth_service, mock_connection)
    
    @pytest.fixture
    def sample_content(self):
        """Sample content for testing"""
        return PostContent(
            title="Handmade Ceramic Mug",
            description="Beautiful handcrafted ceramic mug perfect for your morning coffee. Made with love and attention to detail.",
            hashtags=["handmade", "ceramic", "mug", "pottery", "coffee"],
            images=["https://example.com/image1.jpg", "https://example.com/image2.jpg"],
            product_data={
                "price": "25.00",
                "quantity": 5,
                "category": "handmade"
            }
        )
    
    @pytest.fixture
    def mock_shop_data(self):
        """Mock shop data"""
        return {
            "shop_id": "shop123",
            "shop_name": "TestShop",
            "user_id": "user123",
            "currency_code": "USD",
            "is_vacation": False,
            "listing_active_count": 10
        }
    
    @pytest.fixture
    def mock_user_data(self):
        """Mock user data"""
        return {
            "user_id": "user123",
            "login_name": "testuser",
            "primary_email": "test@example.com"
        }
    
    def test_etsy_integration_initialization(self, etsy_integration):
        """Test Etsy integration initialization"""
        assert etsy_integration.platform == Platform.ETSY
        assert etsy_integration.config.api_base_url == "https://openapi.etsy.com/v3"
        assert etsy_integration.config.max_title_length == 140
        assert etsy_integration.config.max_description_length == 13000
        assert etsy_integration.config.max_hashtags == 13
    
    def test_etsy_listing_data(self):
        """Test EtsyListingData class"""
        data = {
            "listing_id": "123456",
            "title": "Test Product",
            "description": "Test description",
            "price": {"amount": "25.00", "currency_code": "USD"},
            "quantity": 5,
            "state": "active",
            "views": 100,
            "num_favorers": 10,
            "materials": ["ceramic", "handmade"],
            "tags": ["mug", "coffee"]
        }
        
        listing = EtsyListingData(data)
        assert listing.listing_id == "123456"
        assert listing.title == "Test Product"
        assert listing.price == "25.00"
        assert listing.currency_code == "USD"
        assert listing.quantity == 5
        assert listing.state == "active"
        assert listing.views == 100
        assert listing.num_favorers == 10
        assert listing.materials == ["ceramic", "handmade"]
        assert listing.tags == ["mug", "coffee"]
    
    def test_etsy_shop_data(self, mock_shop_data):
        """Test EtsyShopData class"""
        shop = EtsyShopData(mock_shop_data)
        assert shop.shop_id == "shop123"
        assert shop.shop_name == "TestShop"
        assert shop.user_id == "user123"
        assert shop.currency_code == "USD"
        assert shop.is_vacation is False
        assert shop.listing_active_count == 10
    
    @patch('httpx.AsyncClient')
    async def test_validate_connection_success(self, mock_httpx, etsy_integration, mock_user_data, mock_shop_data):
        """Test successful connection validation"""
        mock_client = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        # Mock user info response
        mock_client.get.side_effect = [
            # User info
            Mock(status_code=200, json=lambda: mock_user_data),
            # Shops info
            Mock(status_code=200, json=lambda: {"results": [mock_shop_data]}),
            # Shipping templates
            Mock(status_code=200, json=lambda: {"results": []})
        ]
        
        result = await etsy_integration.validate_connection()
        assert result is True
        assert etsy_integration._shop_data is not None
        assert etsy_integration._shop_data.shop_id == "shop123"
    
    @patch('httpx.AsyncClient')
    async def test_validate_connection_failure(self, mock_httpx, etsy_integration):
        """Test connection validation failure"""
        mock_client = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        # Mock failed response
        mock_client.get.return_value = Mock(status_code=401)
        
        result = await etsy_integration.validate_connection()
        assert result is False
    
    @patch('httpx.AsyncClient')
    async def test_post_content_success(self, mock_httpx, etsy_integration, sample_content, mock_user_data, mock_shop_data):
        """Test successful listing creation"""
        mock_client = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        # Mock responses
        mock_client.get.side_effect = [
            # User info
            Mock(status_code=200, json=lambda: mock_user_data),
            # Shops info
            Mock(status_code=200, json=lambda: {"results": [mock_shop_data]}),
            # Shipping templates
            Mock(status_code=200, json=lambda: {"results": []})
        ]
        
        # Mock listing creation
        mock_client.post.side_effect = [
            # Listing creation
            Mock(status_code=201, json=lambda: {"listing_id": "listing123"}),
            # Image upload 1
            Mock(status_code=201, json=lambda: {"listing_image_id": "img1"}),
            # Image upload 2
            Mock(status_code=201, json=lambda: {"listing_image_id": "img2"})
        ]
        
        result = await etsy_integration.post_content(sample_content)
        
        assert result.status == PostStatus.SUCCESS
        assert result.post_id == "listing123"
        assert result.url == "https://www.etsy.com/listing/listing123"
        assert result.metadata["shop_id"] == "shop123"
        assert result.metadata["images_uploaded"] == 2
    
    @patch('httpx.AsyncClient')
    async def test_post_content_validation_failure(self, mock_httpx, etsy_integration, mock_user_data, mock_shop_data):
        """Test listing creation with validation failure"""
        mock_client = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        # Mock shop data loading
        mock_client.get.side_effect = [
            Mock(status_code=200, json=lambda: mock_user_data),
            Mock(status_code=200, json=lambda: {"results": [mock_shop_data]}),
            Mock(status_code=200, json=lambda: {"results": []})
        ]
        
        # Create invalid content (no title)
        invalid_content = PostContent(
            title="",  # Empty title
            description="Test description",
            hashtags=["test"],
            images=["https://example.com/image.jpg"]
        )
        
        result = await etsy_integration.post_content(invalid_content)
        
        assert result.status == PostStatus.FAILED
        assert result.error_code == "CONTENT_VALIDATION_FAILED"
        assert "Title is required" in result.error_message
    
    @patch('httpx.AsyncClient')
    async def test_get_post_metrics_success(self, mock_httpx, etsy_integration):
        """Test successful metrics retrieval"""
        mock_client = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        # Mock listing data response
        mock_client.get.return_value = Mock(
            status_code=200,
            json=lambda: {
                "listing_id": "listing123",
                "views": 150,
                "num_favorers": 25
            }
        )
        
        result = await etsy_integration.get_post_metrics("listing123")
        
        assert result is not None
        assert result.platform == Platform.ETSY
        assert result.post_id == "listing123"
        assert result.views == 150
        assert result.likes == 25
    
    @patch('httpx.AsyncClient')
    async def test_get_post_metrics_failure(self, mock_httpx, etsy_integration):
        """Test metrics retrieval failure"""
        mock_client = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        # Mock failed response
        mock_client.get.return_value = Mock(status_code=404)
        
        result = await etsy_integration.get_post_metrics("listing123")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_format_content(self, etsy_integration):
        """Test content formatting for Etsy"""
        # Test with content that needs formatting
        long_title = "A" * 200  # Exceeds 140 character limit
        long_description = "B" * 15000  # Exceeds 13000 character limit
        many_hashtags = [f"tag{i}" for i in range(20)]  # Exceeds 13 tag limit
        many_images = [f"https://example.com/image{i}.jpg" for i in range(15)]  # Exceeds 10 image limit
        
        content = PostContent(
            title=long_title,
            description=long_description,
            hashtags=many_hashtags,
            images=many_images
        )
        
        formatted = await etsy_integration.format_content(content)
        
        # Check title truncation
        assert len(formatted.title) <= 140
        assert formatted.title.endswith("...")
        
        # Check description truncation
        assert len(formatted.description) <= 13000
        assert formatted.description.endswith("...")
        
        # Check hashtag limit
        assert len(formatted.hashtags) <= 13
        
        # Check image limit
        assert len(formatted.images) <= 10
        
        # Check hashtag formatting (no # symbols)
        for tag in formatted.hashtags:
            assert not tag.startswith("#")
            assert tag.islower()
    
    @patch('httpx.AsyncClient')
    async def test_update_listing_success(self, mock_httpx, etsy_integration, sample_content, mock_shop_data):
        """Test successful listing update"""
        mock_client = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        # Set up shop data
        etsy_integration._shop_data = EtsyShopData(mock_shop_data)
        
        # Mock successful update response
        mock_client.put.return_value = Mock(status_code=200)
        
        result = await etsy_integration.update_listing(
            "listing123",
            sample_content,
            price=Decimal("30.00"),
            quantity=10
        )
        
        assert result.status == PostStatus.SUCCESS
        assert result.post_id == "listing123"
        assert result.metadata["action"] == "update"
    
    @patch('httpx.AsyncClient')
    async def test_get_shop_listings_success(self, mock_httpx, etsy_integration, mock_shop_data):
        """Test successful shop listings retrieval"""
        mock_client = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        # Set up shop data
        etsy_integration._shop_data = EtsyShopData(mock_shop_data)
        
        # Mock listings response
        mock_listings_data = [
            {
                "listing_id": "listing1",
                "title": "Product 1",
                "state": "active",
                "views": 100
            },
            {
                "listing_id": "listing2",
                "title": "Product 2",
                "state": "active",
                "views": 50
            }
        ]
        
        mock_client.get.return_value = Mock(
            status_code=200,
            json=lambda: {"results": mock_listings_data}
        )
        
        listings = await etsy_integration.get_shop_listings()
        
        assert len(listings) == 2
        assert listings[0].listing_id == "listing1"
        assert listings[0].title == "Product 1"
        assert listings[1].listing_id == "listing2"
        assert listings[1].title == "Product 2"
    
    @patch('httpx.AsyncClient')
    async def test_sync_inventory_success(self, mock_httpx, etsy_integration, mock_shop_data):
        """Test successful inventory synchronization"""
        mock_client = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        # Set up shop data
        etsy_integration._shop_data = EtsyShopData(mock_shop_data)
        
        # Mock successful update responses
        mock_client.put.return_value = Mock(status_code=200)
        
        listings_data = [
            {
                "listing_id": "listing1",
                "quantity": 10,
                "price": "25.00"
            },
            {
                "listing_id": "listing2",
                "quantity": 5,
                "price": "15.00"
            }
        ]
        
        result = await etsy_integration.sync_inventory(listings_data)
        
        assert result["updated"] == 2
        assert result["failed"] == 0
        assert len(result["errors"]) == 0
    
    @patch('httpx.AsyncClient')
    async def test_sync_inventory_partial_failure(self, mock_httpx, etsy_integration, mock_shop_data):
        """Test inventory synchronization with partial failures"""
        mock_client = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        # Set up shop data
        etsy_integration._shop_data = EtsyShopData(mock_shop_data)
        
        # Mock mixed responses (success and failure)
        mock_client.put.side_effect = [
            Mock(status_code=200),  # Success
            Mock(status_code=400)   # Failure
        ]
        
        listings_data = [
            {
                "listing_id": "listing1",
                "quantity": 10
            },
            {
                "listing_id": "listing2",
                "quantity": 5
            }
        ]
        
        result = await etsy_integration.sync_inventory(listings_data)
        
        assert result["updated"] == 1
        assert result["failed"] == 1
        assert len(result["errors"]) == 1
        assert "listing2" in result["errors"][0]
    
    @pytest.mark.asyncio
    async def test_validate_listing_content(self, etsy_integration):
        """Test listing content validation"""
        # Test valid content
        valid_content = PostContent(
            title="Valid Title",
            description="Valid description",
            hashtags=["tag1", "tag2"],
            images=["https://example.com/image.jpg"],
            product_data={"price": "25.00"}
        )
        
        errors = await etsy_integration._validate_listing_content(valid_content)
        assert len(errors) == 0
        
        # Test invalid content
        invalid_content = PostContent(
            title="",  # Empty title
            description="",  # Empty description
            hashtags=["tag"] * 20,  # Too many tags
            images=["url"] * 15,  # Too many images
            product_data={"price": "0.10"}  # Price too low
        )
        
        errors = await etsy_integration._validate_listing_content(invalid_content)
        assert len(errors) > 0
        assert any("Title is required" in error for error in errors)
        assert any("Description is required" in error for error in errors)
        assert any("Too many materials/tags" in error for error in errors)
        assert any("Too many images" in error for error in errors)
        assert any("Price must be at least" in error for error in errors)
    
    def test_determine_taxonomy_id(self, etsy_integration):
        """Test taxonomy ID determination"""
        # Test with product data category
        content_with_category = PostContent(
            title="Test",
            description="Test",
            hashtags=[],
            images=[],
            product_data={"category": "jewelry"}
        )
        
        taxonomy_id = etsy_integration._determine_taxonomy_id(content_with_category)
        assert taxonomy_id == etsy_integration.DEFAULT_TAXONOMY_CATEGORIES["jewelry"]
        
        # Test with hashtag category
        content_with_hashtag = PostContent(
            title="Test",
            description="Test",
            hashtags=["art", "other"],
            images=[]
        )
        
        taxonomy_id = etsy_integration._determine_taxonomy_id(content_with_hashtag)
        assert taxonomy_id == etsy_integration.DEFAULT_TAXONOMY_CATEGORIES["art"]
        
        # Test default category
        content_default = PostContent(
            title="Test",
            description="Test",
            hashtags=["unknown"],
            images=[]
        )
        
        taxonomy_id = etsy_integration._determine_taxonomy_id(content_default)
        assert taxonomy_id == etsy_integration.DEFAULT_TAXONOMY_CATEGORIES["handmade"]
    
    def test_create_etsy_integration_factory(self, mock_oauth_service, mock_connection):
        """Test factory function for creating Etsy integration"""
        integration = create_etsy_integration(mock_oauth_service, mock_connection)
        assert isinstance(integration, EtsyIntegration)
        assert integration.platform == Platform.ETSY


class TestEtsyAPIError:
    """Test Etsy API error handling"""
    
    def test_etsy_api_error_creation(self):
        """Test EtsyAPIError creation"""
        error = EtsyAPIError("Test error", status_code=400, error_code="INVALID_REQUEST")
        
        assert str(error) == "Test error"
        assert error.platform == Platform.ETSY
        assert error.status_code == 400
        assert error.error_code == "INVALID_REQUEST"
    
    def test_etsy_api_error_without_optional_params(self):
        """Test EtsyAPIError creation without optional parameters"""
        error = EtsyAPIError("Test error")
        
        assert str(error) == "Test error"
        assert error.platform == Platform.ETSY
        assert error.status_code is None
        assert error.error_code is None


# Integration test fixtures for sandbox testing
class TestEtsySandboxIntegration:
    """
    Integration tests for Etsy sandbox environment.
    
    These tests require actual Etsy sandbox credentials and should be run
    separately from unit tests. They are marked with pytest.mark.integration
    to allow selective execution.
    """
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_sandbox_authentication(self):
        """Test authentication with Etsy sandbox"""
        # This test would require actual sandbox credentials
        # and should only be run in integration test environment
        pytest.skip("Requires Etsy sandbox credentials")
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_sandbox_listing_creation(self):
        """Test listing creation in Etsy sandbox"""
        # This test would create an actual listing in sandbox
        pytest.skip("Requires Etsy sandbox credentials")
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_sandbox_inventory_sync(self):
        """Test inventory synchronization in Etsy sandbox"""
        # This test would sync inventory with sandbox
        pytest.skip("Requires Etsy sandbox credentials")


if __name__ == "__main__":
    # Run tests with: python -m pytest backend/tests/test_etsy_integration.py -v
    pytest.main([__file__, "-v"])