import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from jose import jwt
from app.auth import PasswordManager, JWTManager, AuthService
from app.config import settings


class TestPasswordManager:
    """Test password hashing and verification functionality."""
    
    def test_hash_password(self):
        """Test password hashing."""
        password = "test_password_123"
        hashed = PasswordManager.hash_password(password)
        
        # Hash should be different from original password
        assert hashed != password
        # Hash should be a string
        assert isinstance(hashed, str)
        # Hash should not be empty
        assert len(hashed) > 0
    
    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "test_password_123"
        hashed = PasswordManager.hash_password(password)
        
        # Verification should succeed
        assert PasswordManager.verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "test_password_123"
        wrong_password = "wrong_password_456"
        hashed = PasswordManager.hash_password(password)
        
        # Verification should fail
        assert PasswordManager.verify_password(wrong_password, hashed) is False
    
    def test_hash_same_password_different_hashes(self):
        """Test that same password produces different hashes (salt)."""
        password = "test_password_123"
        hash1 = PasswordManager.hash_password(password)
        hash2 = PasswordManager.hash_password(password)
        
        # Hashes should be different due to salt
        assert hash1 != hash2
        # But both should verify correctly
        assert PasswordManager.verify_password(password, hash1) is True
        assert PasswordManager.verify_password(password, hash2) is True


class TestJWTManager:
    """Test JWT token generation and validation functionality."""
    
    def test_create_access_token(self):
        """Test access token creation."""
        user_data = {"sub": "user123", "email": "test@example.com"}
        token = JWTManager.create_access_token(user_data)
        
        # Token should be a string
        assert isinstance(token, str)
        # Token should not be empty
        assert len(token) > 0
        
        # Decode and verify token content
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "access"
        assert "exp" in payload
    
    def test_create_refresh_token(self):
        """Test refresh token creation."""
        user_data = {"sub": "user123"}
        token = JWTManager.create_refresh_token(user_data)
        
        # Token should be a string
        assert isinstance(token, str)
        # Token should not be empty
        assert len(token) > 0
        
        # Decode and verify token content
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        assert payload["sub"] == "user123"
        assert payload["type"] == "refresh"
        assert "exp" in payload
    
    def test_create_access_token_with_custom_expiry(self):
        """Test access token creation with custom expiry."""
        user_data = {"sub": "user123"}
        custom_expiry = timedelta(minutes=60)
        token = JWTManager.create_access_token(user_data, custom_expiry)
        
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        
        # Check that expiry is approximately 60 minutes from now
        exp_time = datetime.utcfromtimestamp(payload["exp"])
        expected_time = datetime.utcnow() + custom_expiry
        time_diff = abs((exp_time - expected_time).total_seconds())
        assert time_diff < 5  # Allow 5 seconds tolerance
    
    def test_verify_token_valid_access(self):
        """Test verification of valid access token."""
        user_data = {"sub": "user123", "email": "test@example.com"}
        token = JWTManager.create_access_token(user_data)
        
        payload = JWTManager.verify_token(token, "access")
        
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "access"
    
    def test_verify_token_valid_refresh(self):
        """Test verification of valid refresh token."""
        user_data = {"sub": "user123"}
        token = JWTManager.create_refresh_token(user_data)
        
        payload = JWTManager.verify_token(token, "refresh")
        
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["type"] == "refresh"
    
    def test_verify_token_wrong_type(self):
        """Test verification fails when token type doesn't match expected."""
        user_data = {"sub": "user123"}
        access_token = JWTManager.create_access_token(user_data)
        
        # Try to verify access token as refresh token
        payload = JWTManager.verify_token(access_token, "refresh")
        assert payload is None
    
    def test_verify_token_invalid_signature(self):
        """Test verification fails with invalid signature."""
        # Create token with different secret
        user_data = {"sub": "user123"}
        fake_token = jwt.encode(user_data, "wrong_secret", algorithm=settings.jwt_algorithm)
        
        payload = JWTManager.verify_token(fake_token, "access")
        assert payload is None
    
    def test_verify_token_expired(self):
        """Test verification fails with expired token."""
        user_data = {"sub": "user123"}
        # Create token that expires immediately
        expired_token = JWTManager.create_access_token(user_data, timedelta(seconds=-1))
        
        payload = JWTManager.verify_token(expired_token, "access")
        assert payload is None
    
    def test_get_user_id_from_token_valid(self):
        """Test extracting user ID from valid token."""
        user_data = {"sub": "user123"}
        token = JWTManager.create_access_token(user_data)
        
        user_id = JWTManager.get_user_id_from_token(token)
        assert user_id == "user123"
    
    def test_get_user_id_from_token_invalid(self):
        """Test extracting user ID from invalid token."""
        invalid_token = "invalid.token.here"
        
        user_id = JWTManager.get_user_id_from_token(invalid_token)
        assert user_id is None


