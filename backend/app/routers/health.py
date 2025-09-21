"""
Health check endpoints for monitoring system health.

This module provides comprehensive health checks for:
- Database connectivity
- Redis connectivity
- External API availability
- System resources
- Application metrics
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
import time
import psutil
from datetime import datetime, timedelta

from ..monitoring import health_checker, metrics_collector, error_tracker, logger
from ..dependencies import get_current_user
from ..models import User

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
async def basic_health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "service": "artisan-platform",
        "version": "1.0.0"
    }


@router.get("/detailed")
async def detailed_health_check():
    """Detailed health check with all system components."""
    try:
        start_time = time.time()
        
        # Run all registered health checks
        health_results = await health_checker.run_all_checks()
        
        # Add system metrics
        system_metrics = await _get_system_metrics()
        health_results["system"] = system_metrics
        
        # Add application metrics
        app_metrics = await _get_application_metrics()
        health_results["application"] = app_metrics
        
        # Calculate total check duration
        total_duration = (time.time() - start_time) * 1000
        health_results["total_duration_ms"] = round(total_duration, 2)
        
        # Log health check
        logger.info(
            f"Health check completed in {total_duration:.2f}ms",
            metadata={"status": health_results["status"]}
        )
        
        # Return appropriate status code
        if health_results["status"] == "unhealthy":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=health_results
            )
        
        return health_results
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"status": "error", "message": str(e)}
        )


@router.get("/readiness")
async def readiness_check():
    """Kubernetes readiness probe endpoint."""
    try:
        # Check critical dependencies
        db_healthy = await health_checker.check_database()
        redis_healthy = await health_checker.check_redis()
        
        if db_healthy and redis_healthy:
            return {"status": "ready"}
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "status": "not_ready",
                    "database": db_healthy,
                    "redis": redis_healthy
                }
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "error", "message": str(e)}
        )


@router.get("/liveness")
async def liveness_check():
    """Kubernetes liveness probe endpoint."""
    # Simple check to ensure the application is running
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat() + "Z"}


@router.get("/metrics")
async def get_health_metrics(current_user: User = Depends(get_current_user)):
    """Get application health metrics (requires authentication)."""
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1)
        
        # Get various metrics
        response_time_metrics = await metrics_collector.get_metrics(
            "response_time", start_time, end_time
        )
        
        error_rate_metrics = await metrics_collector.get_metrics(
            "error_rate", start_time, end_time
        )
        
        request_count_metrics = await metrics_collector.get_metrics(
            "request_count", start_time, end_time
        )
        
        # Get recent errors
        recent_errors = await error_tracker.get_recent_errors(hours=1)
        
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "time_range": {
                "start": start_time.isoformat() + "Z",
                "end": end_time.isoformat() + "Z"
            },
            "metrics": {
                "response_times": [
                    {"timestamp": m.timestamp, "value": m.value, "unit": m.unit}
                    for m in response_time_metrics
                ],
                "error_rates": [
                    {"timestamp": m.timestamp, "value": m.value, "unit": m.unit}
                    for m in error_rate_metrics
                ],
                "request_counts": [
                    {"timestamp": m.timestamp, "value": m.value, "unit": m.unit}
                    for m in request_count_metrics
                ]
            },
            "recent_errors": [
                {
                    "timestamp": e.timestamp,
                    "severity": e.severity,
                    "title": e.title,
                    "error_type": e.error_type
                }
                for e in recent_errors[:10]  # Last 10 errors
            ],
            "summary": {
                "total_errors": len(recent_errors),
                "avg_response_time": _calculate_average([m.value for m in response_time_metrics]),
                "total_requests": sum(m.value for m in request_count_metrics)
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get health metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Failed to retrieve metrics", "message": str(e)}
        )


async def _get_system_metrics() -> Dict[str, Any]:
    """Get system resource metrics."""
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_available_gb = memory.available / (1024**3)
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        disk_free_gb = disk.free / (1024**3)
        
        # Network stats (if available)
        try:
            network = psutil.net_io_counters()
            network_stats = {
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_recv": network.packets_recv
            }
        except:
            network_stats = None
        
        return {
            "status": "healthy" if cpu_percent < 80 and memory_percent < 80 and disk_percent < 90 else "warning",
            "cpu": {
                "usage_percent": round(cpu_percent, 2),
                "status": "healthy" if cpu_percent < 80 else "warning"
            },
            "memory": {
                "usage_percent": round(memory_percent, 2),
                "available_gb": round(memory_available_gb, 2),
                "status": "healthy" if memory_percent < 80 else "warning"
            },
            "disk": {
                "usage_percent": round(disk_percent, 2),
                "free_gb": round(disk_free_gb, 2),
                "status": "healthy" if disk_percent < 90 else "warning"
            },
            "network": network_stats
        }
        
    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


async def _get_application_metrics() -> Dict[str, Any]:
    """Get application-specific metrics."""
    try:
        # Get recent metrics
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=5)
        
        # Calculate error rate
        recent_errors = await error_tracker.get_recent_errors(hours=1)
        error_count = len(recent_errors)
        
        # Get response time metrics
        response_times = await metrics_collector.get_metrics(
            "response_time", start_time, end_time
        )
        
        avg_response_time = _calculate_average([m.value for m in response_times])
        
        return {
            "status": "healthy" if error_count < 10 and avg_response_time < 1000 else "warning",
            "error_rate": {
                "count_last_hour": error_count,
                "status": "healthy" if error_count < 10 else "warning"
            },
            "response_time": {
                "avg_ms": round(avg_response_time, 2) if avg_response_time else 0,
                "status": "healthy" if avg_response_time < 1000 else "warning"
            },
            "uptime_seconds": time.time() - _get_start_time()
        }
        
    except Exception as e:
        logger.error(f"Failed to get application metrics: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


def _calculate_average(values: list) -> float:
    """Calculate average of a list of values."""
    if not values:
        return 0.0
    return sum(values) / len(values)


# Store application start time
_start_time = time.time()

def _get_start_time() -> float:
    """Get application start time."""
    return _start_time