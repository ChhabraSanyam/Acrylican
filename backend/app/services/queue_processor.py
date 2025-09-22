"""
Queue Processor Service

This module provides background task processing for the posting queue.
It handles scheduled posts and retry logic with proper error handling.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any
from sqlalchemy.orm import Session

from ..database import get_db
from .posting_service import get_posting_service, PostingService

logger = logging.getLogger(__name__)


class QueueProcessor:
    """
    Background service for processing the posting queue.
    
    This service runs continuously to process scheduled posts,
    handle retries, and maintain queue health.
    """
    
    def __init__(self, posting_service: PostingService = None):
        self.posting_service = posting_service or get_posting_service()
        self.logger = logging.getLogger(__name__)
        self.running = False
        self.process_interval = 30  # seconds
        self.batch_size = 10
    
    async def start(self):
        """Start the queue processor."""
        if self.running:
            self.logger.warning("Queue processor is already running")
            return
        
        self.running = True
        self.logger.info("Starting queue processor")
        
        try:
            while self.running:
                try:
                    await self._process_cycle()
                except Exception as e:
                    self.logger.error(f"Error in queue processing cycle: {e}")
                
                # Wait before next cycle
                await asyncio.sleep(self.process_interval)
                
        except asyncio.CancelledError:
            self.logger.info("Queue processor cancelled")
        except Exception as e:
            self.logger.error(f"Queue processor error: {e}")
        finally:
            self.running = False
            self.logger.info("Queue processor stopped")
    
    async def stop(self):
        """Stop the queue processor."""
        self.logger.info("Stopping queue processor")
        self.running = False
    
    async def _process_cycle(self):
        """Process one cycle of the queue."""
        try:
            db = next(get_db())
            try:
                stats = await self.posting_service.process_queue(db, self.batch_size)
                
                if stats["processed"] > 0:
                    self.logger.info(
                        f"Processed {stats['processed']} items: "
                        f"{stats['successful']} successful, "
                        f"{stats['failed']} failed, "
                        f"{stats['retried']} retried"
                    )
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error in processing cycle: {e}")
    
    def set_process_interval(self, seconds: int):
        """Set the processing interval."""
        if seconds < 10:
            raise ValueError("Process interval must be at least 10 seconds")
        self.process_interval = seconds
        self.logger.info(f"Set process interval to {seconds} seconds")
    
    def set_batch_size(self, size: int):
        """Set the batch size for processing."""
        if size < 1 or size > 100:
            raise ValueError("Batch size must be between 1 and 100")
        self.batch_size = size
        self.logger.info(f"Set batch size to {size}")


class SchedulingService:
    """
    Service for optimal post scheduling.
    
    This service provides intelligent scheduling recommendations
    based on platform best practices and user engagement patterns.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Platform-specific optimal posting times (UTC hours)
        self.optimal_times = {
            "facebook": [13, 15, 19],  # 1 PM, 3 PM, 7 PM UTC
            "instagram": [11, 14, 17, 20],  # 11 AM, 2 PM, 5 PM, 8 PM UTC
            "pinterest": [14, 16, 20, 21],  # 2 PM, 4 PM, 8 PM, 9 PM UTC
            "etsy": [10, 14, 19],  # 10 AM, 2 PM, 7 PM UTC
            "shopify": [12, 15, 18],  # 12 PM, 3 PM, 6 PM UTC
        }
        
        # Days of week preferences (0 = Monday, 6 = Sunday)
        self.optimal_days = {
            "facebook": [1, 2, 3, 4],  # Tuesday to Friday
            "instagram": [0, 1, 2, 3, 4],  # Monday to Friday
            "pinterest": [5, 6, 0, 1],  # Saturday to Tuesday
            "etsy": [0, 1, 2, 3, 4],  # Monday to Friday
            "shopify": [1, 2, 3, 4],  # Tuesday to Friday
        }
    
    def get_optimal_posting_times(
        self, 
        platforms: list[str], 
        start_date: datetime = None,
        days_ahead: int = 7
    ) -> Dict[str, list[datetime]]:
        """
        Get optimal posting times for specified platforms.
        
        Args:
            platforms: List of platform names
            start_date: Start date for scheduling (default: now)
            days_ahead: Number of days to look ahead
            
        Returns:
            Dictionary mapping platforms to optimal posting times
        """
        if start_date is None:
            start_date = datetime.utcnow()
        
        results = {}
        
        for platform in platforms:
            platform_times = []
            
            # Get platform preferences
            optimal_hours = self.optimal_times.get(platform, [12, 15, 18])
            optimal_weekdays = self.optimal_days.get(platform, [0, 1, 2, 3, 4])
            
            # Generate optimal times for the next N days
            current_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            
            for day_offset in range(days_ahead):
                check_date = current_date + timedelta(days=day_offset)
                weekday = check_date.weekday()
                
                # Skip if not an optimal day for this platform
                if weekday not in optimal_weekdays:
                    continue
                
                # Add optimal hours for this day
                for hour in optimal_hours:
                    posting_time = check_date.replace(hour=hour)
                    
                    # Only include future times
                    if posting_time > start_date:
                        platform_times.append(posting_time)
            
            results[platform] = sorted(platform_times)
        
        return results
    
    def get_next_optimal_time(
        self, 
        platform: str, 
        after: datetime = None
    ) -> datetime:
        """
        Get the next optimal posting time for a platform.
        
        Args:
            platform: Platform name
            after: Get time after this datetime (default: now)
            
        Returns:
            Next optimal posting time
        """
        if after is None:
            after = datetime.utcnow()
        
        optimal_times = self.get_optimal_posting_times([platform], after, 14)
        platform_times = optimal_times.get(platform, [])
        
        if not platform_times:
            # Fallback: next hour
            return after.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        
        return platform_times[0]
    
    def suggest_staggered_schedule(
        self, 
        platforms: list[str], 
        start_time: datetime = None,
        stagger_minutes: int = 15
    ) -> Dict[str, datetime]:
        """
        Suggest staggered posting times for multiple platforms.
        
        This helps avoid overwhelming the user with simultaneous posts
        and can improve engagement by spreading content over time.
        
        Args:
            platforms: List of platform names
            start_time: Base time for staggering (default: next optimal time)
            stagger_minutes: Minutes between posts
            
        Returns:
            Dictionary mapping platforms to suggested posting times
        """
        if start_time is None:
            start_time = datetime.utcnow() + timedelta(hours=1)
        
        results = {}
        current_time = start_time
        
        # Sort platforms by priority (social media first, then marketplaces)
        social_platforms = ["facebook", "instagram", "pinterest"]
        marketplace_platforms = ["etsy", "shopify"]
        
        sorted_platforms = []
        for platform in platforms:
            if platform in social_platforms:
                sorted_platforms.append(platform)
        for platform in platforms:
            if platform in marketplace_platforms:
                sorted_platforms.append(platform)
        for platform in platforms:
            if platform not in social_platforms and platform not in marketplace_platforms:
                sorted_platforms.append(platform)
        
        # Assign staggered times
        for platform in sorted_platforms:
            results[platform] = current_time
            current_time += timedelta(minutes=stagger_minutes)
        
        return results
    
    def analyze_posting_patterns(
        self, 
        user_id: str, 
        db: Session,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze user's posting patterns to suggest improvements.
        
        Args:
            user_id: User ID
            db: Database session
            days_back: Number of days to analyze
            
        Returns:
            Analysis results with recommendations
        """
        # This would analyze the user's posting history
        # For now, return basic recommendations
        return {
            "recommendations": [
                "Post consistently during weekdays for better engagement",
                "Stagger posts across platforms by 15-30 minutes",
                "Avoid posting on weekends for B2B platforms",
                "Use optimal times based on your audience timezone"
            ],
            "optimal_days": ["Tuesday", "Wednesday", "Thursday"],
            "optimal_hours": ["2 PM", "3 PM", "7 PM"],
            "suggested_frequency": "3-5 posts per week"
        }


# Global instances
queue_processor = QueueProcessor()
scheduling_service = SchedulingService()


def get_queue_processor() -> QueueProcessor:
    """Get the global queue processor instance."""
    return queue_processor


def get_scheduling_service() -> SchedulingService:
    """Get the global scheduling service instance."""
    return scheduling_service