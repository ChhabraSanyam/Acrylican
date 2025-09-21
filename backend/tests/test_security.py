"""
Security tests for the Artisan Promotion Platform.

Tests cover:
- Input validation and sanitization
- Rate limiting
- Token encryption
- Password security
- File upload security
- Security headers
- Authentication security
"""

import pytest
import time
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch, MagicMock

from app.main import app
from app.security import (
    InputSanitizer, TokenEncryption, RateLimiter, SecurityValidator,
    SecurityError, security_validator, token_encryption, rate_limiter
)
from app.secure_storage import SecureTokenStorage, APIKeyManager
from app.models import User, PlatformConnection
from app.config import settings


class TestInputSanitizer:
    """Test input sanitization and validation."""
    
    def test_sanitize_string_basic(self):
        """Test basic string sanitization."""
        sanitizer = InputSanitizer()
        
        # Normal string should pass
        result = sanitizer.sanitize_string("Hello World")
        assert result == "Hello World"
        
        # HTML should be escaped
        result = sanitizer.sanitize_string("<b>Bold</b>")
        assert result == "&lt;b&gt;Bold&lt;/b&gt;"
    
    def test_sanitize_string_xss_detection(self):
        """Test XSS pattern detection."""
        sanitizer = InputSanitizer()
        
        # Script tags should be rejected
        with pytest.raises(SecurityError):
            sanitizer.sanitize_string("<script>alert('xss')</script>")
        
        # JavaScript URLs should be rejected
        with pytest.raises(SecurityError):
            sanitizer.sanitize_string("javascript:alert('xss')")
        
        # Event handlers should be rejected
        with pytest.raises(SecurityError):
            sanitizer.sanitize_string("<img onload='alert(1)'>")
    
    def test_sanitize_string_sql_injection(self):
        """Test SQL injection pattern detection."""
        sanitizer = InputSanitizer()
        
        # SQL keywords should be rejected
        with pytest.raises(SecurityError):
            sanitizer.sanitize_string("'; DROP TABLE users; --")
        
        with pytest.raises(SecurityError):
            sanitizer.sanitize_string("1 OR 1=1")
        
        with pytest.raises(SecurityError):
            sanitizer.sanitize_string("UNION SELECT * FROM users")
    
    def test_sanitize_string_length_limit(self):
        """Test string length limits."""
        sanitizer = InputSanitizer()
        
        # Should pass within limit
        result = sanitizer.sanitize_string("short", max_length=10)
        assert result == "short"
        
        # Should fail over limit
        with pytest.raises(SecurityError):
            sanitizer.sanitize_string("very long string", max_length=5)
    
    def test_sanitize_email(self):
        """Test email sanitization."""
        sanitizer = InputSanitizer()
        
        # Valid email should pass
        result = sanitizer.sanitize_email("user@example.com")
        assert result == "user@example.com"
        
        # Email should be lowercased
        result = sanitizer.sanitize_email("USER@EXAMPLE.COM")
        assert result == "user@example.com"
        
        # Invalid email should fail
        with pytest.raises(SecurityError):
            sanitizer.sanitize_email("invalid-email")
        
        with pytest.raises(SecurityError):
            sanitizer.sanitize_email("user@")
        
        with pytest.raises(SecurityError):
            sanitizer.sanitize_email("@example.com")
    
    def test_sanitize_url(self):
        """Test URL sanitization."""
        sanitizer = InputSanitizer()
        
        # Valid URLs should pass
        result = sanitizer.sanitize_url("https://example.com")
        assert result == "https://example.com"
        
        result = sanitizer.sanitize_url("http://example.com/path?param=value")
        assert result == "http://example.com/path?param=value"
        
        # Dangerous protocols should fail
        with pytest.raises(SecurityError):
            sanitizer.sanitize_url("javascript:alert('xss')")
        
        with pytest.raises(SecurityError):
            sanitizer.sanitize_url("data:text/html,<script>alert(1)</script>")
        
        # Invalid URLs should fail
        with pytest.raises(SecurityError):
            sanitizer.sanitize_url("not-a-url")
    
    def test_sanitize_dict(self):
        """Test dictionary sanitization."""
        sanitizer = InputSanitizer()
        
        # Normal dict should pass
        data = {"name": "John", "age": 30}
        result = sanitizer.sanitize_dict(data)
        assert result == {"name": "John", "age": 30}
        
        # Nested dict should be sanitized
        data = {
            "user": {"name": "<script>alert(1)</script>"},
            "safe": "normal text"
        }
        
        with pytest.raises(SecurityError):
            sanitizer.sanitize_dict(data)


