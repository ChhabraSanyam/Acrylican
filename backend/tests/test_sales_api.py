"""
Tests for sales tracking API endpoints.
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models import User, Product, SaleEvent
from app.schemas import SaleEventCreate


class TestSalesAPI:
    """Test cases for sales tracking API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)
    
    @pytest.fixture
    def test_user(self, db_session: Session):
        """Create a test user."""
        user = User(
            email="salestest@example.com",
            password_hash="hashed_password",
            business_name="Sales Test Business",
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
            title="API Test Product",
            description="A test product for API testing"
        )
        db_session.add(product)
        db_session.commit()
        db_session.refresh(product)
        return product
    
    @pytest.fixture
    def auth_headers(self, test_user: User):
        """Create authentication headers for test user."""
        # This would normally create a JWT token
        # For testing, we'll mock the authentication
        return {"Authorization": f"Bearer test-token-{test_user.id}"}
    
    @pytest.fixture
    def sample_sale_event(self, db_session: Session, test_user: User, test_product: Product):
        """Create a sample sale event in the database."""
        sale_event = SaleEvent(
            user_id=test_user.id,
            product_id=test_product.id,
            platform="etsy",
            order_id="API_TEST_ORDER",
            amount=49.99,
            currency="USD",
            product_title="API Test Product",
            quantity=1,
            commission_rate=0.065,
            commission_amount=3.25,
            net_amount=46.74,
            occurred_at=datetime.utcnow() - timedelta(days=1),
            status="confirmed"
        )
        db_session.add(sale_event)
        db_session.commit()
        db_session.refresh(sale_event)
        return sale_event
    
    def test_create_sale_event(self, client: TestClient, auth_headers: dict, test_product: Product):
        """Test creating a sale event via API."""
        sale_data = {
            "product_id": test_product.id,
            "platform": "facebook",
            "order_id": "FB_ORDER_123",
            "amount": 35.50,
            "currency": "USD",
            "product_title": "Facebook Test Product",
            "quantity": 2,
            "commission_rate": 0.03,
            "occurred_at": datetime.utcnow().isoformat(),
            "status": "confirmed"
        }
        
        response = client.post("/sales/events", json=sale_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["platform"] == "facebook"
        assert data["order_id"] == "FB_ORDER_123"
        assert data["amount"] == 35.50
        assert data["quantity"] == 2
        assert data["status"] == "confirmed"
        assert "commission_amount" in data
        assert "net_amount" in data
    
    def test_create_sale_event_validation_error(self, client: TestClient, auth_headers: dict):
        """Test creating a sale event with validation errors."""
        sale_data = {
            "platform": "etsy",
            "order_id": "INVALID_ORDER",
            "amount": -10.00,  # Invalid negative amount
            "currency": "USD",
            "occurred_at": datetime.utcnow().isoformat(),
            "status": "confirmed"
        }
        
        response = client.post("/sales/events", json=sale_data, headers=auth_headers)
        
        assert response.status_code == 422  # Validation error
    
    def test_get_sales_list(self, client: TestClient, auth_headers: dict, sample_sale_event: SaleEvent):
        """Test getting paginated sales list."""
        response = client.get("/sales/events", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "sales" in data
        assert "total" in data
        assert "skip" in data
        assert "limit" in data
        assert len(data["sales"]) >= 1
        
        # Check that our sample sale is in the list
        sale_ids = [sale["id"] for sale in data["sales"]]
        assert sample_sale_event.id in sale_ids
    
    def test_get_sales_list_with_filters(self, client: TestClient, auth_headers: dict, sample_sale_event: SaleEvent):
        """Test getting sales list with filters."""
        # Test platform filter
        response = client.get("/sales/events?platform=etsy", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        for sale in data["sales"]:
            assert sale["platform"] == "etsy"
        
        # Test date filter
        yesterday = (datetime.utcnow() - timedelta(days=1)).isoformat()
        response = client.get(f"/sales/events?start_date={yesterday}", headers=auth_headers)
        assert response.status_code == 200
        
        # Test pagination
        response = client.get("/sales/events?skip=0&limit=5", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["skip"] == 0
        assert data["limit"] == 5
    
    def test_get_sale_event(self, client: TestClient, auth_headers: dict, sample_sale_event: SaleEvent):
        """Test getting a specific sale event."""
        response = client.get(f"/sales/events/{sample_sale_event.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == sample_sale_event.id
        assert data["platform"] == "etsy"
        assert data["order_id"] == "API_TEST_ORDER"
        assert data["amount"] == 49.99
    
    def test_get_nonexistent_sale_event(self, client: TestClient, auth_headers: dict):
        """Test getting a non-existent sale event."""
        response = client.get("/sales/events/nonexistent-id", headers=auth_headers)
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_update_sale_event(self, client: TestClient, auth_headers: dict, sample_sale_event: SaleEvent):
        """Test updating a sale event."""
        update_data = {
            "amount": 59.99,
            "customer_location": "San Francisco, CA",
            "status": "refunded"
        }
        
        response = client.put(f"/sales/events/{sample_sale_event.id}", json=update_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["amount"] == 59.99
        assert data["customer_location"] == "San Francisco, CA"
        assert data["status"] == "refunded"
    
    def test_update_nonexistent_sale_event(self, client: TestClient, auth_headers: dict):
        """Test updating a non-existent sale event."""
        update_data = {"amount": 100.00}
        
        response = client.put("/sales/events/nonexistent-id", json=update_data, headers=auth_headers)
        
        assert response.status_code == 404
    
    def test_delete_sale_event(self, client: TestClient, auth_headers: dict, sample_sale_event: SaleEvent):
        """Test deleting a sale event."""
        response = client.delete(f"/sales/events/{sample_sale_event.id}", headers=auth_headers)
        
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]
        
        # Verify it's deleted
        response = client.get(f"/sales/events/{sample_sale_event.id}", headers=auth_headers)
        assert response.status_code == 404
    
    def test_delete_nonexistent_sale_event(self, client: TestClient, auth_headers: dict):
        """Test deleting a non-existent sale event."""
        response = client.delete("/sales/events/nonexistent-id", headers=auth_headers)
        
        assert response.status_code == 404
    
    def test_get_sales_metrics(self, client: TestClient, auth_headers: dict, sample_sale_event: SaleEvent):
        """Test getting sales metrics."""
        response = client.get("/sales/metrics", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total_revenue" in data
        assert "total_orders" in data
        assert "average_order_value" in data
        assert "total_commission" in data
        assert "net_revenue" in data
        assert "currency" in data
        assert "period_start" in data
        assert "period_end" in data
        
        # Should include our sample sale
        assert data["total_revenue"] >= 49.99
        assert data["total_orders"] >= 1
    
    def test_get_sales_metrics_with_date_range(self, client: TestClient, auth_headers: dict):
        """Test getting sales metrics with custom date range."""
        start_date = (datetime.utcnow() - timedelta(days=7)).isoformat()
        end_date = datetime.utcnow().isoformat()
        
        response = client.get(f"/sales/metrics?start_date={start_date}&end_date={end_date}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["period_start"] == start_date
        assert data["period_end"] == end_date
    
    def test_get_sales_dashboard(self, client: TestClient, auth_headers: dict, sample_sale_event: SaleEvent):
        """Test getting sales dashboard data."""
        response = client.get("/sales/dashboard", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "overall_metrics" in data
        assert "platform_breakdown" in data
        assert "top_products" in data
        assert "recent_sales" in data
        assert "sales_trend" in data
        
        # Check overall metrics structure
        metrics = data["overall_metrics"]
        assert "total_revenue" in metrics
        assert "total_orders" in metrics
        
        # Check platform breakdown
        assert isinstance(data["platform_breakdown"], list)
        
        # Check recent sales
        assert isinstance(data["recent_sales"], list)
    
    def test_get_sales_dashboard_with_custom_period(self, client: TestClient, auth_headers: dict):
        """Test getting sales dashboard with custom period."""
        response = client.get("/sales/dashboard?days=7&currency=USD", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["overall_metrics"]["currency"] == "USD"
    
    def test_generate_sales_report(self, client: TestClient, auth_headers: dict, sample_sale_event: SaleEvent):
        """Test generating a sales report."""
        report_data = {
            "start_date": (datetime.utcnow() - timedelta(days=30)).isoformat(),
            "end_date": datetime.utcnow().isoformat(),
            "group_by": "day",
            "include_details": True
        }
        
        response = client.post("/sales/report", json=report_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "report_period" in data
        assert "overall_metrics" in data
        assert "platform_breakdown" in data
        assert "top_products" in data
        assert "sales_trend" in data
        assert "detailed_sales" in data  # Because include_details=True
        assert "generated_at" in data
        
        # Check report period
        assert data["report_period"]["group_by"] == "day"
    
    def test_generate_sales_report_without_details(self, client: TestClient, auth_headers: dict):
        """Test generating a sales report without detailed sales."""
        report_data = {
            "start_date": (datetime.utcnow() - timedelta(days=7)).isoformat(),
            "end_date": datetime.utcnow().isoformat(),
            "group_by": "week",
            "include_details": False
        }
        
        response = client.post("/sales/report", json=report_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "detailed_sales" not in data  # Should not include details
        assert data["report_period"]["group_by"] == "week"
    
    def test_sync_platform_sales(self, client: TestClient, auth_headers: dict):
        """Test syncing platform sales (placeholder)."""
        response = client.post("/sales/sync/etsy", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["platform"] == "etsy"
        assert data["status"] == "not_implemented"
        assert "synced_count" in data
        assert "last_sync" in data
    
    def test_get_sales_platforms(self, client: TestClient, auth_headers: dict, sample_sale_event: SaleEvent):
        """Test getting list of platforms with sales data."""
        response = client.get("/sales/platforms", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "platforms" in data
        assert "total_platforms" in data
        assert isinstance(data["platforms"], list)
        
        # Should include etsy from our sample sale
        assert "etsy" in data["platforms"]
    
    def test_unauthorized_access(self, client: TestClient):
        """Test accessing sales endpoints without authentication."""
        response = client.get("/sales/events")
        
        # Should return 401 or 403 (depending on auth implementation)
        assert response.status_code in [401, 403]
    
    def test_sales_metrics_validation(self, client: TestClient, auth_headers: dict):
        """Test sales metrics endpoint with invalid parameters."""
        # Test invalid currency
        response = client.get("/sales/metrics?currency=INVALID", headers=auth_headers)
        
        # Should still work but return empty results
        assert response.status_code == 200
        
        # Test invalid date format
        response = client.get("/sales/metrics?start_date=invalid-date", headers=auth_headers)
        
        assert response.status_code == 422  # Validation error