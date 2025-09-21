#!/usr/bin/env python3
"""
Demo script for image processing functionality.

This script demonstrates the image processing service capabilities
without requiring a full API setup.
"""

import asyncio
import io
import time
from PIL import Image
from fastapi import UploadFile
from unittest.mock import Mock

from app.services.image_processing import image_service, ImageValidationError


async def create_demo_image() -> UploadFile:
    """Create a demo image for testing."""
    # Create a colorful gradient image
    img = Image.new('RGB', (800, 600))
    pixels = []
    
    for y in range(600):
        for x in range(800):
            # Create a colorful gradient
            r = int((x / 800) * 255)
            g = int((y / 600) * 255)
            b = int(((x + y) / 1400) * 255)
            pixels.append((r, g, b))
    
    img.putdata(pixels)
    
    # Convert to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG', quality=90)
    img_bytes.seek(0)
    
    # Create mock UploadFile
    mock_file = Mock(spec=UploadFile)
    mock_file.filename = "demo_gradient.jpg"
    mock_file.size = len(img_bytes.getvalue())
    
    async def mock_read():
        return img_bytes.getvalue()
    
    async def mock_seek(pos):
        return img_bytes.seek(pos)
    
    mock_file.read = mock_read
    mock_file.seek = mock_seek
    
    return mock_file


async def demo_image_validation():
    """Demonstrate image validation."""
    print("🔍 Testing Image Validation...")
    
    # Test with valid image
    valid_image = await create_demo_image()
    try:
        await image_service.validate_image(valid_image)
        print("✅ Valid image passed validation")
    except ImageValidationError as e:
        print(f"❌ Valid image failed validation: {e}")
    
    # Test with invalid file
    invalid_file = Mock(spec=UploadFile)
    invalid_file.filename = "test.txt"
    invalid_file.size = 100
    
    async def mock_invalid_read():
        return b"not an image"
    
    async def mock_invalid_seek(pos):
        return None
    
    invalid_file.read = mock_invalid_read
    invalid_file.seek = mock_invalid_seek
    
    try:
        await image_service.validate_image(invalid_file)
        print("❌ Invalid file passed validation (should have failed)")
    except ImageValidationError as e:
        print(f"✅ Invalid file correctly rejected: {e}")


def demo_image_compression():
    """Demonstrate image compression."""
    print("\n🗜️  Testing Image Compression...")
    
    # Create test image
    img = Image.new('RGB', (1200, 900), color='blue')
    
    # Test different quality levels
    high_quality = image_service.compress_image(img, quality=95)
    medium_quality = image_service.compress_image(img, quality=75)
    low_quality = image_service.compress_image(img, quality=50)
    
    print(f"Original size: 1200x900")
    print(f"High quality (95%): {len(high_quality):,} bytes")
    print(f"Medium quality (75%): {len(medium_quality):,} bytes")
    print(f"Low quality (50%): {len(low_quality):,} bytes")
    
    # Test with resizing
    resized = image_service.compress_image(img, quality=85, max_width=800, max_height=600)
    resized_img = Image.open(io.BytesIO(resized))
    print(f"Resized (800x600 max): {resized_img.size}, {len(resized):,} bytes")


def demo_thumbnail_generation():
    """Demonstrate thumbnail generation."""
    print("\n🖼️  Testing Thumbnail Generation...")
    
    # Create test image
    img = Image.new('RGB', (1000, 750), color='green')
    
    # Generate different thumbnail sizes
    small_thumb = image_service.generate_thumbnail(img, (150, 150))
    medium_thumb = image_service.generate_thumbnail(img, (300, 300))
    large_thumb = image_service.generate_thumbnail(img, (600, 600))
    
    # Check actual sizes
    small_img = Image.open(io.BytesIO(small_thumb))
    medium_img = Image.open(io.BytesIO(medium_thumb))
    large_img = Image.open(io.BytesIO(large_thumb))
    
    print(f"Original: {img.size}")
    print(f"Small thumbnail: {small_img.size}, {len(small_thumb):,} bytes")
    print(f"Medium thumbnail: {medium_img.size}, {len(medium_thumb):,} bytes")
    print(f"Large thumbnail: {large_img.size}, {len(large_thumb):,} bytes")


def demo_platform_optimization():
    """Demonstrate platform-specific optimization."""
    print("\n🌐 Testing Platform Optimization...")
    
    # Create test image
    img = Image.new('RGB', (2000, 1500), color='red')
    
    # Test optimization for different platforms
    platforms = ['facebook', 'instagram', 'pinterest', 'etsy']
    
    print(f"Original: {img.size}")
    
    for platform in platforms:
        try:
            optimized = image_service.optimize_for_platform(img, platform)
            optimized_img = Image.open(io.BytesIO(optimized))
            requirements = image_service.get_platform_requirements(platform)
            
            print(f"{platform.capitalize()}: {optimized_img.size}, {len(optimized):,} bytes "
                  f"(max: {requirements['max_width']}x{requirements['max_height']}, "
                  f"quality: {requirements['quality']}%)")
        except Exception as e:
            print(f"❌ {platform}: {e}")


async def demo_full_processing():
    """Demonstrate full image processing pipeline."""
    print("\n⚙️  Testing Full Processing Pipeline...")
    
    # Create demo image
    demo_file = await create_demo_image()
    platforms = ['facebook', 'instagram', 'etsy']
    
    start_time = time.time()
    
    try:
        result = await image_service.process_image(demo_file, platforms)
        processing_time = time.time() - start_time
        
        print(f"✅ Processing completed in {processing_time:.2f}s")
        print(f"Image ID: {result.id}")
        print(f"Original filename: {result.original_filename}")
        print(f"File size: {result.file_size:,} bytes")
        print(f"Dimensions: {result.dimensions['width']}x{result.dimensions['height']}")
        print(f"Format: {result.format}")
        print(f"Compressed size: {len(result.compressed_data):,} bytes")
        print(f"Thumbnails generated: {len(result.thumbnail_data)}")
        print(f"Platform optimizations: {len(result.platform_optimized)}")
        
        # Show thumbnail sizes
        for size_name, thumb_data in result.thumbnail_data.items():
            thumb_img = Image.open(io.BytesIO(thumb_data))
            print(f"  {size_name}: {thumb_img.size}, {len(thumb_data):,} bytes")
        
        # Show platform optimizations
        for platform, opt_data in result.platform_optimized.items():
            opt_img = Image.open(io.BytesIO(opt_data))
            print(f"  {platform}: {opt_img.size}, {len(opt_data):,} bytes")
            
    except Exception as e:
        print(f"❌ Processing failed: {e}")


def demo_platform_info():
    """Demonstrate platform information retrieval."""
    print("\n📋 Platform Information...")
    
    platforms = image_service.get_supported_platforms()
    print(f"Supported platforms ({len(platforms)}):")
    
    for platform in platforms:
        requirements = image_service.get_platform_requirements(platform)
        print(f"  {platform}: {requirements['max_width']}x{requirements['max_height']}, "
              f"{requirements['quality']}% quality, {requirements['format']}")


async def main():
    """Run all demos."""
    print("🎨 Image Processing Service Demo")
    print("=" * 50)
    
    await demo_image_validation()
    demo_image_compression()
    demo_thumbnail_generation()
    demo_platform_optimization()
    await demo_full_processing()
    demo_platform_info()
    
    print("\n✨ Demo completed!")


if __name__ == "__main__":
    asyncio.run(main())