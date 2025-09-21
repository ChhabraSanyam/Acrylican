"""
Pytest configuration for deployment tests.
"""

import pytest
import os
import time
import requests
from typing import Generator


@pytest.fixture(scope="session", autouse=True)
def wait_for_services():
    """Wait for services to be ready before running tests."""
    api_url = os.getenv("TEST_API_URL", "http://localhost:8000")
    frontend_url = os.getenv("TEST_BASE_URL", "http://localhost")
    
    max_wait_time = 300  # 5 minutes
    check_interval = 10  # 10 seconds
    
    print(f"\nWaiting for services to be ready...")
    print(f"API URL: {api_url}")
    print(f"Frontend URL: {frontend_url}")
    
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        try:
            # Check API health
            api_response = requests.get(f"{api_url}/health", timeout=10)
            if api_response.status_code == 200:
                print(f"✅ API is ready")
                break
        except requests.exceptions.RequestException:
            pass
        
        print(f"⏳ Waiting for services... ({int(time.time() - start_time)}s)")
        time.sleep(check_interval)
    else:
        pytest.fail(f"Services did not become ready within {max_wait_time} seconds")
    
    # Additional small delay to ensure full readiness
    time.sleep(5)


@pytest.fixture(scope="session")
def deployment_config():
    """Deployment configuration for tests."""
    return {
        "api_url": os.getenv("TEST_API_URL", "http://localhost:8000"),
        "frontend_url": os.getenv("TEST_BASE_URL", "http://localhost"),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "db_host": os.getenv("DB_HOST", "localhost"),
        "db_port": int(os.getenv("DB_PORT", "5432")),
        "redis_host": os.getenv("REDIS_HOST", "localhost"),
        "redis_port": int(os.getenv("REDIS_PORT", "6379")),
    }


@pytest.fixture(scope="function")
def cleanup_test_data():
    """Cleanup test data after each test."""
    yield
    
    # Cleanup logic here if needed
    # For example, remove test users, test posts, etc.
    pass


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "deployment: marks tests as deployment tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers."""
    for item in items:
        # Mark all tests in deployment directory as deployment tests
        if "deployment" in str(item.fspath):
            item.add_marker(pytest.mark.deployment)
        
        # Mark slow tests
        if "concurrent" in item.name or "performance" in item.name:
            item.add_marker(pytest.mark.slow)