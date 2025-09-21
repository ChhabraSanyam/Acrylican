"""
Engagement Metrics Collection Service

This service handles the collection, aggregation, and analysis of engagement metrics
from various social media and marketplace platforms. It provides comprehensive
analytics for posts across all connected platforms.
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

from ..database import get_db
from ..models import EngagementMetrics, MetricsAggregation, Post, User, PlatformConnection
from ..schemas import (
    EngagementMetricsCreate,
    EngagementMetricsResponse,
    EngagementDashboardData,
    MetricsCollectionResult,
    MetricsAggregationResponse
)
from .platform_service import get_platform_service
from .platform_integration import Platform, PlatformMetrics

logger = logging.getLogger(__name__)


class EngagementMetricsService:
    """
    Service for collecting and managing engagement metrics from platforms.
    
    This service provides:
    - Automated metrics collection from platform APIs
    - Metrics aggregation and calculation
    - Dashboard data preparation
    - Historical metrics tracking
    """
    
    def __init__(self):
        self.platform_service = get_platform_service()
        self.logger = logging.getLogger(__name__)
    
    async def collect_metrics_for_post(
        self,
        user_id: str,
        post_id: str,
        platform: Platform,
        platform_post_id: str,
        force_refresh: bool = False
    ) -> Optional[EngagementMetricsResponse]:
        """
        Collect engagement metrics for a specific post on a platform.
        
        Args:
            user_id: User identifier
            post_id: Internal post ID
            platform: Platform to collect from
            platform_post_id: Platform-specific post ID
            force_refresh: Whether to force refresh existing metrics
            
        Returns:
            EngagementMetricsResponse or None if collection failed
        """
        try:
            db = next(get_db())
            
            # Check if we already have recent metrics (within last hour)
            if not force_refresh:
                existing_metrics = db.query(EngagementMetrics).filter(
                    and_(
                        EngagementMetrics.user_id == user_id,
                        EngagementMetrics.post_id == post_id,
                        EngagementMetrics.platform == platform.value,
                        EngagementMetrics.collected_at > datetime.utcnow() - timedelta(hours=1)
                    )
                ).first()
                
                if existing_metrics:
                    self.logger.debug(f"Using cached metrics for post {post_id} on {platform.value}")
                    return EngagementMetricsResponse.model_validate(existing_metrics)
            
            # Collect metrics from platform
            platform_metrics = await self.platform_service.get_platform_metrics(
                platform, user_id, platform_post_id
            )
            
            if not platform_metrics:
                self.logger.warning(f"No metrics available for post {platform_post_id} on {platform.value}")
                return None
            
            # Calculate engagement rate
            engagement_rate = self._calculate_engagement_rate(platform_metrics)
            
            # Create or update metrics record
            metrics_data = EngagementMetricsCreate(
                post_id=post_id,
                platform=platform.value,
                platform_post_id=platform_post_id,
                likes=platform_metrics.likes or 0,
                shares=platform_metrics.shares or 0,
                comments=platform_metrics.comments or 0,
                views=platform_metrics.views or 0,
                reach=platform_metrics.reach or 0,
                engagement_rate=engagement_rate,
                platform_specific_metrics=self._extract_platform_specific_metrics(platform_metrics),
                collection_method="api",
                data_quality="complete",
                metrics_date=datetime.utcnow()
            )
            
            # Save to database
            db_metrics = await self._save_metrics(db, user_id, metrics_data, force_refresh)
            
            if db_metrics:
                self.logger.info(f"Collected metrics for post {post_id} on {platform.value}")
                return EngagementMetricsResponse.model_validate(db_metrics)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to collect metrics for post {post_id}: {e}")
            return None
        finally:
            db.close()
    
    async def collect_metrics_for_user(
        self,
        user_id: str,
        platforms: Optional[List[Platform]] = None,
        post_ids: Optional[List[str]] = None,
        force_refresh: bool = False
    ) -> MetricsCollectionResult:
        """
        Collect engagement metrics for all posts of a user.
        
        Args:
            user_id: User identifier
            platforms: Specific platforms to collect from (None for all)
            post_ids: Specific post IDs to collect for (None for all)
            force_refresh: Whether to force refresh existing metrics
            
        Returns:
            MetricsCollectionResult with collection summary
        """
        try:
            db = next(get_db())
            
            # Get posts to collect metrics for
            query = db.query(Post).filter(Post.user_id == user_id)
            
            if post_ids:
                query = query.filter(Post.id.in_(post_ids))
            
            # Only get published posts with results
            query = query.filter(
                and_(
                    Post.status == "published",
                    Post.results.isnot(None)
                )
            )
            
            posts = query.all()
            
            collected_count = 0
            failed_count = 0
            skipped_count = 0
            errors = []
            collected_metrics = []
            
            for post in posts:
                if not post.results:
                    continue
                
                # Process each platform result
                for result in post.results:
                    if not isinstance(result, dict):
                        continue
                    
                    platform_name = result.get("platform")
                    platform_post_id = result.get("post_id")
                    status = result.get("status")
                    
                    if not platform_name or not platform_post_id or status != "SUCCESS":
                        skipped_count += 1
                        continue
                    
                    # Skip if platform filter is specified and doesn't match
                    if platforms:
                        platform_enum = Platform(platform_name)
                        if platform_enum not in platforms:
                            skipped_count += 1
                            continue
                    
                    try:
                        platform_enum = Platform(platform_name)
                        metrics = await self.collect_metrics_for_post(
                            user_id, post.id, platform_enum, platform_post_id, force_refresh
                        )
                        
                        if metrics:
                            collected_count += 1
                            collected_metrics.append(metrics.id)
                        else:
                            failed_count += 1
                            
                    except Exception as e:
                        failed_count += 1
                        errors.append(f"Failed to collect metrics for post {post.id} on {platform_name}: {str(e)}")
                        self.logger.error(f"Metrics collection failed for post {post.id}: {e}")
            
            # Update aggregations after collection
            if collected_count > 0:
                await self._update_aggregations(user_id, db)
            
            return MetricsCollectionResult(
                success=True,
                collected_count=collected_count,
                failed_count=failed_count,
                skipped_count=skipped_count,
                errors=errors,
                collected_metrics=collected_metrics,
                message=f"Collected metrics for {collected_count} posts, {failed_count} failed, {skipped_count} skipped"
            )
            
        except Exception as e:
            self.logger.error(f"Bulk metrics collection failed for user {user_id}: {e}")
            return MetricsCollectionResult(
                success=False,
                collected_count=0,
                failed_count=0,
                skipped_count=0,
                errors=[str(e)],
                message="Bulk metrics collection failed"
            )
        finally:
            db.close()
    
    async def get_engagement_dashboard_data(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        platforms: Optional[List[str]] = None
    ) -> EngagementDashboardData:
        """
        Get comprehensive engagement dashboard data for a user.
        
        Args:
            user_id: User identifier
            start_date: Start date for data (defaults to 30 days ago)
            end_date: End date for data (defaults to now)
            platforms: Specific platforms to include
            
        Returns:
            EngagementDashboardData with dashboard metrics
        """
        try:
            db = next(get_db())
            
            # Set default date range
            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = end_date - timedelta(days=30)
            
            # Base query for metrics in date range
            base_query = db.query(EngagementMetrics).filter(
                and_(
                    EngagementMetrics.user_id == user_id,
                    EngagementMetrics.metrics_date >= start_date,
                    EngagementMetrics.metrics_date <= end_date,
                    EngagementMetrics.status == "active"
                )
            )
            
            if platforms:
                base_query = base_query.filter(EngagementMetrics.platform.in_(platforms))
            
            # Get total engagement metrics
            total_metrics = base_query.with_entities(
                func.sum(EngagementMetrics.likes).label("total_likes"),
                func.sum(EngagementMetrics.shares).label("total_shares"),
                func.sum(EngagementMetrics.comments).label("total_comments"),
                func.sum(EngagementMetrics.views).label("total_views"),
                func.sum(EngagementMetrics.reach).label("total_reach"),
                func.avg(EngagementMetrics.engagement_rate).label("avg_engagement_rate")
            ).first()
            
            total_engagement = {
                "likes": int(total_metrics.total_likes or 0),
                "shares": int(total_metrics.total_shares or 0),
                "comments": int(total_metrics.total_comments or 0),
                "views": int(total_metrics.total_views or 0),
                "reach": int(total_metrics.total_reach or 0)
            }
            
            # Get engagement by platform
            platform_metrics = base_query.with_entities(
                EngagementMetrics.platform,
                func.sum(EngagementMetrics.likes).label("likes"),
                func.sum(EngagementMetrics.shares).label("shares"),
                func.sum(EngagementMetrics.comments).label("comments"),
                func.sum(EngagementMetrics.views).label("views"),
                func.sum(EngagementMetrics.reach).label("reach"),
                func.avg(EngagementMetrics.engagement_rate).label("avg_engagement_rate"),
                func.count(EngagementMetrics.id).label("post_count")
            ).group_by(EngagementMetrics.platform).all()
            
            engagement_by_platform = []
            for metric in platform_metrics:
                engagement_by_platform.append({
                    "platform": metric.platform,
                    "likes": int(metric.likes or 0),
                    "shares": int(metric.shares or 0),
                    "comments": int(metric.comments or 0),
                    "views": int(metric.views or 0),
                    "reach": int(metric.reach or 0),
                    "average_engagement_rate": float(metric.avg_engagement_rate or 0),
                    "post_count": int(metric.post_count or 0)
                })
            
            # Get engagement trend (daily aggregation)
            engagement_trend = await self._get_engagement_trend(
                db, user_id, start_date, end_date, platforms
            )
            
            # Get top performing posts
            top_posts_query = base_query.join(Post).with_entities(
                EngagementMetrics.post_id,
                Post.title,
                EngagementMetrics.platform,
                EngagementMetrics.likes,
                EngagementMetrics.shares,
                EngagementMetrics.comments,
                EngagementMetrics.views,
                EngagementMetrics.engagement_rate,
                (EngagementMetrics.likes + EngagementMetrics.shares + EngagementMetrics.comments).label("total_engagement")
            ).order_by(desc("total_engagement")).limit(10)
            
            top_performing_posts = []
            for post in top_posts_query.all():
                top_performing_posts.append({
                    "post_id": post.post_id,
                    "title": post.title,
                    "platform": post.platform,
                    "likes": post.likes,
                    "shares": post.shares,
                    "comments": post.comments,
                    "views": post.views,
                    "engagement_rate": float(post.engagement_rate or 0),
                    "total_engagement": int(post.total_engagement or 0)
                })
            
            # Get recent metrics
            recent_metrics_query = base_query.order_by(desc(EngagementMetrics.collected_at)).limit(20)
            recent_metrics = [
                EngagementMetricsResponse.model_validate(metric)
                for metric in recent_metrics_query.all()
            ]
            
            return EngagementDashboardData(
                total_engagement=total_engagement,
                engagement_by_platform=engagement_by_platform,
                engagement_trend=engagement_trend,
                top_performing_posts=top_performing_posts,
                recent_metrics=recent_metrics,
                average_engagement_rate=float(total_metrics.avg_engagement_rate or 0),
                total_reach=total_engagement["reach"]
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get dashboard data for user {user_id}: {e}")
            # Return empty dashboard data on error
            return EngagementDashboardData(
                total_engagement={"likes": 0, "shares": 0, "comments": 0, "views": 0, "reach": 0},
                engagement_by_platform=[],
                engagement_trend=[],
                top_performing_posts=[],
                recent_metrics=[],
                average_engagement_rate=0.0,
                total_reach=0
            )
        finally:
            db.close()
    
    async def get_metrics_for_post(
        self,
        user_id: str,
        post_id: str,
        platforms: Optional[List[str]] = None
    ) -> List[EngagementMetricsResponse]:
        """
        Get all engagement metrics for a specific post.
        
        Args:
            user_id: User identifier
            post_id: Post identifier
            platforms: Specific platforms to filter by
            
        Returns:
            List of EngagementMetricsResponse
        """
        try:
            db = next(get_db())
            
            query = db.query(EngagementMetrics).filter(
                and_(
                    EngagementMetrics.user_id == user_id,
                    EngagementMetrics.post_id == post_id,
                    EngagementMetrics.status == "active"
                )
            )
            
            if platforms:
                query = query.filter(EngagementMetrics.platform.in_(platforms))
            
            metrics = query.order_by(desc(EngagementMetrics.collected_at)).all()
            
            return [EngagementMetricsResponse.model_validate(metric) for metric in metrics]
            
        except Exception as e:
            self.logger.error(f"Failed to get metrics for post {post_id}: {e}")
            return []
        finally:
            db.close()
    
    def _calculate_engagement_rate(self, metrics: PlatformMetrics) -> Optional[float]:
        """
        Calculate engagement rate from platform metrics.
        
        Args:
            metrics: Platform metrics data
            
        Returns:
            Engagement rate as percentage or None
        """
        try:
            # Use reach if available, otherwise use views
            denominator = metrics.reach or metrics.views
            
            if not denominator or denominator == 0:
                return None
            
            # Calculate total engagement
            total_engagement = (metrics.likes or 0) + (metrics.shares or 0) + (metrics.comments or 0)
            
            if total_engagement == 0:
                return 0.0
            
            # Calculate engagement rate as percentage
            engagement_rate = (total_engagement / denominator) * 100
            
            # Round to 2 decimal places and cap at 100%
            return min(round(engagement_rate, 2), 100.0)
            
        except Exception as e:
            self.logger.error(f"Failed to calculate engagement rate: {e}")
            return None
    
    def _extract_platform_specific_metrics(self, metrics: PlatformMetrics) -> Dict[str, Any]:
        """
        Extract platform-specific metrics from PlatformMetrics.
        
        Args:
            metrics: Platform metrics data
            
        Returns:
            Dictionary of platform-specific metrics
        """
        platform_specific = {}
        
        # Add any additional metrics that might be in metadata
        if hasattr(metrics, 'metadata') and metrics.metadata:
            platform_specific.update(metrics.metadata)
        
        # Add platform-specific calculations
        if metrics.platform == Platform.FACEBOOK:
            # Facebook-specific metrics
            if metrics.reach and metrics.views:
                platform_specific["impression_reach_ratio"] = round(metrics.views / metrics.reach, 2)
        
        elif metrics.platform == Platform.INSTAGRAM:
            # Instagram-specific metrics
            if metrics.likes and metrics.comments:
                platform_specific["like_comment_ratio"] = round(metrics.likes / max(metrics.comments, 1), 2)
        
        elif metrics.platform == Platform.PINTEREST:
            # Pinterest-specific metrics (saves are like shares)
            if metrics.shares:
                platform_specific["saves"] = metrics.shares
                platform_specific["save_rate"] = round((metrics.shares / max(metrics.views, 1)) * 100, 2)
        
        return platform_specific
    
    async def _save_metrics(
        self,
        db: Session,
        user_id: str,
        metrics_data: EngagementMetricsCreate,
        force_refresh: bool = False
    ) -> Optional[EngagementMetrics]:
        """
        Save engagement metrics to database.
        
        Args:
            db: Database session
            user_id: User identifier
            metrics_data: Metrics data to save
            force_refresh: Whether to update existing metrics
            
        Returns:
            Saved EngagementMetrics instance or None
        """
        try:
            # Check for existing metrics
            existing = db.query(EngagementMetrics).filter(
                and_(
                    EngagementMetrics.user_id == user_id,
                    EngagementMetrics.post_id == metrics_data.post_id,
                    EngagementMetrics.platform == metrics_data.platform,
                    EngagementMetrics.platform_post_id == metrics_data.platform_post_id
                )
            ).first()
            
            if existing and not force_refresh:
                # Update existing metrics
                for field, value in metrics_data.model_dump(exclude_unset=True).items():
                    if hasattr(existing, field):
                        setattr(existing, field, value)
                existing.updated_at = datetime.utcnow()
                existing.sync_status = "synced"
                
                db.commit()
                db.refresh(existing)
                return existing
            
            elif existing and force_refresh:
                # Update all fields for force refresh
                for field, value in metrics_data.model_dump().items():
                    if hasattr(existing, field):
                        setattr(existing, field, value)
                existing.updated_at = datetime.utcnow()
                existing.collected_at = datetime.utcnow()
                existing.sync_status = "synced"
                
                db.commit()
                db.refresh(existing)
                return existing
            
            else:
                # Create new metrics record
                db_metrics = EngagementMetrics(
                    user_id=user_id,
                    **metrics_data.model_dump()
                )
                
                db.add(db_metrics)
                db.commit()
                db.refresh(db_metrics)
                return db_metrics
                
        except Exception as e:
            db.rollback()
            self.logger.error(f"Failed to save metrics: {e}")
            return None
    
    async def _get_engagement_trend(
        self,
        db: Session,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        platforms: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get engagement trend data for dashboard charts.
        
        Args:
            db: Database session
            user_id: User identifier
            start_date: Start date for trend
            end_date: End date for trend
            platforms: Specific platforms to include
            
        Returns:
            List of daily engagement data
        """
        try:
            # Query daily aggregated metrics
            query = db.query(
                func.date(EngagementMetrics.metrics_date).label("date"),
                func.sum(EngagementMetrics.likes).label("likes"),
                func.sum(EngagementMetrics.shares).label("shares"),
                func.sum(EngagementMetrics.comments).label("comments"),
                func.sum(EngagementMetrics.views).label("views"),
                func.sum(EngagementMetrics.reach).label("reach"),
                func.avg(EngagementMetrics.engagement_rate).label("avg_engagement_rate")
            ).filter(
                and_(
                    EngagementMetrics.user_id == user_id,
                    EngagementMetrics.metrics_date >= start_date,
                    EngagementMetrics.metrics_date <= end_date,
                    EngagementMetrics.status == "active"
                )
            )
            
            if platforms:
                query = query.filter(EngagementMetrics.platform.in_(platforms))
            
            daily_metrics = query.group_by(func.date(EngagementMetrics.metrics_date)).order_by("date").all()
            
            trend_data = []
            for metric in daily_metrics:
                trend_data.append({
                    "date": metric.date.isoformat(),
                    "likes": int(metric.likes or 0),
                    "shares": int(metric.shares or 0),
                    "comments": int(metric.comments or 0),
                    "views": int(metric.views or 0),
                    "reach": int(metric.reach or 0),
                    "engagement_rate": float(metric.avg_engagement_rate or 0),
                    "total_engagement": int((metric.likes or 0) + (metric.shares or 0) + (metric.comments or 0))
                })
            
            return trend_data
            
        except Exception as e:
            self.logger.error(f"Failed to get engagement trend: {e}")
            return []
    
    async def _update_aggregations(self, user_id: str, db: Session):
        """
        Update metrics aggregations after collecting new metrics.
        
        Args:
            user_id: User identifier
            db: Database session
        """
        try:
            # Update daily aggregation for today
            today = datetime.utcnow().date()
            await self._update_daily_aggregation(db, user_id, today)
            
            # Update weekly aggregation for current week
            week_start = today - timedelta(days=today.weekday())
            await self._update_weekly_aggregation(db, user_id, week_start)
            
            # Update monthly aggregation for current month
            month_start = today.replace(day=1)
            await self._update_monthly_aggregation(db, user_id, month_start)
            
        except Exception as e:
            self.logger.error(f"Failed to update aggregations for user {user_id}: {e}")
    
    async def _update_daily_aggregation(self, db: Session, user_id: str, date: datetime.date):
        """Update daily metrics aggregation."""
        # Implementation for daily aggregation
        pass
    
    async def _update_weekly_aggregation(self, db: Session, user_id: str, week_start: datetime.date):
        """Update weekly metrics aggregation."""
        # Implementation for weekly aggregation
        pass
    
    async def _update_monthly_aggregation(self, db: Session, user_id: str, month_start: datetime.date):
        """Update monthly metrics aggregation."""
        # Implementation for monthly aggregation
        pass


# Global service instance
engagement_metrics_service = EngagementMetricsService()


def get_engagement_metrics_service() -> EngagementMetricsService:
    """
    Get the global engagement metrics service instance.
    
    Returns:
        Global EngagementMetricsService instance
    """
    return engagement_metrics_service