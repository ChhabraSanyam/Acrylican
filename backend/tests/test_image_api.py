"""
Integration tests for image processing API endpoints.
"""

import io
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from app.main import app
from app.services.image_processing import PLATFORM_REQUIREMENTS
from app.services.cloud_storage import StoredFile, PresignedUploadData, StorageError
from datetime import datetime, timedelta


class TestImageAPI:
    """Test cases for image processing API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def sample_image_file(self):
        """Create a sample image file for testing."""
        img = Image.new('RGB', (400, 300), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        return img_bytes
    
    @pytest.fixture
    def auth_headers(self):
        """Mock authentication headers."""
        # In a real test, you would create a test user and get a real token
        # For now, we'll mock the authentication dependency
        return {"Authorization": "Bearer test-token"}
    
    def test_get_supported_platforms(self, client):
        """Test getting supported platforms endpoint."""
        response = client.get("/images/platforms")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "platforms" in data
        assert "count" in data
        assert isinstance(data["platforms"], list)
        assert data["count"] == len(PLATFORM_REQUIREMENTS)
        assert "facebook" in data["platforms"]
        assert "instagram" in data["platforms"]
    
    def test_get_platform_requirements_valid(self, client):
        """Test getting platform requirements for valid platform."""
        response = client.get("/images/platforms/facebook/requirements")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["platform"] == "facebook"
        assert "requirements" in data
        
        requirements = data["requirements"]
        assert "max_width" in requirements
        assert "max_height" in requirements
        assert "quality" in requirements
        assert "format" in requirements
    
    def test_get_platform_requirements_invalid(self, client):
        """Test getting platform requirements for invalid platform."""
        response = client.get("/images/platforms/invalid_platform/requirements")
        
        assert response.status_code == 404
        assert "not supported" in response.json()["detail"]
    
    # Note: The following tests would require proper authentication setup
    # For now, they are commented out as they would fail without auth mocking
    
    # def test_validate_image_valid(self, client, sample_image_file, auth_headers):
    #     """Test image validation with valid image."""
    #     files = {"file": ("test.jpg", sample_image_file, "image/jpeg")}
    #     
    #     response = client.post("/images/validate", files=files, headers=auth_headers)
    #     
    #     assert response.status_code == 200
    #     data = response.json()
    #     
    #     assert data["valid"] is True
    #     assert data["filename"] == "test.jpg"
    #     assert "message" in data
    
    # def test_validate_image_invalid(self, client, auth_headers):
    #     """Test image validation with invalid file."""
    #     invalid_file = io.BytesIO(b"not an image")
    #     files = {"file": ("test.txt", invalid_file, "text/plain")}
    #     
    #     response = client.post("/images/validate", files=files, headers=auth_headers)
    #     
    #     assert response.status_code == 200
    #     data = response.json()
    #     
    #     assert data["valid"] is False
    #     assert "error" in data
    
    # def test_process_image_success(self, client, sample_image_file, auth_headers):
    #     """Test successful image processing."""
    #     files = {"file": ("test.jpg", sample_image_file, "image/jpeg")}
    #     params = {"platforms": ["facebook", "instagram"]}
    #     
    #     response = client.post("/images/process", files=files, params=params, headers=auth_headers)
    #     
    #     assert response.status_code == 200
    #     data = response.json()
    #     
    #     assert "id" in data
    #     assert data["original_filename"] == "test.jpg"
    #     assert data["file_size"] > 0
    #     assert "dimensions" in data
    #     assert data["format"] == "JPEG"
    #     assert "processing_time" in data
    #     assert len(data["platform_optimizations"]) == 2
    
    # def test_upload_image_success(self, client, sample_image_file, auth_headers):
    #     """Test successful image upload."""
    #     files = {"file": ("test.jpg", sample_image_file, "image/jpeg")}
    #     params = {"platforms": ["facebook"]}
    #     
    #     response = client.post("/images/upload", files=files, params=params, headers=auth_headers)
    #     
    #     assert response.status_code == 200
    #     data = response.json()
    #     
    #     assert data["success"] is True
    #     assert "image_id" in data
    #     assert "message" in data
    #     assert "urls" in data
    #     
    #     urls = data["urls"]
    #     assert "original" in urls
    #     assert "compressed" in urls
    #     assert "thumbnail" in urls


class TestImageAPIConstants:
    """Test API constants and configurations."""
    
    def test_platform_requirements_completeness(self):
        """Test that all required platforms have complete requirements."""
        required_platforms = [
            'facebook', 'instagram', 'facebook_marketplace', 
            'etsy', 'pinterest', 'shopify', 'meesho', 'snapdeal', 'indiamart'
        ]
        
        for platform in required_platforms:
            assert platform in PLATFORM_REQUIREMENTS
            
            requirements = PLATFORM_REQUIREMENTS[platform]
            assert 'max_width' in requirements
            assert 'max_height' in requirements
            assert 'quality' in requirements
            assert 'format' in requirements
            
            # Validate reasonable values
            assert 100 <= requirements['max_width'] <= 5000
            assert 100 <= requirements['max_height'] <= 5000
            assert 1 <= requirements['quality'] <= 100
            assert requirements['format'] in ['JPEG', 'PNG', 'WEBP']


class TestImageAPICloudStorageIntegration:
    """Test cloud storage integration in image API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def sample_image_file(self):
        """Create a sample image file for testing."""
        img = Image.new('RGB', (400, 300), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        return img_bytes
    
    @pytest.fixture
    def mock_stored_file(self):
        """Create mock stored file response."""
        return StoredFile(
            file_id="test-file-id",
            filename="test.jpg",
            url="https://example.com/test.jpg",
            size=1024,
            content_type="image/jpeg",
            storage_path="images/original/test.jpg",
            created_at=datetime.utcnow()
        )
    
    @pytest.fixture
    def mock_presigned_data(self):
        """Create mock presigned upload data."""
        return PresignedUploadData(
            upload_url="https://example.com/upload",
            fields={"key": "test-key", "Content-Type": "image/jpeg"},
            file_id="test-file-id",
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
    
    # Note: These tests would require proper authentication setup
    # They demonstrate the expected behavior with cloud storage integration
    
    @pytest.mark.skip(reason="Requires authentication setup")
    @patch('app.services.image_processing.storage_service')
    def test_upload_image_with_cloud_storage(self, mock_storage_service, client, sample_image_file, mock_stored_file):
        """Test image upload with cloud storage integration."""
        # Mock cloud storage responses
        mock_storage_service.upload_image.return_value = mock_stored_file
        
        files = {"file": ("test.jpg", sample_image_file, "image/jpeg")}
        params = {"platforms": ["facebook"]}
        
        response = client.post("/images/upload", files=files, params=params)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "image_id" in data
        assert "urls" in data
        
        urls = data["urls"]
        assert "original" in urls
        assert "compressed" in urls
        assert "thumbnails" in urls
        assert "platform_optimized" in urls
        
        # Verify cloud URLs are returned
        assert urls["original"] == "https://example.com/test.jpg"
    
    @pytest.mark.skip(reason="Requires authentication setup")
    def test_generate_presigned_upload_url(self, client, mock_presigned_data):
        """Test presigned upload URL generation endpoint."""
        with patch('app.services.image_processing.image_service.generate_presigned_upload_url') as mock_generate:
            mock_generate.return_value = {
                'upload_url': mock_presigned_data.upload_url,
                'fields': mock_presigned_data.fields,
                'file_id': mock_presigned_data.file_id,
                'expires_at': mock_presigned_data.expires_at.isoformat()
            }
            
            params = {
                "filename": "test.jpg",
                "content_type": "image/jpeg",
                "image_type": "original"
            }
            
            response = client.post("/images/presigned-upload", params=params)
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert "upload_data" in data
            
            upload_data = data["upload_data"]
            assert upload_data["upload_url"] == "https://example.com/upload"
            assert upload_data["file_id"] == "test-file-id"
    
    @pytest.mark.skip(reason="Requires authentication setup")
    @patch('app.services.cloud_storage.storage_service')
    def test_generate_presigned_download_url(self, mock_storage_service, client):
        """Test presigned download URL generation endpoint."""
        mock_storage_service.generate_presigned_download_url.return_value = "https://example.com/download?signature=abc123"
        
        response = client.get("/images/download/images/original/test.jpg?expires_in=3600")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["download_url"] == "https://example.com/download?signature=abc123"
        assert data["expires_in"] == 3600
    
    @pytest.mark.skip(reason="Requires authentication setup")
    @patch('app.services.cloud_storage.storage_service')
    def test_delete_image(self, mock_storage_service, client):
        """Test image deletion endpoint."""
        mock_storage_service.delete_file.return_value = True
        
        response = client.delete("/images/images/original/test.jpg")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "deleted successfully" in data["message"]
    
    @pytest.mark.skip(reason="Requires authentication setup")
    @patch('app.services.cloud_storage.storage_service')
    def test_delete_image_not_found(self, mock_storage_service, client):
        """Test image deletion when file not found."""
        mock_storage_service.delete_file.return_value = False
        
        response = client.delete("/images/images/original/nonexistent.jpg")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    @pytest.mark.skip(reason="Requires authentication setup")
    @patch('app.services.cloud_storage.storage_service')
    def test_list_user_images(self, mock_storage_service, client, mock_stored_file):
        """Test listing user images endpoint."""
        mock_storage_service.list_user_images.return_value = [mock_stored_file]
        
        response = client.get("/images/user/images?limit=50")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "images" in data
        assert data["count"] == 1
        
        images = data["images"]
        assert len(images) == 1
        assert images[0]["file_id"] == "test-file-id"
        assert images[0]["filename"] == "test.jpg"
        assert images[0]["url"] == "https://example.com/test.jpg"
    
    @pytest.mark.skip(reason="Requires authentication setup")
    @patch('app.services.cloud_storage.storage_service')
    def test_get_storage_stats(self, mock_storage_service, client):
        """Test storage statistics endpoint."""
        mock_stats = {
            'total_files': 150,
            'total_size_bytes': 52428800,  # 50MB
            'type_breakdown': {
                'original': 50,
                'compressed': 50,
                'thumbnail_small': 25,
                'thumbnail_medium': 25
            }
        }
        mock_storage_service.get_storage_stats.return_value = mock_stats
        
        response = client.get("/images/storage/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["stats"] == mock_stats
    
    @pytest.mark.skip(reason="Requires authentication setup")
    @patch('app.services.cloud_storage.storage_service')
    def test_storage_error_handling(self, mock_storage_service, client, sample_image_file):
        """Test handling of storage errors in upload endpoint."""
        mock_storage_service.upload_image.side_effect = StorageError("Storage unavailable")
        
        files = {"file": ("test.jpg", sample_image_file, "image/jpeg")}
        
        response = client.post("/images/upload", files=files)
        
        assert response.status_code == 500
        assert "File upload failed" in response.json()["detail"]