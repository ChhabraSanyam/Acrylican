"""
Image processing service for the Artisan Promotion Platform.

This service handles image compression, thumbnail generation, format validation,
and optimization for different platform requirements.
"""

import io
import uuid
from typing import List, Dict, Tuple, Optional, BinaryIO
from PIL import Image, ImageOps
from fastapi import UploadFile, HTTPException
from pydantic import BaseModel
import logging

from .cloud_storage import get_storage_service, StorageError

logger = logging.getLogger(__name__)

# Supported image formats
SUPPORTED_FORMATS = {'JPEG', 'PNG', 'WEBP'}
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}

# Platform-specific image requirements
PLATFORM_REQUIREMENTS = {
    'facebook': {
        'max_width': 2048,
        'max_height': 2048,
        'quality': 85,
        'format': 'JPEG'
    },
    'instagram': {
        'max_width': 1080,
        'max_height': 1080,
        'quality': 85,
        'format': 'JPEG'
    },
    'facebook_marketplace': {
        'max_width': 1200,
        'max_height': 1200,
        'quality': 80,
        'format': 'JPEG'
    },
    'etsy': {
        'max_width': 2000,
        'max_height': 2000,
        'quality': 90,
        'format': 'JPEG'
    },
    'pinterest': {
        'max_width': 1000,
        'max_height': 1500,
        'quality': 85,
        'format': 'JPEG'
    },
    'shopify': {
        'max_width': 2048,
        'max_height': 2048,
        'quality': 85,
        'format': 'JPEG'
    },
    'meesho': {
        'max_width': 1000,
        'max_height': 1000,
        'quality': 80,
        'format': 'JPEG'
    },
    'snapdeal': {
        'max_width': 1000,
        'max_height': 1000,
        'quality': 80,
        'format': 'JPEG'
    },
    'indiamart': {
        'max_width': 800,
        'max_height': 800,
        'quality': 75,
        'format': 'JPEG'
    }
}

# Thumbnail configurations
THUMBNAIL_SIZES = {
    'small': (150, 150),
    'medium': (300, 300),
    'large': (600, 600)
}


class ProcessedImage(BaseModel):
    """Schema for processed image data."""
    id: str
    original_filename: str
    file_size: int
    dimensions: Dict[str, int]
    format: str
    original_url: str
    compressed_url: str
    thumbnail_urls: Dict[str, str]
    platform_optimized_urls: Dict[str, str]
    storage_paths: Dict[str, str]


class ImageValidationError(Exception):
    """Custom exception for image validation errors."""
    pass


