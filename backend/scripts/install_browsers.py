#!/usr/bin/env python3
"""
Browser Installation Script

This script installs Playwright browsers required for browser automation.
It should be run during deployment or development setup.
"""

import asyncio
import subprocess
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_command(command: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command and return the result."""
    logger.info(f"Running command: {command}")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=check,
            capture_output=True,
            text=True
        )
        
        if result.stdout:
            logger.info(f"STDOUT: {result.stdout}")
        
        if result.stderr:
            logger.warning(f"STDERR: {result.stderr}")
        
        return result
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with exit code {e.returncode}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        raise


def check_playwright_installed() -> bool:
    """Check if Playwright is installed."""
    try:
        result = run_command("python -c 'import playwright; print(playwright.__version__)'", check=False)
        if result.returncode == 0:
            logger.info(f"Playwright is installed: {result.stdout.strip()}")
            return True
        else:
            logger.info("Playwright is not installed")
            return False
    except Exception as e:
        logger.error(f"Error checking Playwright installation: {e}")
        return False


def install_playwright_browsers():
    """Install Playwright browsers."""
    logger.info("Installing Playwright browsers...")
    
    try:
        # Install browsers
        run_command("playwright install chromium")
        
        # Install system dependencies (Linux only)
        if sys.platform.startswith('linux'):
            logger.info("Installing system dependencies for Linux...")
            run_command("playwright install-deps chromium")
        
        logger.info("Playwright browsers installed successfully")
        
    except subprocess.CalledProcessError as e:
        logger.error("Failed to install Playwright browsers")
        raise


def verify_browser_installation():
    """Verify that browsers are properly installed."""
    logger.info("Verifying browser installation...")
    
    try:
        # Test browser launch
        test_script = """
import asyncio
from playwright.async_api import async_playwright

async def test_browser():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('https://example.com')
        title = await page.title()
        print(f'Page title: {title}')
        await browser.close()
        return True

if __name__ == '__main__':
    result = asyncio.run(test_browser())
    print('Browser test successful' if result else 'Browser test failed')
"""
        
        # Write test script to temporary file
        test_file = Path("/tmp/test_browser.py")
        test_file.write_text(test_script)
        
        # Run test
        result = run_command(f"python {test_file}")
        
        # Clean up
        test_file.unlink()
        
        logger.info("Browser verification successful")
        
    except Exception as e:
        logger.error(f"Browser verification failed: {e}")
        raise


def setup_browser_environment():
    """Set up browser environment variables and directories."""
    logger.info("Setting up browser environment...")
    
    # Create directories for screenshots and downloads
    directories = [
        "/tmp/browser_screenshots",
        "/tmp/browser_downloads"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {directory}")
    
    # Set environment variables for headless operation
    import os
    os.environ.setdefault("DISPLAY", ":99")  # For headless operation
    
    logger.info("Browser environment setup complete")


def main():
    """Main installation function."""
    logger.info("Starting browser automation setup...")
    
    try:
        # Check if Playwright is installed
        if not check_playwright_installed():
            logger.error("Playwright is not installed. Please install it first with: pip install playwright")
            sys.exit(1)
        
        # Install browsers
        install_playwright_browsers()
        
        # Set up environment
        setup_browser_environment()
        
        # Verify installation
        verify_browser_installation()
        
        logger.info("Browser automation setup completed successfully!")
        
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()