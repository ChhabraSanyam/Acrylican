#!/usr/bin/env python3
"""
Security validation script to verify security measures are working.

This script performs basic validation of:
- Input sanitization
- Token encryption
- Rate limiting
- Password validation
- Security headers
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.security import (
    InputSanitizer, TokenEncryption, RateLimiter, 
    SecurityValidator, SecurityError
)
from app.security_config import security_config
from app.config import settings

def test_input_sanitization():
    """Test input sanitization."""
    print("Testing input sanitization...")
    sanitizer = InputSanitizer()
    
    # Test XSS protection
    try:
        sanitizer.sanitize_string("<script>alert('xss')</script>")
        print("❌ XSS protection failed")
        return False
    except SecurityError:
        print("✅ XSS protection working")
    
    # Test SQL injection protection
    try:
        sanitizer.sanitize_string("'; DROP TABLE users; --")
        print("❌ SQL injection protection failed")
        return False
    except SecurityError:
        print("✅ SQL injection protection working")
    
    # Test normal input
    try:
        result = sanitizer.sanitize_string("Hello World")
        if result == "Hello World":
            print("✅ Normal input sanitization working")
        else:
            print("❌ Normal input sanitization failed")
            return False
    except SecurityError:
        print("❌ Normal input sanitization failed")
        return False
    
    return True

def test_token_encryption():
    """Test token encryption."""
    print("\nTesting token encryption...")
    encryption = TokenEncryption(settings.jwt_secret_key)
    
    # Test encryption/decryption
    original_token = "test-access-token-12345"
    encrypted = encryption.encrypt_token(original_token)
    decrypted = encryption.decrypt_token(encrypted)
    
    if decrypted == original_token:
        print("✅ Token encryption/decryption working")
    else:
        print("❌ Token encryption/decryption failed")
        return False
    
    # Test encrypted token detection
    if encryption.is_token_encrypted(encrypted):
        print("✅ Encrypted token detection working")
    else:
        print("❌ Encrypted token detection failed")
        return False
    
    return True

def test_rate_limiting():
    """Test rate limiting."""
    print("\nTesting rate limiting...")
    limiter = RateLimiter()
    
    # Test basic rate limiting
    identifier = "test-user"
    
    # First request should be allowed
    if limiter.is_allowed(identifier, max_requests=2, window_minutes=1):
        print("✅ First request allowed")
    else:
        print("❌ First request denied")
        return False
    
    # Second request should be allowed
    if limiter.is_allowed(identifier, max_requests=2, window_minutes=1):
        print("✅ Second request allowed")
    else:
        print("❌ Second request denied")
        return False
    
    # Third request should be denied
    if not limiter.is_allowed(identifier, max_requests=2, window_minutes=1):
        print("✅ Third request denied (rate limit working)")
    else:
        print("❌ Third request allowed (rate limit not working)")
        return False
    
    return True

def test_password_validation():
    """Test password validation."""
    print("\nTesting password validation...")
    validator = SecurityValidator()
    
    # Test strong password
    try:
        if validator.validate_password_strength("StrongP@ssw0rd!"):
            print("✅ Strong password accepted")
        else:
            print("❌ Strong password rejected")
            return False
    except SecurityError:
        print("❌ Strong password rejected")
        return False
    
    # Test weak password
    try:
        validator.validate_password_strength("weak")
        print("❌ Weak password accepted")
        return False
    except SecurityError:
        print("✅ Weak password rejected")
    
    return True

def test_security_configuration():
    """Test security configuration."""
    print("\nTesting security configuration...")
    
    # Test rate limits configuration
    rate_limits = security_config.get_rate_limits()
    if "default" in rate_limits and "/auth/login" in rate_limits:
        print("✅ Rate limits configured")
    else:
        print("❌ Rate limits not configured")
        return False
    
    # Test security headers
    headers = security_config.get_security_headers()
    required_headers = ["X-Content-Type-Options", "X-Frame-Options", "Content-Security-Policy"]
    
    missing_headers = [h for h in required_headers if h not in headers]
    if not missing_headers:
        print("✅ Security headers configured")
    else:
        print(f"❌ Missing security headers: {missing_headers}")
        return False
    
    return True

def test_file_upload_validation():
    """Test file upload validation."""
    print("\nTesting file upload validation...")
    validator = SecurityValidator()
    
    # Test valid file
    try:
        if validator.validate_file_upload("image.jpg", "image/jpeg", 1024 * 1024):
            print("✅ Valid file accepted")
        else:
            print("❌ Valid file rejected")
            return False
    except SecurityError:
        print("❌ Valid file rejected")
        return False
    
    # Test dangerous file
    try:
        validator.validate_file_upload("malware.exe", "application/exe", 1024)
        print("❌ Dangerous file accepted")
        return False
    except SecurityError:
        print("✅ Dangerous file rejected")
    
    return True

def main():
    """Run all security validation tests."""
    print("🔒 Security Validation Tests")
    print("=" * 40)
    
    tests = [
        test_input_sanitization,
        test_token_encryption,
        test_rate_limiting,
        test_password_validation,
        test_security_configuration,
        test_file_upload_validation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                print("❌ Test failed")
        except Exception as e:
            print(f"❌ Test error: {e}")
    
    print("\n" + "=" * 40)
    print(f"Security Validation Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All security tests passed!")
        return 0
    else:
        print("⚠️  Some security tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())