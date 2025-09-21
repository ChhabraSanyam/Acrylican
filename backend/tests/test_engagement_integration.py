"""
Integration Tests for Engagement Metrics

This module contains integration tests that verify the complete engagement metrics
workflow from collection to dashboard display.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.orm import Session

from app.models import User, Post, EngagementMetrics
from app.services.engagement_metrics import get_engagement_metrics_service
from app.services.platform_integration import Platform, PlatformMetrics
from app.schemas import EngagementDashboardData


class TestEngagementMetricsIntegration:
    """Integration tests for engagement metrics functionality"""
    
    @pytest.fixture
    def test_user(self, db_session):
        """Create a test user"""
        user = User(
            id="integration_user_123",
            email="integration@test.com",
            password_hash="hashed_password",
            business_name="Integration Test Business",
            business_type="Artisan"
        )
        db_session.add(user)
        db_session.commit()
        return user
    
    @pytest.fixture
    def test_posts(self, db_session, test_user):
        """Create test posts with results"""
        posts = []
        
        # Post 1 - Facebook and Instagram
        post1 = Post(
            id="integration_post_1",
            user_id=test_user.id,
            title="Test Product 1",
            description="First test product for integration",
            hashtags=["#test1", "#integration"],
            images=["https://example.com/test1.jpg"],
            target_platforms=["facebook", "instagram"],
            status="published",
            results=[
                {
                    "platform": "facebook",
                    "status": "SUCCESS",
                    "post_id": "fb_integration_1",
                    "url": "https://facebook.com/post/1"
                },
                {
                    "platform": "instagram",
                    "status": "SUCCESS",
                    "post_id": "ig_integration_1",
                    "url": "https://instagram.com/p/1"
                }
            ]
        )
        
        # Post 2 - Pinterest only
        post2 = Post(
            id="integration_post_2",
            user_id=test_user.id,
            title="Test Product 2",
            description="Second test product for integration",
            hashtags=["#test2", "#pinterest"],
            images=["https://example.com/test2.jpg"],
            target_platforms=["pinterest"],
            status="published",
            results=[
                {
                    "platform": "pinterest",
                    "status": "SUCCESS",
                    "post_id": "pin_integration_2",
                    "url": "https://pinterest.com/pin/2"
                }
            ]
        )
        
        posts.extend([post1, post2])
        db_session.add_all(posts)
        db_session.commit()
        return posts
    
    @pytest.mark.asyncio
    async def test_complete_metrics_collection_workflow(self, db_session, test_user, test_posts):
        """Test the complete workflow from post creation to metrics collection"""
        service = get_engagement_metrics_service()
        
        # Mock platform metrics for different platforms
        mock_metrics = {
            "fb_integration_1": PlatformMetrics(
                platform=Platform.FACEBOOK,
                post_id="fb_integration_1",
                likes=200,
                shares=40,
                comments=35,
                views=2500,
                reach=2000,
                retrieved_at=datetime.utcnow()
            ),
            "ig_integration_1": PlatformMetrics(
                platform=Platform.INSTAGRAM,
                post_id="ig_integration_1",
                likes=180,
                shares=25,
                comments=30,
                views=2000,
                reach=1800,
                retrieved_at=datetime.utcnow()
            ),
            "pin_integration_2": PlatformMetrics(
                platform=Platform.PINTEREST,
                post_id="pin_integration_2",
                likes=150,
                shares=60,  # Pinterest saves
                comments=20,
                views=1500,
                reach=1200,
                retrieved_at=datetime.utcnow()
            )
        }
        
        def mock_get_metrics(platform, user_id, post_id):
            return mock_metrics.get(post_id)
        
        with patch.object(service.platform_service, 'get_platform_metrics', side_effect=mock_get_metrics):
            # Collect metrics for all user posts
            result = await service.collect_metrics_for_user(user_id=test_user.id)
            
            # Verify collection results
            assert result.success is True
            assert result.collected_count == 3  # 3 platform posts
            assert result.failed_count == 0
            
            # Verify metrics were saved to database
            saved_metrics = db_session.query(EngagementMetrics).filter(
                EngagementMetrics.user_id == test_user.id
            ).all()
            
            assert len(saved_metrics) == 3
            
            # Verify Facebook metrics
            fb_metric = next(m for m in saved_metrics if m.platform == "facebook")
            assert fb_metric.likes == 200
            assert fb_metric.shares == 40
            assert fb_metric.comments == 35
            assert fb_metric.views == 2500
            assert fb_metric.reach == 2000
            assert fb_metric.engagement_rate is not None
            
            # Verify Instagram metrics
            ig_metric = next(m for m in saved_metrics if m.platform == "instagram")
            assert ig_metric.likes == 180
            assert ig_metric.shares == 25
            assert ig_metric.comments == 30
            
            # Verify Pinterest metrics
            pin_metric = next(m for m in saved_metrics if m.platform == "pinterest")
            assert pin_metric.likes == 150
            assert pin_metric.shares == 60  # Pinterest saves
            assert pin_metric.comments == 20
            
            # Test dashboard data generation
            dashboard_data = await service.get_engagement_dashboard_data(user_id=test_user.id)
            
            assert isinstance(dashboard_data, EngagementDashboardData)
            assert dashboard_data.total_engagement["likes"] == 530  # 200 + 180 + 150
            assert dashboard_data.total_engagement["shares"] == 125  # 40 + 25 + 60
            assert dashboard_data.total_engagement["comments"] == 85  # 35 + 30 + 20
            assert dashboard_data.total_engagement["views"] == 6000  # 2500 + 2000 + 1500
            assert dashboard_data.total_engagement["reach"] == 5000  # 2000 + 1800 + 1200
            
            # Verify platform breakdown
            assert len(dashboard_data.engagement_by_platform) == 3
            platform_names = [p["platform"] for p in dashboard_data.engagement_by_platform]
            assert "facebook" in platform_names
            assert "instagram" in platform_names
            assert "pinterest" in platform_names
    
    @pytest.mark.asyncio
    async def test_metrics_collection_with_failures(self, db_session, test_user, test_posts):
        """Test metrics collection when some platforms fail"""
        service = get_engagement_metrics_service()
        
        # Mock platform metrics with some failures
        def mock_get_metrics_with_failures(platform, user_id, post_id):
            if post_id == "fb_integration_1":
                return PlatformMetrics(
                    platform=Platform.FACEBOOK,
                    post_id="fb_integration_1",
                    likes=100,
                    shares=20,
                    comments=15,
                    views=1000,
                    reach=800,
                    retrieved_at=datetime.utcnow()
                )
            elif post_id == "ig_integration_1":
                return None  # Simulate failure
            elif post_id == "pin_integration_2":
                return PlatformMetrics(
                    platform=Platform.PINTEREST,
                    post_id="pin_integration_2",
                    likes=75,
                    shares=30,
                    comments=10,
                    views=750,
                    reach=600,
                    retrieved_at=datetime.utcnow()
                )
            return None
        
        with patch.object(service.platform_service, 'get_platform_metrics', side_effect=mock_get_metrics_with_failures):
            result = await service.collect_metrics_for_user(user_id=test_user.id)
            
            # Should have 2 successful collections and 1 failure
            assert result.success is True
            assert result.collected_count == 2
            assert result.failed_count == 1
            
            # Verify only successful metrics were saved
            saved_metrics = db_session.query(EngagementMetrics).filter(
                EngagementMetrics.user_id == test_user.id
            ).all()
            
            assert len(saved_metrics) == 2
            platforms = [m.platform for m in saved_metrics]
            assert "facebook" in platforms
            assert "pinterest" in platforms
            assert "instagram" not in platforms
    
    @pytest.mark.asyncio
    async def test_metrics_update_with_force_refresh(self, db_session, test_user, test_posts):
        """Test metrics update with force refresh"""
        service = get_engagement_metrics_service()
        
        # First, create some existing metrics
        existing_metric = EngagementMetrics(
            id="existing_metric_123",
            user_id=test_user.id,
            post_id=test_posts[0].id,
            platform="facebook",
            platform_post_id="fb_integration_1",
            likes=50,
            shares=10,
            comments=5,
            views=500,
            reach=400,
            engagement_rate=13.0,
            collection_method="api",
            data_quality="complete",
            metrics_date=datetime.utcnow() - timedelta(hours=2),
            collected_at=datetime.utcnow() - timedelta(hours=2),
            updated_at=datetime.utcnow() - timedelta(hours=2),
            status="active",
            sync_status="synced"
        )
        db_session.add(existing_metric)
        db_session.commit()
        
        # Mock updated platform metrics
        updated_metrics = PlatformMetrics(
            platform=Platform.FACEBOOK,
            post_id="fb_integration_1",
            likes=150,  # Increased
            shares=30,  # Increased
            comments=25,  # Increased
            views=1500,  # Increased
            reach=1200,  # Increased
            retrieved_at=datetime.utcnow()
        )
        
        with patch.object(service.platform_service, 'get_platform_metrics', return_value=updated_metrics):
            # Collect with force refresh
            result = await service.collect_metrics_for_post(
                user_id=test_user.id,
                post_id=test_posts[0].id,
                platform=Platform.FACEBOOK,
                platform_post_id="fb_integration_1",
                force_refresh=True
            )
            
            assert result is not None
            assert result.likes == 150
            assert result.shares == 30
            assert result.comments == 25
            
            # Verify the database was updated
            updated_metric = db_session.query(EngagementMetrics).filter(
                EngagementMetrics.id == existing_metric.id
            ).first()
            
            assert updated_metric.likes == 150
            assert updated_metric.shares == 30
            assert updated_metric.comments == 25
            assert updated_metric.updated_at > existing_metric.updated_at
    
    @pytest.mark.asyncio
    async def test_dashboard_data_with_date_filtering(self, db_session, test_user):
        """Test dashboard data with date range filtering"""
        service = get_engagement_metrics_service()
        
        # Create metrics for different dates
        old_metric = EngagementMetrics(
            id="old_metric",
            user_id=test_user.id,
            post_id="test_post_old",
            platform="facebook",
            platform_post_id="fb_old",
            likes=50,
            shares=10,
            comments=5,
            views=500,
            reach=400,
            engagement_rate=13.0,
            collection_method="api",
            data_quality="complete",
            metrics_date=datetime.utcnow() - timedelta(days=45),  # Outside 30-day range
            collected_at=datetime.utcnow() - timedelta(days=45),
            updated_at=datetime.utcnow() - timedelta(days=45),
            status="active",
            sync_status="synced"
        )
        
        recent_metric = EngagementMetrics(
            id="recent_metric",
            user_id=test_user.id,
            post_id="test_post_recent",
            platform="instagram",
            platform_post_id="ig_recent",
            likes=100,
            shares=20,
            comments=15,
            views=1000,
            reach=800,
            engagement_rate=16.9,
            collection_method="api",
            data_quality="complete",
            metrics_date=datetime.utcnow() - timedelta(days=5),  # Within 30-day range
            collected_at=datetime.utcnow() - timedelta(days=5),
            updated_at=datetime.utcnow() - timedelta(days=5),
            status="active",
            sync_status="synced"
        )
        
        db_session.add_all([old_metric, recent_metric])
        db_session.commit()
        
        # Get dashboard data for last 30 days
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        
        dashboard_data = await service.get_engagement_dashboard_data(
            user_id=test_user.id,
            start_date=start_date,
            end_date=end_date
        )
        
        # Should only include recent metric
        assert dashboard_data.total_engagement["likes"] == 100
        assert dashboard_data.total_engagement["shares"] == 20
        assert dashboard_data.total_engagement["comments"] == 15
        
        # Should only have Instagram platform
        assert len(dashboard_data.engagement_by_platform) == 1
        assert dashboard_data.engagement_by_platform[0]["platform"] == "instagram"
    
    @pytest.mark.asyncio
    async def test_platform_specific_metrics_extraction(self, db_session, test_user):
        """Test extraction of platform-specific metrics"""
        service = get_engagement_metrics_service()
        
        # Test Facebook-specific metrics
        fb_metrics = PlatformMetrics(
            platform=Platform.FACEBOOK,
            post_id="fb_test",
            likes=100,
            shares=20,
            comments=15,
            views=2000,
            reach=1500,
            retrieved_at=datetime.utcnow()
        )
        
        platform_specific = service._extract_platform_specific_metrics(fb_metrics)
        assert "impression_reach_ratio" in platform_specific
        assert platform_specific["impression_reach_ratio"] == 1.33  # 2000/1500
        
        # Test Pinterest-specific metrics (saves)
        pinterest_metrics = PlatformMetrics(
            platform=Platform.PINTEREST,
            post_id="pin_test",
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
    
    def test_engagement_rate_calculations(self):
        """Test various engagement rate calculation scenarios"""
        service = get_engagement_metrics_service()
        
        # Test with reach (preferred denominator)
        metrics_with_reach = PlatformMetrics(
            platform=Platform.FACEBOOK,
            post_id="test",
            likes=100,
            shares=20,
            comments=30,
            views=2000,
            reach=1500,
            retrieved_at=datetime.utcnow()
        )
        
        rate = service._calculate_engagement_rate(metrics_with_reach)
        assert rate == 10.0  # (100+20+30)/1500 * 100
        
        # Test with views only (no reach)
        metrics_with_views = PlatformMetrics(
            platform=Platform.INSTAGRAM,
            post_id="test",
            likes=75,
            shares=15,
            comments=10,
            views=1000,
            reach=None,
            retrieved_at=datetime.utcnow()
        )
        
        rate = service._calculate_engagement_rate(metrics_with_views)
        assert rate == 10.0  # (75+15+10)/1000 * 100
        
        # Test with zero engagement
        metrics_zero_engagement = PlatformMetrics(
            platform=Platform.PINTEREST,
            post_id="test",
            likes=0,
            shares=0,
            comments=0,
            views=1000,
            reach=800,
            retrieved_at=datetime.utcnow()
        )
        
        rate = service._calculate_engagement_rate(metrics_zero_engagement)
        assert rate == 0.0
        
        # Test with no denominator
        metrics_no_denominator = PlatformMetrics(
            platform=Platform.ETSY,
            post_id="test",
            likes=50,
            shares=10,
            comments=5,
            views=None,
            reach=None,
            retrieved_at=datetime.utcnow()
        )
        
        rate = service._calculate_engagement_rate(metrics_no_denominator)
        assert rate is None