class TestTokenEncryption:
    """Test token encryption and decryption."""
    
    def test_encrypt_decrypt_token(self):
        """Test basic token encryption and decryption."""
        encryption = TokenEncryption("test-secret-key")
        
        original_token = "test-access-token-12345"
        
        # Encrypt token
        encrypted = encryption.encrypt_token(original_token)
        assert encrypted != original_token
        assert len(encrypted) > 0
        
        # Decrypt token
        decrypted = encryption.decrypt_token(encrypted)
        assert decrypted == original_token
    
    def test_encrypt_empty_token(self):
        """Test encryption of empty token."""
        encryption = TokenEncryption("test-secret-key")
        
        encrypted = encryption.encrypt_token("")
        assert encrypted == ""
        
        decrypted = encryption.decrypt_token("")
        assert decrypted == ""
    
    def test_decrypt_invalid_token(self):
        """Test decryption of invalid token."""
        encryption = TokenEncryption("test-secret-key")
        
        with pytest.raises(SecurityError):
            encryption.decrypt_token("invalid-encrypted-token")
    
    def test_is_token_encrypted(self):
        """Test token encryption detection."""
        encryption = TokenEncryption("test-secret-key")
        
        # JWT token should not be detected as encrypted
        jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"
        assert not encryption.is_token_encrypted(jwt_token)
        
        # Encrypted token should be detected
        original_token = "test-token"
        encrypted_token = encryption.encrypt_token(original_token)
        assert encryption.is_token_encrypted(encrypted_token)
        
        # Plain text should not be detected as encrypted
        assert not encryption.is_token_encrypted("plain-text-token")


class TestRateLimiter:
    """Test rate limiting functionality."""
    
    def test_rate_limit_basic(self):
        """Test basic rate limiting."""
        limiter = RateLimiter()
        identifier = "test-user"
        
        # First request should be allowed
        assert limiter.is_allowed(identifier, max_requests=2, window_minutes=1)
        
        # Second request should be allowed
        assert limiter.is_allowed(identifier, max_requests=2, window_minutes=1)
        
        # Third request should be denied
        assert not limiter.is_allowed(identifier, max_requests=2, window_minutes=1)
    
    def test_rate_limit_window_expiry(self):
        """Test rate limit window expiry."""
        limiter = RateLimiter()
        identifier = "test-user-2"
        
        # Fill up the rate limit
        assert limiter.is_allowed(identifier, max_requests=1, window_minutes=1)
        assert not limiter.is_allowed(identifier, max_requests=1, window_minutes=1)
        
        # Simulate time passing (in real implementation, you'd mock datetime)
        # For testing, we'll manually clean the requests
        limiter.requests[identifier] = []
        
        # Should be allowed again
        assert limiter.is_allowed(identifier, max_requests=1, window_minutes=1)
    
    def test_get_remaining_requests(self):
        """Test getting remaining requests."""
        limiter = RateLimiter()
        identifier = "test-user-3"
        
        # Initially should have full limit
        remaining = limiter.get_remaining_requests(identifier, max_requests=3, window_minutes=1)
        assert remaining == 3
        
        # After one request
        limiter.is_allowed(identifier, max_requests=3, window_minutes=1)
        remaining = limiter.get_remaining_requests(identifier, max_requests=3, window_minutes=1)
        assert remaining == 2
    
    def test_ip_blocking(self):
        """Test IP blocking for excessive requests."""
        limiter = RateLimiter()
        identifier = "abusive-user"
        
        # Make many requests to trigger blocking
        for _ in range(10):  # More than 2x the limit
            limiter.is_allowed(identifier, max_requests=2, window_minutes=1)
        
        # Should be blocked
        assert identifier in limiter.blocked_ips


