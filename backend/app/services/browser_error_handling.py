"""
Browser Automation Error Handling and Retry Mechanisms

Provides robust error handling, retry logic, and recovery mechanisms
for browser automation platforms.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from enum import Enum
from dataclasses import dataclass
from functools import wraps

from playwright.async_api import TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError

from .platform_integration import (
    Platform,
    PostResult,
    PostStatus,
    PlatformIntegrationError,
    AuthenticationError,
    PostingError,
    RateLimitError
)

logger = logging.getLogger(__name__)


class ErrorType(str, Enum):
    """Types of errors that can occur during browser automation."""
    NETWORK_ERROR = "network_error"
    TIMEOUT_ERROR = "timeout_error"
    AUTHENTICATION_ERROR = "authentication_error"
    ELEMENT_NOT_FOUND = "element_not_found"
    RATE_LIMIT_ERROR = "rate_limit_error"
    CAPTCHA_ERROR = "captcha_error"
    SESSION_EXPIRED = "session_expired"
    PLATFORM_MAINTENANCE = "platform_maintenance"
    BROWSER_ERROR = "browser_error"
    VALIDATION_ERROR = "validation_error"
    UNKNOWN_ERROR = "unknown_error"


class ErrorSeverity(str, Enum):
    """Severity levels for errors."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorInfo:
    """Information about an error that occurred."""
    error_type: ErrorType
    severity: ErrorSeverity
    message: str
    platform: Platform
    timestamp: datetime
    retry_count: int = 0
    max_retries: int = 3
    retry_delay: float = 1.0
    recoverable: bool = True
    context: Optional[Dict[str, Any]] = None
    original_exception: Optional[Exception] = None


