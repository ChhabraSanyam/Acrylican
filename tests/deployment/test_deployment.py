"""
Deployment tests for production environment.

These tests verify that the deployment is successful and all components
are working correctly in the production environment.
"""

import pytest
import requests
import time
import docker
import psycopg2
import redis
from typing import Dict, Any
import os
from datetime import datetime, timedelta


class TestDeploymentHealth:
    """Test deployment health and basic functionality."""
    
    @pytest.fixture(scope="class")
    def base_url(self):
        """Base URL for the deployed application."""
        return os.getenv("TEST_BASE_URL", "http://localhost")
    
    @pytest.fixture(scope="class")
    def api_url(self):
        """API URL for the deployed application."""
        return os.getenv("TEST_API_URL", "http://localhost:8000")
    
    def test_frontend_health(self, base_url):
        """Test that frontend is responding."""
        response = requests.get(f"{base_url}/health", timeout=30)
        assert response.status_code == 200
        assert "healthy" in response.text.lower()
    
    def test_backend_health(self, api_url):
        """Test that backend API is responding."""
        response = requests.get(f"{api_url}/health", timeout=30)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "service" in data
    
    def test_backend_detailed_health(self, api_url):
        """Test detailed health check endpoint."""
        response = requests.get(f"{api_url}/health/detailed", timeout=60)
        
        # Should return 200 for healthy or 503 for unhealthy
        assert response.status_code in [200, 503]
        
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "redis" in data
        assert "total_duration_ms" in data
    
    def test_api_documentation(self, api_url):
        """Test that API documentation is accessible."""
        response = requests.get(f"{api_url}/docs", timeout=30)
        assert response.status_code == 200
        assert "swagger" in response.text.lower() or "openapi" in response.text.lower()
    
    def test_api_openapi_spec(self, api_url):
        """Test that OpenAPI specification is accessible."""
        response = requests.get(f"{api_url}/openapi.json", timeout=30)
        assert response.status_code == 200
        
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data


class TestDatabaseConnectivity:
    """Test database connectivity and basic operations."""
    
    @pytest.fixture(scope="class")
    def db_config(self):
        """Database configuration from environment."""
        return {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "5432")),
            "database": os.getenv("POSTGRES_DB", "artisan_platform"),
            "user": os.getenv("POSTGRES_USER", "artisan_user"),
            "password": os.getenv("POSTGRES_PASSWORD", "")
        }
    
    def test_database_connection(self, db_config):
        """Test database connection."""
        conn = None
        try:
            conn = psycopg2.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1
        finally:
            if conn:
                conn.close()
    
    def test_database_tables_exist(self, db_config):
        """Test that required tables exist."""
        required_tables = [
            "users", "products", "product_images", "platform_connections",
            "posts", "sale_events", "engagement_metrics", "audit_log"
        ]
        
        conn = None
        try:
            conn = psycopg2.connect(**db_config)
            cursor = conn.cursor()
            
            for table in required_tables:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = %s
                    );
                """, (table,))
                exists = cursor.fetchone()[0]
                assert exists, f"Table {table} does not exist"
        finally:
            if conn:
                conn.close()
    
    def test_database_indexes_exist(self, db_config):
        """Test that important indexes exist."""
        required_indexes = [
            "idx_audit_log_table_name",
            "idx_audit_log_timestamp",
            "idx_audit_log_user_id"
        ]
        
        conn = None
        try:
            conn = psycopg2.connect(**db_config)
            cursor = conn.cursor()
            
            for index in required_indexes:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM pg_indexes 
                        WHERE schemaname = 'public' 
                        AND indexname = %s
                    );
                """, (index,))
                exists = cursor.fetchone()[0]
                assert exists, f"Index {index} does not exist"
        finally:
            if conn:
                conn.close()


class TestRedisConnectivity:
    """Test Redis connectivity and basic operations."""
    
    @pytest.fixture(scope="class")
    def redis_config(self):
        """Redis configuration from environment."""
        return {
            "host": os.getenv("REDIS_HOST", "localhost"),
            "port": int(os.getenv("REDIS_PORT", "6379")),
            "password": os.getenv("REDIS_PASSWORD", None),
            "db": int(os.getenv("REDIS_DB", "0"))
        }
    
    def test_redis_connection(self, redis_config):
        """Test Redis connection."""
        r = redis.Redis(**redis_config)
        assert r.ping()
    
    def test_redis_basic_operations(self, redis_config):
        """Test basic Redis operations."""
        r = redis.Redis(**redis_config)
        
        # Test set and get
        test_key = f"deployment_test_{int(time.time())}"
        test_value = "deployment_test_value"
        
        r.set(test_key, test_value, ex=60)  # Expire in 60 seconds
        retrieved_value = r.get(test_key)
        
        assert retrieved_value.decode() == test_value
        
        # Clean up
        r.delete(test_key)


