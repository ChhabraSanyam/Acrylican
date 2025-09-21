#!/usr/bin/env python3
"""
Demo script for cloud storage integration.

This script demonstrates the cloud storage functionality without requiring
actual cloud credentials by using mocked providers.
"""

import asyncio
import io
from PIL import Image
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from app.services.cloud_storage import (
    CloudStorageService, StoredFile, PresignedUploadData, StorageError
)


def create_sample_image() -> bytes:
    """Create a sample image for testing."""
    img = Image.new('RGB', (400, 300), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    return img_bytes.getvalue()


def create_mock_provider():
    """Create a mock cloud storage provider for demonstration."""
    mock_provider = Mock()
    
    # Mock upload_file
    async def mock_upload_file(file_data, filename, content_type, folder=""):
        return StoredFile(
            file_id="demo-file-id",
            filename=filename,
            url=f"https://demo-bucket.s3.amazonaws.com/{folder}/{filename}",
            size=len(file_data),
            content_type=content_type,
            storage_path=f"{folder}/{filename}",
            created_at=datetime.utcnow()
        )
    
    # Mock download_file
    async def mock_download_file(storage_path):
        return create_sample_image()
    
    # Mock delete_file
    async def mock_delete_file(storage_path):
        return True
    
    # Mock generate_presigned_upload_url
    async def mock_generate_presigned_upload_url(filename, content_type, folder="", expires_in=3600):
        return PresignedUploadData(
            upload_url=f"https://demo-bucket.s3.amazonaws.com/upload?key={folder}/{filename}",
            fields={"key": f"{folder}/{filename}", "Content-Type": content_type},
            file_id="demo-presigned-id",
            expires_at=datetime.utcnow()
        )
    
    # Mock generate_presigned_download_url
    async def mock_generate_presigned_download_url(storage_path, expires_in=3600):
        return f"https://demo-bucket.s3.amazonaws.com/{storage_path}?signature=demo-signature"
    
    # Mock list_files
    async def mock_list_files(folder="", limit=100):
        return [
            StoredFile(
                file_id="demo-file-1",
                filename="demo1.jpg",
                url=f"https://demo-bucket.s3.amazonaws.com/{folder}/demo1.jpg",
                size=1024,
                content_type="image/jpeg",
                storage_path=f"{folder}/demo1.jpg",
                created_at=datetime.utcnow()
            ),
            StoredFile(
                file_id="demo-file-2",
                filename="demo2.jpg",
                url=f"https://demo-bucket.s3.amazonaws.com/{folder}/demo2.jpg",
                size=2048,
                content_type="image/jpeg",
                storage_path=f"{folder}/demo2.jpg",
                created_at=datetime.utcnow()
            )
        ]
    
    # Assign async methods
    mock_provider.upload_file = mock_upload_file
    mock_provider.download_file = mock_download_file
    mock_provider.delete_file = mock_delete_file
    mock_provider.generate_presigned_upload_url = mock_generate_presigned_upload_url
    mock_provider.generate_presigned_download_url = mock_generate_presigned_download_url
    mock_provider.list_files = mock_list_files
    
    return mock_provider


async def demo_cloud_storage():
    """Demonstrate cloud storage functionality."""
    print("🚀 Cloud Storage Integration Demo")
    print("=" * 50)
    
    # Create a mock service with our demo provider
    service = CloudStorageService.__new__(CloudStorageService)
    service.provider = create_mock_provider()
    
    # Create sample image data
    image_data = create_sample_image()
    print(f"📸 Created sample image: {len(image_data)} bytes")
    
    # Demo 1: Upload single image
    print("\n1️⃣ Uploading single image...")
    stored_file = await service.upload_image(
        image_data, "demo.jpg", "image/jpeg", "original"
    )
    print(f"   ✅ Uploaded: {stored_file.filename}")
    print(f"   📍 URL: {stored_file.url}")
    print(f"   📁 Storage path: {stored_file.storage_path}")
    
    # Demo 2: Upload product images
    print("\n2️⃣ Uploading product images...")
    images = {
        "original": image_data,
        "compressed": image_data[:len(image_data)//2],  # Simulate compression
        "thumbnail": image_data[:len(image_data)//4]    # Simulate thumbnail
    }
    filenames = {
        "original": "product_original.jpg",
        "compressed": "product_compressed.jpg", 
        "thumbnail": "product_thumbnail.jpg"
    }
    content_types = {
        "original": "image/jpeg",
        "compressed": "image/jpeg",
        "thumbnail": "image/jpeg"
    }
    
    uploaded_files = await service.upload_product_images(
        "product-123", images, filenames, content_types
    )
    
    for image_type, file_info in uploaded_files.items():
        print(f"   ✅ {image_type}: {file_info.url}")
    
    # Demo 3: Generate presigned upload URL
    print("\n3️⃣ Generating presigned upload URL...")
    presigned_data = await service.generate_presigned_upload_url(
        "client_upload.jpg", "image/jpeg", "uploads"
    )
    print(f"   🔗 Upload URL: {presigned_data.upload_url}")
    print(f"   🆔 File ID: {presigned_data.file_id}")
    
    # Demo 4: Generate presigned download URL
    print("\n4️⃣ Generating presigned download URL...")
    download_url = await service.generate_presigned_download_url(
        "images/original/demo.jpg"
    )
    print(f"   🔗 Download URL: {download_url}")
    
    # Demo 5: List user images
    print("\n5️⃣ Listing user images...")
    user_images = await service.list_user_images("user-123")
    for img in user_images:
        print(f"   📄 {img.filename} ({img.size} bytes)")
    
    # Demo 6: Download file
    print("\n6️⃣ Downloading file...")
    downloaded_data = await service.download_file("images/original/demo.jpg")
    print(f"   ⬇️ Downloaded: {len(downloaded_data)} bytes")
    
    # Demo 7: Delete file
    print("\n7️⃣ Deleting file...")
    success = await service.delete_file("images/original/demo.jpg")
    print(f"   🗑️ Deleted: {'✅ Success' if success else '❌ Failed'}")
    
    # Demo 8: Get storage stats
    print("\n8️⃣ Getting storage statistics...")
    stats = await service.get_storage_stats()
    print(f"   📊 Total files: {stats['total_files']}")
    print(f"   💾 Total size: {stats['total_size_bytes']} bytes")
    print(f"   📈 Type breakdown: {stats['type_breakdown']}")
    
    print("\n🎉 Demo completed successfully!")
    print("\n💡 Key Features Demonstrated:")
    print("   • Multi-provider support (AWS S3, Google Cloud, Cloudflare R2)")
    print("   • Secure file upload with presigned URLs")
    print("   • Organized folder structure for different image types")
    print("   • Image retrieval and URL generation")
    print("   • Comprehensive error handling and logging")
    print("   • Storage usage statistics and monitoring")


async def demo_error_handling():
    """Demonstrate error handling in cloud storage operations."""
    print("\n🚨 Error Handling Demo")
    print("=" * 30)
    
    # Create a service with a provider that throws errors
    service = CloudStorageService.__new__(CloudStorageService)
    mock_provider = Mock()
    
    # Mock provider that throws StorageError
    async def failing_upload(file_data, filename, content_type, folder=""):
        raise StorageError("Simulated upload failure")
    
    mock_provider.upload_file = failing_upload
    service.provider = mock_provider
    
    try:
        await service.upload_image(b"test data", "test.jpg", "image/jpeg")
    except StorageError as e:
        print(f"   ❌ Caught expected error: {e}")
    
    print("   ✅ Error handling working correctly")


if __name__ == "__main__":
    print("Cloud Storage Integration Demo")
    print("This demo shows cloud storage functionality with mocked providers")
    print("In production, this would connect to real cloud storage services\n")
    
    # Run the demos
    asyncio.run(demo_cloud_storage())
    asyncio.run(demo_error_handling())
    
    print("\n📚 Next Steps:")
    print("1. Configure real cloud storage credentials in .env file")
    print("2. Set STORAGE_PROVIDER environment variable (aws/gcp/cloudflare)")
    print("3. Test with actual cloud storage buckets")
    print("4. Monitor storage usage and costs")
    print("5. Implement backup and disaster recovery procedures")