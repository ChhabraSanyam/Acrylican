"""
Monitoring and error tracking system for the Artisan Promotion Platform.

This module provides:
- Structured logging with JSON format
- Error tracking and alerting
- Performance metrics collection
- Health check utilities
- Application monitoring
"""

import json
import time
import logging
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio
from contextlib import asynccontextmanager

from fastapi import Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis

from .config import settings
from .database import get_db


class LogLevel(str, Enum):
    """Log levels for structured logging."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class LogEntry:
    """Structured log entry."""
    timestamp: str
    level: LogLevel
    message: str
    service: str
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    client_ip: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    status_code: Optional[int] = None
    duration_ms: Optional[float] = None
    error_type: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class MetricEntry:
    """Performance metric entry."""
    timestamp: str
    metric_name: str
    value: float
    unit: str
    tags: Optional[Dict[str, str]] = None


@dataclass
class AlertEntry:
    """Alert entry for error tracking."""
    timestamp: str
    severity: AlertSeverity
    title: str
    message: str
    service: str
    error_type: Optional[str] = None
    stack_trace: Optional[str] = None
    request_context: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class StructuredLogger:
    """Structured JSON logger."""
    
    def __init__(self, service_name: str = "artisan-platform"):
        self.service_name = service_name
        self.logger = logging.getLogger(service_name)
        
        # Configure JSON formatter
        handler = logging.StreamHandler()
        handler.setFormatter(self._get_json_formatter())
        
        self.logger.handlers.clear()
        self.logger.addHandler(handler)
        self.logger.setLevel(
            logging.DEBUG if settings.environment == "development" else logging.INFO
        )
    
    def _get_json_formatter(self) -> logging.Formatter:
        """Get JSON formatter for structured logging."""
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "level": record.levelname,
                    "message": record.getMessage(),
                    "service": "artisan-platform",
                    "logger": record.name,
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno
                }
                
                # Add extra fields if present
                if hasattr(record, 'request_id'):
                    log_entry['request_id'] = record.request_id
                if hasattr(record, 'user_id'):
                    log_entry['user_id'] = record.user_id
                if hasattr(record, 'client_ip'):
                    log_entry['client_ip'] = record.client_ip
                if hasattr(record, 'endpoint'):
                    log_entry['endpoint'] = record.endpoint
                if hasattr(record, 'method'):
                    log_entry['method'] = record.method
                if hasattr(record, 'status_code'):
                    log_entry['status_code'] = record.status_code
                if hasattr(record, 'duration_ms'):
                    log_entry['duration_ms'] = record.duration_ms
                if hasattr(record, 'metadata'):
                    log_entry['metadata'] = record.metadata
                
                # Add exception info if present
                if record.exc_info and record.exc_info[0]:
                    log_entry['error_type'] = record.exc_info[0].__name__
                    log_entry['stack_trace'] = self.formatException(record.exc_info)
                
                return json.dumps(log_entry)
        
        return JSONFormatter()
    
    def log(self, level: LogLevel, message: str, **kwargs):
        """Log a structured message."""
        # Separate logging-specific kwargs from extra data
        logging_kwargs = {}
        extra = {}
        
        for k, v in kwargs.items():
            if v is not None:
                if k in ['exc_info', 'stack_info', 'stacklevel']:
                    logging_kwargs[k] = v
                else:
                    extra[k] = v
        
        getattr(self.logger, level.lower())(message, extra=extra, **logging_kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.log(LogLevel.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self.log(LogLevel.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.log(LogLevel.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self.log(LogLevel.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self.log(LogLevel.CRITICAL, message, **kwargs)


class MetricsCollector:
    """Collect and store performance metrics."""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.metrics_buffer: List[MetricEntry] = []
        self.buffer_size = 100
        self.flush_interval = 60  # seconds
    
    async def initialize(self):
        """Initialize Redis connection for metrics storage."""
        try:
            self.redis_client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
        except Exception as e:
            logger.error(f"Failed to initialize metrics Redis: {e}")
    
    async def record_metric(
        self,
        name: str,
        value: float,
        unit: str = "count",
        tags: Optional[Dict[str, str]] = None
    ):
        """Record a performance metric."""
        metric = MetricEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            metric_name=name,
            value=value,
            unit=unit,
            tags=tags or {}
        )
        
        self.metrics_buffer.append(metric)
        
        # Flush buffer if it's full
        if len(self.metrics_buffer) >= self.buffer_size:
            await self._flush_metrics()
    
    async def _flush_metrics(self):
        """Flush metrics buffer to Redis."""
        if not self.redis_client or not self.metrics_buffer:
            return
        
        try:
            # Store metrics in Redis with TTL
            pipe = self.redis_client.pipeline()
            
            for metric in self.metrics_buffer:
                key = f"metrics:{metric.metric_name}:{metric.timestamp}"
                pipe.setex(key, 86400 * 7, json.dumps(asdict(metric)))  # 7 days TTL
            
            await pipe.execute()
            self.metrics_buffer.clear()
            
        except Exception as e:
            logger.error(f"Failed to flush metrics: {e}")
    
    async def get_metrics(
        self,
        metric_name: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[MetricEntry]:
        """Retrieve metrics for a time range."""
        if not self.redis_client:
            return []
        
        try:
            pattern = f"metrics:{metric_name}:*"
            keys = await self.redis_client.keys(pattern)
            
            metrics = []
            for key in keys:
                data = await self.redis_client.get(key)
                if data:
                    metric_dict = json.loads(data)
                    metric = MetricEntry(**metric_dict)
                    
                    # Filter by time range
                    metric_time = datetime.fromisoformat(metric.timestamp.replace('Z', '+00:00'))
                    if start_time <= metric_time <= end_time:
                        metrics.append(metric)
            
            return sorted(metrics, key=lambda m: m.timestamp)
            
        except Exception as e:
            logger.error(f"Failed to retrieve metrics: {e}")
            return []
    
    @asynccontextmanager
    async def measure_time(self, metric_name: str, tags: Optional[Dict[str, str]] = None):
        """Context manager to measure execution time."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = (time.time() - start_time) * 1000  # Convert to milliseconds
            await self.record_metric(metric_name, duration, "milliseconds", tags)


