"""
Integration tests for the posts API endpoints.

Tests the REST API for post management, scheduling, and queue monitoring.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.models import User, Product, Post, PostQueue, PlatformConnection
from app.services.posting_service import PostingService
from app.services.queue_processor import SchedulingService


@pytest.fixture
def test_user_with_auth(db_session, test_client):
    """Create a test user and return auth headers."""
    # Create user
    user = User(
        email="test@example.com",
        password_hash="hashed_password",
        business_name="Test Business",
        business_type="Artisan"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    # Mock authentication
    with patch('app.auth.get_current_user', return_value=user):
        yield user


@pytest.fixture
def test_product(db_session, test_user_with_auth):
    """Create a test product."""
    product = Product(
        user_id=test_user_with_auth.id,
        title="Test Product",
        description="A test product for testing"
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    return product


@pytest.fixture
def platform_connections(db_session, test_user_with_auth):
    """Create test platform connections."""
    connections = []
    platforms = ["facebook", "instagram", "etsy"]
    
    for platform in platforms:
        connection = PlatformConnection(
            user_id=test_user_with_auth.id,
            platform=platform,
            integration_type="api",
            auth_method="oauth2",
            access_token="test_token",
            is_active=True
        )
        db_session.add(connection)
        connections.append(connection)
    
    db_session.commit()
    return connections


class TestPostCRUD:
    """Test post CRUD operations."""
    
    def test_create_post_success(self, test_client, test_user_with_auth, test_product):
        """Test successful post creation."""
        post_data = {
            "product_id": test_product.id,
            "title": "Test Post",
            "description": "This is a test post",
            "hashtags": ["#test", "#artisan"],
            "images": ["https://example.com/image1.jpg"],
            "target_platforms": ["facebook", "instagram"],
            "priority": 5
        }
        
        response = test_client.post("/posts/", json=post_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Post"
        assert data["description"] == "This is a test post"
        assert data["hashtags"] == ["#test", "#artisan"]
        assert data["target_platforms"] == ["facebook", "instagram"]
        assert data["status"] == "draft"
        assert data["priority"] == 5
        assert data["user_id"] == test_user_with_auth.id
        assert data["product_id"] == test_product.id
    
    def test_create_post_validation_error(self, test_client, test_user_with_auth):
        """Test post creation with validation errors."""
        post_data = {
            "title": "",  # Empty title should fail
            "description": "This is a test post",
            "hashtags": ["#test"],
            "images": ["https://example.com/image1.jpg"],
            "target_platforms": ["facebook"]
        }
        
        response = test_client.post("/posts/", json=post_data)
        assert response.status_code == 422  # Validation error
    
    def test_create_post_invalid_platform(self, test_client, test_user_with_auth):
        """Test post creation with invalid platform."""
        post_data = {
            "title": "Test Post",
            "description": "This is a test post",
            "hashtags": ["#test"],
            "images": ["https://example.com/image1.jpg"],
            "target_platforms": ["invalid_platform"]
        }
        
        response = test_client.post("/posts/", json=post_data)
        assert response.status_code == 400
        assert "Invalid platforms" in response.json()["detail"]
    
    def test_list_posts(self, test_client, test_user_with_auth, test_product):
        """Test listing posts."""
        # Create a test post first
        post = Post(
            user_id=test_user_with_auth.id,
            product_id=test_product.id,
            title="Test Post",
            description="This is a test post",
            hashtags=["#test"],
            images=["https://example.com/image1.jpg"],
            target_platforms=["facebook"],
            status="draft"
        )
        test_client.app.dependency_overrides[get_db] = lambda: db_session
        db_session = next(get_db())
        db_session.add(post)
        db_session.commit()
        
        response = test_client.get("/posts/")
        
        assert response.status_code == 200
        data = response.json()
        assert "posts" in data
        assert "total" in data
        assert data["total"] >= 1
        assert len(data["posts"]) >= 1
    
    def test_get_post_success(self, test_client, test_user_with_auth, test_product):
        """Test getting a specific post."""
        # Create a test post
        post = Post(
            user_id=test_user_with_auth.id,
            product_id=test_product.id,
            title="Test Post",
            description="This is a test post",
            hashtags=["#test"],
            images=["https://example.com/image1.jpg"],
            target_platforms=["facebook"],
            status="draft"
        )
        db_session = next(get_db())
        db_session.add(post)
        db_session.commit()
        db_session.refresh(post)
        
        response = test_client.get(f"/posts/{post.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == post.id
        assert data["title"] == "Test Post"
    
    def test_get_post_not_found(self, test_client, test_user_with_auth):
        """Test getting a non-existent post."""
        response = test_client.get("/posts/nonexistent_id")
        assert response.status_code == 404
    
    def test_update_post_success(self, test_client, test_user_with_auth, test_product):
        """Test updating a post."""
        # Create a test post
        post = Post(
            user_id=test_user_with_auth.id,
            product_id=test_product.id,
            title="Original Title",
            description="Original description",
            hashtags=["#original"],
            images=["https://example.com/image1.jpg"],
            target_platforms=["facebook"],
            status="draft"
        )
        db_session = next(get_db())
        db_session.add(post)
        db_session.commit()
        db_session.refresh(post)
        
        update_data = {
            "title": "Updated Title",
            "description": "Updated description"
        }
        
        response = test_client.put(f"/posts/{post.id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["description"] == "Updated description"
    
    def test_delete_post_success(self, test_client, test_user_with_auth, test_product):
        """Test deleting a post."""
        # Create a test post
        post = Post(
            user_id=test_user_with_auth.id,
            product_id=test_product.id,
            title="Test Post",
            description="This is a test post",
            hashtags=["#test"],
            images=["https://example.com/image1.jpg"],
            target_platforms=["facebook"],
            status="draft"
        )
        db_session = next(get_db())
        db_session.add(post)
        db_session.commit()
        db_session.refresh(post)
        
        response = test_client.delete(f"/posts/{post.id}")
        
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]


class TestPostPublishing:
    """Test post publishing functionality."""
    
    @patch('app.services.posting_service.PostingService.publish_post_immediately')
    def test_publish_post_success(
        self, mock_publish, test_client, test_user_with_auth, 
        test_product, platform_connections
    ):
        """Test successful immediate post publishing."""
        # Create a test post
        post = Post(
            user_id=test_user_with_auth.id,
            product_id=test_product.id,
            title="Test Post",
            description="This is a test post",
            hashtags=["#test"],
            images=["https://example.com/image1.jpg"],
            target_platforms=["facebook", "instagram"],
            status="draft"
        )
        db_session = next(get_db())
        db_session.add(post)
        db_session.commit()
        db_session.refresh(post)
        
        # Mock successful publishing
        from app.schemas import PostingResult, PostResultResponse
        mock_publish.return_value = PostingResult(
            success=True,
            post_id=post.id,
            results=[
                PostResultResponse(
                    platform="facebook",
                    status="success",
                    post_id="fb_123"
                ),
                PostResultResponse(
                    platform="instagram",
                    status="success",
                    post_id="ig_456"
                )
            ],
            queued_items=[],
            message="Posted to 2/2 platforms"
        )
        
        publish_data = {"post_id": post.id}
        response = test_client.post("/posts/publish", json=publish_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["post_id"] == post.id
        assert len(data["results"]) == 2
        assert all(r["status"] == "success" for r in data["results"])
    
    @patch('app.services.posting_service.PostingService.schedule_post')
    def test_schedule_post_success(
        self, mock_schedule, test_client, test_user_with_auth, 
        test_product, platform_connections
    ):
        """Test successful post scheduling."""
        # Create a test post
        post = Post(
            user_id=test_user_with_auth.id,
            product_id=test_product.id,
            title="Test Post",
            description="This is a test post",
            hashtags=["#test"],
            images=["https://example.com/image1.jpg"],
            target_platforms=["facebook"],
            status="draft"
        )
        db_session = next(get_db())
        db_session.add(post)
        db_session.commit()
        db_session.refresh(post)
        
        # Mock successful scheduling
        from app.schemas import PostingResult
        mock_schedule.return_value = PostingResult(
            success=True,
            post_id=post.id,
            results=[],
            queued_items=["queue_item_123"],
            message="Scheduled for 1 platforms"
        )
        
        future_time = (datetime.utcnow() + timedelta(hours=2)).isoformat()
        schedule_data = {
            "post_id": post.id,
            "scheduled_at": future_time
        }
        
        response = test_client.post("/posts/schedule", json=schedule_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["post_id"] == post.id
        assert len(data["queued_items"]) == 1
    
    def test_schedule_post_past_time(self, test_client, test_user_with_auth, test_product):
        """Test scheduling with past time."""
        # Create a test post
        post = Post(
            user_id=test_user_with_auth.id,
            product_id=test_product.id,
            title="Test Post",
            description="This is a test post",
            hashtags=["#test"],
            images=["https://example.com/image1.jpg"],
            target_platforms=["facebook"],
            status="draft"
        )
        db_session = next(get_db())
        db_session.add(post)
        db_session.commit()
        db_session.refresh(post)
        
        past_time = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        schedule_data = {
            "post_id": post.id,
            "scheduled_at": past_time
        }
        
        response = test_client.post("/posts/schedule", json=schedule_data)
        assert response.status_code == 400
        assert "future" in response.json()["detail"]


class TestQueueManagement:
    """Test queue management endpoints."""
    
    def test_get_queue_status(self, test_client, test_user_with_auth, test_product):
        """Test getting queue status."""
        # Create a test post and queue item
        post = Post(
            user_id=test_user_with_auth.id,
            product_id=test_product.id,
            title="Test Post",
            description="This is a test post",
            hashtags=["#test"],
            images=["https://example.com/image1.jpg"],
            target_platforms=["facebook"],
            status="scheduled"
        )
        db_session = next(get_db())
        db_session.add(post)
        db_session.commit()
        db_session.refresh(post)
        
        queue_item = PostQueue(
            post_id=post.id,
            platform="facebook",
            status="pending",
            scheduled_at=datetime.utcnow() + timedelta(hours=1)
        )
        db_session.add(queue_item)
        db_session.commit()
        
        response = test_client.get("/posts/queue/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "queue_items" in data
        assert "total" in data
        assert data["total"] >= 1
    
    @patch('app.services.posting_service.PostingService.retry_failed_posts')
    def test_retry_failed_posts(self, mock_retry, test_client, test_user_with_auth):
        """Test retrying failed posts."""
        mock_retry.return_value = {"retried": 2, "successful": 0, "failed": 0}
        
        response = test_client.post("/posts/retry-failed?max_age_hours=24")
        
        assert response.status_code == 200
        data = response.json()
        assert "Queued 2 posts for retry" in data["message"]
        assert data["stats"]["retried"] == 2


class TestSchedulingEndpoints:
    """Test scheduling optimization endpoints."""
    
    def test_get_optimal_posting_times(self, test_client, test_user_with_auth):
        """Test getting optimal posting times."""
        response = test_client.get(
            "/posts/scheduling/optimal-times?platforms=facebook&platforms=instagram&days_ahead=7"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "platforms" in data
        assert "optimal_times" in data
        assert "facebook" in data["optimal_times"]
        assert "instagram" in data["optimal_times"]
        assert len(data["optimal_times"]["facebook"]) > 0
    
    def test_get_next_optimal_time(self, test_client, test_user_with_auth):
        """Test getting next optimal time for a platform."""
        response = test_client.get("/posts/scheduling/next-optimal/facebook")
        
        assert response.status_code == 200
        data = response.json()
        assert data["platform"] == "facebook"
        assert "next_optimal_time" in data
        assert "hours_from_now" in data
    
    def test_suggest_staggered_schedule(self, test_client, test_user_with_auth):
        """Test suggesting staggered schedule."""
        platforms = ["facebook", "instagram", "etsy"]
        
        response = test_client.post(
            "/posts/scheduling/staggered?stagger_minutes=20",
            json=platforms
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "schedule" in data
        assert len(data["schedule"]) == 3
        assert "facebook" in data["schedule"]
        assert "instagram" in data["schedule"]
        assert "etsy" in data["schedule"]
    
    def test_get_posting_analysis(self, test_client, test_user_with_auth):
        """Test getting posting pattern analysis."""
        response = test_client.get("/posts/scheduling/analysis?days_back=30")
        
        assert response.status_code == 200
        data = response.json()
        assert "analysis" in data
        assert "recommendations" in data["analysis"]
        assert "optimal_days" in data["analysis"]
        assert "optimal_hours" in data["analysis"]


class TestAdminEndpoints:
    """Test admin endpoints."""
    
    @patch('app.services.posting_service.PostingService.process_queue')
    def test_process_queue_admin(self, mock_process, test_client, test_user_with_auth):
        """Test admin queue processing endpoint."""
        mock_process.return_value = {
            "processed": 5, "successful": 4, "failed": 1, "retried": 0
        }
        
        response = test_client.post("/posts/admin/process-queue?batch_size=10")
        
        assert response.status_code == 200
        data = response.json()
        assert "Processing up to 10 queue items" in data["message"]
    
    def test_get_all_queue_status_admin(self, test_client, test_user_with_auth):
        """Test admin endpoint for getting all queue status."""
        response = test_client.get("/posts/admin/queue/all")
        
        assert response.status_code == 200
        data = response.json()
        assert "queue_items" in data
        assert "total" in data


class TestErrorHandling:
    """Test error handling in posts API."""
    
    def test_create_post_without_auth(self, test_client):
        """Test creating post without authentication."""
        post_data = {
            "title": "Test Post",
            "description": "This is a test post",
            "hashtags": ["#test"],
            "images": ["https://example.com/image1.jpg"],
            "target_platforms": ["facebook"]
        }
        
        # Remove auth mock
        response = test_client.post("/posts/", json=post_data)
        assert response.status_code == 401  # Unauthorized
    
    def test_publish_nonexistent_post(self, test_client, test_user_with_auth):
        """Test publishing a non-existent post."""
        publish_data = {"post_id": "nonexistent_id"}
        response = test_client.post("/posts/publish", json=publish_data)
        assert response.status_code == 400
        assert "not found" in response.json()["detail"]
    
    def test_invalid_pagination_params(self, test_client, test_user_with_auth):
        """Test invalid pagination parameters."""
        response = test_client.get("/posts/?skip=-1")
        assert response.status_code == 422  # Validation error
        
        response = test_client.get("/posts/?limit=0")
        assert response.status_code == 422  # Validation error
        
        response = test_client.get("/posts/?limit=101")
        assert response.status_code == 422  # Validation error