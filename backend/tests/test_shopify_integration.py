"""
Tests for Shopify Integration

This module contains comprehensive tests for the Shopify integration,
including OAuth authentication, product creation, inventory management,
order tracking, and error handling.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import httpx

from app.services.shopify_integration import (
    ShopifyIntegration,
    ShopifyAPIError,
    ShopifyProductData,
    ShopifyShopData,
    ShopifyOrderData,
    SHOPIFY_CONFIG
)
from app.services.platform_integration import (
    Platform,
    PostContent,
    PostResult,
    PostStatus,
    PlatformMetrics,
    PlatformCredentials,
    AuthenticationMethod
)
from app.services.oauth_service import OAuthService
from app.models import PlatformConnection


# Test fixtures
@pytest.fixture
def mock_oauth_service():
    """Mock OAuth service"""
    service = Mock(spec=OAuthService)
    service.get_decrypted_credentials.return_value = PlatformCredentials(
        platform=Platform.SHOPIFY,
        auth_method=AuthenticationMethod.OAUTH2,
        access_token="test_access_token",
        refresh_token="test_refresh_token"
    )
    return service

@pytest.fixture
def mock_connection():
    """Mock platform connection"""
    connection = Mock(spec=PlatformConnection)
    connection.platform = Platform.SHOPIFY.value
    connection.platform_data = {"shop_domain": "test-shop"}
    connection.is_active = True
    return connection

@pytest.fixture
def shopify_integration(mock_oauth_service, mock_connection):
    """Create Shopify integration instance"""
    return ShopifyIntegration(mock_oauth_service, mock_connection)

@pytest.fixture
def sample_post_content():
    """Sample post content for testing"""
    return PostContent(
        title="Handcrafted Ceramic Vase",
        description="Beautiful handmade ceramic vase perfect for home decoration",
        hashtags=["handmade", "ceramic", "vase", "homedecor"],
        images=["https://example.com/image1.jpg", "https://example.com/image2.jpg"],
        product_data={
            "price": "29.99",
            "quantity": 5,
            "product_type": "Home & Garden",
            "vendor": "Artisan Ceramics",
            "weight": "1.2",
            "weight_unit": "kg",
            "sku": "CERAMIC-VASE-001"
        }
    )

@pytest.fixture
def sample_shop_data():
    """Sample shop data for testing"""
    return {
        "shop": {
            "id": 12345,
            "name": "Test Artisan Shop",
            "email": "test@example.com",
            "domain": "test-shop.com",
            "myshopify_domain": "test-shop.myshopify.com",
            "currency": "USD",
            "timezone": "America/New_York",
            "plan_name": "basic",
            "country_code": "US",
            "created_at": "2023-01-01T00:00:00Z"
        }
    }

@pytest.fixture
def sample_product_data():
    """Sample product data for testing"""
    return {
        "product": {
            "id": 67890,
            "title": "Handcrafted Ceramic Vase",
            "body_html": "<p>Beautiful handmade ceramic vase</p>",
            "vendor": "Artisan Ceramics",
            "product_type": "Home & Garden",
            "handle": "handcrafted-ceramic-vase",
            "status": "active",
            "published_at": "2023-01-01T12:00:00Z",
            "created_at": "2023-01-01T12:00:00Z",
            "updated_at": "2023-01-01T12:00:00Z",
            "tags": "handmade, ceramic, vase, homedecor",
            "variants": [
                {
                    "id": 98765,
                    "price": "29.99",
                    "compare_at_price": None,
                    "inventory_quantity": 5,
                    "sku": "CERAMIC-VASE-001",
                    "weight": 1.2,
                    "weight_unit": "kg"
                }
            ],
            "images": [
                {"id": 11111, "src": "https://example.com/image1.jpg"},
                {"id": 22222, "src": "https://example.com/image2.jpg"}
            ]
        }
    }

@pytest.fixture
def sample_order_data():
    """Sample order data for testing"""
    return {
        "orders": [
            {
                "id": 54321,
                "order_number": 1001,
                "name": "#1001",
                "email": "customer@example.com",
                "created_at": "2023-01-01T15:00:00Z",
                "currency": "USD",
                "total_price": "29.99",
                "subtotal_price": "29.99",
                "total_tax": "0.00",
                "financial_status": "paid",
                "fulfillment_status": "unfulfilled",
                "line_items": [
                    {
                        "id": 11111,
                        "product_id": 67890,
                        "variant_id": 98765,
                        "quantity": 1,
                        "price": "29.99",
                        "title": "Handcrafted Ceramic Vase"
                    }
                ],
                "customer": {
                    "id": 33333,
                    "email": "customer@example.com",
                    "first_name": "John",
                    "last_name": "Doe"
                }
            }
        ]
    }


class TestShopifyIntegration:
    """Test suite for Shopify integration functionality"""


class TestShopifyAuthentication:
    """Test Shopify authentication functionality"""
    
    @pytest.mark.asyncio
    async def test_authenticate_success(self, shopify_integration, sample_shop_data):
        """Test successful authentication"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = sample_shop_data
            
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            credentials = PlatformCredentials(
                platform=Platform.SHOPIFY,
                auth_method=AuthenticationMethod.OAUTH2,
                access_token="test_token"
            )
            
            result = await shopify_integration.authenticate(credentials)
            assert result is True
    
    @pytest.mark.asyncio
    async def test_authenticate_failure(self, shopify_integration):
        """Test authentication failure"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 401
            
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            credentials = PlatformCredentials(
                platform=Platform.SHOPIFY,
                auth_method=AuthenticationMethod.OAUTH2,
                access_token="invalid_token"
            )
            
            result = await shopify_integration.authenticate(credentials)
            assert result is False
    
    @pytest.mark.asyncio
    async def test_validate_connection_success(self, shopify_integration, sample_shop_data):
        """Test successful connection validation"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = sample_shop_data
            
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await shopify_integration.validate_connection()
            assert result is True
            assert shopify_integration._shop_data is not None
            assert shopify_integration._shop_data.name == "Test Artisan Shop"
    
    @pytest.mark.asyncio
    async def test_validate_connection_failure(self, shopify_integration):
        """Test connection validation failure"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 403
            
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await shopify_integration.validate_connection()
            assert result is False


class TestShopifyProductOperations:
    """Test Shopify product creation and management"""
    
    @pytest.mark.asyncio
    async def test_post_content_success(self, shopify_integration, sample_post_content, sample_shop_data, sample_product_data):
        """Test successful product creation"""
        with patch('httpx.AsyncClient') as mock_client:
            # Mock shop data request
            shop_response = Mock()
            shop_response.status_code = 200
            shop_response.json.return_value = sample_shop_data
            
            # Mock product creation request
            product_response = Mock()
            product_response.status_code = 201
            product_response.json.return_value = sample_product_data
            
            mock_client.return_value.__aenter__.return_value.get.return_value = shop_response
            mock_client.return_value.__aenter__.return_value.post.return_value = product_response
            
            result = await shopify_integration.post_content(sample_post_content)
            
            assert result.status == PostStatus.SUCCESS
            assert result.post_id == "67890"
            assert "test-shop.myshopify.com" in result.url
            assert result.published_at is not None
            assert result.metadata["shop_domain"] == "test-shop"
    
    @pytest.mark.asyncio
    async def test_post_content_validation_failure(self, shopify_integration, sample_shop_data):
        """Test product creation with validation errors"""
        with patch('httpx.AsyncClient') as mock_client:
            shop_response = Mock()
            shop_response.status_code = 200
            shop_response.json.return_value = sample_shop_data
            
            mock_client.return_value.__aenter__.return_value.get.return_value = shop_response
            
            # Create content with validation errors
            invalid_content = PostContent(
                title="",  # Empty title should fail validation
                description="Test description",
                hashtags=[],
                images=[]
            )
            
            result = await shopify_integration.post_content(invalid_content)
            
            assert result.status == PostStatus.FAILED
            assert result.error_code == "CONTENT_VALIDATION_FAILED"
            assert "Title is required" in result.error_message
    
    @pytest.mark.asyncio
    async def test_post_content_api_failure(self, shopify_integration, sample_post_content, sample_shop_data):
        """Test product creation API failure"""
        with patch('httpx.AsyncClient') as mock_client:
            # Mock shop data request
            shop_response = Mock()
            shop_response.status_code = 200
            shop_response.json.return_value = sample_shop_data
            
            # Mock failed product creation
            product_response = Mock()
            product_response.status_code = 422
            product_response.json.return_value = {"errors": {"title": ["can't be blank"]}}
            product_response.content = True
            
            mock_client.return_value.__aenter__.return_value.get.return_value = shop_response
            mock_client.return_value.__aenter__.return_value.post.return_value = product_response
            
            result = await shopify_integration.post_content(sample_post_content)
            
            assert result.status == PostStatus.FAILED
            assert result.error_code == "PRODUCT_CREATION_FAILED"
    
    @pytest.mark.asyncio
    async def test_update_product_success(self, shopify_integration, sample_post_content, sample_product_data):
        """Test successful product update"""
        with patch('httpx.AsyncClient') as mock_client:
            # Mock product update request
            update_response = Mock()
            update_response.status_code = 200
            update_response.json.return_value = sample_product_data
            
            # Mock variant update request
            variant_response = Mock()
            variant_response.status_code = 200
            
            mock_client.return_value.__aenter__.return_value.put.return_value = update_response
            
            result = await shopify_integration.update_product(
                "67890",
                sample_post_content,
                price=Decimal("39.99"),
                inventory_quantity=10
            )
            
            assert result.status == PostStatus.SUCCESS
            assert result.post_id == "67890"
            assert result.metadata["action"] == "update"
    
    @pytest.mark.asyncio
    async def test_get_products_success(self, shopify_integration, sample_product_data):
        """Test successful product retrieval"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"products": [sample_product_data["product"]]}
            
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            products = await shopify_integration.get_products(status="active", limit=10)
            
            assert len(products) == 1
            assert products[0].product_id == 67890
            assert products[0].title == "Handcrafted Ceramic Vase"
            assert products[0].status == "active"
    
    @pytest.mark.asyncio
    async def test_format_content(self, shopify_integration, sample_post_content):
        """Test content formatting for Shopify"""
        formatted = await shopify_integration.format_content(sample_post_content)
        
        assert formatted.title == sample_post_content.title
        assert "<p>" in formatted.description  # Should be converted to HTML
        assert formatted.hashtags == ["handmade", "ceramic", "vase", "homedecor"]  # No # symbols
        assert len(formatted.images) == 2


