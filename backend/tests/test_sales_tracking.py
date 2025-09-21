"""
Tests for sales tracking functionality.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models import User, Product, SaleEvent
from app.schemas import SaleEventCreate, SaleEventUpdate
from app.services.sales_tracking import SalesTrackingService


class TestSalesTrackingService:
    """Test cases for SalesTrackingService."""
    
    @pytest.fixture
    def sales_service(self, db_session: Session):
        """Create a SalesTrackingService instance."""
        return SalesTrackingService(db_session)
    
    @pytest.fixture
    def test_user(self, db_session: Session):
        """Create a test user."""
        user = User(
            email="testuser@example.com",
            password_hash="hashed_password",
            business_name="Test Business",
            business_type="Artisan"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user
    
    @pytest.fixture
    def test_product(self, db_session: Session, test_user: User):
        """Create a test product."""
        product = Product(
            user_id=test_user.id,
            title="Test Product",
            description="A test product for sales tracking"
        )
        db_session.add(product)
        db_session.commit()
        db_session.refresh(product)
        return product
    
    @pytest.fixture
    def sample_sale_data(self, test_product: Product):
        """Create sample sale event data."""
        return SaleEventCreate(
            product_id=test_product.id,
            platform="etsy",
            order_id="ORDER123",
            amount=29.99,
            currency="USD",
            product_title="Test Product",
            product_sku="TEST-001",
            quantity=1,
            customer_location="New York, NY",
            customer_type="new",
            sale_source="organic",
            commission_rate=0.065,  # 6.5% commission
            occurred_at=datetime.utcnow(),
            status="confirmed"
        )
    
    @pytest.mark.asyncio
    async def test_create_sale_event(self, sales_service: SalesTrackingService, test_user: User, sample_sale_data: SaleEventCreate):
        """Test creating a sale event."""
        result = await sales_service.create_sale_event(test_user.id, sample_sale_data)
        
        assert result.user_id == test_user.id
        assert result.platform == "etsy"
        assert result.order_id == "ORDER123"
        assert result.amount == 29.99
        assert result.currency == "USD"
        assert result.quantity == 1
        assert result.status == "confirmed"
        
        # Check calculated fields
        expected_commission = 29.99 * 0.065
        expected_net = 29.99 - expected_commission
        assert abs(result.commission_amount - expected_commission) < 0.01
        assert abs(result.net_amount - expected_net) < 0.01
    
    @pytest.mark.asyncio
    async def test_create_sale_event_with_commission_amount(self, sales_service: SalesTrackingService, test_user: User, test_product: Product):
        """Test creating a sale event with explicit commission amount."""
        sale_data = SaleEventCreate(
            product_id=test_product.id,
            platform="facebook",
            order_id="FB456",
            amount=50.00,
            currency="USD",
            commission_amount=5.00,  # Explicit commission
            occurred_at=datetime.utcnow(),
            status="confirmed"
        )
        
        result = await sales_service.create_sale_event(test_user.id, sale_data)
        
        assert result.commission_amount == 5.00
        assert result.net_amount == 45.00
    
    @pytest.mark.asyncio
    async def test_get_sale_event(self, sales_service: SalesTrackingService, test_user: User, sample_sale_data: SaleEventCreate):
        """Test retrieving a sale event."""
        created_sale = await sales_service.create_sale_event(test_user.id, sample_sale_data)
        
        retrieved_sale = await sales_service.get_sale_event(test_user.id, created_sale.id)
        
        assert retrieved_sale is not None
        assert retrieved_sale.id == created_sale.id
        assert retrieved_sale.platform == "etsy"
        assert retrieved_sale.amount == 29.99
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_sale_event(self, sales_service: SalesTrackingService, test_user: User):
        """Test retrieving a non-existent sale event."""
        result = await sales_service.get_sale_event(test_user.id, "nonexistent-id")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_update_sale_event(self, sales_service: SalesTrackingService, test_user: User, sample_sale_data: SaleEventCreate):
        """Test updating a sale event."""
        created_sale = await sales_service.create_sale_event(test_user.id, sample_sale_data)
        
        update_data = SaleEventUpdate(
            amount=39.99,
            customer_location="Los Angeles, CA",
            status="refunded"
        )
        
        updated_sale = await sales_service.update_sale_event(test_user.id, created_sale.id, update_data)
        
        assert updated_sale is not None
        assert updated_sale.amount == 39.99
        assert updated_sale.customer_location == "Los Angeles, CA"
        assert updated_sale.status == "refunded"
        
        # Net amount should be recalculated
        expected_commission = 39.99 * 0.065
        expected_net = 39.99 - expected_commission
        assert abs(updated_sale.net_amount - expected_net) < 0.01
    
    @pytest.mark.asyncio
    async def test_delete_sale_event(self, sales_service: SalesTrackingService, test_user: User, sample_sale_data: SaleEventCreate):
        """Test deleting a sale event."""
        created_sale = await sales_service.create_sale_event(test_user.id, sample_sale_data)
        
        success = await sales_service.delete_sale_event(test_user.id, created_sale.id)
        assert success is True
        
        # Verify it's deleted
        retrieved_sale = await sales_service.get_sale_event(test_user.id, created_sale.id)
        assert retrieved_sale is None
    
    @pytest.mark.asyncio
    async def test_get_sales_list(self, sales_service: SalesTrackingService, test_user: User, test_product: Product):
        """Test getting paginated sales list."""
        # Create multiple sales
        sales_data = []
        for i in range(5):
            sale_data = SaleEventCreate(
                product_id=test_product.id,
                platform="etsy" if i % 2 == 0 else "facebook",
                order_id=f"ORDER{i}",
                amount=20.00 + i * 5,
                currency="USD",
                occurred_at=datetime.utcnow() - timedelta(days=i),
                status="confirmed"
            )
            await sales_service.create_sale_event(test_user.id, sale_data)
        
        # Test pagination
        result = await sales_service.get_sales_list(test_user.id, skip=0, limit=3)
        
        assert len(result["sales"]) == 3
        assert result["total"] == 5
        assert result["skip"] == 0
        assert result["limit"] == 3
        
        # Test platform filter
        result = await sales_service.get_sales_list(test_user.id, platform="etsy")
        assert len(result["sales"]) == 3  # 3 etsy sales (indices 0, 2, 4)
        
        # Test date filter - get sales from 2 days ago onwards (should include 3 sales: today, yesterday, 2 days ago)
        two_days_ago = datetime.utcnow() - timedelta(days=2, hours=1)  # Add hour buffer to ensure we catch all
        result = await sales_service.get_sales_list(test_user.id, start_date=two_days_ago)
        assert len(result["sales"]) == 3  # Sales from today, yesterday, and 2 days ago
    
    @pytest.mark.asyncio
    async def test_get_sales_metrics(self, sales_service: SalesTrackingService, test_user: User, test_product: Product):
        """Test calculating sales metrics."""
        # Create test sales
        sales_data = [
            SaleEventCreate(
                product_id=test_product.id,
                platform="etsy",
                order_id="ORDER1",
                amount=30.00,
                currency="USD",
                commission_rate=0.05,
                occurred_at=datetime.utcnow() - timedelta(days=1),
                status="confirmed"
            ),
            SaleEventCreate(
                product_id=test_product.id,
                platform="facebook",
                order_id="ORDER2",
                amount=50.00,
                currency="USD",
                commission_rate=0.03,
                occurred_at=datetime.utcnow() - timedelta(days=2),
                status="confirmed"
            ),
            SaleEventCreate(
                product_id=test_product.id,
                platform="etsy",
                order_id="ORDER3",
                amount=25.00,
                currency="USD",
                commission_rate=0.05,
                occurred_at=datetime.utcnow() - timedelta(days=3),
                status="pending"  # Should be excluded
            )
        ]
        
        for sale_data in sales_data:
            await sales_service.create_sale_event(test_user.id, sale_data)
        
        # Calculate metrics for last 7 days
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)
        
        metrics = await sales_service.get_sales_metrics(test_user.id, start_date, end_date)
        
        assert metrics.total_revenue == 80.00  # Only confirmed sales
        assert metrics.total_orders == 2
        assert metrics.average_order_value == 40.00
        assert abs(metrics.total_commission - 3.00) < 0.01  # 30*0.05 + 50*0.03
        assert abs(metrics.net_revenue - 77.00) < 0.01  # 80 - 3
        assert metrics.currency == "USD"
    
    @pytest.mark.asyncio
    async def test_get_platform_breakdown(self, sales_service: SalesTrackingService, test_user: User, test_product: Product):
        """Test getting platform sales breakdown."""
        # Create sales on different platforms
        sales_data = [
            SaleEventCreate(
                product_id=test_product.id,
                platform="etsy",
                order_id="ETSY1",
                amount=30.00,
                currency="USD",
                commission_rate=0.065,
                product_title="Handmade Jewelry",
                occurred_at=datetime.utcnow() - timedelta(days=1),
                status="confirmed"
            ),
            SaleEventCreate(
                product_id=test_product.id,
                platform="etsy",
                order_id="ETSY2",
                amount=45.00,
                currency="USD",
                commission_rate=0.065,
                product_title="Handmade Jewelry",
                occurred_at=datetime.utcnow() - timedelta(days=2),
                status="confirmed"
            ),
            SaleEventCreate(
                product_id=test_product.id,
                platform="facebook",
                order_id="FB1",
                amount=60.00,
                currency="USD",
                commission_rate=0.03,
                product_title="Custom Art",
                occurred_at=datetime.utcnow() - timedelta(days=1),
                status="confirmed"
            )
        ]
        
        for sale_data in sales_data:
            await sales_service.create_sale_event(test_user.id, sale_data)
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)
        
        breakdown = await sales_service.get_platform_breakdown(test_user.id, start_date, end_date)
        
        # Should have 2 platforms
        assert len(breakdown) == 2
        
        # Find Etsy breakdown
        etsy_breakdown = next((b for b in breakdown if b.platform == "etsy"), None)
        assert etsy_breakdown is not None
        assert etsy_breakdown.total_revenue == 75.00
        assert etsy_breakdown.total_orders == 2
        assert etsy_breakdown.average_order_value == 37.50
        assert len(etsy_breakdown.top_products) == 1
        assert etsy_breakdown.top_products[0]["title"] == "Handmade Jewelry"
        
        # Find Facebook breakdown
        fb_breakdown = next((b for b in breakdown if b.platform == "facebook"), None)
        assert fb_breakdown is not None
        assert fb_breakdown.total_revenue == 60.00
        assert fb_breakdown.total_orders == 1
    
    @pytest.mark.asyncio
    async def test_get_top_products(self, sales_service: SalesTrackingService, test_user: User, test_product: Product):
        """Test getting top products by revenue."""
        # Create sales for different products
        sales_data = [
            SaleEventCreate(
                product_id=test_product.id,
                platform="etsy",
                order_id="ORDER1",
                amount=100.00,
                currency="USD",
                product_title="Premium Product",
                quantity=1,
                occurred_at=datetime.utcnow() - timedelta(days=1),
                status="confirmed"
            ),
            SaleEventCreate(
                product_id=test_product.id,
                platform="facebook",
                order_id="ORDER2",
                amount=50.00,
                currency="USD",
                product_title="Premium Product",
                quantity=2,
                occurred_at=datetime.utcnow() - timedelta(days=2),
                status="confirmed"
            ),
            SaleEventCreate(
                product_id=None,  # No product linked
                platform="etsy",
                order_id="ORDER3",
                amount=30.00,
                currency="USD",
                product_title="Basic Product",
                quantity=1,
                occurred_at=datetime.utcnow() - timedelta(days=1),
                status="confirmed"
            )
        ]
        
        for sale_data in sales_data:
            await sales_service.create_sale_event(test_user.id, sale_data)
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)
        
        top_products = await sales_service.get_top_products(test_user.id, start_date, end_date, limit=5)
        
        assert len(top_products) == 2
        
        # First product should be Premium Product with highest revenue
        assert top_products[0]["product_title"] == "Premium Product"
        assert top_products[0]["total_revenue"] == 150.00
        assert top_products[0]["total_orders"] == 2
        assert top_products[0]["total_quantity"] == 3
        
        # Second product should be Basic Product
        assert top_products[1]["product_title"] == "Basic Product"
        assert top_products[1]["total_revenue"] == 30.00
    
    @pytest.mark.asyncio
    async def test_get_sales_trend(self, sales_service: SalesTrackingService, test_user: User, test_product: Product):
        """Test getting sales trend data."""
        # Create sales over multiple days
        base_date = datetime.utcnow().replace(hour=12, minute=0, second=0, microsecond=0)
        
        sales_data = [
            SaleEventCreate(
                product_id=test_product.id,
                platform="etsy",
                order_id="DAY1_1",
                amount=30.00,
                currency="USD",
                occurred_at=base_date - timedelta(days=2),
                status="confirmed"
            ),
            SaleEventCreate(
                product_id=test_product.id,
                platform="facebook",
                order_id="DAY1_2",
                amount=45.00,
                currency="USD",
                occurred_at=base_date - timedelta(days=2),
                status="confirmed"
            ),
            SaleEventCreate(
                product_id=test_product.id,
                platform="etsy",
                order_id="DAY2_1",
                amount=60.00,
                currency="USD",
                occurred_at=base_date - timedelta(days=1),
                status="confirmed"
            )
        ]
        
        for sale_data in sales_data:
            await sales_service.create_sale_event(test_user.id, sale_data)
        
        end_date = base_date
        start_date = base_date - timedelta(days=3)
        
        trend = await sales_service.get_sales_trend(test_user.id, start_date, end_date, group_by="day")
        
        # Should have data for 2 days (days with sales)
        assert len(trend) == 2
        
        # Check first day (2 days ago)
        day1 = next((t for t in trend if t["revenue"] == 75.00), None)
        assert day1 is not None
        assert day1["orders"] == 2
        
        # Check second day (1 day ago)
        day2 = next((t for t in trend if t["revenue"] == 60.00), None)
        assert day2 is not None
        assert day2["orders"] == 1
    
    @pytest.mark.asyncio
    async def test_get_dashboard_data(self, sales_service: SalesTrackingService, test_user: User, test_product: Product):
        """Test getting comprehensive dashboard data."""
        # Create some test sales
        sales_data = [
            SaleEventCreate(
                product_id=test_product.id,
                platform="etsy",
                order_id="DASH1",
                amount=50.00,
                currency="USD",
                commission_rate=0.05,
                product_title="Dashboard Product",
                occurred_at=datetime.utcnow() - timedelta(days=1),
                status="confirmed"
            ),
            SaleEventCreate(
                product_id=test_product.id,
                platform="facebook",
                order_id="DASH2",
                amount=75.00,
                currency="USD",
                commission_rate=0.03,
                product_title="Dashboard Product",
                occurred_at=datetime.utcnow() - timedelta(days=2),
                status="confirmed"
            )
        ]
        
        for sale_data in sales_data:
            await sales_service.create_sale_event(test_user.id, sale_data)
        
        dashboard_data = await sales_service.get_dashboard_data(test_user.id, days=30)
        
        # Check overall metrics
        assert dashboard_data.overall_metrics.total_revenue == 125.00
        assert dashboard_data.overall_metrics.total_orders == 2
        
        # Check platform breakdown
        assert len(dashboard_data.platform_breakdown) == 2
        
        # Check top products
        assert len(dashboard_data.top_products) == 1
        assert dashboard_data.top_products[0]["product_title"] == "Dashboard Product"
        
        # Check recent sales
        assert len(dashboard_data.recent_sales) == 2
        
        # Check sales trend
        assert len(dashboard_data.sales_trend) >= 1
    
    @pytest.mark.asyncio
    async def test_sync_platform_sales_placeholder(self, sales_service: SalesTrackingService, test_user: User):
        """Test platform sales sync placeholder."""
        result = await sales_service.sync_platform_sales(test_user.id, "etsy")
        
        assert result["platform"] == "etsy"
        assert result["status"] == "not_implemented"
        assert result["synced_count"] == 0
        assert "last_sync" in result