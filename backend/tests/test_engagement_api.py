"""
Tests for Engagement Metrics API Endpoints

This module contains tests for the engagement metrics REST API endpoints,
including collection, retrieval, and dashboard functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models import User, Post, EngagementMetrics
from app.schemas import EngagementDashboardData, MetricsCollectionResult


class TestEngagementAPI:
    """Test cases for engagement metrics API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self, test_user, test_token):
        """Create authentication headers"""
        return {"Authorization": f"Bearer {test_token}"}
    
    @pytest.fixture
    def sample_post_with_results(self, db_session, test_user):
        """Create a sample post with platform results"""
        post = Post(
            id="api_test_post",
            user_id=test_user.id,
            title="API Test Product",
            description="Test product for API testing",
            hashtags=["#api", "#test"],
            images=["https://example.com/api_test.jpg"],
            target_platforms=["facebook", "instagram"],
            status="published",
            results=[
                {
                    "platform": "facebook",
                    "status": "SUCCESS",
                    "post_id": "fb_api_123",
                    "url": "https://facebook.com/post/api123"
                },
                {
                    "platform": "instagram",
                    "status": "SUCCESS",
                    "post_id": "ig_api_123",
                    "url": "https://instagram.com/p/api123"
                }
            ]
        )
        db_session.add(post)
        db_session.commit()
        return post
    
    @pytest.fixture
    def sample_engagement_metrics(self, db_session, test_user, sample_post_with_results):
        """Create sample engagement metrics"""
        metrics = [
            EngagementMetrics(
                id="api_metrics_1",
                user_id=test_user.id,
                post_id=sample_post_with_results.id,
                platform="facebook",
                platform_post_id="fb_api_123",
                likes=200,
                shares=40,
                comments=35,
                views=2500,
                reach=2000,
                engagement_rate=13.75,
                metrics_date=datetime.utcnow() - timedelta(days=1),
                status="active"
            ),
            EngagementMetrics(
                id="api_metrics_2",
                user_id=test_user.id,
                post_id=sample_post_with_results.id,
                platform="instagram",
                platform_post_id="ig_api_123",
                likes=180,
                shares=25,
                comments=30,
                views=2000,
                reach=1800,
                engagement_rate=13.06,
                metrics_date=datetime.utcnow(),
                status="active"
            )
        ]
        db_session.add_all(metrics)
        db_session.commit()
        return metrics
    
    def test_collect_engagement_metrics_success(self, client, auth_headers, test_user):
        """Test successful engagement metrics collection"""
        request_data = {
            "post_ids": ["test_post_1", "test_post_2"],
            "platforms": ["facebook", "instagram"],
            "force_refresh": True
        }
        
        mock_result = MetricsCollectionResult(
            success=True,
            collected_count=2,
            failed_count=0,
            skipped_count=0,
            collected_metrics=["metrics_1", "metrics_2"],
            message="Successfully collected metrics for 2 posts"
        )
        
        with patch('app.routers.engagement.get_engagement_metrics_service') as mock_service:
            mock_service.return_value.collect_metrics_for_user = AsyncMock(return_value=mock_result)
            
            response = client.post(
                "/engagement/collect",
                json=request_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["collected_count"] == 2
            assert data["failed_count"] == 0
            assert len(data["collected_metrics"]) == 2
    
    def test_collect_engagement_metrics_invalid_platform(self, client, auth_headers):
        """Test metrics collection with invalid platform"""
        request_data = {
            "platforms": ["invalid_platform"],
            "force_refresh": False
        }
        
        response = client.post(
            "/engagement/collect",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "Invalid platform specified" in response.json()["detail"]
    
    def test_collect_engagement_metrics_background_task(self, client, auth_headers):
        """Test metrics collection that runs in background"""
        request_data = {}  # Empty request triggers background collection
        
        response = client.post(
            "/engagement/collect",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "background" in data["message"].lower()
    
    def test_get_engagement_dashboard_success(self, client, auth_headers, sample_engagement_metrics):
        """Test successful dashboard data retrieval"""
        mock_dashboard_data = EngagementDashboardData(
            total_engagement={
                "likes": 380,
                "shares": 65,
                "comments": 65,
                "views": 4500,
                "reach": 3800
            },
            engagement_by_platform=[
                {
                    "platform": "facebook",
                    "likes": 200,
                    "shares": 40,
                    "comments": 35,
                    "views": 2500,
                    "reach": 2000,
                    "average_engagement_rate": 13.75,
                    "post_count": 1
                },
                {
                    "platform": "instagram",
                    "likes": 180,
                    "shares": 25,
                    "comments": 30,
                    "views": 2000,
                    "reach": 1800,
                    "average_engagement_rate": 13.06,
                    "post_count": 1
                }
            ],
            engagement_trend=[
                {
                    "date": "2024-01-01",
                    "likes": 200,
                    "shares": 40,
                    "comments": 35,
                    "total_engagement": 275
                }
            ],
            top_performing_posts=[
                {
                    "post_id": "api_test_post",
                    "title": "API Test Product",
                    "platform": "facebook",
                    "likes": 200,
                    "shares": 40,
                    "comments": 35,
                    "total_engagement": 275
                }
            ],
            recent_metrics=[],
            average_engagement_rate=13.4,
            total_reach=3800
        )
        
        with patch('app.routers.engagement.get_engagement_metrics_service') as mock_service:
            mock_service.return_value.get_engagement_dashboard_data = AsyncMock(return_value=mock_dashboard_data)
            
            response = client.get(
                "/engagement/dashboard",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["total_engagement"]["likes"] == 380
            assert data["total_engagement"]["shares"] == 65
            assert len(data["engagement_by_platform"]) == 2
            assert len(data["top_performing_posts"]) == 1
            assert data["average_engagement_rate"] == 13.4
    
    def test_get_engagement_dashboard_with_filters(self, client, auth_headers):
        """Test dashboard data retrieval with date and platform filters"""
        start_date = "2024-01-01T00:00:00"
        end_date = "2024-01-31T23:59:59"
        platforms = ["facebook", "instagram"]
        
        mock_dashboard_data = EngagementDashboardData(
            total_engagement={"likes": 100, "shares": 20, "comments": 15, "views": 1000, "reach": 800},
            engagement_by_platform=[],
            engagement_trend=[],
            top_performing_posts=[],
            recent_metrics=[],
            average_engagement_rate=13.5,
            total_reach=800
        )
        
        with patch('app.routers.engagement.get_engagement_metrics_service') as mock_service:
            mock_service.return_value.get_engagement_dashboard_data = AsyncMock(return_value=mock_dashboard_data)
            
            response = client.get(
                f"/engagement/dashboard?start_date={start_date}&end_date={end_date}&platforms={platforms[0]}&platforms={platforms[1]}",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            # Verify service was called with correct parameters
            mock_service.return_value.get_engagement_dashboard_data.assert_called_once()
    
    def test_get_engagement_dashboard_invalid_date_range(self, client, auth_headers):
        """Test dashboard with invalid date range"""
        start_date = "2024-01-31T00:00:00"
        end_date = "2024-01-01T00:00:00"  # End before start
        
        response = client.get(
            f"/engagement/dashboard?start_date={start_date}&end_date={end_date}",
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "Start date must be before end date" in response.json()["detail"]
    
    def test_get_post_engagement_metrics_success(self, client, auth_headers, sample_post_with_results, sample_engagement_metrics):
        """Test successful retrieval of post engagement metrics"""
        with patch('app.routers.engagement.get_engagement_metrics_service') as mock_service:
            mock_service.return_value.get_metrics_for_post = AsyncMock(return_value=[
                {
                    "id": "api_metrics_1",
                    "platform": "facebook",
                    "likes": 200,
                    "shares": 40,
                    "comments": 35,
                    "views": 2500,
                    "reach": 2000
                },
                {
                    "id": "api_metrics_2",
                    "platform": "instagram",
                    "likes": 180,
                    "shares": 25,
                    "comments": 30,
                    "views": 2000,
                    "reach": 1800
                }
            ])
            
            response = client.get(
                f"/engagement/posts/{sample_post_with_results.id}",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["platform"] == "facebook"
            assert data[1]["platform"] == "instagram"
    
    def test_get_post_engagement_metrics_not_found(self, client, auth_headers):
        """Test retrieval of metrics for non-existent post"""
        response = client.get(
            "/engagement/posts/non_existent_post",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        assert "Post not found" in response.json()["detail"]
    
    def test_collect_post_engagement_metrics_success(self, client, auth_headers, sample_post_with_results):
        """Test successful collection of metrics for specific post"""
        mock_metrics = [
            {
                "id": "collected_metrics_1",
                "platform": "facebook",
                "likes": 250,
                "shares": 50,
                "comments": 40,
                "views": 3000,
                "reach": 2500
            }
        ]
        
        with patch('app.routers.engagement.get_engagement_metrics_service') as mock_service:
            mock_service.return_value.collect_metrics_for_post = AsyncMock(return_value=mock_metrics[0])
            
            response = client.post(
                f"/engagement/posts/{sample_post_with_results.id}/collect?force_refresh=true",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["platform"] == "facebook"
            assert data[0]["likes"] == 250
    
    def test_collect_post_engagement_metrics_no_results(self, client, auth_headers, db_session, test_user):
        """Test collection for post with no published results"""
        post_no_results = Post(
            id="post_no_results",
            user_id=test_user.id,
            title="Post Without Results",
            description="Test post without results",
            hashtags=["#test"],
            images=["https://example.com/test.jpg"],
            target_platforms=["facebook"],
            status="draft",
            results=None
        )
        db_session.add(post_no_results)
        db_session.commit()
        
        response = client.post(
            f"/engagement/posts/{post_no_results.id}/collect",
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "no published results" in response.json()["detail"]
    
    def test_get_engagement_metrics_list_success(self, client, auth_headers, sample_engagement_metrics):
        """Test successful retrieval of paginated engagement metrics"""
        response = client.get(
            "/engagement/metrics?skip=0&limit=10",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "metrics" in data
        assert "total" in data
        assert "skip" in data
        assert "limit" in data
        assert data["skip"] == 0
        assert data["limit"] == 10
    
    def test_get_engagement_metrics_list_with_filters(self, client, auth_headers, sample_engagement_metrics):
        """Test engagement metrics list with filters"""
        response = client.get(
            "/engagement/metrics?platform=facebook&start_date=2024-01-01T00:00:00&end_date=2024-12-31T23:59:59",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "metrics" in data
    
    def test_get_engagement_metrics_list_invalid_platform(self, client, auth_headers):
        """Test metrics list with invalid platform filter"""
        response = client.get(
            "/engagement/metrics?platform=invalid_platform",
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "Invalid platform" in response.json()["detail"]
    
    def test_get_available_platforms(self, client):
        """Test retrieval of available platforms"""
        response = client.get("/engagement/platforms")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert "facebook" in data
        assert "instagram" in data
        assert "pinterest" in data
    
    def test_delete_engagement_metric_success(self, client, auth_headers, sample_engagement_metrics, db_session):
        """Test successful deletion of engagement metric"""
        metric_id = sample_engagement_metrics[0].id
        
        response = client.delete(
            f"/engagement/metrics/{metric_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]
        
        # Verify metric is marked as inactive
        updated_metric = db_session.query(EngagementMetrics).filter(
            EngagementMetrics.id == metric_id
        ).first()
        assert updated_metric.status == "inactive"
    
    def test_delete_engagement_metric_not_found(self, client, auth_headers):
        """Test deletion of non-existent engagement metric"""
        response = client.delete(
            "/engagement/metrics/non_existent_metric",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_get_engagement_summary_success(self, client, auth_headers, sample_engagement_metrics):
        """Test successful retrieval of engagement summary"""
        response = client.get(
            "/engagement/summary?days=30",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "period_days" in data
        assert "total_posts" in data
        assert "total_likes" in data
        assert "total_shares" in data
        assert "total_comments" in data
        assert "total_views" in data
        assert "total_reach" in data
        assert "average_engagement_rate" in data
        assert "active_platforms" in data
        assert "total_engagement" in data
        assert data["period_days"] == 30
    
    def test_get_engagement_summary_custom_period(self, client, auth_headers):
        """Test engagement summary with custom time period"""
        response = client.get(
            "/engagement/summary?days=7",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["period_days"] == 7
    
    def test_get_engagement_summary_invalid_period(self, client, auth_headers):
        """Test engagement summary with invalid time period"""
        response = client.get(
            "/engagement/summary?days=0",
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_unauthorized_access(self, client):
        """Test API endpoints without authentication"""
        endpoints = [
            "/engagement/collect",
            "/engagement/dashboard",
            "/engagement/posts/test_post",
            "/engagement/metrics",
            "/engagement/summary"
        ]
        
        for endpoint in endpoints:
            if endpoint == "/engagement/collect":
                response = client.post(endpoint, json={})
            else:
                response = client.get(endpoint)
            
            assert response.status_code == 401
    
    def test_engagement_metrics_pagination(self, client, auth_headers, db_session, test_user, sample_post_with_results):
        """Test pagination of engagement metrics"""
        # Create multiple metrics for pagination testing
        metrics = []
        for i in range(15):
            metric = EngagementMetrics(
                id=f"pagination_metric_{i}",
                user_id=test_user.id,
                post_id=sample_post_with_results.id,
                platform="facebook",
                platform_post_id=f"fb_pagination_{i}",
                likes=100 + i,
                shares=20 + i,
                comments=15 + i,
                views=1000 + (i * 100),
                reach=800 + (i * 80),
                metrics_date=datetime.utcnow() - timedelta(days=i),
                status="active"
            )
            metrics.append(metric)
        
        db_session.add_all(metrics)
        db_session.commit()
        
        # Test first page
        response = client.get(
            "/engagement/metrics?skip=0&limit=10",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["metrics"]) == 10
        assert data["total"] >= 15
        assert data["skip"] == 0
        assert data["limit"] == 10
        
        # Test second page
        response = client.get(
            "/engagement/metrics?skip=10&limit=10",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["metrics"]) >= 5  # At least the remaining metrics
        assert data["skip"] == 10
        assert data["limit"] == 10


class TestEngagementAPIErrorHandling:
    """Test error handling in engagement API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self, test_user, test_token):
        """Create authentication headers"""
        return {"Authorization": f"Bearer {test_token}"}
    
    def test_collect_metrics_service_error(self, client, auth_headers):
        """Test handling of service errors during metrics collection"""
        request_data = {
            "post_ids": ["test_post"],
            "force_refresh": True
        }
        
        with patch('app.routers.engagement.get_engagement_metrics_service') as mock_service:
            mock_service.return_value.collect_metrics_for_user = AsyncMock(
                side_effect=Exception("Service error")
            )
            
            response = client.post(
                "/engagement/collect",
                json=request_data,
                headers=auth_headers
            )
            
            assert response.status_code == 500
            assert "Failed to collect engagement metrics" in response.json()["detail"]
    
    def test_dashboard_service_error(self, client, auth_headers):
        """Test handling of service errors in dashboard endpoint"""
        with patch('app.routers.engagement.get_engagement_metrics_service') as mock_service:
            mock_service.return_value.get_engagement_dashboard_data = AsyncMock(
                side_effect=Exception("Dashboard error")
            )
            
            response = client.get(
                "/engagement/dashboard",
                headers=auth_headers
            )
            
            assert response.status_code == 500
            assert "Failed to get dashboard data" in response.json()["detail"]
    
    def test_post_metrics_service_error(self, client, auth_headers, db_session, test_user):
        """Test handling of service errors in post metrics endpoint"""
        # Create a test post
        post = Post(
            id="error_test_post",
            user_id=test_user.id,
            title="Error Test Post",
            description="Test post for error handling",
            hashtags=["#error"],
            images=["https://example.com/error.jpg"],
            target_platforms=["facebook"],
            status="published"
        )
        db_session.add(post)
        db_session.commit()
        
        with patch('app.routers.engagement.get_engagement_metrics_service') as mock_service:
            mock_service.return_value.get_metrics_for_post = AsyncMock(
                side_effect=Exception("Post metrics error")
            )
            
            response = client.get(
                f"/engagement/posts/{post.id}",
                headers=auth_headers
            )
            
            assert response.status_code == 500
            assert "Failed to get post metrics" in response.json()["detail"]
    
    def test_metrics_list_database_error(self, client, auth_headers):
        """Test handling of database errors in metrics list endpoint"""
        with patch('app.routers.engagement.db_session') as mock_db:
            mock_db.query.side_effect = Exception("Database error")
            
            response = client.get(
                "/engagement/metrics",
                headers=auth_headers
            )
            
            assert response.status_code == 500
            assert "Failed to get engagement metrics" in response.json()["detail"]