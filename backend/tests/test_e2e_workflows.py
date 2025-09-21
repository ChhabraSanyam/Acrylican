"""
End-to-end workflow tests for the Artisan Promotion Platform.

These tests cover complete user workflows from start to finish,
ensuring all components work together correctly.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import io
from PIL import Image

from app.main import app
from app.models import User, Product, Post, SaleEvent
from app.auth import AuthService


@pytest.mark.e2e


@pytest.mark.e2e
class TestCompleteUserJourney:
    """Test complete user journey from registration to analytics."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def auth_service(self):
        return AuthService()
    
    def create_test_image(self, width=800, height=600):
        """Create a test image for upload."""
        img = Image.new('RGB', (width, height), color='blue')
        output = io.BytesIO()
        img.save(output, format='JPEG')
        output.seek(0)
        return output
    
    @pytest.mark.asyncio
    async def test_complete_artisan_workflow(self, client, auth_service):
        """Test complete workflow: register -> create product -> post -> track sales."""
        
        # Step 1: User Registration
        registration_data = {
            "email": "artisan@example.com",
            "password": "SecurePass123!",
            "business_name": "Artisan Crafts Co",
            "business_type": "Handmade Jewelry"
        }
        
        with patch('app.routers.auth.get_db') as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            # Mock user creation
            mock_user = User(
                id="user-123",
                email=registration_data["email"],
                business_name=registration_data["business_name"],
                business_type=registration_data["business_type"],
                is_active=True
            )
            mock_db.add = Mock()
            mock_db.commit = Mock()
            mock_db.refresh = Mock()
            mock_db.query.return_value.filter.return_value.first.return_value = None  # No existing user
            
            with patch('app.routers.auth.AuthService') as mock_auth_service:
                mock_auth_service.return_value.hash_password.return_value = "hashed_password"
                mock_auth_service.return_value.create_tokens.return_value = {
                    "access_token": "test_access_token",
                    "refresh_token": "test_refresh_token",
                    "token_type": "bearer"
                }
                
                response = client.post("/auth/register", json=registration_data)
                
                # Should successfully register
                assert response.status_code == 201
                response_data = response.json()
                assert "access_token" in response_data
                assert response_data["user"]["email"] == registration_data["email"]
        
        # Step 2: Platform Connection (Mock OAuth)
        access_token = "test_access_token"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        with patch('app.dependencies.get_current_user') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            # Connect to Facebook
            with patch('app.routers.oauth.OAuthService') as mock_oauth:
                mock_oauth.return_value.initiate_oauth_flow.return_value = {
                    "authorization_url": "https://facebook.com/oauth/authorize?...",
                    "state": "random_state"
                }
                
                response = client.post("/oauth/facebook/connect", headers=headers)
                assert response.status_code == 200
                assert "authorization_url" in response.json()
        
        # Step 3: Product Creation with Images
        with patch('app.dependencies.get_current_user', return_value=mock_user):
            with patch('app.routers.products.get_db') as mock_get_db:
                mock_db = Mock()
                mock_get_db.return_value = mock_db
                
                # Mock product creation
                mock_product = Product(
                    id="product-123",
                    user_id="user-123",
                    title="Handmade Silver Ring",
                    description="Beautiful handcrafted silver ring with turquoise stone"
                )
                mock_db.add = Mock()
                mock_db.commit = Mock()
                mock_db.refresh = Mock()
                
                product_data = {
                    "title": "Handmade Silver Ring",
                    "description": "Beautiful handcrafted silver ring with turquoise stone",
                    "category": "Jewelry",
                    "price": "89.99",
                    "materials": ["silver", "turquoise"]
                }
                
                response = client.post("/products/", json=product_data, headers=headers)
                assert response.status_code == 201
        
        # Step 4: Image Upload
        with patch('app.dependencies.get_current_user', return_value=mock_user):
            with patch('app.services.image_processing.ImageProcessingService') as mock_image_service:
                mock_processed_image = {
                    "id": "image-123",
                    "original_url": "https://storage.example.com/original/ring.jpg",
                    "compressed_url": "https://storage.example.com/compressed/ring.jpg",
                    "thumbnail_urls": {
                        "small": "https://storage.example.com/thumb_small/ring.jpg",
                        "medium": "https://storage.example.com/thumb_medium/ring.jpg"
                    },
                    "platform_optimized_urls": {
                        "facebook": "https://storage.example.com/facebook/ring.jpg",
                        "instagram": "https://storage.example.com/instagram/ring.jpg"
                    }
                }
                mock_image_service.return_value.process_image.return_value = mock_processed_image
                
                # Create test image file
                test_image = self.create_test_image()
                files = {"file": ("ring.jpg", test_image, "image/jpeg")}
                
                response = client.post(
                    "/images/upload",
                    files=files,
                    data={"product_id": "product-123", "platforms": "facebook,instagram"},
                    headers=headers
                )
                assert response.status_code == 200
                assert "original_url" in response.json()
        
        # Step 5: Content Generation
        with patch('app.dependencies.get_current_user', return_value=mock_user):
            with patch('app.services.content_generation.ContentGenerationService') as mock_content_service:
                mock_generated_content = {
                    "title": "✨ Stunning Handmade Silver Ring with Turquoise Stone ✨",
                    "description": "Discover the perfect blend of elegance and craftsmanship with this exquisite handmade silver ring. Featuring a beautiful turquoise stone, each piece is uniquely crafted by skilled artisans.",
                    "hashtags": ["#handmade", "#silver", "#turquoise", "#jewelry", "#artisan", "#unique", "#crafted", "#elegant"],
                    "platform_variations": {
                        "facebook": {
                            "title": "✨ Stunning Handmade Silver Ring with Turquoise Stone ✨",
                            "description": "Discover the perfect blend of elegance and craftsmanship..."
                        },
                        "instagram": {
                            "title": "✨ Stunning Handmade Silver Ring ✨",
                            "description": "Perfect blend of elegance and craftsmanship 💍✨"
                        }
                    }
                }
                mock_content_service.return_value.generate_content.return_value = mock_generated_content
                
                content_request = {
                    "product_id": "product-123",
                    "platforms": ["facebook", "instagram"],
                    "tone": "elegant",
                    "target_audience": "jewelry_lovers"
                }
                
                response = client.post("/content/generate", json=content_request, headers=headers)
                assert response.status_code == 200
                generated = response.json()
                assert "title" in generated
                assert "hashtags" in generated
                assert len(generated["hashtags"]) > 0
        
        # Step 6: Post Creation and Scheduling
        with patch('app.dependencies.get_current_user', return_value=mock_user):
            with patch('app.routers.posts.get_db') as mock_get_db:
                mock_db = Mock()
                mock_get_db.return_value = mock_db
                
                mock_post = Post(
                    id="post-123",
                    user_id="user-123",
                    product_id="product-123",
                    platforms=["facebook", "instagram"],
                    content=mock_generated_content,
                    status="scheduled",
                    scheduled_at=datetime.utcnow() + timedelta(hours=2),
                    images=["https://storage.example.com/facebook/ring.jpg"]
                )
                mock_db.add = Mock()
                mock_db.commit = Mock()
                mock_db.refresh = Mock()
                
                post_data = {
                    "product_id": "product-123",
                    "platforms": ["facebook", "instagram"],
                    "content": mock_generated_content,
                    "scheduled_at": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
                    "images": ["image-123"]
                }
                
                response = client.post("/posts/", json=post_data, headers=headers)
                assert response.status_code == 201
                assert response.json()["status"] == "scheduled"
        
        # Step 7: Post Publishing (Simulate scheduled post execution)
        with patch('app.services.posting_service.PostingService') as mock_posting_service:
            mock_posting_result = {
                "success": True,
                "results": {
                    "facebook": {
                        "success": True,
                        "post_id": "fb_123456789",
                        "url": "https://facebook.com/posts/123456789"
                    },
                    "instagram": {
                        "success": True,
                        "post_id": "ig_987654321",
                        "url": "https://instagram.com/p/987654321"
                    }
                }
            }
            mock_posting_service.return_value.publish_post.return_value = mock_posting_result
            
            # Simulate queue processing
            with patch('app.dependencies.get_current_user', return_value=mock_user):
                response = client.post("/posts/post-123/publish", headers=headers)
                assert response.status_code == 200
                result = response.json()
                assert result["success"] is True
                assert "facebook" in result["results"]
                assert "instagram" in result["results"]
        
        # Step 8: Sales Tracking
        with patch('app.dependencies.get_current_user', return_value=mock_user):
            with patch('app.routers.sales.get_db') as mock_get_db:
                mock_db = Mock()
                mock_get_db.return_value = mock_db
                
                # Simulate a sale from the post
                sale_data = {
                    "product_id": "product-123",
                    "platform": "facebook",
                    "amount": "89.99",
                    "currency": "USD",
                    "order_id": "fb_order_123",
                    "customer_info": {
                        "source": "facebook_post",
                        "post_id": "fb_123456789"
                    }
                }
                
                mock_sale = SaleEvent(
                    id="sale-123",
                    user_id="user-123",
                    product_id="product-123",
                    platform="facebook",
                    amount=89.99,
                    currency="USD",
                    order_id="fb_order_123",
                    occurred_at=datetime.utcnow()
                )
                mock_db.add = Mock()
                mock_db.commit = Mock()
                mock_db.refresh = Mock()
                
                response = client.post("/sales/", json=sale_data, headers=headers)
                assert response.status_code == 201
                assert response.json()["amount"] == "89.99"
        
        # Step 9: Analytics Dashboard
        with patch('app.dependencies.get_current_user', return_value=mock_user):
            with patch('app.services.analytics_service.AnalyticsService') as mock_analytics:
                mock_dashboard_data = {
                    "total_revenue": 89.99,
                    "total_orders": 1,
                    "average_order_value": 89.99,
                    "platform_breakdown": {
                        "facebook": {"revenue": 89.99, "orders": 1},
                        "instagram": {"revenue": 0, "orders": 0}
                    },
                    "top_products": [
                        {
                            "id": "product-123",
                            "title": "Handmade Silver Ring",
                            "revenue": 89.99,
                            "orders": 1
                        }
                    ],
                    "engagement_metrics": {
                        "total_likes": 25,
                        "total_shares": 5,
                        "total_comments": 3,
                        "reach": 1250
                    }
                }
                mock_analytics.return_value.get_dashboard_data.return_value = mock_dashboard_data
                
                response = client.get("/analytics/dashboard?days=30", headers=headers)
                assert response.status_code == 200
                dashboard = response.json()
                assert dashboard["total_revenue"] == 89.99
                assert dashboard["total_orders"] == 1
                assert "platform_breakdown" in dashboard
                assert "top_products" in dashboard


