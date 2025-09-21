"""
Integration tests for cloud storage service.
"""

import pytest
import io
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from app.services.cloud_storage import (
    CloudStorageService, AWSS3Provider, GoogleCloudProvider, CloudflareR2Provider,
    StorageError, StoredFile, PresignedUploadData
)
from app.config import settings


class TestCloudStorageService:
    """Test cases for the unified cloud storage service."""
    
    @pytest.fixture
    def mock_aws_provider(self):
        """Mock AWS S3 provider."""
        provider = Mock(spec=AWSS3Provider)
        provider.upload_file = AsyncMock()
        provider.download_file = AsyncMock()
        provider.delete_file = AsyncMock()
        provider.generate_presigned_upload_url = AsyncMock()
        provider.generate_presigned_download_url = AsyncMock()
        provider.list_files = AsyncMock()
        return provider
    
    @pytest.fixture
    def sample_file_data(self):
        """Sample file data for testing."""
        return b"fake image data"
    
    @pytest.fixture
    def sample_stored_file(self):
        """Sample stored file response."""
        return StoredFile(
            file_id="test-file-id",
            filename="test.jpg",
            url="https://example.com/test.jpg",
            size=1024,
            content_type="image/jpeg",
            storage_path="images/original/2024/01/01/test-file-id_test.jpg",
            created_at=datetime.utcnow()
        )
    
    @pytest.fixture
    def sample_presigned_data(self):
        """Sample presigned upload data."""
        return PresignedUploadData(
            upload_url="https://example.com/upload",
            fields={"key": "test-key", "Content-Type": "image/jpeg"},
            file_id="test-file-id",
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
    
    @patch('app.services.cloud_storage.CloudStorageService._initialize_provider')
    def test_service_initialization(self, mock_init_provider, mock_aws_provider):
        """Test service initialization with different providers."""
        mock_init_provider.return_value = mock_aws_provider
        
        service = CloudStorageService()
        assert service.provider == mock_aws_provider
        mock_init_provider.assert_called_once()
    
    @patch('app.services.cloud_storage.settings')
    @patch('app.services.cloud_storage.AWSS3Provider')
    def test_initialize_aws_provider(self, mock_aws_class, mock_settings):
        """Test AWS provider initialization."""
        mock_settings.storage_provider = "aws"
        mock_provider = Mock()
        mock_aws_class.return_value = mock_provider
        
        service = CloudStorageService()
        assert service.provider == mock_provider
        mock_aws_class.assert_called_once()
    
    @patch('app.services.cloud_storage.settings')
    @patch('app.services.cloud_storage.GoogleCloudProvider')
    def test_initialize_gcp_provider(self, mock_gcp_class, mock_settings):
        """Test Google Cloud provider initialization."""
        mock_settings.storage_provider = "gcp"
        mock_provider = Mock()
        mock_gcp_class.return_value = mock_provider
        
        service = CloudStorageService()
        assert service.provider == mock_provider
        mock_gcp_class.assert_called_once()
    
    @patch('app.services.cloud_storage.settings')
    @patch('app.services.cloud_storage.CloudflareR2Provider')
    def test_initialize_cloudflare_provider(self, mock_cf_class, mock_settings):
        """Test Cloudflare R2 provider initialization."""
        mock_settings.storage_provider = "cloudflare"
        mock_provider = Mock()
        mock_cf_class.return_value = mock_provider
        
        service = CloudStorageService()
        assert service.provider == mock_provider
        mock_cf_class.assert_called_once()
    
    @patch('app.services.cloud_storage.settings')
    def test_initialize_unsupported_provider(self, mock_settings):
        """Test initialization with unsupported provider."""
        mock_settings.storage_provider = "unsupported"
        
        with pytest.raises(StorageError, match="Unsupported storage provider"):
            CloudStorageService()
    
    @pytest.mark.asyncio
    @patch('app.services.cloud_storage.CloudStorageService._initialize_provider')
    async def test_upload_image(self, mock_init_provider, mock_aws_provider, 
                               sample_file_data, sample_stored_file):
        """Test image upload functionality."""
        mock_init_provider.return_value = mock_aws_provider
        mock_aws_provider.upload_file.return_value = sample_stored_file
        
        service = CloudStorageService()
        result = await service.upload_image(
            sample_file_data, "test.jpg", "image/jpeg", "original"
        )
        
        assert result == sample_stored_file
        mock_aws_provider.upload_file.assert_called_once_with(
            sample_file_data, "test.jpg", "image/jpeg", "images/original"
        )
    
    @pytest.mark.asyncio
    @patch('app.services.cloud_storage.CloudStorageService._initialize_provider')
    async def test_upload_product_images(self, mock_init_provider, mock_aws_provider, 
                                        sample_stored_file):
        """Test product images upload functionality."""
        mock_init_provider.return_value = mock_aws_provider
        mock_aws_provider.upload_file.return_value = sample_stored_file
        
        service = CloudStorageService()
        
        images = {
            "original": b"original data",
            "compressed": b"compressed data"
        }
        filenames = {
            "original": "test.jpg",
            "compressed": "test_compressed.jpg"
        }
        content_types = {
            "original": "image/jpeg",
            "compressed": "image/jpeg"
        }
        
        result = await service.upload_product_images(
            "product-123", images, filenames, content_types
        )
        
        assert len(result) == 2
        assert "original" in result
        assert "compressed" in result
        assert mock_aws_provider.upload_file.call_count == 2
    
    @pytest.mark.asyncio
    @patch('app.services.cloud_storage.CloudStorageService._initialize_provider')
    async def test_download_file(self, mock_init_provider, mock_aws_provider, sample_file_data):
        """Test file download functionality."""
        mock_init_provider.return_value = mock_aws_provider
        mock_aws_provider.download_file.return_value = sample_file_data
        
        service = CloudStorageService()
        result = await service.download_file("test/path/file.jpg")
        
        assert result == sample_file_data
        mock_aws_provider.download_file.assert_called_once_with("test/path/file.jpg")
    
    @pytest.mark.asyncio
    @patch('app.services.cloud_storage.CloudStorageService._initialize_provider')
    async def test_delete_file(self, mock_init_provider, mock_aws_provider):
        """Test file deletion functionality."""
        mock_init_provider.return_value = mock_aws_provider
        mock_aws_provider.delete_file.return_value = True
        
        service = CloudStorageService()
        result = await service.delete_file("test/path/file.jpg")
        
        assert result is True
        mock_aws_provider.delete_file.assert_called_once_with("test/path/file.jpg")
    
    @pytest.mark.asyncio
    @patch('app.services.cloud_storage.CloudStorageService._initialize_provider')
    async def test_delete_product_images(self, mock_init_provider, mock_aws_provider, 
                                        sample_stored_file):
        """Test product images deletion functionality."""
        mock_init_provider.return_value = mock_aws_provider
        mock_aws_provider.list_files.return_value = [sample_stored_file]
        mock_aws_provider.delete_file.return_value = True
        
        service = CloudStorageService()
        result = await service.delete_product_images("product-123")
        
        assert len(result) == 1
        assert sample_stored_file.storage_path in result
        assert result[sample_stored_file.storage_path] is True
        mock_aws_provider.list_files.assert_called_once_with("products/product-123")
        mock_aws_provider.delete_file.assert_called_once_with(sample_stored_file.storage_path)
    
    @pytest.mark.asyncio
    @patch('app.services.cloud_storage.CloudStorageService._initialize_provider')
    async def test_generate_presigned_upload_url(self, mock_init_provider, mock_aws_provider, 
                                               sample_presigned_data):
        """Test presigned upload URL generation."""
        mock_init_provider.return_value = mock_aws_provider
        mock_aws_provider.generate_presigned_upload_url.return_value = sample_presigned_data
        
        service = CloudStorageService()
        result = await service.generate_presigned_upload_url(
            "test.jpg", "image/jpeg", "original", 3600
        )
        
        assert result == sample_presigned_data
        mock_aws_provider.generate_presigned_upload_url.assert_called_once_with(
            "test.jpg", "image/jpeg", "images/original", 3600
        )
    
    @pytest.mark.asyncio
    @patch('app.services.cloud_storage.CloudStorageService._initialize_provider')
    async def test_generate_presigned_download_url(self, mock_init_provider, mock_aws_provider):
        """Test presigned download URL generation."""
        mock_init_provider.return_value = mock_aws_provider
        mock_aws_provider.generate_presigned_download_url.return_value = "https://example.com/download"
        
        service = CloudStorageService()
        result = await service.generate_presigned_download_url("test/path/file.jpg", 3600)
        
        assert result == "https://example.com/download"
        mock_aws_provider.generate_presigned_download_url.assert_called_once_with(
            "test/path/file.jpg", 3600
        )
    
    @pytest.mark.asyncio
    @patch('app.services.cloud_storage.CloudStorageService._initialize_provider')
    async def test_list_user_images(self, mock_init_provider, mock_aws_provider, sample_stored_file):
        """Test user images listing functionality."""
        mock_init_provider.return_value = mock_aws_provider
        mock_aws_provider.list_files.return_value = [sample_stored_file]
        
        service = CloudStorageService()
        result = await service.list_user_images("user-123", 100)
        
        assert len(result) == 1
        assert result[0] == sample_stored_file
        mock_aws_provider.list_files.assert_called_once_with("users/user-123", 100)
    
    @pytest.mark.asyncio
    @patch('app.services.cloud_storage.CloudStorageService._initialize_provider')
    async def test_get_storage_stats(self, mock_init_provider, mock_aws_provider, sample_stored_file):
        """Test storage statistics functionality."""
        mock_init_provider.return_value = mock_aws_provider
        
        # Create multiple files with different paths
        files = [
            StoredFile(
                file_id="1", filename="test1.jpg", url="url1", size=1024,
                content_type="image/jpeg", storage_path="images/original/file1.jpg",
                created_at=datetime.utcnow()
            ),
            StoredFile(
                file_id="2", filename="test2.jpg", url="url2", size=2048,
                content_type="image/jpeg", storage_path="images/compressed/file2.jpg",
                created_at=datetime.utcnow()
            )
        ]
        mock_aws_provider.list_files.return_value = files
        
        service = CloudStorageService()
        result = await service.get_storage_stats()
        
        assert result['total_files'] == 2
        assert result['total_size_bytes'] == 3072
        assert result['type_breakdown']['original'] == 1
        assert result['type_breakdown']['compressed'] == 1
        mock_aws_provider.list_files.assert_called_once_with("", 1000)
    
    @pytest.mark.asyncio
    @patch('app.services.cloud_storage.CloudStorageService._initialize_provider')
    async def test_upload_with_storage_error(self, mock_init_provider, mock_aws_provider):
        """Test handling of storage errors during upload."""
        mock_init_provider.return_value = mock_aws_provider
        mock_aws_provider.upload_file.side_effect = StorageError("Upload failed")
        
        service = CloudStorageService()
        
        # Should not raise exception, but log error and continue
        result = await service.upload_product_images(
            "product-123", 
            {"original": b"data"}, 
            {"original": "test.jpg"}, 
            {"original": "image/jpeg"}
        )
        
        assert len(result) == 0  # No successful uploads


class TestAWSS3Provider:
    """Test cases for AWS S3 provider."""
    
    @patch('app.services.cloud_storage.boto3')
    @patch('app.services.cloud_storage.settings')
    def test_initialization_success(self, mock_settings, mock_boto3):
        """Test successful AWS S3 provider initialization."""
        mock_settings.aws_access_key_id = "test_key"
        mock_settings.aws_secret_access_key = "test_secret"
        mock_settings.aws_region = "us-east-1"
        mock_settings.aws_s3_bucket = "test-bucket"
        
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        
        provider = AWSS3Provider()
        
        assert provider.client == mock_client
        assert provider.bucket == "test-bucket"
        mock_boto3.client.assert_called_once()
        mock_client.head_bucket.assert_called_once_with(Bucket="test-bucket")
    
    @patch('app.services.cloud_storage.boto3')
    def test_initialization_no_credentials(self, mock_boto3):
        """Test AWS S3 provider initialization without credentials."""
        from botocore.exceptions import NoCredentialsError
        
        mock_boto3.client.side_effect = NoCredentialsError()
        
        with pytest.raises(StorageError, match="AWS credentials not found"):
            AWSS3Provider()
    
    def test_generate_storage_path(self):
        """Test storage path generation."""
        with patch('app.services.cloud_storage.boto3'), \
             patch('app.services.cloud_storage.settings') as mock_settings:
            
            mock_settings.aws_access_key_id = "test_key"
            mock_settings.aws_secret_access_key = "test_secret"
            mock_settings.aws_region = "us-east-1"
            mock_settings.aws_s3_bucket = "test-bucket"
            
            mock_client = Mock()
            with patch('app.services.cloud_storage.boto3.client', return_value=mock_client):
                provider = AWSS3Provider()
                
                path = provider._generate_storage_path("test.jpg", "images")
                
                assert path.startswith("images/")
                assert path.endswith("_test.jpg")
                assert len(path.split('/')) == 4  # images/YYYY/MM/DD/uuid_filename


class TestGoogleCloudProvider:
    """Test cases for Google Cloud Storage provider."""
    
    @patch('app.services.cloud_storage.gcs')
    @patch('app.services.cloud_storage.settings')
    def test_initialization_with_credentials_file(self, mock_settings, mock_gcs):
        """Test Google Cloud provider initialization with credentials file."""
        mock_settings.gcp_credentials_path = "/path/to/credentials.json"
        mock_settings.gcp_bucket_name = "test-bucket"
        
        mock_client = Mock()
        mock_bucket = Mock()
        mock_gcs.Client.from_service_account_json.return_value = mock_client
        mock_client.bucket.return_value = mock_bucket
        
        provider = GoogleCloudProvider()
        
        assert provider.client == mock_client
        assert provider.bucket == mock_bucket
        mock_gcs.Client.from_service_account_json.assert_called_once_with("/path/to/credentials.json")
        mock_bucket.reload.assert_called_once()
    
    @patch('app.services.cloud_storage.gcs')
    @patch('app.services.cloud_storage.settings')
    def test_initialization_with_project_id(self, mock_settings, mock_gcs):
        """Test Google Cloud provider initialization with project ID."""
        mock_settings.gcp_credentials_path = ""
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gcp_bucket_name = "test-bucket"
        
        mock_client = Mock()
        mock_bucket = Mock()
        mock_gcs.Client.return_value = mock_client
        mock_client.bucket.return_value = mock_bucket
        
        provider = GoogleCloudProvider()
        
        assert provider.client == mock_client
        assert provider.bucket == mock_bucket
        mock_gcs.Client.assert_called_once_with(project="test-project")


class TestCloudflareR2Provider:
    """Test cases for Cloudflare R2 provider."""
    
    @patch('app.services.cloud_storage.boto3')
    @patch('app.services.cloud_storage.settings')
    def test_initialization_success(self, mock_settings, mock_boto3):
        """Test successful Cloudflare R2 provider initialization."""
        mock_settings.cloudflare_access_key_id = "test_key"
        mock_settings.cloudflare_secret_access_key = "test_secret"
        mock_settings.cloudflare_endpoint_url = "https://test.r2.cloudflarestorage.com"
        mock_settings.cloudflare_bucket_name = "test-bucket"
        
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        
        provider = CloudflareR2Provider()
        
        assert provider.client == mock_client
        assert provider.bucket == "test-bucket"
        mock_boto3.client.assert_called_once()
        mock_client.head_bucket.assert_called_once_with(Bucket="test-bucket")


# Integration test with actual file operations (mocked)
class TestCloudStorageIntegration:
    """Integration tests for cloud storage operations."""
    
    @pytest.fixture
    def mock_image_file(self):
        """Create a mock image file for testing."""
        return io.BytesIO(b"fake image data")
    
    @pytest.mark.asyncio
    @patch('app.services.cloud_storage.CloudStorageService._initialize_provider')
    async def test_complete_image_workflow(self, mock_init_provider, mock_image_file):
        """Test complete image upload, download, and delete workflow."""
        # Setup mock provider
        mock_provider = Mock()
        mock_provider.upload_file = AsyncMock()
        mock_provider.download_file = AsyncMock()
        mock_provider.delete_file = AsyncMock()
        mock_provider.generate_presigned_upload_url = AsyncMock()
        mock_provider.generate_presigned_download_url = AsyncMock()
        mock_provider.list_files = AsyncMock()
        
        mock_init_provider.return_value = mock_provider
        
        # Create stored file response
        stored_file = StoredFile(
            file_id="test-id",
            filename="test.jpg",
            url="https://example.com/test.jpg",
            size=1024,
            content_type="image/jpeg",
            storage_path="images/original/test.jpg",
            created_at=datetime.utcnow()
        )
        
        mock_provider.upload_file.return_value = stored_file
        mock_provider.download_file.return_value = b"fake image data"
        mock_provider.delete_file.return_value = True
        
        service = CloudStorageService()
        
        # Test upload
        upload_result = await service.upload_image(
            b"fake image data", "test.jpg", "image/jpeg", "original"
        )
        assert upload_result == stored_file
        
        # Test download
        download_result = await service.download_file("images/original/test.jpg")
        assert download_result == b"fake image data"
        
        # Test delete
        delete_result = await service.delete_file("images/original/test.jpg")
        assert delete_result is True
        
        # Verify all operations were called
        mock_provider.upload_file.assert_called_once()
        mock_provider.download_file.assert_called_once()
        mock_provider.delete_file.assert_called_once()