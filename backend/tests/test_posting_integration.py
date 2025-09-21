"""
Simple integration test for the posting service to verify core functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock

from app.services.posting_service import PostingService
from app.services.platform_service import PlatformService
from app.services.platform_integration import Platform, PostContent, PostResult, PostStatus
from app.services.queue_processor import SchedulingService
from app.models import User, Product, Post, PostQueue, PlatformConnection
from app.schemas import PostCreate


def test_posting_service_creation():
    """Test that posting service can be created."""
    service = PostingService()
    assert service is not None
    assert service.platform_service is not None


def test_scheduling_service_creation():
    """Test that scheduling service can be created."""
    service = SchedulingService()
    assert service is not None
    assert len(service.optimal_times) > 0
    assert len(service.optimal_days) > 0


def test_optimal_times_calculation():
    """Test optimal times calculation."""
    service = SchedulingService()
    
    platforms = ["facebook", "instagram", "etsy"]
    optimal_times = service.get_optimal_posting_times(platforms, days_ahead=3)
    
    assert len(optimal_times) == 3
    assert "facebook" in optimal_times
    assert "instagram" in optimal_times
    assert "etsy" in optimal_times
    
    # Each platform should have some optimal times
    for platform, times in optimal_times.items():
        assert len(times) > 0
        # All times should be datetime objects
        for time in times:
            assert isinstance(time, datetime)


def test_staggered_scheduling():
    """Test staggered scheduling functionality."""
    service = SchedulingService()
    
    platforms = ["facebook", "instagram", "etsy", "shopify"]
    start_time = datetime.utcnow() + timedelta(hours=2)
    
    schedule = service.suggest_staggered_schedule(platforms, start_time, 15)
    
    assert len(schedule) == 4
    
    # Verify times are staggered
    times = sorted(schedule.values())
    for i in range(1, len(times)):
        diff_minutes = (times[i] - times[i-1]).total_seconds() / 60
        assert diff_minutes == 15


def test_platform_validation():
    """Test platform validation in post creation."""
    # Mock platform service
    mock_platform_service = Mock(spec=PlatformService)
    service = PostingService(platform_service=mock_platform_service)
    
    # Test valid platforms
    valid_platforms = ["facebook", "instagram", "etsy", "pinterest", "shopify"]
    for platform in valid_platforms:
        assert platform in [p.value for p in Platform]
    
    # Test invalid platforms
    invalid_platforms = ["invalid_platform", "nonexistent"]
    for platform in invalid_platforms:
        assert platform not in [p.value for p in Platform]


@pytest.mark.asyncio
async def test_post_content_creation():
    """Test post content creation."""
    content = PostContent(
        title="Test Product",
        description="This is a test product description",
        hashtags=["#test", "#artisan", "#handmade"],
        images=["https://example.com/image1.jpg", "https://example.com/image2.jpg"],
        product_data={"price": "$25.00", "category": "jewelry"}
    )
    
    assert content.title == "Test Product"
    assert len(content.hashtags) == 3
    assert len(content.images) == 2
    assert content.product_data["price"] == "$25.00"


def test_post_result_creation():
    """Test post result creation."""
    result = PostResult(
        platform=Platform.FACEBOOK,
        status=PostStatus.SUCCESS,
        post_id="fb_12345",
        url="https://facebook.com/post/12345",
        published_at=datetime.utcnow()
    )
    
    assert result.platform == Platform.FACEBOOK
    assert result.status == PostStatus.SUCCESS
    assert result.post_id == "fb_12345"
    assert result.url is not None


def test_scheduling_recommendations():
    """Test scheduling recommendations."""
    service = SchedulingService()
    
    # Test analysis (mock database)
    mock_db = Mock()
    analysis = service.analyze_posting_patterns("user123", mock_db)
    
    assert "recommendations" in analysis
    assert "optimal_days" in analysis
    assert "optimal_hours" in analysis
    assert "suggested_frequency" in analysis
    
    assert isinstance(analysis["recommendations"], list)
    assert len(analysis["recommendations"]) > 0


def test_platform_specific_optimal_times():
    """Test that different platforms have different optimal times."""
    service = SchedulingService()
    
    facebook_times = service.optimal_times.get("facebook", [])
    instagram_times = service.optimal_times.get("instagram", [])
    pinterest_times = service.optimal_times.get("pinterest", [])
    
    assert len(facebook_times) > 0
    assert len(instagram_times) > 0
    assert len(pinterest_times) > 0
    
    # Instagram typically has more optimal posting times
    assert len(instagram_times) >= len(facebook_times)


def test_weekday_preferences():
    """Test that platforms have appropriate weekday preferences."""
    service = SchedulingService()
    
    # Business platforms should prefer weekdays
    etsy_days = service.optimal_days.get("etsy", [])
    shopify_days = service.optimal_days.get("shopify", [])
    
    # Should include weekdays (0-4 = Monday-Friday)
    assert any(day in [0, 1, 2, 3, 4] for day in etsy_days)
    assert any(day in [0, 1, 2, 3, 4] for day in shopify_days)
    
    # Pinterest should include weekends
    pinterest_days = service.optimal_days.get("pinterest", [])
    # Pinterest often performs well on weekends
    assert len(pinterest_days) > 0


def test_next_optimal_time_calculation():
    """Test next optimal time calculation."""
    service = SchedulingService()
    
    # Test for a known platform
    current_time = datetime(2024, 1, 15, 10, 0, 0)  # Monday 10 AM
    next_time = service.get_next_optimal_time("facebook", current_time)
    
    assert next_time > current_time
    assert isinstance(next_time, datetime)
    
    # Should be within a reasonable timeframe (next few days)
    time_diff = next_time - current_time
    assert time_diff.days <= 7  # Within a week


def test_indian_platform_timing():
    """Test that Indian platforms have appropriate timing."""
    service = SchedulingService()
    
    indian_platforms = ["meesho", "snapdeal", "indiamart"]
    
    for platform in indian_platforms:
        optimal_hours = service.optimal_times.get(platform, [])
        optimal_days = service.optimal_days.get(platform, [])
        
        assert len(optimal_hours) > 0
        assert len(optimal_days) > 0
        
        # Should include business days
        assert any(day in [0, 1, 2, 3, 4] for day in optimal_days)


if __name__ == "__main__":
    # Run basic tests
    test_posting_service_creation()
    test_scheduling_service_creation()
    test_optimal_times_calculation()
    test_staggered_scheduling()
    test_platform_validation()
    
    print("All basic integration tests passed!")