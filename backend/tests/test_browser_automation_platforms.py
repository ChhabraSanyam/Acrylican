"""
Integration Tests for Browser Automation Platforms

Tests for Meesho, Snapdeal, and IndiaMART browser automation integrations.
Uses mock browser automation service for testing without actual browser instances.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

from app.services.platform_integration import (
    Platform,
    PostContent,
    PostResult,
    PostStatus,
    PlatformCredentials,
    AuthenticationMethod
)
from app.services.browser_automation import BrowserCredentials
from app.services.meesho_integration import MeeshoIntegration, MEESHO_CONFIG
from app.services.snapdeal_integration import SnapdealIntegration, SNAPDEAL_CONFIG
from app.services.indiamart_integration import IndiaMARTIntegration, INDIAMART_CONFIG
from app.services.browser_platform_registry import (
    register_browser_automation_platforms,
    get_browser_automation_platforms,
    is_browser_automation_platform,
    validate_content_for_platform,
    get_platform_requirements
)


class TestBrowserAutomationPlatforms:
    """Test suite for browser automation platform integrations."""
    
    @pytest.fixture
    def sample_content(self) -> PostContent:
        """Sample content for testing."""
        return PostContent(
            title="Handcrafted Wooden Jewelry Box",
            description="Beautiful handcrafted wooden jewelry box with intricate carvings. Perfect for storing your precious jewelry items.",
            hashtags=["#handcrafted", "#wooden", "#jewelry", "#box", "#artisan"],
            images=["https://example.com/image1.jpg", "https://example.com/image2.jpg"],
            product_data={
                "price": 1500,
                "category": "Home & Kitchen",
                "brand": "Artisan Crafts",
                "color": "Brown",
                "size": "Medium",
                "stock_quantity": 10
            }
        )
    
    @pytest.fixture
    def browser_credentials(self) -> BrowserCredentials:
        """Sample browser credentials for testing."""
        return BrowserCredentials(
            username="test@example.com",
            password="testpassword123",
            platform=Platform.MEESHO
        )
    
    @pytest.fixture
    def mock_automation_service(self):
        """Mock browser automation service."""
        service = AsyncMock()
        service.authenticate_platform = AsyncMock(return_value=True)
        service.validate_session = AsyncMock(return_value=True)
        service.post_content = AsyncMock(return_value=PostResult(
            platform=Platform.MEESHO,
            status=PostStatus.SUCCESS,
            post_id="test_post_123",
            published_at=datetime.now()
        ))
        service.disconnect_platform = AsyncMock(return_value=True)
        return service


class TestMeeshoIntegration(TestBrowserAutomationPlatforms):
    """Test Meesho platform integration."""
    
    @pytest.fixture
    def meesho_integration(self) -> MeeshoIntegration:
        """Meesho integration instance."""
        return MeeshoIntegration(MEESHO_CONFIG)
    
    @patch('app.services.meesho_integration.get_browser_automation_service')
    async def test_meesho_authentication_success(self, mock_get_service, meesho_integration, browser_credentials, mock_automation_service):
        """Test successful Meesho authentication."""
        mock_get_service.return_value = mock_automation_service
        
        result = await meesho_integration.authenticate(browser_credentials)
        
        assert result is True
        assert meesho_integration.session_active is True
        mock_automation_service.authenticate_platform.assert_called_once_with(
            Platform.MEESHO, 'default', browser_credentials
        )
    
    @patch('app.services.meesho_integration.get_browser_automation_service')
    async def test_meesho_authentication_failure(self, mock_get_service, meesho_integration, browser_credentials):
        """Test failed Meesho authentication."""
        mock_service = AsyncMock()
        mock_service.authenticate_platform = AsyncMock(return_value=False)
        mock_get_service.return_value = mock_service
        
        result = await meesho_integration.authenticate(browser_credentials)
        
        assert result is False
        assert meesho_integration.session_active is False
    
    @patch('app.services.meesho_integration.get_browser_automation_service')
    async def test_meesho_validate_connection(self, mock_get_service, meesho_integration, mock_automation_service):
        """Test Meesho connection validation."""
        mock_get_service.return_value = mock_automation_service
        
        result = await meesho_integration.validate_connection()
        
        assert result is True
        assert meesho_integration.session_active is True
        mock_automation_service.validate_session.assert_called_once_with(Platform.MEESHO, 'default')
    
    @patch('app.services.meesho_integration.get_browser_automation_service')
    async def test_meesho_post_content_success(self, mock_get_service, meesho_integration, sample_content, mock_automation_service):
        """Test successful content posting to Meesho."""
        mock_get_service.return_value = mock_automation_service
        
        result = await meesho_integration.post_content(sample_content)
        
        assert result.platform == Platform.MEESHO
        assert result.status == PostStatus.SUCCESS
        assert result.post_id == "test_post_123"
        mock_automation_service.validate_session.assert_called_once()
        mock_automation_service.post_content.assert_called_once()
    
    @patch('app.services.meesho_integration.get_browser_automation_service')
    async def test_meesho_post_content_invalid_session(self, mock_get_service, meesho_integration, sample_content):
        """Test posting with invalid session."""
        mock_service = AsyncMock()
        mock_service.validate_session = AsyncMock(return_value=False)
        mock_get_service.return_value = mock_service
        
        result = await meesho_integration.post_content(sample_content)
        
        assert result.platform == Platform.MEESHO
        assert result.status == PostStatus.FAILED
        assert result.error_code == "SESSION_INVALID"
    
    async def test_meesho_format_content(self, meesho_integration, sample_content):
        """Test content formatting for Meesho."""
        formatted = await meesho_integration.format_content(sample_content)
        
        assert len(formatted.title) <= 100  # Meesho title limit
        assert len(formatted.description) <= 2000  # Meesho description limit
        assert len(formatted.hashtags) <= 10  # Meesho hashtag limit
        assert len(formatted.images) <= 5  # Meesho image limit
        assert formatted.product_data["category"] == "Home & Kitchen"
        assert formatted.platform_specific["meesho_price"] == 1500
    
    async def test_meesho_format_content_long_title(self, meesho_integration):
        """Test content formatting with long title."""
        long_content = PostContent(
            title="A" * 150,  # Exceeds Meesho limit
            description="Test description",
            hashtags=["#test"],
            images=["image1.jpg"]
        )
        
        formatted = await meesho_integration.format_content(long_content)
        
        assert len(formatted.title) == 100  # Should be truncated
        assert formatted.title == "A" * 100


class TestSnapdealIntegration(TestBrowserAutomationPlatforms):
    """Test Snapdeal platform integration."""
    
    @pytest.fixture
    def snapdeal_integration(self) -> SnapdealIntegration:
        """Snapdeal integration instance."""
        return SnapdealIntegration(SNAPDEAL_CONFIG)
    
    @patch('app.services.snapdeal_integration.get_browser_automation_service')
    async def test_snapdeal_authentication_success(self, mock_get_service, snapdeal_integration, browser_credentials, mock_automation_service):
        """Test successful Snapdeal authentication."""
        browser_credentials.platform = Platform.SNAPDEAL
        mock_get_service.return_value = mock_automation_service
        
        result = await snapdeal_integration.authenticate(browser_credentials)
        
        assert result is True
        assert snapdeal_integration.session_active is True
    
    async def test_snapdeal_format_content(self, snapdeal_integration, sample_content):
        """Test content formatting for Snapdeal."""
        # Add MRP to sample content for Snapdeal
        sample_content.product_data["mrp"] = 2000
        sample_content.product_data["material"] = "Wood"
        
        formatted = await snapdeal_integration.format_content(sample_content)
        
        assert len(formatted.title) <= 150  # Snapdeal title limit
        assert len(formatted.description) <= 3000  # Snapdeal description limit
        assert len(formatted.hashtags) <= 15  # Snapdeal hashtag limit
        assert len(formatted.images) <= 8  # Snapdeal image limit
        assert "Key Features:" in formatted.description
        assert "Brand: Artisan Crafts" in formatted.description
        assert "Material: Wood" in formatted.description
        assert formatted.platform_specific["snapdeal_mrp"] == 2000
    
    @patch('app.services.snapdeal_integration.get_browser_automation_service')
    async def test_snapdeal_post_content_success(self, mock_get_service, snapdeal_integration, sample_content, mock_automation_service):
        """Test successful content posting to Snapdeal."""
        mock_automation_service.post_content.return_value = PostResult(
            platform=Platform.SNAPDEAL,
            status=PostStatus.SUCCESS,
            post_id="snapdeal_123",
            published_at=datetime.now()
        )
        mock_get_service.return_value = mock_automation_service
        
        result = await snapdeal_integration.post_content(sample_content)
        
        assert result.platform == Platform.SNAPDEAL
        assert result.status == PostStatus.SUCCESS
        assert result.post_id == "snapdeal_123"


class TestIndiaMARTIntegration(TestBrowserAutomationPlatforms):
    """Test IndiaMART platform integration."""
    
    @pytest.fixture
    def indiamart_integration(self) -> IndiaMARTIntegration:
        """IndiaMART integration instance."""
        return IndiaMARTIntegration(INDIAMART_CONFIG)
    
    @pytest.fixture
    def b2b_content(self) -> PostContent:
        """B2B focused content for IndiaMART."""
        return PostContent(
            title="Industrial Grade Wooden Storage Boxes",
            description="High-quality wooden storage boxes suitable for industrial and commercial use.",
            hashtags=["#industrial", "#storage", "#wooden", "#commercial"],
            images=["image1.jpg", "image2.jpg"],
            product_data={
                "price": 5000,
                "category": "Industrial Supplies",
                "unit": "Piece",
                "minimum_order": 10,
                "brand": "Industrial Crafts",
                "material": "Hardwood",
                "country_of_origin": "India",
                "payment_terms": "30% Advance, 70% on Delivery",
                "delivery_time": "15-20 days",
                "specifications": {
                    "Length": "50 cm",
                    "Width": "30 cm",
                    "Height": "20 cm",
                    "Weight": "2 kg"
                }
            }
        )
    
    @patch('app.services.indiamart_integration.get_browser_automation_service')
    async def test_indiamart_authentication_success(self, mock_get_service, indiamart_integration, browser_credentials, mock_automation_service):
        """Test successful IndiaMART authentication."""
        browser_credentials.platform = Platform.INDIAMART
        mock_get_service.return_value = mock_automation_service
        
        result = await indiamart_integration.authenticate(browser_credentials)
        
        assert result is True
        assert indiamart_integration.session_active is True
    
    async def test_indiamart_format_content(self, indiamart_integration, b2b_content):
        """Test content formatting for IndiaMART."""
        formatted = await indiamart_integration.format_content(b2b_content)
        
        assert len(formatted.title) <= 200  # IndiaMART title limit
        assert len(formatted.description) <= 5000  # IndiaMART description limit
        assert len(formatted.hashtags) <= 20  # IndiaMART hashtag limit
        assert len(formatted.images) <= 10  # IndiaMART image limit
        
        # Check B2B specific formatting
        assert "Specifications:" in formatted.description
        assert "Length: 50 cm" in formatted.description
        assert "Minimum Order Quantity: 10" in formatted.description
        assert "Payment Terms: 30% Advance, 70% on Delivery" in formatted.description
        assert "bulk orders and business inquiries" in formatted.description
        
        assert formatted.product_data["unit"] == "Piece"
        assert formatted.product_data["minimum_order"] == 10
        assert formatted.platform_specific["indiamart_payment_terms"] == "30% Advance, 70% on Delivery"
    
    @patch('app.services.indiamart_integration.get_browser_automation_service')
    async def test_indiamart_post_content_success(self, mock_get_service, indiamart_integration, b2b_content, mock_automation_service):
        """Test successful content posting to IndiaMART."""
        mock_automation_service.post_content.return_value = PostResult(
            platform=Platform.INDIAMART,
            status=PostStatus.SUCCESS,
            post_id="indiamart_456",
            published_at=datetime.now()
        )
        mock_get_service.return_value = mock_automation_service
        
        result = await indiamart_integration.post_content(b2b_content)
        
        assert result.platform == Platform.INDIAMART
        assert result.status == PostStatus.SUCCESS
        assert result.post_id == "indiamart_456"


class TestBrowserPlatformRegistry:
    """Test browser platform registry functionality."""
    
    def test_register_browser_automation_platforms(self):
        """Test registration of browser automation platforms."""
        results = register_browser_automation_platforms()
        
        assert Platform.MEESHO in results
        assert Platform.SNAPDEAL in results
        assert Platform.INDIAMART in results
        
        # All should be successfully registered
        assert all(results.values())
    
    def test_get_browser_automation_platforms(self):
        """Test getting list of browser automation platforms."""
        platforms = get_browser_automation_platforms()
        
        assert Platform.MEESHO in platforms
        assert Platform.SNAPDEAL in platforms
        assert Platform.INDIAMART in platforms
        assert len(platforms) == 3
    
    def test_is_browser_automation_platform(self):
        """Test checking if platform uses browser automation."""
        assert is_browser_automation_platform(Platform.MEESHO) is True
        assert is_browser_automation_platform(Platform.SNAPDEAL) is True
        assert is_browser_automation_platform(Platform.INDIAMART) is True
        assert is_browser_automation_platform(Platform.FACEBOOK) is False
        assert is_browser_automation_platform(Platform.INSTAGRAM) is False
    
    def test_get_platform_requirements(self):
        """Test getting platform requirements."""
        meesho_req = get_platform_requirements(Platform.MEESHO)
        snapdeal_req = get_platform_requirements(Platform.SNAPDEAL)
        indiamart_req = get_platform_requirements(Platform.INDIAMART)
        
        # Check Meesho requirements
        assert "title" in meesho_req["required_fields"]
        assert "price" in meesho_req["required_fields"]
        assert meesho_req["max_images"] == 5
        assert meesho_req["max_title_length"] == 100
        
        # Check Snapdeal requirements
        assert "brand" in snapdeal_req["required_fields"]
        assert "mrp" in snapdeal_req["required_fields"]
        assert snapdeal_req["max_images"] == 8
        assert snapdeal_req["supports_variants"] is True
        
        # Check IndiaMART requirements
        assert "unit" in indiamart_req["required_fields"]
        assert "minimum_order" in indiamart_req["required_fields"]
        assert indiamart_req["max_images"] == 10
        assert indiamart_req["b2b_focused"] is True
    
    def test_validate_content_for_platform_success(self):
        """Test successful content validation."""
        valid_content = {
            "title": "Test Product",
            "description": "Test description",
            "price": 1000,
            "category": "Fashion"
        }
        
        result = validate_content_for_platform(Platform.MEESHO, valid_content)
        
        assert len(result["errors"]) == 0
        assert len(result["warnings"]) == 0
    
    def test_validate_content_for_platform_missing_fields(self):
        """Test content validation with missing required fields."""
        invalid_content = {
            "title": "Test Product",
            # Missing description, price, category
        }
        
        result = validate_content_for_platform(Platform.MEESHO, invalid_content)
        
        assert len(result["errors"]) > 0
        assert any("description" in error for error in result["errors"])
        assert any("price" in error for error in result["errors"])
        assert any("category" in error for error in result["errors"])
    
    def test_validate_content_for_platform_length_limits(self):
        """Test content validation with length limit violations."""
        long_content = {
            "title": "A" * 200,  # Exceeds Meesho limit of 100
            "description": "B" * 3000,  # Exceeds Meesho limit of 2000
            "price": 1000,
            "category": "Fashion",
            "images": ["img1.jpg"] * 10  # Exceeds Meesho limit of 5
        }
        
        result = validate_content_for_platform(Platform.MEESHO, long_content)
        
        assert len(result["errors"]) >= 2  # Title and description length errors
        assert len(result["warnings"]) >= 1  # Image count warning
        assert any("Title exceeds" in error for error in result["errors"])
        assert any("Description exceeds" in error for error in result["errors"])
    
    def test_validate_content_snapdeal_price_validation(self):
        """Test Snapdeal-specific price validation."""
        invalid_price_content = {
            "title": "Test Product",
            "description": "Test description",
            "price": 2000,  # Higher than MRP
            "mrp": 1500,
            "category": "Fashion",
            "brand": "Test Brand"
        }
        
        result = validate_content_for_platform(Platform.SNAPDEAL, invalid_price_content)
        
        assert len(result["errors"]) > 0
        assert any("Selling price cannot be higher than MRP" in error for error in result["errors"])
    
    def test_validate_content_indiamart_minimum_order(self):
        """Test IndiaMART-specific minimum order validation."""
        invalid_order_content = {
            "title": "Test Product",
            "description": "Test description",
            "price": 1000,
            "unit": "Piece",
            "minimum_order": 0,  # Invalid minimum order
            "category": "Industrial Supplies"
        }
        
        result = validate_content_for_platform(Platform.INDIAMART, invalid_order_content)
        
        assert len(result["errors"]) > 0
        assert any("Minimum order quantity must be at least 1" in error for error in result["errors"])


class TestErrorHandlingAndRetry(TestBrowserAutomationPlatforms):
    """Test error handling and retry mechanisms."""
    
    @pytest.fixture
    def meesho_integration(self) -> MeeshoIntegration:
        """Meesho integration instance."""
        return MeeshoIntegration(MEESHO_CONFIG)
    
    @patch('app.services.meesho_integration.get_browser_automation_service')
    async def test_authentication_error_handling(self, mock_get_service, meesho_integration, browser_credentials):
        """Test authentication error handling."""
        mock_service = AsyncMock()
        mock_service.authenticate_platform = AsyncMock(side_effect=Exception("Network error"))
        mock_get_service.return_value = mock_service
        
        with pytest.raises(Exception):  # Should raise AuthenticationError
            await meesho_integration.authenticate(browser_credentials)
    
    @patch('app.services.meesho_integration.get_browser_automation_service')
    async def test_posting_error_handling(self, mock_get_service, meesho_integration, sample_content):
        """Test posting error handling."""
        mock_service = AsyncMock()
        mock_service.validate_session = AsyncMock(return_value=True)
        mock_service.post_content = AsyncMock(side_effect=Exception("Posting failed"))
        mock_get_service.return_value = mock_service
        
        result = await meesho_integration.post_content(sample_content)
        
        assert result.platform == Platform.MEESHO
        assert result.status == PostStatus.FAILED
        assert result.error_code == "POSTING_ERROR"
        assert "Posting failed" in result.error_message
    
    @patch('app.services.meesho_integration.get_browser_automation_service')
    async def test_session_validation_error_handling(self, mock_get_service, meesho_integration):
        """Test session validation error handling."""
        mock_service = AsyncMock()
        mock_service.validate_session = AsyncMock(side_effect=Exception("Validation error"))
        mock_get_service.return_value = mock_service
        
        result = await meesho_integration.validate_connection()
        
        assert result is False
        assert meesho_integration.session_active is False


@pytest.mark.asyncio
class TestIntegrationWorkflow:
    """Test complete integration workflow."""
    
    @pytest.fixture
    def sample_workflow_content(self) -> PostContent:
        """Sample content for workflow testing."""
        return PostContent(
            title="Artisan Wooden Jewelry Box - Handcrafted",
            description="Exquisite handcrafted wooden jewelry box with traditional Indian designs. Perfect for storing jewelry, accessories, and small treasures.",
            hashtags=["#handcrafted", "#wooden", "#jewelry", "#artisan", "#traditional"],
            images=[
                "https://example.com/jewelry-box-1.jpg",
                "https://example.com/jewelry-box-2.jpg",
                "https://example.com/jewelry-box-3.jpg"
            ],
            product_data={
                "price": 2500,
                "mrp": 3000,
                "category": "Home & Kitchen",
                "brand": "Traditional Crafts",
                "color": "Brown",
                "size": "Medium",
                "material": "Sheesham Wood",
                "weight": "500g",
                "stock_quantity": 25
            }
        )
    
    @patch('app.services.meesho_integration.get_browser_automation_service')
    @patch('app.services.snapdeal_integration.get_browser_automation_service')
    @patch('app.services.indiamart_integration.get_browser_automation_service')
    async def test_multi_platform_posting_workflow(
        self, 
        mock_indiamart_service, 
        mock_snapdeal_service, 
        mock_meesho_service,
        sample_workflow_content
    ):
        """Test posting to multiple browser automation platforms."""
        # Setup mock services
        for mock_service in [mock_meesho_service, mock_snapdeal_service, mock_indiamart_service]:
            service = AsyncMock()
            service.authenticate_platform = AsyncMock(return_value=True)
            service.validate_session = AsyncMock(return_value=True)
            service.post_content = AsyncMock(return_value=PostResult(
                platform=Platform.MEESHO,  # Will be overridden by each platform
                status=PostStatus.SUCCESS,
                post_id="test_post_123",
                published_at=datetime.now()
            ))
            mock_service.return_value = service
        
        # Create integrations
        meesho = MeeshoIntegration(MEESHO_CONFIG)
        snapdeal = SnapdealIntegration(SNAPDEAL_CONFIG)
        indiamart = IndiaMARTIntegration(INDIAMART_CONFIG)
        
        integrations = [meesho, snapdeal, indiamart]
        
        # Test authentication for all platforms
        credentials = BrowserCredentials(
            username="test@example.com",
            password="testpassword123",
            platform=Platform.MEESHO
        )
        
        auth_results = []
        for integration in integrations:
            credentials.platform = integration.platform
            result = await integration.authenticate(credentials)
            auth_results.append(result)
        
        assert all(auth_results), "All platforms should authenticate successfully"
        
        # Test posting to all platforms
        post_results = []
        for integration in integrations:
            result = await integration.post_content(sample_workflow_content)
            post_results.append(result)
        
        assert all(result.status == PostStatus.SUCCESS for result in post_results), "All posts should succeed"
        
        # Test disconnection from all platforms
        disconnect_results = []
        for integration in integrations:
            result = await integration.disconnect()
            disconnect_results.append(result)
        
        assert all(disconnect_results), "All platforms should disconnect successfully"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])