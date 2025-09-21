from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # Database Configuration
    database_url: str = "sqlite:///./test.db"
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379"
    
    # JWT Configuration
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production-" + "a" * 32)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    
    # Environment
    environment: str = "development"
    
    # External APIs
    gemini_api_key: str = ""
    
    # Cloud Storage Configuration
    storage_provider: str = "aws"  # Options: aws, gcp, cloudflare
    
    # AWS S3 Configuration
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_s3_bucket: str = ""
    aws_region: str = "us-east-1"
    
    # Google Cloud Storage Configuration
    gcp_project_id: str = ""
    gcp_bucket_name: str = ""
    gcp_credentials_path: str = ""
    
    # Cloudflare R2 Configuration (S3-compatible)
    cloudflare_account_id: str = ""
    cloudflare_access_key_id: str = ""
    cloudflare_secret_access_key: str = ""
    cloudflare_bucket_name: str = ""
    cloudflare_endpoint_url: str = ""
    
    # CORS Configuration
    cors_origins: List[str] = ["http://localhost:3000"]
    
    # Security
    bcrypt_rounds: int = 12
    session_timeout_minutes: int = 30
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15
    
    # Rate Limiting
    rate_limit_enabled: bool = True
    default_rate_limit: int = 100  # requests per window
    auth_rate_limit: int = 5  # login attempts per window
    
    # File Upload Security
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_image_types: List[str] = ["image/jpeg", "image/png", "image/webp"]
    max_files_per_upload: int = 10
    
    # Content Security
    max_content_length: int = 10000  # characters
    max_title_length: int = 200
    max_description_length: int = 5000
    max_hashtags: int = 30
    
    # API Security
    api_key_length: int = 32
    token_encryption_enabled: bool = True
    
    # Monitoring
    log_security_events: bool = True
    log_failed_auth: bool = True
    log_rate_limits: bool = True
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False
    }


# Global settings instance
settings = Settings()