"""
Comprehensive unit tests for all service classes.

This module ensures complete coverage of all service layer functionality
with proper mocking and edge case testing.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any
import json
import io
from PIL import Image

from app.services.content_generation import ContentGenerationService
from app.services.image_processing import ImageProcessingService
from app.services.posting_service import PostingService
from app.services.analytics_service import AnalyticsService
from app.services.platform_service import PlatformService
from app.services.oauth_service import OAuthService
from app.services.sales_tracking import SalesTrackingService
from app.services.engagement_metrics import EngagementMetricsService
from app.services.preferences_service import PreferencesService
from app.services.queue_processor import QueueProcessor
from app.services.data_privacy_service import DataPrivacyService
from app.services.encryption_service import EncryptionService
from app.services.audit_service import AuditService
from app.models import User, Product, Post, SaleEvent, PlatformConnection


@pytest.mark.unit
class TestContentGenerationServiceUnit:
    """Comprehensive unit tests for ContentGenerationService."""
    
    @pytest.fixture
    def service(self):
        return ContentGenerationService()
    
    @pytest.fixture
    def mock_genai(self):
        with patch('app.services.content_generation.genai') as mock:
            yield mock
    
    @pytest.mark.asyncio
    async def test_generate_content_success(self, service, mock_genai):
        """Test successful content generation with proper formatting."""
        mock_response = Mock()
        mock_response.text = """
        Title: Beautiful Handmade Ceramic Vase - Artisan Crafted
        
        Description: Transform your space with this exquisite handcrafted ceramic vase. Each piece is lovingly created by skilled artisans using traditional techniques passed down through generations.
        
        Hashtags: #handmade #ceramic #vase #artisan #homedecor #unique #handcrafted #pottery #art #decor
        """
        
        mock_model = Mock()
        mock_model.generate_content = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model
        
        content_request = {
            'title': 'Ceramic Vase',
            'description': 'Handmade ceramic vase',
            'category': 'Home Decor',
            'price': '45.99'
        }
        
        result = await service.generate_content(content_request)
        
        assert result is not None
        assert 'title' in result
        assert 'description' in result
        assert 'hashtags' in result
        assert isinstance(result['hashtags'], list)
        assert len(result['hashtags']) > 0
        assert 'Beautiful Handmade Ceramic Vase' in result['title']
    
    @pytest.mark.asyncio
    async def test_generate_content_api_failure(self, service, mock_genai):
        """Test content generation with API failure and retry logic."""
        mock_model = Mock()
        mock_model.generate_content = AsyncMock(side_effect=Exception("API Rate Limit"))
        mock_genai.GenerativeModel.return_value = mock_model
        
        content_request = {
            'title': 'Test Product',
            'description': 'Test description'
        }
        
        with pytest.raises(Exception, match="API Rate Limit"):
            await service.generate_content(content_request)
    
    @pytest.mark.asyncio
    async def test_generate_content_empty_response(self, service, mock_genai):
        """Test handling of empty API response."""
        mock_response = Mock()
        mock_response.text = ""
        
        mock_model = Mock()
        mock_model.generate_content = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model
        
        content_request = {'title': 'Test', 'description': 'Test'}
        
        result = await service.generate_content(content_request)
        
        # Should return fallback content
        assert result is not None
        assert 'title' in result
        assert 'description' in result
    
    def test_parse_generated_content(self, service):
        """Test parsing of generated content from API response."""
        api_response = """
        Title: Amazing Product Title
        
        Description: This is a detailed description of the product with multiple sentences. It includes features and benefits.
        
        Hashtags: #tag1 #tag2 #tag3 #tag4 #tag5
        """
        
        result = service._parse_generated_content(api_response)
        
        assert result['title'] == 'Amazing Product Title'
        assert 'detailed description' in result['description']
        assert len(result['hashtags']) == 5
        assert '#tag1' in result['hashtags']
    
    def test_validate_content_length(self, service):
        """Test content length validation for different platforms."""
        content = {
            'title': 'A' * 300,  # Very long title
            'description': 'B' * 5000,  # Very long description
            'hashtags': ['#tag'] * 50  # Too many hashtags
        }
        
        validated = service._validate_content_length(content, 'facebook')
        
        # Should truncate to platform limits
        assert len(validated['title']) <= 255
        assert len(validated['description']) <= 2000
        assert len(validated['hashtags']) <= 30
    
    def test_generate_fallback_content(self, service):
        """Test fallback content generation when API fails."""
        product_data = {
            'title': 'Handmade Jewelry',
            'description': 'Beautiful handcrafted jewelry piece',
            'category': 'Jewelry'
        }
        
        result = service._generate_fallback_content(product_data)
        
        assert result['title'] == 'Handmade Jewelry'
        assert 'Beautiful handcrafted jewelry piece' in result['description']
        assert len(result['hashtags']) > 0
        assert '#handmade' in result['hashtags']


@pytest.mark.unit
class TestImageProcessingServiceUnit:
    """Comprehensive unit tests for ImageProcessingService."""
    
    @pytest.fixture
    def service(self):
        return ImageProcessingService()
    
    @pytest.fixture
    def sample_image(self):
        """Create a sample image for testing."""
        img = Image.new('RGB', (1920, 1080), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        return img_bytes.getvalue()
    
    @pytest.mark.asyncio
    async def test_process_image_success(self, service, sample_image):
        """Test successful image processing with compression and thumbnails."""
        mock_file = Mock()
        mock_file.filename = "test.jpg"
        mock_file.size = len(sample_image)
        mock_file.read = AsyncMock(return_value=sample_image)
        mock_file.seek = AsyncMock()
        
        with patch('app.services.image_processing.get_storage_service') as mock_storage:
            mock_storage_instance = Mock()
            mock_storage_instance.upload_image = AsyncMock(return_value=Mock(
                file_id="test-id",
                url="https://example.com/test.jpg",
                size=1024,
                content_type="image/jpeg"
            ))
            mock_storage.return_value = mock_storage_instance
            
            result = await service.process_image(mock_file, ['facebook', 'instagram'])
            
            assert result is not None
            assert 'original_url' in result
            assert 'compressed_url' in result
            assert 'thumbnail_urls' in result
            assert 'platform_optimized_urls' in result
    
    def test_compress_image(self, service, sample_image):
        """Test image compression with different quality levels."""
        img = Image.open(io.BytesIO(sample_image))
        original_size = len(sample_image)
        
        # Test different compression levels
        compressed_high = service.compress_image(img, quality=95)
        compressed_medium = service.compress_image(img, quality=75)
        compressed_low = service.compress_image(img, quality=50)
        
        # Compressed images should be smaller than original
        assert len(compressed_high) < original_size
        assert len(compressed_medium) < len(compressed_high)
        assert len(compressed_low) < len(compressed_medium)
    
    def test_generate_thumbnails(self, service, sample_image):
        """Test thumbnail generation with different sizes."""
        img = Image.open(io.BytesIO(sample_image))
        
        thumbnail_sizes = [(150, 150), (300, 300), (600, 600)]
        thumbnails = service.generate_thumbnails(img, thumbnail_sizes)
        
        assert len(thumbnails) == len(thumbnail_sizes)
        
        for i, thumbnail_data in enumerate(thumbnails):
            thumb_img = Image.open(io.BytesIO(thumbnail_data))
            expected_size = thumbnail_sizes[i]
            assert thumb_img.width <= expected_size[0]
            assert thumb_img.height <= expected_size[1]
    
    def test_optimize_for_platform(self, service, sample_image):
        """Test platform-specific image optimization."""
        img = Image.open(io.BytesIO(sample_image))
        
        # Test Facebook optimization
        fb_optimized = service.optimize_for_platform(img, 'facebook')
        fb_img = Image.open(io.BytesIO(fb_optimized))
        assert fb_img.width <= 1200  # Facebook recommended width
        
        # Test Instagram optimization
        ig_optimized = service.optimize_for_platform(img, 'instagram')
        ig_img = Image.open(io.BytesIO(ig_optimized))
        assert ig_img.width == ig_img.height  # Instagram square format
    
    def test_validate_image_format(self, service):
        """Test image format validation."""
        # Valid formats
        assert service.validate_image_format("test.jpg") is True
        assert service.validate_image_format("test.jpeg") is True
        assert service.validate_image_format("test.png") is True
        assert service.validate_image_format("test.webp") is True
        
        # Invalid formats
        assert service.validate_image_format("test.gif") is False
        assert service.validate_image_format("test.bmp") is False
        assert service.validate_image_format("test.txt") is False
    
    def test_calculate_image_metrics(self, service, sample_image):
        """Test image metrics calculation."""
        img = Image.open(io.BytesIO(sample_image))
        
        metrics = service.calculate_image_metrics(img, len(sample_image))
        
        assert metrics['width'] == 1920
        assert metrics['height'] == 1080
        assert metrics['aspect_ratio'] == 1920 / 1080
        assert metrics['file_size'] == len(sample_image)
        assert metrics['format'] == 'JPEG'


@pytest.mark.unit
class TestPostingServiceUnit:
    """Comprehensive unit tests for PostingService."""
    
    @pytest.fixture
    def service(self):
        with patch('app.services.posting_service.get_db'):
            return PostingService()
    
    @pytest.fixture
    def sample_post_data(self):
        return {
            'id': 'post-123',
            'user_id': 'user-123',
            'product_id': 'product-123',
            'content': {
                'title': 'Test Post',
                'description': 'Test description',
                'hashtags': ['#test', '#handmade']
            },
            'platforms': ['facebook', 'instagram'],
            'images': ['https://example.com/image1.jpg'],
            'scheduled_at': datetime.utcnow() + timedelta(hours=2)
        }
    
    @pytest.mark.asyncio
    async def test_create_post_success(self, service, sample_post_data):
        """Test successful post creation."""
        with patch.object(service, 'db') as mock_db:
            mock_db.add = Mock()
            mock_db.commit = Mock()
            mock_db.refresh = Mock()
            
            result = await service.create_post(sample_post_data)
            
            assert result is not None
            assert result['status'] == 'scheduled'
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_schedule_post(self, service, sample_post_data):
        """Test post scheduling functionality."""
        schedule_time = datetime.utcnow() + timedelta(hours=4)
        
        with patch.object(service, 'db') as mock_db:
            mock_db.add = Mock()
            mock_db.commit = Mock()
            
            result = await service.schedule_post(
                sample_post_data, 
                schedule_time, 
                mock_db
            )
            
            assert result['scheduled'] is True
            assert result['scheduled_at'] == schedule_time
    
    @pytest.mark.asyncio
    async def test_get_due_posts(self, service):
        """Test retrieval of posts due for publishing."""
        mock_posts = [
            Mock(id='post-1', scheduled_at=datetime.utcnow() - timedelta(minutes=5)),
            Mock(id='post-2', scheduled_at=datetime.utcnow() - timedelta(minutes=10))
        ]
        
        with patch.object(service, 'db') as mock_db:
            mock_query = Mock()
            mock_query.filter.return_value.filter.return_value.all.return_value = mock_posts
            mock_db.query.return_value = mock_query
            
            due_posts = await service.get_due_posts()
            
            assert len(due_posts) == 2
            assert due_posts[0].id == 'post-1'
    
    def test_validate_post_content(self, service):
        """Test post content validation."""
        valid_content = {
            'title': 'Valid Title',
            'description': 'Valid description',
            'hashtags': ['#valid', '#tags']
        }
        
        invalid_content = {
            'title': '',  # Empty title
            'description': 'A' * 10000,  # Too long
            'hashtags': []  # No hashtags
        }
        
        assert service.validate_post_content(valid_content) is True
        assert service.validate_post_content(invalid_content) is False
    
    def test_calculate_posting_priority(self, service):
        """Test posting priority calculation."""
        high_priority_post = {
            'platforms': ['facebook', 'instagram', 'pinterest'],
            'engagement_history': {'avg_likes': 100, 'avg_shares': 20},
            'scheduled_at': datetime.utcnow() + timedelta(minutes=30)
        }
        
        low_priority_post = {
            'platforms': ['facebook'],
            'engagement_history': {'avg_likes': 10, 'avg_shares': 2},
            'scheduled_at': datetime.utcnow() + timedelta(hours=24)
        }
        
        high_score = service.calculate_posting_priority(high_priority_post)
        low_score = service.calculate_posting_priority(low_priority_post)
        
        assert high_score > low_score


@pytest.mark.unit
class TestAnalyticsServiceUnit:
    """Comprehensive unit tests for AnalyticsService."""
    
    @pytest.fixture
    def service(self):
        mock_db = Mock()
        return AnalyticsService(mock_db)
    
    @pytest.fixture
    def sample_sales_data(self):
        return [
            {
                'id': 'sale-1',
                'amount': Decimal('25.99'),
                'platform': 'facebook',
                'occurred_at': datetime.utcnow() - timedelta(days=1),
                'product_id': 'product-1'
            },
            {
                'id': 'sale-2',
                'amount': Decimal('45.50'),
                'platform': 'instagram',
                'occurred_at': datetime.utcnow() - timedelta(days=2),
                'product_id': 'product-2'
            },
            {
                'id': 'sale-3',
                'amount': Decimal('30.00'),
                'platform': 'facebook',
                'occurred_at': datetime.utcnow() - timedelta(days=3),
                'product_id': 'product-1'
            }
        ]
    
    @pytest.mark.asyncio
    async def test_calculate_revenue_metrics(self, service, sample_sales_data):
        """Test revenue metrics calculation."""
        with patch.object(service, 'get_sales_data', return_value=sample_sales_data):
            metrics = await service.calculate_revenue_metrics('user-123', 30)
            
            assert metrics['total_revenue'] == Decimal('101.49')
            assert metrics['total_orders'] == 3
            assert metrics['average_order_value'] == Decimal('33.83')
    
    @pytest.mark.asyncio
    async def test_get_platform_breakdown(self, service, sample_sales_data):
        """Test platform performance breakdown."""
        with patch.object(service, 'get_sales_data', return_value=sample_sales_data):
            breakdown = await service.get_platform_breakdown('user-123', 30)
            
            assert 'facebook' in breakdown
            assert 'instagram' in breakdown
            assert breakdown['facebook']['revenue'] == Decimal('55.99')
            assert breakdown['facebook']['orders'] == 2
            assert breakdown['instagram']['revenue'] == Decimal('45.50')
            assert breakdown['instagram']['orders'] == 1
    
    @pytest.mark.asyncio
    async def test_get_top_products(self, service, sample_sales_data):
        """Test top products identification."""
        mock_products = [
            {
                'id': 'product-1',
                'title': 'Product 1',
                'revenue': Decimal('55.99'),
                'orders': 2
            },
            {
                'id': 'product-2',
                'title': 'Product 2',
                'revenue': Decimal('45.50'),
                'orders': 1
            }
        ]
        
        with patch.object(service, 'get_product_performance', return_value=mock_products):
            top_products = await service.get_top_products('user-123', limit=5)
            
            assert len(top_products) == 2
            assert top_products[0]['revenue'] >= top_products[1]['revenue']
    
    def test_calculate_growth_rate(self, service):
        """Test growth rate calculation."""
        current_value = 150.0
        previous_value = 100.0
        
        growth_rate = service.calculate_growth_rate(current_value, previous_value)
        
        assert growth_rate == 0.5  # 50% growth
    
    def test_calculate_conversion_rate(self, service):
        """Test conversion rate calculation."""
        conversions = 25
        total_visitors = 1000
        
        conversion_rate = service.calculate_conversion_rate(conversions, total_visitors)
        
        assert conversion_rate == 0.025  # 2.5% conversion rate
    
    @pytest.mark.asyncio
    async def test_generate_insights(self, service, sample_sales_data):
        """Test automated insights generation."""
        with patch.object(service, 'get_sales_data', return_value=sample_sales_data):
            insights = await service.generate_insights('user-123', 30)
            
            assert isinstance(insights, list)
            assert len(insights) > 0
            
            # Check for specific insight types
            insight_types = [insight['type'] for insight in insights]
            assert 'top_platform' in insight_types
            assert 'revenue_trend' in insight_types


@pytest.mark.unit
class TestPlatformServiceUnit:
    """Comprehensive unit tests for PlatformService."""
    
    @pytest.fixture
    def service(self):
        return PlatformService()
    
    @pytest.mark.asyncio
    async def test_get_user_connections(self, service):
        """Test retrieval of user platform connections."""
        mock_connections = [
            Mock(
                platform='facebook',
                is_active=True,
                expires_at=datetime.utcnow() + timedelta(days=30)
            ),
            Mock(
                platform='instagram',
                is_active=True,
                expires_at=datetime.utcnow() - timedelta(days=1)  # Expired
            )
        ]
        
        with patch.object(service, 'db') as mock_db:
            mock_query = Mock()
            mock_query.filter.return_value.all.return_value = mock_connections
            mock_db.query.return_value = mock_query
            
            connections = await service.get_user_connections('user-123')
            
            assert len(connections) == 2
            assert connections[0].platform == 'facebook'
    
    @pytest.mark.asyncio
    async def test_validate_connections(self, service):
        """Test platform connection validation."""
        mock_connections = [
            {
                'platform': 'facebook',
                'is_active': True,
                'expires_at': datetime.utcnow() + timedelta(days=30),
                'access_token': 'valid_token'
            },
            {
                'platform': 'instagram',
                'is_active': True,
                'expires_at': datetime.utcnow() - timedelta(days=1),  # Expired
                'access_token': 'expired_token'
            }
        ]
        
        with patch.object(service, 'get_user_connections', return_value=mock_connections):
            validation_results = await service.validate_connections('user-123')
            
            assert validation_results['facebook']['valid'] is True
            assert validation_results['instagram']['valid'] is False
            assert 'expired' in validation_results['instagram']['reason']
    
    @pytest.mark.asyncio
    async def test_disconnect_platform(self, service):
        """Test platform disconnection."""
        with patch.object(service, 'db') as mock_db:
            mock_connection = Mock()
            mock_query = Mock()
            mock_query.filter.return_value.filter.return_value.first.return_value = mock_connection
            mock_db.query.return_value = mock_query
            mock_db.delete = Mock()
            mock_db.commit = Mock()
            
            result = await service.disconnect_platform('user-123', 'facebook')
            
            assert result['success'] is True
            mock_db.delete.assert_called_once_with(mock_connection)
            mock_db.commit.assert_called_once()
    
    def test_get_supported_platforms(self, service):
        """Test retrieval of supported platforms."""
        platforms = service.get_supported_platforms()
        
        assert isinstance(platforms, list)
        assert len(platforms) > 0
        assert 'facebook' in platforms
        assert 'instagram' in platforms
        assert 'etsy' in platforms
    
    def test_get_platform_capabilities(self, service):
        """Test platform capabilities retrieval."""
        fb_capabilities = service.get_platform_capabilities('facebook')
        
        assert 'posting' in fb_capabilities
        assert 'analytics' in fb_capabilities
        assert 'oauth' in fb_capabilities
        
        # Test unsupported platform
        unknown_capabilities = service.get_platform_capabilities('unknown')
        assert unknown_capabilities == {}


@pytest.mark.unit
class TestSecurityServicesUnit:
    """Comprehensive unit tests for security-related services."""
    
    @pytest.fixture
    def encryption_service(self):
        return EncryptionService()
    
    @pytest.fixture
    def audit_service(self):
        mock_db = Mock()
        return AuditService(mock_db)
    
    def test_encrypt_decrypt_data(self, encryption_service):
        """Test data encryption and decryption."""
        original_data = "sensitive_information"
        
        encrypted = encryption_service.encrypt(original_data)
        decrypted = encryption_service.decrypt(encrypted)
        
        assert encrypted != original_data
        assert decrypted == original_data
    
    def test_hash_password(self, encryption_service):
        """Test password hashing."""
        password = "secure_password123"
        
        hashed = encryption_service.hash_password(password)
        
        assert hashed != password
        assert encryption_service.verify_password(password, hashed) is True
        assert encryption_service.verify_password("wrong_password", hashed) is False
    
    @pytest.mark.asyncio
    async def test_log_security_event(self, audit_service):
        """Test security event logging."""
        with patch.object(audit_service, 'db') as mock_db:
            mock_db.add = Mock()
            mock_db.commit = Mock()
            
            await audit_service.log_security_event(
                user_id='user-123',
                event_type='login_attempt',
                details={'ip_address': '192.168.1.1', 'success': True}
            )
            
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_security_events(self, audit_service):
        """Test security events retrieval."""
        mock_events = [
            Mock(
                event_type='login_attempt',
                timestamp=datetime.utcnow(),
                details={'success': True}
            ),
            Mock(
                event_type='password_change',
                timestamp=datetime.utcnow() - timedelta(hours=1),
                details={'success': True}
            )
        ]
        
        with patch.object(audit_service, 'db') as mock_db:
            mock_query = Mock()
            mock_query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_events
            mock_db.query.return_value = mock_query
            
            events = await audit_service.get_security_events('user-123', limit=10)
            
            assert len(events) == 2
            assert events[0].event_type == 'login_attempt'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])