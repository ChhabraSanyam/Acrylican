"""
Test utilities and helper functions for the Artisan Promotion Platform test suite.

This module provides common utilities, fixtures, and helper functions
used across different test modules.
"""

import pytest
import asyncio
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta
from decimal import Decimal
import json
import io
from PIL import Image
import random
import string

from app.models import User, Product, Post, SaleEvent, PlatformConnection
from app.schemas import UserCreate, ProductCreate


class TestDataFactory:
    """Factory class for generating test data."""
    
    @staticmethod
    def create_user_data(**kwargs) -> Dict[str, Any]:
        """Create test user data."""
        defaults = {
            "email": f"test_{random.randint(1000, 9999)}@example.com",
            "password": "SecureTestPass123!",
            "business_name": "Test Artisan Business",
            "business_type": "Handmade Crafts",
            "business_description": "A test business for artisan crafts",
            "website": "https://testbusiness.com",
            "location": "Test City, Test Country"
        }
        defaults.update(kwargs)
        return defaults
    
    @staticmethod
    def create_product_data(**kwargs) -> Dict[str, Any]:
        """Create test product data."""
        defaults = {
            "title": f"Test Product {random.randint(1000, 9999)}",
            "description": "A beautiful handcrafted test product made with care and attention to detail.",
            "category": "Test Category",
            "price": f"{random.uniform(10.0, 100.0):.2f}",
            "materials": ["test_material_1", "test_material_2"],
            "dimensions": "10x10x5 cm",
            "weight": "200g",
            "colors": ["blue", "red"],
            "tags": ["handmade", "test", "artisan"]
        }
        defaults.update(kwargs)
        return defaults
    
    @staticmethod
    def create_post_data(**kwargs) -> Dict[str, Any]:
        """Create test post data."""
        defaults = {
            "product_id": f"product-{random.randint(1000, 9999)}",
            "platforms": ["facebook", "instagram"],
            "content": {
                "title": "Test Post Title",
                "description": "This is a test post description with relevant details.",
                "hashtags": ["#test", "#handmade", "#artisan"]
            },
            "images": [f"https://example.com/image{random.randint(1, 100)}.jpg"],
            "scheduled_at": datetime.utcnow() + timedelta(hours=2)
        }
        defaults.update(kwargs)
        return defaults
    
    @staticmethod
    def create_sale_event_data(**kwargs) -> Dict[str, Any]:
        """Create test sale event data."""
        defaults = {
            "product_id": f"product-{random.randint(1000, 9999)}",
            "platform": random.choice(["facebook", "instagram", "etsy", "pinterest"]),
            "amount": f"{random.uniform(20.0, 200.0):.2f}",
            "currency": "USD",
            "order_id": f"order_{random.randint(10000, 99999)}",
            "customer_info": {
                "source": "organic",
                "location": "Test City"
            }
        }
        defaults.update(kwargs)
        return defaults
    
    @staticmethod
    def create_platform_connection_data(**kwargs) -> Dict[str, Any]:
        """Create test platform connection data."""
        defaults = {
            "platform": random.choice(["facebook", "instagram", "etsy", "pinterest"]),
            "access_token": f"test_token_{random.randint(1000, 9999)}",
            "refresh_token": f"refresh_token_{random.randint(1000, 9999)}",
            "expires_at": datetime.utcnow() + timedelta(days=60),
            "is_active": True,
            "user_info": {
                "id": f"platform_user_{random.randint(1000, 9999)}",
                "name": "Test Platform User"
            }
        }
        defaults.update(kwargs)
        return defaults


class MockFactory:
    """Factory class for creating mock objects."""
    
    @staticmethod
    def create_gemini_mock(response_text: str = None):
        """Create a mock for Google Gemini API."""
        if response_text is None:
            response_text = """
            Title: Beautiful Handcrafted Test Product
            
            Description: Experience the artistry of handcrafted excellence with this unique test product. Each piece is lovingly created by skilled artisans using traditional techniques.
            
            Hashtags: #handmade #test #artisan #unique #crafted #beautiful #quality #traditional
            """
        
        mock_response = Mock()
        mock_response.text = response_text
        
        mock_model = Mock()
        mock_model.generate_content = AsyncMock(return_value=mock_response)
        
        mock_genai = Mock()
        mock_genai.GenerativeModel.return_value = mock_model
        
        return mock_genai
    
    @staticmethod
    def create_storage_mock():
        """Create a mock for storage service."""
        mock_storage = Mock()
        mock_storage.upload_image = AsyncMock(return_value=Mock(
            file_id=f"test-file-{random.randint(1000, 9999)}",
            url=f"https://storage.example.com/test-image-{random.randint(1000, 9999)}.jpg",
            size=random.randint(100000, 1000000),
            content_type="image/jpeg"
        ))
        mock_storage.delete_image = AsyncMock(return_value=True)
        mock_storage.get_image_url = Mock(return_value="https://storage.example.com/test.jpg")
        return mock_storage
    
    @staticmethod
    def create_platform_service_mock():
        """Create a mock for platform service."""
        mock_service = Mock()
        mock_service.post_content = AsyncMock(return_value={
            'facebook': {'success': True, 'post_id': f'fb_{random.randint(1000, 9999)}'},
            'instagram': {'success': True, 'post_id': f'ig_{random.randint(1000, 9999)}'}
        })
        mock_service.get_metrics = AsyncMock(return_value={
            'likes': random.randint(10, 100),
            'shares': random.randint(5, 50),
            'comments': random.randint(2, 20)
        })
        return mock_service
    
    @staticmethod
    def create_oauth_service_mock():
        """Create a mock for OAuth service."""
        mock_service = Mock()
        mock_service.initiate_oauth_flow = AsyncMock(return_value={
            "authorization_url": f"https://platform.com/oauth/authorize?state={random.randint(1000, 9999)}",
            "state": f"state_{random.randint(1000, 9999)}"
        })
        mock_service.handle_oauth_callback = AsyncMock(return_value={
            "success": True,
            "access_token": f"access_token_{random.randint(1000, 9999)}",
            "user_info": {"id": f"user_{random.randint(1000, 9999)}", "name": "Test User"}
        })
        return mock_service


