# Monitoring and Error Tracking Implementation

## Overview

This document describes the comprehensive monitoring and error tracking system implemented for the Artisan Promotion Platform. The system provides structured logging, metrics collection, error tracking with alerting, and health checks.

## Components Implemented

### 1. Structured Logging (`app/monitoring.py`)

**Features:**
- JSON-formatted logs with structured data
- Contextual information (request ID, user ID, client IP, etc.)
- Multiple log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Exception tracking with stack traces
- Metadata support for additional context

**Usage:**
```python
from app.monitoring import logger

logger.info("User action", user_id="123", endpoint="/api/products")
logger.error("Database error", exc_info=True, metadata={"query": "SELECT * FROM users"})
```

### 2. Metrics Collection (`app/monitoring.py`)

**Features:**
- Performance metrics collection (response times, request counts, etc.)
- Custom metrics with tags and metadata
- Buffer-based collection with automatic flushing
- Redis storage for persistence
- Time measurement context manager

**Usage:**
```python
from app.monitoring import metrics_collector

# Record a metric
await metrics_collector.record_metric("api_requests", 1, "count", {"endpoint": "/api/users"})

# Measure execution time
async with metrics_collector.measure_time("database_query"):
    result = await db.execute(query)
```

### 3. Error Tracking and Alerting (`app/monitoring.py`)

**Features:**
- Automatic error tracking with context
- Alert severity levels (LOW, MEDIUM, HIGH, CRITICAL)
- Threshold-based alerting
- Error aggregation and reporting
- Integration with request context

**Usage:**
```python
from app.monitoring import error_tracker, AlertSeverity

await error_tracker.track_error(
    exception,
    AlertSeverity.HIGH,
    context={"operation": "user_registration"},
    request=request
)
```

### 4. Health Checks (`app/routers/health.py`)

**Endpoints:**
- `GET /health/` - Basic health check
- `GET /health/liveness` - Kubernetes liveness probe
- `GET /health/readiness` - Kubernetes readiness probe  
- `GET /health/detailed` - Comprehensive health check with system metrics
- `GET /health/metrics` - Application metrics (requires authentication)

**Features:**
- Database connectivity checks
- Redis connectivity checks
- External API availability checks
- System resource monitoring (CPU, memory, disk)
- Application performance metrics

### 5. Monitoring Middleware (`app/monitoring_middleware.py`)

**Components:**
- `MonitoringMiddleware` - Request/response logging and metrics
- `DatabaseMonitoringMiddleware` - Database operation monitoring
- `SecurityMonitoringMiddleware` - Security event monitoring

**Features:**
- Request correlation IDs
- Response time tracking
- Error rate monitoring
- Security threat detection
- User activity tracking

## Configuration

### Environment Variables

```bash
# Redis configuration for metrics storage
REDIS_URL=redis://localhost:6379

# Logging level
LOG_LEVEL=INFO

# Environment
ENVIRONMENT=development
```

### Dependencies Added

```txt
psutil==5.9.6  # System metrics
```

## Integration

### Application Startup

The monitoring system is integrated into the FastAPI application lifecycle:

```python
# app/main.py
from .monitoring import initialize_monitoring, shutdown_monitoring

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await initialize_monitoring()
    yield
    # Shutdown
    await shutdown_monitoring()

app = FastAPI(lifespan=lifespan)
```

### Middleware Stack

```python
# Order matters - monitoring middleware should be first
app.add_middleware(MonitoringMiddleware)
app.add_middleware(DatabaseMonitoringMiddleware)
app.add_middleware(SecurityMonitoringMiddleware)
app.add_middleware(SecurityMiddleware)
# ... other middleware
```

## Testing

### Unit Tests (`tests/test_monitoring.py`)

- Structured logging functionality
- Metrics collection and retrieval
- Error tracking and alerting
- Health check endpoints
- Monitoring middleware

### Integration Tests (`tests/test_monitoring_integration.py`)

- End-to-end monitoring workflows
- Real service integration (when available)
- Performance monitoring
- Security monitoring
- Concurrent request handling

### Manual Testing (`test_monitoring_manual.py`)

A comprehensive manual test script that demonstrates all monitoring features:

```bash
cd backend
python test_monitoring_manual.py
```

## Monitoring Dashboard Data

The system provides data for monitoring dashboards through the `/health/metrics` endpoint:

```json
{
  "metrics": {
    "response_times": [...],
    "error_rates": [...],
    "request_counts": [...]
  },
  "recent_errors": [...],
  "summary": {
    "total_errors": 5,
    "avg_response_time": 150.5,
    "total_requests": 1000
  }
}
```

## Production Considerations

### Redis Configuration

For production, ensure Redis is properly configured:
- Persistence enabled
- Memory limits set
- Clustering for high availability
- Monitoring and alerting

### Log Aggregation

In production, logs should be aggregated using tools like:
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Fluentd
- Grafana Loki
- Cloud logging services (AWS CloudWatch, Google Cloud Logging)

### Alerting Integration

The alert system can be extended to integrate with:
- Slack webhooks
- PagerDuty
- Email notifications
- SMS alerts
- Custom webhook endpoints

### Performance Impact

The monitoring system is designed to be lightweight:
- Asynchronous operations
- Buffered metrics collection
- Minimal overhead on request processing
- Graceful degradation when Redis is unavailable

## Security Considerations

- Sensitive data is not logged
- PII is excluded from metrics
- Authentication required for detailed metrics
- Rate limiting on health check endpoints
- Secure Redis connection in production

## Maintenance

### Log Retention

- Application logs: 30 days
- Metrics: 7 days in Redis
- Errors: 30 days
- Alerts: 7 days

### Monitoring the Monitoring

- Health checks for Redis connectivity
- Metrics buffer size monitoring
- Error tracking system health
- Log ingestion rate monitoring

## Future Enhancements

1. **Distributed Tracing** - OpenTelemetry integration
2. **Custom Dashboards** - Grafana dashboard templates
3. **Machine Learning** - Anomaly detection for metrics
4. **Advanced Alerting** - Smart alert grouping and suppression
5. **Performance Profiling** - Code-level performance insights

## Troubleshooting

### Common Issues

1. **Redis Connection Errors**
   - Check Redis server status
   - Verify connection string
   - Check network connectivity

2. **High Memory Usage**
   - Monitor metrics buffer size
   - Adjust flush intervals
   - Check Redis memory usage

3. **Missing Metrics**
   - Verify middleware order
   - Check Redis connectivity
   - Review error logs

### Debug Mode

Enable debug logging for troubleshooting:

```python
import logging
logging.getLogger("artisan-platform").setLevel(logging.DEBUG)
```

## Compliance

The monitoring system supports compliance requirements:
- GDPR: No PII in logs/metrics
- SOC 2: Audit logging and monitoring
- HIPAA: Secure data handling (if applicable)
- PCI DSS: Security monitoring and alerting