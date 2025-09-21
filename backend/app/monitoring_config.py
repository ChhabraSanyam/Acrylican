"""
Production monitoring and logging configuration
"""
import logging
import os
import sys
from typing import Dict, Any
from datetime import datetime
import json
from pythonjsonlogger import jsonlogger


class ProductionLogger:
    """Production-ready structured logging configuration"""
    
    def __init__(self):
        self.log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        self.log_format = os.getenv('LOG_FORMAT', 'json')
        self.service_name = os.getenv('SERVICE_NAME', 'artisan-platform')
        self.environment = os.getenv('ENVIRONMENT', 'production')
        
    def setup_logging(self) -> logging.Logger:
        """Configure structured logging for production"""
        logger = logging.getLogger(self.service_name)
        logger.setLevel(getattr(logging, self.log_level))
        
        # Remove existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Create console handler
        handler = logging.StreamHandler(sys.stdout)
        
        if self.log_format == 'json':
            # JSON formatter for structured logging
            formatter = jsonlogger.JsonFormatter(
                fmt='%(asctime)s %(name)s %(levelname)s %(message)s',
                datefmt='%Y-%m-%dT%H:%M:%S'
            )
        else:
            # Standard formatter for development
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # Add context filter
        logger.addFilter(self._context_filter)
        
        return logger
    
    def _context_filter(self, record):
        """Add context information to log records"""
        record.service = self.service_name
        record.environment = self.environment
        record.timestamp = datetime.utcnow().isoformat()
        return True


class MetricsCollector:
    """Collect and expose application metrics"""
    
    def __init__(self):
        self.metrics = {}
        self.counters = {}
        self.gauges = {}
        self.histograms = {}
    
    def increment_counter(self, name: str, value: int = 1, labels: Dict[str, str] = None):
        """Increment a counter metric"""
        key = self._get_metric_key(name, labels)
        self.counters[key] = self.counters.get(key, 0) + value
    
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge metric value"""
        key = self._get_metric_key(name, labels)
        self.gauges[key] = value
    
    def record_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a histogram metric value"""
        key = self._get_metric_key(name, labels)
        if key not in self.histograms:
            self.histograms[key] = []
        self.histograms[key].append(value)
    
    def _get_metric_key(self, name: str, labels: Dict[str, str] = None) -> str:
        """Generate metric key with labels"""
        if not labels:
            return name
        label_str = ','.join(f'{k}={v}' for k, v in sorted(labels.items()))
        return f'{name}{{{label_str}}}'
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics"""
        return {
            'counters': self.counters,
            'gauges': self.gauges,
            'histograms': self.histograms,
            'timestamp': datetime.utcnow().isoformat()
        }


class HealthChecker:
    """Application health check utilities"""
    
    def __init__(self, db_session, redis_client):
        self.db_session = db_session
        self.redis_client = redis_client
        self.checks = {
            'database': self._check_database,
            'redis': self._check_redis,
            'disk_space': self._check_disk_space,
            'memory': self._check_memory
        }
    
    async def check_health(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        results = {}
        overall_status = 'healthy'
        
        for check_name, check_func in self.checks.items():
            try:
                result = await check_func()
                results[check_name] = result
                if result['status'] != 'healthy':
                    overall_status = 'unhealthy'
            except Exception as e:
                results[check_name] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
                overall_status = 'unhealthy'
        
        return {
            'status': overall_status,
            'checks': results,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def _check_database(self) -> Dict[str, Any]:
        """Check database connectivity"""
        try:
            # Simple query to test connection
            result = await self.db_session.execute("SELECT 1")
            return {
                'status': 'healthy',
                'response_time_ms': 0  # Would measure actual time
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    async def _check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity"""
        try:
            await self.redis_client.ping()
            return {
                'status': 'healthy',
                'response_time_ms': 0  # Would measure actual time
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    async def _check_disk_space(self) -> Dict[str, Any]:
        """Check available disk space"""
        import shutil
        try:
            total, used, free = shutil.disk_usage('/')
            free_percent = (free / total) * 100
            
            status = 'healthy' if free_percent > 10 else 'unhealthy'
            
            return {
                'status': status,
                'free_space_gb': free // (1024**3),
                'free_percent': round(free_percent, 2)
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    async def _check_memory(self) -> Dict[str, Any]:
        """Check memory usage"""
        import psutil
        try:
            memory = psutil.virtual_memory()
            status = 'healthy' if memory.percent < 90 else 'unhealthy'
            
            return {
                'status': status,
                'used_percent': memory.percent,
                'available_gb': memory.available // (1024**3)
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }


# Global instances
production_logger = ProductionLogger()
metrics_collector = MetricsCollector()
logger = production_logger.setup_logging()