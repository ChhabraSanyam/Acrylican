"""
Browser Automation Service for Non-API Platforms

This module provides browser automation capabilities for platforms that don't
offer public APIs, using Playwright for secure session management and posting.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import tempfile
import os
from contextlib import asynccontextmanager

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright
from cryptography.fernet import Fernet
from pydantic import BaseModel, Field

from .platform_integration import (
    Platform,
    PostContent,
    PostResult,
    PostStatus,
    PlatformCredentials,
    AuthenticationMethod,
    AuthenticationError,
    PostingError
)

logger = logging.getLogger(__name__)


class BrowserSession(BaseModel):
    """Browser session data for a platform."""
    platform: Platform
    user_id: str
    session_data: Dict[str, Any] = Field(default_factory=dict)
    cookies: List[Dict[str, Any]] = Field(default_factory=list)
    local_storage: Dict[str, str] = Field(default_factory=dict)
    session_storage: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    last_used_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    is_active: bool = True


class BrowserCredentials(PlatformCredentials):
    """Credentials for browser automation platforms."""
    username: str
    password: str
    additional_data: Dict[str, Any] = Field(default_factory=dict)
    
    def __init__(self, username: str, password: str, platform: Platform = None, **kwargs):
        # Set default values for required parent fields
        super().__init__(
            platform=platform or Platform.MEESHO,  # Default platform
            auth_method=AuthenticationMethod.CREDENTIALS,
            username=username,
            password=password,
            **kwargs
        )


class BrowserAutomationConfig:
    """Configuration for browser automation."""
    
    # Browser settings
    HEADLESS = True
    TIMEOUT = 30000  # 30 seconds
    VIEWPORT = {"width": 1920, "height": 1080}
    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    
    # Session settings
    SESSION_TIMEOUT_HOURS = 24
    MAX_RETRY_ATTEMPTS = 3
    RETRY_DELAY_SECONDS = 2
    
    # Security settings
    DISABLE_IMAGES = True  # For faster loading
    DISABLE_JAVASCRIPT_DIALOGS = True
    BLOCK_RESOURCES = ["font", "stylesheet"]  # Block non-essential resources


class PlatformAutomator:
    """Base class for platform-specific browser automation."""
    
    def __init__(self, platform: Platform, config: BrowserAutomationConfig):
        self.platform = platform
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{platform.value}")
    
    async def login(self, page: Page, credentials: BrowserCredentials) -> bool:
        """Login to the platform. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement login method")
    
    async def post_content(self, page: Page, content: PostContent) -> PostResult:
        """Post content to the platform. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement post_content method")
    
    async def validate_session(self, page: Page) -> bool:
        """Validate that the session is still active."""
        try:
            # Default implementation: check if we're still logged in
            # by looking for common logout indicators
            logout_selectors = [
                'a[href*="logout"]',
                'button[data-testid="logout"]',
                '.logout-button',
                '[data-action="logout"]'
            ]
            
            for selector in logout_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=5000)
                    if element:
                        return True  # Found logout button, we're logged in
                except:
                    continue
            
            # If no logout button found, check for login form
            login_selectors = [
                'input[type="password"]',
                'form[action*="login"]',
                '.login-form',
                '[data-testid="login"]'
            ]
            
            for selector in login_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=5000)
                    if element:
                        return False  # Found login form, we're not logged in
                except:
                    continue
            
            return True  # Assume logged in if no clear indicators
            
        except Exception as e:
            self.logger.error(f"Session validation failed: {e}")
            return False


class MeeshoAutomator(PlatformAutomator):
    """Meesho platform automation."""
    
    def __init__(self, config: BrowserAutomationConfig):
        super().__init__(Platform.MEESHO, config)
        self.base_url = "https://supplier.meesho.com"
    
    async def login(self, page: Page, credentials: BrowserCredentials) -> bool:
        """Login to Meesho supplier dashboard."""
        try:
            # Navigate to login page
            await page.goto(f"{self.base_url}/login")
            await page.wait_for_load_state("networkidle")
            
            # Fill login form
            await page.fill('input[type="email"], input[name="email"]', credentials.username)
            await page.fill('input[type="password"], input[name="password"]', credentials.password)
            
            # Submit form
            await page.click('button[type="submit"], .login-button')
            
            # Wait for navigation or dashboard
            await page.wait_for_load_state("networkidle")
            
            # Check if login was successful
            if "dashboard" in page.url.lower() or "supplier" in page.url.lower():
                self.logger.info("Successfully logged into Meesho")
                return True
            
            # Check for error messages
            error_selectors = ['.error-message', '.alert-danger', '[data-testid="error"]']
            for selector in error_selectors:
                try:
                    error = await page.wait_for_selector(selector, timeout=3000)
                    if error:
                        error_text = await error.text_content()
                        self.logger.error(f"Meesho login error: {error_text}")
                        return False
                except:
                    continue
            
            return False
            
        except Exception as e:
            self.logger.error(f"Meesho login failed: {e}")
            return False
    
    async def post_content(self, page: Page, content: PostContent) -> PostResult:
        """Post product to Meesho."""
        try:
            # Navigate to add product page
            await page.goto(f"{self.base_url}/products/add")
            await page.wait_for_load_state("networkidle")
            
            # Fill product details
            await page.fill('input[name="title"], [data-testid="product-title"]', content.title)
            await page.fill('textarea[name="description"], [data-testid="product-description"]', content.description)
            
            # Upload images
            if content.images:
                file_input = await page.wait_for_selector('input[type="file"]')
                # Note: In real implementation, you'd need to download images locally first
                # await file_input.set_input_files(image_paths)
            
            # Set price if available
            if content.product_data and content.product_data.get("price"):
                price_input = await page.wait_for_selector('input[name="price"], [data-testid="price"]')
                await price_input.fill(str(content.product_data["price"]))
            
            # Submit the form
            submit_button = await page.wait_for_selector('button[type="submit"], .submit-button')
            await submit_button.click()
            
            # Wait for success confirmation
            await page.wait_for_load_state("networkidle")
            
            # Check for success indicators
            success_selectors = ['.success-message', '.alert-success', '[data-testid="success"]']
            for selector in success_selectors:
                try:
                    success = await page.wait_for_selector(selector, timeout=10000)
                    if success:
                        self.logger.info("Successfully posted to Meesho")
                        return PostResult(
                            platform=self.platform,
                            status=PostStatus.SUCCESS,
                            post_id=f"meesho_{datetime.now().timestamp()}",
                            posted_at=datetime.now()
                        )
                except:
                    continue
            
            return PostResult(
                platform=self.platform,
                status=PostStatus.FAILED,
                error_message="Could not confirm successful posting",
                error_code="CONFIRMATION_FAILED"
            )
            
        except Exception as e:
            self.logger.error(f"Meesho posting failed: {e}")
            return PostResult(
                platform=self.platform,
                status=PostStatus.FAILED,
                error_message=str(e),
                error_code="POSTING_ERROR"
            )


class SnapdealAutomator(PlatformAutomator):
    """Snapdeal platform automation."""
    
    def __init__(self, config: BrowserAutomationConfig):
        super().__init__(Platform.SNAPDEAL, config)
        self.base_url = "https://seller.snapdeal.com"
    
    async def login(self, page: Page, credentials: BrowserCredentials) -> bool:
        """Login to Snapdeal seller panel."""
        try:
            await page.goto(f"{self.base_url}/login")
            await page.wait_for_load_state("networkidle")
            
            # Fill login credentials
            await page.fill('input[name="username"], input[type="email"]', credentials.username)
            await page.fill('input[name="password"], input[type="password"]', credentials.password)
            
            # Submit login
            await page.click('button[type="submit"], .login-btn')
            await page.wait_for_load_state("networkidle")
            
            # Verify login success
            if "dashboard" in page.url.lower() or "seller" in page.url.lower():
                self.logger.info("Successfully logged into Snapdeal")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Snapdeal login failed: {e}")
            return False
    
    async def post_content(self, page: Page, content: PostContent) -> PostResult:
        """Post product to Snapdeal."""
        try:
            # Navigate to product listing page
            await page.goto(f"{self.base_url}/products/add")
            await page.wait_for_load_state("networkidle")
            
            # Fill product information
            await page.fill('[name="productName"]', content.title)
            await page.fill('[name="description"]', content.description)
            
            # Handle category selection (simplified)
            if content.product_data and content.product_data.get("category"):
                category_dropdown = await page.wait_for_selector('.category-dropdown')
                await category_dropdown.click()
                await page.click(f'text="{content.product_data["category"]}"')
            
            # Submit product
            await page.click('.submit-product')
            await page.wait_for_load_state("networkidle")
            
            # Check for success
            success_indicator = await page.wait_for_selector('.success-message', timeout=10000)
            if success_indicator:
                return PostResult(
                    platform=self.platform,
                    status=PostStatus.SUCCESS,
                    post_id=f"snapdeal_{datetime.now().timestamp()}",
                    posted_at=datetime.now()
                )
            
            return PostResult(
                platform=self.platform,
                status=PostStatus.FAILED,
                error_message="Posting confirmation not received",
                error_code="NO_CONFIRMATION"
            )
            
        except Exception as e:
            self.logger.error(f"Snapdeal posting failed: {e}")
            return PostResult(
                platform=self.platform,
                status=PostStatus.FAILED,
                error_message=str(e),
                error_code="POSTING_ERROR"
            )


class IndiaMARTAutomator(PlatformAutomator):
    """IndiaMART platform automation."""
    
    def __init__(self, config: BrowserAutomationConfig):
        super().__init__(Platform.INDIAMART, config)
        self.base_url = "https://my.indiamart.com"
    
    async def login(self, page: Page, credentials: BrowserCredentials) -> bool:
        """Login to IndiaMART seller account."""
        try:
            await page.goto(f"{self.base_url}/login")
            await page.wait_for_load_state("networkidle")
            
            # Fill credentials
            await page.fill('input[name="email"], input[type="email"]', credentials.username)
            await page.fill('input[name="password"], input[type="password"]', credentials.password)
            
            # Submit
            await page.click('input[type="submit"], .login-button, button:has-text("Login")')
            await page.wait_for_load_state("networkidle")
            
            # Check login success
            if "my-indiamart" in page.url.lower() or "dashboard" in page.url.lower():
                self.logger.info("Successfully logged into IndiaMART")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"IndiaMART login failed: {e}")
            return False
    
    async def post_content(self, page: Page, content: PostContent) -> PostResult:
        """Post product to IndiaMART."""
        try:
            # Navigate to add product
            await page.goto(f"{self.base_url}/products/add")
            await page.wait_for_load_state("networkidle")
            
            # Fill product details
            await page.fill('input[name="product_name"], input[name="title"]', content.title)
            await page.fill('textarea[name="product_description"], textarea[name="description"]', content.description)
            
            # Set price if available
            if content.product_data and content.product_data.get("price"):
                await page.fill('input[name="price"], input[name="unit_price"]', str(content.product_data["price"]))
            
            # Set minimum order if available
            if content.product_data and content.product_data.get("minimum_order"):
                await page.fill('input[name="minimum_order"]', str(content.product_data["minimum_order"]))
            
            # Submit
            await page.click('input[type="submit"], .add-product-btn, button:has-text("Add Product")')
            await page.wait_for_load_state("networkidle")
            
            # Verify success
            success_selectors = ['.success-msg', '.alert-success', '.product-added']
            for selector in success_selectors:
                try:
                    if await page.wait_for_selector(selector, timeout=10000):
                        return PostResult(
                            platform=self.platform,
                            status=PostStatus.SUCCESS,
                            post_id=f"indiamart_{datetime.now().timestamp()}",
                            published_at=datetime.now()
                        )
                except:
                    continue
            
            return PostResult(
                platform=self.platform,
                status=PostStatus.FAILED,
                error_message="Could not verify successful posting",
                error_code="VERIFICATION_FAILED"
            )
            
        except Exception as e:
            self.logger.error(f"IndiaMART posting failed: {e}")
            return PostResult(
                platform=self.platform,
                status=PostStatus.FAILED,
                error_message=str(e),
                error_code="POSTING_ERROR"
            )


class BrowserAutomationService:
    """Main service for browser automation across platforms."""
    
    def __init__(self, config: Optional[BrowserAutomationConfig] = None):
        self.config = config or BrowserAutomationConfig()
        self.sessions: Dict[str, BrowserSession] = {}
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.logger = logging.getLogger(__name__)
        
        # Initialize platform automators
        self.automators = {
            Platform.MEESHO: MeeshoAutomator(self.config),
            Platform.SNAPDEAL: SnapdealAutomator(self.config),
            Platform.INDIAMART: IndiaMARTAutomator(self.config),
        }
        
        # Encryption for session data
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher = Fernet(self.encryption_key)
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for session data."""
        key_file = Path(tempfile.gettempdir()) / "browser_automation_key"
        
        if key_file.exists():
            return key_file.read_bytes()
        
        key = Fernet.generate_key()
        key_file.write_bytes(key)
        return key
    
    def _encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data."""
        return self.cipher.encrypt(data.encode()).decode()
    
    def _decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        return self.cipher.decrypt(encrypted_data.encode()).decode()
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
    
    async def start(self):
        """Start the browser automation service."""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=self.config.HEADLESS,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-extensions',
                    '--disable-plugins',
                    '--disable-images' if self.config.DISABLE_IMAGES else '',
                ]
            )
            self.logger.info("Browser automation service started")
        except Exception as e:
            self.logger.error(f"Failed to start browser automation service: {e}")
            raise
    
    async def stop(self):
        """Stop the browser automation service."""
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            self.logger.info("Browser automation service stopped")
        except Exception as e:
            self.logger.error(f"Error stopping browser automation service: {e}")
    
    def _get_session_key(self, platform: Platform, user_id: str) -> str:
        """Generate session key for a platform and user."""
        return f"{platform.value}_{user_id}"
    
    async def _create_browser_context(self, session: Optional[BrowserSession] = None) -> BrowserContext:
        """Create a new browser context with optional session data."""
        context = await self.browser.new_context(
            viewport=self.config.VIEWPORT,
            user_agent=self.config.USER_AGENT,
        )
        
        # Restore session data if available
        if session and session.cookies:
            await context.add_cookies(session.cookies)
        
        # Block unnecessary resources for faster loading
        if self.config.BLOCK_RESOURCES:
            await context.route("**/*", lambda route: (
                route.abort() if route.request.resource_type in self.config.BLOCK_RESOURCES
                else route.continue_()
            ))
        
        return context
    
    async def authenticate_platform(
        self,
        platform: Platform,
        user_id: str,
        credentials: BrowserCredentials
    ) -> bool:
        """Authenticate with a platform using browser automation."""
        if platform not in self.automators:
            raise AuthenticationError(f"Platform {platform.value} not supported for browser automation", platform)
        
        session_key = self._get_session_key(platform, user_id)
        automator = self.automators[platform]
        
        try:
            context = await self._create_browser_context()
            page = await context.new_page()
            
            # Set page timeout
            page.set_default_timeout(self.config.TIMEOUT)
            
            # Attempt login
            success = await automator.login(page, credentials)
            
            if success:
                # Save session data
                cookies = await context.cookies()
                
                session = BrowserSession(
                    platform=platform,
                    user_id=user_id,
                    cookies=cookies,
                    expires_at=datetime.now() + timedelta(hours=self.config.SESSION_TIMEOUT_HOURS)
                )
                
                self.sessions[session_key] = session
                self.logger.info(f"Successfully authenticated {user_id} with {platform.value}")
            
            await context.close()
            return success
            
        except Exception as e:
            self.logger.error(f"Authentication failed for {platform.value}: {e}")
            raise AuthenticationError(f"Failed to authenticate with {platform.value}: {str(e)}", platform)
    
    async def validate_session(self, platform: Platform, user_id: str) -> bool:
        """Validate that a session is still active."""
        session_key = self._get_session_key(platform, user_id)
        session = self.sessions.get(session_key)
        
        if not session or not session.is_active:
            return False
        
        # Check if session has expired
        if session.expires_at and datetime.now() > session.expires_at:
            session.is_active = False
            return False
        
        # Validate with the platform
        if platform not in self.automators:
            return False
        
        try:
            context = await self._create_browser_context(session)
            page = await context.new_page()
            
            automator = self.automators[platform]
            is_valid = await automator.validate_session(page)
            
            if not is_valid:
                session.is_active = False
            else:
                session.last_used_at = datetime.now()
            
            await context.close()
            return is_valid
            
        except Exception as e:
            self.logger.error(f"Session validation failed for {platform.value}: {e}")
            session.is_active = False
            return False
    
    async def post_content(
        self,
        platform: Platform,
        user_id: str,
        content: PostContent
    ) -> PostResult:
        """Post content to a platform using browser automation."""
        if platform not in self.automators:
            return PostResult(
                platform=platform,
                status=PostStatus.FAILED,
                error_message=f"Platform {platform.value} not supported for browser automation",
                error_code="PLATFORM_NOT_SUPPORTED"
            )
        
        session_key = self._get_session_key(platform, user_id)
        session = self.sessions.get(session_key)
        
        if not session or not session.is_active:
            return PostResult(
                platform=platform,
                status=PostStatus.FAILED,
                error_message="No active session found. Please authenticate first.",
                error_code="NO_ACTIVE_SESSION"
            )
        
        # Validate session before posting
        if not await self.validate_session(platform, user_id):
            return PostResult(
                platform=platform,
                status=PostStatus.FAILED,
                error_message="Session validation failed. Please re-authenticate.",
                error_code="SESSION_INVALID"
            )
        
        automator = self.automators[platform]
        
        try:
            context = await self._create_browser_context(session)
            page = await context.new_page()
            page.set_default_timeout(self.config.TIMEOUT)
            
            # Post content
            result = await automator.post_content(page, content)
            
            # Update session last used time
            session.last_used_at = datetime.now()
            
            await context.close()
            return result
            
        except Exception as e:
            self.logger.error(f"Posting failed for {platform.value}: {e}")
            return PostResult(
                platform=platform,
                status=PostStatus.FAILED,
                error_message=str(e),
                error_code="POSTING_ERROR"
            )
    
    async def disconnect_platform(self, platform: Platform, user_id: str) -> bool:
        """Disconnect from a platform by removing session data."""
        session_key = self._get_session_key(platform, user_id)
        
        if session_key in self.sessions:
            del self.sessions[session_key]
            self.logger.info(f"Disconnected {user_id} from {platform.value}")
            return True
        
        return False
    
    def get_supported_platforms(self) -> List[Platform]:
        """Get list of platforms supported by browser automation."""
        return list(self.automators.keys())
    
    def is_platform_supported(self, platform: Platform) -> bool:
        """Check if a platform is supported by browser automation."""
        return platform in self.automators
    
    async def cleanup_expired_sessions(self):
        """Clean up expired sessions."""
        current_time = datetime.now()
        expired_keys = []
        
        for key, session in self.sessions.items():
            if session.expires_at and current_time > session.expires_at:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.sessions[key]
        
        if expired_keys:
            self.logger.info(f"Cleaned up {len(expired_keys)} expired sessions")


# Global service instance
_browser_automation_service: Optional[BrowserAutomationService] = None


async def get_browser_automation_service() -> BrowserAutomationService:
    """Get the global browser automation service instance."""
    global _browser_automation_service
    
    if _browser_automation_service is None:
        _browser_automation_service = BrowserAutomationService()
        await _browser_automation_service.start()
    
    return _browser_automation_service


async def cleanup_browser_automation_service():
    """Cleanup the global browser automation service."""
    global _browser_automation_service
    
    if _browser_automation_service:
        await _browser_automation_service.stop()
        _browser_automation_service = None