class TestAuthService:
    """Test the main authentication service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.auth_service = AuthService()
    
    def test_hash_password(self):
        """Test password hashing through auth service."""
        password = "test_password_123"
        hashed = self.auth_service.hash_password(password)
        
        assert hashed != password
        assert isinstance(hashed, str)
        assert len(hashed) > 0
    
    def test_verify_password(self):
        """Test password verification through auth service."""
        password = "test_password_123"
        hashed = self.auth_service.hash_password(password)
        
        assert self.auth_service.verify_password(password, hashed) is True
        assert self.auth_service.verify_password("wrong_password", hashed) is False
    
    def test_create_tokens(self):
        """Test token creation through auth service."""
        user_id = "user123"
        tokens = self.auth_service.create_tokens(user_id)
        
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert "token_type" in tokens
        assert tokens["token_type"] == "bearer"
        
        # Verify tokens are valid
        access_payload = jwt.decode(
            tokens["access_token"], 
            settings.jwt_secret_key, 
            algorithms=[settings.jwt_algorithm]
        )
        refresh_payload = jwt.decode(
            tokens["refresh_token"], 
            settings.jwt_secret_key, 
            algorithms=[settings.jwt_algorithm]
        )
        
        assert access_payload["sub"] == user_id
        assert access_payload["type"] == "access"
        assert refresh_payload["sub"] == user_id
        assert refresh_payload["type"] == "refresh"
    
    def test_verify_access_token_valid(self):
        """Test access token verification through auth service."""
        user_id = "user123"
        tokens = self.auth_service.create_tokens(user_id)
        
        verified_user_id = self.auth_service.verify_access_token(tokens["access_token"])
        assert verified_user_id == user_id
    
    def test_verify_access_token_invalid(self):
        """Test access token verification with invalid token."""
        invalid_token = "invalid.token.here"
        
        verified_user_id = self.auth_service.verify_access_token(invalid_token)
        assert verified_user_id is None
    
    def test_refresh_access_token_valid(self):
        """Test refreshing access token with valid refresh token."""
        user_id = "user123"
        tokens = self.auth_service.create_tokens(user_id)
        
        new_tokens = self.auth_service.refresh_access_token(tokens["refresh_token"])
        
        assert new_tokens is not None
        assert "access_token" in new_tokens
        assert "token_type" in new_tokens
        assert new_tokens["token_type"] == "bearer"
        
        # Verify new access token is valid
        verified_user_id = self.auth_service.verify_access_token(new_tokens["access_token"])
        assert verified_user_id == user_id
    
    def test_refresh_access_token_invalid(self):
        """Test refreshing access token with invalid refresh token."""
        invalid_token = "invalid.token.here"
        
        new_tokens = self.auth_service.refresh_access_token(invalid_token)
        assert new_tokens is None
    
    def test_refresh_access_token_wrong_type(self):
        """Test refreshing access token with access token instead of refresh token."""
        user_id = "user123"
        tokens = self.auth_service.create_tokens(user_id)
        
        # Try to refresh using access token instead of refresh token
        new_tokens = self.auth_service.refresh_access_token(tokens["access_token"])
        assert new_tokens is None


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    with patch('app.auth.settings') as mock:
        mock.jwt_secret_key = "test_secret_key"
        mock.jwt_algorithm = "HS256"
        mock.jwt_access_token_expire_minutes = 30
        mock.jwt_refresh_token_expire_days = 7
        yield mock


class TestAuthServiceWithMockedSettings:
    """Test auth service with mocked settings."""
    
    def test_token_expiry_times(self, mock_settings):
        """Test that tokens have correct expiry times based on settings."""
        auth_service = AuthService()
        user_id = "user123"
        
        tokens = auth_service.create_tokens(user_id)
        
        # Decode tokens to check expiry
        access_payload = jwt.decode(
            tokens["access_token"], 
            mock_settings.jwt_secret_key, 
            algorithms=[mock_settings.jwt_algorithm]
        )
        refresh_payload = jwt.decode(
            tokens["refresh_token"], 
            mock_settings.jwt_secret_key, 
            algorithms=[mock_settings.jwt_algorithm]
        )
        
        # Check access token expiry (should be ~30 minutes)
        access_exp = datetime.utcfromtimestamp(access_payload["exp"])
        expected_access_exp = datetime.utcnow() + timedelta(minutes=30)
        access_diff = abs((access_exp - expected_access_exp).total_seconds())
        assert access_diff < 5  # Allow 5 seconds tolerance
        
        # Check refresh token expiry (should be ~7 days)
        refresh_exp = datetime.utcfromtimestamp(refresh_payload["exp"])
        expected_refresh_exp = datetime.utcnow() + timedelta(days=7)
        refresh_diff = abs((refresh_exp - expected_refresh_exp).total_seconds())
        assert refresh_diff < 5  # Allow 5 seconds tolerance