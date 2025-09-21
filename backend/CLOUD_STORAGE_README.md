# Cloud Storage Integration

This document describes the cloud storage integration for the Artisan Promotion Platform, which provides a unified interface for storing and managing images across multiple cloud storage providers.

## Overview

The cloud storage service supports multiple providers with a focus on cost-effective solutions that offer generous free tiers:

- **AWS S3**: Industry standard with 5GB free storage
- **Google Cloud Storage**: 5GB free storage per month
- **Cloudflare R2**: 10GB free storage with 1M operations/month

## Architecture

### Service Structure

```
app/services/cloud_storage.py
├── CloudStorageProvider (Abstract Base Class)
├── AWSS3Provider
├── GoogleCloudProvider  
├── CloudflareR2Provider
└── CloudStorageService (Unified Interface)
```

### Key Components

1. **Abstract Provider Interface**: Ensures consistent API across all providers
2. **Provider Implementations**: Specific implementations for each cloud service
3. **Unified Service**: Single interface for all storage operations
4. **Error Handling**: Comprehensive error handling and logging
5. **Security**: Secure credential management and presigned URLs

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Storage Provider Selection
STORAGE_PROVIDER=aws  # Options: aws, gcp, cloudflare

# AWS S3 Configuration
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_S3_BUCKET=your-bucket-name
AWS_REGION=us-east-1

# Google Cloud Storage Configuration
GCP_PROJECT_ID=your-project-id
GCP_BUCKET_NAME=your-bucket-name
GCP_CREDENTIALS_PATH=/path/to/credentials.json

# Cloudflare R2 Configuration
CLOUDFLARE_ACCOUNT_ID=your-account-id
CLOUDFLARE_ACCESS_KEY_ID=your-access-key
CLOUDFLARE_SECRET_ACCESS_KEY=your-secret-key
CLOUDFLARE_BUCKET_NAME=your-bucket-name
CLOUDFLARE_ENDPOINT_URL=https://your-account-id.r2.cloudflarestorage.com
```

### Provider Setup

#### AWS S3 Setup

1. Create an S3 bucket in AWS Console
2. Create IAM user with S3 permissions
3. Generate access keys
4. Configure CORS if needed for direct uploads

```json
{
    "CORSRules": [
        {
            "AllowedHeaders": ["*"],
            "AllowedMethods": ["GET", "POST", "PUT"],
            "AllowedOrigins": ["*"],
            "ExposeHeaders": ["ETag"]
        }
    ]
}
```

#### Google Cloud Storage Setup

1. Create a GCS bucket in Google Cloud Console
2. Create a service account with Storage Admin role
3. Download service account JSON key
4. Set `GCP_CREDENTIALS_PATH` to the JSON file path

#### Cloudflare R2 Setup

1. Create an R2 bucket in Cloudflare Dashboard
2. Generate R2 API tokens
3. Configure custom domain if needed
4. Set up CORS policy for direct uploads

## Usage

### Basic Operations

```python
from app.services.cloud_storage import get_storage_service

# Get service instance
storage_service = get_storage_service()

# Upload image
stored_file = await storage_service.upload_image(
    file_data=image_bytes,
    filename="product.jpg",
    content_type="image/jpeg",
    image_type="original"
)

# Upload multiple product images
uploaded_files = await storage_service.upload_product_images(
    product_id="product-123",
    images={"original": image_data, "compressed": compressed_data},
    filenames={"original": "product.jpg", "compressed": "product_compressed.jpg"},
    content_types={"original": "image/jpeg", "compressed": "image/jpeg"}
)

# Generate presigned upload URL for direct client uploads
presigned_data = await storage_service.generate_presigned_upload_url(
    filename="client_upload.jpg",
    content_type="image/jpeg",
    image_type="original",
    expires_in=3600
)

# Download file
file_data = await storage_service.download_file("images/original/product.jpg")

# Delete file
success = await storage_service.delete_file("images/original/product.jpg")

# List user images
images = await storage_service.list_user_images("user-123", limit=50)

# Get storage statistics
stats = await storage_service.get_storage_stats()
```

### Integration with Image Processing

The cloud storage service is integrated with the image processing service:

```python
from app.services.image_processing import image_service

# Process and upload image with cloud storage
result = await image_service.process_image(
    file=uploaded_file,
    platforms=["facebook", "instagram"],
    product_id="product-123"
)

# Result includes cloud URLs
print(result.original_url)        # Original image URL
print(result.compressed_url)      # Compressed image URL
print(result.thumbnail_urls)      # Thumbnail URLs by size
print(result.platform_optimized_urls)  # Platform-specific URLs
```

## File Organization

The service organizes files in a structured hierarchy:

```
bucket/
├── images/
│   ├── original/
│   ├── compressed/
│   ├── thumbnail_small/
│   ├── thumbnail_medium/
│   ├── thumbnail_large/
│   └── platform_[name]/
├── products/
│   └── [product-id]/
│       ├── original/
│       ├── compressed/
│       └── thumbnails/
└── users/
    └── [user-id]/
        └── uploads/