class BrowserErrorClassifier:
    """Classifies browser automation errors and determines retry strategies."""
    
    def __init__(self):
        self.error_patterns = {
            # Network related errors
            ErrorType.NETWORK_ERROR: [
                "net::ERR_NETWORK_CHANGED",
                "net::ERR_INTERNET_DISCONNECTED",
                "net::ERR_CONNECTION_REFUSED",
                "net::ERR_CONNECTION_RESET",
                "Connection refused",
                "Network error",
                "DNS resolution failed"
            ],
            
            # Timeout errors
            ErrorType.TIMEOUT_ERROR: [
                "Timeout",
                "waiting for selector",
                "waiting for element",
                "Page did not load",
                "Navigation timeout"
            ],
            
            # Authentication errors
            ErrorType.AUTHENTICATION_ERROR: [
                "Invalid credentials",
                "Login failed",
                "Authentication failed",
                "Incorrect password",
                "Account locked",
                "Two-factor authentication required"
            ],
            
            # Element not found errors
            ErrorType.ELEMENT_NOT_FOUND: [
                "Element not found",
                "Selector not found",
                "No such element",
                "Element is not visible",
                "Element is not clickable"
            ],
            
            # Rate limiting errors
            ErrorType.RATE_LIMIT_ERROR: [
                "Rate limit exceeded",
                "Too many requests",
                "Request throttled",
                "API limit reached",
                "Slow down"
            ],
            
            # CAPTCHA errors
            ErrorType.CAPTCHA_ERROR: [
                "CAPTCHA",
                "Verify you are human",
                "Security check",
                "Bot detection",
                "Suspicious activity"
            ],
            
            # Session expired errors
            ErrorType.SESSION_EXPIRED: [
                "Session expired",
                "Please log in again",
                "Authentication required",
                "Session timeout",
                "Invalid session"
            ],
            
            # Platform maintenance
            ErrorType.PLATFORM_MAINTENANCE: [
                "Maintenance mode",
                "Service unavailable",
                "Temporarily down",
                "Under maintenance",
                "503 Service Unavailable"
            ],
            
            # Browser errors
            ErrorType.BROWSER_ERROR: [
                "Browser crashed",
                "Page crashed",
                "Browser disconnected",
                "Context closed",
                "Browser process exited"
            ]
        }
        
        self.severity_mapping = {
            ErrorType.NETWORK_ERROR: ErrorSeverity.MEDIUM,
            ErrorType.TIMEOUT_ERROR: ErrorSeverity.MEDIUM,
            ErrorType.AUTHENTICATION_ERROR: ErrorSeverity.HIGH,
            ErrorType.ELEMENT_NOT_FOUND: ErrorSeverity.MEDIUM,
            ErrorType.RATE_LIMIT_ERROR: ErrorSeverity.LOW,
            ErrorType.CAPTCHA_ERROR: ErrorSeverity.HIGH,
            ErrorType.SESSION_EXPIRED: ErrorSeverity.MEDIUM,
            ErrorType.PLATFORM_MAINTENANCE: ErrorSeverity.LOW,
            ErrorType.BROWSER_ERROR: ErrorSeverity.HIGH,
            ErrorType.VALIDATION_ERROR: ErrorSeverity.MEDIUM,
            ErrorType.UNKNOWN_ERROR: ErrorSeverity.MEDIUM
        }
        
        self.retry_strategies = {
            ErrorType.NETWORK_ERROR: {"max_retries": 3, "delay": 2.0, "backoff": 2.0},
            ErrorType.TIMEOUT_ERROR: {"max_retries": 2, "delay": 5.0, "backoff": 1.5},
            ErrorType.AUTHENTICATION_ERROR: {"max_retries": 1, "delay": 1.0, "backoff": 1.0},
            ErrorType.ELEMENT_NOT_FOUND: {"max_retries": 3, "delay": 1.0, "backoff": 1.5},
            ErrorType.RATE_LIMIT_ERROR: {"max_retries": 5, "delay": 10.0, "backoff": 2.0},
            ErrorType.CAPTCHA_ERROR: {"max_retries": 0, "delay": 0.0, "backoff": 1.0},
            ErrorType.SESSION_EXPIRED: {"max_retries": 1, "delay": 1.0, "backoff": 1.0},
            ErrorType.PLATFORM_MAINTENANCE: {"max_retries": 2, "delay": 30.0, "backoff": 2.0},
            ErrorType.BROWSER_ERROR: {"max_retries": 2, "delay": 3.0, "backoff": 2.0},
            ErrorType.VALIDATION_ERROR: {"max_retries": 0, "delay": 0.0, "backoff": 1.0},
            ErrorType.UNKNOWN_ERROR: {"max_retries": 1, "delay": 2.0, "backoff": 1.5}
        }
    
    def classify_error(self, exception: Exception, platform: Platform, context: Optional[Dict[str, Any]] = None) -> ErrorInfo:
        """
        Classify an error and determine retry strategy.
        
        Args:
            exception: The exception that occurred
            platform: Platform where error occurred
            context: Additional context information
            
        Returns:
            ErrorInfo object with classification and retry strategy
        """
        error_message = str(exception).lower()
        error_type = ErrorType.UNKNOWN_ERROR
        
        # Classify based on exception type first
        if isinstance(exception, PlaywrightTimeoutError):
            error_type = ErrorType.TIMEOUT_ERROR
        elif isinstance(exception, PlaywrightError):
            error_type = ErrorType.BROWSER_ERROR
        elif isinstance(exception, AuthenticationError):
            error_type = ErrorType.AUTHENTICATION_ERROR
        elif isinstance(exception, PostingError):
            error_type = ErrorType.VALIDATION_ERROR
        elif isinstance(exception, RateLimitError):
            error_type = ErrorType.RATE_LIMIT_ERROR
        else:
            # Classify based on error message patterns
            for err_type, patterns in self.error_patterns.items():
                if any(pattern.lower() in error_message for pattern in patterns):
                    error_type = err_type
                    break
        
        # Get retry strategy
        strategy = self.retry_strategies.get(error_type, self.retry_strategies[ErrorType.UNKNOWN_ERROR])
        
        # Determine if error is recoverable
        recoverable = error_type not in [
            ErrorType.CAPTCHA_ERROR,
            ErrorType.VALIDATION_ERROR,
            ErrorType.AUTHENTICATION_ERROR  # Usually requires user intervention
        ]
        
        return ErrorInfo(
            error_type=error_type,
            severity=self.severity_mapping.get(error_type, ErrorSeverity.MEDIUM),
            message=str(exception),
            platform=platform,
            timestamp=datetime.now(),
            max_retries=strategy["max_retries"],
            retry_delay=strategy["delay"],
            recoverable=recoverable,
            context=context or {},
            original_exception=exception
        )