class ErrorTracker:
    """Track and alert on application errors."""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.error_thresholds = {
            "error_rate_5min": 10,  # Max 10 errors per 5 minutes
            "critical_errors": 1,   # Any critical error triggers alert
            "database_errors": 5,   # Max 5 DB errors per 5 minutes
            "external_api_errors": 15  # Max 15 API errors per 5 minutes
        }
    
    async def initialize(self):
        """Initialize Redis connection for error tracking."""
        try:
            self.redis_client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
        except Exception as e:
            logger.error(f"Failed to initialize error tracking Redis: {e}")
    
    async def track_error(
        self,
        error: Exception,
        severity: AlertSeverity = AlertSeverity.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None
    ):
        """Track an error and potentially trigger alerts."""
        error_type = type(error).__name__
        error_message = str(error)
        
        # Create alert entry
        alert = AlertEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            severity=severity,
            title=f"{error_type}: {error_message[:100]}",
            message=error_message,
            service="artisan-platform",
            error_type=error_type,
            stack_trace=traceback.format_exc(),
            request_context=self._extract_request_context(request) if request else None,
            metadata=context
        )
        
        # Store error
        await self._store_error(alert)
        
        # Check if we should trigger an alert
        await self._check_alert_thresholds(error_type, severity)
        
        # Log the error
        logger.error(
            f"Error tracked: {error_type}",
            extra={
                "error_type": error_type,
                "severity": severity.value,
                "metadata": context,
                "request_id": getattr(request, "state", {}).get("request_id") if request else None
            },
            exc_info=True
        )
    
    def _extract_request_context(self, request: Request) -> Dict[str, Any]:
        """Extract relevant context from request."""
        return {
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers),
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent"),
            "request_id": getattr(request.state, "request_id", None)
        }
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP from request."""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        if hasattr(request.client, "host"):
            return request.client.host
        
        return "unknown"
    
    async def _store_error(self, alert: AlertEntry):
        """Store error in Redis."""
        if not self.redis_client:
            return
        
        try:
            key = f"errors:{alert.timestamp}:{alert.error_type}"
            await self.redis_client.setex(
                key,
                86400 * 30,  # 30 days TTL
                json.dumps(asdict(alert))
            )
            
            # Also store in error count for threshold checking
            count_key = f"error_count:{alert.error_type}:{datetime.utcnow().strftime('%Y-%m-%d-%H-%M')}"
            await self.redis_client.incr(count_key)
            await self.redis_client.expire(count_key, 300)  # 5 minutes TTL
            
        except Exception as e:
            logger.error(f"Failed to store error: {e}")
    
    async def _check_alert_thresholds(self, error_type: str, severity: AlertSeverity):
        """Check if error thresholds are exceeded and trigger alerts."""
        if not self.redis_client:
            return
        
        try:
            # Check critical errors (immediate alert)
            if severity == AlertSeverity.CRITICAL:
                await self._trigger_alert(
                    f"Critical error occurred: {error_type}",
                    AlertSeverity.CRITICAL
                )
                return
            
            # Check error rate thresholds
            current_minute = datetime.utcnow().strftime('%Y-%m-%d-%H-%M')
            count_key = f"error_count:{error_type}:{current_minute}"
            
            error_count = await self.redis_client.get(count_key)
            if error_count:
                count = int(error_count)
                
                # Check specific error type thresholds
                threshold = self.error_thresholds.get(f"{error_type.lower()}_errors", 
                                                    self.error_thresholds["error_rate_5min"])
                
                if count >= threshold:
                    await self._trigger_alert(
                        f"High error rate: {count} {error_type} errors in 5 minutes",
                        AlertSeverity.HIGH
                    )
        
        except Exception as e:
            logger.error(f"Failed to check alert thresholds: {e}")
    
    async def _trigger_alert(self, message: str, severity: AlertSeverity):
        """Trigger an alert (in production, this would send to alerting system)."""
        alert_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "severity": severity.value,
            "message": message,
            "service": "artisan-platform"
        }
        
        # In production, you would send this to:
        # - Slack webhook
        # - PagerDuty
        # - Email alerts
        # - SMS alerts
        # For now, we'll log it as a critical message
        
        logger.critical(f"ALERT [{severity.value.upper()}]: {message}", extra=alert_data)
        
        # Store alert for dashboard
        if self.redis_client:
            try:
                key = f"alerts:{datetime.utcnow().isoformat()}"
                await self.redis_client.setex(key, 86400 * 7, json.dumps(alert_data))
            except Exception as e:
                logger.error(f"Failed to store alert: {e}")
    
    async def get_recent_errors(self, hours: int = 24) -> List[AlertEntry]:
        """Get recent errors for dashboard."""
        if not self.redis_client:
            return []
        
        try:
            pattern = "errors:*"
            keys = await self.redis_client.keys(pattern)
            
            errors = []
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            for key in keys:
                data = await self.redis_client.get(key)
                if data:
                    error_dict = json.loads(data)
                    error = AlertEntry(**error_dict)
                    
                    error_time = datetime.fromisoformat(error.timestamp.replace('Z', '+00:00'))
                    if error_time >= cutoff_time:
                        errors.append(error)
            
            return sorted(errors, key=lambda e: e.timestamp, reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to retrieve recent errors: {e}")
            return []


class HealthChecker:
    """Health check utilities for monitoring system health."""
    
    def __init__(self):
        self.checks = {}
    
    def register_check(self, name: str, check_func):
        """Register a health check function."""
        self.checks[name] = check_func
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all registered health checks."""
        results = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "checks": {}
        }
        
        overall_healthy = True
        
        for name, check_func in self.checks.items():
            try:
                start_time = time.time()
                check_result = await check_func()
                duration = (time.time() - start_time) * 1000
                
                results["checks"][name] = {
                    "status": "healthy" if check_result else "unhealthy",
                    "duration_ms": round(duration, 2),
                    "details": check_result if isinstance(check_result, dict) else {}
                }
                
                if not check_result:
                    overall_healthy = False
                    
            except Exception as e:
                results["checks"][name] = {
                    "status": "error",
                    "error": str(e),
                    "duration_ms": 0
                }
                overall_healthy = False
        
        results["status"] = "healthy" if overall_healthy else "unhealthy"
        return results
    
    async def check_database(self) -> bool:
        """Check database connectivity."""
        try:
            async with get_db() as db:
                result = await db.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception:
            return False
    
    async def check_redis(self) -> bool:
        """Check Redis connectivity."""
        try:
            redis_client = redis.from_url(settings.redis_url)
            await redis_client.ping()
            await redis_client.close()
            return True
        except Exception:
            return False
    
    async def check_external_apis(self) -> Dict[str, bool]:
        """Check external API connectivity."""
        import httpx
        
        results = {}
        apis_to_check = [
            ("google_gemini", "https://generativelanguage.googleapis.com"),
            ("facebook_graph", "https://graph.facebook.com"),
            ("pinterest_api", "https://api.pinterest.com"),
        ]
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            for name, url in apis_to_check:
                try:
                    response = await client.get(url)
                    results[name] = response.status_code < 500
                except Exception:
                    results[name] = False
        
        return results


# Global instances
logger = StructuredLogger()
metrics_collector = MetricsCollector()
error_tracker = ErrorTracker()
health_checker = HealthChecker()


async def initialize_monitoring():
    """Initialize all monitoring components."""
    await metrics_collector.initialize()
    await error_tracker.initialize()
    
    # Register health checks
    health_checker.register_check("database", health_checker.check_database)
    health_checker.register_check("redis", health_checker.check_redis)
    health_checker.register_check("external_apis", health_checker.check_external_apis)
    
    logger.info("Monitoring system initialized")


async def shutdown_monitoring():
    """Shutdown monitoring components."""
    await metrics_collector._flush_metrics()
    logger.info("Monitoring system shutdown")