class ImageProcessingService:
    """Service for handling image processing operations."""
    
    def __init__(self):
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.default_quality = 85
        self.thumbnail_quality = 80
    
    async def validate_image(self, file: UploadFile) -> None:
        """
        Validate uploaded image file.
        
        Args:
            file: The uploaded file to validate
            
        Raises:
            ImageValidationError: If validation fails
        """
        # Check file size
        if file.size and file.size > self.max_file_size:
            raise ImageValidationError(f"File size {file.size} exceeds maximum allowed size of {self.max_file_size} bytes")
        
        # Check file extension
        if file.filename:
            extension = '.' + file.filename.split('.')[-1].lower()
            if extension not in ALLOWED_EXTENSIONS:
                raise ImageValidationError(f"File extension {extension} not supported. Allowed: {ALLOWED_EXTENSIONS}")
        
        # Validate image format by trying to open it
        try:
            file_content = await file.read()
            await file.seek(0)  # Reset file pointer
            
            with Image.open(io.BytesIO(file_content)) as img:
                if img.format not in SUPPORTED_FORMATS:
                    raise ImageValidationError(f"Image format {img.format} not supported. Allowed: {SUPPORTED_FORMATS}")
                
                # Check image dimensions (minimum size)
                if img.width < 100 or img.height < 100:
                    raise ImageValidationError("Image dimensions too small. Minimum size is 100x100 pixels")
                
                # Check for corrupted image
                img.verify()
                
        except Exception as e:
            if isinstance(e, ImageValidationError):
                raise
            raise ImageValidationError(f"Invalid image file: {str(e)}")
    
    def compress_image(self, image: Image.Image, quality: int = None, max_width: int = None, max_height: int = None) -> bytes:
        """
        Compress image with specified quality and dimensions.
        
        Args:
            image: PIL Image object
            quality: JPEG quality (1-100)
            max_width: Maximum width in pixels
            max_height: Maximum height in pixels
            
        Returns:
            Compressed image as bytes
        """
        if quality is None:
            quality = self.default_quality
        
        # Create a copy to avoid modifying original
        img_copy = image.copy()
        
        # Resize if dimensions specified
        if max_width or max_height:
            img_copy = self._resize_image(img_copy, max_width, max_height)
        
        # Convert to RGB if necessary (for JPEG)
        if img_copy.mode in ('RGBA', 'LA', 'P'):
            # Create white background for transparency
            background = Image.new('RGB', img_copy.size, (255, 255, 255))
            if img_copy.mode == 'P':
                img_copy = img_copy.convert('RGBA')
            background.paste(img_copy, mask=img_copy.split()[-1] if img_copy.mode in ('RGBA', 'LA') else None)
            img_copy = background
        
        # Compress image
        output = io.BytesIO()
        img_copy.save(output, format='JPEG', quality=quality, optimize=True)
        return output.getvalue()
    
    def generate_thumbnail(self, image: Image.Image, size: Tuple[int, int], quality: int = None) -> bytes:
        """
        Generate thumbnail from image.
        
        Args:
            image: PIL Image object
            size: Tuple of (width, height) for thumbnail
            quality: JPEG quality for thumbnail
            
        Returns:
            Thumbnail image as bytes
        """
        if quality is None:
            quality = self.thumbnail_quality
        
        # Create thumbnail using PIL's thumbnail method (maintains aspect ratio)
        img_copy = image.copy()
        img_copy.thumbnail(size, Image.Resampling.LANCZOS)
        
        # Convert to RGB if necessary
        if img_copy.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img_copy.size, (255, 255, 255))
            if img_copy.mode == 'P':
                img_copy = img_copy.convert('RGBA')
            background.paste(img_copy, mask=img_copy.split()[-1] if img_copy.mode in ('RGBA', 'LA') else None)
            img_copy = background
        
        output = io.BytesIO()
        img_copy.save(output, format='JPEG', quality=quality, optimize=True)
        return output.getvalue()
    
    def optimize_for_platform(self, image: Image.Image, platform: str) -> bytes:
        """
        Optimize image for specific platform requirements.
        
        Args:
            image: PIL Image object
            platform: Platform name (e.g., 'facebook', 'instagram')
            
        Returns:
            Optimized image as bytes
            
        Raises:
            ValueError: If platform is not supported
        """
        if platform not in PLATFORM_REQUIREMENTS:
            raise ValueError(f"Platform {platform} not supported. Available: {list(PLATFORM_REQUIREMENTS.keys())}")
        
        requirements = PLATFORM_REQUIREMENTS[platform]
        
        return self.compress_image(
            image,
            quality=requirements['quality'],
            max_width=requirements['max_width'],
            max_height=requirements['max_height']
        )
    
    async def process_image(self, file: UploadFile, platforms: List[str] = None, product_id: str = None) -> ProcessedImage:
        """
        Process uploaded image: validate, compress, generate thumbnails, optimize for platforms, and upload to cloud storage.
        
        Args:
            file: Uploaded image file
            platforms: List of platforms to optimize for
            product_id: Optional product ID for organizing files
            
        Returns:
            ProcessedImage object with all processed variants and cloud URLs
            
        Raises:
            ImageValidationError: If image validation fails
            HTTPException: If processing fails
        """
        try:
            # Validate image
            await self.validate_image(file)
            
            # Read file content
            file_content = await file.read()
            
            # Open image
            with Image.open(io.BytesIO(file_content)) as img:
                # Apply EXIF orientation
                img = ImageOps.exif_transpose(img)
                
                # Generate unique ID
                image_id = str(uuid.uuid4())
                
                # Get image info
                original_size = len(file_content)
                dimensions = {'width': img.width, 'height': img.height}
                original_filename = file.filename or f"image_{image_id}.jpg"
                
                # Prepare data for cloud upload
                images_to_upload = {}
                filenames = {}
                content_types = {}
                
                # Original image
                images_to_upload['original'] = file_content
                filenames['original'] = original_filename
                content_types['original'] = file.content_type or 'image/jpeg'
                
                # Compressed image
                compressed_data = self.compress_image(img)
                images_to_upload['compressed'] = compressed_data
                filenames['compressed'] = f"compressed_{original_filename}"
                content_types['compressed'] = 'image/jpeg'
                
                # Generate thumbnails
                for size_name, size_dims in THUMBNAIL_SIZES.items():
                    thumbnail_data = self.generate_thumbnail(img, size_dims)
                    images_to_upload[f'thumbnail_{size_name}'] = thumbnail_data
                    filenames[f'thumbnail_{size_name}'] = f"thumb_{size_name}_{original_filename}"
                    content_types[f'thumbnail_{size_name}'] = 'image/jpeg'
                
                # Optimize for platforms
                if platforms:
                    for platform in platforms:
                        try:
                            platform_data = self.optimize_for_platform(img, platform)
                            images_to_upload[f'platform_{platform}'] = platform_data
                            filenames[f'platform_{platform}'] = f"{platform}_{original_filename}"
                            content_types[f'platform_{platform}'] = 'image/jpeg'
                        except ValueError as e:
                            logger.warning(f"Platform optimization failed for {platform}: {e}")
                
                # Upload all images to cloud storage
                storage_service = get_storage_service()
                if product_id:
                    uploaded_files = await storage_service.upload_product_images(
                        product_id, images_to_upload, filenames, content_types
                    )
                else:
                    # Upload to general images folder
                    uploaded_files = {}
                    for image_type, file_data in images_to_upload.items():
                        try:
                            stored_file = await storage_service.upload_image(
                                file_data, filenames[image_type], content_types[image_type], image_type
                            )
                            uploaded_files[image_type] = stored_file
                        except StorageError as e:
                            logger.error(f"Failed to upload {image_type}: {e}")
                
                # Extract URLs and storage paths
                original_url = uploaded_files.get('original', {}).url if 'original' in uploaded_files else ""
                compressed_url = uploaded_files.get('compressed', {}).url if 'compressed' in uploaded_files else ""
                
                thumbnail_urls = {}
                platform_optimized_urls = {}
                storage_paths = {}
                
                for image_type, stored_file in uploaded_files.items():
                    storage_paths[image_type] = stored_file.storage_path
                    
                    if image_type.startswith('thumbnail_'):
                        size_name = image_type.replace('thumbnail_', '')
                        thumbnail_urls[size_name] = stored_file.url
                    elif image_type.startswith('platform_'):
                        platform_name = image_type.replace('platform_', '')
                        platform_optimized_urls[platform_name] = stored_file.url
                
                return ProcessedImage(
                    id=image_id,
                    original_filename=original_filename,
                    file_size=original_size,
                    dimensions=dimensions,
                    format=img.format or "JPEG",
                    original_url=original_url,
                    compressed_url=compressed_url,
                    thumbnail_urls=thumbnail_urls,
                    platform_optimized_urls=platform_optimized_urls,
                    storage_paths=storage_paths
                )
                
        except ImageValidationError:
            raise
        except StorageError as e:
            logger.error(f"Cloud storage operation failed: {e}")
            raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")
        except Exception as e:
            logger.error(f"Image processing failed: {e}")
            raise HTTPException(status_code=500, detail=f"Image processing failed: {str(e)}")
    
    def _resize_image(self, image: Image.Image, max_width: int = None, max_height: int = None) -> Image.Image:
        """
        Resize image while maintaining aspect ratio.
        
        Args:
            image: PIL Image object
            max_width: Maximum width in pixels
            max_height: Maximum height in pixels
            
        Returns:
            Resized PIL Image object
        """
        width, height = image.size
        
        # Calculate new dimensions
        if max_width and max_height:
            # Fit within both constraints
            ratio = min(max_width / width, max_height / height)
        elif max_width:
            ratio = max_width / width
        elif max_height:
            ratio = max_height / height
        else:
            return image
        
        # Only resize if image is larger than constraints
        if ratio < 1:
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            return image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        return image
    
    def get_platform_requirements(self, platform: str) -> Dict:
        """
        Get platform-specific image requirements.
        
        Args:
            platform: Platform name
            
        Returns:
            Dictionary with platform requirements
            
        Raises:
            ValueError: If platform is not supported
        """
        if platform not in PLATFORM_REQUIREMENTS:
            raise ValueError(f"Platform {platform} not supported. Available: {list(PLATFORM_REQUIREMENTS.keys())}")
        
        return PLATFORM_REQUIREMENTS[platform].copy()
    
    def get_supported_platforms(self) -> List[str]:
        """
        Get list of supported platforms.
        
        Returns:
            List of supported platform names
        """
        return list(PLATFORM_REQUIREMENTS.keys())
    
    async def delete_processed_image(self, storage_paths: Dict[str, str]) -> Dict[str, bool]:
        """
        Delete all variants of a processed image from cloud storage.
        
        Args:
            storage_paths: Dictionary of image_type -> storage_path
            
        Returns:
            Dictionary of storage_path -> success_status
        """
        results = {}
        
        storage_service = get_storage_service()
        for image_type, storage_path in storage_paths.items():
            try:
                success = await storage_service.delete_file(storage_path)
                results[storage_path] = success
                if not success:
                    logger.warning(f"Failed to delete {image_type} at {storage_path}")
            except StorageError as e:
                logger.error(f"Error deleting {image_type} at {storage_path}: {e}")
                results[storage_path] = False
        
        return results
    
    async def generate_presigned_upload_url(self, filename: str, content_type: str, 
                                          image_type: str = "original") -> dict:
        """
        Generate presigned URL for direct client upload.
        
        Args:
            filename: Original filename
            content_type: MIME type
            image_type: Type of image (original, compressed, etc.)
            
        Returns:
            Dictionary with presigned upload data
        """
        try:
            storage_service = get_storage_service()
            presigned_data = await storage_service.generate_presigned_upload_url(
                filename, content_type, image_type
            )
            
            return {
                'upload_url': presigned_data.upload_url,
                'fields': presigned_data.fields,
                'file_id': presigned_data.file_id,
                'expires_at': presigned_data.expires_at.isoformat()
            }
            
        except StorageError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to generate upload URL: {str(e)}")


# Global instance
image_service = ImageProcessingService()