"""
Tests for OAuth API Routes

This module contains tests for the OAuth authentication API endpoints.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

from app.main import app
from app.models import User, PlatformConnection
from app.services.platform_integration import Platform, AuthenticationMethod


class TestOAuthRoutes:
    """Test OAuth API routes"""
    
    @pytest.fixture
    def client(self):
        """Test client"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_user(self):
        """Mock authenticated user"""
        return User(
            id="user123",
            email="test@example.com",
            business_name="Test Business",
            business_type="Handmade",
            is_active=True
        )
    
    @pytest.fixture
    def mock_connection(self):
        """Mock platform connection"""
        return PlatformConnection(
            id="conn123",
            user_id="user123",
            platform=Platform.FACEBOOK.value,
            integration_type="api",
            auth_method=AuthenticationMethod.OAUTH2.value,
            access_token="encrypted_token",
            is_active=True,
            platform_username="test_user",
            connected_at=datetime.utcnow(),
            last_validated_at=datetime.utcnow()
        )
    
    def test_get_supported_platforms(self, client):
        """Test getting supported platforms"""
        response = client.get("/auth/platforms")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "platforms" in data
        platforms = data["platforms"]
        
        # Check that all required platforms are present
        platform_ids = [p["id"] for p in platforms]
        assert "facebook" in platform_ids
        assert "instagram" in platform_ids
        assert "etsy" in platform_ids
        assert "pinterest" in platform_ids
        assert "shopify" in platform_ids
        
        # Check platform structure
        for platform in platforms:
            assert "id" in platform
            assert "name" in platform
            assert "description" in platform
    
    @patch('app.routers.oauth.get_current_user')
    @patch('app.routers.oauth.get_oauth_service')
    def test_get_user_connections(self, mock_oauth_service, mock_get_user, client, mock_user, mock_connection):
        """Test getting user connections"""
        mock_get_user.return_value = mock_user
        
        mock_service = AsyncMock()
        mock_service.get_user_connections.return_value = [mock_connection]
        mock_oauth_service.return_value = mock_service
        
        response = client.get("/auth/connections")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 1
        connection = data[0]
        assert connection["platform"] == "facebook"
        assert connection["is_active"] is True
        assert connection["platform_username"] == "test_user"
    
    @patch('app.routers.oauth.get_current_user')
    @patch('app.routers.oauth.get_oauth_service')
    async def test_initiate_oauth_flow(self, mock_oauth_service, mock_get_user, client, mock_user):
        """Test initiating OAuth flow"""
        mock_get_user.return_value = mock_user
        
        mock_service = AsyncMock()
        mock_service.get_authorization_url.return_value = (
            "https://facebook.com/oauth/authorize?client_id=123",
            "state123"
        )
        mock_oauth_service.return_value = mock_service
        
        response = client.post("/auth/facebook/connect")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "authorization_url" in data
        assert "state" in data
        assert "facebook.com" in data["authorization_url"]
    
    @patch('app.routers.oauth.get_current_user')
    @patch('app.routers.oauth.get_oauth_service')
    def test_initiate_oauth_flow_invalid_platform(self, mock_oauth_service, mock_get_user, client, mock_user):
        """Test initiating OAuth flow with invalid platform"""
        mock_get_user.return_value = mock_user
        
        response = client.post("/auth/invalid_platform/connect")
        
        assert response.status_code == 400
        assert "Unsupported platform" in response.json()["detail"]
    
    @patch('app.routers.oauth.get_current_user')
    @patch('app.routers.oauth.get_oauth_service')
    def test_initiate_shopify_oauth_without_domain(self, mock_oauth_service, mock_get_user, client, mock_user):
        """Test initiating Shopify OAuth without shop domain"""
        mock_get_user.return_value = mock_user
        
        response = client.post("/auth/shopify/connect")
        
        assert response.status_code == 400
        assert "shop_domain parameter is required" in response.json()["detail"]
    
    @patch('app.routers.oauth.get_current_user')
    @patch('app.routers.oauth.get_oauth_service')
    async def test_initiate_shopify_oauth_with_domain(self, mock_oauth_service, mock_get_user, client, mock_user):
        """Test initiating Shopify OAuth with shop domain"""
        mock_get_user.return_value = mock_user
        
        mock_service = AsyncMock()
        mock_service.get_authorization_url.return_value = (
            "https://test-shop.myshopify.com/admin/oauth/authorize?client_id=123",
            "state123"
        )
        mock_oauth_service.return_value = mock_service
        
        response = client.post("/auth/shopify/connect?shop_domain=test-shop")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "authorization_url" in data
        assert "test-shop.myshopify.com" in data["authorization_url"]
    
    @patch('app.routers.oauth.get_oauth_service')
    async def test_oauth_callback_success(self, mock_oauth_service, client, mock_connection):
        """Test successful OAuth callback"""
        mock_service = AsyncMock()
        mock_service.handle_oauth_callback.return_value = mock_connection
        mock_oauth_service.return_value = mock_service
        
        response = client.get("/auth/facebook/callback?code=auth_code&state=user123:csrf_state")
        
        assert response.status_code == 302  # Redirect
        assert "connected=facebook" in response.headers["location"]
        assert "status=success" in response.headers["location"]
    
    @patch('app.routers.oauth.get_oauth_service')
    async def test_oauth_callback_failure(self, mock_oauth_service, client):
        """Test failed OAuth callback"""
        mock_service = AsyncMock()
        mock_service.handle_oauth_callback.return_value = None
        mock_oauth_service.return_value = mock_service
        
        response = client.get("/auth/facebook/callback?code=auth_code&state=user123:csrf_state")
        
        assert response.status_code == 302  # Redirect
        assert "connected=facebook" in response.headers["location"]
        assert "status=error" in response.headers["location"]
    
    def test_oauth_callback_invalid_platform(self, client):
        """Test OAuth callback with invalid platform"""
        response = client.get("/auth/invalid_platform/callback?code=auth_code&state=state123")
        
        assert response.status_code == 400
        assert "Unsupported platform" in response.json()["detail"]
    
    @patch('app.routers.oauth.get_current_user')
    @patch('app.routers.oauth.get_oauth_service')
    async def test_disconnect_platform(self, mock_oauth_service, mock_get_user, client, mock_user):
        """Test disconnecting from platform"""
        mock_get_user.return_value = mock_user
        
        mock_service = AsyncMock()
        mock_service.disconnect_platform.return_value = True
        mock_oauth_service.return_value = mock_service
        
        response = client.post("/auth/facebook/disconnect")
        
        assert response.status_code == 200
        data = response.json()
        assert "Successfully disconnected" in data["message"]
    
    @patch('app.routers.oauth.get_current_user')
    @patch('app.routers.oauth.get_oauth_service')
    async def test_disconnect_platform_failure(self, mock_oauth_service, mock_get_user, client, mock_user):
        """Test failed platform disconnection"""
        mock_get_user.return_value = mock_user
        
        mock_service = AsyncMock()
        mock_service.disconnect_platform.return_value = False
        mock_oauth_service.return_value = mock_service
        
        response = client.post("/auth/facebook/disconnect")
        
        assert response.status_code == 500
        assert "Failed to disconnect" in response.json()["detail"]
    
    def test_disconnect_invalid_platform(self, client):
        """Test disconnecting from invalid platform"""
        with patch('app.routers.oauth.get_current_user') as mock_get_user:
            mock_get_user.return_value = Mock()
            
            response = client.post("/auth/invalid_platform/disconnect")
            
            assert response.status_code == 400
            assert "Unsupported platform" in response.json()["detail"]
    
    @patch('app.routers.oauth.get_current_user')
    @patch('app.routers.oauth.get_db')
    @patch('app.routers.oauth.get_oauth_service')
    async def test_validate_platform_connection(
        self, 
        mock_oauth_service, 
        mock_get_db, 
        mock_get_user, 
        client, 
        mock_user, 
        mock_connection
    ):
        """Test validating platform connection"""
        mock_get_user.return_value = mock_user
        
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_connection
        mock_get_db.return_value = mock_db
        
        mock_service = AsyncMock()
        mock_service.validate_connection.return_value = True
        mock_oauth_service.return_value = mock_service
        
        response = client.post("/auth/facebook/validate")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["platform"] == "facebook"
        assert data["is_valid"] is True
    
    @patch('app.routers.oauth.get_current_user')
    @patch('app.routers.oauth.get_db')
    def test_validate_platform_connection_not_found(
        self, 
        mock_get_db, 
        mock_get_user, 
        client, 
        mock_user
    ):
        """Test validating non-existent platform connection"""
        mock_get_user.return_value = mock_user
        
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_get_db.return_value = mock_db
        
        response = client.post("/auth/facebook/validate")
        
        assert response.status_code == 404
        assert "No active connection found" in response.json()["detail"]
    
    @patch('app.routers.oauth.get_current_user')
    @patch('app.routers.oauth.get_oauth_service')
    async def test_validate_all_connections(
        self, 
        mock_oauth_service, 
        mock_get_user, 
        client, 
        mock_user, 
        mock_connection
    ):
        """Test validating all platform connections"""
        mock_get_user.return_value = mock_user
        
        mock_service = AsyncMock()
        mock_service.get_user_connections.return_value = [mock_connection]
        mock_service.validate_connection.return_value = True
        mock_oauth_service.return_value = mock_service
        
        response = client.post("/auth/validate-all")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "results" in data
        assert len(data["results"]) == 1
        assert data["results"][0]["platform"] == "facebook"
        assert data["results"][0]["is_valid"] is True
    
    @patch('app.routers.oauth.get_current_user')
    @patch('app.routers.oauth.get_db')
    def test_get_platform_status_connected(
        self, 
        mock_get_db, 
        mock_get_user, 
        client, 
        mock_user, 
        mock_connection
    ):
        """Test getting platform status for connected platform"""
        mock_get_user.return_value = mock_user
        
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_connection
        mock_get_db.return_value = mock_db
        
        response = client.get("/auth/facebook/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["platform"] == "facebook"
        assert data["connected"] is True
        assert data["status"] == "active"
        assert data["platform_username"] == "test_user"
    
    @patch('app.routers.oauth.get_current_user')
    @patch('app.routers.oauth.get_db')
    def test_get_platform_status_not_connected(
        self, 
        mock_get_db, 
        mock_get_user, 
        client, 
        mock_user
    ):
        """Test getting platform status for non-connected platform"""
        mock_get_user.return_value = mock_user
        
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_get_db.return_value = mock_db
        
        response = client.get("/auth/facebook/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["platform"] == "facebook"
        assert data["connected"] is False
        assert data["status"] == "not_connected"
    
    def test_get_platform_status_invalid_platform(self, client):
        """Test getting status for invalid platform"""
        with patch('app.routers.oauth.get_current_user') as mock_get_user:
            mock_get_user.return_value = Mock()
            
            response = client.get("/auth/invalid_platform/status")
            
            assert response.status_code == 400
            assert "Unsupported platform" in response.json()["detail"]


@pytest.mark.integration
class TestOAuthRoutesIntegration:
    """Integration tests for OAuth routes"""
    
    @pytest.fixture
    def client(self):
        """Test client for integration tests"""
        return TestClient(app)
    
    def test_oauth_flow_endpoints_exist(self, client):
        """Test that all OAuth endpoints exist"""
        # Test platforms endpoint
        response = client.get("/auth/platforms")
        assert response.status_code == 200
        
        # Test that platform-specific endpoints exist (will fail auth but endpoints exist)
        platforms = ["facebook", "instagram", "etsy", "pinterest", "shopify"]
        
        for platform in platforms:
            # Connect endpoint
            response = client.post(f"/auth/{platform}/connect")
            assert response.status_code in [401, 422]  # Auth required or validation error
            
            # Callback endpoint
            response = client.get(f"/auth/{platform}/callback")
            assert response.status_code in [400, 422]  # Missing required params
            
            # Disconnect endpoint
            response = client.post(f"/auth/{platform}/disconnect")
            assert response.status_code == 401  # Auth required
            
            # Validate endpoint
            response = client.post(f"/auth/{platform}/validate")
            assert response.status_code == 401  # Auth required
            
            # Status endpoint
            response = client.get(f"/auth/{platform}/status")
            assert response.status_code == 401  # Auth required


if __name__ == "__main__":
    pytest.main([__file__])