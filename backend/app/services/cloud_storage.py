"""
Cloud storage service for the Artisan Promotion Platform.

This service provides cloud storage operations using Cloudflare R2
with S3-compatible API for cost-effective and reliable file storage.
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from botocore.config import Config
from pydantic import BaseModel

from ..config import settings

logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Custom exception for storage operations."""
    pass


class StoredFile(BaseModel):
    """Schema for stored file information."""
    file_id: str
    filename: str
    url: str
    size: int
    content_type: str
    storage_path: str
    created_at: datetime


class PresignedUploadData(BaseModel):
    """Schema for presigned upload information."""
    upload_url: str
    fields: Dict[str, str]
    file_id: str
    expires_at: datetime





class CloudflareR2Provider:
    """Cloudflare R2 storage provider implementation (S3-compatible)."""
    
    def __init__(self):
        try:
            self.client = boto3.client(
                's3',
                aws_access_key_id=settings.cloudflare_access_key_id,
                aws_secret_access_key=settings.cloudflare_secret_access_key,
                endpoint_url=settings.cloudflare_endpoint_url,
                config=Config(signature_version='s3v4')
            )
            self.bucket = settings.cloudflare_bucket_name
            
            # Test connection
            self.client.head_bucket(Bucket=self.bucket)
            logger.info("Cloudflare R2 provider initialized successfully")
            
        except NoCredentialsError:
            raise StorageError("Cloudflare R2 credentials not found")
        except ClientError as e:
            raise StorageError(f"Cloudflare R2 initialization failed: {e}")
    
    def _generate_storage_path(self, filename: str, folder: str = "") -> str:
        """Generate storage path with folder structure."""
        file_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().strftime("%Y/%m/%d")
        
        if folder:
            return f"{folder}/{timestamp}/{file_id}_{filename}"
        return f"{timestamp}/{file_id}_{filename}"
    
    async def upload_file(self, file_data: bytes, filename: str, content_type: str, 
                         folder: str = "") -> StoredFile:
        """Upload file to Cloudflare R2."""
        try:
            storage_path = self._generate_storage_path(filename, folder)
            file_id = storage_path.split('/')[-1].split('_')[0]
            
            # Upload file
            self.client.put_object(
                Bucket=self.bucket,
                Key=storage_path,
                Body=file_data,
                ContentType=content_type,
                Metadata={
                    'original_filename': filename,
                    'file_id': file_id,
                    'uploaded_at': datetime.utcnow().isoformat()
                }
            )
            
            # Generate public URL using custom domain if available, otherwise endpoint URL
            if settings.cloudflare_public_url:
                url = f"{settings.cloudflare_public_url}/{storage_path}"
            else:
                url = f"{settings.cloudflare_endpoint_url}/{self.bucket}/{storage_path}"
            
            return StoredFile(
                file_id=file_id,
                filename=filename,
                url=url,
                size=len(file_data),
                content_type=content_type,
                storage_path=storage_path,
                created_at=datetime.utcnow()
            )
            
        except ClientError as e:
            logger.error(f"Cloudflare R2 upload failed: {e}")
            raise StorageError(f"Upload failed: {e}")
    
    async def download_file(self, storage_path: str) -> bytes:
        """Download file from Cloudflare R2."""
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=storage_path)
            return response['Body'].read()
        except ClientError as e:
            logger.error(f"Cloudflare R2 download failed: {e}")
            raise StorageError(f"Download failed: {e}")
    
    async def delete_file(self, storage_path: str) -> bool:
        """Delete file from Cloudflare R2."""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=storage_path)
            return True
        except ClientError as e:
            logger.error(f"Cloudflare R2 delete failed: {e}")
            return False
    
    async def generate_presigned_upload_url(self, filename: str, content_type: str,
                                          folder: str = "", expires_in: int = 3600) -> PresignedUploadData:
        """Generate presigned URL for Cloudflare R2 upload."""
        try:
            storage_path = self._generate_storage_path(filename, folder)
            file_id = storage_path.split('/')[-1].split('_')[0]
            
            # Generate presigned POST
            response = self.client.generate_presigned_post(
                Bucket=self.bucket,
                Key=storage_path,
                Fields={
                    'Content-Type': content_type,
                    'x-amz-meta-original_filename': filename,
                    'x-amz-meta-file_id': file_id
                },
                Conditions=[
                    {'Content-Type': content_type},
                    ['content-length-range', 1, settings.max_file_size]
                ],
                ExpiresIn=expires_in
            )
            
            return PresignedUploadData(
                upload_url=response['url'],
                fields=response['fields'],
                file_id=file_id,
                expires_at=datetime.utcnow() + timedelta(seconds=expires_in)
            )
            
        except ClientError as e:
            logger.error(f"Cloudflare R2 presigned URL generation failed: {e}")
            raise StorageError(f"Presigned URL generation failed: {e}")
    
    async def generate_presigned_download_url(self, storage_path: str, 
                                            expires_in: int = 3600) -> str:
        """Generate presigned URL for Cloudflare R2 download."""
        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': storage_path},
                ExpiresIn=expires_in
            )
            return url
        except ClientError as e:
            logger.error(f"Cloudflare R2 presigned download URL generation failed: {e}")
            raise StorageError(f"Presigned download URL generation failed: {e}")
    
    async def list_files(self, folder: str = "", limit: int = 100) -> List[StoredFile]:
        """List files in Cloudflare R2 bucket."""
        try:
            kwargs = {'Bucket': self.bucket, 'MaxKeys': limit}
            if folder:
                kwargs['Prefix'] = folder + '/'
            
            response = self.client.list_objects_v2(**kwargs)
            files = []
            
            for obj in response.get('Contents', []):
                # Get metadata
                head_response = self.client.head_object(Bucket=self.bucket, Key=obj['Key'])
                metadata = head_response.get('Metadata', {})
                
                # Generate public URL using custom domain if available
                if settings.cloudflare_public_url:
                    file_url = f"{settings.cloudflare_public_url}/{obj['Key']}"
                else:
                    file_url = f"{settings.cloudflare_endpoint_url}/{self.bucket}/{obj['Key']}"
                
                files.append(StoredFile(
                    file_id=metadata.get('file_id', obj['Key'].split('/')[-1].split('_')[0]),
                    filename=metadata.get('original_filename', obj['Key'].split('/')[-1]),
                    url=file_url,
                    size=obj['Size'],
                    content_type=head_response.get('ContentType', 'application/octet-stream'),
                    storage_path=obj['Key'],
                    created_at=obj['LastModified']
                ))
            
            return files
            
        except ClientError as e:
            logger.error(f"Cloudflare R2 list files failed: {e}")
            raise StorageError(f"List files failed: {e}")


