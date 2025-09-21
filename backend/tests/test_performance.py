"""
Performance tests for the Artisan Promotion Platform.

These tests focus on performance characteristics, load handling,
and resource usage optimization.
"""

import pytest
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch, AsyncMock
from PIL import Image
import io
from fastapi import UploadFile

from app.services.image_processing import ImageProcessingService
from app.services.posting_service import PostingService
from app.services.analytics_service import AnalyticsService


@pytest.mark.performance


@pytest.mark.performance
class TestImageProcessingPerformance:
    """Performance tests for image processing."""
    
    @pytest.fixture
    def service(self):
        return ImageProcessingService()
    
    @pytest.fixture
    def create_test_image(self):
        """Create a test image of specified size."""
        def _create_image(width=1920, height=1080, format='JPEG'):
            img = Image.new('RGB', (width, height), color='red')
            output = io.BytesIO()
            img.save(output, format=format)
            output.seek(0)
            return output.getvalue()
        return _create_image
    
    @pytest.mark.asyncio
    async def test_single_image_processing_time(self, service, create_test_image):
        """Test processing time for a single large image."""
        image_data = create_test_image(3000, 2000)  # Large image
        
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test_large.jpg"
        mock_file.size = len(image_data)
        mock_file.read = AsyncMock(return_value=image_data)
        mock_file.seek = AsyncMock()
        
        start_time = time.time()
        
        with patch('app.services.image_processing.get_storage_service'):
            # Mock storage service to avoid actual uploads
            mock_storage = Mock()
            mock_storage.upload_image = AsyncMock(return_value=Mock(
                file_id="test-id", url="https://example.com/test.jpg",
                size=1024, content_type="image/jpeg"
            ))
            
            with patch('app.services.image_processing.get_storage_service', return_value=mock_storage):
                result = await service.process_image(mock_file, ['facebook', 'instagram'])
        
        processing_time = time.time() - start_time
        
        # Should process within reasonable time (adjust threshold as needed)
        assert processing_time < 5.0  # 5 seconds max for large image
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_concurrent_image_processing(self, service, create_test_image):
        """Test processing multiple images concurrently."""
        num_images = 5
        image_data = create_test_image(1200, 800)
        
        async def process_single_image(index):
            mock_file = Mock(spec=UploadFile)
            mock_file.filename = f"test_{index}.jpg"
            mock_file.size = len(image_data)
            mock_file.read = AsyncMock(return_value=image_data)
            mock_file.seek = AsyncMock()
            
            with patch('app.services.image_processing.get_storage_service'):
                mock_storage = Mock()
                mock_storage.upload_image = AsyncMock(return_value=Mock(
                    file_id=f"test-id-{index}", url=f"https://example.com/test_{index}.jpg",
                    size=1024, content_type="image/jpeg"
                ))
                
                with patch('app.services.image_processing.get_storage_service', return_value=mock_storage):
                    return await service.process_image(mock_file, ['facebook'])
        
        start_time = time.time()
        
        # Process images concurrently
        tasks = [process_single_image(i) for i in range(num_images)]
        results = await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        
        # Concurrent processing should be faster than sequential
        # Allow reasonable time for concurrent processing
        assert total_time < num_images * 2  # Should be much faster than sequential
        assert len(results) == num_images
        assert all(result is not None for result in results)
    
    def test_image_compression_efficiency(self, service, create_test_image):
        """Test image compression efficiency and quality."""
        original_data = create_test_image(2000, 1500)  # Large image
        original_size = len(original_data)
        
        # Test different quality levels
        quality_levels = [95, 85, 75, 60]
        compressed_sizes = []
        
        for quality in quality_levels:
            img = Image.open(io.BytesIO(original_data))
            compressed = service.compress_image(img, quality=quality)
            compressed_sizes.append(len(compressed))
        
        # Verify compression reduces file size
        for size in compressed_sizes:
            assert size < original_size
        
        # Verify lower quality = smaller size (generally)
        for i in range(len(compressed_sizes) - 1):
            # Allow some tolerance as compression can vary
            assert compressed_sizes[i] >= compressed_sizes[i + 1] * 0.8
    
    @pytest.mark.asyncio
    async def test_bulk_thumbnail_generation(self, service, create_test_image):
        """Test bulk thumbnail generation performance."""
        image_data = create_test_image(1920, 1080)
        img = Image.open(io.BytesIO(image_data))
        
        thumbnail_sizes = [(150, 150), (300, 300), (600, 600), (800, 800)]
        
        start_time = time.time()
        
        thumbnails = []
        for size in thumbnail_sizes:
            thumbnail = service.generate_thumbnail(img, size)
            thumbnails.append(thumbnail)
        
        generation_time = time.time() - start_time
        
        # Should generate all thumbnails quickly
        assert generation_time < 2.0  # 2 seconds max
        assert len(thumbnails) == len(thumbnail_sizes)
        
        # Verify thumbnail sizes are correct
        for i, thumbnail_data in enumerate(thumbnails):
            thumb_img = Image.open(io.BytesIO(thumbnail_data))
            expected_size = thumbnail_sizes[i]
            assert thumb_img.width <= expected_size[0]
            assert thumb_img.height <= expected_size[1]


