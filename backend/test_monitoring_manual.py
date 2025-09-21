#!/usr/bin/env python3
"""
Manual test script for the monitoring system.

This script demonstrates the monitoring system functionality:
- Structured logging
- Metrics collection
- Error tracking
- Health checks
"""

import asyncio
import time
from app.monitoring import (
    logger, metrics_collector, error_tracker, health_checker,
    initialize_monitoring, shutdown_monitoring, AlertSeverity
)


async def test_structured_logging():
    """Test structured logging functionality."""
    print("\n=== Testing Structured Logging ===")
    
    logger.info("Starting monitoring test", metadata={"test": "manual"})
    logger.debug("Debug message with context", request_id="test-123", user_id="user-456")
    logger.warning("Warning message", endpoint="/test", method="GET")
    logger.error("Error message for testing", status_code=500)
    
    # Test logging with exception
    try:
        raise ValueError("Test exception for logging")
    except Exception as e:
        logger.error("Exception occurred during test", exc_info=True)
    
    print("✓ Structured logging test completed")


async def test_metrics_collection():
    """Test metrics collection functionality."""
    print("\n=== Testing Metrics Collection ===")
    
    # Record various metrics
    await metrics_collector.record_metric("test_requests", 1, "count", {"endpoint": "/test"})
    await metrics_collector.record_metric("response_time", 150.5, "milliseconds", {"endpoint": "/test"})
    await metrics_collector.record_metric("database_queries", 3, "count", {"operation": "select"})
    
    # Test time measurement
    async with metrics_collector.measure_time("test_operation", {"type": "manual"}):
        await asyncio.sleep(0.1)  # Simulate work
    
    print(f"✓ Metrics buffer size: {len(metrics_collector.metrics_buffer)}")
    print("✓ Metrics collection test completed")


async def test_error_tracking():
    """Test error tracking functionality."""
    print("\n=== Testing Error Tracking ===")
    
    # Track different types of errors
    test_errors = [
        (ValueError("Test validation error"), AlertSeverity.LOW),
        (ConnectionError("Database connection failed"), AlertSeverity.HIGH),
        (Exception("Critical system error"), AlertSeverity.CRITICAL),
    ]
    
    for error, severity in test_errors:
        await error_tracker.track_error(
            error,
            severity,
            context={"test": "manual", "error_type": type(error).__name__}
        )
    
    print("✓ Error tracking test completed")


async def test_health_checks():
    """Test health check functionality."""
    print("\n=== Testing Health Checks ===")
    
    # Test individual health checks
    print("Testing database health check...")
    db_healthy = await health_checker.check_database()
    print(f"Database healthy: {db_healthy}")
    
    print("Testing Redis health check...")
    redis_healthy = await health_checker.check_redis()
    print(f"Redis healthy: {redis_healthy}")
    
    print("Testing external APIs health check...")
    api_results = await health_checker.check_external_apis()
    print(f"External APIs: {api_results}")
    
    # Test all health checks
    print("Running all health checks...")
    all_results = await health_checker.run_all_checks()
    print(f"Overall status: {all_results['status']}")
    print(f"Number of checks: {len(all_results['checks'])}")
    
    print("✓ Health checks test completed")


async def test_performance_monitoring():
    """Test performance monitoring features."""
    print("\n=== Testing Performance Monitoring ===")
    
    # Simulate multiple requests with different response times
    for i in range(10):
        start_time = time.time()
        await asyncio.sleep(0.01 + (i * 0.005))  # Varying response times
        duration = (time.time() - start_time) * 1000
        
        await metrics_collector.record_metric(
            "simulated_request_time",
            duration,
            "milliseconds",
            {"request_id": f"req_{i}", "endpoint": f"/api/test_{i % 3}"}
        )
    
    print("✓ Performance monitoring test completed")


async def main():
    """Run all monitoring tests."""
    print("🚀 Starting Monitoring System Manual Test")
    print("=" * 50)
    
    try:
        # Initialize monitoring
        print("Initializing monitoring system...")
        await initialize_monitoring()
        print("✓ Monitoring system initialized")
        
        # Run tests
        await test_structured_logging()
        await test_metrics_collection()
        await test_error_tracking()
        await test_health_checks()
        await test_performance_monitoring()
        
        # Show final metrics buffer state
        print(f"\n📊 Final metrics buffer size: {len(metrics_collector.metrics_buffer)}")
        
        # Flush metrics if Redis is available
        if metrics_collector.redis_client:
            print("Flushing metrics to Redis...")
            await metrics_collector._flush_metrics()
            print("✓ Metrics flushed to Redis")
        else:
            print("ℹ️  Redis not available - metrics stored in buffer only")
        
        print("\n🎉 All monitoring tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        logger.error(f"Manual test failed: {e}", exc_info=True)
        
    finally:
        # Shutdown monitoring
        print("\nShutting down monitoring system...")
        await shutdown_monitoring()
        print("✓ Monitoring system shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())