class CloudStorageService:
    """Cloud storage service using Cloudflare R2 with S3-compatible API."""
    
    def __init__(self):
        self.provider = CloudflareR2Provider()
    
    async def upload_image(self, file_data: bytes, filename: str, content_type: str,
                          image_type: str = "original") -> StoredFile:
        """
        Upload image file to cloud storage.
        
        Args:
            file_data: Image file data as bytes
            filename: Original filename
            content_type: MIME type of the file
            image_type: Type of image (original, compressed, thumbnail, platform_optimized)
            
        Returns:
            StoredFile object with storage information
        """
        folder = f"images/{image_type}"
        return await self.provider.upload_file(file_data, filename, content_type, folder)
    
    async def upload_product_images(self, product_id: str, images: Dict[str, bytes],
                                   filenames: Dict[str, str], content_types: Dict[str, str]) -> Dict[str, StoredFile]:
        """
        Upload multiple product images (original, compressed, thumbnails, etc.).
        
        Args:
            product_id: Product ID for organizing files
            images: Dictionary of image_type -> image_data
            filenames: Dictionary of image_type -> filename
            content_types: Dictionary of image_type -> content_type
            
        Returns:
            Dictionary of image_type -> StoredFile
        """
        results = {}
        
        for image_type, file_data in images.items():
            folder = f"products/{product_id}/{image_type}"
            filename = filenames.get(image_type, f"{image_type}.jpg")
            content_type = content_types.get(image_type, "image/jpeg")
            
            try:
                stored_file = await self.provider.upload_file(file_data, filename, content_type, folder)
                results[image_type] = stored_file
            except StorageError as e:
                logger.error(f"Failed to upload {image_type} for product {product_id}: {e}")
                # Continue with other uploads even if one fails
        
        return results
    
    async def download_file(self, storage_path: str) -> bytes:
        """Download file from storage."""
        return await self.provider.download_file(storage_path)
    
    async def delete_file(self, storage_path: str) -> bool:
        """Delete file from storage."""
        return await self.provider.delete_file(storage_path)
    
    async def delete_product_images(self, product_id: str) -> Dict[str, bool]:
        """
        Delete all images for a product.
        
        Args:
            product_id: Product ID
            
        Returns:
            Dictionary of storage_path -> success_status
        """
        results = {}
        
        try:
            # List all files for the product
            files = await self.provider.list_files(f"products/{product_id}")
            
            for file_info in files:
                success = await self.provider.delete_file(file_info.storage_path)
                results[file_info.storage_path] = success
                
        except StorageError as e:
            logger.error(f"Failed to delete images for product {product_id}: {e}")
        
        return results
    
    async def generate_presigned_upload_url(self, filename: str, content_type: str,
                                          image_type: str = "original", expires_in: int = 3600) -> PresignedUploadData:
        """Generate presigned URL for direct client upload."""
        folder = f"images/{image_type}"
        return await self.provider.generate_presigned_upload_url(filename, content_type, folder, expires_in)
    
    async def generate_presigned_download_url(self, storage_path: str, 
                                            expires_in: int = 3600) -> str:
        """Generate presigned URL for secure download."""
        return await self.provider.generate_presigned_download_url(storage_path, expires_in)
    
    async def list_user_images(self, user_id: str, limit: int = 100) -> List[StoredFile]:
        """List all images for a user."""
        return await self.provider.list_files(f"users/{user_id}", limit)
    
    async def get_images_by_ids(self, user_id: str, image_ids: List[str]) -> List[StoredFile]:
        """Get specific images by their IDs for a user."""
        try:
            all_images = await self.list_user_images(user_id, 1000)  # Get more images to search through
            return [img for img in all_images if img.file_id in image_ids]
        except Exception as e:
            logger.error(f"Failed to get images by IDs for user {user_id}: {e}")
            return []
    
    async def get_storage_stats(self) -> Dict[str, int]:
        """Get storage usage statistics."""
        try:
            # Get all files (this is a simplified version - in production you'd want pagination)
            all_files = await self.provider.list_files("", 1000)
            
            total_files = len(all_files)
            total_size = sum(file.size for file in all_files)
            
            # Count by type
            type_counts = {}
            for file in all_files:
                path_parts = file.storage_path.split('/')
                if len(path_parts) >= 2:
                    file_type = path_parts[1]  # images/original, products/xxx/compressed, etc.
                    type_counts[file_type] = type_counts.get(file_type, 0) + 1
            
            return {
                'total_files': total_files,
                'total_size_bytes': total_size,
                'type_breakdown': type_counts
            }
            
        except StorageError as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {'total_files': 0, 'total_size_bytes': 0, 'type_breakdown': {}}


# Global service instance - initialized lazily
storage_service = None


def get_storage_service() -> CloudStorageService:
    """Get or create the global storage service instance."""
    global storage_service
    if storage_service is None:
        storage_service = CloudStorageService()
    return storage_service