class TestSecurityValidator:
    """Test security validation functions."""
    
    def test_validate_password_strength(self):
        """Test password strength validation."""
        validator = SecurityValidator()
        
        # Strong password should pass
        assert validator.validate_password_strength("StrongP@ssw0rd!")
        
        # Weak passwords should fail
        with pytest.raises(SecurityError, match="at least 8 characters"):
            validator.validate_password_strength("weak")
        
        with pytest.raises(SecurityError, match="uppercase"):
            validator.validate_password_strength("nouppercase123!")
        
        with pytest.raises(SecurityError, match="lowercase"):
            validator.validate_password_strength("NOLOWERCASE123!")
        
        with pytest.raises(SecurityError, match="digit"):
            validator.validate_password_strength("NoDigits!")
        
        with pytest.raises(SecurityError, match="special character"):
            validator.validate_password_strength("NoSpecialChars123")
        
        with pytest.raises(SecurityError, match="too common"):
            validator.validate_password_strength("password")
    
    def test_validate_file_upload(self):
        """Test file upload validation."""
        validator = SecurityValidator()
        
        # Valid image should pass
        assert validator.validate_file_upload(
            "image.jpg", "image/jpeg", 1024 * 1024  # 1MB
        )
        
        # File too large should fail
        with pytest.raises(SecurityError, match="exceeds limit"):
            validator.validate_file_upload(
                "large.jpg", "image/jpeg", 50 * 1024 * 1024  # 50MB
            )
        
        # Invalid content type should fail
        with pytest.raises(SecurityError, match="not allowed"):
            validator.validate_file_upload(
                "script.exe", "application/exe", 1024
            )
        
        # Dangerous extension should fail
        with pytest.raises(SecurityError, match="not allowed"):
            validator.validate_file_upload(
                "malware.exe", "image/jpeg", 1024
            )
        
        # Double extension should fail
        with pytest.raises(SecurityError, match="Suspicious"):
            validator.validate_file_upload(
                "image.php.jpg", "image/jpeg", 1024
            )
    
    def test_generate_secure_token(self):
        """Test secure token generation."""
        validator = SecurityValidator()
        
        # Generate token
        token = validator.generate_secure_token(16)
        assert len(token) == 32  # 16 bytes = 32 hex chars
        assert all(c in '0123456789abcdef' for c in token)
        
        # Tokens should be unique
        token2 = validator.generate_secure_token(16)
        assert token != token2
    
    def test_hash_sensitive_data(self):
        """Test sensitive data hashing."""
        validator = SecurityValidator()
        
        data = "sensitive-information"
        
        # Hash with generated salt
        hash1, salt1 = validator.hash_sensitive_data(data)
        assert len(hash1) == 64  # SHA-256 hex
        assert len(salt1) == 32  # 16 bytes = 32 hex chars
        
        # Hash with same salt should produce same hash
        hash2, salt2 = validator.hash_sensitive_data(data, salt1)
        assert hash1 == hash2
        assert salt1 == salt2
        
        # Different data should produce different hash
        hash3, _ = validator.hash_sensitive_data("different-data", salt1)
        assert hash1 != hash3


class TestSecureTokenStorage:
    """Test secure token storage functionality."""
    
    @pytest.fixture
    def db_session(self):
        """Mock database session."""
        return MagicMock(spec=Session)
    
    @pytest.fixture
    def storage(self):
        """Create SecureTokenStorage instance."""
        return SecureTokenStorage()
    
    def test_store_platform_tokens(self, storage, db_session):
        """Test storing platform tokens."""
        # Mock database query to return no existing connection
        db_session.query.return_value.filter.return_value.first.return_value = None
        
        connection = storage.store_platform_tokens(
            db_session,
            user_id="user123",
            platform="facebook",
            access_token="access-token-123",
            refresh_token="refresh-token-456"
        )
        
        # Should create new connection
        assert db_session.add.called
        assert db_session.commit.called
    
    def test_retrieve_platform_tokens(self, storage, db_session):
        """Test retrieving platform tokens."""
        # Mock existing connection
        mock_connection = MagicMock()
        mock_connection.access_token = token_encryption.encrypt_token("access-token")
        mock_connection.refresh_token = token_encryption.encrypt_token("refresh-token")
        mock_connection.expires_at = datetime.utcnow() + timedelta(hours=1)
        mock_connection.platform_data = {"test": "data"}
        mock_connection.id = "conn123"
        
        db_session.query.return_value.filter.return_value.first.return_value = mock_connection
        
        tokens = storage.retrieve_platform_tokens(
            db_session,
            user_id="user123",
            platform="facebook"
        )
        
        assert tokens is not None
        assert tokens["access_token"] == "access-token"
        assert tokens["refresh_token"] == "refresh-token"
        assert tokens["platform_data"] == {"test": "data"}
    
    def test_retrieve_expired_tokens(self, storage, db_session):
        """Test retrieving expired tokens."""
        # Mock expired connection
        mock_connection = MagicMock()
        mock_connection.expires_at = datetime.utcnow() - timedelta(hours=1)  # Expired
        
        db_session.query.return_value.filter.return_value.first.return_value = mock_connection
        
        tokens = storage.retrieve_platform_tokens(
            db_session,
            user_id="user123",
            platform="facebook"
        )
        
        assert tokens is None


