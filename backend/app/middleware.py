"""
Security middleware for the Artisan Promotion Platform.

This module provides middleware for:
- Rate limiting
- Security headers
- HTTPS enforcement
- Request validation
- Logging and monitoring
"""

import time
import logging
from typing import Callable, Dict, Any
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from .security import rate_limiter, security_headers, input_sanitizer, SecurityError
from .config import settings
from .security_config import security_config

logger = logging.getLogger(__name__)


class SecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive security middleware."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        # Use security configuration for rate limits
        self.rate_limits = security_config.get_rate_limits()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through security middleware."""
        start_time = time.time()
        
        try:
            # 1. HTTPS enforcement (in production)
            if settings.environment == "production" and not request.url.scheme == "https":
                return JSONResponse(
                    status_code=status.HTTP_426_UPGRADE_REQUIRED,
                    content={"error": "HTTPS required"}
                )
            
            # 2. Get client identifier
            client_ip = self._get_client_ip(request)
            user_agent = request.headers.get("user-agent", "")
            
            # 3. Basic request validation
            self._validate_request(request)
            
            # 4. Rate limiting
            await self._check_rate_limits(request, client_ip)
            
            # 5. Log request
            logger.info(
                f"Request: {request.method} {request.url.path} "
                f"from {client_ip} ({user_agent[:50]})"
            )
            
            # 6. Process request
            response = await call_next(request)
            
            # 7. Add security headers
            self._add_security_headers(response)
            
            # 8. Log response
            process_time = time.time() - start_time
            logger.info(
                f"Response: {response.status_code} "
                f"for {request.method} {request.url.path} "
                f"in {process_time:.3f}s"
            )
            
            return response
            
        except HTTPException:
            raise
        except SecurityError as e:
            logger.warning(f"Security error from {client_ip}: {e}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "Security validation failed", "detail": str(e)}
            )
        except Exception as e:
            logger.error(f"Middleware error: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": "Internal server error"}
            )
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address, considering proxies."""
        # Check for forwarded headers (common in production)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        if hasattr(request.client, "host"):
            return request.client.host
        
        return "unknown"
    
    def _validate_request(self, request: Request) -> None:
        """Validate basic request properties."""
        # Check request size
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                max_size = 50 * 1024 * 1024  # 50MB
                if size > max_size:
                    raise SecurityError(f"Request too large: {size} bytes")
            except ValueError:
                raise SecurityError("Invalid content-length header")
        
        # Check for suspicious headers
        suspicious_headers = [
            "x-forwarded-host",  # Potential host header injection
            "x-original-url",    # Potential URL manipulation
            "x-rewrite-url",     # Potential URL manipulation
        ]
        
        for header in suspicious_headers:
            if header in request.headers:
                logger.warning(f"Suspicious header detected: {header}")
        
        # Validate User-Agent
        user_agent = request.headers.get("user-agent", "")
        if len(user_agent) > 500:
            raise SecurityError("User-Agent header too long")
        
        # Check for common attack patterns in headers
        for name, value in request.headers.items():
            if any(pattern in value.lower() for pattern in ["<script", "javascript:", "data:"]):
                raise SecurityError(f"Suspicious content in header {name}")
    
    async def _check_rate_limits(self, request: Request, client_ip: str) -> None:
        """Check rate limits for the request."""
        path = request.url.path
        method = request.method
        
        # Skip rate limiting for health checks
        if path in ["/health", "/", "/docs", "/openapi.json"]:
            return
        
        # Get rate limit config for this endpoint
        rate_config = self.rate_limits.get(path, self.rate_limits["default"])
        
        # Create identifier (IP + endpoint for more granular limiting)
        identifier = f"{client_ip}:{path}"
        
        # Check rate limit
        if not rate_limiter.is_allowed(
            identifier,
            rate_config["max_requests"],
            rate_config["window_minutes"]
        ):
            remaining = rate_limiter.get_remaining_requests(
                identifier,
                rate_config["max_requests"],
                rate_config["window_minutes"]
            )
            
            logger.warning(f"Rate limit exceeded for {client_ip} on {path}")
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={
                    "Retry-After": str(rate_config["window_minutes"] * 60),
                    "X-RateLimit-Limit": str(rate_config["max_requests"]),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(int(time.time() + rate_config["window_minutes"] * 60))
                }
            )
    
    def _add_security_headers(self, response: Response) -> None:
        """Add security headers to response."""
        # Use security configuration for headers
        headers = security_config.get_security_headers()
        
        for name, value in headers.items():
            response.headers[name] = value


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for validating and sanitizing request data."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.skip_paths = ["/docs", "/openapi.json", "/health", "/"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Validate request data."""
        # Skip validation for certain paths
        if request.url.path in self.skip_paths:
            return await call_next(request)
        
        try:
            # Validate query parameters
            if request.query_params:
                self._validate_query_params(dict(request.query_params))
            
            # For POST/PUT requests, we'll validate JSON body in the endpoint
            # since FastAPI handles body parsing
            
            return await call_next(request)
            
        except SecurityError as e:
            logger.warning(f"Request validation failed: {e}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "Invalid request data", "detail": str(e)}
            )
    
    def _validate_query_params(self, params: Dict[str, Any]) -> None:
        """Validate query parameters."""
        for key, value in params.items():
            if isinstance(value, str):
                # Basic length check
                if len(value) > 1000:
                    raise SecurityError(f"Query parameter {key} too long")
                
                # Check for suspicious patterns
                if any(pattern in value.lower() for pattern in ["<script", "javascript:", "union select"]):
                    raise SecurityError(f"Suspicious content in query parameter {key}")


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for security-focused logging."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.sensitive_paths = ["/auth/login", "/auth/register", "/auth/refresh"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log security-relevant events."""
        start_time = time.time()
        client_ip = self._get_client_ip(request)
        
        # Log authentication attempts
        if request.url.path in self.sensitive_paths:
            logger.info(f"Auth attempt: {request.method} {request.url.path} from {client_ip}")
        
        response = await call_next(request)
        
        # Log failed authentication
        if request.url.path in self.sensitive_paths and response.status_code >= 400:
            logger.warning(
                f"Auth failed: {request.method} {request.url.path} "
                f"from {client_ip} - Status: {response.status_code}"
            )
        
        # Log suspicious activity
        if response.status_code == 429:  # Rate limited
            logger.warning(f"Rate limit hit: {client_ip} on {request.url.path}")
        
        if response.status_code >= 500:  # Server errors
            logger.error(
                f"Server error: {request.method} {request.url.path} "
                f"from {client_ip} - Status: {response.status_code}"
            )
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        if hasattr(request.client, "host"):
            return request.client.host
        
        return "unknown"


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """CSRF protection middleware for state-changing operations."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.protected_methods = ["POST", "PUT", "DELETE", "PATCH"]
        self.exempt_paths = ["/auth/login", "/auth/register", "/auth/refresh"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check CSRF protection for state-changing requests."""
        # Only check for state-changing methods
        if request.method not in self.protected_methods:
            return await call_next(request)
        
        # Skip CSRF for exempt paths (they use other protection)
        if request.url.path in self.exempt_paths:
            return await call_next(request)
        
        # For API endpoints, we rely on JWT tokens and SameSite cookies
        # In a full web app, you'd check CSRF tokens here
        
        return await call_next(request)