```

## Security Features

### Secure Uploads

- **Presigned URLs**: Direct client uploads without exposing credentials
- **Content Type Validation**: Ensures only allowed file types
- **Size Limits**: Configurable file size restrictions
- **Expiration**: Time-limited upload URLs

### Access Control

- **Private Buckets**: Files not publicly accessible by default
- **Presigned Download URLs**: Temporary access to private files
- **User Isolation**: Files organized by user/product for access control

### Credential Management

- **Environment Variables**: Secure credential storage
- **IAM Roles**: Use cloud provider IAM for fine-grained permissions
- **Token Refresh**: Automatic handling of expired tokens

## Error Handling

The service provides comprehensive error handling:

```python
from app.services.cloud_storage import StorageError

try:
    result = await storage_service.upload_image(file_data, filename, content_type)
except StorageError as e:
    logger.error(f"Storage operation failed: {e}")
    # Handle error appropriately
```

### Common Error Scenarios

- **Network Issues**: Automatic retry with exponential backoff
- **Authentication Failures**: Clear error messages for credential issues
- **Quota Exceeded**: Graceful handling of storage limits
- **File Not Found**: Proper 404 handling for missing files

## Monitoring and Analytics

### Storage Statistics

```python
stats = await storage_service.get_storage_stats()
# Returns:
# {
#     "total_files": 1500,
#     "total_size_bytes": 52428800,
#     "type_breakdown": {
#         "original": 500,
#         "compressed": 500,
#         "thumbnail_small": 250,
#         "thumbnail_medium": 250
#     }
# }
```

### Logging

The service logs all operations for monitoring:

- Upload/download operations
- Error conditions
- Performance metrics
- Security events

## Testing

### Unit Tests

Run the comprehensive test suite:

```bash
# Test cloud storage service
python -m pytest tests/test_cloud_storage.py -v

# Test image processing integration
python -m pytest tests/test_image_processing.py::TestImageProcessingCloudStorageIntegration -v

# Test API endpoints
python -m pytest tests/test_image_api.py::TestImageAPICloudStorageIntegration -v
```

### Demo Script

Run the demo to see functionality:

```bash
python demo_cloud_storage.py
```

## Performance Optimization

### Best Practices

1. **Parallel Uploads**: Upload multiple image variants concurrently
2. **Compression**: Optimize images before upload to reduce bandwidth
3. **CDN Integration**: Use cloud provider CDNs for faster delivery
4. **Caching**: Cache frequently accessed metadata
5. **Batch Operations**: Group multiple operations when possible

### Cost Optimization

1. **Free Tiers**: Leverage generous free tiers from providers
2. **Lifecycle Policies**: Automatically delete old files
3. **Storage Classes**: Use appropriate storage classes for different use cases
4. **Monitoring**: Track usage to avoid unexpected costs

## Migration and Backup

### Provider Migration

The unified interface makes it easy to migrate between providers:

1. Update `STORAGE_PROVIDER` environment variable
2. Configure new provider credentials
3. Run migration script to transfer existing files
4. Update DNS/CDN configuration if needed

### Backup Strategy

1. **Cross-Provider Backup**: Store copies in multiple providers
2. **Regular Snapshots**: Automated backup of critical data
3. **Disaster Recovery**: Documented recovery procedures
4. **Testing**: Regular backup restoration tests

## API Endpoints

The cloud storage functionality is exposed through REST API endpoints:

### Upload Endpoints

- `POST /images/upload` - Upload and process image
- `POST /images/presigned-upload` - Generate presigned upload URL

### Management Endpoints

- `GET /images/download/{storage_path}` - Generate presigned download URL
- `DELETE /images/{storage_path}` - Delete image
- `GET /images/user/images` - List user images
- `GET /images/storage/stats` - Get storage statistics

## Troubleshooting

### Common Issues

1. **Credentials Not Found**
   - Check environment variables
   - Verify credential file paths
   - Ensure IAM permissions

2. **Upload Failures**
   - Check file size limits
   - Verify content type restrictions
   - Check network connectivity

3. **Access Denied**
   - Verify bucket permissions
   - Check CORS configuration
   - Validate presigned URL expiration

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger('app.services.cloud_storage').setLevel(logging.DEBUG)
```

## Future Enhancements

### Planned Features

1. **Image Optimization**: Automatic format conversion and optimization
2. **Metadata Extraction**: EXIF data extraction and storage
3. **Duplicate Detection**: Prevent duplicate file uploads
4. **Batch Operations**: Bulk upload/delete operations
5. **Advanced Analytics**: Detailed usage analytics and reporting

### Integration Opportunities

1. **Content Delivery Network**: CDN integration for global distribution
2. **Image Processing Pipeline**: Advanced image processing workflows
3. **Machine Learning**: Automatic tagging and content analysis
4. **Backup Services**: Automated backup to multiple providers

## Support

For issues or questions:

1. Check the test suite for examples
2. Review the demo script for usage patterns
3. Check logs for error details
4. Consult cloud provider documentation for provider-specific issues

## License

This cloud storage integration is part of the Artisan Promotion Platform and follows the same licensing terms.