class TestShopifyInventoryManagement:
    """Test Shopify inventory synchronization"""
    
    @pytest.mark.asyncio
    async def test_sync_inventory_success(self, shopify_integration, sample_product_data):
        """Test successful inventory synchronization"""
        with patch('httpx.AsyncClient') as mock_client:
            # Mock product request to get variant ID
            product_response = Mock()
            product_response.status_code = 200
            product_response.json.return_value = sample_product_data
            
            # Mock variant update request
            variant_response = Mock()
            variant_response.status_code = 200
            
            mock_client.return_value.__aenter__.return_value.get.return_value = product_response
            mock_client.return_value.__aenter__.return_value.put.return_value = variant_response
            
            inventory_data = [
                {
                    "product_id": "67890",
                    "inventory_quantity": 15,
                    "price": "34.99"
                }
            ]
            
            result = await shopify_integration.sync_inventory(inventory_data)
            
            assert result["updated"] == 1
            assert result["failed"] == 0
            assert len(result["errors"]) == 0
    
    @pytest.mark.asyncio
    async def test_sync_inventory_missing_product_id(self, shopify_integration):
        """Test inventory sync with missing product ID"""
        inventory_data = [
            {
                "inventory_quantity": 15,
                "price": "34.99"
                # Missing product_id
            }
        ]
        
        result = await shopify_integration.sync_inventory(inventory_data)
        
        assert result["updated"] == 0
        assert result["failed"] == 1
        assert "Missing product_id" in result["errors"]