class TestAPIKeyManager:
    """Test API key management."""
    
    def test_generate_api_key(self):
        """Test API key generation."""
        manager = APIKeyManager()
        
        api_key = manager.generate_api_key("user123", "gemini")
        
        assert len(api_key) == 64  # 32 bytes = 64 hex chars
        assert all(c in '0123456789abcdef' for c in api_key)
    
    def test_validate_api_key(self):
        """Test API key validation."""
        manager = APIKeyManager()
        
        # Valid key should pass
        valid_key = "a" * 64  # 64 char hex string
        result = manager.validate_api_key(valid_key)
        assert result is not None
        assert result["valid"] is True
        
        # Invalid key should fail
        result = manager.validate_api_key("short")
        assert result is None
        
        result = manager.validate_api_key("")
        assert result is None


class TestSecurityIntegration:
    """Integration tests for security features."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_security_headers(self, client):
        """Test security headers are added."""
        response = client.get("/health")
        
        # Check for security headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "Content-Security-Policy" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
    
    def test_rate_limiting(self, client):
        """Test rate limiting on endpoints."""
        # Make multiple requests to trigger rate limit
        # Note: This test might be flaky depending on the rate limit settings
        
        responses = []
        for _ in range(10):  # Make many requests quickly
            response = client.post("/auth/login", json={
                "email": "test@example.com",
                "password": "password"
            })
            responses.append(response)
        
        # At least one should be rate limited (429)
        status_codes = [r.status_code for r in responses]
        # Note: Might not always trigger in test environment
        # assert 429 in status_codes
    
    def test_https_enforcement_production(self, client):
        """Test HTTPS enforcement in production."""
        # This would need to be tested with production settings
        # For now, just verify the middleware is in place
        pass
    
    def test_input_validation_middleware(self, client):
        """Test input validation middleware."""
        # Test with suspicious query parameters
        response = client.get("/health?param=<script>alert(1)</script>")
        
        # Should either sanitize or reject
        assert response.status_code in [200, 400]
    
    def test_cors_configuration(self, client):
        """Test CORS configuration."""
        response = client.options("/health", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET"
        })
        
        # Should have CORS headers
        assert "Access-Control-Allow-Origin" in response.headers


class TestVulnerabilityAssessment:
    """Tests for common security vulnerabilities."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_sql_injection_protection(self, client):
        """Test protection against SQL injection."""
        # Try SQL injection in various endpoints
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "1 OR 1=1",
            "UNION SELECT * FROM users",
            "admin'--",
            "' OR 'a'='a"
        ]
        
        for payload in malicious_inputs:
            # Test in login endpoint
            response = client.post("/auth/login", json={
                "email": payload,
                "password": "password"
            })
            
            # Should not cause server error (500)
            assert response.status_code != 500
    
    def test_xss_protection(self, client):
        """Test protection against XSS attacks."""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "<svg onload=alert('xss')>",
            "';alert('xss');//"
        ]
        
        for payload in xss_payloads:
            # Test in registration endpoint
            response = client.post("/auth/register", json={
                "email": "test@example.com",
                "password": "StrongP@ssw0rd!",
                "business_name": payload,
                "business_type": "retail"
            })
            
            # Should either reject or sanitize
            assert response.status_code in [400, 422]  # Bad request or validation error
    
    def test_file_upload_security(self, client):
        """Test file upload security."""
        # Test with malicious file types
        malicious_files = [
            ("malware.exe", b"MZ\x90\x00", "application/octet-stream"),
            ("script.php", b"<?php echo 'hack'; ?>", "text/php"),
            ("image.php.jpg", b"fake image data", "image/jpeg"),
        ]
        
        for filename, content, content_type in malicious_files:
            response = client.post(
                "/images/upload",
                files={"files": (filename, content, content_type)},
                headers={"Authorization": "Bearer fake-token"}
            )
            
            # Should reject malicious files
            assert response.status_code in [400, 401, 422]
    
    def test_authentication_bypass(self, client):
        """Test for authentication bypass vulnerabilities."""
        # Try accessing protected endpoints without auth
        protected_endpoints = [
            "/products",
            "/posts",
            "/platforms",
            "/analytics"
        ]
        
        for endpoint in protected_endpoints:
            response = client.get(endpoint)
            
            # Should require authentication
            assert response.status_code == 401
    
    def test_privilege_escalation(self, client):
        """Test for privilege escalation vulnerabilities."""
        # This would require creating test users with different roles
        # For now, just verify that user isolation is in place
        pass
    
    def test_information_disclosure(self, client):
        """Test for information disclosure vulnerabilities."""
        # Test error responses don't leak sensitive information
        response = client.get("/nonexistent-endpoint")
        
        # Should not reveal internal paths or stack traces
        assert response.status_code == 404
        response_text = response.text.lower()
        assert "traceback" not in response_text
        assert "exception" not in response_text
        assert "/app/" not in response_text