"""
Sales tracking API endpoints.
"""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models import User
from ..schemas import (
    SaleEventCreate, SaleEventUpdate, SaleEventResponse, SaleEventListResponse,
    SalesMetrics, SalesDashboardData, SalesReportRequest
)
from ..services.sales_tracking import SalesTrackingService
from ..services.sales_sync import SalesSyncService

router = APIRouter(prefix="/sales", tags=["sales"])


@router.post("/events", response_model=SaleEventResponse)
async def create_sale_event(
    sale_data: SaleEventCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new sale event."""
    service = SalesTrackingService(db)
    return await service.create_sale_event(current_user.id, sale_data)


@router.get("/events", response_model=SaleEventListResponse)
async def get_sales_list(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    start_date: Optional[datetime] = Query(None, description="Filter sales from this date"),
    end_date: Optional[datetime] = Query(None, description="Filter sales until this date"),
    status: Optional[str] = Query(None, description="Filter by sale status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get paginated list of sale events with optional filters."""
    service = SalesTrackingService(db)
    result = await service.get_sales_list(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        platform=platform,
        start_date=start_date,
        end_date=end_date,
        status=status
    )
    return SaleEventListResponse(**result)


@router.get("/events/{sale_id}", response_model=SaleEventResponse)
async def get_sale_event(
    sale_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific sale event."""
    service = SalesTrackingService(db)
    sale_event = await service.get_sale_event(current_user.id, sale_id)
    
    if not sale_event:
        raise HTTPException(status_code=404, detail="Sale event not found")
    
    return sale_event


@router.put("/events/{sale_id}", response_model=SaleEventResponse)
async def update_sale_event(
    sale_id: str,
    update_data: SaleEventUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a sale event."""
    service = SalesTrackingService(db)
    sale_event = await service.update_sale_event(current_user.id, sale_id, update_data)
    
    if not sale_event:
        raise HTTPException(status_code=404, detail="Sale event not found")
    
    return sale_event


@router.delete("/events/{sale_id}")
async def delete_sale_event(
    sale_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a sale event."""
    service = SalesTrackingService(db)
    success = await service.delete_sale_event(current_user.id, sale_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Sale event not found")
    
    return {"message": "Sale event deleted successfully"}


@router.get("/metrics", response_model=SalesMetrics)
async def get_sales_metrics(
    start_date: Optional[datetime] = Query(None, description="Start date for metrics calculation"),
    end_date: Optional[datetime] = Query(None, description="End date for metrics calculation"),
    platforms: Optional[List[str]] = Query(None, description="Filter by platforms"),
    currency: str = Query("USD", description="Currency for calculations"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get sales metrics for a specified period."""
    # Default to last 30 days if no dates provided
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    service = SalesTrackingService(db)
    return await service.get_sales_metrics(
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        platforms=platforms,
        currency=currency
    )


@router.get("/dashboard", response_model=SalesDashboardData)
async def get_sales_dashboard(
    days: int = Query(30, ge=1, le=365, description="Number of days to include in dashboard"),
    currency: str = Query("USD", description="Currency for calculations"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive sales dashboard data."""
    service = SalesTrackingService(db)
    return await service.get_dashboard_data(
        user_id=current_user.id,
        days=days,
        currency=currency
    )


@router.post("/report")
async def generate_sales_report(
    report_request: SalesReportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a detailed sales report."""
    service = SalesTrackingService(db)
    
    # Get metrics
    metrics = await service.get_sales_metrics(
        user_id=current_user.id,
        start_date=report_request.start_date,
        end_date=report_request.end_date,
        platforms=report_request.platforms
    )
    
    # Get platform breakdown
    platform_breakdown = await service.get_platform_breakdown(
        user_id=current_user.id,
        start_date=report_request.start_date,
        end_date=report_request.end_date
    )
    
    # Get top products
    top_products = await service.get_top_products(
        user_id=current_user.id,
        start_date=report_request.start_date,
        end_date=report_request.end_date
    )
    
    # Get sales trend
    sales_trend = await service.get_sales_trend(
        user_id=current_user.id,
        start_date=report_request.start_date,
        end_date=report_request.end_date,
        group_by=report_request.group_by
    )
    
    report_data = {
        "report_period": {
            "start_date": report_request.start_date.isoformat(),
            "end_date": report_request.end_date.isoformat(),
            "group_by": report_request.group_by
        },
        "overall_metrics": metrics,
        "platform_breakdown": platform_breakdown,
        "top_products": top_products,
        "sales_trend": sales_trend,
        "generated_at": datetime.utcnow().isoformat()
    }
    
    # Include detailed sales if requested
    if report_request.include_details:
        sales_data = await service.get_sales_list(
            user_id=current_user.id,
            start_date=report_request.start_date,
            end_date=report_request.end_date,
            limit=10000  # Large limit for report
        )
        report_data["detailed_sales"] = sales_data["sales"]
    
    return report_data


@router.post("/sync/{platform}")
async def sync_platform_sales(
    platform: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Sync sales data from a specific platform."""
    sync_service = SalesSyncService(db)
    result = await sync_service.sync_platform_sales(current_user.id, platform)
    return result


@router.post("/sync")
async def sync_all_platforms(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Sync sales data from all connected platforms."""
    sync_service = SalesSyncService(db)
    result = await sync_service.sync_all_platforms(current_user.id)
    return result


@router.get("/sync/status")
async def get_sync_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get sync status for all platforms."""
    sync_service = SalesSyncService(db)
    result = await sync_service.get_sync_status(current_user.id)
    return result


@router.post("/manual")
async def create_manual_sale(
    sale_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a manual sale entry."""
    sync_service = SalesSyncService(db)
    result = await sync_service.create_manual_sale(current_user.id, sale_data)
    return result


@router.post("/bulk-import")
async def bulk_import_sales(
    sales_data: List[dict],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Bulk import sales data."""
    sync_service = SalesSyncService(db)
    result = await sync_service.bulk_import_sales(current_user.id, sales_data)
    return result


@router.get("/platforms")
async def get_sales_platforms(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of platforms with sales data."""
    service = SalesTrackingService(db)
    
    # Get unique platforms from user's sales
    from sqlalchemy import distinct
    from ..models import SaleEvent
    
    platforms = db.query(distinct(SaleEvent.platform)).filter(
        SaleEvent.user_id == current_user.id
    ).all()
    
    platform_list = [platform[0] for platform in platforms]
    
    return {
        "platforms": platform_list,
        "total_platforms": len(platform_list)
    }