class ImageTestUtils:
    """Utilities for image-related testing."""
    
    @staticmethod
    def create_test_image(width: int = 800, height: int = 600, format: str = 'JPEG') -> bytes:
        """Create a test image as bytes."""
        img = Image.new('RGB', (width, height), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format=format)
        img_bytes.seek(0)
        return img_bytes.getvalue()
    
    @staticmethod
    def create_test_image_file(filename: str = "test.jpg", width: int = 800, height: int = 600):
        """Create a test image file-like object."""
        image_data = ImageTestUtils.create_test_image(width, height)
        file_obj = io.BytesIO(image_data)
        file_obj.name = filename
        return file_obj
    
    @staticmethod
    def validate_image_dimensions(image_data: bytes, expected_width: int, expected_height: int) -> bool:
        """Validate image dimensions."""
        img = Image.open(io.BytesIO(image_data))
        return img.width == expected_width and img.height == expected_height
    
    @staticmethod
    def get_image_info(image_data: bytes) -> Dict[str, Any]:
        """Get image information."""
        img = Image.open(io.BytesIO(image_data))
        return {
            'width': img.width,
            'height': img.height,
            'format': img.format,
            'mode': img.mode,
            'size': len(image_data)
        }


class DatabaseTestUtils:
    """Utilities for database testing."""
    
    @staticmethod
    def create_test_user(db_session, **kwargs) -> User:
        """Create a test user in the database."""
        user_data = TestDataFactory.create_user_data(**kwargs)
        user = User(
            email=user_data["email"],
            password_hash="hashed_password",  # In real tests, use proper hashing
            business_name=user_data["business_name"],
            business_type=user_data["business_type"],
            business_description=user_data.get("business_description"),
            website=user_data.get("website"),
            location=user_data.get("location")
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user
    
    @staticmethod
    def create_test_product(db_session, user_id: str, **kwargs) -> Product:
        """Create a test product in the database."""
        product_data = TestDataFactory.create_product_data(**kwargs)
        product = Product(
            user_id=user_id,
            title=product_data["title"],
            description=product_data["description"],
            category=product_data.get("category"),
            price=product_data.get("price"),
            materials=product_data.get("materials"),
            dimensions=product_data.get("dimensions"),
            weight=product_data.get("weight"),
            colors=product_data.get("colors"),
            tags=product_data.get("tags")
        )
        db_session.add(product)
        db_session.commit()
        db_session.refresh(product)
        return product
    
    @staticmethod
    def create_test_post(db_session, user_id: str, product_id: str, **kwargs) -> Post:
        """Create a test post in the database."""
        post_data = TestDataFactory.create_post_data(product_id=product_id, **kwargs)
        post = Post(
            user_id=user_id,
            product_id=product_id,
            platforms=post_data["platforms"],
            content=post_data["content"],
            images=post_data["images"],
            status="draft",
            scheduled_at=post_data.get("scheduled_at")
        )
        db_session.add(post)
        db_session.commit()
        db_session.refresh(post)
        return post
    
    @staticmethod
    def create_test_sale_event(db_session, user_id: str, **kwargs) -> SaleEvent:
        """Create a test sale event in the database."""
        sale_data = TestDataFactory.create_sale_event_data(**kwargs)
        sale = SaleEvent(
            user_id=user_id,
            product_id=sale_data.get("product_id"),
            platform=sale_data["platform"],
            amount=Decimal(sale_data["amount"]),
            currency=sale_data["currency"],
            order_id=sale_data["order_id"],
            occurred_at=datetime.utcnow()
        )
        db_session.add(sale)
        db_session.commit()
        db_session.refresh(sale)
        return sale


class AssertionHelpers:
    """Helper functions for common test assertions."""
    
    @staticmethod
    def assert_valid_uuid(value: str):
        """Assert that a value is a valid UUID."""
        import uuid
        try:
            uuid.UUID(value)
        except ValueError:
            pytest.fail(f"'{value}' is not a valid UUID")
    
    @staticmethod
    def assert_valid_email(email: str):
        """Assert that a value is a valid email."""
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            pytest.fail(f"'{email}' is not a valid email address")
    
    @staticmethod
    def assert_valid_url(url: str):
        """Assert that a value is a valid URL."""
        import re
        url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        if not re.match(url_pattern, url):
            pytest.fail(f"'{url}' is not a valid URL")
    
    @staticmethod
    def assert_datetime_recent(dt: datetime, max_age_seconds: int = 60):
        """Assert that a datetime is recent (within max_age_seconds)."""
        now = datetime.utcnow()
        age = (now - dt).total_seconds()
        if age > max_age_seconds:
            pytest.fail(f"Datetime {dt} is too old (age: {age} seconds)")
    
    @staticmethod
    def assert_dict_contains(actual: Dict, expected: Dict):
        """Assert that actual dict contains all key-value pairs from expected dict."""
        for key, value in expected.items():
            if key not in actual:
                pytest.fail(f"Key '{key}' not found in actual dict")
            if actual[key] != value:
                pytest.fail(f"Value for key '{key}' does not match. Expected: {value}, Actual: {actual[key]}")
    
    @staticmethod
    def assert_list_contains_item(items: List, predicate):
        """Assert that list contains at least one item matching the predicate."""
        if not any(predicate(item) for item in items):
            pytest.fail("No item in list matches the predicate")


class PerformanceTestUtils:
    """Utilities for performance testing."""
    
    @staticmethod
    def measure_execution_time(func, *args, **kwargs):
        """Measure execution time of a function."""
        import time
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        return result, execution_time
    
    @staticmethod
    async def measure_async_execution_time(func, *args, **kwargs):
        """Measure execution time of an async function."""
        import time
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        return result, execution_time
    
    @staticmethod
    def assert_execution_time_under(execution_time: float, max_time: float):
        """Assert that execution time is under the maximum allowed time."""
        if execution_time > max_time:
            pytest.fail(f"Execution time {execution_time:.3f}s exceeds maximum {max_time:.3f}s")
    
    @staticmethod
    def generate_large_dataset(size: int) -> List[Dict]:
        """Generate a large dataset for performance testing."""
        return [TestDataFactory.create_sale_event_data() for _ in range(size)]


class SecurityTestUtils:
    """Utilities for security testing."""
    
    @staticmethod
    def generate_sql_injection_payloads() -> List[str]:
        """Generate common SQL injection payloads."""
        return [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM users --",
            "'; INSERT INTO users (email) VALUES ('hacker@evil.com'); --",
            "' OR 1=1 --"
        ]
    
    @staticmethod
    def generate_xss_payloads() -> List[str]:
        """Generate common XSS payloads."""
        return [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>",
            "';alert('XSS');//"
        ]
    
    @staticmethod
    def generate_invalid_tokens() -> List[str]:
        """Generate invalid JWT tokens for testing."""
        return [
            "invalid.token.here",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature",
            "",
            "Bearer invalid_token",
            "malformed_token_without_dots"
        ]
    
    @staticmethod
    def assert_no_sensitive_data_in_response(response_data: Dict):
        """Assert that response doesn't contain sensitive data."""
        sensitive_fields = ['password', 'password_hash', 'access_token', 'refresh_token', 'secret']
        
        def check_dict(data, path=""):
            if isinstance(data, dict):
                for key, value in data.items():
                    current_path = f"{path}.{key}" if path else key
                    if key.lower() in sensitive_fields:
                        pytest.fail(f"Sensitive field '{current_path}' found in response")
                    check_dict(value, current_path)
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    check_dict(item, f"{path}[{i}]")
        
        check_dict(response_data)


# Pytest fixtures that can be used across test modules
@pytest.fixture
def test_data_factory():
    """Provide TestDataFactory instance."""
    return TestDataFactory()


@pytest.fixture
def mock_factory():
    """Provide MockFactory instance."""
    return MockFactory()


@pytest.fixture
def image_utils():
    """Provide ImageTestUtils instance."""
    return ImageTestUtils()


@pytest.fixture
def db_utils():
    """Provide DatabaseTestUtils instance."""
    return DatabaseTestUtils()


@pytest.fixture
def assert_helpers():
    """Provide AssertionHelpers instance."""
    return AssertionHelpers()


@pytest.fixture
def perf_utils():
    """Provide PerformanceTestUtils instance."""
    return PerformanceTestUtils()


@pytest.fixture
def security_utils():
    """Provide SecurityTestUtils instance."""
    return SecurityTestUtils()


@pytest.fixture
def sample_image():
    """Provide a sample test image."""
    return ImageTestUtils.create_test_image()


@pytest.fixture
def large_image():
    """Provide a large test image."""
    return ImageTestUtils.create_test_image(3000, 2000)


@pytest.fixture
def mock_gemini_api():
    """Provide a mocked Gemini API."""
    return MockFactory.create_gemini_mock()


@pytest.fixture
def mock_storage_service():
    """Provide a mocked storage service."""
    return MockFactory.create_storage_mock()


@pytest.fixture
def mock_platform_service():
    """Provide a mocked platform service."""
    return MockFactory.create_platform_service_mock()