"""
Engagement Metrics API Router

This module provides REST API endpoints for engagement metrics collection,
retrieval, and analytics dashboard functionality.
"""

from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models import User
from ..schemas import (
    EngagementMetricsResponse,
    EngagementMetricsListResponse,
    EngagementDashboardData,
    MetricsCollectionRequest,
    MetricsCollectionResult,
    MetricsAggregationResponse
)
from ..services.engagement_metrics import get_engagement_metrics_service
from ..services.platform_integration import Platform

router = APIRouter(prefix="/engagement", tags=["engagement"])


@router.post("/collect", response_model=MetricsCollectionResult)
async def collect_engagement_metrics(
    request: MetricsCollectionRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Collect engagement metrics for user's posts.
    
    This endpoint triggers collection of engagement metrics from connected platforms.
    The collection runs in the background to avoid timeout issues.
    """
    try:
        engagement_service = get_engagement_metrics_service()
        
        # Convert platform strings to Platform enums if provided
        platforms = None
        if request.platforms:
            try:
                platforms = [Platform(platform) for platform in request.platforms]
            except ValueError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid platform specified: {str(e)}"
                )
        
        # Run collection in background for better performance
        if request.post_ids or request.platforms or request.start_date or request.end_date:
            # Specific collection request - run synchronously for immediate feedback
            result = await engagement_service.collect_metrics_for_user(
                user_id=current_user.id,
                platforms=platforms,
                post_ids=request.post_ids,
                force_refresh=request.force_refresh
            )
        else:
            # Full collection - run in background
            background_tasks.add_task(
                engagement_service.collect_metrics_for_user,
                user_id=current_user.id,
                platforms=platforms,
                post_ids=request.post_ids,
                force_refresh=request.force_refresh
            )
            
            result = MetricsCollectionResult(
                success=True,
                collected_count=0,
                failed_count=0,
                skipped_count=0,
                message="Metrics collection started in background. Check dashboard for updates."
            )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to collect engagement metrics: {str(e)}"
        )


@router.get("/dashboard", response_model=EngagementDashboardData)
async def get_engagement_dashboard(
    start_date: Optional[datetime] = Query(None, description="Start date for dashboard data"),
    end_date: Optional[datetime] = Query(None, description="End date for dashboard data"),
    platforms: Optional[List[str]] = Query(None, description="Specific platforms to include"),
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive engagement dashboard data.
    
    Returns aggregated engagement metrics, trends, and top-performing posts
    for the specified date range and platforms.
    """
    try:
        engagement_service = get_engagement_metrics_service()
        
        # Set default date range if not provided (last 30 days)
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Validate date range
        if start_date > end_date:
            raise HTTPException(
                status_code=400,
                detail="Start date must be before end date"
            )
        
        # Validate platforms if provided
        if platforms:
            try:
                for platform in platforms:
                    Platform(platform)  # Validate platform enum
            except ValueError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid platform specified: {str(e)}"
                )
        
        dashboard_data = await engagement_service.get_engagement_dashboard_data(
            user_id=current_user.id,
            start_date=start_date,
            end_date=end_date,
            platforms=platforms
        )
        
        return dashboard_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get dashboard data: {str(e)}"
        )


@router.get("/posts/{post_id}", response_model=List[EngagementMetricsResponse])
async def get_post_engagement_metrics(
    post_id: str,
    platforms: Optional[List[str]] = Query(None, description="Specific platforms to filter by"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get engagement metrics for a specific post across all platforms.
    
    Returns detailed engagement metrics for the specified post,
    optionally filtered by platform.
    """
    try:
        engagement_service = get_engagement_metrics_service()
        
        # Validate platforms if provided
        if platforms:
            try:
                for platform in platforms:
                    Platform(platform)  # Validate platform enum
            except ValueError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid platform specified: {str(e)}"
                )
        
        # Verify post belongs to user
        from ..models import Post
        post = db.query(Post).filter(
            Post.id == post_id,
            Post.user_id == current_user.id
        ).first()
        
        if not post:
            raise HTTPException(
                status_code=404,
                detail="Post not found"
            )
        
        metrics = await engagement_service.get_metrics_for_post(
            user_id=current_user.id,
            post_id=post_id,
            platforms=platforms
        )
        
        return metrics
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get post metrics: {str(e)}"
        )


@router.post("/posts/{post_id}/collect", response_model=List[EngagementMetricsResponse])
async def collect_post_engagement_metrics(
    post_id: str,
    platforms: Optional[List[str]] = Query(None, description="Specific platforms to collect from"),
    force_refresh: bool = Query(False, description="Force refresh of existing metrics"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Collect engagement metrics for a specific post.
    
    Triggers immediate collection of engagement metrics for the specified post
    from all connected platforms or specific platforms if provided.
    """
    try:
        engagement_service = get_engagement_metrics_service()
        
        # Verify post belongs to user
        from ..models import Post
        post = db.query(Post).filter(
            Post.id == post_id,
            Post.user_id == current_user.id
        ).first()
        
        if not post:
            raise HTTPException(
                status_code=404,
                detail="Post not found"
            )
        
        if not post.results:
            raise HTTPException(
                status_code=400,
                detail="Post has no published results to collect metrics from"
            )
        
        # Validate platforms if provided
        platform_enums = None
        if platforms:
            try:
                platform_enums = [Platform(platform) for platform in platforms]
            except ValueError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid platform specified: {str(e)}"
                )
        
        collected_metrics = []
        
        # Collect metrics for each platform result
        for result in post.results:
            if not isinstance(result, dict):
                continue
            
            platform_name = result.get("platform")
            platform_post_id = result.get("post_id")
            status = result.get("status")
            
            if not platform_name or not platform_post_id or status != "SUCCESS":
                continue
            
            # Skip if platform filter is specified and doesn't match
            if platform_enums:
                try:
                    platform_enum = Platform(platform_name)
                    if platform_enum not in platform_enums:
                        continue
                except ValueError:
                    continue
            
            try:
                platform_enum = Platform(platform_name)
                metrics = await engagement_service.collect_metrics_for_post(
                    user_id=current_user.id,
                    post_id=post_id,
                    platform=platform_enum,
                    platform_post_id=platform_post_id,
                    force_refresh=force_refresh
                )
                
                if metrics:
                    collected_metrics.append(metrics)
                    
            except Exception as e:
                # Log error but continue with other platforms
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to collect metrics for {platform_name}: {e}")
        
        return collected_metrics
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to collect post metrics: {str(e)}"
        )


