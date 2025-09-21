"""
Unit tests for image processing service.
"""

import io
import pytest
from PIL import Image
from fastapi import UploadFile
from unittest.mock import Mock, AsyncMock, patch

from app.services.image_processing import (
    ImageProcessingService,
    ImageValidationError,
    PLATFORM_REQUIREMENTS,
    THUMBNAIL_SIZES,
    SUPPORTED_FORMATS
)
from app.services.cloud_storage import StoredFile
from datetime import datetime


class TestImageProcessingService:
    """Test cases for ImageProcessingService."""
    
    @pytest.fixture
    def service(self):
        """Create ImageProcessingService instance."""
        return ImageProcessingService()
    
    @pytest.fixture
    def sample_image(self):
        """Create a sample PIL Image for testing."""
        img = Image.new('RGB', (800, 600), color='red')
        return img
    
    @pytest.fixture
    def sample_image_bytes(self, sample_image):
        """Create sample image as bytes."""
        output = io.BytesIO()
        sample_image.save(output, format='JPEG')
        output.seek(0)
        return output.getvalue()
    
    @pytest.fixture
    def mock_upload_file(self, sample_image_bytes):
        """Create mock UploadFile."""
        file = Mock(spec=UploadFile)
        file.filename = "test_image.jpg"
        file.size = len(sample_image_bytes)
        file.read = AsyncMock(return_value=sample_image_bytes)
        file.seek = AsyncMock()
        return file
    
    @pytest.fixture
    def large_image(self):
        """Create a large PIL Image for testing."""
        return Image.new('RGB', (3000, 2000), color='blue')
    
    @pytest.fixture
    def small_image(self):
        """Create a small PIL Image for testing."""
        return Image.new('RGB', (50, 50), color='green')
    
    @pytest.fixture
    def rgba_image(self):
        """Create an RGBA PIL Image for testing."""
        return Image.new('RGBA', (400, 300), color=(255, 0, 0, 128))

    # Test image validation
    @pytest.mark.asyncio
    async def test_validate_image_success(self, service, mock_upload_file):
        """Test successful image validation."""
        # Should not raise any exception
        await service.validate_image(mock_upload_file)
    
    @pytest.mark.asyncio
    async def test_validate_image_file_too_large(self, service):
        """Test validation failure for oversized file."""
        large_file = Mock(spec=UploadFile)
        large_file.size = service.max_file_size + 1
        large_file.filename = "large.jpg"
        
        with pytest.raises(ImageValidationError, match="exceeds maximum allowed size"):
            await service.validate_image(large_file)
    
    @pytest.mark.asyncio
    async def test_validate_image_invalid_extension(self, service, sample_image_bytes):
        """Test validation failure for invalid file extension."""
        invalid_file = Mock(spec=UploadFile)
        invalid_file.filename = "test.txt"
        invalid_file.size = len(sample_image_bytes)
        invalid_file.read = AsyncMock(return_value=sample_image_bytes)
        invalid_file.seek = AsyncMock()
        
        with pytest.raises(ImageValidationError, match="File extension .txt not supported"):
            await service.validate_image(invalid_file)
    
    @pytest.mark.asyncio
    async def test_validate_image_too_small(self, service):
        """Test validation failure for image too small."""
        small_img = Image.new('RGB', (50, 50), color='red')
        small_bytes = io.BytesIO()
        small_img.save(small_bytes, format='JPEG')
        small_bytes = small_bytes.getvalue()
        
        small_file = Mock(spec=UploadFile)
        small_file.filename = "small.jpg"
        small_file.size = len(small_bytes)
        small_file.read = AsyncMock(return_value=small_bytes)
        small_file.seek = AsyncMock()
        
        with pytest.raises(ImageValidationError, match="Image dimensions too small"):
            await service.validate_image(small_file)
    
    @pytest.mark.asyncio
    async def test_validate_image_corrupted(self, service):
        """Test validation failure for corrupted image."""
        corrupted_file = Mock(spec=UploadFile)
        corrupted_file.filename = "corrupted.jpg"
        corrupted_file.size = 100
        corrupted_file.read = AsyncMock(return_value=b"not an image")
        corrupted_file.seek = AsyncMock()
        
        with pytest.raises(ImageValidationError, match="Invalid image file"):
            await service.validate_image(corrupted_file)

    # Test image compression
    def test_compress_image_default(self, service, sample_image):
        """Test image compression with default settings."""
        compressed = service.compress_image(sample_image)
        
        assert isinstance(compressed, bytes)
        assert len(compressed) > 0
        
        # Verify compressed image can be opened
        compressed_img = Image.open(io.BytesIO(compressed))
        assert compressed_img.format == 'JPEG'
        assert compressed_img.size == sample_image.size
    
    def test_compress_image_with_quality(self, service):
        """Test image compression with custom quality."""
        # Create a more complex image with gradients that will show quality differences
        complex_img = Image.new('RGB', (400, 300))
        pixels = []
        for y in range(300):
            for x in range(400):
                # Create gradient pattern
                r = int((x / 400) * 255)
                g = int((y / 300) * 255)
                b = int(((x + y) / 700) * 255)
                pixels.append((r, g, b))
        complex_img.putdata(pixels)
        
        high_quality = service.compress_image(complex_img, quality=95)
        low_quality = service.compress_image(complex_img, quality=30)
        
        # High quality should result in larger file size for complex images
        assert len(high_quality) > len(low_quality)
    
    def test_compress_image_with_resize(self, service, large_image):
        """Test image compression with resizing."""
        compressed = service.compress_image(large_image, max_width=1000, max_height=800)
        
        compressed_img = Image.open(io.BytesIO(compressed))
        assert compressed_img.width <= 1000
        assert compressed_img.height <= 800
    
    def test_compress_image_rgba_conversion(self, service, rgba_image):
        """Test RGBA image conversion to RGB during compression."""
        compressed = service.compress_image(rgba_image)
        
        compressed_img = Image.open(io.BytesIO(compressed))
        assert compressed_img.mode == 'RGB'
        assert compressed_img.format == 'JPEG'

    # Test thumbnail generation
    def test_generate_thumbnail(self, service, sample_image):
        """Test thumbnail generation."""
        size = (150, 150)
        thumbnail = service.generate_thumbnail(sample_image, size)
        
        assert isinstance(thumbnail, bytes)
        assert len(thumbnail) > 0
        
        # Verify thumbnail
        thumb_img = Image.open(io.BytesIO(thumbnail))
        assert thumb_img.format == 'JPEG'
        assert thumb_img.width <= size[0]
        assert thumb_img.height <= size[1]
    
    def test_generate_thumbnail_maintains_aspect_ratio(self, service, sample_image):
        """Test that thumbnail generation maintains aspect ratio."""
        size = (200, 200)
        thumbnail = service.generate_thumbnail(sample_image, size)
        
        thumb_img = Image.open(io.BytesIO(thumbnail))
        
        # Original aspect ratio: 800/600 = 1.33
        # Thumbnail should maintain this ratio
        thumb_ratio = thumb_img.width / thumb_img.height
        original_ratio = sample_image.width / sample_image.height
        
        assert abs(thumb_ratio - original_ratio) < 0.01  # Allow small floating point differences

    # Test platform optimization
    def test_optimize_for_platform_facebook(self, service, sample_image):
        """Test platform optimization for Facebook."""
        optimized = service.optimize_for_platform(sample_image, 'facebook')
        
        assert isinstance(optimized, bytes)
        
        opt_img = Image.open(io.BytesIO(optimized))
        fb_req = PLATFORM_REQUIREMENTS['facebook']
        
        assert opt_img.width <= fb_req['max_width']
        assert opt_img.height <= fb_req['max_height']
        assert opt_img.format == 'JPEG'
    
    def test_optimize_for_platform_instagram(self, service, large_image):
        """Test platform optimization for Instagram."""
        optimized = service.optimize_for_platform(large_image, 'instagram')
        
        opt_img = Image.open(io.BytesIO(optimized))
        ig_req = PLATFORM_REQUIREMENTS['instagram']
        
        assert opt_img.width <= ig_req['max_width']
        assert opt_img.height <= ig_req['max_height']
    
    def test_optimize_for_platform_invalid(self, service, sample_image):
        """Test platform optimization with invalid platform."""
        with pytest.raises(ValueError, match="Platform invalid_platform not supported"):
            service.optimize_for_platform(sample_image, 'invalid_platform')

    # Test full image processing with cloud storage
    @pytest.mark.asyncio
    @patch('app.services.image_processing.get_storage_service')
    async def test_process_image_success_with_cloud_storage(self, mock_get_storage_service, service, mock_upload_file):
        """Test successful image processing with cloud storage integration."""
        # Mock cloud storage responses
        mock_stored_files = {}
        for image_type in ['original', 'compressed', 'thumbnail_small', 'thumbnail_medium', 'thumbnail_large', 'platform_facebook', 'platform_instagram']:
            mock_stored_files[image_type] = StoredFile(
                file_id=f"file-{image_type}",
                filename=f"{image_type}_test_image.jpg",
                url=f"https://example.com/{image_type}_test_image.jpg",
                size=1024,
                content_type="image/jpeg",
                storage_path=f"images/{image_type}/test_image.jpg",
                created_at=datetime.utcnow()
            )
        
        mock_storage_service = Mock()
        mock_get_storage_service.return_value = mock_storage_service
        mock_storage_service.upload_image = AsyncMock(side_effect=lambda file_data, filename, content_type, image_type: mock_stored_files[image_type])
        
        platforms = ['facebook', 'instagram']
        result = await service.process_image(mock_upload_file, platforms)
        
        assert result.id is not None
        assert result.original_filename == "test_image.jpg"
        assert result.file_size > 0
        assert result.dimensions['width'] == 800
        assert result.dimensions['height'] == 600
        assert result.format == 'JPEG'
        
        # Verify cloud storage URLs
        assert result.original_url == "https://example.com/original_test_image.jpg"
        assert result.compressed_url == "https://example.com/compressed_test_image.jpg"
        
        # Verify thumbnail URLs
        assert len(result.thumbnail_urls) == len(THUMBNAIL_SIZES)
        for size_name in THUMBNAIL_SIZES:
            assert size_name in result.thumbnail_urls
            assert result.thumbnail_urls[size_name] == f"https://example.com/thumbnail_{size_name}_test_image.jpg"
        
        # Verify platform optimization URLs
        assert len(result.platform_optimized_urls) == len(platforms)
        for platform in platforms:
            assert platform in result.platform_optimized_urls
            assert result.platform_optimized_urls[platform] == f"https://example.com/platform_{platform}_test_image.jpg"
        
        # Verify storage paths
        assert len(result.storage_paths) == 5 + len(platforms)  # original, compressed, 3 thumbnails, + platforms
    
    @pytest.mark.asyncio
    @patch('app.services.image_processing.get_storage_service')
    async def test_process_image_with_product_id(self, mock_get_storage_service, service, mock_upload_file):
        """Test image processing with product ID for organized storage."""
        mock_stored_files = {
            'original': StoredFile(
                file_id="file-original",
                filename="test_image.jpg",
                url="https://example.com/products/product-123/original/test_image.jpg",
                size=1024,
                content_type="image/jpeg",
                storage_path="products/product-123/original/test_image.jpg",
                created_at=datetime.utcnow()
            ),
            'compressed': StoredFile(
                file_id="file-compressed",
                filename="compressed_test_image.jpg",
                url="https://example.com/products/product-123/compressed/test_image.jpg",
                size=512,
                content_type="image/jpeg",
                storage_path="products/product-123/compressed/test_image.jpg",
                created_at=datetime.utcnow()
            )
        }
        
        mock_storage_service = Mock()
        mock_get_storage_service.return_value = mock_storage_service
        mock_storage_service.upload_product_images = AsyncMock(return_value=mock_stored_files)
        
        result = await service.process_image(mock_upload_file, product_id="product-123")
        
        # Verify product-specific storage was used
        mock_storage_service.upload_product_images.assert_called_once()
        
        # Verify URLs contain product path
        assert "products/product-123" in result.original_url
        assert "products/product-123" in result.compressed_url
    
    @pytest.mark.asyncio
    @patch('app.services.image_processing.get_storage_service')
    async def test_process_image_no_platforms(self, mock_get_storage_service, service, mock_upload_file):
        """Test image processing without platform optimization."""
        # Mock minimal storage responses
        mock_stored_files = {
            'original': StoredFile(
                file_id="file-original", filename="test_image.jpg",
                url="https://example.com/original_test_image.jpg", size=1024,
                content_type="image/jpeg", storage_path="images/original/test_image.jpg",
                created_at=datetime.utcnow()
            ),
            'compressed': StoredFile(
                file_id="file-compressed", filename="compressed_test_image.jpg",
                url="https://example.com/compressed_test_image.jpg", size=512,
                content_type="image/jpeg", storage_path="images/compressed/test_image.jpg",
                created_at=datetime.utcnow()
            )
        }
        
        # Add thumbnail files
        for size_name in THUMBNAIL_SIZES:
            mock_stored_files[f'thumbnail_{size_name}'] = StoredFile(
                file_id=f"file-thumb-{size_name}", filename=f"thumb_{size_name}_test_image.jpg",
                url=f"https://example.com/thumb_{size_name}_test_image.jpg", size=256,
                content_type="image/jpeg", storage_path=f"images/thumbnail_{size_name}/test_image.jpg",
                created_at=datetime.utcnow()
            )
        
        mock_storage_service = Mock()
        mock_get_storage_service.return_value = mock_storage_service
        mock_storage_service.upload_image = AsyncMock(side_effect=lambda file_data, filename, content_type, image_type: mock_stored_files[image_type])
        
        result = await service.process_image(mock_upload_file)
        
        assert len(result.platform_optimized_urls) == 0
        assert len(result.thumbnail_urls) == len(THUMBNAIL_SIZES)
    
    @pytest.mark.asyncio
    @patch('app.services.image_processing.get_storage_service')
    async def test_process_image_invalid_platform(self, mock_get_storage_service, service, mock_upload_file):
        """Test image processing with invalid platform (should skip with warning)."""
        # Mock storage service
        mock_storage_service = Mock()
        mock_get_storage_service.return_value = mock_storage_service
        
        # Mock minimal storage responses
        mock_stored_files = {
            'original': StoredFile(
                file_id="file-original", filename="test_image.jpg",
                url="https://example.com/original_test_image.jpg", size=1024,
                content_type="image/jpeg", storage_path="images/original/test_image.jpg",
                created_at=datetime.utcnow()
            ),
            'compressed': StoredFile(
                file_id="file-compressed", filename="compressed_test_image.jpg",
                url="https://example.com/compressed_test_image.jpg", size=512,
                content_type="image/jpeg", storage_path="images/compressed/test_image.jpg",
                created_at=datetime.utcnow()
            ),
            'platform_facebook': StoredFile(
                file_id="file-facebook", filename="facebook_test_image.jpg",
                url="https://example.com/facebook_test_image.jpg", size=512,
                content_type="image/jpeg", storage_path="images/platform_facebook/test_image.jpg",
                created_at=datetime.utcnow()
            )
        }
        
        # Add thumbnail files
        for size_name in THUMBNAIL_SIZES:
            mock_stored_files[f'thumbnail_{size_name}'] = StoredFile(
                file_id=f"file-thumb-{size_name}", filename=f"thumb_{size_name}_test_image.jpg",
                url=f"https://example.com/thumb_{size_name}_test_image.jpg", size=256,
                content_type="image/jpeg", storage_path=f"images/thumbnail_{size_name}/test_image.jpg",
                created_at=datetime.utcnow()
            )
        
        mock_storage_service.upload_image = AsyncMock(side_effect=lambda file_data, filename, content_type, image_type: mock_stored_files[image_type])
        
        platforms = ['facebook', 'invalid_platform']
        result = await service.process_image(mock_upload_file, platforms)
        
        # Should only have facebook optimization, invalid_platform should be skipped
        assert 'facebook' in result.platform_optimized_urls
        assert 'invalid_platform' not in result.platform_optimized_urls

    # Test utility methods
    def test_resize_image_both_constraints(self, service, large_image):
        """Test image resizing with both width and height constraints."""
        resized = service._resize_image(large_image, max_width=1000, max_height=800)
        
        assert resized.width <= 1000
        assert resized.height <= 800
        
        # Should maintain aspect ratio
        original_ratio = large_image.width / large_image.height
        resized_ratio = resized.width / resized.height
        assert abs(original_ratio - resized_ratio) < 0.01
    
    def test_resize_image_width_only(self, service, large_image):
        """Test image resizing with width constraint only."""
        resized = service._resize_image(large_image, max_width=1000)
        
        assert resized.width <= 1000
        # Height should be proportionally scaled
        expected_height = int(large_image.height * (1000 / large_image.width))
        assert abs(resized.height - expected_height) <= 1  # Allow 1 pixel difference due to rounding
    
    def test_resize_image_no_resize_needed(self, service, sample_image):
        """Test that small images are not resized."""
        resized = service._resize_image(sample_image, max_width=1000, max_height=800)
        
        # Should return same image since it's already smaller
        assert resized.size == sample_image.size
    
    def test_get_platform_requirements(self, service):
        """Test getting platform requirements."""
        fb_req = service.get_platform_requirements('facebook')
        
        assert 'max_width' in fb_req
        assert 'max_height' in fb_req
        assert 'quality' in fb_req
        assert 'format' in fb_req
        
        # Should be a copy, not reference
        fb_req['max_width'] = 9999
        original_req = service.get_platform_requirements('facebook')
        assert original_req['max_width'] != 9999
    
    def test_get_platform_requirements_invalid(self, service):
        """Test getting requirements for invalid platform."""
        with pytest.raises(ValueError, match="Platform invalid not supported"):
            service.get_platform_requirements('invalid')
    
    def test_get_supported_platforms(self, service):
        """Test getting list of supported platforms."""
        platforms = service.get_supported_platforms()
        
        assert isinstance(platforms, list)
        assert len(platforms) > 0
        assert 'facebook' in platforms
        assert 'instagram' in platforms
        assert len(platforms) == len(PLATFORM_REQUIREMENTS)


