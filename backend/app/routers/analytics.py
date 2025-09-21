"""
Analytics API endpoints for platform performance analysis.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models import User
from ..services.sales_tracking import SalesTrackingService
from ..services.engagement_metrics import get_engagement_metrics_service
from ..services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/platform-performance")
async def get_platform_performance_breakdown(
    start_date: Optional[datetime] = Query(None, description="Start date for analysis"),
    end_date: Optional[datetime] = Query(None, description="End date for analysis"),
    platforms: Optional[List[str]] = Query(None, description="Specific platforms to analyze"),
    currency: str = Query("USD", description="Currency for calculations"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive platform performance breakdown."""
    # Default to last 30 days if no dates provided
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    analytics_service = AnalyticsService(db)
    return await analytics_service.get_platform_performance_breakdown(
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        platforms=platforms,
        currency=currency
    )


@router.get("/platform-comparison")
async def get_platform_comparison(
    platform_a: str = Query(..., description="First platform to compare"),
    platform_b: str = Query(..., description="Second platform to compare"),
    start_date: Optional[datetime] = Query(None, description="Start date for comparison"),
    end_date: Optional[datetime] = Query(None, description="End date for comparison"),
    currency: str = Query("USD", description="Currency for calculations"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Compare performance between two platforms."""
    # Default to last 30 days if no dates provided
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    analytics_service = AnalyticsService(db)
    return await analytics_service.compare_platforms(
        user_id=current_user.id,
        platform_a=platform_a,
        platform_b=platform_b,
        start_date=start_date,
        end_date=end_date,
        currency=currency
    )


@router.get("/top-products")
async def get_top_performing_products(
    start_date: Optional[datetime] = Query(None, description="Start date for analysis"),
    end_date: Optional[datetime] = Query(None, description="End date for analysis"),
    platforms: Optional[List[str]] = Query(None, description="Specific platforms to analyze"),
    limit: int = Query(10, ge=1, le=50, description="Number of top products to return"),
    currency: str = Query("USD", description="Currency for calculations"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get top performing products across platforms."""
    # Default to last 30 days if no dates provided
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    analytics_service = AnalyticsService(db)
    return await analytics_service.get_top_performing_products(
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        platforms=platforms,
        limit=limit,
        currency=currency
    )


@router.get("/platform-roi")
async def get_platform_roi_analysis(
    start_date: Optional[datetime] = Query(None, description="Start date for ROI analysis"),
    end_date: Optional[datetime] = Query(None, description="End date for ROI analysis"),
    platforms: Optional[List[str]] = Query(None, description="Specific platforms to analyze"),
    currency: str = Query("USD", description="Currency for calculations"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get ROI analysis for platforms."""
    # Default to last 30 days if no dates provided
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    analytics_service = AnalyticsService(db)
    return await analytics_service.get_platform_roi_analysis(
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        platforms=platforms,
        currency=currency
    )


@router.get("/insights")
async def get_analytics_insights(
    start_date: Optional[datetime] = Query(None, description="Start date for insights"),
    end_date: Optional[datetime] = Query(None, description="End date for insights"),
    platforms: Optional[List[str]] = Query(None, description="Specific platforms to analyze"),
    currency: str = Query("USD", description="Currency for calculations"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get AI-powered analytics insights and recommendations."""
    # Default to last 30 days if no dates provided
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    analytics_service = AnalyticsService(db)
    return await analytics_service.get_analytics_insights(
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        platforms=platforms,
        currency=currency
    )


@router.get("/performance-trends")
async def get_performance_trends(
    start_date: Optional[datetime] = Query(None, description="Start date for trend analysis"),
    end_date: Optional[datetime] = Query(None, description="End date for trend analysis"),
    platforms: Optional[List[str]] = Query(None, description="Specific platforms to analyze"),
    group_by: str = Query("day", description="Grouping period: day, week, month"),
    currency: str = Query("USD", description="Currency for calculations"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get performance trends over time for platforms."""
    # Default to last 30 days if no dates provided
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    # Validate group_by parameter
    if group_by not in ["day", "week", "month"]:
        raise HTTPException(status_code=400, detail="Invalid group_by parameter. Must be 'day', 'week', or 'month'")
    
    analytics_service = AnalyticsService(db)
    return await analytics_service.get_performance_trends(
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        platforms=platforms,
        group_by=group_by,
        currency=currency
    )