@router.get("/metrics", response_model=EngagementMetricsListResponse)
async def get_engagement_metrics(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of records to return"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    post_id: Optional[str] = Query(None, description="Filter by post ID"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get paginated list of engagement metrics.
    
    Returns a paginated list of engagement metrics with optional filtering
    by platform, post, and date range.
    """
    try:
        from ..models import EngagementMetrics
        from sqlalchemy import and_, desc
        
        # Build query with filters
        query = db.query(EngagementMetrics).filter(
            EngagementMetrics.user_id == current_user.id,
            EngagementMetrics.status == "active"
        )
        
        if platform:
            # Validate platform
            try:
                Platform(platform)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid platform: {platform}"
                )
            query = query.filter(EngagementMetrics.platform == platform)
        
        if post_id:
            query = query.filter(EngagementMetrics.post_id == post_id)
        
        if start_date:
            query = query.filter(EngagementMetrics.metrics_date >= start_date)
        
        if end_date:
            query = query.filter(EngagementMetrics.metrics_date <= end_date)
        
        # Get total count
        total = query.count()
        
        # Get paginated results
        metrics = query.order_by(desc(EngagementMetrics.collected_at)).offset(skip).limit(limit).all()
        
        return EngagementMetricsListResponse(
            metrics=[EngagementMetricsResponse.model_validate(metric) for metric in metrics],
            total=total,
            skip=skip,
            limit=limit
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get engagement metrics: {str(e)}"
        )


@router.get("/platforms", response_model=List[str])
async def get_available_platforms():
    """
    Get list of available platforms for engagement metrics collection.
    
    Returns a list of platform identifiers that support engagement metrics.
    """
    try:
        # Return all platforms that support metrics collection
        platforms = [platform.value for platform in Platform]
        return platforms
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get available platforms: {str(e)}"
        )


@router.delete("/metrics/{metric_id}")
async def delete_engagement_metric(
    metric_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a specific engagement metric record.
    
    Marks the engagement metric as inactive rather than permanently deleting it
    to maintain data integrity for aggregations.
    """
    try:
        from ..models import EngagementMetrics
        
        # Find the metric
        metric = db.query(EngagementMetrics).filter(
            EngagementMetrics.id == metric_id,
            EngagementMetrics.user_id == current_user.id
        ).first()
        
        if not metric:
            raise HTTPException(
                status_code=404,
                detail="Engagement metric not found"
            )
        
        # Mark as inactive instead of deleting
        metric.status = "inactive"
        metric.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {"message": "Engagement metric deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete engagement metric: {str(e)}"
        )


@router.get("/summary", response_model=dict)
async def get_engagement_summary(
    days: int = Query(30, ge=1, le=365, description="Number of days to include in summary"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a quick engagement summary for the specified number of days.
    
    Returns key engagement metrics and trends for quick overview.
    """
    try:
        from ..models import EngagementMetrics
        from sqlalchemy import func, and_
        
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get summary metrics
        summary_query = db.query(
            func.count(EngagementMetrics.id).label("total_posts"),
            func.sum(EngagementMetrics.likes).label("total_likes"),
            func.sum(EngagementMetrics.shares).label("total_shares"),
            func.sum(EngagementMetrics.comments).label("total_comments"),
            func.sum(EngagementMetrics.views).label("total_views"),
            func.sum(EngagementMetrics.reach).label("total_reach"),
            func.avg(EngagementMetrics.engagement_rate).label("avg_engagement_rate"),
            func.count(func.distinct(EngagementMetrics.platform)).label("active_platforms")
        ).filter(
            and_(
                EngagementMetrics.user_id == current_user.id,
                EngagementMetrics.metrics_date >= start_date,
                EngagementMetrics.metrics_date <= end_date,
                EngagementMetrics.status == "active"
            )
        ).first()
        
        return {
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_posts": int(summary_query.total_posts or 0),
            "total_likes": int(summary_query.total_likes or 0),
            "total_shares": int(summary_query.total_shares or 0),
            "total_comments": int(summary_query.total_comments or 0),
            "total_views": int(summary_query.total_views or 0),
            "total_reach": int(summary_query.total_reach or 0),
            "average_engagement_rate": float(summary_query.avg_engagement_rate or 0),
            "active_platforms": int(summary_query.active_platforms or 0),
            "total_engagement": int((summary_query.total_likes or 0) + 
                                 (summary_query.total_shares or 0) + 
                                 (summary_query.total_comments or 0))
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get engagement summary: {str(e)}"
        )