class TestImageProcessingConstants:
    """Test image processing constants and configurations."""
    
    def test_supported_formats(self):
        """Test supported formats configuration."""
        assert 'JPEG' in SUPPORTED_FORMATS
        assert 'PNG' in SUPPORTED_FORMATS
        assert 'WEBP' in SUPPORTED_FORMATS
    
    def test_platform_requirements_structure(self):
        """Test platform requirements have required fields."""
        required_fields = {'max_width', 'max_height', 'quality', 'format'}
        
        for platform, requirements in PLATFORM_REQUIREMENTS.items():
            assert isinstance(platform, str)
            assert isinstance(requirements, dict)
            
            for field in required_fields:
                assert field in requirements
                
            assert isinstance(requirements['max_width'], int)
            assert isinstance(requirements['max_height'], int)
            assert isinstance(requirements['quality'], int)
            assert isinstance(requirements['format'], str)
            
            assert 1 <= requirements['quality'] <= 100
            assert requirements['max_width'] > 0
            assert requirements['max_height'] > 0
    
    def test_thumbnail_sizes_structure(self):
        """Test thumbnail sizes configuration."""
        for size_name, dimensions in THUMBNAIL_SIZES.items():
            assert isinstance(size_name, str)
            assert isinstance(dimensions, tuple)
            assert len(dimensions) == 2
            assert isinstance(dimensions[0], int)
            assert isinstance(dimensions[1], int)
            assert dimensions[0] > 0
            assert dimensions[1] > 0


