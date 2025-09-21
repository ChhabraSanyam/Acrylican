"""
Security utilities and middleware for the Artisan Promotion Platform.

This module provides comprehensive security measures including:
- Input validation and sanitization
- Rate limiting
- Security headers
- Secure token storage
- HTTPS enforcement
"""

import re
import html
import hashlib
import secrets
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import json
import logging
from .config import settings

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Custom exception for security-related errors."""
    pass


class InputSanitizer:
    """Handles input validation and sanitization."""
    
    # Common XSS patterns
    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'<iframe[^>]*>.*?</iframe>',
        r'<object[^>]*>.*?</object>',
        r'<embed[^>]*>.*?</embed>',
        r'<link[^>]*>',
        r'<meta[^>]*>',
        r'<style[^>]*>.*?</style>',
    ]
    
    # SQL injection patterns
    SQL_PATTERNS = [
        r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)',
        r'(\b(OR|AND)\s+\d+\s*=\s*\d+)',
        r'(\b(OR|AND)\s+[\'"][^\'"]*[\'"])',
        r'(--|#|/\*|\*/)',
        r'(\bxp_cmdshell\b)',
        r'(\bsp_executesql\b)',
    ]
    
    @classmethod
    def sanitize_string(cls, value: str, max_length: Optional[int] = None) -> str:
        """
        Sanitize a string input by removing potentially dangerous content.
        
        Args:
            value: The string to sanitize
            max_length: Maximum allowed length
            
        Returns:
            Sanitized string
            
        Raises:
            SecurityError: If input contains dangerous patterns
        """
        if not isinstance(value, str):
            raise SecurityError("Input must be a string")
        
        # Check length
        if max_length and len(value) > max_length:
            raise SecurityError(f"Input exceeds maximum length of {max_length}")
        
        # HTML escape
        sanitized = html.escape(value)
        
        # Check for XSS patterns
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, sanitized, re.IGNORECASE):
                logger.warning(f"XSS pattern detected: {pattern}")
                raise SecurityError("Potentially dangerous content detected")
        
        # Check for SQL injection patterns
        for pattern in cls.SQL_PATTERNS:
            if re.search(pattern, sanitized, re.IGNORECASE):
                logger.warning(f"SQL injection pattern detected: {pattern}")
                raise SecurityError("Potentially dangerous content detected")
        
        return sanitized.strip()
    
    @classmethod
    def sanitize_email(cls, email: str) -> str:
        """
        Sanitize and validate email address.
        
        Args:
            email: Email address to validate
            
        Returns:
            Sanitized email address
            
        Raises:
            SecurityError: If email is invalid
        """
        if not isinstance(email, str):
            raise SecurityError("Email must be a string")
        
        email = email.strip().lower()
        
        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise SecurityError("Invalid email format")
        
        # Check length
        if len(email) > 254:  # RFC 5321 limit
            raise SecurityError("Email address too long")
        
        return email
    
    @classmethod
    def sanitize_url(cls, url: str) -> str:
        """
        Sanitize and validate URL.
        
        Args:
            url: URL to validate
            
        Returns:
            Sanitized URL
            
        Raises:
            SecurityError: If URL is invalid or dangerous
        """
        if not isinstance(url, str):
            raise SecurityError("URL must be a string")
        
        url = url.strip()
        
        # Check for dangerous protocols
        dangerous_protocols = ['javascript:', 'data:', 'vbscript:', 'file:']
        for protocol in dangerous_protocols:
            if url.lower().startswith(protocol):
                raise SecurityError("Dangerous URL protocol detected")
        
        # Basic URL validation
        url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        if not re.match(url_pattern, url, re.IGNORECASE):
            raise SecurityError("Invalid URL format")
        
        return url
    
    @classmethod
    def sanitize_dict(cls, data: Dict[str, Any], max_depth: int = 10) -> Dict[str, Any]:
        """
        Recursively sanitize dictionary values.
        
        Args:
            data: Dictionary to sanitize
            max_depth: Maximum recursion depth
            
        Returns:
            Sanitized dictionary
        """
        if max_depth <= 0:
            raise SecurityError("Maximum recursion depth exceeded")
        
        sanitized = {}
        for key, value in data.items():
            # Sanitize key
            if isinstance(key, str):
                key = cls.sanitize_string(key, max_length=100)
            
            # Sanitize value based on type
            if isinstance(value, str):
                sanitized[key] = cls.sanitize_string(value, max_length=10000)
            elif isinstance(value, dict):
                sanitized[key] = cls.sanitize_dict(value, max_depth - 1)
            elif isinstance(value, list):
                sanitized[key] = [
                    cls.sanitize_string(item, max_length=1000) if isinstance(item, str) else item
                    for item in value[:100]  # Limit list size
                ]
            else:
                sanitized[key] = value
        
        return sanitized


class TokenEncryption:
    """Handles secure encryption and decryption of sensitive tokens."""
    
    def __init__(self, secret_key: str):
        """
        Initialize token encryption with a secret key.
        
        Args:
            secret_key: Secret key for encryption
        """
        # Derive encryption key from secret
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'artisan_platform_salt',  # In production, use random salt per user
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))
        self.cipher = Fernet(key)
    
    def encrypt_token(self, token: str) -> str:
        """
        Encrypt a token for secure storage.
        
        Args:
            token: Token to encrypt
            
        Returns:
            Encrypted token as base64 string
        """
        if not token:
            return ""
        
        encrypted = self.cipher.encrypt(token.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt_token(self, encrypted_token: str) -> str:
        """
        Decrypt a token from storage.
        
        Args:
            encrypted_token: Encrypted token as base64 string
            
        Returns:
            Decrypted token
            
        Raises:
            SecurityError: If decryption fails
        """
        if not encrypted_token:
            return ""
        
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_token.encode())
            decrypted = self.cipher.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Token decryption failed: {e}")
            raise SecurityError("Failed to decrypt token")
    
    def is_token_encrypted(self, token: str) -> bool:
        """
        Check if a token appears to be encrypted.
        
        Args:
            token: Token to check
            
        Returns:
            True if token appears encrypted
        """
        if not token:
            return False
            
        # JWT tokens start with 'ey'
        if token.startswith('ey'):
            return False
            
        try:
            # Try to decode as base64 - encrypted tokens should be valid base64
            decoded = base64.urlsafe_b64decode(token.encode())
            # If it's valid base64 and longer than 32 bytes, likely encrypted
            return len(decoded) > 32
        except:
            return False


class RateLimiter:
    """In-memory rate limiter for API endpoints."""
    
    def __init__(self):
        self.requests: Dict[str, List[datetime]] = {}
        self.blocked_ips: Dict[str, datetime] = {}
    
    def is_allowed(self, identifier: str, max_requests: int, window_minutes: int) -> bool:
        """
        Check if a request is allowed based on rate limits.
        
        Args:
            identifier: Unique identifier (IP, user ID, etc.)
            max_requests: Maximum requests allowed
            window_minutes: Time window in minutes
            
        Returns:
            True if request is allowed
        """
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=window_minutes)
        
        # Check if IP is temporarily blocked
        if identifier in self.blocked_ips:
            if now < self.blocked_ips[identifier]:
                return False
            else:
                # Unblock expired blocks
                del self.blocked_ips[identifier]
        
        # Clean old requests
        if identifier in self.requests:
            self.requests[identifier] = [
                req_time for req_time in self.requests[identifier]
                if req_time > window_start
            ]
        else:
            self.requests[identifier] = []
        
        # Check rate limit
        if len(self.requests[identifier]) >= max_requests:
            # Block IP for 15 minutes if severely over limit
            if len(self.requests[identifier]) > max_requests * 2:
                self.blocked_ips[identifier] = now + timedelta(minutes=15)
                logger.warning(f"IP {identifier} blocked for excessive requests")
            return False
        
        # Record this request
        self.requests[identifier].append(now)
        return True
    
    def get_remaining_requests(self, identifier: str, max_requests: int, window_minutes: int) -> int:
        """
        Get remaining requests for an identifier.
        
        Args:
            identifier: Unique identifier
            max_requests: Maximum requests allowed
            window_minutes: Time window in minutes
            
        Returns:
            Number of remaining requests
        """
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=window_minutes)
        
        if identifier not in self.requests:
            return max_requests
        
        # Clean old requests
        recent_requests = [
            req_time for req_time in self.requests[identifier]
            if req_time > window_start
        ]
        
        return max(0, max_requests - len(recent_requests))


class SecurityHeaders:
    """Security headers for HTTP responses."""
    
    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """
        Get standard security headers.
        
        Returns:
            Dictionary of security headers
        """
        return {
            # Prevent XSS attacks
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            
            # Content Security Policy
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' https:; "
                "frame-ancestors 'none';"
            ),
            
            # HTTPS enforcement
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            
            # Referrer policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Permissions policy
            "Permissions-Policy": (
                "geolocation=(), "
                "microphone=(), "
                "camera=(), "
                "payment=(), "
                "usb=(), "
                "magnetometer=(), "
                "gyroscope=(), "
                "speaker=()"
            ),
        }


class SecurityValidator:
    """Validates security requirements for requests."""
    
    @staticmethod
    def validate_password_strength(password: str) -> bool:
        """
        Validate password strength.
        
        Args:
            password: Password to validate
            
        Returns:
            True if password meets requirements
            
        Raises:
            SecurityError: If password is weak
        """
        if len(password) < 8:
            raise SecurityError("Password must be at least 8 characters long")
        
        if len(password) > 128:
            raise SecurityError("Password must be less than 128 characters")
        
        # Check for required character types
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
        
        if not (has_upper and has_lower and has_digit and has_special):
            raise SecurityError(
                "Password must contain uppercase, lowercase, digit, and special character"
            )
        
        # Check for common weak passwords (only if all other requirements are met)
        weak_passwords = [
            "password", "123456", "qwerty", "admin", "letmein",
            "welcome", "monkey", "dragon", "master", "shadow"
        ]
        
        if password.lower() in weak_passwords:
            raise SecurityError("Password is too common")
        
        return True
    
    @staticmethod
    def validate_file_upload(filename: str, content_type: str, file_size: int) -> bool:
        """
        Validate file upload security.
        
        Args:
            filename: Name of uploaded file
            content_type: MIME type of file
            file_size: Size of file in bytes
            
        Returns:
            True if file is safe
            
        Raises:
            SecurityError: If file is dangerous
        """
        # Check file size
        if file_size > settings.max_file_size:
            raise SecurityError(f"File size exceeds limit of {settings.max_file_size} bytes")
        
        # Check content type
        if content_type not in settings.allowed_image_types:
            raise SecurityError(f"File type {content_type} not allowed")
        
        # Check filename
        if not filename or len(filename) > 255:
            raise SecurityError("Invalid filename")
        
        # Check for dangerous extensions
        dangerous_extensions = [
            '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js',
            '.jar', '.php', '.asp', '.aspx', '.jsp', '.py', '.rb', '.pl'
        ]
        
        filename_lower = filename.lower()
        for ext in dangerous_extensions:
            if filename_lower.endswith(ext):
                raise SecurityError(f"File extension {ext} not allowed")
        
        # Check for double extensions
        if filename_lower.count('.') > 1:
            parts = filename_lower.split('.')
            if len(parts) > 2 and any(ext in dangerous_extensions for ext in [f'.{part}' for part in parts[:-1]]):
                raise SecurityError("Suspicious file extension detected")
        
        return True
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """
        Generate a cryptographically secure random token.
        
        Args:
            length: Length of token in bytes
            
        Returns:
            Secure random token as hex string
        """
        return secrets.token_hex(length)
    
    @staticmethod
    def hash_sensitive_data(data: str, salt: Optional[str] = None) -> tuple[str, str]:
        """
        Hash sensitive data with salt.
        
        Args:
            data: Data to hash
            salt: Optional salt (generated if not provided)
            
        Returns:
            Tuple of (hash, salt)
        """
        if salt is None:
            salt = secrets.token_hex(16)
        
        # Use SHA-256 with salt
        hash_obj = hashlib.sha256()
        hash_obj.update(salt.encode())
        hash_obj.update(data.encode())
        
        return hash_obj.hexdigest(), salt


# Global instances
input_sanitizer = InputSanitizer()
token_encryption = TokenEncryption(settings.jwt_secret_key)
rate_limiter = RateLimiter()
security_headers = SecurityHeaders()
security_validator = SecurityValidator()