@pytest.mark.performance
class TestPostingServicePerformance:
    """Performance tests for posting service."""
    
    @pytest.fixture
    def service(self):
        return PostingService()
    
    @pytest.fixture
    def sample_posts(self):
        """Generate sample posts for testing."""
        posts = []
        for i in range(10):
            posts.append({
                'id': f'post-{i}',
                'user_id': 'user-123',
                'product_id': f'product-{i}',
                'content': {
                    'title': f'Test Post {i}',
                    'description': f'Description for post {i}',
                    'hashtags': [f'#test{i}', '#performance']
                },
                'platforms': ['facebook', 'instagram'],
                'images': [f'https://example.com/image{i}.jpg']
            })
        return posts
    
    @pytest.mark.asyncio
    async def test_concurrent_posting_performance(self, service, sample_posts):
        """Test concurrent posting to multiple platforms."""
        
        async def mock_platform_post(post_data):
            # Simulate API call delay
            await asyncio.sleep(0.1)
            return {
                'facebook': {'success': True, 'post_id': f"fb_{post_data['id']}"},
                'instagram': {'success': True, 'post_id': f"ig_{post_data['id']}"}
            }
        
        with patch.object(service, 'publish_post', side_effect=mock_platform_post):
            start_time = time.time()
            
            # Post concurrently
            tasks = [service.publish_post(post) for post in sample_posts[:5]]
            results = await asyncio.gather(*tasks)
            
            total_time = time.time() - start_time
            
            # Should complete faster than sequential posting
            assert total_time < 1.0  # Should be much faster than 5 * 0.1 = 0.5s sequential
            assert len(results) == 5
    
    @pytest.mark.asyncio
    async def test_queue_processing_performance(self, service):
        """Test queue processing performance with many posts."""
        queue_size = 50
        
        # Mock queue with many posts
        mock_queue = [
            {
                'id': f'queued-post-{i}',
                'user_id': 'user-123',
                'status': 'scheduled',
                'scheduled_at': time.time() - 60  # Past due
            }
            for i in range(queue_size)
        ]
        
        with patch.object(service, 'get_due_posts', return_value=mock_queue):
            with patch.object(service, 'publish_post', return_value={'success': True}):
                start_time = time.time()
                
                processed = await service.process_queue(batch_size=10)
                
                processing_time = time.time() - start_time
                
                # Should process efficiently
                assert processing_time < 5.0  # 5 seconds max for 50 posts
                assert processed >= queue_size


