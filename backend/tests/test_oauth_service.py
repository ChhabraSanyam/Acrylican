"""
Tests for OAuth Service

This module contains comprehensive tests for OAuth authentication flows,
token management, and platform integrations.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import httpx
from sqlalchemy.orm import Session

from app.services.oauth_service import OAuthService, TokenEncryption, OAuthConfig
from app.services.platform_integration import Platform, AuthenticationMethod, PlatformCredentials
from app.models import PlatformConnection, User
from app.database import get_db


class TestTokenEncryption:
    """Test token encryption functionality"""
    
    def test_encrypt_decrypt_token(self):
        """Test token encryption and decryption"""
        encryption = TokenEncryption()
        
        original_token = "test_access_token_12345"
        encrypted = encryption.encrypt_token(original_token)
        decrypted = encryption.decrypt_token(encrypted)
        
        assert decrypted == original_token
        assert encrypted != original_token
    
    def test_encrypt_empty_token(self):
        """Test encryption of empty token"""
        encryption = TokenEncryption()
        
        encrypted = encryption.encrypt_token("")
        decrypted = encryption.decrypt_token(encrypted)
        
        assert decrypted == ""
        assert encrypted == ""
    
    def test_decrypt_empty_token(self):
        """Test decryption of empty token"""
        encryption = TokenEncryption()
        
        decrypted = encryption.decrypt_token("")
        assert decrypted == ""


class TestOAuthService:
    """Test OAuth service functionality"""
    
    @pytest.fixture
    def oauth_service(self):
        """Create OAuth service instance for testing"""
        return OAuthService(base_url="http://localhost:8000")
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def sample_user(self):
        """Sample user for testing"""
        return User(
            id="user123",
            email="test@example.com",
            business_name="Test Business"
        )
    
    @pytest.fixture
    def sample_connection(self):
        """Sample platform connection for testing"""
        return PlatformConnection(
            id="conn123",
            user_id="user123",
            platform=Platform.FACEBOOK.value,
            integration_type="api",
            auth_method=AuthenticationMethod.OAUTH2.value,
            access_token="encrypted_access_token",
            refresh_token="encrypted_refresh_token",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            is_active=True,
            platform_user_id="fb_user_123",
            platform_username="test_user"
        )
    
    def test_get_platform_config(self, oauth_service):
        """Test getting platform configuration"""
        config = oauth_service._get_platform_config(Platform.FACEBOOK)
        
        assert config["auth_method"] == AuthenticationMethod.OAUTH2
        assert "client_id_env" in config
        assert "auth_url" in config
        assert "token_url" in config
    
    def test_get_platform_config_invalid_platform(self, oauth_service):
        """Test getting configuration for invalid platform"""
        with pytest.raises(ValueError, match="OAuth configuration not found"):
            oauth_service._get_platform_config("invalid_platform")
    
    @patch.dict('os.environ', {
        'FACEBOOK_CLIENT_ID': 'test_client_id',
        'FACEBOOK_CLIENT_SECRET': 'test_client_secret'
    })
    def test_get_oauth_client(self, oauth_service):
        """Test getting OAuth client"""
        client = oauth_service._get_oauth_client(Platform.FACEBOOK)
        
        assert client is not None
        assert client.client_id == "test_client_id"
    
    @patch.dict('os.environ', {})
    def test_get_oauth_client_missing_credentials(self, oauth_service):
        """Test getting OAuth client with missing credentials"""
        with pytest.raises(ValueError, match="OAuth credentials not configured"):
            oauth_service._get_oauth_client(Platform.FACEBOOK)
    
    @patch.dict('os.environ', {
        'FACEBOOK_CLIENT_ID': 'test_client_id',
        'FACEBOOK_CLIENT_SECRET': 'test_client_secret'
    })
    async def test_get_authorization_url(self, oauth_service):
        """Test generating authorization URL"""
        url, state = await oauth_service.get_authorization_url(
            Platform.FACEBOOK,
            "user123"
        )
        
        assert "facebook.com" in url
        assert "client_id=test_client_id" in url
        assert "response_type=code" in url
        assert "user123:" in state
    
    @patch.dict('os.environ', {
        'SHOPIFY_CLIENT_ID': 'test_client_id',
        'SHOPIFY_CLIENT_SECRET': 'test_client_secret'
    })
    async def test_get_authorization_url_shopify(self, oauth_service):
        """Test generating Shopify authorization URL with shop domain"""
        url, state = await oauth_service.get_authorization_url(
            Platform.SHOPIFY,
            "user123",
            shop_domain="test-shop"
        )
        
        assert "test-shop.myshopify.com" in url
        assert "client_id=test_client_id" in url
    
    async def test_get_authorization_url_shopify_missing_domain(self, oauth_service):
        """Test Shopify authorization URL without shop domain"""
        with pytest.raises(ValueError, match="shop_domain is required"):
            await oauth_service.get_authorization_url(
                Platform.SHOPIFY,
                "user123"
            )
    
    @patch('app.services.oauth_service.get_db')
    @patch('httpx.AsyncClient')
    async def test_handle_oauth_callback_success(
        self, 
        mock_httpx, 
        mock_get_db,
        oauth_service, 
        mock_db
    ):
        """Test successful OAuth callback handling"""
        # Mock HTTP client
        mock_client = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        # Mock OAuth client
        mock_oauth_client = AsyncMock()
        mock_oauth_client.fetch_token.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600
        }
        
        # Mock platform user info
        mock_client.get.return_value.status_code = 200
        mock_client.get.return_value.json.return_value = {
            "id": "fb_user_123",
            "name": "Test User"
        }
        
        # Mock database
        mock_get_db.return_value.__next__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with patch.object(oauth_service, '_get_oauth_client', return_value=mock_oauth_client):
            connection = await oauth_service.handle_oauth_callback(
                Platform.FACEBOOK,
                "auth_code_123",
                "user123:csrf_state"
            )
        
        assert connection is not None
        mock_oauth_client.fetch_token.assert_called_once()
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called()
    
    async def test_handle_oauth_callback_invalid_state(self, oauth_service):
        """Test OAuth callback with invalid state"""
        connection = await oauth_service.handle_oauth_callback(
            Platform.FACEBOOK,
            "auth_code_123",
            "invalid_state"
        )
        
        assert connection is None
    
    @patch('httpx.AsyncClient')
    async def test_get_platform_user_info_facebook(self, mock_httpx, oauth_service):
        """Test getting Facebook user info"""
        mock_client = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        mock_client.get.return_value.status_code = 200
        mock_client.get.return_value.json.return_value = {
            "id": "fb_user_123",
            "name": "Test User",
            "email": "test@example.com"
        }
        
        user_info = await oauth_service._get_platform_user_info(
            Platform.FACEBOOK,
            "access_token"
        )
        
        assert user_info["id"] == "fb_user_123"
        assert user_info["name"] == "Test User"
    
    @patch('httpx.AsyncClient')
    async def test_get_platform_user_info_api_error(self, mock_httpx, oauth_service):
        """Test getting user info with API error"""
        mock_client = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        mock_client.get.return_value.status_code = 401
        
        user_info = await oauth_service._get_platform_user_info(
            Platform.FACEBOOK,
            "invalid_token"
        )
        
        assert user_info == {}
    
    async def test_store_platform_connection_new(self, oauth_service, mock_db):
        """Test storing new platform connection"""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        connection = await oauth_service._store_platform_connection(
            db=mock_db,
            user_id="user123",
            platform=Platform.FACEBOOK,
            access_token="access_token",
            refresh_token="refresh_token",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            platform_user_info={"id": "fb_user_123", "name": "Test User"}
        )
        
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called()
        mock_db.refresh.assert_called_once()
    
    async def test_store_platform_connection_existing(self, oauth_service, mock_db, sample_connection):
        """Test updating existing platform connection"""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_connection
        
        connection = await oauth_service._store_platform_connection(
            db=mock_db,
            user_id="user123",
            platform=Platform.FACEBOOK,
            access_token="new_access_token",
            refresh_token="new_refresh_token",
            expires_at=datetime.utcnow() + timedelta(hours=2),
            platform_user_info={"id": "fb_user_123", "name": "Updated User"}
        )
        
        assert connection == sample_connection
        mock_db.add.assert_not_called()  # Should not add new record
        mock_db.commit.assert_called()
    
    @patch('httpx.AsyncClient')
    async def test_refresh_access_token_success(
        self, 
        mock_httpx, 
        oauth_service, 
        mock_db, 
        sample_connection
    ):
        """Test successful token refresh"""
        mock_client = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        # Mock OAuth client
        mock_oauth_client = AsyncMock()
        mock_oauth_client.refresh_token.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600
        }
        
        with patch.object(oauth_service, '_get_oauth_client', return_value=mock_oauth_client):
            success = await oauth_service.refresh_access_token(sample_connection, mock_db)
        
        assert success is True
        mock_oauth_client.refresh_token.assert_called_once()
        mock_db.commit.assert_called()
    
    async def test_refresh_access_token_no_refresh_token(
        self, 
        oauth_service, 
        mock_db, 
        sample_connection
    ):
        """Test token refresh without refresh token"""
        sample_connection.refresh_token = None
        
        success = await oauth_service.refresh_access_token(sample_connection, mock_db)
        
        assert success is False
    
    @patch('httpx.AsyncClient')
    async def test_validate_connection_success(
        self, 
        mock_httpx, 
        oauth_service, 
        mock_db, 
        sample_connection
    ):
        """Test successful connection validation"""
        # Set connection to not be expired
        sample_connection.expires_at = datetime.utcnow() + timedelta(hours=1)
        
        mock_client = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        mock_client.get.return_value.status_code = 200
        mock_client.get.return_value.json.return_value = {"id": "fb_user_123"}
        
        is_valid = await oauth_service.validate_connection(sample_connection, mock_db)
        
        assert is_valid is True
        mock_db.commit.assert_called()
    
    async def test_validate_connection_expired_token(
        self, 
        oauth_service, 
        mock_db, 
        sample_connection
    ):
        """Test connection validation with expired token"""
        # Set connection to be expired
        sample_connection.expires_at = datetime.utcnow() - timedelta(hours=1)
        
        with patch.object(oauth_service, 'refresh_access_token', return_value=True):
            is_valid = await oauth_service.validate_connection(sample_connection, mock_db)
            assert is_valid is True
        
        with patch.object(oauth_service, 'refresh_access_token', return_value=False):
            is_valid = await oauth_service.validate_connection(sample_connection, mock_db)
            assert is_valid is False
            assert sample_connection.is_active is False
    
    async def test_disconnect_platform_success(self, oauth_service, mock_db, sample_connection):
        """Test successful platform disconnection"""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_connection
        
        success = await oauth_service.disconnect_platform(
            "user123",
            Platform.FACEBOOK,
            mock_db
        )
        
        assert success is True
        assert sample_connection.is_active is False
        mock_db.commit.assert_called()
    
    async def test_disconnect_platform_not_found(self, oauth_service, mock_db):
        """Test disconnecting non-existent platform"""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        success = await oauth_service.disconnect_platform(
            "user123",
            Platform.FACEBOOK,
            mock_db
        )
        
        assert success is True  # Should succeed even if not found
    
    async def test_get_user_connections(self, oauth_service, mock_db, sample_connection):
        """Test getting user connections"""
        mock_db.query.return_value.filter.return_value.filter.return_value.all.return_value = [sample_connection]
        
        connections = await oauth_service.get_user_connections("user123", mock_db)
        
        assert len(connections) == 1
        assert connections[0] == sample_connection
    
    async def test_get_user_connections_inactive(self, oauth_service, mock_db, sample_connection):
        """Test getting user connections including inactive"""
        mock_db.query.return_value.filter.return_value.all.return_value = [sample_connection]
        
        connections = await oauth_service.get_user_connections("user123", mock_db, active_only=False)
        
        assert len(connections) == 1
        # Should not filter by is_active when active_only=False
    
    def test_get_decrypted_credentials(self, oauth_service, sample_connection):
        """Test getting decrypted credentials"""
        credentials = oauth_service.get_decrypted_credentials(sample_connection)
        
        assert credentials.platform == Platform.FACEBOOK
        assert credentials.auth_method == AuthenticationMethod.OAUTH2
        assert credentials.access_token is not None
        assert credentials.refresh_token is not None


class TestOAuthConfig:
    """Test OAuth configuration"""
    
    def test_platform_configs_exist(self):
        """Test that all required platforms have OAuth configs"""
        required_platforms = [
            Platform.FACEBOOK,
            Platform.INSTAGRAM,
            Platform.ETSY,
            Platform.PINTEREST,
            Platform.SHOPIFY
        ]
        
        for platform in required_platforms:
            assert platform in OAuthConfig.PLATFORM_CONFIGS
            
            config = OAuthConfig.PLATFORM_CONFIGS[platform]
            assert "auth_method" in config
            assert "client_id_env" in config
            assert "client_secret_env" in config
            assert "auth_url" in config
            assert "token_url" in config
            assert "scope" in config
            assert "redirect_uri" in config
    
    def test_oauth2_auth_method(self):
        """Test that all platforms use OAuth2"""
        for platform, config in OAuthConfig.PLATFORM_CONFIGS.items():
            assert config["auth_method"] == AuthenticationMethod.OAUTH2
    
    def test_shopify_config_has_placeholders(self):
        """Test that Shopify config has shop domain placeholders"""
        config = OAuthConfig.PLATFORM_CONFIGS[Platform.SHOPIFY]
        
        assert "{shop}" in config["auth_url"]
        assert "{shop}" in config["token_url"]


@pytest.mark.integration
class TestOAuthIntegration:
    """Integration tests for OAuth flows"""
    
    @pytest.fixture
    def oauth_service(self):
        """OAuth service for integration tests"""
        return OAuthService(base_url="http://localhost:8000")
    
    @pytest.mark.asyncio
    async def test_facebook_oauth_flow(self, oauth_service):
        """Test complete Facebook OAuth flow (mocked)"""
        # This would be a more comprehensive integration test
        # that tests the entire flow with mocked external APIs
        pass
    
    @pytest.mark.asyncio
    async def test_instagram_oauth_flow(self, oauth_service):
        """Test complete Instagram OAuth flow (mocked)"""
        pass
    
    @pytest.mark.asyncio
    async def test_etsy_oauth_flow(self, oauth_service):
        """Test complete Etsy OAuth flow (mocked)"""
        pass
    
    @pytest.mark.asyncio
    async def test_pinterest_oauth_flow(self, oauth_service):
        """Test complete Pinterest OAuth flow (mocked)"""
        pass
    
    @pytest.mark.asyncio
    async def test_shopify_oauth_flow(self, oauth_service):
        """Test complete Shopify OAuth flow (mocked)"""
        pass


if __name__ == "__main__":
    pytest.main([__file__])