@pytest.mark.e2e
class TestContentCreationWorkflow:
    """Test the complete content creation workflow."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.mark.asyncio
    async def test_product_to_post_workflow(self, client):
        """Test workflow from product creation to published post."""
        
        # Mock authenticated user
        mock_user = User(id="user-123", email="test@example.com", is_active=True)
        
        with patch('app.dependencies.get_current_user', return_value=mock_user):
            headers = {"Authorization": "Bearer test_token"}
            
            # Step 1: Create product
            with patch('app.routers.products.get_db') as mock_get_db:
                mock_db = Mock()
                mock_get_db.return_value = mock_db
                
                product_data = {
                    "title": "Ceramic Bowl",
                    "description": "Hand-thrown ceramic bowl with blue glaze",
                    "category": "Pottery",
                    "price": "35.00"
                }
                
                response = client.post("/products/", json=product_data, headers=headers)
                assert response.status_code == 201
            
            # Step 2: Upload product images
            with patch('app.services.image_processing.ImageProcessingService') as mock_image_service:
                mock_image_service.return_value.process_image.return_value = {
                    "id": "image-123",
                    "original_url": "https://example.com/bowl.jpg"
                }
                
                test_image = io.BytesIO()
                Image.new('RGB', (800, 600), color='red').save(test_image, format='JPEG')
                test_image.seek(0)
                
                files = {"file": ("bowl.jpg", test_image, "image/jpeg")}
                response = client.post("/images/upload", files=files, headers=headers)
                assert response.status_code == 200
            
            # Step 3: Generate content
            with patch('app.services.content_generation.ContentGenerationService') as mock_content:
                mock_content.return_value.generate_content.return_value = {
                    "title": "Beautiful Hand-Thrown Ceramic Bowl",
                    "description": "Add elegance to your dining with this stunning ceramic bowl",
                    "hashtags": ["#ceramic", "#handmade", "#pottery", "#bowl"]
                }
                
                content_request = {
                    "product_id": "product-123",
                    "platforms": ["facebook", "instagram"]
                }
                
                response = client.post("/content/generate", json=content_request, headers=headers)
                assert response.status_code == 200
            
            # Step 4: Create and publish post
            with patch('app.routers.posts.get_db') as mock_get_db:
                mock_db = Mock()
                mock_get_db.return_value = mock_db
                
                with patch('app.services.posting_service.PostingService') as mock_posting:
                    mock_posting.return_value.publish_post.return_value = {
                        "success": True,
                        "results": {"facebook": {"success": True, "post_id": "fb_123"}}
                    }
                    
                    post_data = {
                        "product_id": "product-123",
                        "platforms": ["facebook"],
                        "content": {
                            "title": "Beautiful Hand-Thrown Ceramic Bowl",
                            "description": "Add elegance to your dining"
                        }
                    }
                    
                    response = client.post("/posts/", json=post_data, headers=headers)
                    assert response.status_code == 201


@pytest.mark.e2e
class TestPlatformIntegrationWorkflow:
    """Test platform integration workflows."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.mark.asyncio
    async def test_oauth_connection_workflow(self, client):
        """Test OAuth connection workflow for multiple platforms."""
        
        mock_user = User(id="user-123", email="test@example.com", is_active=True)
        headers = {"Authorization": "Bearer test_token"}
        
        platforms = ["facebook", "instagram", "pinterest", "etsy"]
        
        with patch('app.dependencies.get_current_user', return_value=mock_user):
            for platform in platforms:
                with patch('app.routers.oauth.OAuthService') as mock_oauth:
                    # Step 1: Initiate OAuth flow
                    mock_oauth.return_value.initiate_oauth_flow.return_value = {
                        "authorization_url": f"https://{platform}.com/oauth/authorize",
                        "state": f"{platform}_state"
                    }
                    
                    response = client.post(f"/oauth/{platform}/connect", headers=headers)
                    assert response.status_code == 200
                    assert "authorization_url" in response.json()
                    
                    # Step 2: Handle OAuth callback
                    mock_oauth.return_value.handle_oauth_callback.return_value = {
                        "success": True,
                        "access_token": f"{platform}_access_token",
                        "user_info": {"id": f"{platform}_user_123", "name": "Test User"}
                    }
                    
                    callback_data = {
                        "code": f"{platform}_auth_code",
                        "state": f"{platform}_state"
                    }
                    
                    response = client.post(f"/oauth/{platform}/callback", json=callback_data, headers=headers)
                    assert response.status_code == 200
                    assert response.json()["success"] is True