class TestShopifyOrderTracking:
    """Test Shopify order tracking and sales metrics"""
    
    @pytest.mark.asyncio
    async def test_get_orders_success(self, shopify_integration, sample_order_data):
        """Test successful order retrieval"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = sample_order_data
            
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            orders = await shopify_integration.get_orders(
                status="any",
                financial_status="paid",
                limit=10
            )
            
            assert len(orders) == 1
            assert orders[0].order_id == 54321
            assert orders[0].total_price == "29.99"
            assert orders[0].financial_status == "paid"
            assert len(orders[0].line_items) == 1
    
    @pytest.mark.asyncio
    async def test_get_post_metrics_success(self, shopify_integration, sample_product_data, sample_order_data):
        """Test successful metrics retrieval"""
        with patch('httpx.AsyncClient') as mock_client:
            # Mock product request
            product_response = Mock()
            product_response.status_code = 200
            product_response.json.return_value = sample_product_data
            
            # Mock orders request for sales data
            orders_response = Mock()
            orders_response.status_code = 200
            orders_response.json.return_value = sample_order_data
            
            mock_client.return_value.__aenter__.return_value.get.side_effect = [
                product_response,  # First call for product data
                orders_response   # Second call for orders data
            ]
            
            metrics = await shopify_integration.get_post_metrics("67890")
            
            assert metrics is not None
            assert metrics.platform == Platform.SHOPIFY
            assert metrics.post_id == "67890"
            assert metrics.retrieved_at is not None


class TestShopifyErrorHandling:
    """Test Shopify error handling and edge cases"""
    
    @pytest.mark.asyncio
    async def test_api_error_handling(self, shopify_integration, sample_post_content):
        """Test API error handling"""
        with patch('httpx.AsyncClient') as mock_client:
            # Mock network error
            mock_client.return_value.__aenter__.return_value.get.side_effect = httpx.RequestError("Network error")
            
            result = await shopify_integration.post_content(sample_post_content)
            
            assert result.status == PostStatus.FAILED
            assert result.error_code == "POSTING_EXCEPTION"
    
    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, shopify_integration, sample_post_content, sample_shop_data):
        """Test rate limit error handling"""
        with patch('httpx.AsyncClient') as mock_client:
            # Mock shop data request
            shop_response = Mock()
            shop_response.status_code = 200
            shop_response.json.return_value = sample_shop_data
            
            # Mock rate limit response
            rate_limit_response = Mock()
            rate_limit_response.status_code = 429
            rate_limit_response.json.return_value = {"errors": "Exceeded 2 calls per second for api client"}
            rate_limit_response.content = True
            
            mock_client.return_value.__aenter__.return_value.get.return_value = shop_response
            mock_client.return_value.__aenter__.return_value.post.return_value = rate_limit_response
            
            result = await shopify_integration.post_content(sample_post_content)
            
            assert result.status == PostStatus.FAILED
            assert result.error_code == "PRODUCT_CREATION_FAILED"
    
    def test_shopify_product_data_parsing(self, sample_product_data):
        """Test ShopifyProductData parsing"""
        product = ShopifyProductData(sample_product_data["product"])
        
        assert product.product_id == 67890
        assert product.title == "Handcrafted Ceramic Vase"
        assert product.status == "active"
        assert product.price == "29.99"
        assert product.inventory_quantity == 5
        assert len(product.variants) == 1
        assert len(product.images) == 2
    
    def test_shopify_shop_data_parsing(self, sample_shop_data):
        """Test ShopifyShopData parsing"""
        shop = ShopifyShopData(sample_shop_data)
        
        assert shop.shop_id == 12345
        assert shop.name == "Test Artisan Shop"
        assert shop.currency == "USD"
        assert shop.myshopify_domain == "test-shop.myshopify.com"
    
    def test_shopify_order_data_parsing(self, sample_order_data):
        """Test ShopifyOrderData parsing"""
        order = ShopifyOrderData(sample_order_data["orders"][0])
        
        assert order.order_id == 54321
        assert order.order_number == 1001
        assert order.total_price == "29.99"
        assert order.financial_status == "paid"
        assert len(order.line_items) == 1


class TestShopifyConfiguration:
    """Test Shopify configuration and setup"""
    
    def test_shopify_config(self):
        """Test Shopify configuration constants"""
        assert SHOPIFY_CONFIG.platform == Platform.SHOPIFY
        assert SHOPIFY_CONFIG.integration_type.value == "api"
        assert SHOPIFY_CONFIG.auth_method.value == "oauth2"
        assert SHOPIFY_CONFIG.max_title_length == 255
        assert SHOPIFY_CONFIG.max_description_length == 65535
        assert SHOPIFY_CONFIG.rate_limit_per_minute == 40
    
    def test_shopify_integration_initialization(self, mock_oauth_service, mock_connection):
        """Test Shopify integration initialization"""
        integration = ShopifyIntegration(mock_oauth_service, mock_connection)
        
        assert integration.platform == Platform.SHOPIFY
        assert integration.shop_domain == "test-shop"
        assert integration.config.api_base_url == "https://test-shop.myshopify.com/admin/api/2023-10"
    
    def test_shopify_integration_missing_shop_domain(self, mock_oauth_service):
        """Test Shopify integration with missing shop domain"""
        connection = Mock(spec=PlatformConnection)
        connection.platform_data = None
        
        with pytest.raises(ValueError, match="Shop domain is required"):
            ShopifyIntegration(mock_oauth_service, connection)


class TestShopifyValidation:
    """Test Shopify content validation"""
    
    @pytest.mark.asyncio
    async def test_validate_product_content_success(self, shopify_integration, sample_post_content):
        """Test successful content validation"""
        errors = await shopify_integration._validate_product_content(sample_post_content)
        assert len(errors) == 0
    
    @pytest.mark.asyncio
    async def test_validate_product_content_empty_title(self, shopify_integration):
        """Test validation with empty title"""
        content = PostContent(
            title="",
            description="Test description",
            hashtags=[],
            images=[]
        )
        
        errors = await shopify_integration._validate_product_content(content)
        assert "Title is required" in errors
    
    @pytest.mark.asyncio
    async def test_validate_product_content_long_title(self, shopify_integration):
        """Test validation with title too long"""
        content = PostContent(
            title="x" * 300,  # Exceeds 255 character limit
            description="Test description",
            hashtags=[],
            images=[]
        )
        
        errors = await shopify_integration._validate_product_content(content)
        assert any("Title exceeds" in error for error in errors)
    
    @pytest.mark.asyncio
    async def test_validate_product_content_invalid_price(self, shopify_integration):
        """Test validation with invalid price"""
        content = PostContent(
            title="Test Product",
            description="Test description",
            hashtags=[],
            images=[],
            product_data={"price": "invalid_price"}
        )
        
        errors = await shopify_integration._validate_product_content(content)
        assert "Invalid price format" in errors


# Integration test markers
pytestmark = [
    pytest.mark.integration,
    pytest.mark.shopify
]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])