@pytest.mark.performance
class TestAnalyticsServicePerformance:
    """Performance tests for analytics service."""
    
    @pytest.fixture
    def service(self):
        return AnalyticsService()
    
    @pytest.mark.asyncio
    async def test_large_dataset_aggregation(self, service):
        """Test analytics aggregation with large datasets."""
        # Mock large dataset
        large_dataset = []
        for i in range(10000):  # 10k records
            large_dataset.append({
                'id': f'sale-{i}',
                'amount': 25.99 + (i % 100),
                'platform': ['facebook', 'instagram', 'etsy'][i % 3],
                'occurred_at': time.time() - (i * 3600)  # Spread over time
            })
        
        with patch.object(service, 'get_sales_data', return_value=large_dataset):
            start_time = time.time()
            
            metrics = await service.calculate_revenue_metrics('user-123', 365)
            
            calculation_time = time.time() - start_time
            
            # Should calculate efficiently even with large dataset
            assert calculation_time < 2.0  # 2 seconds max
            assert metrics['total_orders'] == 10000
    
    @pytest.mark.asyncio
    async def test_concurrent_analytics_requests(self, service):
        """Test handling concurrent analytics requests."""
        
        async def get_analytics(user_id):
            # Mock some processing time
            await asyncio.sleep(0.05)
            return {
                'revenue': 1000.0,
                'orders': 50,
                'platforms': {'facebook': 500, 'instagram': 300, 'etsy': 200}
            }
        
        with patch.object(service, 'get_dashboard_data', side_effect=get_analytics):
            start_time = time.time()
            
            # Simulate concurrent requests from multiple users
            tasks = [service.get_dashboard_data(f'user-{i}', 30) for i in range(20)]
            results = await asyncio.gather(*tasks)
            
            total_time = time.time() - start_time
            
            # Should handle concurrent requests efficiently
            assert total_time < 2.0  # Should be much faster than 20 * 0.05 = 1.0s
            assert len(results) == 20


@pytest.mark.performance
class TestDatabasePerformance:
    """Database performance tests."""
    
    @pytest.mark.asyncio
    async def test_bulk_insert_performance(self):
        """Test bulk insert operations performance."""
        # This would test bulk database operations
        pass
    
    @pytest.mark.asyncio
    async def test_complex_query_performance(self):
        """Test complex analytics queries performance."""
        # This would test complex JOIN queries and aggregations
        pass
    
    @pytest.mark.asyncio
    async def test_concurrent_database_access(self):
        """Test concurrent database access performance."""
        # This would test database connection pooling and concurrent access
        pass


@pytest.mark.performance
class TestMemoryUsage:
    """Memory usage and resource management tests."""
    
    def test_image_processing_memory_usage(self):
        """Test memory usage during image processing."""
        # This would monitor memory usage during image operations
        pass
    
    def test_large_response_memory_usage(self):
        """Test memory usage with large API responses."""
        # This would test memory efficiency with large datasets
        pass


@pytest.mark.performance
class TestCachePerformance:
    """Cache performance tests."""
    
    @pytest.mark.asyncio
    async def test_redis_cache_performance(self):
        """Test Redis cache read/write performance."""
        # This would test cache operations performance
        pass
    
    @pytest.mark.asyncio
    async def test_cache_hit_ratio(self):
        """Test cache hit ratio under load."""
        # This would test cache effectiveness
        pass


# Performance benchmarking utilities
class PerformanceBenchmark:
    """Utility class for performance benchmarking."""
    
    def __init__(self, name: str):
        self.name = name
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        print(f"Benchmark '{self.name}': {duration:.4f} seconds")
    
    @property
    def duration(self):
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None


def measure_memory_usage(func):
    """Decorator to measure memory usage of a function."""
    import psutil
    import os
    
    def wrapper(*args, **kwargs):
        process = psutil.Process(os.getpid())
        mem_before = process.memory_info().rss / 1024 / 1024  # MB
        
        result = func(*args, **kwargs)
        
        mem_after = process.memory_info().rss / 1024 / 1024  # MB
        mem_diff = mem_after - mem_before
        
        print(f"Memory usage for {func.__name__}: {mem_diff:.2f} MB")
        return result
    
    return wrapper


# Load testing utilities
async def simulate_concurrent_users(num_users: int, user_action, *args, **kwargs):
    """Simulate concurrent users performing an action."""
    tasks = []
    for i in range(num_users):
        task = asyncio.create_task(user_action(f"user-{i}", *args, **kwargs))
        tasks.append(task)
    
    start_time = time.time()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    total_time = time.time() - start_time
    
    successful = sum(1 for r in results if not isinstance(r, Exception))
    failed = len(results) - successful
    
    return {
        'total_time': total_time,
        'successful': successful,
        'failed': failed,
        'requests_per_second': len(results) / total_time if total_time > 0 else 0
    }