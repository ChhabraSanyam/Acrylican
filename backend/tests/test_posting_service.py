"""
Integration tests for the unified posting service.

Tests the complete posting workflow including post creation, scheduling,
queue management, and result tracking.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.orm import Session

from app.services.posting_service import PostingService
from app.services.platform_service import PlatformService
from app.services.platform_integration import Platform, PostContent, PostResult, PostStatus
from app.models import User, Product, Post, PostQueue, PlatformConnection
from app.schemas import PostCreate, PostingRequest, SchedulePostRequest
from app.database import get_db


@pytest.fixture
def mock_platform_service():
    """Mock platform service for testing."""
    service = Mock(spec=PlatformService)
    service.post_to_platform = AsyncMock()
    service.post_to_multiple_platforms = AsyncMock()
    return service


@pytest.fixture
def posting_service(mock_platform_service):
    """Create posting service with mocked dependencies."""
    return PostingService(platform_service=mock_platform_service)


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        email="test@example.com",
        password_hash="hashed_password",
        business_name="Test Business",
        business_type="Artisan"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_product(db_session, test_user):
    """Create a test product."""
    product = Product(
        user_id=test_user.id,
        title="Test Product",
        description="A test product for testing"
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    return product


@pytest.fixture
def platform_connections(db_session, test_user):
    """Create test platform connections."""
    connections = []
    platforms = ["facebook", "instagram", "etsy"]
    
    for platform in platforms:
        connection = PlatformConnection(
            user_id=test_user.id,
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


class TestPostCreation:
    """Test post creation functionality."""
    
    @pytest.mark.asyncio
    async def test_create_post_success(self, posting_service, db_session, test_user, test_product):
        """Test successful post creation."""
        post_data = PostCreate(
            product_id=test_product.id,
            title="Test Post",
            description="This is a test post",
            hashtags=["#test", "#artisan"],
            images=["https://example.com/image1.jpg"],
            target_platforms=["facebook", "instagram"],
            priority=5
        )
        
        result = await posting_service.create_post(test_user.id, post_data, db_session)
        
        assert result.title == "Test Post"
        assert result.description == "This is a test post"
        assert result.hashtags == ["#test", "#artisan"]
        assert result.target_platforms == ["facebook", "instagram"]
        assert result.status == "draft"
        assert result.priority == 5
        
        # Verify post was saved to database
        post = db_session.query(Post).filter(Post.id == result.id).first()
        assert post is not None
        assert post.user_id == test_user.id
        assert post.product_id == test_product.id
    
    @pytest.mark.asyncio
    async def test_create_post_invalid_user(self, posting_service, db_session):
        """Test post creation with invalid user."""
        post_data = PostCreate(
            title="Test Post",
            description="This is a test post",
            hashtags=["#test"],
            images=["https://example.com/image1.jpg"],
            target_platforms=["facebook"]
        )
        
        with pytest.raises(ValueError, match="User not found"):
            await posting_service.create_post("invalid_user_id", post_data, db_session)
    
    @pytest.mark.asyncio
    async def test_create_post_invalid_product(self, posting_service, db_session, test_user):
        """Test post creation with invalid product."""
        post_data = PostCreate(
            product_id="invalid_product_id",
            title="Test Post",
            description="This is a test post",
            hashtags=["#test"],
            images=["https://example.com/image1.jpg"],
            target_platforms=["facebook"]
        )
        
        with pytest.raises(ValueError, match="Product not found"):
            await posting_service.create_post(test_user.id, post_data, db_session)
    
    @pytest.mark.asyncio
    async def test_create_post_invalid_platforms(self, posting_service, db_session, test_user):
        """Test post creation with invalid platforms."""
        post_data = PostCreate(
            title="Test Post",
            description="This is a test post",
            hashtags=["#test"],
            images=["https://example.com/image1.jpg"],
            target_platforms=["invalid_platform"]
        )
        
        with pytest.raises(ValueError, match="Invalid platforms"):
            await posting_service.create_post(test_user.id, post_data, db_session)


class TestPostManagement:
    """Test post management functionality."""
    
    @pytest.fixture
    def test_post(self, db_session, test_user, test_product):
        """Create a test post."""
        post = Post(
            user_id=test_user.id,
            product_id=test_product.id,
            title="Test Post",
            description="This is a test post",
            hashtags=["#test", "#artisan"],
            images=["https://example.com/image1.jpg"],
            target_platforms=["facebook", "instagram"],
            status="draft"
        )
        db_session.add(post)
        db_session.commit()
        db_session.refresh(post)
        return post
    
    @pytest.mark.asyncio
    async def test_get_post_success(self, posting_service, db_session, test_user, test_post):
        """Test successful post retrieval."""
        result = await posting_service.get_post(test_post.id, test_user.id, db_session)
        
        assert result is not None
        assert result.id == test_post.id
        assert result.title == "Test Post"
        assert result.user_id == test_user.id
    
    @pytest.mark.asyncio
    async def test_get_post_not_found(self, posting_service, db_session, test_user):
        """Test post retrieval with invalid ID."""
        result = await posting_service.get_post("invalid_id", test_user.id, db_session)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_list_posts(self, posting_service, db_session, test_user, test_post):
        """Test post listing."""
        posts, total = await posting_service.list_posts(test_user.id, db_session)
        
        assert total == 1
        assert len(posts) == 1
        assert posts[0].id == test_post.id
    
    @pytest.mark.asyncio
    async def test_delete_post_success(self, posting_service, db_session, test_user, test_post):
        """Test successful post deletion."""
        success = await posting_service.delete_post(test_post.id, test_user.id, db_session)
        
        assert success is True
        
        # Verify post was deleted
        post = db_session.query(Post).filter(Post.id == test_post.id).first()
        assert post is None
    
    @pytest.mark.asyncio
    async def test_delete_post_not_found(self, posting_service, db_session, test_user):
        """Test post deletion with invalid ID."""
        success = await posting_service.delete_post("invalid_id", test_user.id, db_session)
        assert success is False


class TestImmediatePosting:
    """Test immediate posting functionality."""
    
    @pytest.fixture
    def test_post(self, db_session, test_user, test_product):
        """Create a test post."""
        post = Post(
            user_id=test_user.id,
            product_id=test_product.id,
            title="Test Post",
            description="This is a test post",
            hashtags=["#test", "#artisan"],
            images=["https://example.com/image1.jpg"],
            target_platforms=["facebook", "instagram"],
            status="draft"
        )
        db_session.add(post)
        db_session.commit()
        db_session.refresh(post)
        return post
    
    @pytest.mark.asyncio
    async def test_publish_post_immediately_success(
        self, posting_service, mock_platform_service, db_session, 
        test_user, test_post, platform_connections
    ):
        """Test successful immediate posting."""
        # Mock successful posting results
        mock_results = [
            PostResult(
                platform=Platform.FACEBOOK,
                status=PostStatus.SUCCESS,
                post_id="fb_123",
                url="https://facebook.com/post/123"
            ),
            PostResult(
                platform=Platform.INSTAGRAM,
                status=PostStatus.SUCCESS,
                post_id="ig_456",
                url="https://instagram.com/post/456"
            )
        ]
        mock_platform_service.post_to_multiple_platforms.return_value = mock_results
        
        request = PostingRequest(post_id=test_post.id)
        result = await posting_service.publish_post_immediately(request, test_user.id, db_session)
        
        assert result.success is True
        assert result.post_id == test_post.id
        assert len(result.results) == 2
        assert all(r.status == "success" for r in result.results)
        
        # Verify post status was updated
        db_session.refresh(test_post)
        assert test_post.status == "published"
        assert test_post.published_at is not None
        assert test_post.results is not None
        assert len(test_post.results) == 2
    
    @pytest.mark.asyncio
    async def test_publish_post_partial_failure(
        self, posting_service, mock_platform_service, db_session, 
        test_user, test_post, platform_connections
    ):
        """Test posting with partial failures."""
        # Mock mixed results
        mock_results = [
            PostResult(
                platform=Platform.FACEBOOK,
                status=PostStatus.SUCCESS,
                post_id="fb_123",
                url="https://facebook.com/post/123"
            ),
            PostResult(
                platform=Platform.INSTAGRAM,
                status=PostStatus.FAILED,
                error_message="API rate limit exceeded",
                error_code="RATE_LIMIT"
            )
        ]
        mock_platform_service.post_to_multiple_platforms.return_value = mock_results
        
        request = PostingRequest(post_id=test_post.id)
        result = await posting_service.publish_post_immediately(request, test_user.id, db_session)
        
        assert result.success is True  # At least one succeeded
        assert len(result.results) == 2
        assert result.results[0].status == "success"
        assert result.results[1].status == "failed"
        
        # Verify post status
        db_session.refresh(test_post)
        assert test_post.status == "partial"
    
    @pytest.mark.asyncio
    async def test_publish_post_no_connections(
        self, posting_service, db_session, test_user, test_post
    ):
        """Test posting without platform connections."""
        request = PostingRequest(post_id=test_post.id)
        
        with pytest.raises(ValueError, match="Not connected to platforms"):
            await posting_service.publish_post_immediately(request, test_user.id, db_session)


class TestScheduledPosting:
    """Test scheduled posting functionality."""
    
    @pytest.fixture
    def test_post(self, db_session, test_user, test_product):
        """Create a test post."""
        post = Post(
            user_id=test_user.id,
            product_id=test_product.id,
            title="Test Post",
            description="This is a test post",
            hashtags=["#test", "#artisan"],
            images=["https://example.com/image1.jpg"],
            target_platforms=["facebook", "instagram"],
            status="draft"
        )
        db_session.add(post)
        db_session.commit()
        db_session.refresh(post)
        return post
    
    @pytest.mark.asyncio
    async def test_schedule_post_success(
        self, posting_service, db_session, test_user, test_post, platform_connections
    ):
        """Test successful post scheduling."""
        future_time = datetime.utcnow() + timedelta(hours=2)
        request = SchedulePostRequest(
            post_id=test_post.id,
            scheduled_at=future_time
        )
        
        result = await posting_service.schedule_post(request, test_user.id, db_session)
        
        assert result.success is True
        assert result.post_id == test_post.id
        assert len(result.queued_items) == 2  # Two platforms
        
        # Verify post was updated
        db_session.refresh(test_post)
        assert test_post.status == "scheduled"
        assert test_post.scheduled_at == future_time
        
        # Verify queue items were created
        queue_items = db_session.query(PostQueue).filter(
            PostQueue.post_id == test_post.id
        ).all()
        assert len(queue_items) == 2
        assert all(item.status == "pending" for item in queue_items)
        assert all(item.scheduled_at == future_time for item in queue_items)
    
    @pytest.mark.asyncio
    async def test_schedule_post_past_time(
        self, posting_service, db_session, test_user, test_post, platform_connections
    ):
        """Test scheduling with past time."""
        past_time = datetime.utcnow() - timedelta(hours=1)
        request = SchedulePostRequest(
            post_id=test_post.id,
            scheduled_at=past_time
        )
        
        with pytest.raises(ValueError, match="Scheduled time must be in the future"):
            await posting_service.schedule_post(request, test_user.id, db_session)


class TestQueueProcessing:
    """Test queue processing functionality."""
    
    @pytest.fixture
    def test_queue_items(self, db_session, test_user, test_product):
        """Create test queue items."""
        # Create post
        post = Post(
            user_id=test_user.id,
            product_id=test_product.id,
            title="Test Post",
            description="This is a test post",
            hashtags=["#test"],
            images=["https://example.com/image1.jpg"],
            target_platforms=["facebook", "instagram"],
            status="scheduled"
        )
        db_session.add(post)
        db_session.commit()
        db_session.refresh(post)
        
        # Create queue items
        queue_items = []
        for platform in ["facebook", "instagram"]:
            item = PostQueue(
                post_id=post.id,
                platform=platform,
                status="pending",
                scheduled_at=datetime.utcnow() - timedelta(minutes=5)  # Ready to process
            )
            db_session.add(item)
            queue_items.append(item)
        
        db_session.commit()
        return post, queue_items
    
    @pytest.mark.asyncio
    async def test_process_queue_success(
        self, posting_service, mock_platform_service, db_session, 
        test_user, test_queue_items, platform_connections
    ):
        """Test successful queue processing."""
        post, queue_items = test_queue_items
        
        # Mock successful posting
        mock_platform_service.post_to_platform.return_value = PostResult(
            platform=Platform.FACEBOOK,
            status=PostStatus.SUCCESS,
            post_id="fb_123"
        )
        
        stats = await posting_service.process_queue(db_session, batch_size=10)
        
        assert stats["processed"] == 2
        assert stats["successful"] == 2
        assert stats["failed"] == 0
        
        # Verify queue items were updated
        for item in queue_items:
            db_session.refresh(item)
            assert item.status == "completed"
            assert item.completed_at is not None
        
        # Verify post was updated
        db_session.refresh(post)
        assert post.status == "published"
        assert post.published_at is not None
    
    @pytest.mark.asyncio
    async def test_process_queue_with_failures(
        self, posting_service, mock_platform_service, db_session, 
        test_user, test_queue_items, platform_connections
    ):
        """Test queue processing with failures and retries."""
        post, queue_items = test_queue_items
        
        # Mock failed posting
        mock_platform_service.post_to_platform.return_value = PostResult(
            platform=Platform.FACEBOOK,
            status=PostStatus.FAILED,
            error_message="API error",
            error_code="API_ERROR"
        )
        
        stats = await posting_service.process_queue(db_session, batch_size=10)
        
        assert stats["processed"] == 2
        assert stats["successful"] == 0
        assert stats["retried"] == 2  # Should retry failed items
        
        # Verify queue items were updated for retry
        for item in queue_items:
            db_session.refresh(item)
            assert item.status == "pending"  # Reset for retry
            assert item.retry_count == 1
            assert item.scheduled_at > datetime.utcnow()  # Rescheduled for later
    
    @pytest.mark.asyncio
    async def test_get_queue_status(
        self, posting_service, db_session, test_user, test_queue_items
    ):
        """Test queue status retrieval."""
        post, queue_items = test_queue_items
        
        items, total = await posting_service.get_queue_status(
            test_user.id, db_session
        )
        
        assert total == 2
        assert len(items) == 2
        assert all(item.post_id == post.id for item in items)
        assert all(item.status == "pending" for item in items)


class TestRetryLogic:
    """Test retry functionality."""
    
    @pytest.fixture
    def failed_queue_items(self, db_session, test_user, test_product):
        """Create failed queue items for testing."""
        # Create post
        post = Post(
            user_id=test_user.id,
            product_id=test_product.id,
            title="Test Post",
            description="This is a test post",
            hashtags=["#test"],
            images=["https://example.com/image1.jpg"],
            target_platforms=["facebook"],
            status="failed"
        )
        db_session.add(post)
        db_session.commit()
        db_session.refresh(post)
        
        # Create failed queue item
        item = PostQueue(
            post_id=post.id,
            platform="facebook",
            status="failed",
            retry_count=1,
            max_retries=3,
            scheduled_at=datetime.utcnow() - timedelta(hours=1)
        )
        db_session.add(item)
        db_session.commit()
        
        return post, item
    
    @pytest.mark.asyncio
    async def test_retry_failed_posts(
        self, posting_service, db_session, test_user, failed_queue_items
    ):
        """Test retrying failed posts."""
        post, queue_item = failed_queue_items
        
        stats = await posting_service.retry_failed_posts(test_user.id, db_session)
        
        assert stats["retried"] == 1
        
        # Verify queue item was reset for retry
        db_session.refresh(queue_item)
        assert queue_item.status == "pending"
        assert queue_item.retry_count == 2
        assert queue_item.scheduled_at >= datetime.utcnow()


@pytest.mark.asyncio
async def test_end_to_end_posting_workflow(
    posting_service, mock_platform_service, db_session, test_user, test_product
):
    """Test complete end-to-end posting workflow."""
    # Create platform connections
    connection = PlatformConnection(
        user_id=test_user.id,
        platform="facebook",
        integration_type="api",
        auth_method="oauth2",
        access_token="test_token",
        is_active=True
    )
    db_session.add(connection)
    db_session.commit()
    
    # 1. Create post
    post_data = PostCreate(
        product_id=test_product.id,
        title="End-to-End Test Post",
        description="Testing the complete workflow",
        hashtags=["#test", "#e2e"],
        images=["https://example.com/image1.jpg"],
        target_platforms=["facebook"]
    )
    
    post_response = await posting_service.create_post(test_user.id, post_data, db_session)
    assert post_response.status == "draft"
    
    # 2. Schedule post
    future_time = datetime.utcnow() + timedelta(minutes=30)
    schedule_request = SchedulePostRequest(
        post_id=post_response.id,
        scheduled_at=future_time
    )
    
    schedule_result = await posting_service.schedule_post(schedule_request, test_user.id, db_session)
    assert schedule_result.success is True
    assert len(schedule_result.queued_items) == 1
    
    # 3. Simulate queue processing
    # Update queue item to be ready for processing
    queue_item = db_session.query(PostQueue).filter(
        PostQueue.post_id == post_response.id
    ).first()
    queue_item.scheduled_at = datetime.utcnow() - timedelta(minutes=1)
    db_session.commit()
    
    # Mock successful posting
    mock_platform_service.post_to_platform.return_value = PostResult(
        platform=Platform.FACEBOOK,
        status=PostStatus.SUCCESS,
        post_id="fb_123",
        url="https://facebook.com/post/123"
    )
    
    # Process queue
    stats = await posting_service.process_queue(db_session, batch_size=10)
    assert stats["processed"] == 1
    assert stats["successful"] == 1
    
    # 4. Verify final state
    final_post = await posting_service.get_post(post_response.id, test_user.id, db_session)
    assert final_post.status == "published"
    assert final_post.published_at is not None
    assert final_post.results is not None
    assert len(final_post.results) == 1
    assert final_post.results[0].status == "success"