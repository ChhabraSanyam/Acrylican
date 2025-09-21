"""
Tests for the Analytics Service
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.orm import Session

from app.services.analytics_service import AnalyticsService
from app.models import SaleEvent, EngagementMetrics, Post, User
from app.schemas import PlatformSalesBreakdown


@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def analytics_service(mock_db):
    """Analytics service instance with mocked dependencies."""
    with patch('app.services.analytics_service.SalesTrackingService') as mock_sales_service, \
         patch('app.services.analytics_service.get_engagement_metrics_service') as mock_engagement_service:
        
        service = AnalyticsService(mock_db)
        service.sales_service = mock_sales_service.return_value
        service.engagement_service = mock_engagement_service.return_value
        return service


@pytest.fixture
def sample_dates():
    """Sample date range for testing."""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    return start_date, end_date


@pytest.fixture
def mock_sales_breakdown():
    """Mock sales breakdown data."""
    return [
        PlatformSalesBreakdown(
            platform="facebook",
            total_revenue=1500.0,
            total_orders=15,
            average_order_value=100.0,
            commission_rate=0.05,
            total_commission=75.0,
            net_revenue=1425.0,
            top_products=[
                {"title": "Handmade Vase", "revenue": 500.0, "orders": 5}
            ]
        ),
        PlatformSalesBreakdown(
            platform="instagram",
            total_revenue=1200.0,
            total_orders=12,
            average_order_value=100.0,
            commission_rate=0.03,
            total_commission=36.0,
            net_revenue=1164.0,
            top_products=[
                {"title": "Ceramic Bowl", "revenue": 400.0, "orders": 4}
            ]
        )
    ]


@pytest.fixture
def mock_engagement_data():
    """Mock engagement dashboard data."""
    return Mock(
        engagement_by_platform=[
            {
                "platform": "facebook",
                "likes": 150,
                "shares": 25,
                "comments": 30,
                "views": 1000,
                "reach": 800,
                "average_engagement_rate": 25.6,
                "post_count": 5
            },
            {
                "platform": "instagram",
                "likes": 200,
                "shares": 15,
                "comments": 40,
                "views": 1200,
                "reach": 900,
                "average_engagement_rate": 28.3,
                "post_count": 6
            }
        ]
    )


class TestAnalyticsService:
    """Test cases for AnalyticsService."""

    @pytest.mark.asyncio
    async def test_get_platform_performance_breakdown(
        self, 
        analytics_service, 
        sample_dates, 
        mock_sales_breakdown, 
        mock_engagement_data
    ):
        """Test platform performance breakdown calculation."""
        start_date, end_date = sample_dates
        user_id = "test_user_123"
        
        # Mock service responses
        analytics_service.sales_service.get_platform_breakdown = AsyncMock(return_value=mock_sales_breakdown)
        analytics_service.engagement_service.get_engagement_dashboard_data = AsyncMock(return_value=mock_engagement_data)
        analytics_service._get_post_counts_by_platform = AsyncMock(return_value={"facebook": 5, "instagram": 6})
        analytics_service._calculate_trend = AsyncMock(return_value=("up", 15.5))
        
        result = await analytics_service.get_platform_performance_breakdown(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            currency="USD"
        )
        
        # Verify structure
        assert "period_start" in result
        assert "period_end" in result
        assert "platforms" in result
        assert "overall_insights" in result
        
        # Verify platform data
        platforms = result["platforms"]
        assert len(platforms) == 2
        
        facebook_platform = next(p for p in platforms if p["platform"] == "facebook")
        assert facebook_platform["sales_metrics"]["total_revenue"] == 1500.0
        assert facebook_platform["engagement_metrics"]["likes"] == 150
        assert facebook_platform["roi_metrics"]["revenue_per_post"] == 300.0  # 1500 / 5
        assert facebook_platform["performance_score"] > 0
        assert facebook_platform["trend_direction"] == "up"
        
        # Verify service calls
        analytics_service.sales_service.get_platform_breakdown.assert_called_once_with(
            user_id, start_date, end_date, "USD"
        )
        analytics_service.engagement_service.get_engagement_dashboard_data.assert_called_once_with(
            user_id, start_date, end_date, None
        )

    @pytest.mark.asyncio
    async def test_compare_platforms(self, analytics_service, sample_dates):
        """Test platform comparison functionality."""
        start_date, end_date = sample_dates
        user_id = "test_user_123"
        
        # Mock performance data
        mock_performance_data = {
            "platforms": [
                {
                    "platform": "facebook",
                    "sales_metrics": {"total_revenue": 1500.0},
                    "engagement_metrics": {"likes": 150, "shares": 25, "comments": 30, "engagement_rate": 25.0},
                    "roi_metrics": {"return_on_investment": 150.0},
                    "performance_score": 85
                },
                {
                    "platform": "instagram", 
                    "sales_metrics": {"total_revenue": 1200.0},
                    "engagement_metrics": {"likes": 200, "shares": 15, "comments": 40, "engagement_rate": 28.0},
                    "roi_metrics": {"return_on_investment": 120.0},
                    "performance_score": 78
                }
            ]
        }
        
        analytics_service.get_platform_performance_breakdown = AsyncMock(return_value=mock_performance_data)
        
        result = await analytics_service.compare_platforms(
            user_id=user_id,
            platform_a="facebook",
            platform_b="instagram",
            start_date=start_date,
            end_date=end_date
        )
        
        # Verify comparison structure
        assert result["platform_a"] == "facebook"
        assert result["platform_b"] == "instagram"
        assert "comparison" in result
        
        comparison = result["comparison"]
        assert comparison["revenue_difference"] == 300.0  # 1500 - 1200
        assert comparison["revenue_difference_percentage"] == 25.0  # 300/1200 * 100
        assert comparison["better_platform"] == "facebook"  # Higher performance score
        assert "recommendation" in comparison

    @pytest.mark.asyncio
    async def test_get_top_performing_products(self, analytics_service, mock_db, sample_dates):
        """Test top performing products identification."""
        start_date, end_date = sample_dates
        user_id = "test_user_123"
        
        # Mock database query results
        mock_sales_results = [
            Mock(
                product_id="prod_1",
                product_title="Handmade Vase",
                platform="facebook",
                revenue=Decimal("500.0"),
                orders=5,
                quantity=5
            ),
            Mock(
                product_id="prod_1",
                product_title="Handmade Vase", 
                platform="instagram",
                revenue=Decimal("400.0"),
                orders=4,
                quantity=4
            )
        ]
        
        mock_engagement_results = [
            Mock(
                post_id="post_1",
                title="Handmade Vase Post",
                platform="facebook",
                total_engagement=80
            )
        ]
        
        # Mock database queries
        mock_db.query.return_value.filter.return_value.group_by.return_value.all.return_value = mock_sales_results
        mock_db.query.return_value.join.return_value.filter.return_value.group_by.return_value.all.return_value = mock_engagement_results
        
        result = await analytics_service.get_top_performing_products(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            limit=10
        )
        
        # Verify structure
        assert "products" in result
        assert "total_products" in result
        
        products = result["products"]
        assert len(products) == 1
        
        product = products[0]
        assert product["title"] == "Handmade Vase"
        assert product["total_revenue"] == 900.0  # 500 + 400
        assert product["total_orders"] == 9  # 5 + 4
        assert len(product["platforms"]) == 2
        assert product["best_platform"] != ""

    @pytest.mark.asyncio
    async def test_get_platform_roi_analysis(self, analytics_service, sample_dates, mock_sales_breakdown):
        """Test ROI analysis calculation."""
        start_date, end_date = sample_dates
        user_id = "test_user_123"
        
        analytics_service.sales_service.get_platform_breakdown = AsyncMock(return_value=mock_sales_breakdown)
        analytics_service._get_post_counts_by_platform = AsyncMock(return_value={"facebook": 5, "instagram": 6})
        
        result = await analytics_service.get_platform_roi_analysis(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )
        
        # Verify structure
        assert "roi_analysis" in result
        assert "summary" in result
        
        roi_analysis = result["roi_analysis"]
        assert len(roi_analysis) == 2
        
        facebook_roi = next(r for r in roi_analysis if r["platform"] == "facebook")
        assert facebook_roi["investment_metrics"]["total_investment"] > 0
        assert facebook_roi["return_metrics"]["net_revenue"] == 1425.0
        assert facebook_roi["roi_percentage"] > 0
        assert facebook_roi["roi_category"] in ["excellent", "good", "average", "poor"]
        assert len(facebook_roi["recommendations"]) > 0

    @pytest.mark.asyncio
    async def test_get_analytics_insights(self, analytics_service, sample_dates):
        """Test analytics insights generation."""
        start_date, end_date = sample_dates
        user_id = "test_user_123"
        
        # Mock all required methods
        analytics_service.get_platform_performance_breakdown = AsyncMock(return_value={"platforms": []})
        analytics_service.get_platform_roi_analysis = AsyncMock(return_value={"roi_analysis": []})
        analytics_service.get_top_performing_products = AsyncMock(return_value={"products": []})
        
        result = await analytics_service.get_analytics_insights(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )
        
        # Verify structure
        assert "performance_insights" in result
        assert "roi_insights" in result
        assert "product_insights" in result
        assert "recommendations" in result

    def test_calculate_performance_score(self, analytics_service):
        """Test performance score calculation."""
        mock_sales_data = Mock(
            total_revenue=1000.0,
            total_orders=10
        )
        
        mock_engagement_data = {
            "likes": 100,
            "shares": 20,
            "comments": 30,
            "average_engagement_rate": 15.0
        }
        
        post_count = 5
        
        score = analytics_service._calculate_performance_score(
            mock_sales_data, mock_engagement_data, post_count
        )
        
        assert isinstance(score, int)
        assert 0 <= score <= 100

    def test_calculate_conversion_rate(self, analytics_service):
        """Test conversion rate calculation."""
        # Test normal case
        rate = analytics_service._calculate_conversion_rate(orders=10, reach=1000)
        assert rate == 1.0  # 10/1000 * 100
        
        # Test zero reach
        rate = analytics_service._calculate_conversion_rate(orders=10, reach=0)
        assert rate == 0.0

    def test_calculate_cpa(self, analytics_service):
        """Test cost per acquisition calculation."""
        # Test normal case
        cpa = analytics_service._calculate_cpa(revenue=1000.0, orders=10)
        assert cpa == 10.0  # (1000 * 0.1) / 10
        
        # Test zero orders
        cpa = analytics_service._calculate_cpa(revenue=1000.0, orders=0)
        assert cpa == 0.0

    def test_calculate_simple_roi(self, analytics_service):
        """Test simple ROI calculation."""
        # Test positive ROI
        roi = analytics_service._calculate_simple_roi(net_revenue=500.0, post_count=5)
        expected_investment = 5 * 35  # 175
        expected_roi = ((500 - 175) / 175) * 100  # ~185.7%
        assert abs(roi - expected_roi) < 0.1
        
        # Test zero posts
        roi = analytics_service._calculate_simple_roi(net_revenue=500.0, post_count=0)
        assert roi == 0.0

    def test_calculate_product_platform_score(self, analytics_service):
        """Test product platform score calculation."""
        platform_data = {
            "revenue": 500.0,
            "orders": 5,
            "engagement": 100
        }
        
        score = analytics_service._calculate_product_platform_score(platform_data)
        
        assert isinstance(score, int)
        assert score >= 0

    def test_generate_performance_insights(self, analytics_service):
        """Test performance insights generation."""
        platforms = [
            {
                "platform": "facebook",
                "performance_score": 85,
                "sales_metrics": {"total_revenue": 1500.0},
                "engagement_metrics": {"engagement_rate": 25.6}
            },
            {
                "platform": "instagram",
                "performance_score": 78,
                "sales_metrics": {"total_revenue": 1200.0},
                "engagement_metrics": {"engagement_rate": 28.3}
            }
        ]
        
        insights = analytics_service._generate_performance_insights(platforms)
        
        assert insights["best_performing_platform"] == "facebook"
        assert insights["highest_revenue_platform"] == "facebook"
        assert insights["most_engaging_platform"] == "instagram"
        assert insights["total_platforms"] == 2
        assert insights["average_performance_score"] == 81.5

    def test_generate_roi_insights(self, analytics_service):
        """Test ROI insights generation."""
        roi_analysis = [
            {
                "platform": "facebook",
                "roi_percentage": 200.0,
                "investment_metrics": {"total_investment": 300.0},
                "return_metrics": {"total_return": 900.0}
            },
            {
                "platform": "instagram",
                "roi_percentage": 150.0,
                "investment_metrics": {"total_investment": 250.0},
                "return_metrics": {"total_return": 625.0}
            }
        ]
        
        insights = analytics_service._generate_roi_insights(roi_analysis)
        
        assert insights["best_roi_platform"] == "facebook"
        assert insights["best_roi_percentage"] == 200.0
        assert insights["average_roi"] == 175.0
        assert insights["profitable_platforms_count"] == 2
        assert insights["total_investment"] == 550.0
        assert insights["total_return"] == 1525.0

    def test_generate_product_insights(self, analytics_service):
        """Test product insights generation."""
        products = [
            {
                "title": "Handmade Vase",
                "total_revenue": 900.0,
                "best_platform": "facebook"
            },
            {
                "title": "Ceramic Bowl",
                "total_revenue": 600.0,
                "best_platform": "facebook"
            }
        ]
        
        insights = analytics_service._generate_product_insights(products)
        
        assert insights["top_product"] == "Handmade Vase"
        assert insights["top_product_revenue"] == 900.0
        assert insights["total_products_revenue"] == 1500.0
        assert insights["most_successful_platform"] == "facebook"
        assert insights["average_product_revenue"] == 750.0

    def test_generate_comparison_recommendation(self, analytics_service):
        """Test platform comparison recommendation generation."""
        platform_a_data = {
            "platform": "facebook",
            "sales_metrics": {"total_revenue": 1500.0},
            "engagement_metrics": {"engagement_rate": 25.0}
        }
        
        platform_b_data = {
            "platform": "instagram",
            "sales_metrics": {"total_revenue": 500.0},
            "engagement_metrics": {"engagement_rate": 20.0}
        }
        
        recommendation = analytics_service._generate_comparison_recommendation(
            platform_a_data, platform_b_data, "facebook"
        )
        
        assert isinstance(recommendation, str)
        assert len(recommendation) > 0
        assert "facebook" in recommendation.lower()

    def test_generate_roi_recommendations(self, analytics_service):
        """Test ROI recommendations generation."""
        platform_data = Mock()
        
        # Test excellent ROI
        recommendations = analytics_service._generate_roi_recommendations(
            "facebook", 250.0, "excellent", platform_data
        )
        assert len(recommendations) > 0
        assert "excellent" in recommendations[0].lower()
        
        # Test poor ROI
        recommendations = analytics_service._generate_roi_recommendations(
            "facebook", 25.0, "poor", platform_data
        )
        assert len(recommendations) > 0
        assert "poor" in recommendations[0].lower()

    def test_generate_overall_recommendations(self, analytics_service):
        """Test overall recommendations generation."""
        platforms = [{"platform": "facebook", "performance_score": 85}]
        roi_analysis = [{"platform": "facebook", "roi_percentage": 200.0}]
        top_products = [{"title": "Handmade Vase"}]
        
        recommendations = analytics_service._generate_overall_recommendations(
            platforms, roi_analysis, top_products
        )
        
        assert isinstance(recommendations, list)
        assert len(recommendations) <= 5
        assert all(isinstance(rec, str) for rec in recommendations)

    @pytest.mark.asyncio
    async def test_error_handling(self, analytics_service, sample_dates):
        """Test error handling in analytics service."""
        start_date, end_date = sample_dates
        user_id = "test_user_123"
        
        # Mock service to raise exception
        analytics_service.sales_service.get_platform_breakdown = AsyncMock(
            side_effect=Exception("Database error")
        )
        
        with pytest.raises(Exception) as exc_info:
            await analytics_service.get_platform_performance_breakdown(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date
            )
        
        assert "Database error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_platform_filtering(self, analytics_service, sample_dates, mock_sales_breakdown, mock_engagement_data):
        """Test platform filtering functionality."""
        start_date, end_date = sample_dates
        user_id = "test_user_123"
        platforms = ["facebook"]  # Only facebook
        
        # Mock service responses
        analytics_service.sales_service.get_platform_breakdown = AsyncMock(return_value=mock_sales_breakdown)
        analytics_service.engagement_service.get_engagement_dashboard_data = AsyncMock(return_value=mock_engagement_data)
        analytics_service._get_post_counts_by_platform = AsyncMock(return_value={"facebook": 5})
        analytics_service._calculate_trend = AsyncMock(return_value=("up", 15.5))
        
        result = await analytics_service.get_platform_performance_breakdown(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            platforms=platforms
        )
        
        # Should only include facebook platform
        result_platforms = result["platforms"]
        assert len(result_platforms) == 1
        assert result_platforms[0]["platform"] == "facebook"