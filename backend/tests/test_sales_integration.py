"""
Integration tests for sales tracking API.
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch

from app.main import app
from app.models import User, Product, SaleEvent
from app.dependencies import get_current_user


class TestSalesIntegration:
    """Integration tests for sales tracking functionality."""
    
    @pytest.fixture
    def test_user(self, db_session: Session):
        """Create a test user."""
        user = User(
            email="integration@example.com",
            password_hash="hashed_password",
            business_name="Integration Test Business",
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
            title="Integration Test Product",
            description="A test product for integration testing"
        )
        db_session.add(product)
        db_session.commit()
        db_session.refresh(product)
        return product
    
    @pytest.fixture
    def authenticated_client(self, client: TestClient, test_user: User):
        """Create an authenticated test client."""
        # Mock the get_current_user dependency to return our test user
        def mock_get_current_user():
            return test_user
        
        app.dependency_overrides[get_current_user] = mock_get_current_user
        yield client
        # Clean up the override
        if get_current_user in app.dependency_overrides:
            del app.dependency_overrides[get_current_user]
    
    def test_create_and_retrieve_sale_event(self, authenticated_client: TestClient, test_product: Product):
        """Test creating and retrieving a sale event through the API."""
        # Create a sale event
        sale_data = {
            "product_id": test_product.id,
            "platform": "etsy",
            "order_id": "INTEGRATION_TEST_001",
            "amount": 45.99,
            "currency": "USD",
            "product_title": "Integration Test Product",
            "quantity": 1,
            "commission_rate": 0.065,
            "occurred_at": datetime.utcnow().isoformat(),
            "status": "confirmed"
        }
        
        # Create the sale event
        response = authenticated_client.post("/sales/events", json=sale_data)
        assert response.status_code == 200
        
        created_sale = response.json()
        assert created_sale["platform"] == "etsy"
        assert created_sale["order_id"] == "INTEGRATION_TEST_001"
        assert created_sale["amount"] == 45.99
        assert "commission_amount" in created_sale
        assert "net_amount" in created_sale
        
        sale_id = created_sale["id"]
        
        # Retrieve the sale event
        response = authenticated_client.get(f"/sales/events/{sale_id}")
        assert response.status_code == 200
        
        retrieved_sale = response.json()
        assert retrieved_sale["id"] == sale_id
        assert retrieved_sale["platform"] == "etsy"
        assert retrieved_sale["amount"] == 45.99
    
    def test_sales_list_and_metrics(self, authenticated_client: TestClient, test_product: Product):
        """Test sales list and metrics endpoints."""
        # Create multiple sale events
        sales_data = [
            {
                "product_id": test_product.id,
                "platform": "etsy",
                "order_id": "METRICS_TEST_001",
                "amount": 30.00,
                "currency": "USD",
                "occurred_at": (datetime.utcnow() - timedelta(days=1)).isoformat(),
                "status": "confirmed"
            },
            {
                "product_id": test_product.id,
                "platform": "facebook",
                "order_id": "METRICS_TEST_002",
                "amount": 50.00,
                "currency": "USD",
                "occurred_at": (datetime.utcnow() - timedelta(days=2)).isoformat(),
                "status": "confirmed"
            }
        ]
        
        # Create the sales
        for sale_data in sales_data:
            response = authenticated_client.post("/sales/events", json=sale_data)
            assert response.status_code == 200
        
        # Test sales list
        response = authenticated_client.get("/sales/events")
        assert response.status_code == 200
        
        sales_list = response.json()
        assert "sales" in sales_list
        assert "total" in sales_list
        assert len(sales_list["sales"]) == 2
        assert sales_list["total"] == 2
        
        # Test sales metrics
        response = authenticated_client.get("/sales/metrics")
        assert response.status_code == 200
        
        metrics = response.json()
        assert "total_revenue" in metrics
        assert "total_orders" in metrics
        assert metrics["total_revenue"] == 80.00
        assert metrics["total_orders"] == 2
        assert metrics["average_order_value"] == 40.00
    
    def test_sales_dashboard(self, authenticated_client: TestClient, test_product: Product):
        """Test sales dashboard endpoint."""
        # Create a sale event for dashboard data
        sale_data = {
            "product_id": test_product.id,
            "platform": "etsy",
            "order_id": "DASHBOARD_TEST_001",
            "amount": 75.00,
            "currency": "USD",
            "product_title": "Dashboard Test Product",
            "commission_rate": 0.05,
            "occurred_at": datetime.utcnow().isoformat(),
            "status": "confirmed"
        }
        
        response = authenticated_client.post("/sales/events", json=sale_data)
        assert response.status_code == 200
        
        # Get dashboard data
        response = authenticated_client.get("/sales/dashboard")
        assert response.status_code == 200
        
        dashboard = response.json()
        assert "overall_metrics" in dashboard
        assert "platform_breakdown" in dashboard
        assert "top_products" in dashboard
        assert "recent_sales" in dashboard
        assert "sales_trend" in dashboard
        
        # Check overall metrics
        metrics = dashboard["overall_metrics"]
        assert metrics["total_revenue"] == 75.00
        assert metrics["total_orders"] == 1
        
        # Check platform breakdown
        assert len(dashboard["platform_breakdown"]) == 1
        assert dashboard["platform_breakdown"][0]["platform"] == "etsy"
        
        # Check recent sales
        assert len(dashboard["recent_sales"]) == 1
        assert dashboard["recent_sales"][0]["order_id"] == "DASHBOARD_TEST_001"
    
    def test_update_and_delete_sale_event(self, authenticated_client: TestClient, test_product: Product):
        """Test updating and deleting a sale event."""
        # Create a sale event
        sale_data = {
            "product_id": test_product.id,
            "platform": "facebook",
            "order_id": "UPDATE_DELETE_TEST",
            "amount": 25.00,
            "currency": "USD",
            "occurred_at": datetime.utcnow().isoformat(),
            "status": "confirmed"
        }
        
        response = authenticated_client.post("/sales/events", json=sale_data)
        assert response.status_code == 200
        sale_id = response.json()["id"]
        
        # Update the sale event
        update_data = {
            "amount": 35.00,
            "customer_location": "Test City, TS",
            "status": "refunded"
        }
        
        response = authenticated_client.put(f"/sales/events/{sale_id}", json=update_data)
        assert response.status_code == 200
        
        updated_sale = response.json()
        assert updated_sale["amount"] == 35.00
        assert updated_sale["customer_location"] == "Test City, TS"
        assert updated_sale["status"] == "refunded"
        
        # Delete the sale event
        response = authenticated_client.delete(f"/sales/events/{sale_id}")
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]
        
        # Verify it's deleted
        response = authenticated_client.get(f"/sales/events/{sale_id}")
        assert response.status_code == 404
    
    def test_sales_report_generation(self, authenticated_client: TestClient, test_product: Product):
        """Test sales report generation."""
        # Create a sale event
        sale_data = {
            "product_id": test_product.id,
            "platform": "pinterest",
            "order_id": "REPORT_TEST_001",
            "amount": 60.00,
            "currency": "USD",
            "product_title": "Report Test Product",
            "occurred_at": datetime.utcnow().isoformat(),
            "status": "confirmed"
        }
        
        response = authenticated_client.post("/sales/events", json=sale_data)
        assert response.status_code == 200
        
        # Generate a report
        report_request = {
            "start_date": (datetime.utcnow() - timedelta(days=7)).isoformat(),
            "end_date": datetime.utcnow().isoformat(),
            "group_by": "day",
            "include_details": True
        }
        
        response = authenticated_client.post("/sales/report", json=report_request)
        assert response.status_code == 200
        
        report = response.json()
        assert "report_period" in report
        assert "overall_metrics" in report
        assert "platform_breakdown" in report
        assert "top_products" in report
        assert "sales_trend" in report
        assert "detailed_sales" in report
        assert "generated_at" in report
        
        # Check report content
        assert report["overall_metrics"]["total_revenue"] == 60.00
        assert len(report["platform_breakdown"]) == 1
        assert report["platform_breakdown"][0]["platform"] == "pinterest"
    
    def test_platform_sync_placeholder(self, authenticated_client: TestClient):
        """Test platform sync endpoint (placeholder)."""
        response = authenticated_client.post("/sales/sync/etsy")
        assert response.status_code == 200
        
        sync_result = response.json()
        assert sync_result["platform"] == "etsy"
        # Since no platform connection exists, it should return "no_connection"
        assert sync_result["status"] == "no_connection"
        assert "synced_count" in sync_result
        assert sync_result["synced_count"] == 0
    
    def test_get_sales_platforms(self, authenticated_client: TestClient, test_product: Product):
        """Test getting list of platforms with sales data."""
        # Create sales on different platforms
        platforms = ["etsy", "facebook", "pinterest"]
        for i, platform in enumerate(platforms):
            sale_data = {
                "product_id": test_product.id,
                "platform": platform,
                "order_id": f"PLATFORM_TEST_{i}",
                "amount": 20.00 + i * 10,
                "currency": "USD",
                "occurred_at": datetime.utcnow().isoformat(),
                "status": "confirmed"
            }
            
            response = authenticated_client.post("/sales/events", json=sale_data)
            assert response.status_code == 200
        
        # Get platforms list
        response = authenticated_client.get("/sales/platforms")
        assert response.status_code == 200
        
        platforms_data = response.json()
        assert "platforms" in platforms_data
        assert "total_platforms" in platforms_data
        assert platforms_data["total_platforms"] == 3
        
        # Check that all platforms are included
        returned_platforms = set(platforms_data["platforms"])
        expected_platforms = {"etsy", "facebook", "pinterest"}
        assert returned_platforms == expected_platforms