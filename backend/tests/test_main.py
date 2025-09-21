import pytest
from fastapi.testclient import TestClient


def test_root(client):
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Artisan Promotion Platform API"}


def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "environment" in data
    assert "version" in data


@pytest.mark.unit
def test_cors_headers(client):
    """Test that CORS headers are properly configured."""
    response = client.get("/", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 200
    # Check if CORS headers are present (they should be added by middleware)
    assert "access-control-allow-origin" in response.headers