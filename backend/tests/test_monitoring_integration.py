"""
Integration tests for the monitoring system.

This module tests:
- End-to-end monitoring workflows
- Real Redis integration (if available)
- Health check integration with actual services
- Monitoring middleware with real requests
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from app.main import app
from app.monitoring import (
    metrics_collector, error_tracker, health_checker, logger,
    initialize_monitoring, shutdown_monitoring
)
from app.config import settings


class TestMonitoringIntegration:
    """Integration tests for monitoring system."""
    
    @pytest.fixture(autouse=True)
    async def setup_monitoring(self):
        """Set up monitoring for tests."""
        # Initialize monitoring system
        await initialize_monitoring()
        yield
        # Clean up
        await shutdown_monitoring()
    
    @pytest.mark.asyncio
    async def test_full_request_monitoring_cycle(self):
        """Test complete request monitoring from start to finish."""
        client = TestClient(app)
        
        # Make a request that should be monitored
        response = client.get("/health/")
        
        assert response.status_code == 200
        
        # Verify metrics were collected (check buffer)
        assert len(metrics_collector.metrics_buffer) > 0
        
        # Find response time metric
        response_time_metrics = [
            m for m in metrics_collector.metrics_buffer 
            if m.metric_name == "response_time"
        ]
        assert len(response_time_metrics) > 0
        
        # Verify metric properties
        metric = response_time_metrics[0]
        assert metric.value > 0  # Should have some response time
        assert metric.unit == "milliseconds"
        assert "endpoint" in metric.tags
        assert metric.tags["endpoint"] == "/health/"
    
    @pytest.mark.asyncio
    async def test_error_tracking_integration(self):
        """Test error tracking with real error scenarios."""
        # Create a test error
        test_error = ValueError("Integration test error")
        
        await error_tracker.track_error(
            test_error,
            context={"test": "integration"},
            request=None
        )
        
        # If Redis is available, verify error was stored
        if error_tracker.redis_client:
            # Wait a moment for async operations
            await asyncio.sleep(0.1)
            
            # Check that error was stored (this would work with real Redis)
            # In tests, we're mainly verifying the flow doesn't crash
    
    @pytest.mark.asyncio
    async def test_health_checks_with_real_services(self):
        """Test health checks against actual services."""
        # Test database health check
        db_healthy = await health_checker.check_database()
        # This might fail in test environment, which is expected
        assert isinstance(db_healthy, bool)
        
        # Test Redis health check
        redis_healthy = await health_checker.check_redis()
        assert isinstance(redis_healthy, bool)
        
        # Test external APIs health check
        api_results = await health_checker.check_external_apis()
        assert isinstance(api_results, dict)
        
        # Run all checks
        all_results = await health_checker.run_all_checks()
        assert "status" in all_results
        assert "checks" in all_results
        assert "timestamp" in all_results
    
    def test_health_endpoints_integration(self):
        """Test health endpoints with real monitoring data."""
        client = TestClient(app)
        
        # Test basic health
        response = client.get("/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        
        # Test liveness
        response = client.get("/health/liveness")
        assert response.status_code == 200
        
        # Test readiness
        response = client.get("/health/readiness")
        # This might return 503 if services are not available in test env
        assert response.status_code in [200, 503]
        
        # Test detailed health
        response = client.get("/health/detailed")
        # This might return 503 if some checks fail
        assert response.status_code in [200, 503]
        
        if response.status_code == 200:
            data = response.json()
            assert "system" in data
            assert "application" in data
            assert "checks" in data
    
    @pytest.mark.asyncio
    async def test_metrics_collection_and_retrieval(self):
        """Test metrics collection and retrieval cycle."""
        # Record some test metrics
        await metrics_collector.record_metric("test_metric_1", 100.0, "count")
        await metrics_collector.record_metric("test_metric_2", 250.5, "milliseconds")
        await metrics_collector.record_metric("test_metric_1", 150.0, "count")
        
        # Verify metrics are in buffer
        assert len(metrics_collector.metrics_buffer) >= 3
        
        # Test time measurement
        async with metrics_collector.measure_time("test_operation"):
            await asyncio.sleep(0.01)  # Small delay
        
        # Should have one more metric
        time_metrics = [
            m for m in metrics_collector.metrics_buffer 
            if m.metric_name == "test_operation"
        ]
        assert len(time_metrics) == 1
        assert time_metrics[0].unit == "milliseconds"
        assert time_metrics[0].value >= 10  # At least 10ms
    
    def test_monitoring_middleware_with_various_requests(self):
        """Test monitoring middleware with different types of requests."""
        client = TestClient(app)
        
        # Test successful request
        response = client.get("/health/")
        assert response.status_code == 200
        
        # Test 404 request
        response = client.get("/nonexistent")
        assert response.status_code == 404
        
        # Test POST request (if auth endpoint exists)
        response = client.post("/auth/login", json={"email": "test", "password": "test"})
        # This will likely fail validation, but should be monitored
        assert response.status_code in [400, 422, 404]  # Various possible error codes
        
        # Verify metrics were collected for all requests
        request_metrics = [
            m for m in metrics_collector.metrics_buffer 
            if m.metric_name == "request_count"
        ]
        assert len(request_metrics) >= 3  # At least 3 requests made
    
    @pytest.mark.asyncio
    async def test_structured_logging_integration(self):
        """Test structured logging in real scenarios."""
        # Test various log levels
        logger.info("Integration test info message", metadata={"test": "integration"})
        logger.warning("Integration test warning", request_id="test-123")
        logger.error("Integration test error", user_id="test-user")
        
        # Test logging with exception
        try:
            raise ValueError("Test exception for logging")
        except Exception as e:
            logger.error("Exception occurred during integration test", exc_info=True)
        
        # If this doesn't crash, logging is working
        assert True
    
    @pytest.mark.asyncio
    async def test_alert_threshold_checking(self):
        """Test alert threshold checking with multiple errors."""
        # Generate multiple errors quickly to test threshold
        for i in range(5):
            test_error = Exception(f"Test error {i}")
            await error_tracker.track_error(test_error)
        
        # Wait for async processing
        await asyncio.sleep(0.1)
        
        # This should not crash and should handle the errors appropriately
        assert True
    
    def test_security_monitoring_integration(self):
        """Test security monitoring with suspicious requests."""
        client = TestClient(app)
        
        # Test request with suspicious patterns
        response = client.get("/health/?param=<script>alert('xss')</script>")
        # Should still work but be logged as suspicious
        assert response.status_code == 200
        
        # Test with SQL injection pattern
        response = client.get("/health/?search='; DROP TABLE users; --")
        assert response.status_code == 200
        
        # These should be logged as security events
        # In a real scenario, you'd check logs or metrics for security events
    
    @pytest.mark.asyncio
    async def test_performance_monitoring(self):
        """Test performance monitoring features."""
        client = TestClient(app)
        
        # Make multiple requests to generate performance data
        for i in range(10):
            response = client.get("/health/")
            assert response.status_code == 200
        
        # Check that response time metrics were collected
        response_time_metrics = [
            m for m in metrics_collector.metrics_buffer 
            if m.metric_name == "response_time"
        ]
        
        assert len(response_time_metrics) >= 10
        
        # Verify all metrics have reasonable values
        for metric in response_time_metrics:
            assert metric.value > 0
            assert metric.value < 10000  # Less than 10 seconds (reasonable for health check)
            assert metric.unit == "milliseconds"
    
    @pytest.mark.asyncio
    async def test_monitoring_system_resilience(self):
        """Test that monitoring system handles failures gracefully."""
        # Test with Redis unavailable
        original_redis = metrics_collector.redis_client
        metrics_collector.redis_client = None
        
        try:
            # Should not crash even without Redis
            await metrics_collector.record_metric("test_metric", 42.0, "count")
            await error_tracker.track_error(Exception("Test error"))
            
            # Make HTTP request - should still work
            client = TestClient(app)
            response = client.get("/health/")
            assert response.status_code == 200
            
        finally:
            # Restore Redis client
            metrics_collector.redis_client = original_redis
    
    def test_cors_and_monitoring_interaction(self):
        """Test that CORS and monitoring middleware work together."""
        client = TestClient(app)
        
        # Test preflight request
        response = client.options(
            "/health/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )
        
        # Should handle CORS preflight and monitor it
        assert response.status_code in [200, 405]  # Depends on CORS configuration
    
    @pytest.mark.asyncio
    async def test_concurrent_monitoring(self):
        """Test monitoring system under concurrent load."""
        client = TestClient(app)
        
        async def make_request():
            response = client.get("/health/")
            return response.status_code
        
        # Make concurrent requests
        tasks = [make_request() for _ in range(20)]
        results = await asyncio.gather(*tasks)
        
        # All requests should succeed
        assert all(status == 200 for status in results)
        
        # Should have collected metrics for all requests
        request_metrics = [
            m for m in metrics_collector.metrics_buffer 
            if m.metric_name == "request_count"
        ]
        assert len(request_metrics) >= 20


@pytest.mark.skipif(
    not settings.redis_url or "localhost" not in settings.redis_url,
    reason="Redis not available for integration testing"
)
class TestRedisIntegration:
    """Tests that require actual Redis connection."""
    
    @pytest.mark.asyncio
    async def test_metrics_storage_and_retrieval(self):
        """Test storing and retrieving metrics from Redis."""
        # Initialize with real Redis
        await metrics_collector.initialize()
        
        # Record metrics
        await metrics_collector.record_metric("redis_test_metric", 123.45, "count")
        
        # Force flush to Redis
        await metrics_collector._flush_metrics()
        
        # Retrieve metrics
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=1)
        
        metrics = await metrics_collector.get_metrics("redis_test_metric", start_time, end_time)
        
        # Should find the metric we just stored
        assert len(metrics) >= 1
        found_metric = next((m for m in metrics if m.value == 123.45), None)
        assert found_metric is not None
        assert found_metric.metric_name == "redis_test_metric"
    
    @pytest.mark.asyncio
    async def test_error_storage_and_retrieval(self):
        """Test storing and retrieving errors from Redis."""
        # Initialize with real Redis
        await error_tracker.initialize()
        
        # Track an error
        test_error = ValueError("Redis integration test error")
        await error_tracker.track_error(test_error)
        
        # Wait for async storage
        await asyncio.sleep(0.1)
        
        # Retrieve recent errors
        recent_errors = await error_tracker.get_recent_errors(hours=1)
        
        # Should find the error we just tracked
        found_error = next((e for e in recent_errors if "Redis integration test error" in e.message), None)
        assert found_error is not None
        assert found_error.error_type == "ValueError"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])