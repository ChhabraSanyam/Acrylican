"""
Security configuration for the Acrylican.

This module provides security configuration and utilities for:
- Production security settings
- Security policy enforcement
- Compliance requirements
- Security monitoring configuration
"""

from typing import Dict, List, Any
from enum import Enum
from .config import settings


class SecurityLevel(str, Enum):
    """Security levels for different environments."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityConfig:
    """Security configuration based on environment and requirements."""
    
    def __init__(self):
        self.environment = settings.environment
        self.security_level = self._determine_security_level()
    
    def _determine_security_level(self) -> SecurityLevel:
        """Determine security level based on environment."""
        if self.environment == "production":
            return SecurityLevel.CRITICAL
        elif self.environment == "staging":
            return SecurityLevel.HIGH
        elif self.environment == "testing":
            return SecurityLevel.MEDIUM
        else:
            return SecurityLevel.LOW
    
    def get_rate_limits(self) -> Dict[str, Dict[str, int]]:
        """Get rate limits based on security level."""
        base_limits = {
            "default": {"max_requests": 100, "window_minutes": 15},
            "/auth/login": {"max_requests": 5, "window_minutes": 15},
            "/auth/register": {"max_requests": 3, "window_minutes": 60},
            "/auth/refresh": {"max_requests": 10, "window_minutes": 15},
            "/images/upload": {"max_requests": 20, "window_minutes": 15},
            "/content/generate": {"max_requests": 10, "window_minutes": 15},
            "/posts/create": {"max_requests": 30, "window_minutes": 15},
            "/posts/publish": {"max_requests": 50, "window_minutes": 15},
        }
        
        # Adjust limits based on security level
        multipliers = {
            SecurityLevel.LOW: 2.0,
            SecurityLevel.MEDIUM: 1.5,
            SecurityLevel.HIGH: 1.0,
            SecurityLevel.CRITICAL: 0.5
        }
        
        multiplier = multipliers[self.security_level]
        
        adjusted_limits = {}
        for endpoint, limits in base_limits.items():
            adjusted_limits[endpoint] = {
                "max_requests": max(1, int(limits["max_requests"] * multiplier)),
                "window_minutes": limits["window_minutes"]
            }
        
        return adjusted_limits
    
    def get_password_requirements(self) -> Dict[str, Any]:
        """Get password requirements based on security level."""
        base_requirements = {
            "min_length": 8,
            "max_length": 128,
            "require_uppercase": True,
            "require_lowercase": True,
            "require_digits": True,
            "require_special": True,
            "max_age_days": 90,
            "history_count": 5
        }
        
        if self.security_level == SecurityLevel.CRITICAL:
            base_requirements.update({
                "min_length": 12,
                "max_age_days": 60,
                "history_count": 10
            })
        elif self.security_level == SecurityLevel.HIGH:
            base_requirements.update({
                "min_length": 10,
                "max_age_days": 75,
                "history_count": 8
            })
        
        return base_requirements
    
    def get_session_config(self) -> Dict[str, Any]:
        """Get session configuration based on security level."""
        base_config = {
            "timeout_minutes": 30,
            "absolute_timeout_hours": 8,
            "require_reauth_for_sensitive": True,
            "secure_cookies": True,
            "httponly_cookies": True,
            "samesite": "strict"
        }
        
        if self.security_level == SecurityLevel.CRITICAL:
            base_config.update({
                "timeout_minutes": 15,
                "absolute_timeout_hours": 4
            })
        elif self.security_level == SecurityLevel.HIGH:
            base_config.update({
                "timeout_minutes": 20,
                "absolute_timeout_hours": 6
            })
        
        return base_config
    
    def get_file_upload_config(self) -> Dict[str, Any]:
        """Get file upload security configuration."""
        base_config = {
            "max_file_size": 10 * 1024 * 1024,  # 10MB
            "allowed_types": ["image/jpeg", "image/png", "image/webp"],
            "max_files_per_request": 10,
            "scan_for_malware": False,
            "quarantine_suspicious": True,
            "allowed_extensions": [".jpg", ".jpeg", ".png", ".webp"]
        }
        
        if self.security_level in [SecurityLevel.HIGH, SecurityLevel.CRITICAL]:
            base_config.update({
                "max_file_size": 5 * 1024 * 1024,  # 5MB
                "max_files_per_request": 5,
                "scan_for_malware": True
            })
        
        return base_config
    
    def get_encryption_config(self) -> Dict[str, Any]:
        """Get encryption configuration."""
        base_config = {
            "algorithm": "AES-256-GCM",
            "key_rotation_days": 90,
            "encrypt_sensitive_data": True,
            "encrypt_tokens": True,
            "encrypt_api_keys": True
        }
        
        if self.security_level == SecurityLevel.CRITICAL:
            base_config.update({
                "key_rotation_days": 30,
                "algorithm": "AES-256-GCM"  # Already the strongest
            })
        
        return base_config
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get security logging configuration."""
        base_config = {
            "log_auth_attempts": True,
            "log_failed_auth": True,
            "log_rate_limits": True,
            "log_file_uploads": True,
            "log_sensitive_operations": True,
            "log_level": "INFO",
            "retention_days": 30
        }
        
        if self.security_level in [SecurityLevel.HIGH, SecurityLevel.CRITICAL]:
            base_config.update({
                "log_level": "DEBUG",
                "retention_days": 90,
                "log_all_requests": True
            })
        
        return base_config
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get security monitoring configuration."""
        base_config = {
            "enable_intrusion_detection": False,
            "alert_on_suspicious_activity": True,
            "alert_on_rate_limit_exceeded": True,
            "alert_on_auth_failures": True,
            "max_failed_attempts": 5,
            "lockout_duration_minutes": 15
        }
        
        if self.security_level in [SecurityLevel.HIGH, SecurityLevel.CRITICAL]:
            base_config.update({
                "enable_intrusion_detection": True,
                "max_failed_attempts": 3,
                "lockout_duration_minutes": 30
            })
        
        return base_config
    
    def get_api_security_config(self) -> Dict[str, Any]:
        """Get API security configuration."""
        base_config = {
            "require_https": self.environment == "production",
            "validate_content_type": True,
            "max_request_size": 50 * 1024 * 1024,  # 50MB
            "timeout_seconds": 30,
            "enable_cors": True,
            "strict_cors": self.environment == "production"
        }
        
        if self.security_level == SecurityLevel.CRITICAL:
            base_config.update({
                "max_request_size": 10 * 1024 * 1024,  # 10MB
                "timeout_seconds": 15,
                "strict_cors": True
            })
        
        return base_config
    
    def get_compliance_requirements(self) -> Dict[str, Any]:
        """Get compliance requirements based on security level."""
        base_requirements = {
            "data_retention_days": 365,
            "audit_trail": True,
            "data_encryption_at_rest": True,
            "data_encryption_in_transit": True,
            "access_logging": True,
            "user_consent_required": True
        }
        
        if self.security_level == SecurityLevel.CRITICAL:
            base_requirements.update({
                "data_retention_days": 2555,  # 7 years
                "detailed_audit_trail": True,
                "data_anonymization": True,
                "right_to_deletion": True
            })
        
        return base_requirements
    
    def validate_security_configuration(self) -> List[Dict[str, Any]]:
        """Validate current security configuration."""
        issues = []
        
        # Check JWT secret
        if settings.jwt_secret_key == "your-secret-key-here-change-in-production":
            issues.append({
                "severity": "critical",
                "issue": "Default JWT secret key in use",
                "recommendation": "Change JWT secret key to a secure random value"
            })
        
        # Check database configuration
        if "sqlite" in settings.database_url and self.environment == "production":
            issues.append({
                "severity": "high",
                "issue": "SQLite database in production",
                "recommendation": "Use PostgreSQL or another production database"
            })
        
        # Check CORS configuration
        if "*" in settings.cors_origins and self.environment == "production":
            issues.append({
                "severity": "high",
                "issue": "CORS allows all origins in production",
                "recommendation": "Restrict CORS to specific origins"
            })
        
        # Check HTTPS enforcement
        if not self.get_api_security_config()["require_https"] and self.environment == "production":
            issues.append({
                "severity": "critical",
                "issue": "HTTPS not enforced in production",
                "recommendation": "Enable HTTPS enforcement"
            })
        
        return issues
    
    def get_security_headers(self) -> Dict[str, str]:
        """Get security headers based on security level."""
        base_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' https:; "
                "frame-ancestors 'none';"
            )
        }
        
        if self.get_api_security_config()["require_https"]:
            base_headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        if self.security_level == SecurityLevel.CRITICAL:
            # Stricter CSP for critical environments
            base_headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self'; "
                "img-src 'self' data:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self';"
            )
            
            base_headers["Permissions-Policy"] = (
                "geolocation=(), "
                "microphone=(), "
                "camera=(), "
                "payment=(), "
                "usb=(), "
                "magnetometer=(), "
                "gyroscope=(), "
                "speaker=(), "
                "fullscreen=(), "
                "sync-xhr=()"
            )
        
        return base_headers


# Global security configuration instance
security_config = SecurityConfig()