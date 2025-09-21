import pytest
from app.config import settings


@pytest.mark.unit
def test_default_settings():
    """Test that default settings are loaded correctly."""
    assert settings.environment == "development"
    assert settings.jwt_algorithm == "HS256"
    assert settings.jwt_access_token_expire_minutes == 30
    assert settings.bcrypt_rounds == 12
    assert settings.max_file_size == 10 * 1024 * 1024  # 10MB
    assert "image/jpeg" in settings.allowed_image_types
    assert "image/png" in settings.allowed_image_types
    assert "image/webp" in settings.allowed_image_types


@pytest.mark.unit
def test_cors_origins():
    """Test that CORS origins are configured."""
    assert "http://localhost:3000" in settings.cors_origins


@pytest.mark.unit
def test_database_url():
    """Test that database URL is configured."""
    assert settings.database_url is not None
    assert "postgresql" in settings.database_url or "sqlite" in settings.database_url