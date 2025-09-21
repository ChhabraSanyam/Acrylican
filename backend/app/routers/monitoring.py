"""
Monitoring and health check endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
import redis.asyncio as redis
from ..database import get_db
from ..monitoring_config import HealthChecker, metrics_collector, logger
from ..config import settings

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

# Redis client for health checks
redis_client = redis.from_url(settings.REDIS_URL)


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Comprehensive health check endpoint
    Returns the health status of all system components
    """
    try:
        health_checker = HealthChecker(db, redis_client)
        health_status = await health_checker.check_health()
        
        # Log health check
        logger.info("Health check performed", extra={
            "status": health_status["status"],
            "checks": len(health_status["checks"])
        })
        
        return health_status
    except Exception as e:
        logger.error("Health check failed", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="Health check failed")


@router.get("/health/liveness")
async def liveness_probe() -> Dict[str, str]:
    """
    Kubernetes liveness probe endpoint
    Simple check to verify the application is running
    """
    return {"status": "alive", "service": "artisan-platform"}


@router.get("/health/readiness")
async def readiness_probe(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Kubernetes readiness probe endpoint
    Checks if the application is ready to serve traffic
    """
    try:
        # Quick database check
        await db.execute("SELECT 1")
        
        # Quick Redis check
        await redis_client.ping()
        
        return {
            "status": "ready",
            "service": "artisan-platform",
            "database": "connected",
            "cache": "connected"
        }
    except Exception as e:
        logger.error("Readiness check failed", extra={"error": str(e)})
        raise HTTPException(status_code=503, detail="Service not ready")


@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """
    Prometheus-compatible metrics endpoint
    Returns application metrics in a structured format
    """
    try:
        metrics = metrics_collector.get_metrics()
        
        # Add system metrics
        import psutil
        metrics['system'] = {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_usage_percent': psutil.disk_usage('/').percent
        }
        
        return metrics
    except Exception as e:
        logger.error("Failed to collect metrics", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="Metrics collection failed")


@router.get("/info")
async def service_info() -> Dict[str, Any]:
    """
    Service information endpoint
    Returns basic information about the service
    """
    import os
    from datetime import datetime
    
    return {
        "service": "artisan-platform",
        "version": os.getenv("APP_VERSION", "unknown"),
        "environment": os.getenv("ENVIRONMENT", "production"),
        "build_time": os.getenv("BUILD_TIME", "unknown"),
        "uptime": datetime.utcnow().isoformat(),
        "python_version": os.getenv("PYTHON_VERSION", "unknown")
    }