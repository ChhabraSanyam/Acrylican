"""
Comprehensive integration tests for the Artisan Promotion Platform.

These tests verify that different components work together correctly,
including API endpoints, services, and database interactions.
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from decimal import Decimal
import json
import io
from PIL import Image

from app.main import app
from app.models import User, Product, Post, SaleEvent, PlatformConnection
from app.database import get_db


@pytest.mark.integration
class TestAuthenticationIntegration:
    """Integration tests for authentication flow."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_complete_auth_flow(self, client, db_session):
        """Test complete authentication flow from registration to protected access."""
        # Step 1: Register new user
        registration_data = {
            "email": "integration@test.com",
            "password": "SecurePass123!",
            "business_name": "Integration Test Business",
            "business_type": "Handicrafts"
        }
        
        response = client.post("/auth/register", json=registration_data)
        assert response.status_code == 201
        
        user_data = response.json()
        assert "access_token" in user_data
        assert user_data["user"]["email"] == registration_data["email"]
        
        access_token = user_data["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Step 2: Access protected endpoint
        response = client.get("/auth/me", headers=headers)
        assert response.status_code == 200
        
        current_user = response.json()
        assert current_user["email"] == registration_data["email"]
        
        # Step 3: Login with credentials
        login_data = {
            "email": registration_data["email"],
            "password": registration_data["password"]
        }
        
        response = client.post("/auth/login", json=login_data)
        assert response.status_code == 200
        
        login_result = response.json()
        assert "access_token" in login_result
        
        # Step 4: Refresh token
        refresh_token = user_data.get("refresh_token")
        if refresh_token:
            response = client.post("/auth/refresh", json={"refresh_token": refresh_token})
            assert response.status_code == 200
    
    def test_invalid_authentication_attempts(self, client):
        """Test various invalid authentication scenarios."""
        # Invalid registration data
        invalid_registration = {
            "email": "invalid-email",
            "password": "weak",
            "business_name": "",
            "business_type": ""
        }
        
        response = client.post("/auth/register", json=invalid_registration)
        assert response.status_code == 422
        
        # Invalid login credentials
        invalid_login = {
            "email": "nonexistent@test.com",
            "password": "wrongpassword"
        }
        
        response = client.post("/auth/login", json=invalid_login)
        assert response.status_code == 401
        
        # Access protected endpoint without token
        response = client.get("/auth/me")
        assert response.status_code == 401


@pytest.mark.integration
class TestProductManagementIntegration:
    """Integration tests for product management."""
    
    @pytest.fixture
    def authenticated_client(self, client, sample_user_data):
        """Create authenticated client with test user."""
        # Register user
        response = client.post("/auth/register", json=sample_user_data)
        assert response.status_code == 201
        
        user_data = response.json()
        access_token = user_data["access_token"]
        
        client.headers = {"Authorization": f"Bearer {access_token}"}
        client.user_id = user_data["user"]["id"]
        
        return client
    
    def test_product_lifecycle(self, authenticated_client):
        """Test complete product lifecycle: create, read, update, delete."""
        # Create product
        product_data = {
            "title": "Integration Test Product",
            "description": "A product created during integration testing",
            "category": "Test Category",
            "price": "29.99",
            "materials": ["test_material"],
            "dimensions": "10x10x10 cm"
        }
        
        response = authenticated_client.post("/products/", json=product_data)
        assert response.status_code == 201
        
        created_product = response.json()
        product_id = created_product["id"]
        assert created_product["title"] == product_data["title"]
        
        # Read product
        response = authenticated_client.get(f"/products/{product_id}")
        assert response.status_code == 200
        
        retrieved_product = response.json()
        assert retrieved_product["id"] == product_id
        
        # Update product
        update_data = {
            "title": "Updated Integration Test Product",
            "price": "39.99"
        }
        
        response = authenticated_client.put(f"/products/{product_id}", json=update_data)
        assert response.status_code == 200
        
        updated_product = response.json()
        assert updated_product["title"] == update_data["title"]
        assert updated_product["price"] == update_data["price"]
        
        # List products
        response = authenticated_client.get("/products/")
        assert response.status_code == 200
        
        products_list = response.json()
        assert len(products_list) >= 1
        assert any(p["id"] == product_id for p in products_list)
        
        # Delete product
        response = authenticated_client.delete(f"/products/{product_id}")
        assert response.status_code == 200
        
        # Verify deletion
        response = authenticated_client.get(f"/products/{product_id}")
        assert response.status_code == 404


@pytest.mark.integration
class TestContentGenerationIntegration:
    """Integration tests for content generation workflow."""
    
    @pytest.fixture
    def authenticated_client(self, client, sample_user_data):
        """Create authenticated client with test user."""
        response = client.post("/auth/register", json=sample_user_data)
        user_data = response.json()
        access_token = user_data["access_token"]
        
        client.headers = {"Authorization": f"Bearer {access_token}"}
        return client
    
    @patch('app.services.content_generation.genai')
    def test_content_generation_workflow(self, mock_genai, authenticated_client):
        """Test complete content generation workflow."""
        # Mock Gemini API response
        mock_response = Mock()
        mock_response.text = """
        Title: Beautiful Handcrafted Test Product
        
        Description: Experience the artistry of handcrafted excellence with this unique test product. Each piece is lovingly created by skilled artisans.
        
        Hashtags: #handmade #test #artisan #unique #crafted
        """
        
        mock_model = Mock()
        mock_model.generate_content = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model
        
        # Create a product first
        product_data = {
            "title": "Test Product for Content",
            "description": "A test product for content generation",
            "category": "Test"
        }
        
        response = authenticated_client.post("/products/", json=product_data)
        assert response.status_code == 201
        product = response.json()
        
        # Generate content for the product
        content_request = {
            "product_id": product["id"],
            "platforms": ["facebook", "instagram"],
            "tone": "professional",
            "target_audience": "art_lovers"
        }
        
        response = authenticated_client.post("/content/generate", json=content_request)
        assert response.status_code == 200
        
        generated_content = response.json()
        assert "title" in generated_content
        assert "description" in generated_content
        assert "hashtags" in generated_content
        assert len(generated_content["hashtags"]) > 0
        
        # Validate content for platforms
        validation_request = {
            "content": generated_content,
            "platforms": ["facebook", "instagram"]
        }
        
        response = authenticated_client.post("/content/validate", json=validation_request)
        assert response.status_code == 200
        
        validation_result = response.json()
        assert "facebook" in validation_result
        assert "instagram" in validation_result


@pytest.mark.integration
class TestImageProcessingIntegration:
    """Integration tests for image processing workflow."""
    
    @pytest.fixture
    def authenticated_client(self, client, sample_user_data):
        """Create authenticated client with test user."""
        response = client.post("/auth/register", json=sample_user_data)
        user_data = response.json()
        access_token = user_data["access_token"]
        
        client.headers = {"Authorization": f"Bearer {access_token}"}
        return client
    
    @pytest.fixture
    def test_image(self):
        """Create a test image file."""
        img = Image.new('RGB', (800, 600), color='blue')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        return img_bytes
    
    @patch('app.services.image_processing.get_storage_service')
    def test_image_upload_and_processing(self, mock_storage, authenticated_client, test_image):
        """Test complete image upload and processing workflow."""
        # Mock storage service
        mock_storage_instance = Mock()
        mock_storage_instance.upload_image = AsyncMock(return_value=Mock(
            file_id="test-image-id",
            url="https://example.com/test-image.jpg",
            size=1024,
            content_type="image/jpeg"
        ))
        mock_storage.return_value = mock_storage_instance
        
        # Create a product first
        product_data = {
            "title": "Product with Image",
            "description": "Test product for image upload"
        }
        
        response = authenticated_client.post("/products/", json=product_data)
        product = response.json()
        
        # Upload image
        files = {"file": ("test.jpg", test_image, "image/jpeg")}
        data = {
            "product_id": product["id"],
            "platforms": "facebook,instagram"
        }
        
        response = authenticated_client.post("/images/upload", files=files, data=data)
        assert response.status_code == 200
        
        upload_result = response.json()
        assert "original_url" in upload_result
        assert "compressed_url" in upload_result
        assert "thumbnail_urls" in upload_result
        
        # Get product images
        response = authenticated_client.get(f"/products/{product['id']}/images")
        assert response.status_code == 200
        
        images = response.json()
        assert len(images) >= 1


@pytest.mark.integration
class TestPostingWorkflowIntegration:
    """Integration tests for posting workflow."""
    
    @pytest.fixture
    def authenticated_client(self, client, sample_user_data):
        """Create authenticated client with test user."""
        response = client.post("/auth/register", json=sample_user_data)
        user_data = response.json()
        access_token = user_data["access_token"]
        
        client.headers = {"Authorization": f"Bearer {access_token}"}
        client.user_id = user_data["user"]["id"]
        return client
    
    @patch('app.services.posting_service.get_platform_service')
    def test_post_creation_and_scheduling(self, mock_platform_service, authenticated_client):
        """Test post creation and scheduling workflow."""
        # Mock platform service
        mock_platform_service.return_value.post_content = AsyncMock(return_value={
            'facebook': {'success': True, 'post_id': 'fb_123'},
            'instagram': {'success': True, 'post_id': 'ig_123'}
        })
        
        # Create product and content
        product_data = {
            "title": "Test Product for Posting",
            "description": "Product for testing posting workflow"
        }
        
        response = authenticated_client.post("/products/", json=product_data)
        product = response.json()
        
        # Create post
        post_data = {
            "product_id": product["id"],
            "platforms": ["facebook", "instagram"],
            "content": {
                "title": "Test Post",
                "description": "This is a test post",
                "hashtags": ["#test", "#integration"]
            },
            "scheduled_at": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            "images": ["https://example.com/test-image.jpg"]
        }
        
        response = authenticated_client.post("/posts/", json=post_data)
        assert response.status_code == 201
        
        created_post = response.json()
        post_id = created_post["id"]
        assert created_post["status"] == "scheduled"
        
        # Get post details
        response = authenticated_client.get(f"/posts/{post_id}")
        assert response.status_code == 200
        
        # Publish post immediately
        response = authenticated_client.post(f"/posts/{post_id}/publish")
        assert response.status_code == 200
        
        publish_result = response.json()
        assert publish_result["success"] is True
        
        # Check post status
        response = authenticated_client.get(f"/posts/{post_id}")
        post_status = response.json()
        assert post_status["status"] in ["published", "publishing"]


@pytest.mark.integration
class TestAnalyticsIntegration:
    """Integration tests for analytics and reporting."""
    
    @pytest.fixture
    def authenticated_client(self, client, sample_user_data):
        """Create authenticated client with test user."""
        response = client.post("/auth/register", json=sample_user_data)
        user_data = response.json()
        access_token = user_data["access_token"]
        
        client.headers = {"Authorization": f"Bearer {access_token}"}
        client.user_id = user_data["user"]["id"]
        return client
    
    def test_sales_tracking_and_analytics(self, authenticated_client):
        """Test sales tracking and analytics generation."""
        # Create some test sales events
        sales_events = [
            {
                "product_id": "test-product-1",
                "platform": "facebook",
                "amount": "25.99",
                "currency": "USD",
                "order_id": "fb_order_1"
            },
            {
                "product_id": "test-product-2",
                "platform": "instagram",
                "amount": "45.50",
                "currency": "USD",
                "order_id": "ig_order_1"
            },
            {
                "product_id": "test-product-1",
                "platform": "etsy",
                "amount": "25.99",
                "currency": "USD",
                "order_id": "etsy_order_1"
            }
        ]
        
        # Create sales events
        for sale_data in sales_events:
            response = authenticated_client.post("/sales/", json=sale_data)
            assert response.status_code == 201
        
        # Get analytics dashboard
        response = authenticated_client.get("/analytics/dashboard?days=30")
        assert response.status_code == 200
        
        dashboard_data = response.json()
        assert "total_revenue" in dashboard_data
        assert "total_orders" in dashboard_data
        assert "platform_breakdown" in dashboard_data
        
        # Verify calculations
        assert float(dashboard_data["total_revenue"]) == 97.48
        assert dashboard_data["total_orders"] == 3
        
        # Get platform breakdown
        response = authenticated_client.get("/analytics/platform-breakdown?days=30")
        assert response.status_code == 200
        
        platform_data = response.json()
        assert "facebook" in platform_data
        assert "instagram" in platform_data
        assert "etsy" in platform_data
        
        # Get top products
        response = authenticated_client.get("/analytics/top-products?limit=5")
        assert response.status_code == 200
        
        top_products = response.json()
        assert len(top_products) >= 1


@pytest.mark.integration
class TestPlatformConnectionIntegration:
    """Integration tests for platform connections."""
    
    @pytest.fixture
    def authenticated_client(self, client, sample_user_data):
        """Create authenticated client with test user."""
        response = client.post("/auth/register", json=sample_user_data)
        user_data = response.json()
        access_token = user_data["access_token"]
        
        client.headers = {"Authorization": f"Bearer {access_token}"}
        return client
    
    @patch('app.services.oauth_service.OAuthService')
    def test_oauth_connection_flow(self, mock_oauth_service, authenticated_client):
        """Test OAuth connection flow for platforms."""
        # Mock OAuth service
        mock_oauth_instance = Mock()
        mock_oauth_instance.initiate_oauth_flow = AsyncMock(return_value={
            "authorization_url": "https://facebook.com/oauth/authorize?...",
            "state": "random_state_123"
        })
        mock_oauth_instance.handle_oauth_callback = AsyncMock(return_value={
            "success": True,
            "access_token": "fb_access_token_123",
            "user_info": {"id": "fb_user_123", "name": "Test User"}
        })
        mock_oauth_service.return_value = mock_oauth_instance
        
        # Initiate OAuth flow
        response = authenticated_client.post("/oauth/facebook/connect")
        assert response.status_code == 200
        
        oauth_data = response.json()
        assert "authorization_url" in oauth_data
        assert "state" in oauth_data
        
        # Handle OAuth callback
        callback_data = {
            "code": "facebook_auth_code",
            "state": oauth_data["state"]
        }
        
        response = authenticated_client.post("/oauth/facebook/callback", json=callback_data)
        assert response.status_code == 200
        
        callback_result = response.json()
        assert callback_result["success"] is True
        
        # Get user connections
        response = authenticated_client.get("/oauth/connections")
        assert response.status_code == 200
        
        connections = response.json()
        assert len(connections) >= 1
        assert any(conn["platform"] == "facebook" for conn in connections)
        
        # Test connection validation
        response = authenticated_client.get("/oauth/facebook/status")
        assert response.status_code == 200
        
        status = response.json()
        assert status["connected"] is True


@pytest.mark.integration
class TestErrorHandlingIntegration:
    """Integration tests for error handling across the system."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_validation_error_handling(self, client):
        """Test validation error handling across endpoints."""
        # Test invalid registration data
        invalid_data = {
            "email": "not-an-email",
            "password": "123",  # Too short
            "business_name": "",  # Empty
            "business_type": ""   # Empty
        }
        
        response = client.post("/auth/register", json=invalid_data)
        assert response.status_code == 422
        
        error_data = response.json()
        assert "detail" in error_data
        assert isinstance(error_data["detail"], list)
    
    def test_authentication_error_handling(self, client):
        """Test authentication error handling."""
        # Access protected endpoint without token
        response = client.get("/products/")
        assert response.status_code == 401
        
        # Use invalid token
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/products/", headers=headers)
        assert response.status_code == 401
    
    def test_not_found_error_handling(self, client, sample_user_data):
        """Test 404 error handling."""
        # Register and authenticate user
        response = client.post("/auth/register", json=sample_user_data)
        user_data = response.json()
        headers = {"Authorization": f"Bearer {user_data['access_token']}"}
        
        # Try to access non-existent product
        response = client.get("/products/non-existent-id", headers=headers)
        assert response.status_code == 404
        
        error_data = response.json()
        assert "detail" in error_data
    
    def test_rate_limiting_error_handling(self, client):
        """Test rate limiting error handling."""
        # This would test rate limiting if implemented
        # For now, we'll test that the endpoint exists
        response = client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "password"
        })
        
        # Should get 401 for invalid credentials, not 429 for rate limiting
        assert response.status_code in [401, 429]


@pytest.mark.integration
class TestDatabaseIntegration:
    """Integration tests for database operations."""
    
    def test_database_transactions(self, db_session):
        """Test database transaction handling."""
        # Create user
        user = User(
            email="db_test@example.com",
            password_hash="hashed_password",
            business_name="DB Test Business",
            business_type="Test"
        )
        
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        assert user.id is not None
        
        # Create product for user
        product = Product(
            user_id=user.id,
            title="DB Test Product",
            description="Product for database testing"
        )
        
        db_session.add(product)
        db_session.commit()
        db_session.refresh(product)
        
        assert product.id is not None
        assert product.user_id == user.id
        
        # Test cascade deletion
        db_session.delete(user)
        db_session.commit()
        
        # Product should still exist (depending on cascade settings)
        remaining_product = db_session.query(Product).filter(Product.id == product.id).first()
        # This depends on your cascade configuration
    
    def test_database_constraints(self, db_session):
        """Test database constraint enforcement."""
        # Test unique email constraint
        user1 = User(
            email="unique_test@example.com",
            password_hash="hash1",
            business_name="Business 1",
            business_type="Type 1"
        )
        
        user2 = User(
            email="unique_test@example.com",  # Same email
            password_hash="hash2",
            business_name="Business 2",
            business_type="Type 2"
        )
        
        db_session.add(user1)
        db_session.commit()
        
        db_session.add(user2)
        
        # Should raise integrity error
        with pytest.raises(Exception):  # SQLAlchemy IntegrityError
            db_session.commit()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])