"""
Browser Automation Configuration

This module provides configuration settings for browser automation,
including headless browser setup, error handling, and platform-specific settings.
"""

import os
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from enum import Enum


class BrowserType(str, Enum):
    """Supported browser types."""
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"


class LogLevel(str, Enum):
    """Logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class BrowserAutomationSettings(BaseSettings):
    """Browser automation configuration settings."""
    
    # Browser settings
    browser_type: BrowserType = Field(default=BrowserType.CHROMIUM, env="BROWSER_TYPE")
    headless: bool = Field(default=True, env="BROWSER_HEADLESS")
    timeout_ms: int = Field(default=30000, env="BROWSER_TIMEOUT_MS")
    
    # Viewport settings
    viewport_width: int = Field(default=1920, env="BROWSER_VIEWPORT_WIDTH")
    viewport_height: int = Field(default=1080, env="BROWSER_VIEWPORT_HEIGHT")
    
    # User agent
    user_agent: str = Field(
        default=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        env="BROWSER_USER_AGENT"
    )
    
    # Performance settings
    disable_images: bool = Field(default=True, env="BROWSER_DISABLE_IMAGES")
    disable_javascript: bool = Field(default=False, env="BROWSER_DISABLE_JAVASCRIPT")
    disable_css: bool = Field(default=False, env="BROWSER_DISABLE_CSS")
    disable_fonts: bool = Field(default=True, env="BROWSER_DISABLE_FONTS")
    
    # Security settings
    disable_web_security: bool = Field(default=False, env="BROWSER_DISABLE_WEB_SECURITY")
    ignore_https_errors: bool = Field(default=False, env="BROWSER_IGNORE_HTTPS_ERRORS")
    
    # Session settings
    session_timeout_hours: int = Field(default=24, env="BROWSER_SESSION_TIMEOUT_HOURS")
    max_concurrent_sessions: int = Field(default=10, env="BROWSER_MAX_CONCURRENT_SESSIONS")
    
    # Retry settings
    max_retry_attempts: int = Field(default=3, env="BROWSER_MAX_RETRY_ATTEMPTS")
    retry_delay_seconds: int = Field(default=2, env="BROWSER_RETRY_DELAY_SECONDS")
    exponential_backoff: bool = Field(default=True, env="BROWSER_EXPONENTIAL_BACKOFF")
    
    # Error handling
    screenshot_on_error: bool = Field(default=True, env="BROWSER_SCREENSHOT_ON_ERROR")
    save_page_source_on_error: bool = Field(default=False, env="BROWSER_SAVE_PAGE_SOURCE_ON_ERROR")
    
    # Logging
    log_level: LogLevel = Field(default=LogLevel.INFO, env="BROWSER_LOG_LEVEL")
    log_browser_console: bool = Field(default=False, env="BROWSER_LOG_CONSOLE")
    
    # Storage paths
    screenshots_dir: str = Field(default="/tmp/browser_screenshots", env="BROWSER_SCREENSHOTS_DIR")
    downloads_dir: str = Field(default="/tmp/browser_downloads", env="BROWSER_DOWNLOADS_DIR")
    
    # Encryption
    credentials_encryption_key: Optional[str] = Field(default=None, env="BROWSER_CREDENTIALS_KEY")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


class PlatformBrowserConfig:
    """Platform-specific browser configuration."""
    
    # Platform-specific timeouts (in milliseconds)
    PLATFORM_TIMEOUTS = {
        "meesho": 45000,      # Meesho can be slow
        "snapdeal": 30000,    # Standard timeout
        "indiamart": 35000,   # Slightly longer for IndiaMART
    }
    
    # Platform-specific selectors
    PLATFORM_SELECTORS = {
        "meesho": {
            "login": {
                "email_input": 'input[type="email"], input[name="email"]',
                "password_input": 'input[type="password"], input[name="password"]',
                "submit_button": 'button[type="submit"], .login-button',
                "error_message": '.error-message, .alert-danger, [data-testid="error"]',
                "success_indicator": 'dashboard, supplier'
            },
            "posting": {
                "title_input": 'input[name="title"], [data-testid="product-title"]',
                "description_input": 'textarea[name="description"], [data-testid="product-description"]',
                "price_input": 'input[name="price"], [data-testid="price"]',
                "file_input": 'input[type="file"]',
                "submit_button": 'button[type="submit"], .submit-button',
                "success_message": '.success-message, .alert-success, [data-testid="success"]'
            }
        },
        "snapdeal": {
            "login": {
                "email_input": 'input[name="username"], input[type="email"]',
                "password_input": 'input[name="password"], input[type="password"]',
                "submit_button": 'button[type="submit"], .login-btn',
                "success_indicator": 'dashboard, seller'
            },
            "posting": {
                "title_input": '[name="productName"]',
                "description_input": '[name="description"]',
                "category_dropdown": '.category-dropdown',
                "submit_button": '.submit-product',
                "success_message": '.success-message'
            }
        },
        "indiamart": {
            "login": {
                "email_input": 'input[name="email"]',
                "password_input": 'input[name="password"]',
                "submit_button": 'input[type="submit"], .login-button',
                "success_indicator": 'my-indiamart, dashboard'
            },
            "posting": {
                "title_input": '[name="product_name"]',
                "description_input": '[name="product_description"]',
                "price_input": '[name="price"]',
                "submit_button": '.add-product-btn',
                "success_message": '.success-msg'
            }
        }
    }
    
    # Platform URLs
    PLATFORM_URLS = {
        "meesho": {
            "base": "https://supplier.meesho.com",
            "login": "https://supplier.meesho.com/login",
            "dashboard": "https://supplier.meesho.com/dashboard",
            "add_product": "https://supplier.meesho.com/products/add"
        },
        "snapdeal": {
            "base": "https://seller.snapdeal.com",
            "login": "https://seller.snapdeal.com/login",
            "dashboard": "https://seller.snapdeal.com/dashboard",
            "add_product": "https://seller.snapdeal.com/products/add"
        },
        "indiamart": {
            "base": "https://seller.indiamart.com",
            "login": "https://seller.indiamart.com/login",
            "dashboard": "https://seller.indiamart.com/my-indiamart",
            "add_product": "https://seller.indiamart.com/products/add"
        }
    }
    
    # Browser launch arguments for different environments
    BROWSER_ARGS = {
        "production": [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--disable-extensions",
            "--disable-plugins",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-features=TranslateUI",
            "--disable-ipc-flooding-protection",
            "--disable-background-networking",
            "--disable-default-apps",
            "--disable-sync",
            "--disable-translate",
            "--hide-scrollbars",
            "--metrics-recording-only",
            "--mute-audio",
            "--no-first-run",
            "--safebrowsing-disable-auto-update",
            "--ignore-certificate-errors",
            "--ignore-ssl-errors",
            "--ignore-certificate-errors-spki-list"
        ],
        "development": [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu"
        ],
        "testing": [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--disable-extensions",
            "--disable-plugins"
        ]
    }
    
    @classmethod
    def get_platform_timeout(cls, platform: str) -> int:
        """Get timeout for a specific platform."""
        return cls.PLATFORM_TIMEOUTS.get(platform.lower(), 30000)
    
    @classmethod
    def get_platform_selectors(cls, platform: str) -> Dict[str, Any]:
        """Get selectors for a specific platform."""
        return cls.PLATFORM_SELECTORS.get(platform.lower(), {})
    
    @classmethod
    def get_platform_urls(cls, platform: str) -> Dict[str, str]:
        """Get URLs for a specific platform."""
        return cls.PLATFORM_URLS.get(platform.lower(), {})
    
    @classmethod
    def get_browser_args(cls, environment: str = "production") -> List[str]:
        """Get browser launch arguments for environment."""
        return cls.BROWSER_ARGS.get(environment, cls.BROWSER_ARGS["production"])


class ErrorHandlingConfig:
    """Configuration for error handling in browser automation."""
    
    # Error categories and their retry strategies
    ERROR_STRATEGIES = {
        "network_error": {
            "max_retries": 3,
            "delay_seconds": 5,
            "exponential_backoff": True,
            "screenshot": True
        },
        "timeout_error": {
            "max_retries": 2,
            "delay_seconds": 10,
            "exponential_backoff": False,
            "screenshot": True
        },
        "element_not_found": {
            "max_retries": 3,
            "delay_seconds": 2,
            "exponential_backoff": False,
            "screenshot": True
        },
        "authentication_error": {
            "max_retries": 1,
            "delay_seconds": 0,
            "exponential_backoff": False,
            "screenshot": True
        },
        "platform_error": {
            "max_retries": 2,
            "delay_seconds": 5,
            "exponential_backoff": True,
            "screenshot": True
        }
    }
    
    # Error patterns to match against error messages
    ERROR_PATTERNS = {
        "network_error": [
            "net::ERR_",
            "Network error",
            "Connection refused",
            "Timeout",
            "DNS_PROBE_FINISHED"
        ],
        "authentication_error": [
            "Invalid credentials",
            "Login failed",
            "Authentication failed",
            "Incorrect password",
            "User not found"
        ],
        "element_not_found": [
            "Element not found",
            "Selector not found",
            "No such element",
            "Element is not visible"
        ],
        "platform_error": [
            "Server error",
            "Internal error",
            "Service unavailable",
            "Maintenance mode"
        ]
    }
    
    @classmethod
    def get_error_strategy(cls, error_type: str) -> Dict[str, Any]:
        """Get error handling strategy for error type."""
        return cls.ERROR_STRATEGIES.get(error_type, cls.ERROR_STRATEGIES["platform_error"])
    
    @classmethod
    def classify_error(cls, error_message: str) -> str:
        """Classify error based on error message."""
        error_message_lower = error_message.lower()
        
        for error_type, patterns in cls.ERROR_PATTERNS.items():
            for pattern in patterns:
                if pattern.lower() in error_message_lower:
                    return error_type
        
        return "platform_error"  # Default category


# Global configuration instance
browser_settings = BrowserAutomationSettings()


def get_browser_settings() -> BrowserAutomationSettings:
    """Get browser automation settings."""
    return browser_settings


def get_platform_config() -> PlatformBrowserConfig:
    """Get platform-specific browser configuration."""
    return PlatformBrowserConfig()


def get_error_config() -> ErrorHandlingConfig:
    """Get error handling configuration."""
    return ErrorHandlingConfig()