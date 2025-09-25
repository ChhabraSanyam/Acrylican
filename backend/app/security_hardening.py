"""
Production security hardening configurations
"""
import os
import secrets
from typing import Dict, Any, List
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from .config import settings
import time
import hashlib
from collections import defaultdict
from datetime import datetime, timedelta


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Content Security Policy
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none';"
        )
        response.headers["Content-Security-Policy"] = csp
        
        # Remove server information
        if "server" in response.headers:
            del response.headers["server"]
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware to prevent abuse"""
    
    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.clients = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next):
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Clean old entries
        now = time.time()
        self.clients[client_ip] = [
            timestamp for timestamp in self.clients[client_ip]
            if now - timestamp < self.period
        ]
        
        # Check rate limit - be more lenient in development
        is_development = os.getenv("ENVIRONMENT") != "production"
        if not is_development and len(self.clients[client_ip]) >= self.calls:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later."
            )
        
        # Add current request
        self.clients[client_ip].append(now)
        
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = max(0, self.calls - len(self.clients[client_ip]))
        response.headers["X-RateLimit-Limit"] = str(self.calls)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(now + self.period))
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address considering proxies"""
        # Check for forwarded headers (from load balancer/proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"


class SecurityAuditLogger:
    """Log security-related events for monitoring"""
    
    def __init__(self):
        self.events = []
    
    def log_failed_login(self, email: str, ip: str, user_agent: str):
        """Log failed login attempt"""
        self._log_event("failed_login", {
            "email": email,
            "ip": ip,
            "user_agent": user_agent
        })
    
    def log_suspicious_activity(self, event_type: str, details: Dict[str, Any]):
        """Log suspicious activity"""
        self._log_event("suspicious_activity", {
            "type": event_type,
            "details": details
        })
    
    def log_privilege_escalation(self, user_id: str, action: str, ip: str):
        """Log privilege escalation attempts"""
        self._log_event("privilege_escalation", {
            "user_id": user_id,
            "action": action,
            "ip": ip
        })
    
    def log_data_access(self, user_id: str, resource: str, action: str):
        """Log sensitive data access"""
        self._log_event("data_access", {
            "user_id": user_id,
            "resource": resource,
            "action": action
        })
    
    def _log_event(self, event_type: str, data: Dict[str, Any]):
        """Internal method to log security events"""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "data": data,
            "severity": self._get_severity(event_type)
        }
        
        self.events.append(event)
        
        # In production, this would send to a SIEM system
        print(f"SECURITY EVENT: {event}")
    
    def _get_severity(self, event_type: str) -> str:
        """Determine event severity"""
        high_severity = ["privilege_escalation", "suspicious_activity"]
        medium_severity = ["failed_login", "data_access"]
        
        if event_type in high_severity:
            return "HIGH"
        elif event_type in medium_severity:
            return "MEDIUM"
        else:
            return "LOW"


class InputSanitizer:
    """Sanitize and validate user inputs"""
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """Sanitize string input"""
        if not isinstance(value, str):
            raise ValueError("Input must be a string")
        
        # Remove null bytes and control characters
        sanitized = ''.join(char for char in value if ord(char) >= 32 or char in '\t\n\r')
        
        # Limit length
        if len(sanitized) > max_length:
            raise ValueError(f"Input too long (max {max_length} characters)")
        
        return sanitized.strip()
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent path traversal"""
        if not filename:
            raise ValueError("Filename cannot be empty")
        
        # Remove path separators and dangerous characters
        dangerous_chars = ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*']
        sanitized = filename
        
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '_')
        
        # Limit length
        if len(sanitized) > 255:
            name, ext = os.path.splitext(sanitized)
            sanitized = name[:250] + ext
        
        return sanitized
    
    @staticmethod
    def validate_email(email: str) -> str:
        """Validate and sanitize email address"""
        import re
        
        email = InputSanitizer.sanitize_string(email, 254)
        
        # Basic email validation
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(pattern, email):
            raise ValueError("Invalid email format")
        
        return email.lower()


def configure_security_middleware(app: FastAPI) -> FastAPI:
    """Configure all security middleware for the application"""
    
    # Environment-specific settings
    is_production = settings.environment == "production"

    # Use settings.cors_origins for both CORS and TrustedHostMiddleware
    allowed_origins = settings.cors_origins

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"]
    )

    # Trusted host middleware
    if is_production:
        # Extract hostnames from allowed_origins (strip protocol and trailing slashes)
        def extract_hostname(url):
            if url.startswith('http://') or url.startswith('https://'):
                return url.split('//')[-1].split('/')[0]
            else:
                # If no protocol, assume it's already a hostname
                return url.split('/')[0]
        
        allowed_hosts = []
        for origin in allowed_origins:
            hostname = extract_hostname(origin)
            if hostname and hostname not in allowed_hosts:
                allowed_hosts.append(hostname)
        
        # Add render hostname if not already present
        if "acrylican.onrender.com" not in allowed_hosts:
            allowed_hosts.append("acrylican.onrender.com")
            
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=allowed_hosts
        )
    
    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Rate limiting - more lenient in development
    if is_production:
        rate_limit_calls = 100
        rate_limit_period = 60
    else:
        # Much more lenient for development
        rate_limit_calls = 10000
        rate_limit_period = 60
    
    app.add_middleware(RateLimitMiddleware, calls=rate_limit_calls, period=rate_limit_period)
    
    # Gzip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Session middleware with secure settings
    session_secret = os.getenv("SESSION_SECRET")
    if not session_secret:
        if is_production:
            raise ValueError("SESSION_SECRET must be set in production")
        session_secret = secrets.token_urlsafe(32)
    
    app.add_middleware(
        SessionMiddleware,
        secret_key=session_secret,
        max_age=3600,  # 1 hour
        same_site="strict" if is_production else "lax",
        https_only=is_production
    )
    
    return app


def get_security_config() -> Dict[str, Any]:
    """Get security configuration for the application"""
    is_production = os.getenv("ENVIRONMENT") == "production"
    
    return {
        "password_min_length": 12,
        "password_require_special": True,
        "password_require_numbers": True,
        "password_require_uppercase": True,
        "session_timeout": 3600,  # 1 hour
        "max_login_attempts": 5,
        "lockout_duration": 900,  # 15 minutes
        "jwt_expiry": 3600,  # 1 hour
        "refresh_token_expiry": 86400 * 7,  # 7 days
        "file_upload_max_size": 10 * 1024 * 1024,  # 10MB
        "allowed_file_types": [".jpg", ".jpeg", ".png", ".webp"],
        "encryption_algorithm": "AES-256-GCM",
        "hash_algorithm": "bcrypt",
        "hash_rounds": 12,
        "secure_cookies": is_production,
        "https_only": is_production
    }


# Global instances
security_audit_logger = SecurityAuditLogger()
input_sanitizer = InputSanitizer()