class RetryManager:
    """Manages retry logic for browser automation operations."""
    
    def __init__(self, classifier: Optional[BrowserErrorClassifier] = None):
        self.classifier = classifier or BrowserErrorClassifier()
        self.retry_history: Dict[str, List[ErrorInfo]] = {}
    
    def _get_retry_key(self, platform: Platform, operation: str, user_id: str = "default") -> str:
        """Generate a key for tracking retry history."""
        return f"{platform.value}_{operation}_{user_id}"
    
    async def execute_with_retry(
        self,
        operation: Callable,
        platform: Platform,
        operation_name: str,
        user_id: str = "default",
        context: Optional[Dict[str, Any]] = None,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute an operation with retry logic.
        
        Args:
            operation: The async function to execute
            platform: Platform where operation is being performed
            operation_name: Name of the operation for logging
            user_id: User identifier for tracking
            context: Additional context information
            *args, **kwargs: Arguments to pass to the operation
            
        Returns:
            Result of the operation
            
        Raises:
            Exception: If all retries are exhausted
        """
        retry_key = self._get_retry_key(platform, operation_name, user_id)
        retry_count = 0
        last_error = None
        
        while True:
            try:
                logger.info(f"Executing {operation_name} for {platform.value} (attempt {retry_count + 1})")
                result = await operation(*args, **kwargs)
                
                # Clear retry history on success
                if retry_key in self.retry_history:
                    del self.retry_history[retry_key]
                
                return result
                
            except Exception as e:
                last_error = e
                error_info = self.classifier.classify_error(e, platform, context)
                error_info.retry_count = retry_count
                
                # Track error in history
                if retry_key not in self.retry_history:
                    self.retry_history[retry_key] = []
                self.retry_history[retry_key].append(error_info)
                
                logger.warning(
                    f"{operation_name} failed for {platform.value} "
                    f"(attempt {retry_count + 1}): {error_info.error_type.value} - {error_info.message}"
                )
                
                # Check if we should retry
                if not error_info.recoverable or retry_count >= error_info.max_retries:
                    logger.error(
                        f"{operation_name} failed permanently for {platform.value} "
                        f"after {retry_count + 1} attempts: {error_info.message}"
                    )
                    raise e
                
                # Calculate delay with exponential backoff
                delay = error_info.retry_delay * (2 ** retry_count)
                logger.info(f"Retrying {operation_name} for {platform.value} in {delay} seconds...")
                
                await asyncio.sleep(delay)
                retry_count += 1
    
    def get_retry_history(self, platform: Platform, operation: str, user_id: str = "default") -> List[ErrorInfo]:
        """Get retry history for a specific operation."""
        retry_key = self._get_retry_key(platform, operation, user_id)
        return self.retry_history.get(retry_key, [])
    
    def clear_retry_history(self, platform: Platform, operation: str, user_id: str = "default"):
        """Clear retry history for a specific operation."""
        retry_key = self._get_retry_key(platform, operation, user_id)
        if retry_key in self.retry_history:
            del self.retry_history[retry_key]


class CircuitBreaker:
    """Circuit breaker pattern for browser automation operations."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 300):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count: Dict[str, int] = {}
        self.last_failure_time: Dict[str, datetime] = {}
        self.state: Dict[str, str] = {}  # "closed", "open", "half-open"
    
    def _get_circuit_key(self, platform: Platform, operation: str) -> str:
        """Generate a key for circuit breaker state."""
        return f"{platform.value}_{operation}"
    
    def _is_circuit_open(self, circuit_key: str) -> bool:
        """Check if circuit is open."""
        state = self.state.get(circuit_key, "closed")
        
        if state == "open":
            # Check if recovery timeout has passed
            last_failure = self.last_failure_time.get(circuit_key)
            if last_failure and datetime.now() - last_failure > timedelta(seconds=self.recovery_timeout):
                self.state[circuit_key] = "half-open"
                return False
            return True
        
        return False
    
    async def execute(
        self,
        operation: Callable,
        platform: Platform,
        operation_name: str,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute operation with circuit breaker protection.
        
        Args:
            operation: The async function to execute
            platform: Platform where operation is being performed
            operation_name: Name of the operation
            *args, **kwargs: Arguments to pass to the operation
            
        Returns:
            Result of the operation
            
        Raises:
            Exception: If circuit is open or operation fails
        """
        circuit_key = self._get_circuit_key(platform, operation_name)
        
        # Check if circuit is open
        if self._is_circuit_open(circuit_key):
            raise PlatformIntegrationError(
                f"Circuit breaker is open for {platform.value} {operation_name}",
                platform,
                "CIRCUIT_BREAKER_OPEN"
            )
        
        try:
            result = await operation(*args, **kwargs)
            
            # Reset failure count on success
            self.failure_count[circuit_key] = 0
            if self.state.get(circuit_key) == "half-open":
                self.state[circuit_key] = "closed"
            
            return result
            
        except Exception as e:
            # Increment failure count
            self.failure_count[circuit_key] = self.failure_count.get(circuit_key, 0) + 1
            self.last_failure_time[circuit_key] = datetime.now()
            
            # Open circuit if threshold is reached
            if self.failure_count[circuit_key] >= self.failure_threshold:
                self.state[circuit_key] = "open"
                logger.warning(
                    f"Circuit breaker opened for {platform.value} {operation_name} "
                    f"after {self.failure_count[circuit_key]} failures"
                )
            
            raise e
    
    def get_circuit_state(self, platform: Platform, operation: str) -> Dict[str, Any]:
        """Get current circuit breaker state."""
        circuit_key = self._get_circuit_key(platform, operation)
        return {
            "state": self.state.get(circuit_key, "closed"),
            "failure_count": self.failure_count.get(circuit_key, 0),
            "last_failure_time": self.last_failure_time.get(circuit_key),
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout
        }


def with_error_handling(
    platform: Platform,
    operation_name: str,
    retry_manager: Optional[RetryManager] = None,
    circuit_breaker: Optional[CircuitBreaker] = None
):
    """
    Decorator for adding error handling and retry logic to browser automation methods.
    
    Args:
        platform: Platform where operation is being performed
        operation_name: Name of the operation
        retry_manager: RetryManager instance (optional)
        circuit_breaker: CircuitBreaker instance (optional)
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user_id from args/kwargs if available
            user_id = kwargs.get('user_id', 'default')
            if not user_id and args and hasattr(args[0], 'user_id'):
                user_id = getattr(args[0], 'user_id', 'default')
            
            # Use provided managers or create default ones
            rm = retry_manager or RetryManager()
            cb = circuit_breaker or CircuitBreaker()
            
            # Execute with circuit breaker and retry logic
            async def execute_operation():
                return await cb.execute(func, platform, operation_name, *args, **kwargs)
            
            return await rm.execute_with_retry(
                execute_operation,
                platform,
                operation_name,
                user_id,
                context={"function": func.__name__}
            )
        
        return wrapper
    return decorator


class ErrorReporter:
    """Reports and tracks errors for monitoring and alerting."""
    
    def __init__(self):
        self.error_stats: Dict[str, Dict[str, int]] = {}
        self.recent_errors: List[ErrorInfo] = []
        self.max_recent_errors = 100
    
    def report_error(self, error_info: ErrorInfo):
        """Report an error for tracking and monitoring."""
        # Update statistics
        platform_key = error_info.platform.value
        error_type_key = error_info.error_type.value
        
        if platform_key not in self.error_stats:
            self.error_stats[platform_key] = {}
        
        if error_type_key not in self.error_stats[platform_key]:
            self.error_stats[platform_key][error_type_key] = 0
        
        self.error_stats[platform_key][error_type_key] += 1
        
        # Add to recent errors
        self.recent_errors.append(error_info)
        if len(self.recent_errors) > self.max_recent_errors:
            self.recent_errors.pop(0)
        
        # Log error based on severity
        if error_info.severity == ErrorSeverity.CRITICAL:
            logger.critical(f"CRITICAL ERROR on {error_info.platform.value}: {error_info.message}")
        elif error_info.severity == ErrorSeverity.HIGH:
            logger.error(f"HIGH SEVERITY ERROR on {error_info.platform.value}: {error_info.message}")
        elif error_info.severity == ErrorSeverity.MEDIUM:
            logger.warning(f"MEDIUM SEVERITY ERROR on {error_info.platform.value}: {error_info.message}")
        else:
            logger.info(f"LOW SEVERITY ERROR on {error_info.platform.value}: {error_info.message}")
    
    def get_error_stats(self) -> Dict[str, Dict[str, int]]:
        """Get error statistics by platform and error type."""
        return self.error_stats.copy()
    
    def get_recent_errors(self, limit: int = 50) -> List[ErrorInfo]:
        """Get recent errors."""
        return self.recent_errors[-limit:]
    
    def get_platform_health(self, platform: Platform) -> Dict[str, Any]:
        """Get health metrics for a specific platform."""
        platform_key = platform.value
        platform_stats = self.error_stats.get(platform_key, {})
        
        total_errors = sum(platform_stats.values())
        recent_platform_errors = [
            error for error in self.recent_errors[-50:]
            if error.platform == platform
        ]
        
        return {
            "platform": platform_key,
            "total_errors": total_errors,
            "recent_errors": len(recent_platform_errors),
            "error_types": platform_stats,
            "health_score": max(0, 100 - (total_errors * 2))  # Simple health score
        }


# Global instances
_retry_manager = RetryManager()
_circuit_breaker = CircuitBreaker()
_error_reporter = ErrorReporter()


def get_retry_manager() -> RetryManager:
    """Get the global retry manager instance."""
    return _retry_manager


def get_circuit_breaker() -> CircuitBreaker:
    """Get the global circuit breaker instance."""
    return _circuit_breaker


def get_error_reporter() -> ErrorReporter:
    """Get the global error reporter instance."""
    return _error_reporter