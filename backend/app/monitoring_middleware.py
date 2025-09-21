"""
Enhanced monitoring middleware for comprehensive request/response tracking.

This middleware provides:
- Request/response logging with structured format
- Performance metrics collection
- Error tracking and alerting
- Request correlation IDs
- User activity tracking
"""

import time
import uuid
from typing import Callable
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .monitoring import logger, metrics_collector, error_tracker, AlertSeverity


class MonitoringMiddleware(BaseHTTPMiddleware):
    """Comprehensive monitoring middleware."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.skip_paths = ["/docs", "/openapi.json", "/favicon.ico"]
        self.health_paths = ["/health", "/health/liveness", "/health/readiness"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with comprehensive monitoring."""
        # Generate request ID for correlation
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Extract request context
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        method = request.method
        path = request.url.path
        
        # Skip detailed monitoring for certain paths
        skip_detailed = path in self.skip_paths
        is_health_check = path in self.health_paths
        
        start_time = time.time()
        
        # Log request start (except for health checks to reduce noise)
        if not is_health_check:
            logger.info(
                f"Request started: {method} {path}",
                request_id=request_id,
                client_ip=client_ip,
                endpoint=path,
                method=method,
                metadata={
                    "user_agent": user_agent[:100],
                    "content_length": request.headers.get("content-length"),
                    "content_type": request.headers.get("content-type")
                }
            )
        
        response = None
        error_occurred = False
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate response time
            duration_ms = (time.time() - start_time) * 1000
            
            # Extract user ID if available (from JWT token)
            user_id = getattr(request.state, "user_id", None)
            
            # Log response (except for health checks)
            if not is_health_check:
                logger.info(
                    f"Request completed: {method} {path} - {response.status_code}",
                    request_id=request_id,
                    user_id=user_id,
                    client_ip=client_ip,
                    endpoint=path,
                    method=method,
                    status_code=response.status_code,
                    duration_ms=round(duration_ms, 2),
                    metadata={
                        "response_size": response.headers.get("content-length"),
                        "cache_status": response.headers.get("cache-control")
                    }
                )
            
            # Record metrics (skip for health checks to reduce noise)
            if not skip_detailed:
                await self._record_metrics(method, path, response.status_code, duration_ms, user_id)
            
            # Track slow requests
            if duration_ms > 5000:  # 5 seconds
                logger.warning(
                    f"Slow request detected: {method} {path} took {duration_ms:.2f}ms",
                    request_id=request_id,
                    endpoint=path,
                    method=method,
                    duration_ms=duration_ms,
                    metadata={"threshold_ms": 5000}
                )
                
                await metrics_collector.record_metric(
                    "slow_requests",
                    1,
                    "count",
                    {"endpoint": path, "method": method}
                )
            
            return response
            
        except HTTPException as e:
            error_occurred = True
            duration_ms = (time.time() - start_time) * 1000
            
            # Log HTTP exceptions
            logger.warning(
                f"HTTP exception: {method} {path} - {e.status_code}",
                request_id=request_id,
                client_ip=client_ip,
                endpoint=path,
                method=method,
                status_code=e.status_code,
                duration_ms=round(duration_ms, 2),
                metadata={"detail": e.detail}
            )
            
            # Record error metrics
            await self._record_error_metrics(method, path, e.status_code, "HTTPException")
            
            # Track error if it's a server error
            if e.status_code >= 500:
                await error_tracker.track_error(
                    e,
                    AlertSeverity.HIGH,
                    context={
                        "endpoint": path,
                        "method": method,
                        "status_code": e.status_code,
                        "client_ip": client_ip
                    },
                    request=request
                )
            
            raise
            
        except Exception as e:
            error_occurred = True
            duration_ms = (time.time() - start_time) * 1000
            
            # Log unexpected exceptions
            logger.error(
                f"Unhandled exception: {method} {path}",
                request_id=request_id,
                client_ip=client_ip,
                endpoint=path,
                method=method,
                duration_ms=round(duration_ms, 2),
                metadata={"error_type": type(e).__name__}
            )
            
            # Record error metrics
            await self._record_error_metrics(method, path, 500, type(e).__name__)
            
            # Track critical error
            await error_tracker.track_error(
                e,
                AlertSeverity.CRITICAL,
                context={
                    "endpoint": path,
                    "method": method,
                    "client_ip": client_ip
                },
                request=request
            )
            
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address, considering proxies."""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        if hasattr(request.client, "host"):
            return request.client.host
        
        return "unknown"
    
    async def _record_metrics(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        user_id: str = None
    ):
        """Record request metrics."""
        tags = {
            "method": method,
            "endpoint": path,
            "status_code": str(status_code),
            "status_class": f"{status_code // 100}xx"
        }
        
        if user_id:
            tags["has_user"] = "true"
        
        # Record response time
        await metrics_collector.record_metric(
            "response_time",
            duration_ms,
            "milliseconds",
            tags
        )
        
        # Record request count
        await metrics_collector.record_metric(
            "request_count",
            1,
            "count",
            tags
        )
        
        # Record status code metrics
        await metrics_collector.record_metric(
            f"http_status_{status_code}",
            1,
            "count",
            {"endpoint": path, "method": method}
        )
        
        # Record user activity if user is authenticated
        if user_id:
            await metrics_collector.record_metric(
                "user_activity",
                1,
                "count",
                {"user_id": user_id, "endpoint": path}
            )
    
    async def _record_error_metrics(
        self,
        method: str,
        path: str,
        status_code: int,
        error_type: str
    ):
        """Record error-specific metrics."""
        tags = {
            "method": method,
            "endpoint": path,
            "status_code": str(status_code),
            "error_type": error_type
        }
        
        # Record error count
        await metrics_collector.record_metric(
            "error_count",
            1,
            "count",
            tags
        )
        
        # Record error rate (errors per minute)
        await metrics_collector.record_metric(
            "error_rate",
            1,
            "count",
            {"endpoint": path, "time_window": "1min"}
        )
        
        # Record specific error type
        await metrics_collector.record_metric(
            f"error_type_{error_type.lower()}",
            1,
            "count",
            {"endpoint": path}
        )


class DatabaseMonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware to monitor database operations."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Monitor database-related operations."""
        # Track database connection pool metrics
        # This would integrate with SQLAlchemy's connection pool
        
        response = await call_next(request)
        
        # Record database metrics if this was a database-heavy operation
        if hasattr(request.state, "db_queries_count"):
            await metrics_collector.record_metric(
                "database_queries",
                request.state.db_queries_count,
                "count",
                {"endpoint": request.url.path}
            )
        
        if hasattr(request.state, "db_query_time"):
            await metrics_collector.record_metric(
                "database_query_time",
                request.state.db_query_time * 1000,  # Convert to ms
                "milliseconds",
                {"endpoint": request.url.path}
            )
        
        return response


class SecurityMonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware to monitor security-related events."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.suspicious_patterns = [
            "union select",
            "<script",
            "javascript:",
            "../",
            "etc/passwd",
            "cmd.exe"
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Monitor for security threats."""
        client_ip = self._get_client_ip(request)
        
        # Check for suspicious patterns in URL
        url_str = str(request.url).lower()
        for pattern in self.suspicious_patterns:
            if pattern in url_str:
                logger.warning(
                    f"Suspicious URL pattern detected: {pattern}",
                    client_ip=client_ip,
                    endpoint=request.url.path,
                    metadata={
                        "pattern": pattern,
                        "full_url": str(request.url),
                        "user_agent": request.headers.get("user-agent")
                    }
                )
                
                await metrics_collector.record_metric(
                    "security_threats",
                    1,
                    "count",
                    {"type": "suspicious_url", "pattern": pattern}
                )
        
        # Monitor authentication failures
        response = await call_next(request)
        
        if (request.url.path.startswith("/auth/") and 
            response.status_code in [401, 403]):
            
            logger.warning(
                f"Authentication failure: {request.url.path}",
                client_ip=client_ip,
                status_code=response.status_code,
                metadata={"endpoint": request.url.path}
            )
            
            await metrics_collector.record_metric(
                "auth_failures",
                1,
                "count",
                {"endpoint": request.url.path, "client_ip": client_ip}
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