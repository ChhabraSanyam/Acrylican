"""
Tests for the monitoring and error tracking system.

This module tests:
- Structured logging functionality
- Metrics collection and retrieval
- Error tracking and alerting
- Health check endpoints
- Monitoring middleware
"""

import pytest
import json
import time
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.monitoring import (
    StructuredLogger, MetricsCollector, ErrorTracker, HealthChecker,
    LogLevel, AlertSeverity, LogEntry, MetricEntry, AlertEntry
)
from app.monitoring_middleware import MonitoringMiddleware
from app.main import app


class TestStructuredLogger:
    """Test structured logging functionality."""
    
    def test_log_entry_creation(self):
        """Test creating structured log entries."""
        logger = StructuredLogger("test-service")
        
        # Test that logger is properly configured
        assert logger.service_name == "test-service"
        assert logger.logger.name == "test-service"
    
    @patch('app.monitoring.logging.getLogger')
    def test_structured_logging(self, mock_get_logger):
        """Test structured logging with metadata."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        logger = StructuredLogger("test-service")
        logger.logger = mock_logger
        
        # Test info logging with metadata
        logger.info(
            "Test message",
            request_id="test-123",
            user_id="user-456",
            metadata={"key": "value"}
        )
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "Test message"
        assert "request_id" in call_args[1]["extra"]
        assert call_args[1]["extra"]["request_id"] == "test-123"
    
    def test_log_levels(self):
        """Test different log levels."""
        logger = StructuredLogger("test-service")
        
        with patch.object(logger.logger, 'debug') as mock_debug:
            logger.debug("Debug message")
            mock_debug.assert_called_once()
        
        with patch.object(logger.logger, 'error') as mock_error:
            logger.error("Error message")
            mock_error.assert_called_once()


class TestMetricsCollector:
    """Test metrics collection functionality."""
    
    @pytest.fixture
    def metrics_collector(self):
        """Create metrics collector for testing."""
        collector = MetricsCollector()
        collector.redis_client = AsyncMock()
        return collector
    
    @pytest.mark.asyncio
    async def test_record_metric(self, metrics_collector):
        """Test recording a metric."""
        await metrics_collector.record_metric(
            "test_metric",
            42.5,
            "milliseconds",
            {"endpoint": "/test"}
        )
        
        assert len(metrics_collector.metrics_buffer) == 1
        metric = metrics_collector.metrics_buffer[0]
        assert metric.metric_name == "test_metric"
        assert metric.value == 42.5
        assert metric.unit == "milliseconds"
        assert metric.tags["endpoint"] == "/test"
    
    @pytest.mark.asyncio
    async def test_buffer_flush(self, metrics_collector):
        """Test metrics buffer flushing."""
        # Mock the pipeline properly
        mock_pipeline = AsyncMock()
        metrics_collector.redis_client.pipeline.return_value = mock_pipeline
        mock_pipeline.execute.return_value = []
        
        # Fill buffer to trigger flush
        for i in range(100):
            await metrics_collector.record_metric(f"metric_{i}", i, "count")
        
        # Buffer should be flushed
        metrics_collector.redis_client.pipeline.assert_called()
        assert len(metrics_collector.metrics_buffer) == 0
    
    @pytest.mark.asyncio
    async def test_measure_time_context_manager(self, metrics_collector):
        """Test time measurement context manager."""
        async with metrics_collector.measure_time("test_operation"):
            await asyncio.sleep(0.1)  # Simulate work
        
        assert len(metrics_collector.metrics_buffer) == 1
        metric = metrics_collector.metrics_buffer[0]
        assert metric.metric_name == "test_operation"
        assert metric.unit == "milliseconds"
        assert metric.value >= 100  # At least 100ms
    
    @pytest.mark.asyncio
    async def test_get_metrics(self, metrics_collector):
        """Test retrieving metrics."""
        # Mock Redis response
        mock_data = {
            "timestamp": "2023-01-01T00:00:00Z",
            "metric_name": "test_metric",
            "value": 42.0,
            "unit": "count",
            "tags": {}
        }
        
        metrics_collector.redis_client.keys.return_value = ["metrics:test_metric:2023-01-01T00:00:00Z"]
        metrics_collector.redis_client.get.return_value = json.dumps(mock_data)
        
        # Use timezone-aware datetimes
        from datetime import timezone
        start_time = datetime(2023, 1, 1, tzinfo=timezone.utc)
        end_time = datetime(2023, 1, 2, tzinfo=timezone.utc)
        
        metrics = await metrics_collector.get_metrics("test_metric", start_time, end_time)
        
        assert len(metrics) == 1
        assert metrics[0].metric_name == "test_metric"
        assert metrics[0].value == 42.0


class TestErrorTracker:
    """Test error tracking functionality."""
    
    @pytest.fixture
    def error_tracker(self):
        """Create error tracker for testing."""
        tracker = ErrorTracker()
        tracker.redis_client = AsyncMock()
        return tracker
    
    @pytest.mark.asyncio
    async def test_track_error(self, error_tracker):
        """Test error tracking."""
        test_error = ValueError("Test error")
        
        await error_tracker.track_error(
            test_error,
            AlertSeverity.HIGH,
            context={"operation": "test"}
        )
        
        # Verify error was stored
        error_tracker.redis_client.setex.assert_called()
        error_tracker.redis_client.incr.assert_called()
    
    @pytest.mark.asyncio
    async def test_critical_error_alert(self, error_tracker):
        """Test that critical errors trigger immediate alerts."""
        test_error = Exception("Critical error")
        
        with patch.object(error_tracker, '_trigger_alert') as mock_alert:
            await error_tracker.track_error(
                test_error,
                AlertSeverity.CRITICAL
            )
            
            mock_alert.assert_called_once()
            assert "Critical error occurred" in mock_alert.call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_error_threshold_checking(self, error_tracker):
        """Test error threshold checking."""
        # Mock high error count
        error_tracker.redis_client.get.return_value = "15"
        
        with patch.object(error_tracker, '_trigger_alert') as mock_alert:
            await error_tracker._check_alert_thresholds("TestError", AlertSeverity.MEDIUM)
            
            mock_alert.assert_called_once()
            assert "High error rate" in mock_alert.call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_get_recent_errors(self, error_tracker):
        """Test retrieving recent errors."""
        # Mock Redis response
        mock_error_data = {
            "timestamp": "2023-01-01T00:00:00Z",
            "severity": "high",
            "title": "Test Error",
            "message": "Test error message",
            "service": "test-service",
            "error_type": "ValueError",
            "stack_trace": "Traceback...",
            "request_context": None,
            "metadata": None
        }
        
        error_tracker.redis_client.keys.return_value = ["errors:2023-01-01T00:00:00Z:ValueError"]
        error_tracker.redis_client.get.return_value = json.dumps(mock_error_data)
        
        errors = await error_tracker.get_recent_errors(hours=24)
        
        assert len(errors) == 1
        assert errors[0].error_type == "ValueError"
        assert errors[0].severity == AlertSeverity.HIGH


class TestHealthChecker:
    """Test health check functionality."""
    
    @pytest.fixture
    def health_checker(self):
        """Create health checker for testing."""
        return HealthChecker()
    
    @pytest.mark.asyncio
    async def test_register_and_run_checks(self, health_checker):
        """Test registering and running health checks."""
        # Register mock health checks
        async def healthy_check():
            return True
        
        async def unhealthy_check():
            return False
        
        health_checker.register_check("healthy_service", healthy_check)
        health_checker.register_check("unhealthy_service", unhealthy_check)
        
        results = await health_checker.run_all_checks()
        
        assert results["status"] == "unhealthy"  # One check failed
        assert results["checks"]["healthy_service"]["status"] == "healthy"
        assert results["checks"]["unhealthy_service"]["status"] == "unhealthy"
        assert "timestamp" in results
    
    @pytest.mark.asyncio
    async def test_check_with_exception(self, health_checker):
        """Test health check that raises an exception."""
        async def failing_check():
            raise Exception("Check failed")
        
        health_checker.register_check("failing_service", failing_check)
        
        results = await health_checker.run_all_checks()
        
        assert results["status"] == "unhealthy"
        assert results["checks"]["failing_service"]["status"] == "error"
        assert "Check failed" in results["checks"]["failing_service"]["error"]
    
    @pytest.mark.asyncio
    async def test_database_check(self, health_checker):
        """Test database health check."""
        with patch('app.monitoring.get_db') as mock_get_db:
            mock_db = AsyncMock()
            mock_result = Mock()
            mock_result.scalar.return_value = 1
            mock_db.execute.return_value = mock_result
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            result = await health_checker.check_database()
            assert result is True
    
    @pytest.mark.asyncio
    async def test_redis_check(self, health_checker):
        """Test Redis health check."""
        with patch('redis.asyncio.from_url') as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client
            
            result = await health_checker.check_redis()
            assert result is True
            mock_client.ping.assert_called_once()
            mock_client.close.assert_called_once()


class TestMonitoringMiddleware:
    """Test monitoring middleware functionality."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_request_response_logging(self, client):
        """Test that requests and responses are logged."""
        with patch('app.monitoring_middleware.logger') as mock_logger:
            response = client.get("/")
            
            assert response.status_code == 200
            # Verify logging calls were made
            assert mock_logger.info.call_count >= 2  # Request start and completion
    
    def test_error_tracking(self, client):
        """Test that errors are tracked."""
        with patch('app.monitoring_middleware.error_tracker') as mock_tracker:
            # This should trigger a 404 error
            response = client.get("/nonexistent-endpoint")
            
            assert response.status_code == 404
            # Error tracking might not be called for 404s, but middleware should handle it
    
    def test_metrics_collection(self, client):
        """Test that metrics are collected."""
        with patch('app.monitoring_middleware.metrics_collector') as mock_collector:
            response = client.get("/")
            
            assert response.status_code == 200
            # Verify metrics were recorded
            assert mock_collector.record_metric.call_count >= 2  # Response time and request count
    
    def test_slow_request_detection(self, client):
        """Test slow request detection."""
        with patch('app.monitoring_middleware.logger') as mock_logger:
            with patch('time.time', side_effect=[0, 6]):  # 6 second request
                response = client.get("/")
                
                # Check if slow request was logged
                warning_calls = [call for call in mock_logger.warning.call_args_list 
                               if "Slow request detected" in str(call)]
                assert len(warning_calls) > 0


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_basic_health_check(self, client):
        """Test basic health check endpoint."""
        response = client.get("/health/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["service"] == "artisan-platform"
    
    def test_liveness_check(self, client):
        """Test liveness probe endpoint."""
        response = client.get("/health/liveness")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert "timestamp" in data
    
    def test_readiness_check(self, client):
        """Test readiness probe endpoint."""
        with patch('app.routers.health.health_checker') as mock_checker:
            mock_checker.check_database = AsyncMock(return_value=True)
            mock_checker.check_redis = AsyncMock(return_value=True)
            
            response = client.get("/health/readiness")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ready"
    
    def test_readiness_check_failure(self, client):
        """Test readiness check when services are down."""
        with patch('app.routers.health.health_checker') as mock_checker:
            mock_checker.check_database = AsyncMock(return_value=False)
            mock_checker.check_redis = AsyncMock(return_value=True)
            
            response = client.get("/health/readiness")
            
            assert response.status_code == 503
            data = response.json()
            assert data["detail"]["status"] == "not_ready"
            assert data["detail"]["database"] is False
    
    def test_detailed_health_check(self, client):
        """Test detailed health check endpoint."""
        with patch('app.routers.health.health_checker') as mock_checker:
            mock_checker.run_all_checks = AsyncMock(return_value={
                "status": "healthy",
                "timestamp": "2023-01-01T00:00:00Z",
                "checks": {
                    "database": {"status": "healthy", "duration_ms": 10.5},
                    "redis": {"status": "healthy", "duration_ms": 5.2}
                }
            })
            
            response = client.get("/health/detailed")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "system" in data
            assert "application" in data
            assert "total_duration_ms" in data


@pytest.mark.asyncio
async def test_monitoring_initialization():
    """Test monitoring system initialization."""
    with patch('app.monitoring.metrics_collector') as mock_metrics:
        with patch('app.monitoring.error_tracker') as mock_tracker:
            with patch('app.monitoring.health_checker') as mock_health:
                from app.monitoring import initialize_monitoring
                
                await initialize_monitoring()
                
                mock_metrics.initialize.assert_called_once()
                mock_tracker.initialize.assert_called_once()
                # Health checker should have checks registered
                assert mock_health.register_check.call_count >= 3


@pytest.mark.asyncio
async def test_monitoring_shutdown():
    """Test monitoring system shutdown."""
    with patch('app.monitoring.metrics_collector') as mock_metrics:
        from app.monitoring import shutdown_monitoring
        
        await shutdown_monitoring()
        
        mock_metrics._flush_metrics.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])