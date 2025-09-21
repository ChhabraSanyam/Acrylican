"""
Unified Posting Service

This module provides a comprehensive posting service that handles:
- Post orchestration across multiple platforms
- Queue management with priority and retry logic
- Post status tracking and result aggregation
- Scheduling system for optimal posting times
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc

from ..database import get_db
from ..models import Post, PostQueue, User, Product, PlatformConnection
from ..schemas import (
    PostCreate, PostUpdate, PostResponse, PostQueueResponse, 
    PostResultResponse, PostingResult, PostingRequest, SchedulePostRequest
)
from .platform_service import get_platform_service, PlatformService
from .platform_integration import (
    Platform, PostContent, PostResult, PostStatus, 
    PlatformIntegrationError, PostingError
)

logger = logging.getLogger(__name__)


class PostingService:
    """
    Unified service for managing posts across multiple platforms.
    
    This service handles post creation, scheduling, queue management,
    and result tracking with retry logic and error handling.
    """
    
    def __init__(self, platform_service: Optional[PlatformService] = None):
        self.platform_service = platform_service or get_platform_service()
        self.logger = logging.getLogger(__name__)
    
    async def create_post(
        self, 
        user_id: str, 
        post_data: PostCreate, 
        db: Session
    ) -> PostResponse:
        """
        Create a new post.
        
        Args:
            user_id: User creating the post
            post_data: Post creation data
            db: Database session
            
        Returns:
            Created post response
            
        Raises:
            ValueError: If validation fails
        """
        try:
            # Validate user exists
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError("User not found")
            
            # Validate product if provided
            if post_data.product_id:
                product = db.query(Product).filter(
                    and_(Product.id == post_data.product_id, Product.user_id == user_id)
                ).first()
                if not product:
                    raise ValueError("Product not found or not owned by user")
            
            # Validate platforms
            available_platforms = [p.value for p in Platform]
            invalid_platforms = [p for p in post_data.target_platforms if p not in available_platforms]
            if invalid_platforms:
                raise ValueError(f"Invalid platforms: {invalid_platforms}")
            
            # Create post
            post = Post(
                user_id=user_id,
                product_id=post_data.product_id,
                title=post_data.title,
                description=post_data.description,
                hashtags=post_data.hashtags,
                images=post_data.images,
                target_platforms=post_data.target_platforms,
                product_data=post_data.product_data,
                platform_specific_content=post_data.platform_specific_content,
                scheduled_at=post_data.scheduled_at,
                priority=post_data.priority,
                status="draft"
            )
            
            db.add(post)
            db.commit()
            db.refresh(post)
            
            self.logger.info(f"Created post {post.id} for user {user_id}")
            
            return self._post_to_response(post)
            
        except Exception as e:
            db.rollback()
            self.logger.error(f"Error creating post for user {user_id}: {e}")
            raise
    
    async def update_post(
        self, 
        post_id: str, 
        user_id: str, 
        post_data: PostUpdate, 
        db: Session
    ) -> PostResponse:
        """
        Update an existing post.
        
        Args:
            post_id: Post ID to update
            user_id: User updating the post
            post_data: Post update data
            db: Database session
            
        Returns:
            Updated post response
            
        Raises:
            ValueError: If post not found or validation fails
        """
        try:
            # Get post
            post = db.query(Post).filter(
                and_(Post.id == post_id, Post.user_id == user_id)
            ).first()
            if not post:
                raise ValueError("Post not found")
            
            # Can't update published posts
            if post.status == "published":
                raise ValueError("Cannot update published posts")
            
            # Update fields
            update_data = post_data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                if hasattr(post, field):
                    setattr(post, field, value)
            
            # Validate platforms if updated
            if post_data.target_platforms:
                available_platforms = [p.value for p in Platform]
                invalid_platforms = [p for p in post_data.target_platforms if p not in available_platforms]
                if invalid_platforms:
                    raise ValueError(f"Invalid platforms: {invalid_platforms}")
            
            db.commit()
            db.refresh(post)
            
            self.logger.info(f"Updated post {post_id}")
            
            return self._post_to_response(post)
            
        except Exception as e:
            db.rollback()
            self.logger.error(f"Error updating post {post_id}: {e}")
            raise
    
    async def get_post(self, post_id: str, user_id: str, db: Session) -> Optional[PostResponse]:
        """
        Get a specific post.
        
        Args:
            post_id: Post ID
            user_id: User requesting the post
            db: Database session
            
        Returns:
            Post response or None if not found
        """
        post = db.query(Post).filter(
            and_(Post.id == post_id, Post.user_id == user_id)
        ).first()
        
        if not post:
            return None
        
        return self._post_to_response(post)
    
    async def list_posts(
        self, 
        user_id: str, 
        db: Session,
        skip: int = 0,
        limit: int = 50,
        status: Optional[str] = None,
        product_id: Optional[str] = None
    ) -> Tuple[List[PostResponse], int]:
        """
        List posts for a user with pagination and filtering.
        
        Args:
            user_id: User ID
            db: Database session
            skip: Number of posts to skip
            limit: Maximum number of posts to return
            status: Filter by status
            product_id: Filter by product ID
            
        Returns:
            Tuple of (posts, total_count)
        """
        query = db.query(Post).filter(Post.user_id == user_id)
        
        if status:
            query = query.filter(Post.status == status)
        
        if product_id:
            query = query.filter(Post.product_id == product_id)
        
        total = query.count()
        posts = query.order_by(desc(Post.created_at)).offset(skip).limit(limit).all()
        
        post_responses = [self._post_to_response(post) for post in posts]
        
        return post_responses, total
    
    async def delete_post(self, post_id: str, user_id: str, db: Session) -> bool:
        """
        Delete a post and its queue items.
        
        Args:
            post_id: Post ID
            user_id: User deleting the post
            db: Database session
            
        Returns:
            True if deleted, False if not found
        """
        try:
            post = db.query(Post).filter(
                and_(Post.id == post_id, Post.user_id == user_id)
            ).first()
            
            if not post:
                return False
            
            # Can't delete posts that are currently publishing
            if post.status == "publishing":
                raise ValueError("Cannot delete posts that are currently publishing")
            
            # Delete queue items first
            db.query(PostQueue).filter(PostQueue.post_id == post_id).delete()
            
            # Delete post
            db.delete(post)
            db.commit()
            
            self.logger.info(f"Deleted post {post_id}")
            return True
            
        except Exception as e:
            db.rollback()
            self.logger.error(f"Error deleting post {post_id}: {e}")
            raise
    
    async def publish_post_immediately(
        self, 
        request: PostingRequest, 
        user_id: str, 
        db: Session
    ) -> PostingResult:
        """
        Publish a post immediately to specified platforms.
        
        Args:
            request: Posting request
            user_id: User publishing the post
            db: Database session
            
        Returns:
            Posting result with immediate results
        """
        try:
            # Get post
            post = db.query(Post).filter(
                and_(Post.id == request.post_id, Post.user_id == user_id)
            ).first()
            if not post:
                raise ValueError("Post not found")
            
            # Determine platforms to post to
            platforms = request.platforms or post.target_platforms
            
            # Validate user has connections to these platforms
            connected_platforms = await self._get_user_connected_platforms(user_id, db)
            unavailable_platforms = [p for p in platforms if p not in connected_platforms]
            if unavailable_platforms:
                raise ValueError(f"Not connected to platforms: {unavailable_platforms}")
            
            # Update post status
            post.status = "publishing"
            post.published_at = datetime.utcnow()
            db.commit()
            
            # Create post content
            content = PostContent(
                title=post.title,
                description=post.description,
                hashtags=post.hashtags,
                images=post.images,
                product_data=post.product_data,
                platform_specific=post.platform_specific_content
            )
            
            # Post to platforms
            platform_enums = [Platform(p) for p in platforms]
            results = await self.platform_service.post_to_multiple_platforms(
                platform_enums, user_id, content
            )
            
            # Update post with results
            post.results = [self._post_result_to_dict(r) for r in results]
            
            # Determine final status
            successful_posts = [r for r in results if r.status == PostStatus.SUCCESS]
            if successful_posts:
                post.status = "published" if len(successful_posts) == len(results) else "partial"
            else:
                post.status = "failed"
                post.last_error = "All platforms failed"
            
            db.commit()
            
            self.logger.info(
                f"Published post {request.post_id} to {len(successful_posts)}/{len(results)} platforms"
            )
            
            return PostingResult(
                success=len(successful_posts) > 0,
                post_id=request.post_id,
                results=[self._post_result_to_response(r) for r in results],
                queued_items=[],
                message=f"Posted to {len(successful_posts)}/{len(results)} platforms"
            )
            
        except Exception as e:
            # Update post status on error
            if 'post' in locals():
                post.status = "failed"
                post.last_error = str(e)
                db.commit()
            
            self.logger.error(f"Error publishing post {request.post_id}: {e}")
            raise
    
    async def schedule_post(
        self, 
        request: SchedulePostRequest, 
        user_id: str, 
        db: Session
    ) -> PostingResult:
        """
        Schedule a post for future publishing.
        
        Args:
            request: Schedule request
            user_id: User scheduling the post
            db: Database session
            
        Returns:
            Posting result with queue information
        """
        try:
            # Get post
            post = db.query(Post).filter(
                and_(Post.id == request.post_id, Post.user_id == user_id)
            ).first()
            if not post:
                raise ValueError("Post not found")
            
            # Validate schedule time is in the future
            if request.scheduled_at <= datetime.utcnow():
                raise ValueError("Scheduled time must be in the future")
            
            # Determine platforms to post to
            platforms = request.platforms or post.target_platforms
            
            # Validate user has connections to these platforms
            connected_platforms = await self._get_user_connected_platforms(user_id, db)
            unavailable_platforms = [p for p in platforms if p not in connected_platforms]
            if unavailable_platforms:
                raise ValueError(f"Not connected to platforms: {unavailable_platforms}")
            
            # Update post
            post.scheduled_at = request.scheduled_at
            post.status = "scheduled"
            
            # Clear existing queue items for this post
            db.query(PostQueue).filter(PostQueue.post_id == request.post_id).delete()
            
            # Create queue items for each platform
            queue_items = []
            for platform in platforms:
                queue_item = PostQueue(
                    post_id=request.post_id,
                    platform=platform,
                    scheduled_at=request.scheduled_at,
                    priority=post.priority,
                    status="pending"
                )
                db.add(queue_item)
                queue_items.append(queue_item)
            
            db.commit()
            
            # Refresh to get IDs
            for item in queue_items:
                db.refresh(item)
            
            self.logger.info(
                f"Scheduled post {request.post_id} for {request.scheduled_at} "
                f"on {len(platforms)} platforms"
            )
            
            return PostingResult(
                success=True,
                post_id=request.post_id,
                results=[],
                queued_items=[item.id for item in queue_items],
                message=f"Scheduled for {len(platforms)} platforms at {request.scheduled_at}"
            )
            
        except Exception as e:
            db.rollback()
            self.logger.error(f"Error scheduling post {request.post_id}: {e}")
            raise
    
    async def process_queue(self, db: Session, batch_size: int = 10) -> Dict[str, int]:
        """
        Process pending queue items.
        
        Args:
            db: Database session
            batch_size: Maximum number of items to process
            
        Returns:
            Dictionary with processing statistics
        """
        try:
            # Get pending queue items that are ready to be processed
            now = datetime.utcnow()
            queue_items = db.query(PostQueue).filter(
                and_(
                    PostQueue.status == "pending",
                    PostQueue.scheduled_at <= now
                )
            ).order_by(
                desc(PostQueue.priority),
                asc(PostQueue.scheduled_at)
            ).limit(batch_size).all()
            
            if not queue_items:
                return {"processed": 0, "successful": 0, "failed": 0, "retried": 0}
            
            self.logger.info(f"Processing {len(queue_items)} queue items")
            
            stats = {"processed": 0, "successful": 0, "failed": 0, "retried": 0}
            
            for queue_item in queue_items:
                try:
                    result = await self._process_queue_item(queue_item, db)
                    stats["processed"] += 1
                    
                    if result["success"]:
                        stats["successful"] += 1
                    elif result["retry"]:
                        stats["retried"] += 1
                    else:
                        stats["failed"] += 1
                        
                except Exception as e:
                    self.logger.error(f"Error processing queue item {queue_item.id}: {e}")
                    stats["processed"] += 1
                    stats["failed"] += 1
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error processing queue: {e}")
            raise
    
    async def get_queue_status(
        self, 
        user_id: Optional[str] = None, 
        db: Session = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[PostQueueResponse], int]:
        """
        Get queue status with optional filtering.
        
        Args:
            user_id: Filter by user ID
            db: Database session
            status: Filter by status
            skip: Number of items to skip
            limit: Maximum number of items to return
            
        Returns:
            Tuple of (queue_items, total_count)
        """
        query = db.query(PostQueue)
        
        if user_id:
            query = query.join(Post).filter(Post.user_id == user_id)
        
        if status:
            query = query.filter(PostQueue.status == status)
        
        total = query.count()
        queue_items = query.order_by(
            desc(PostQueue.priority),
            asc(PostQueue.scheduled_at)
        ).offset(skip).limit(limit).all()
        
        responses = [self._queue_item_to_response(item) for item in queue_items]
        
        return responses, total
    
    async def retry_failed_posts(
        self, 
        user_id: str, 
        db: Session,
        max_age_hours: int = 24
    ) -> Dict[str, int]:
        """
        Retry failed posts within a time window.
        
        Args:
            user_id: User ID
            db: Database session
            max_age_hours: Maximum age of failed posts to retry
            
        Returns:
            Dictionary with retry statistics
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
            
            # Get failed queue items for the user
            failed_items = db.query(PostQueue).join(Post).filter(
                and_(
                    Post.user_id == user_id,
                    PostQueue.status == "failed",
                    PostQueue.retry_count < PostQueue.max_retries,
                    PostQueue.updated_at >= cutoff_time
                )
            ).all()
            
            stats = {"retried": 0, "successful": 0, "failed": 0}
            
            for item in failed_items:
                # Reset status and increment retry count
                item.status = "pending"
                item.retry_count += 1
                item.scheduled_at = datetime.utcnow()
                
                stats["retried"] += 1
            
            db.commit()
            
            self.logger.info(f"Queued {stats['retried']} failed posts for retry")
            
            return stats
            
        except Exception as e:
            db.rollback()
            self.logger.error(f"Error retrying failed posts: {e}")
            raise
    
    async def _process_queue_item(self, queue_item: PostQueue, db: Session) -> Dict[str, Any]:
        """
        Process a single queue item.
        
        Args:
            queue_item: Queue item to process
            db: Database session
            
        Returns:
            Dictionary with processing result
        """
        try:
            # Update status to processing
            queue_item.status = "processing"
            queue_item.started_at = datetime.utcnow()
            db.commit()
            
            # Get post
            post = db.query(Post).filter(Post.id == queue_item.post_id).first()
            if not post:
                raise ValueError("Post not found")
            
            # Create post content
            content = PostContent(
                title=post.title,
                description=post.description,
                hashtags=post.hashtags,
                images=post.images,
                product_data=post.product_data,
                platform_specific=post.platform_specific_content
            )
            
            # Post to platform
            platform = Platform(queue_item.platform)
            result = await self.platform_service.post_to_platform(
                platform, post.user_id, content
            )
            
            # Update queue item with result
            queue_item.result = self._post_result_to_dict(result)
            queue_item.completed_at = datetime.utcnow()
            
            if result.status == PostStatus.SUCCESS:
                queue_item.status = "completed"
                success = True
                retry = False
            else:
                # Check if we should retry
                if queue_item.retry_count < queue_item.max_retries:
                    queue_item.status = "pending"
                    queue_item.retry_count += 1
                    queue_item.scheduled_at = datetime.utcnow() + timedelta(minutes=5 * (queue_item.retry_count + 1))
                    success = False
                    retry = True
                else:
                    queue_item.status = "failed"
                    queue_item.error_message = result.error_message
                    success = False
                    retry = False
            
            # Update post results
            if not post.results:
                post.results = []
            
            # Update or add result for this platform
            platform_results = [r for r in post.results if r.get("platform") != queue_item.platform]
            platform_results.append(self._post_result_to_dict(result))
            post.results = platform_results
            
            # Update post status if all queue items are done
            remaining_pending = db.query(PostQueue).filter(
                and_(
                    PostQueue.post_id == queue_item.post_id,
                    PostQueue.status.in_(["pending", "processing"])
                )
            ).count()
            
            if remaining_pending == 0:
                # All queue items are done, update post status
                successful_results = [r for r in post.results if r.get("status") == "success"]
                if successful_results:
                    post.status = "published" if len(successful_results) == len(post.results) else "partial"
                    post.published_at = datetime.utcnow()
                else:
                    post.status = "failed"
                    post.last_error = "All platforms failed"
            
            db.commit()
            
            return {"success": success, "retry": retry, "result": result}
            
        except Exception as e:
            # Update queue item with error
            queue_item.status = "failed"
            queue_item.error_message = str(e)
            queue_item.completed_at = datetime.utcnow()
            db.commit()
            
            self.logger.error(f"Error processing queue item {queue_item.id}: {e}")
            return {"success": False, "retry": False, "error": str(e)}
    
    async def _get_user_connected_platforms(self, user_id: str, db: Session) -> List[str]:
        """
        Get list of platforms the user is connected to.
        
        Args:
            user_id: User ID
            db: Database session
            
        Returns:
            List of platform names
        """
        connections = db.query(PlatformConnection).filter(
            and_(
                PlatformConnection.user_id == user_id,
                PlatformConnection.is_active == True
            )
        ).all()
        
        return [conn.platform for conn in connections]
    
    def _post_to_response(self, post: Post) -> PostResponse:
        """Convert Post model to PostResponse."""
        results = None
        if post.results:
            results = [
                PostResultResponse(**result) if isinstance(result, dict) else result
                for result in post.results
            ]
        
        return PostResponse(
            id=post.id,
            user_id=post.user_id,
            product_id=post.product_id,
            title=post.title,
            description=post.description,
            hashtags=post.hashtags,
            images=post.images,
            target_platforms=post.target_platforms,
            product_data=post.product_data,
            platform_specific_content=post.platform_specific_content,
            scheduled_at=post.scheduled_at,
            published_at=post.published_at,
            status=post.status,
            results=results,
            priority=post.priority,
            retry_count=post.retry_count,
            max_retries=post.max_retries,
            last_error=post.last_error,
            created_at=post.created_at,
            updated_at=post.updated_at
        )
    
    def _queue_item_to_response(self, item: PostQueue) -> PostQueueResponse:
        """Convert PostQueue model to PostQueueResponse."""
        result = None
        if item.result:
            result = PostResultResponse(**item.result) if isinstance(item.result, dict) else item.result
        
        return PostQueueResponse(
            id=item.id,
            post_id=item.post_id,
            platform=item.platform,
            status=item.status,
            priority=item.priority,
            scheduled_at=item.scheduled_at,
            started_at=item.started_at,
            completed_at=item.completed_at,
            retry_count=item.retry_count,
            max_retries=item.max_retries,
            result=result,
            error_message=item.error_message,
            created_at=item.created_at,
            updated_at=item.updated_at
        )
    
    def _post_result_to_dict(self, result: PostResult) -> Dict[str, Any]:
        """Convert PostResult to dictionary."""
        return {
            "platform": result.platform.value,
            "status": result.status.value,
            "post_id": result.post_id,
            "url": result.url,
            "error_message": result.error_message,
            "error_code": result.error_code,
            "published_at": result.published_at.isoformat() if result.published_at else None,
            "retry_count": result.retry_count,
            "metadata": result.metadata
        }
    
    def _post_result_to_response(self, result: PostResult) -> PostResultResponse:
        """Convert PostResult to PostResultResponse."""
        return PostResultResponse(
            platform=result.platform.value,
            status=result.status.value,
            post_id=result.post_id,
            url=result.url,
            error_message=result.error_message,
            error_code=result.error_code,
            published_at=result.published_at,
            retry_count=result.retry_count,
            metadata=result.metadata
        )


# Global service instance
posting_service = PostingService()


def get_posting_service() -> PostingService:
    """
    Get the global posting service instance.
    
    Returns:
        Global PostingService instance
    """
    return posting_service