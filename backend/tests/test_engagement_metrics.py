"""
Tests for Engagement Metrics Service

This module contains comprehensive tests for the engagement metrics collection,
aggregation, and analytics functionality.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.orm import Session

from app.services.engagement_metrics import EngagementMetricsService, get_engagement_metrics_service
from app.services.platform_integration import Platform, PlatformMetrics
from app.models import EngagementMetrics, Post, User, MetricsAggregation
from app.schemas import (
    EngagementMetricsCreate,
    EngagementDashboardData,
    MetricsCollectionResult
)


class TestEngagementMetricsService:
    """Test cases for EngagementMetricsService"""
    
    @pytest.fixture
    def service(self):
        """Create engagement metrics service instance"""
        return EngagementMetricsService()
    
    @pytest.fixture
    def mock_platform_metrics(self):
        """Create mock platform metrics"""
        return PlatformMetrics(
            platform=Platform.FACEBOOK,
            post_id="fb_post_123",
            likes=150,
            shares=25,
            comments=30,
            views=1000,
            reach=800,
            retrieved_at=datetime.utcnow()
        )
    
    @pytest.fixture
    def sample_user(self, db_session):
        """Create a sample user"""
        user = User(
            id="user_123",
            email="test@example.com",
            password_hash="hashed_password",
            business_name="Test Business",
            business_type="Artisan"
        )
        db_session.add(user)
        db_session.commit()
        return user
    
    @pytest.fixture
    def sample_post(self, db_session, sample_user):
        """Create a sample post"""
        post = Post(
            id="post_123",
            user_id=sample_user.id,
            title="Test Product",
            description="Test product description",
            hashtags=["#test", "#product"],
            images=["https://example.com/image.jpg"],
            target_platforms=["facebook", "instagram"],
            status="published",
            results=[
                {
                    "platform": "facebook",
                    "status": "SUCCESS",
                    "post_id": "fb_post_123",
                    "url": "https://facebook.com/post/123"
                }
            ]
        )
        db_session.add(post)
        db_session.commit()
        return post
    
    @pytest.mark.asyncio
    async def test_collect_metrics_for_post_success(self, service, sample_user, sample_post, mock_platform_metrics):
        """Test successful metrics collection for a single post"""
        with patch.object(service.platform_service, 'get_platform_metrics', return_value=mock_platform_metrics):
            with patch('app.services.engagement_metrics.get_db') as mock_get_db:
                mock_db = Mock()
                mock_get_db.return_value.__next__.return_value = mock_db
                mock_db.query.return_value.filter.return_value.first.return_value = None  # No existing metrics
                mock_db.add = Mock()
                mock_db.commit = Mock()
                
                # Mock the saved metrics object
                saved_metrics = EngagementMetrics(
                    id="metrics_123",
                    user_id=sample_user.id,
                    post_id=sample_post.id,
                    platform="facebook",
                    platform_post_id="fb_post_123",
                    likes=150,
                    shares=25,
                    comments=30,
                    views=1000,
                    reach=800,
                    engagement_rate=25.63,
                    collection_method="api",
                    data_quality="complete",
                    metrics_date=datetime.utcnow(),
                    collected_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    status="active",
                    sync_status="synced"
                )
                
                # Mock the _save_metrics method to return the saved metrics
                with patch.object(service, '_save_metrics', return_value=saved_metrics) as mock_save:
                
                    result = await service.collect_metrics_for_post(
                        user_id=sample_user.id,
                        post_id=sample_post.id,
                        platform=Platform.FACEBOOK,
                        platform_post_id="fb_post_123"
                    )
                    
                    assert result is not None
                    assert result.platform == "facebook"
                    assert result.likes == 150
                    assert result.shares == 25
                    assert result.comments == 30
                    assert result.views == 1000
                    assert result.reach == 800
    
    @pytest.mark.asyncio
    async def test_collect_metrics_for_post_no_metrics_available(self, service, sample_user, sample_post):
        """Test metrics collection when platform returns no metrics"""
        with patch.object(service.platform_service, 'get_platform_metrics', return_value=None):
            result = await service.collect_metrics_for_post(
                user_id=sample_user.id,
                post_id=sample_post.id,
                platform=Platform.FACEBOOK,
                platform_post_id="fb_post_123"
            )
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_collect_metrics_for_post_with_existing_metrics(self, service, sample_user, sample_post, mock_platform_metrics):
        """Test metrics collection with existing recent metrics (should use cache)"""
        existing_metrics = EngagementMetrics(
            id="existing_123",
            user_id=sample_user.id,
            post_id=sample_post.id,
            platform="facebook",
            platform_post_id="fb_post_123",
            likes=100,
            shares=20,
            comments=25,
            views=800,
            reach=600,
            collection_method="api",
            data_quality="complete",
            metrics_date=datetime.utcnow() - timedelta(minutes=30),
            collected_at=datetime.utcnow() - timedelta(minutes=30),  # Recent
            updated_at=datetime.utcnow() - timedelta(minutes=30),
            status="active",
            sync_status="synced"
        )
        
        with patch('app.services.engagement_metrics.get_db') as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value.__next__.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = existing_metrics
            
            result = await service.collect_metrics_for_post(
                user_id=sample_user.id,
                post_id=sample_post.id,
                platform=Platform.FACEBOOK,
                platform_post_id="fb_post_123",
                force_refresh=False
            )
            
            assert result is not None
            assert result.likes == 100  # Should use cached metrics
    
    @pytest.mark.asyncio
    async def test_collect_metrics_for_user_success(self, service, sample_user, sample_post):
        """Test bulk metrics collection for a user"""
        # Mock the post results properly
        sample_post.results = [
            {
                "platform": "facebook",
                "status": "SUCCESS",
                "post_id": "fb_post_123",
                "url": "https://facebook.com/post/123"
            }
        ]
        
        with patch('app.services.engagement_metrics.get_db') as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value.__next__.return_value = mock_db
            mock_db.query.return_value.filter.return_value.all.return_value = [sample_post]
            
            with patch.object(service, 'collect_metrics_for_post') as mock_collect:
                mock_metrics = Mock()
                mock_metrics.id = "metrics_123"
                mock_collect.return_value = mock_metrics
                
                with patch.object(service, '_update_aggregations') as mock_update:
                    result = await service.collect_metrics_for_user(
                        user_id=sample_user.id
                    )
                    
                    assert result.success is True
                    assert result.collected_count == 1
                    assert result.failed_count == 0
                    assert len(result.collected_metrics) == 1
                    mock_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_engagement_dashboard_data(self, service, sample_user):
        """Test engagement dashboard data retrieval"""
        with patch('app.services.engagement_metrics.get_db') as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value.__next__.return_value = mock_db
            
            # Mock total metrics query
            mock_total = Mock()
            mock_total.total_likes = 500
            mock_total.total_shares = 100
            mock_total.total_comments = 150
            mock_total.total_views = 5000
            mock_total.total_reach = 4000
            mock_total.avg_engagement_rate = 15.5
            
            # Mock platform metrics query
            mock_platform = Mock()
            mock_platform.platform = "facebook"
            mock_platform.likes = 300
            mock_platform.shares = 60
            mock_platform.comments = 90
            mock_platform.views = 3000
            mock_platform.reach = 2500
            mock_platform.avg_engagement_rate = 16.0
            mock_platform.post_count = 5
            
            # Mock top posts query
            mock_post = Mock()
            mock_post.post_id = "post_123"
            mock_post.title = "Test Product"
            mock_post.platform = "facebook"
            mock_post.likes = 150
            mock_post.shares = 25
            mock_post.comments = 30
            mock_post.views = 1000
            mock_post.engagement_rate = 20.5
            mock_post.total_engagement = 205
            
            # Configure mock queries
            base_query = mock_db.query.return_value.filter.return_value
            base_query.with_entities.return_value.first.return_value = mock_total
            base_query.with_entities.return_value.group_by.return_value.all.return_value = [mock_platform]
            base_query.join.return_value.with_entities.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_post]
            base_query.order_by.return_value.limit.return_value.all.return_value = []
            
            with patch.object(service, '_get_engagement_trend', return_value=[]):
                dashboard_data = await service.get_engagement_dashboard_data(
                    user_id=sample_user.id
                )
                
                assert isinstance(dashboard_data, EngagementDashboardData)
                assert dashboard_data.total_engagement["likes"] == 500
                assert dashboard_data.total_engagement["shares"] == 100
                assert dashboard_data.total_engagement["comments"] == 150
                assert dashboard_data.total_engagement["views"] == 5000
                assert dashboard_data.total_engagement["reach"] == 4000
                assert dashboard_data.average_engagement_rate == 15.5
                assert len(dashboard_data.engagement_by_platform) == 1
                assert dashboard_data.engagement_by_platform[0]["platform"] == "facebook"
                assert len(dashboard_data.top_performing_posts) == 1
    
    def test_calculate_engagement_rate(self, service):
        """Test engagement rate calculation"""
        # Test with reach
        metrics_with_reach = PlatformMetrics(
            platform=Platform.FACEBOOK,
            post_id="test_post",
            likes=100,
            shares=20,
            comments=30,
            views=2000,
            reach=1500,
            retrieved_at=datetime.utcnow()
        )
        
        rate = service._calculate_engagement_rate(metrics_with_reach)
        assert rate == 10.0  # (100+20+30)/1500 * 100 = 10%
        
        # Test with views (no reach)
        metrics_with_views = PlatformMetrics(
            platform=Platform.INSTAGRAM,
            post_id="test_post",
            likes=50,
            shares=10,
            comments=15,
            views=1000,
            reach=None,
            retrieved_at=datetime.utcnow()
        )
        
        rate = service._calculate_engagement_rate(metrics_with_views)
        assert rate == 7.5  # (50+10+15)/1000 * 100 = 7.5%
        
        # Test with no denominator
        metrics_no_denominator = PlatformMetrics(
            platform=Platform.PINTEREST,
            post_id="test_post",
            likes=50,
            shares=10,
            comments=15,
            views=None,
            reach=None,
            retrieved_at=datetime.utcnow()
        )
        
        rate = service._calculate_engagement_rate(metrics_no_denominator)
        assert rate is None
    
    def test_extract_platform_specific_metrics(self, service):
        """Test extraction of platform-specific metrics"""
        # Test Facebook metrics
        fb_metrics = PlatformMetrics(
            platform=Platform.FACEBOOK,
            post_id="fb_post",
            likes=100,
            shares=20,
            comments=30,
            views=2000,
            reach=1500,
            retrieved_at=datetime.utcnow()
        )
        
        platform_specific = service._extract_platform_specific_metrics(fb_metrics)
        assert "impression_reach_ratio" in platform_specific
        assert platform_specific["impression_reach_ratio"] == 1.33  # 2000/1500
        
        # Test Instagram metrics
        ig_metrics = PlatformMetrics(
            platform=Platform.INSTAGRAM,
            post_id="ig_post",
            likes=150,
            shares=10,
            comments=25,
            views=1000,
            reach=800,
            retrieved_at=datetime.utcnow()
        )
        
        platform_specific = service._extract_platform_specific_metrics(ig_metrics)
        assert "like_comment_ratio" in platform_specific
        assert platform_specific["like_comment_ratio"] == 6.0  # 150/25
        
        # Test Pinterest metrics
        pinterest_metrics = PlatformMetrics(
            platform=Platform.PINTEREST,
            post_id="pin_123",
            likes=50,
            shares=75,  # Pinterest saves
            comments=5,
            views=500,
            reach=400,
            retrieved_at=datetime.utcnow()
        )
        
        platform_specific = service._extract_platform_specific_metrics(pinterest_metrics)
        assert "saves" in platform_specific
        assert platform_specific["saves"] == 75
        assert "save_rate" in platform_specific
        assert platform_specific["save_rate"] == 15.0  # 75/500 * 100
    
    @pytest.mark.asyncio
    async def test_get_metrics_for_post(self, service, sample_user, sample_post):
        """Test retrieving metrics for a specific post"""
        sample_metrics = [
            EngagementMetrics(
                id="metrics_1",
                user_id=sample_user.id,
                post_id=sample_post.id,
                platform="facebook",
                platform_post_id="fb_post_123",
                likes=100,
                shares=20,
                comments=25,
                views=1000,
                reach=800,
                collection_method="api",
                data_quality="complete",
                metrics_date=datetime.utcnow(),
                collected_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                status="active",
                sync_status="synced"
            ),
            EngagementMetrics(
                id="metrics_2",
                user_id=sample_user.id,
                post_id=sample_post.id,
                platform="instagram",
                platform_post_id="ig_post_123",
                likes=80,
                shares=15,
                comments=20,
                views=800,
                reach=600,
                collection_method="api",
                data_quality="complete",
                metrics_date=datetime.utcnow(),
                collected_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                status="active",
                sync_status="synced"
            )
        ]
        
        with patch('app.services.engagement_metrics.get_db') as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value.__next__.return_value = mock_db
            mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = sample_metrics
            
            metrics = await service.get_metrics_for_post(
                user_id=sample_user.id,
                post_id=sample_post.id
            )
            
            assert len(metrics) == 2
            assert metrics[0].platform == "facebook"
            assert metrics[1].platform == "instagram"
    
    def test_get_engagement_metrics_service(self):
        """Test service factory function"""
        service = get_engagement_metrics_service()
        assert isinstance(service, EngagementMetricsService)
        
        # Test singleton behavior
        service2 = get_engagement_metrics_service()
        assert service is service2


class TestEngagementMetricsIntegration:
    """Integration tests for engagement metrics functionality"""
    
    @pytest.mark.asyncio
    async def test_full_metrics_collection_workflow(self, db_session):
        """Test complete workflow from post creation to metrics collection"""
        # Create user
        user = User(
            id="integration_user",
            email="integration@example.com",
            password_hash="hashed_password",
            business_name="Integration Test Business",
            business_type="Artisan"
        )
        db_session.add(user)
        
        # Create post with results
        post = Post(
            id="integration_post",
            user_id=user.id,
            title="Integration Test Product",
            description="Test product for integration testing",
            hashtags=["#integration", "#test"],
            images=["https://example.com/test.jpg"],
            target_platforms=["facebook", "instagram"],
            status="published",
            results=[
                {
                    "platform": "facebook",
                    "status": "SUCCESS",
                    "post_id": "fb_integration_123",
                    "url": "https://facebook.com/post/integration123"
                },
                {
                    "platform": "instagram",
                    "status": "SUCCESS",
                    "post_id": "ig_integration_123",
                    "url": "https://instagram.com/p/integration123"
                }
            ]
        )
        db_session.add(post)
        db_session.commit()
        
        # Mock platform metrics
        mock_fb_metrics = PlatformMetrics(
            platform=Platform.FACEBOOK,
            post_id="fb_integration_123",
            likes=200,
            shares=40,
            comments=35,
            views=2500,
            reach=2000,
            retrieved_at=datetime.utcnow()
        )
        
        mock_ig_metrics = PlatformMetrics(
            platform=Platform.INSTAGRAM,
            post_id="ig_integration_123",
            likes=180,
            shares=25,
            comments=30,
            views=2000,
            reach=1800,
            retrieved_at=datetime.utcnow()
        )
        
        service = EngagementMetricsService()
        
        with patch.object(service.platform_service, 'get_platform_metrics') as mock_get_metrics:
            mock_get_metrics.side_effect = [mock_fb_metrics, mock_ig_metrics]
            
            # Collect metrics for user
            result = await service.collect_metrics_for_user(user_id=user.id)
            
            assert result.success is True
            assert result.collected_count == 2
            assert result.failed_count == 0
            
            # Verify metrics were saved to database
            saved_metrics = db_session.query(EngagementMetrics).filter(
                EngagementMetrics.user_id == user.id
            ).all()
            
            assert len(saved_metrics) == 2
            
            # Check Facebook metrics
            fb_metric = next(m for m in saved_metrics if m.platform == "facebook")
            assert fb_metric.likes == 200
            assert fb_metric.shares == 40
            assert fb_metric.comments == 35
            assert fb_metric.views == 2500
            assert fb_metric.reach == 2000
            assert fb_metric.engagement_rate is not None
            
            # Check Instagram metrics
            ig_metric = next(m for m in saved_metrics if m.platform == "instagram")
            assert ig_metric.likes == 180
            assert ig_metric.shares == 25
            assert ig_metric.comments == 30
            assert ig_metric.views == 2000
            assert ig_metric.reach == 1800
            assert ig_metric.engagement_rate is not None
    
    @pytest.mark.asyncio
    async def test_dashboard_data_with_real_database(self, db_session):
        """Test dashboard data generation with real database queries"""
        # Create user
        user = User(
            id="dashboard_user",
            email="dashboard@example.com",
            password_hash="hashed_password",
            business_name="Dashboard Test Business",
            business_type="Artisan"
        )
        db_session.add(user)
        
        # Create posts
        post1 = Post(
            id="dashboard_post_1",
            user_id=user.id,
            title="Dashboard Test Product 1",
            description="First test product",
            hashtags=["#test1"],
            images=["https://example.com/test1.jpg"],
            target_platforms=["facebook"],
            status="published"
        )
        
        post2 = Post(
            id="dashboard_post_2",
            user_id=user.id,
            title="Dashboard Test Product 2",
            description="Second test product",
            hashtags=["#test2"],
            images=["https://example.com/test2.jpg"],
            target_platforms=["instagram"],
            status="published"
        )
        
        db_session.add_all([post1, post2])
        
        # Create engagement metrics
        metrics1 = EngagementMetrics(
            id="dashboard_metrics_1",
            user_id=user.id,
            post_id=post1.id,
            platform="facebook",
            platform_post_id="fb_dashboard_1",
            likes=150,
            shares=30,
            comments=25,
            views=1500,
            reach=1200,
            engagement_rate=17.08,
            metrics_date=datetime.utcnow() - timedelta(days=1),
            status="active"
        )
        
        metrics2 = EngagementMetrics(
            id="dashboard_metrics_2",
            user_id=user.id,
            post_id=post2.id,
            platform="instagram",
            platform_post_id="ig_dashboard_2",
            likes=120,
            shares=20,
            comments=18,
            views=1200,
            reach=1000,
            engagement_rate=15.8,
            metrics_date=datetime.utcnow(),
            status="active"
        )
        
        db_session.add_all([metrics1, metrics2])
        db_session.commit()
        
        # Get dashboard data
        service = EngagementMetricsService()
        dashboard_data = await service.get_engagement_dashboard_data(user_id=user.id)
        
        # Verify dashboard data
        assert dashboard_data.total_engagement["likes"] == 270
        assert dashboard_data.total_engagement["shares"] == 50
        assert dashboard_data.total_engagement["comments"] == 43
        assert dashboard_data.total_engagement["views"] == 2700
        assert dashboard_data.total_engagement["reach"] == 2200
        
        assert len(dashboard_data.engagement_by_platform) == 2
        
        # Check platform breakdown
        fb_platform = next(p for p in dashboard_data.engagement_by_platform if p["platform"] == "facebook")
        assert fb_platform["likes"] == 150
        assert fb_platform["post_count"] == 1
        
        ig_platform = next(p for p in dashboard_data.engagement_by_platform if p["platform"] == "instagram")
        assert ig_platform["likes"] == 120
        assert ig_platform["post_count"] == 1