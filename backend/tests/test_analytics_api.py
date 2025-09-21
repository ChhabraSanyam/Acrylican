"""
Tests for Analytics API endpoints
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import status

from app.main import app
from app.models import User


@pytest.fixture
def client():
    """Test client for API endpoints."""
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    return User(
        id="test_user_123",
        email="test@example.com",
        business_name="Test Business"
    )


@pytest.fixture
def auth_headers():
    """Mock authentication headers."""
    return {"Authorization": "Bearer mock_token"}


@pytest.fixture
def sample_performance_data():
    """Sample platform performance data."""
    return {
        "period_start": "2024-01-01T00:00:00",
        "period_end": "2024-01-31T23:59:59",
        "platforms": [
            {
                "platform": "facebook",
                "sales_metrics": {
                    "total_revenue": 1500.0,
                    "total_orders": 15,
                    "average_order_value": 100.0,
                    "commission_rate": 0.05,
                    "total_commission": 75.0,
                    "net_revenue": 1425.0,
                    "conversion_rate": 1.875
                },
                "engagement_metrics": {
                    "likes": 150,
                    "shares": 25,
                    "comments": 30,
                    "views": 1000,
                    "reach": 800,
                    "engagement_rate": 25.6,
                    "total_posts": 5
                },
                "roi_metrics": {
                    "revenue_per_post": 300.0,
                    "engagement_per_post": 41.0,
                    "cost_per_acquisition": 10.0,
                    "return_on_investment": 150.0
                },
                "top_products": [
                    {"title": "Handmade Vase", "revenue": 500.0, "orders": 5}
                ],
                "performance_score": 85,
                "trend_direction": "up",
                "trend_percentage": 15.5
            }
        ],
        "overall_insights": {
            "best_performing_platform": "facebook",
            "highest_revenue_platform": "facebook",
            "most_engaging_platform": "facebook"
        }
    }


@pytest.fixture
def sample_comparison_data():
    """Sample platform comparison data."""
    return {
        "platform_a": "facebook",
        "platform_b": "instagram",
        "comparison": {
            "revenue_difference": 300.0,
            "revenue_difference_percentage": 25.0,
            "engagement_difference": 50,
            "engagement_difference_percentage": 20.0,
            "roi_difference": 30.0,
            "roi_difference_percentage": 25.0,
            "better_platform": "facebook",
            "recommendation": "Focus more resources on facebook as it generates significantly higher revenue."
        }
    }


@pytest.fixture
def sample_top_products_data():
    """Sample top products data."""
    return {
        "products": [
            {
                "id": "prod_1",
                "title": "Handmade Vase",
                "total_revenue": 900.0,
                "total_orders": 9,
                "total_engagement": 150,
                "platforms": [
                    {
                        "platform": "facebook",
                        "revenue": 500.0,
                        "orders": 5,
                        "engagement": 80,
                        "performance_score": 85
                    }
                ],
                "best_platform": "facebook",
                "performance_score": 85
            }
        ],
        "total_products": 1,
        "period_start": "2024-01-01T00:00:00",
        "period_end": "2024-01-31T23:59:59"
    }


@pytest.fixture
def sample_roi_data():
    """Sample ROI analysis data."""
    return {
        "roi_analysis": [
            {
                "platform": "facebook",
                "investment_metrics": {
                    "time_spent_hours": 10,
                    "advertising_cost": 0,
                    "content_creation_cost": 50,
                    "total_investment": 300
                },
                "return_metrics": {
                    "gross_revenue": 1500,
                    "net_revenue": 1425,
                    "engagement_value": 25,
                    "total_return": 1450
                },
                "roi_percentage": 383.3,
                "roi_category": "excellent",
                "recommendations": [
                    "Excellent ROI on facebook! Consider increasing investment here."
                ]
            }
        ],
        "period_start": "2024-01-01T00:00:00",
        "period_end": "2024-01-31T23:59:59",
        "summary": {
            "best_roi_platform": "facebook",
            "average_roi": 383.3,
            "total_investment": 300,
            "total_return": 1450
        }
    }


class TestAnalyticsAPI:
    """Test cases for Analytics API endpoints."""

    @patch('app.dependencies.get_current_user')
    @patch('app.services.analytics_service.AnalyticsService')
    def test_get_platform_performance_breakdown(
        self, 
        mock_analytics_service, 
        mock_get_user, 
        client, 
        mock_user, 
        auth_headers,
        sample_performance_data
    ):
        """Test platform performance breakdown endpoint."""
        mock_get_user.return_value = mock_user
        mock_service_instance = mock_analytics_service.return_value
        mock_service_instance.get_platform_performance_breakdown = AsyncMock(
            return_value=sample_performance_data
        )
        
        response = client.get(
            "/analytics/platform-performance",
            headers=auth_headers,
            params={
                "start_date": "2024-01-01T00:00:00",
                "end_date": "2024-01-31T23:59:59",
                "platforms": ["facebook", "instagram"],
                "currency": "USD"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "platforms" in data
        assert "overall_insights" in data
        assert len(data["platforms"]) == 1
        assert data["platforms"][0]["platform"] == "facebook"
        assert data["platforms"][0]["performance_score"] == 85

    @patch('app.dependencies.get_current_user')
    @patch('app.services.analytics_service.AnalyticsService')
    def test_get_platform_performance_breakdown_default_dates(
        self, 
        mock_analytics_service, 
        mock_get_user, 
        client, 
        mock_user, 
        auth_headers,
        sample_performance_data
    ):
        """Test platform performance breakdown with default dates."""
        mock_get_user.return_value = mock_user
        mock_service_instance = mock_analytics_service.return_value
        mock_service_instance.get_platform_performance_breakdown = AsyncMock(
            return_value=sample_performance_data
        )
        
        response = client.get(
            "/analytics/platform-performance",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify service was called with default date range (last 30 days)
        mock_service_instance.get_platform_performance_breakdown.assert_called_once()
        call_args = mock_service_instance.get_platform_performance_breakdown.call_args
        
        # Check that start_date is approximately 30 days before end_date
        start_date = call_args[1]['start_date']
        end_date = call_args[1]['end_date']
        date_diff = end_date - start_date
        assert 29 <= date_diff.days <= 31  # Allow for some variance

    @patch('app.dependencies.get_current_user')
    @patch('app.services.analytics_service.AnalyticsService')
    def test_get_platform_comparison(
        self, 
        mock_analytics_service, 
        mock_get_user, 
        client, 
        mock_user, 
        auth_headers,
        sample_comparison_data
    ):
        """Test platform comparison endpoint."""
        mock_get_user.return_value = mock_user
        mock_service_instance = mock_analytics_service.return_value
        mock_service_instance.compare_platforms = AsyncMock(
            return_value=sample_comparison_data
        )
        
        response = client.get(
            "/analytics/platform-comparison",
            headers=auth_headers,
            params={
                "platform_a": "facebook",
                "platform_b": "instagram",
                "currency": "USD"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["platform_a"] == "facebook"
        assert data["platform_b"] == "instagram"
        assert "comparison" in data
        assert data["comparison"]["better_platform"] == "facebook"

    @patch('app.dependencies.get_current_user')
    @patch('app.services.analytics_service.AnalyticsService')
    def test_get_platform_comparison_missing_params(
        self, 
        mock_analytics_service, 
        mock_get_user, 
        client, 
        mock_user, 
        auth_headers
    ):
        """Test platform comparison endpoint with missing required parameters."""
        mock_get_user.return_value = mock_user
        
        response = client.get(
            "/analytics/platform-comparison",
            headers=auth_headers,
            params={"platform_a": "facebook"}  # Missing platform_b
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch('app.dependencies.get_current_user')
    @patch('app.services.analytics_service.AnalyticsService')
    def test_get_top_performing_products(
        self, 
        mock_analytics_service, 
        mock_get_user, 
        client, 
        mock_user, 
        auth_headers,
        sample_top_products_data
    ):
        """Test top performing products endpoint."""
        mock_get_user.return_value = mock_user
        mock_service_instance = mock_analytics_service.return_value
        mock_service_instance.get_top_performing_products = AsyncMock(
            return_value=sample_top_products_data
        )
        
        response = client.get(
            "/analytics/top-products",
            headers=auth_headers,
            params={
                "limit": 10,
                "platforms": ["facebook"],
                "currency": "USD"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "products" in data
        assert "total_products" in data
        assert len(data["products"]) == 1
        assert data["products"][0]["title"] == "Handmade Vase"
        assert data["products"][0]["best_platform"] == "facebook"

    @patch('app.dependencies.get_current_user')
    @patch('app.services.analytics_service.AnalyticsService')
    def test_get_top_performing_products_with_limit(
        self, 
        mock_analytics_service, 
        mock_get_user, 
        client, 
        mock_user, 
        auth_headers,
        sample_top_products_data
    ):
        """Test top performing products endpoint with custom limit."""
        mock_get_user.return_value = mock_user
        mock_service_instance = mock_analytics_service.return_value
        mock_service_instance.get_top_performing_products = AsyncMock(
            return_value=sample_top_products_data
        )
        
        response = client.get(
            "/analytics/top-products",
            headers=auth_headers,
            params={"limit": 5}
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify service was called with correct limit
        mock_service_instance.get_top_performing_products.assert_called_once()
        call_args = mock_service_instance.get_top_performing_products.call_args
        assert call_args[1]['limit'] == 5

    @patch('app.dependencies.get_current_user')
    @patch('app.services.analytics_service.AnalyticsService')
    def test_get_platform_roi_analysis(
        self, 
        mock_analytics_service, 
        mock_get_user, 
        client, 
        mock_user, 
        auth_headers,
        sample_roi_data
    ):
        """Test platform ROI analysis endpoint."""
        mock_get_user.return_value = mock_user
        mock_service_instance = mock_analytics_service.return_value
        mock_service_instance.get_platform_roi_analysis = AsyncMock(
            return_value=sample_roi_data
        )
        
        response = client.get(
            "/analytics/platform-roi",
            headers=auth_headers,
            params={
                "platforms": ["facebook"],
                "currency": "USD"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "roi_analysis" in data
        assert "summary" in data
        assert len(data["roi_analysis"]) == 1
        assert data["roi_analysis"][0]["platform"] == "facebook"
        assert data["roi_analysis"][0]["roi_category"] == "excellent"
        assert data["summary"]["best_roi_platform"] == "facebook"

    @patch('app.dependencies.get_current_user')
    @patch('app.services.analytics_service.AnalyticsService')
    def test_get_analytics_insights(
        self, 
        mock_analytics_service, 
        mock_get_user, 
        client, 
        mock_user, 
        auth_headers
    ):
        """Test analytics insights endpoint."""
        mock_get_user.return_value = mock_user
        mock_service_instance = mock_analytics_service.return_value
        
        sample_insights = {
            "performance_insights": {
                "best_performing_platform": "facebook",
                "total_platforms": 2
            },
            "roi_insights": {
                "best_roi_platform": "facebook",
                "average_roi": 200.0
            },
            "product_insights": {
                "top_product": "Handmade Vase",
                "total_products_revenue": 1500.0
            },
            "recommendations": [
                "Focus on facebook - your best performing platform.",
                "Increase investment in facebook - excellent ROI."
            ]
        }
        
        mock_service_instance.get_analytics_insights = AsyncMock(
            return_value=sample_insights
        )
        
        response = client.get(
            "/analytics/insights",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "performance_insights" in data
        assert "roi_insights" in data
        assert "product_insights" in data
        assert "recommendations" in data
        assert len(data["recommendations"]) == 2

    @patch('app.dependencies.get_current_user')
    @patch('app.services.analytics_service.AnalyticsService')
    def test_get_performance_trends(
        self, 
        mock_analytics_service, 
        mock_get_user, 
        client, 
        mock_user, 
        auth_headers
    ):
        """Test performance trends endpoint."""
        mock_get_user.return_value = mock_user
        mock_service_instance = mock_analytics_service.return_value
        
        sample_trends = {
            "trends": [
                {
                    "date": "2024-01-01",
                    "facebook": {"revenue": 100, "engagement": 50},
                    "instagram": {"revenue": 80, "engagement": 60}
                }
            ]
        }
        
        mock_service_instance.get_performance_trends = AsyncMock(
            return_value=sample_trends
        )
        
        response = client.get(
            "/analytics/performance-trends",
            headers=auth_headers,
            params={
                "group_by": "day",
                "platforms": ["facebook", "instagram"]
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "trends" in data

    @patch('app.dependencies.get_current_user')
    @patch('app.services.analytics_service.AnalyticsService')
    def test_get_performance_trends_invalid_group_by(
        self, 
        mock_analytics_service, 
        mock_get_user, 
        client, 
        mock_user, 
        auth_headers
    ):
        """Test performance trends endpoint with invalid group_by parameter."""
        mock_get_user.return_value = mock_user
        
        response = client.get(
            "/analytics/performance-trends",
            headers=auth_headers,
            params={"group_by": "invalid"}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "Invalid group_by parameter" in data["detail"]

    @patch('app.dependencies.get_current_user')
    @patch('app.services.analytics_service.AnalyticsService')
    def test_analytics_service_error_handling(
        self, 
        mock_analytics_service, 
        mock_get_user, 
        client, 
        mock_user, 
        auth_headers
    ):
        """Test error handling when analytics service raises exception."""
        mock_get_user.return_value = mock_user
        mock_service_instance = mock_analytics_service.return_value
        mock_service_instance.get_platform_performance_breakdown = AsyncMock(
            side_effect=Exception("Service error")
        )
        
        response = client.get(
            "/analytics/platform-performance",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_unauthorized_access(self, client):
        """Test that endpoints require authentication."""
        response = client.get("/analytics/platform-performance")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch('app.dependencies.get_current_user')
    @patch('app.services.analytics_service.AnalyticsService')
    def test_currency_parameter_handling(
        self, 
        mock_analytics_service, 
        mock_get_user, 
        client, 
        mock_user, 
        auth_headers,
        sample_performance_data
    ):
        """Test that currency parameter is properly passed to service."""
        mock_get_user.return_value = mock_user
        mock_service_instance = mock_analytics_service.return_value
        mock_service_instance.get_platform_performance_breakdown = AsyncMock(
            return_value=sample_performance_data
        )
        
        response = client.get(
            "/analytics/platform-performance",
            headers=auth_headers,
            params={"currency": "EUR"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify service was called with EUR currency
        mock_service_instance.get_platform_performance_breakdown.assert_called_once()
        call_args = mock_service_instance.get_platform_performance_breakdown.call_args
        assert call_args[1]['currency'] == "EUR"

    @patch('app.dependencies.get_current_user')
    @patch('app.services.analytics_service.AnalyticsService')
    def test_platforms_parameter_handling(
        self, 
        mock_analytics_service, 
        mock_get_user, 
        client, 
        mock_user, 
        auth_headers,
        sample_performance_data
    ):
        """Test that platforms parameter is properly passed to service."""
        mock_get_user.return_value = mock_user
        mock_service_instance = mock_analytics_service.return_value
        mock_service_instance.get_platform_performance_breakdown = AsyncMock(
            return_value=sample_performance_data
        )
        
        response = client.get(
            "/analytics/platform-performance",
            headers=auth_headers,
            params={"platforms": ["facebook", "instagram"]}
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify service was called with correct platforms
        mock_service_instance.get_platform_performance_breakdown.assert_called_once()
        call_args = mock_service_instance.get_platform_performance_breakdown.call_args
        assert call_args[1]['platforms'] == ["facebook", "instagram"]

    @patch('app.dependencies.get_current_user')
    @patch('app.services.analytics_service.AnalyticsService')
    def test_date_range_validation(
        self, 
        mock_analytics_service, 
        mock_get_user, 
        client, 
        mock_user, 
        auth_headers,
        sample_performance_data
    ):
        """Test that date range parameters are properly validated."""
        mock_get_user.return_value = mock_user
        mock_service_instance = mock_analytics_service.return_value
        mock_service_instance.get_platform_performance_breakdown = AsyncMock(
            return_value=sample_performance_data
        )
        
        # Test with valid date range
        response = client.get(
            "/analytics/platform-performance",
            headers=auth_headers,
            params={
                "start_date": "2024-01-01T00:00:00",
                "end_date": "2024-01-31T23:59:59"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify service was called with correct dates
        mock_service_instance.get_platform_performance_breakdown.assert_called_once()
        call_args = mock_service_instance.get_platform_performance_breakdown.call_args
        assert call_args[1]['start_date'].year == 2024
        assert call_args[1]['start_date'].month == 1
        assert call_args[1]['start_date'].day == 1
        assert call_args[1]['end_date'].year == 2024
        assert call_args[1]['end_date'].month == 1
        assert call_args[1]['end_date'].day == 31