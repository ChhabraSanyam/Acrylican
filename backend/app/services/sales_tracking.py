"""
Sales tracking service for managing sale events and analytics.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
from sqlalchemy.sql import extract

from ..models import SaleEvent, Product, User, Post
from ..schemas import (
    SaleEventCreate, SaleEventUpdate, SaleEventResponse,
    SalesMetrics, PlatformSalesBreakdown, SalesDashboardData,
    SalesReportRequest
)


class SalesTrackingService:
    """Service for tracking and analyzing sales data."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def create_sale_event(self, user_id: str, sale_data: SaleEventCreate) -> SaleEventResponse:
        """Create a new sale event."""
        # Calculate net amount if not provided
        net_amount = sale_data.net_amount
        if net_amount is None and sale_data.commission_amount is not None:
            net_amount = sale_data.amount - sale_data.commission_amount
        elif net_amount is None and sale_data.commission_rate is not None:
            commission = sale_data.amount * sale_data.commission_rate
            net_amount = sale_data.amount - commission
        else:
            net_amount = sale_data.amount
        
        # Calculate commission amount if not provided but rate is
        commission_amount = sale_data.commission_amount
        if commission_amount is None and sale_data.commission_rate is not None:
            commission_amount = sale_data.amount * sale_data.commission_rate
        
        sale_event = SaleEvent(
            user_id=user_id,
            product_id=sale_data.product_id,
            platform=sale_data.platform,
            order_id=sale_data.order_id,
            amount=Decimal(str(sale_data.amount)),
            currency=sale_data.currency,
            product_title=sale_data.product_title,
            product_sku=sale_data.product_sku,
            quantity=sale_data.quantity,
            customer_location=sale_data.customer_location,
            customer_type=sale_data.customer_type,
            sale_source=sale_data.sale_source,
            commission_rate=Decimal(str(sale_data.commission_rate)) if sale_data.commission_rate else None,
            commission_amount=Decimal(str(commission_amount)) if commission_amount else None,
            net_amount=Decimal(str(net_amount)),
            post_id=sale_data.post_id,
            referral_source=sale_data.referral_source,
            campaign_id=sale_data.campaign_id,
            occurred_at=sale_data.occurred_at,
            status=sale_data.status,
            platform_data=sale_data.platform_data
        )
        
        self.db.add(sale_event)
        self.db.commit()
        self.db.refresh(sale_event)
        
        return SaleEventResponse.model_validate(sale_event)
    
    async def get_sale_event(self, user_id: str, sale_id: str) -> Optional[SaleEventResponse]:
        """Get a specific sale event."""
        sale_event = self.db.query(SaleEvent).filter(
            and_(SaleEvent.id == sale_id, SaleEvent.user_id == user_id)
        ).first()
        
        if not sale_event:
            return None
        
        return SaleEventResponse.model_validate(sale_event)
    
    async def update_sale_event(self, user_id: str, sale_id: str, update_data: SaleEventUpdate) -> Optional[SaleEventResponse]:
        """Update a sale event."""
        sale_event = self.db.query(SaleEvent).filter(
            and_(SaleEvent.id == sale_id, SaleEvent.user_id == user_id)
        ).first()
        
        if not sale_event:
            return None
        
        # Update fields
        for field, value in update_data.model_dump(exclude_unset=True).items():
            if field in ['amount', 'commission_rate', 'commission_amount', 'net_amount'] and value is not None:
                value = Decimal(str(value))
            setattr(sale_event, field, value)
        
        # Recalculate commission and net amount if needed
        update_dict = update_data.model_dump(exclude_unset=True)
        if any(field in update_dict for field in ['amount', 'commission_rate', 'commission_amount']):
            # If commission_amount was explicitly updated, use it
            if 'commission_amount' in update_dict:
                sale_event.net_amount = sale_event.amount - (sale_event.commission_amount or Decimal('0'))
            # If amount or commission_rate changed, recalculate commission
            elif sale_event.commission_rate and ('amount' in update_dict or 'commission_rate' in update_dict):
                commission = sale_event.amount * sale_event.commission_rate
                sale_event.commission_amount = commission
                sale_event.net_amount = sale_event.amount - commission
            # If no commission info, net amount equals amount
            elif not sale_event.commission_amount and not sale_event.commission_rate:
                sale_event.net_amount = sale_event.amount
            # If only commission_amount exists (no rate), use existing commission_amount
            elif sale_event.commission_amount:
                sale_event.net_amount = sale_event.amount - sale_event.commission_amount
        
        self.db.commit()
        self.db.refresh(sale_event)
        
        return SaleEventResponse.model_validate(sale_event)
    
    async def delete_sale_event(self, user_id: str, sale_id: str) -> bool:
        """Delete a sale event."""
        sale_event = self.db.query(SaleEvent).filter(
            and_(SaleEvent.id == sale_id, SaleEvent.user_id == user_id)
        ).first()
        
        if not sale_event:
            return False
        
        self.db.delete(sale_event)
        self.db.commit()
        return True
    
    async def get_sales_list(
        self, 
        user_id: str, 
        skip: int = 0, 
        limit: int = 100,
        platform: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get paginated list of sale events with filters."""
        query = self.db.query(SaleEvent).filter(SaleEvent.user_id == user_id)
        
        # Apply filters
        if platform:
            query = query.filter(SaleEvent.platform == platform)
        if start_date:
            query = query.filter(SaleEvent.occurred_at >= start_date)
        if end_date:
            query = query.filter(SaleEvent.occurred_at <= end_date)
        if status:
            query = query.filter(SaleEvent.status == status)
        
        # Get total count
        total = query.count()
        
        # Get paginated results
        sales = query.order_by(desc(SaleEvent.occurred_at)).offset(skip).limit(limit).all()
        
        return {
            "sales": [SaleEventResponse.model_validate(sale) for sale in sales],
            "total": total,
            "skip": skip,
            "limit": limit
        }
    
    async def get_sales_metrics(
        self, 
        user_id: str, 
        start_date: datetime, 
        end_date: datetime,
        platforms: Optional[List[str]] = None,
        currency: str = "USD"
    ) -> SalesMetrics:
        """Calculate sales metrics for a given period."""
        query = self.db.query(SaleEvent).filter(
            and_(
                SaleEvent.user_id == user_id,
                SaleEvent.occurred_at >= start_date,
                SaleEvent.occurred_at <= end_date,
                SaleEvent.status == "confirmed",
                SaleEvent.currency == currency
            )
        )
        
        if platforms:
            query = query.filter(SaleEvent.platform.in_(platforms))
        
        sales = query.all()
        
        if not sales:
            return SalesMetrics(
                total_revenue=0.0,
                total_orders=0,
                average_order_value=0.0,
                total_commission=0.0,
                net_revenue=0.0,
                currency=currency,
                period_start=start_date,
                period_end=end_date
            )
        
        total_revenue = sum(float(sale.amount) for sale in sales)
        total_orders = len(sales)
        average_order_value = total_revenue / total_orders if total_orders > 0 else 0.0
        total_commission = sum(float(sale.commission_amount or 0) for sale in sales)
        net_revenue = sum(float(sale.net_amount or sale.amount) for sale in sales)
        
        return SalesMetrics(
            total_revenue=total_revenue,
            total_orders=total_orders,
            average_order_value=average_order_value,
            total_commission=total_commission,
            net_revenue=net_revenue,
            currency=currency,
            period_start=start_date,
            period_end=end_date
        )
    
    async def get_platform_breakdown(
        self, 
        user_id: str, 
        start_date: datetime, 
        end_date: datetime,
        currency: str = "USD"
    ) -> List[PlatformSalesBreakdown]:
        """Get sales breakdown by platform."""
        query = self.db.query(
            SaleEvent.platform,
            func.sum(SaleEvent.amount).label('total_revenue'),
            func.count(SaleEvent.id).label('total_orders'),
            func.avg(SaleEvent.amount).label('avg_order_value'),
            func.avg(SaleEvent.commission_rate).label('avg_commission_rate'),
            func.sum(SaleEvent.commission_amount).label('total_commission'),
            func.sum(SaleEvent.net_amount).label('net_revenue')
        ).filter(
            and_(
                SaleEvent.user_id == user_id,
                SaleEvent.occurred_at >= start_date,
                SaleEvent.occurred_at <= end_date,
                SaleEvent.status == "confirmed",
                SaleEvent.currency == currency
            )
        ).group_by(SaleEvent.platform)
        
        results = query.all()
        
        breakdown = []
        for result in results:
            # Get top products for this platform
            top_products_query = self.db.query(
                SaleEvent.product_title,
                func.sum(SaleEvent.amount).label('revenue'),
                func.count(SaleEvent.id).label('orders')
            ).filter(
                and_(
                    SaleEvent.user_id == user_id,
                    SaleEvent.platform == result.platform,
                    SaleEvent.occurred_at >= start_date,
                    SaleEvent.occurred_at <= end_date,
                    SaleEvent.status == "confirmed",
                    SaleEvent.product_title.isnot(None)
                )
            ).group_by(SaleEvent.product_title).order_by(desc('revenue')).limit(5)
            
            top_products = [
                {
                    "title": product.product_title,
                    "revenue": float(product.revenue),
                    "orders": product.orders
                }
                for product in top_products_query.all()
            ]
            
            breakdown.append(PlatformSalesBreakdown(
                platform=result.platform,
                total_revenue=float(result.total_revenue or 0),
                total_orders=result.total_orders or 0,
                average_order_value=float(result.avg_order_value or 0),
                commission_rate=float(result.avg_commission_rate or 0) if result.avg_commission_rate else None,
                total_commission=float(result.total_commission or 0),
                net_revenue=float(result.net_revenue or 0),
                top_products=top_products
            ))
        
        return breakdown
    
    async def get_top_products(
        self, 
        user_id: str, 
        start_date: datetime, 
        end_date: datetime,
        limit: int = 10,
        currency: str = "USD"
    ) -> List[Dict[str, Any]]:
        """Get top-performing products by revenue."""
        query = self.db.query(
            SaleEvent.product_id,
            SaleEvent.product_title,
            func.sum(SaleEvent.amount).label('total_revenue'),
            func.count(SaleEvent.id).label('total_orders'),
            func.sum(SaleEvent.quantity).label('total_quantity'),
            func.avg(SaleEvent.amount).label('avg_order_value')
        ).filter(
            and_(
                SaleEvent.user_id == user_id,
                SaleEvent.occurred_at >= start_date,
                SaleEvent.occurred_at <= end_date,
                SaleEvent.status == "confirmed",
                SaleEvent.currency == currency
            )
        ).group_by(SaleEvent.product_id, SaleEvent.product_title).order_by(desc('total_revenue')).limit(limit)
        
        results = query.all()
        
        return [
            {
                "product_id": result.product_id,
                "product_title": result.product_title,
                "total_revenue": float(result.total_revenue),
                "total_orders": result.total_orders,
                "total_quantity": result.total_quantity,
                "average_order_value": float(result.avg_order_value)
            }
            for result in results
        ]
    
    async def get_sales_trend(
        self, 
        user_id: str, 
        start_date: datetime, 
        end_date: datetime,
        group_by: str = "day",
        currency: str = "USD"
    ) -> List[Dict[str, Any]]:
        """Get sales trend data for charts."""
        # Use SQLite-compatible date functions
        if group_by == "day":
            date_part = func.date(SaleEvent.occurred_at)
        elif group_by == "week":
            # SQLite doesn't have week grouping, use day and group manually
            date_part = func.date(SaleEvent.occurred_at)
        elif group_by == "month":
            date_part = func.strftime('%Y-%m', SaleEvent.occurred_at)
        else:
            date_part = func.date(SaleEvent.occurred_at)
        
        query = self.db.query(
            date_part.label('period'),
            func.sum(SaleEvent.amount).label('revenue'),
            func.count(SaleEvent.id).label('orders')
        ).filter(
            and_(
                SaleEvent.user_id == user_id,
                SaleEvent.occurred_at >= start_date,
                SaleEvent.occurred_at <= end_date,
                SaleEvent.status == "confirmed",
                SaleEvent.currency == currency
            )
        ).group_by('period').order_by('period')
        
        results = query.all()
        
        trend_data = []
        for result in results:
            # Convert period to ISO format
            if group_by == "month":
                # For month format like '2025-09', convert to first day of month
                period_str = f"{result.period}-01T00:00:00"
            else:
                # For date format, add time component
                period_str = f"{result.period}T00:00:00"
            
            trend_data.append({
                "period": period_str,
                "revenue": float(result.revenue),
                "orders": result.orders
            })
        
        return trend_data
    
    async def get_dashboard_data(
        self, 
        user_id: str, 
        days: int = 30,
        currency: str = "USD"
    ) -> SalesDashboardData:
        """Get comprehensive dashboard data."""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get overall metrics
        overall_metrics = await self.get_sales_metrics(user_id, start_date, end_date, currency=currency)
        
        # Get platform breakdown
        platform_breakdown = await self.get_platform_breakdown(user_id, start_date, end_date, currency=currency)
        
        # Get top products
        top_products = await self.get_top_products(user_id, start_date, end_date, currency=currency)
        
        # Get recent sales
        recent_sales_data = await self.get_sales_list(user_id, skip=0, limit=10)
        recent_sales = recent_sales_data["sales"]
        
        # Get sales trend
        sales_trend = await self.get_sales_trend(user_id, start_date, end_date, group_by="day", currency=currency)
        
        return SalesDashboardData(
            overall_metrics=overall_metrics,
            platform_breakdown=platform_breakdown,
            top_products=top_products,
            recent_sales=recent_sales,
            sales_trend=sales_trend
        )
    
    async def sync_platform_sales(self, user_id: str, platform: str) -> Dict[str, Any]:
        """Sync sales data from a specific platform (placeholder for platform integrations)."""
        # This method would be implemented to fetch sales data from platform APIs
        # For now, it's a placeholder that returns sync status
        return {
            "platform": platform,
            "status": "not_implemented",
            "message": "Platform sales sync not yet implemented",
            "synced_count": 0,
            "last_sync": datetime.utcnow().isoformat()
        }