class TestImageProcessingCloudStorageIntegration:
    """Test cloud storage integration methods in ImageProcessingService."""
    
    @pytest.fixture
    def service(self):
        """Create ImageProcessingService instance."""
        return ImageProcessingService()
    
    @pytest.mark.asyncio
    @patch('app.services.image_processing.get_storage_service')
    async def test_delete_processed_image(self, mock_get_storage_service, service):
        """Test deletion of processed image from cloud storage."""
        storage_paths = {
            'original': 'images/original/test.jpg',
            'compressed': 'images/compressed/test.jpg',
            'thumbnail_small': 'images/thumbnail_small/test.jpg'
        }
        
        mock_storage_service = Mock()
        mock_get_storage_service.return_value = mock_storage_service
        mock_storage_service.delete_file = AsyncMock(return_value=True)
        
        result = await service.delete_processed_image(storage_paths)
        
        assert len(result) == 3
        for path in storage_paths.values():
            assert result[path] is True
        
        assert mock_storage_service.delete_file.call_count == 3
    
    @pytest.mark.asyncio
    @patch('app.services.image_processing.get_storage_service')
    async def test_delete_processed_image_partial_failure(self, mock_get_storage_service, service):
        """Test deletion with some failures."""
        storage_paths = {
            'original': 'images/original/test.jpg',
            'compressed': 'images/compressed/test.jpg'
        }
        
        mock_storage_service = Mock()
        mock_get_storage_service.return_value = mock_storage_service
        # Mock one success, one failure
        mock_storage_service.delete_file = AsyncMock(side_effect=[True, False])
        
        result = await service.delete_processed_image(storage_paths)
        
        assert result['images/original/test.jpg'] is True
        assert result['images/compressed/test.jpg'] is False
    
    @pytest.mark.asyncio
    @patch('app.services.image_processing.get_storage_service')
    async def test_generate_presigned_upload_url(self, mock_get_storage_service, service):
        """Test presigned upload URL generation."""
        from app.services.cloud_storage import PresignedUploadData
        from datetime import datetime, timedelta
        
        mock_presigned_data = PresignedUploadData(
            upload_url="https://example.com/upload",
            fields={"key": "test-key", "Content-Type": "image/jpeg"},
            file_id="test-file-id",
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        
        mock_storage_service = Mock()
        mock_get_storage_service.return_value = mock_storage_service
        mock_storage_service.generate_presigned_upload_url = AsyncMock(return_value=mock_presigned_data)
        
        result = await service.generate_presigned_upload_url(
            "test.jpg", "image/jpeg", "original"
        )
        
        assert result['upload_url'] == "https://example.com/upload"
        assert result['fields'] == {"key": "test-key", "Content-Type": "image/jpeg"}
        assert result['file_id'] == "test-file-id"
        assert 'expires_at' in result
        
        mock_storage_service.generate_presigned_upload_url.assert_called_once_with(
            "test.jpg", "image/jpeg", "original"
        )
    
    @pytest.mark.asyncio
    @patch('app.services.image_processing.get_storage_service')
    async def test_generate_presigned_upload_url_storage_error(self, mock_get_storage_service, service):
        """Test presigned URL generation with storage error."""
        from app.services.cloud_storage import StorageError
        from fastapi import HTTPException
        
        mock_storage_service = Mock()
        mock_get_storage_service.return_value = mock_storage_service
        mock_storage_service.generate_presigned_upload_url = AsyncMock(side_effect=StorageError("Upload failed"))
        
        with pytest.raises(HTTPException) as exc_info:
            await service.generate_presigned_upload_url("test.jpg", "image/jpeg", "original")
        
        assert exc_info.value.status_code == 500
        assert "Failed to generate upload URL" in str(exc_info.value.detail)