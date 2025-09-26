"""
Analytics Service for Platform Performance Analysis

This service provides comprehensive analytics functionality including:
- Platform performance breakdown and comparison
- ROI analysis and calculations
- Top performing products identification
- Performance trends and insights
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc, distinct
import logging

from ..models import SaleEvent, EngagementMetrics, Post, Product, PlatformConnection
from .sales_tracking import SalesTrackingService
from .engagement_metrics import get_engagement_metrics_service

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Service for advanced analytics and platform performance analysis.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.sales_service = SalesTrackingService(db)
        self.engagement_service = get_engagement_metrics_service()
        self.logger = logging.getLogger(__name__)
    
    async def get_platform_performance_breakdown(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        platforms: Optional[List[str]] = None,
        currency: str = "INR"
    ) -> Dict[str, Any]:
        """
        Get comprehensive platform performance breakdown.
        
        Args:
            user_id: User identifier
            start_date: Start date for analysis
            end_date: End date for analysis
            platforms: Specific platforms to analyze
            currency: Currency for calculations
            
        Returns:
            Dictionary containing platform performance metrics
        """
        try:
            # Get sales data for each platform
            platform_breakdown = await self.sales_service.get_platform_breakdown(
                user_id, start_date, end_date, currency
            )
            
            # Get engagement data
            engagement_data = await self.engagement_service.get_engagement_dashboard_data(
                user_id, start_date, end_date, platforms
            )
            
            # Get post counts per platform
            post_counts = await self._get_post_counts_by_platform(user_id, start_date, end_date, platforms)
            
            # Calculate performance metrics for each platform
            performance_metrics = []
            
            for sales_data in platform_breakdown:
                platform = sales_data.platform
                
                # Skip if platform filter is specified and doesn't match
                if platforms and platform not in platforms:
                    continue
                
                # Find corresponding engagement data
                engagement = next(
                    (e for e in engagement_data.engagement_by_platform if e["platform"] == platform),
                    {
                        "likes": 0, "shares": 0, "comments": 0, "views": 0, 
                        "reach": 0, "average_engagement_rate": 0, "post_count": 0
                    }
                )
                
                # Get post count for this platform
                post_count = post_counts.get(platform, 1)  # Avoid division by zero
                
                # Calculate ROI metrics
                revenue_per_post = sales_data.total_revenue / max(post_count, 1)
                engagement_per_post = (engagement["likes"] + engagement["shares"] + engagement["comments"]) / max(post_count, 1)
                
                # Calculate performance score (0-100)
                performance_score = self._calculate_performance_score(
                    sales_data, engagement, post_count
                )
                
                # Calculate trend (simplified - would need historical data for real trends)
                trend_direction, trend_percentage = await self._calculate_trend(
                    user_id, platform, start_date, end_date, currency
                )
                
                performance_metrics.append({
                    "platform": platform,
                    "sales_metrics": {
                        "total_revenue": float(sales_data.total_revenue),
                        "total_orders": sales_data.total_orders,
                        "average_order_value": float(sales_data.average_order_value),
                        "commission_rate": float(sales_data.commission_rate or 0),
                        "total_commission": float(sales_data.total_commission),
                        "net_revenue": float(sales_data.net_revenue),
                        "conversion_rate": self._calculate_conversion_rate(sales_data.total_orders, engagement["reach"])
                    },
                    "engagement_metrics": {
                        "likes": engagement["likes"],
                        "shares": engagement["shares"],
                        "comments": engagement["comments"],
                        "views": engagement["views"],
                        "reach": engagement["reach"],
                        "engagement_rate": engagement["average_engagement_rate"],
                        "total_posts": post_count
                    },
                    "roi_metrics": {
                        "revenue_per_post": float(revenue_per_post),
                        "engagement_per_post": float(engagement_per_post),
                        "cost_per_acquisition": self._calculate_cpa(sales_data.total_revenue, sales_data.total_orders),
                        "return_on_investment": self._calculate_simple_roi(sales_data.net_revenue, post_count)
                    },
                    "top_products": sales_data.top_products,
                    "performance_score": performance_score,
                    "trend_direction": trend_direction,
                    "trend_percentage": trend_percentage
                })
            
            # Generate overall insights
            insights = self._generate_performance_insights(performance_metrics)
            
            return {
                "period_start": start_date.isoformat(),
                "period_end": end_date.isoformat(),
                "platforms": performance_metrics,
                "overall_insights": insights
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get platform performance breakdown: {e}")
            raise
    
    async def compare_platforms(
        self,
        user_id: str,
        platform_a: str,
        platform_b: str,
        start_date: datetime,
        end_date: datetime,
        currency: str = "INR"
    ) -> Dict[str, Any]:
        """
        Compare performance between two platforms.
        
        Args:
            user_id: User identifier
            platform_a: First platform to compare
            platform_b: Second platform to compare
            start_date: Start date for comparison
            end_date: End date for comparison
            currency: Currency for calculations
            
        Returns:
            Dictionary containing platform comparison data
        """
        try:
            # Get performance data for both platforms
            performance_data = await self.get_platform_performance_breakdown(
                user_id, start_date, end_date, [platform_a, platform_b], currency
            )
            
            platforms = performance_data["platforms"]
            
            if len(platforms) < 2:
                return {
                    "error": "Insufficient data for comparison",
                    "platform_a": platform_a,
                    "platform_b": platform_b,
                    "available_platforms": [p["platform"] for p in platforms]
                }
            
            # Find the two platforms
            platform_a_data = next((p for p in platforms if p["platform"] == platform_a), None)
            platform_b_data = next((p for p in platforms if p["platform"] == platform_b), None)
            
            if not platform_a_data or not platform_b_data:
                return {
                    "error": "One or both platforms not found in data",
                    "platform_a": platform_a,
                    "platform_b": platform_b
                }
            
            # Calculate differences
            revenue_diff = platform_a_data["sales_metrics"]["total_revenue"] - platform_b_data["sales_metrics"]["total_revenue"]
            revenue_diff_pct = (revenue_diff / max(platform_b_data["sales_metrics"]["total_revenue"], 1)) * 100
            
            engagement_a = platform_a_data["engagement_metrics"]["likes"] + platform_a_data["engagement_metrics"]["shares"] + platform_a_data["engagement_metrics"]["comments"]
            engagement_b = platform_b_data["engagement_metrics"]["likes"] + platform_b_data["engagement_metrics"]["shares"] + platform_b_data["engagement_metrics"]["comments"]
            engagement_diff = engagement_a - engagement_b
            engagement_diff_pct = (engagement_diff / max(engagement_b, 1)) * 100
            
            roi_diff = platform_a_data["roi_metrics"]["return_on_investment"] - platform_b_data["roi_metrics"]["return_on_investment"]
            roi_diff_pct = (roi_diff / max(platform_b_data["roi_metrics"]["return_on_investment"], 1)) * 100
            
            # Determine better platform
            better_platform = platform_a if platform_a_data["performance_score"] > platform_b_data["performance_score"] else platform_b
            
            # Generate recommendation
            recommendation = self._generate_comparison_recommendation(
                platform_a_data, platform_b_data, better_platform
            )
            
            return {
                "platform_a": platform_a,
                "platform_b": platform_b,
                "platform_a_data": platform_a_data,
                "platform_b_data": platform_b_data,
                "comparison": {
                    "revenue_difference": revenue_diff,
                    "revenue_difference_percentage": revenue_diff_pct,
                    "engagement_difference": engagement_diff,
                    "engagement_difference_percentage": engagement_diff_pct,
                    "roi_difference": roi_diff,
                    "roi_difference_percentage": roi_diff_pct,
                    "better_platform": better_platform,
                    "recommendation": recommendation
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to compare platforms: {e}")
            raise
    
    async def get_top_performing_products(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        platforms: Optional[List[str]] = None,
        limit: int = 10,
        currency: str = "INR"
    ) -> Dict[str, Any]:
        """
        Get top performing products across platforms.
        
        Args:
            user_id: User identifier
            start_date: Start date for analysis
            end_date: End date for analysis
            platforms: Specific platforms to analyze
            limit: Number of top products to return
            currency: Currency for calculations
            
        Returns:
            Dictionary containing top performing products data
        """
        try:
            # Get sales data by product
            query = self.db.query(
                SaleEvent.product_id,
                SaleEvent.product_title,
                SaleEvent.platform,
                func.sum(SaleEvent.amount).label('revenue'),
                func.count(SaleEvent.id).label('orders'),
                func.sum(SaleEvent.quantity).label('quantity')
            ).filter(
                and_(
                    SaleEvent.user_id == user_id,
                    SaleEvent.occurred_at >= start_date,
                    SaleEvent.occurred_at <= end_date,
                    SaleEvent.status == "confirmed",
                    SaleEvent.currency == currency,
                    SaleEvent.product_title.isnot(None)
                )
            )
            
            if platforms:
                query = query.filter(SaleEvent.platform.in_(platforms))
            
            product_sales = query.group_by(
                SaleEvent.product_id, 
                SaleEvent.product_title, 
                SaleEvent.platform
            ).all()
            
            # Get engagement data for products (if available)
            engagement_query = self.db.query(
                EngagementMetrics.post_id,
                Post.title,
                EngagementMetrics.platform,
                func.sum(EngagementMetrics.likes + EngagementMetrics.shares + EngagementMetrics.comments).label('total_engagement')
            ).join(Post).filter(
                and_(
                    EngagementMetrics.user_id == user_id,
                    EngagementMetrics.metrics_date >= start_date,
                    EngagementMetrics.metrics_date <= end_date,
                    EngagementMetrics.status == "active"
                )
            )
            
            if platforms:
                engagement_query = engagement_query.filter(EngagementMetrics.platform.in_(platforms))
            
            product_engagement = engagement_query.group_by(
                EngagementMetrics.post_id,
                Post.title,
                EngagementMetrics.platform
            ).all()
            
            # Aggregate by product
            products_data = {}
            
            for sale in product_sales:
                product_key = sale.product_title or f"Product {sale.product_id}"
                
                if product_key not in products_data:
                    products_data[product_key] = {
                        "id": sale.product_id,
                        "title": product_key,
                        "total_revenue": 0,
                        "total_orders": 0,
                        "total_engagement": 0,
                        "platforms": {},
                        "best_platform": "",
                        "performance_score": 0
                    }
                
                # Add platform data
                products_data[product_key]["platforms"][sale.platform] = {
                    "platform": sale.platform,
                    "revenue": float(sale.revenue),
                    "orders": sale.orders,
                    "engagement": 0,  # Will be updated below
                    "performance_score": 0
                }
                
                products_data[product_key]["total_revenue"] += float(sale.revenue)
                products_data[product_key]["total_orders"] += sale.orders
            
            # Add engagement data
            for engagement in product_engagement:
                # Try to match by product title (simplified matching)
                for product_key, product_data in products_data.items():
                    if engagement.title and engagement.title.lower() in product_key.lower():
                        if engagement.platform in product_data["platforms"]:
                            product_data["platforms"][engagement.platform]["engagement"] = int(engagement.total_engagement or 0)
                            product_data["total_engagement"] += int(engagement.total_engagement or 0)
                        break
            
            # Calculate performance scores and find best platforms
            for product_key, product_data in products_data.items():
                best_platform = ""
                best_score = 0
                
                for platform, platform_data in product_data["platforms"].items():
                    # Calculate performance score for this platform
                    score = self._calculate_product_platform_score(platform_data)
                    platform_data["performance_score"] = score
                    
                    if score > best_score:
                        best_score = score
                        best_platform = platform
                
                product_data["best_platform"] = best_platform
                product_data["performance_score"] = best_score
                
                # Convert platforms dict to list
                product_data["platforms"] = list(product_data["platforms"].values())
            
            # Sort by performance score and limit results
            top_products = sorted(
                products_data.values(),
                key=lambda x: x["performance_score"],
                reverse=True
            )[:limit]
            
            return {
                "products": top_products,
                "total_products": len(products_data),
                "period_start": start_date.isoformat(),
                "period_end": end_date.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get top performing products: {e}")
            raise
    
    async def get_platform_roi_analysis(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        platforms: Optional[List[str]] = None,
        currency: str = "INR"
    ) -> Dict[str, Any]:
        """
        Get ROI analysis for platforms.
        
        Args:
            user_id: User identifier
            start_date: Start date for analysis
            end_date: End date for analysis
            platforms: Specific platforms to analyze
            currency: Currency for calculations
            
        Returns:
            Dictionary containing ROI analysis data
        """
        try:
            # Get platform breakdown data
            platform_breakdown = await self.sales_service.get_platform_breakdown(
                user_id, start_date, end_date, currency
            )
            
            # Get post counts for investment calculation
            post_counts = await self._get_post_counts_by_platform(user_id, start_date, end_date, platforms)
            
            roi_analysis = []
            
            for platform_data in platform_breakdown:
                platform = platform_data.platform
                
                # Skip if platform filter is specified and doesn't match
                if platforms and platform not in platforms:
                    continue
                
                post_count = post_counts.get(platform, 1)
                
                # Calculate investment metrics (simplified)
                # In a real scenario, this would include actual advertising costs, time tracking, etc.
                estimated_time_per_post = 2  # hours
                estimated_hourly_rate = 25  # USD
                time_investment = post_count * estimated_time_per_post * estimated_hourly_rate
                
                # Assume minimal advertising cost for organic posts
                advertising_cost = 0
                content_creation_cost = post_count * 10  # Estimated cost per post
                total_investment = time_investment + advertising_cost + content_creation_cost
                
                # Calculate return metrics
                gross_revenue = float(platform_data.total_revenue)
                net_revenue = float(platform_data.net_revenue)
                
                # Estimate engagement value (simplified)
                engagement_value = post_count * 5  # Estimated value per post engagement
                
                total_return = net_revenue + engagement_value
                
                # Calculate ROI percentage
                roi_percentage = ((total_return - total_investment) / max(total_investment, 1)) * 100
                
                # Categorize ROI
                if roi_percentage >= 200:
                    roi_category = "excellent"
                elif roi_percentage >= 100:
                    roi_category = "good"
                elif roi_percentage >= 50:
                    roi_category = "average"
                else:
                    roi_category = "poor"
                
                # Generate recommendations
                recommendations = self._generate_roi_recommendations(
                    platform, roi_percentage, roi_category, platform_data
                )
                
                roi_analysis.append({
                    "platform": platform,
                    "investment_metrics": {
                        "time_spent_hours": post_count * estimated_time_per_post,
                        "advertising_cost": advertising_cost,
                        "content_creation_cost": content_creation_cost,
                        "total_investment": total_investment
                    },
                    "return_metrics": {
                        "gross_revenue": gross_revenue,
                        "net_revenue": net_revenue,
                        "engagement_value": engagement_value,
                        "total_return": total_return
                    },
                    "roi_percentage": roi_percentage,
                    "roi_category": roi_category,
                    "recommendations": recommendations
                })
            
            return {
                "roi_analysis": roi_analysis,
                "period_start": start_date.isoformat(),
                "period_end": end_date.isoformat(),
                "summary": {
                    "best_roi_platform": max(roi_analysis, key=lambda x: x["roi_percentage"])["platform"] if roi_analysis else None,
                    "average_roi": sum(r["roi_percentage"] for r in roi_analysis) / len(roi_analysis) if roi_analysis else 0,
                    "total_investment": sum(r["investment_metrics"]["total_investment"] for r in roi_analysis),
                    "total_return": sum(r["return_metrics"]["total_return"] for r in roi_analysis)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get platform ROI analysis: {e}")
            raise
    
    async def get_analytics_insights(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        platforms: Optional[List[str]] = None,
        currency: str = "INR"
    ) -> Dict[str, Any]:
        """
        Get AI-powered analytics insights and recommendations.
        
        Args:
            user_id: User identifier
            start_date: Start date for insights
            end_date: End date for insights
            platforms: Specific platforms to analyze
            currency: Currency for calculations
            
        Returns:
            Dictionary containing insights and recommendations
        """
        try:
            # Get comprehensive performance data
            performance_data = await self.get_platform_performance_breakdown(
                user_id, start_date, end_date, platforms, currency
            )
            
            roi_data = await self.get_platform_roi_analysis(
                user_id, start_date, end_date, platforms, currency
            )
            
            top_products_data = await self.get_top_performing_products(
                user_id, start_date, end_date, platforms, 5, currency
            )
            
            # Generate insights
            insights = {
                "performance_insights": self._generate_performance_insights(performance_data["platforms"]),
                "roi_insights": self._generate_roi_insights(roi_data["roi_analysis"]),
                "product_insights": self._generate_product_insights(top_products_data["products"]),
                "recommendations": self._generate_overall_recommendations(
                    performance_data["platforms"], 
                    roi_data["roi_analysis"], 
                    top_products_data["products"]
                )
            }
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Failed to get analytics insights: {e}")
            raise
    
    # Helper methods
    
    async def _get_post_counts_by_platform(
        self, 
        user_id: str, 
        start_date: datetime, 
        end_date: datetime,
        platforms: Optional[List[str]] = None
    ) -> Dict[str, int]:
        """Get post counts by platform for the specified period."""
        try:
            query = self.db.query(
                func.json_extract(Post.results, '$[*].platform').label('platform'),
                func.count(Post.id).label('count')
            ).filter(
                and_(
                    Post.user_id == user_id,
                    Post.published_at >= start_date,
                    Post.published_at <= end_date,
                    Post.status == "published"
                )
            )
            
            # This is a simplified approach - in reality, we'd need to properly parse JSON arrays
            # For now, we'll get total posts and estimate distribution
            total_posts = self.db.query(func.count(Post.id)).filter(
                and_(
                    Post.user_id == user_id,
                    Post.published_at >= start_date,
                    Post.published_at <= end_date,
                    Post.status == "published"
                )
            ).scalar() or 0
            
            # Get unique platforms from sales data as a proxy
            platform_query = self.db.query(distinct(SaleEvent.platform)).filter(
                and_(
                    SaleEvent.user_id == user_id,
                    SaleEvent.occurred_at >= start_date,
                    SaleEvent.occurred_at <= end_date
                )
            )
            
            if platforms:
                platform_query = platform_query.filter(SaleEvent.platform.in_(platforms))
            
            unique_platforms = [p[0] for p in platform_query.all()]
            
            # Distribute posts evenly across platforms (simplified)
            posts_per_platform = max(total_posts // max(len(unique_platforms), 1), 1)
            
            return {platform: posts_per_platform for platform in unique_platforms}
            
        except Exception as e:
            self.logger.error(f"Failed to get post counts by platform: {e}")
            return {}
    
    def _calculate_performance_score(
        self, 
        sales_data, 
        engagement_data: Dict[str, Any], 
        post_count: int
    ) -> int:
        """Calculate a performance score (0-100) for a platform."""
        try:
            # Revenue score (0-40 points)
            revenue_per_post = sales_data.total_revenue / max(post_count, 1)
            revenue_score = min(revenue_per_post / 100 * 40, 40)  # Cap at 40 points
            
            # Engagement score (0-30 points)
            total_engagement = engagement_data["likes"] + engagement_data["shares"] + engagement_data["comments"]
            engagement_per_post = total_engagement / max(post_count, 1)
            engagement_score = min(engagement_per_post / 100 * 30, 30)  # Cap at 30 points
            
            # Order score (0-20 points)
            orders_per_post = sales_data.total_orders / max(post_count, 1)
            order_score = min(orders_per_post * 10, 20)  # Cap at 20 points
            
            # Engagement rate score (0-10 points)
            engagement_rate_score = min(engagement_data["average_engagement_rate"], 10)
            
            total_score = revenue_score + engagement_score + order_score + engagement_rate_score
            return int(min(total_score, 100))
            
        except Exception as e:
            self.logger.error(f"Failed to calculate performance score: {e}")
            return 0
    
    async def _calculate_trend(
        self, 
        user_id: str, 
        platform: str, 
        start_date: datetime, 
        end_date: datetime,
        currency: str
    ) -> Tuple[str, float]:
        """Calculate trend direction and percentage for a platform."""
        try:
            # Get data for the previous period for comparison
            period_length = end_date - start_date
            previous_start = start_date - period_length
            previous_end = start_date
            
            # Get current period revenue
            current_revenue = self.db.query(func.sum(SaleEvent.amount)).filter(
                and_(
                    SaleEvent.user_id == user_id,
                    SaleEvent.platform == platform,
                    SaleEvent.occurred_at >= start_date,
                    SaleEvent.occurred_at <= end_date,
                    SaleEvent.status == "confirmed",
                    SaleEvent.currency == currency
                )
            ).scalar() or 0
            
            # Get previous period revenue
            previous_revenue = self.db.query(func.sum(SaleEvent.amount)).filter(
                and_(
                    SaleEvent.user_id == user_id,
                    SaleEvent.platform == platform,
                    SaleEvent.occurred_at >= previous_start,
                    SaleEvent.occurred_at <= previous_end,
                    SaleEvent.status == "confirmed",
                    SaleEvent.currency == currency
                )
            ).scalar() or 0
            
            if previous_revenue == 0:
                return "stable", 0.0
            
            change_percentage = ((float(current_revenue) - float(previous_revenue)) / float(previous_revenue)) * 100
            
            if change_percentage > 5:
                return "up", change_percentage
            elif change_percentage < -5:
                return "down", abs(change_percentage)
            else:
                return "stable", abs(change_percentage)
                
        except Exception as e:
            self.logger.error(f"Failed to calculate trend: {e}")
            return "stable", 0.0
    
    def _calculate_conversion_rate(self, orders: int, reach: int) -> float:
        """Calculate conversion rate from reach to orders."""
        if reach == 0:
            return 0.0
        return (orders / reach) * 100
    
    def _calculate_cpa(self, revenue: float, orders: int) -> float:
        """Calculate cost per acquisition (simplified)."""
        if orders == 0:
            return 0.0
        # Simplified CPA calculation - in reality would use actual ad spend
        estimated_cost = revenue * 0.1  # Assume 10% of revenue as cost
        return estimated_cost / orders
    
    def _calculate_simple_roi(self, net_revenue: float, post_count: int) -> float:
        """Calculate simple ROI based on estimated investment."""
        estimated_investment = post_count * 35  # Estimated cost per post
        if estimated_investment == 0:
            return 0.0
        return ((net_revenue - estimated_investment) / estimated_investment) * 100
    
    def _calculate_product_platform_score(self, platform_data: Dict[str, Any]) -> int:
        """Calculate performance score for a product on a specific platform."""
        try:
            revenue_score = min(platform_data["revenue"] / 100, 50)  # Max 50 points
            order_score = min(platform_data["orders"] * 5, 30)  # Max 30 points
            engagement_score = min(platform_data["engagement"] / 10, 20)  # Max 20 points
            
            return int(revenue_score + order_score + engagement_score)
            
        except Exception as e:
            self.logger.error(f"Failed to calculate product platform score: {e}")
            return 0
    
    def _generate_performance_insights(self, platforms: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate insights from platform performance data."""
        if not platforms:
            return {"message": "No platform data available for insights"}
        
        # Find best performing platform
        best_platform = max(platforms, key=lambda x: x["performance_score"])
        
        # Find highest revenue platform
        highest_revenue = max(platforms, key=lambda x: x["sales_metrics"]["total_revenue"])
        
        # Find most engaging platform
        most_engaging = max(platforms, key=lambda x: x["engagement_metrics"]["engagement_rate"])
        
        return {
            "best_performing_platform": best_platform["platform"],
            "highest_revenue_platform": highest_revenue["platform"],
            "most_engaging_platform": most_engaging["platform"],
            "total_platforms": len(platforms),
            "average_performance_score": sum(p["performance_score"] for p in platforms) / len(platforms)
        }
    
    def _generate_roi_insights(self, roi_analysis: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate insights from ROI analysis data."""
        if not roi_analysis:
            return {"message": "No ROI data available for insights"}
        
        best_roi = max(roi_analysis, key=lambda x: x["roi_percentage"])
        average_roi = sum(r["roi_percentage"] for r in roi_analysis) / len(roi_analysis)
        
        profitable_platforms = [r for r in roi_analysis if r["roi_percentage"] > 100]
        
        return {
            "best_roi_platform": best_roi["platform"],
            "best_roi_percentage": best_roi["roi_percentage"],
            "average_roi": average_roi,
            "profitable_platforms_count": len(profitable_platforms),
            "total_investment": sum(r["investment_metrics"]["total_investment"] for r in roi_analysis),
            "total_return": sum(r["return_metrics"]["total_return"] for r in roi_analysis)
        }
    
    def _generate_product_insights(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate insights from top products data."""
        if not products:
            return {"message": "No product data available for insights"}
        
        top_product = products[0] if products else None
        total_revenue = sum(p["total_revenue"] for p in products)
        
        # Find most common best platform
        best_platforms = [p["best_platform"] for p in products if p["best_platform"]]
        most_common_platform = max(set(best_platforms), key=best_platforms.count) if best_platforms else None
        
        return {
            "top_product": top_product["title"] if top_product else None,
            "top_product_revenue": top_product["total_revenue"] if top_product else 0,
            "total_products_revenue": total_revenue,
            "most_successful_platform": most_common_platform,
            "average_product_revenue": total_revenue / len(products) if products else 0
        }
    
    def _generate_comparison_recommendation(
        self, 
        platform_a_data: Dict[str, Any], 
        platform_b_data: Dict[str, Any], 
        better_platform: str
    ) -> str:
        """Generate recommendation based on platform comparison."""
        if better_platform == platform_a_data["platform"]:
            better_data = platform_a_data
            worse_data = platform_b_data
        else:
            better_data = platform_b_data
            worse_data = platform_a_data
        
        revenue_diff = better_data["sales_metrics"]["total_revenue"] - worse_data["sales_metrics"]["total_revenue"]
        
        if revenue_diff > 1000:
            return f"Focus more resources on {better_platform} as it generates significantly higher revenue (${revenue_diff:.0f} more)."
        elif better_data["engagement_metrics"]["engagement_rate"] > worse_data["engagement_metrics"]["engagement_rate"] * 1.5:
            return f"{better_platform} has much better engagement rates. Consider adapting successful content strategies from this platform."
        else:
            return f"{better_platform} performs slightly better overall. Consider testing similar content strategies on both platforms."
    
    def _generate_roi_recommendations(
        self, 
        platform: str, 
        roi_percentage: float, 
        roi_category: str, 
        platform_data
    ) -> List[str]:
        """Generate ROI-based recommendations for a platform."""
        recommendations = []
        
        if roi_category == "excellent":
            recommendations.append(f"Excellent ROI on {platform}! Consider increasing investment here.")
            recommendations.append("Scale successful content strategies to maximize returns.")
        elif roi_category == "good":
            recommendations.append(f"Good ROI on {platform}. Look for optimization opportunities.")
            recommendations.append("Analyze top-performing posts to replicate success.")
        elif roi_category == "average":
            recommendations.append(f"Average ROI on {platform}. Focus on improving content quality.")
            recommendations.append("Consider A/B testing different content approaches.")
        else:
            recommendations.append(f"Poor ROI on {platform}. Review strategy or reduce investment.")
            recommendations.append("Analyze what's not working and consider platform-specific optimizations.")
        
        return recommendations
    
    def _generate_overall_recommendations(
        self, 
        platforms: List[Dict[str, Any]], 
        roi_analysis: List[Dict[str, Any]], 
        top_products: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate overall recommendations based on all analytics data."""
        recommendations = []
        
        if platforms:
            best_platform = max(platforms, key=lambda x: x["performance_score"])
            recommendations.append(f"Focus on {best_platform['platform']} - your best performing platform.")
        
        if roi_analysis:
            best_roi = max(roi_analysis, key=lambda x: x["roi_percentage"])
            if best_roi["roi_percentage"] > 200:
                recommendations.append(f"Increase investment in {best_roi['platform']} - excellent ROI of {best_roi['roi_percentage']:.1f}%.")
        
        if top_products:
            top_product = top_products[0]
            recommendations.append(f"Promote '{top_product['title']}' more - it's your top performer.")
        
        # Add general recommendations
        recommendations.extend([
            "Regularly analyze performance metrics to identify trends.",
            "Test new content formats on your best-performing platforms.",
            "Consider cross-promoting successful products across all platforms."
        ])
        
        return recommendations[:5]  # Limit to top 5 recommendations