class TestDockerContainers:
    """Test Docker container status and health."""
    
    @pytest.fixture(scope="class")
    def docker_client(self):
        """Docker client for container inspection."""
        return docker.from_env()
    
    def test_required_containers_running(self, docker_client):
        """Test that all required containers are running."""
        required_containers = [
            "artisan-platform-backend",
            "artisan-platform-frontend",
            "artisan-platform-db",
            "artisan-platform-redis"
        ]
        
        running_containers = [
            container.name for container in docker_client.containers.list()
        ]
        
        for container_name in required_containers:
            assert container_name in running_containers, f"Container {container_name} is not running"
    
    def test_container_health_status(self, docker_client):
        """Test container health status."""
        containers_with_health = [
            "artisan-platform-backend",
            "artisan-platform-frontend",
            "artisan-platform-db",
            "artisan-platform-redis"
        ]
        
        for container_name in containers_with_health:
            try:
                container = docker_client.containers.get(container_name)
                
                # Check if container is running
                assert container.status == "running", f"Container {container_name} is not running"
                
                # Check health status if available
                if hasattr(container.attrs, 'State') and 'Health' in container.attrs['State']:
                    health_status = container.attrs['State']['Health']['Status']
                    assert health_status == "healthy", f"Container {container_name} is not healthy: {health_status}"
                    
            except docker.errors.NotFound:
                pytest.fail(f"Container {container_name} not found")


class TestAPIEndpoints:
    """Test critical API endpoints."""
    
    @pytest.fixture(scope="class")
    def api_url(self):
        """API URL for testing."""
        return os.getenv("TEST_API_URL", "http://localhost:8000")
    
    def test_root_endpoint(self, api_url):
        """Test root API endpoint."""
        response = requests.get(f"{api_url}/", timeout=30)
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "status" in data
    
    def test_auth_endpoints_exist(self, api_url):
        """Test that authentication endpoints exist."""
        # Test registration endpoint (should return 422 for missing data)
        response = requests.post(f"{api_url}/auth/register", json={}, timeout=30)
        assert response.status_code == 422  # Validation error, but endpoint exists
        
        # Test login endpoint (should return 422 for missing data)
        response = requests.post(f"{api_url}/auth/login", json={}, timeout=30)
        assert response.status_code == 422  # Validation error, but endpoint exists
    
    def test_cors_headers(self, api_url):
        """Test CORS headers are properly configured."""
        response = requests.options(f"{api_url}/health", timeout=30)
        
        # Should have CORS headers
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Methods" in response.headers


class TestPerformance:
    """Test basic performance metrics."""
    
    @pytest.fixture(scope="class")
    def api_url(self):
        """API URL for testing."""
        return os.getenv("TEST_API_URL", "http://localhost:8000")
    
    def test_response_time_health_check(self, api_url):
        """Test health check response time."""
        start_time = time.time()
        response = requests.get(f"{api_url}/health", timeout=30)
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        assert response.status_code == 200
        assert response_time < 5000, f"Health check took too long: {response_time}ms"
    
    def test_concurrent_requests(self, api_url):
        """Test handling of concurrent requests."""
        import concurrent.futures
        import threading
        
        def make_request():
            response = requests.get(f"{api_url}/health", timeout=30)
            return response.status_code == 200
        
        # Make 10 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All requests should succeed
        assert all(results), "Some concurrent requests failed"


class TestSecurity:
    """Test basic security configurations."""
    
    @pytest.fixture(scope="class")
    def api_url(self):
        """API URL for testing."""
        return os.getenv("TEST_API_URL", "http://localhost:8000")
    
    def test_security_headers(self, api_url):
        """Test that security headers are present."""
        response = requests.get(f"{api_url}/health", timeout=30)
        
        # Check for important security headers
        headers = response.headers
        
        # These headers should be present for security
        expected_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection"
        ]
        
        for header in expected_headers:
            assert header in headers, f"Security header {header} is missing"
    
    def test_https_redirect(self):
        """Test HTTPS redirect if configured."""
        # This test would be environment-specific
        # Skip if not in production with HTTPS
        if os.getenv("ENVIRONMENT") != "production":
            pytest.skip("HTTPS redirect test only for production")
        
        # Test would check HTTP to HTTPS redirect
        pass


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])