@pytest.mark.e2e
class TestAnalyticsWorkflow:
    """Test analytics and reporting workflows."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.mark.asyncio
    async def test_sales_to_analytics_workflow(self, client):
        """Test workflow from sales events to analytics dashboard."""
        
        mock_user = User(id="user-123", email="test@example.com", is_active=True)
        headers = {"Authorization": "Bearer test_token"}
        
        with patch('app.dependencies.get_current_user', return_value=mock_user):
            # Step 1: Record multiple sales events
            sales_events = [
                {"product_id": "prod-1", "platform": "facebook", "amount": "25.99", "currency": "USD"},
                {"product_id": "prod-2", "platform": "instagram", "amount": "45.50", "currency": "USD"},
                {"product_id": "prod-1", "platform": "etsy", "amount": "25.99", "currency": "USD"}
            ]
            
            with patch('app.routers.sales.get_db') as mock_get_db:
                mock_db = Mock()
                mock_get_db.return_value = mock_db
                
                for sale_data in sales_events:
                    response = client.post("/sales/", json=sale_data, headers=headers)
                    assert response.status_code == 201
            
            # Step 2: Generate analytics dashboard
            with patch('app.services.analytics_service.AnalyticsService') as mock_analytics:
                mock_analytics.return_value.get_dashboard_data.return_value = {
                    "total_revenue": 97.48,
                    "total_orders": 3,
                    "platform_breakdown": {
                        "facebook": {"revenue": 25.99, "orders": 1},
                        "instagram": {"revenue": 45.50, "orders": 1},
                        "etsy": {"revenue": 25.99, "orders": 1}
                    }
                }
                
                response = client.get("/analytics/dashboard", headers=headers)
                assert response.status_code == 200
                dashboard = response.json()
                assert dashboard["total_revenue"] == 97.48
                assert len(dashboard["platform_breakdown"]) == 3


@pytest.mark.e2e
class TestErrorRecoveryWorkflows:
    """Test error handling and recovery in workflows."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.mark.asyncio
    async def test_posting_failure_recovery(self, client):
        """Test recovery from posting failures."""
        
        mock_user = User(id="user-123", email="test@example.com", is_active=True)
        headers = {"Authorization": "Bearer test_token"}
        
        with patch('app.dependencies.get_current_user', return_value=mock_user):
            # Simulate posting failure
            with patch('app.services.posting_service.PostingService') as mock_posting:
                mock_posting.return_value.publish_post.return_value = {
                    "success": False,
                    "results": {
                        "facebook": {"success": False, "error": "API Rate Limit"},
                        "instagram": {"success": True, "post_id": "ig_123"}
                    }
                }
                
                with patch('app.routers.posts.get_db') as mock_get_db:
                    mock_db = Mock()
                    mock_get_db.return_value = mock_db
                    
                    post_data = {
                        "product_id": "product-123",
                        "platforms": ["facebook", "instagram"],
                        "content": {"title": "Test Post"}
                    }
                    
                    response = client.post("/posts/", json=post_data, headers=headers)
                    assert response.status_code == 201
                    
                    # Test retry mechanism
                    response = client.post("/posts/post-123/retry", headers=headers)
                    # Should attempt retry for failed platforms only
                    assert response.status_code == 200


@pytest.mark.e2e
class TestDataConsistencyWorkflows:
    """Test data consistency across workflows."""
    
    @pytest.mark.asyncio
    async def test_cross_service_data_consistency(self):
        """Test data consistency between services."""
        # This would test that data remains consistent
        # across different services and operations
        pass
    
    @pytest.mark.asyncio
    async def test_transaction_rollback_scenarios(self):
        """Test transaction rollback in failure scenarios."""
        # This would test database transaction handling
        # when operations fail partway through
        pass