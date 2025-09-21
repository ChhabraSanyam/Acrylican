"""
Posts API Router

This module provides REST API endpoints for the unified posting service,
including post management, scheduling, and queue monitoring.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from ..database import get_db
from ..dependencies import get_current_user
from ..models import User
from ..schemas import (
    PostCreate, PostUpdate, PostResponse, PostListResponse,
    PostQueueResponse, PostingRequest, SchedulePostRequest, PostingResult
)
from ..services.posting_service import get_posting_service, PostingService
from ..services.queue_processor import get_scheduling_service, SchedulingService

router = APIRouter(prefix="/posts", tags=["posts"])


@router.post("/", response_model=PostResponse)
async def create_post(
    post_data: PostCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    posting_service: PostingService = Depends(get_posting_service)
):
    """
    Create a new post.
    
    Creates a new post in draft status. The post can then be published
    immediately or scheduled for later publishing.
    """
    try:
        return await posting_service.create_post(current_user.id, post_data, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create post")


@router.get("/", response_model=PostListResponse)
async def list_posts(
    skip: int = Query(0, ge=0, description="Number of posts to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of posts to return"),
    status: Optional[str] = Query(None, description="Filter by post status"),
    product_id: Optional[str] = Query(None, description="Filter by product ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    posting_service: PostingService = Depends(get_posting_service)
):
    """
    List posts for the current user with pagination and filtering.
    
    Supports filtering by status and product ID, with pagination.
    """
    try:
        posts, total = await posting_service.list_posts(
            current_user.id, db, skip, limit, status, product_id
        )
        
        return PostListResponse(
            posts=posts,
            total=total,
            skip=skip,
            limit=limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to list posts")


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    posting_service: PostingService = Depends(get_posting_service)
):
    """
    Get a specific post by ID.
    
    Returns detailed information about a post including its status,
    results, and queue information.
    """
    try:
        post = await posting_service.get_post(post_id, current_user.id, db)
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        return post
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get post")


@router.put("/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: str,
    post_data: PostUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    posting_service: PostingService = Depends(get_posting_service)
):
    """
    Update an existing post.
    
    Only draft and scheduled posts can be updated. Published posts
    cannot be modified.
    """
    try:
        return await posting_service.update_post(post_id, current_user.id, post_data, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to update post")


@router.delete("/{post_id}")
async def delete_post(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    posting_service: PostingService = Depends(get_posting_service)
):
    """
    Delete a post and its associated queue items.
    
    Posts that are currently publishing cannot be deleted.
    """
    try:
        success = await posting_service.delete_post(post_id, current_user.id, db)
        if not success:
            raise HTTPException(status_code=404, detail="Post not found")
        return {"message": "Post deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to delete post")


@router.post("/publish", response_model=PostingResult)
async def publish_post(
    request: PostingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    posting_service: PostingService = Depends(get_posting_service)
):
    """
    Publish a post immediately to specified platforms.
    
    Posts the content immediately to all specified platforms (or all
    target platforms if none specified). Returns immediate results.
    """
    try:
        return await posting_service.publish_post_immediately(request, current_user.id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to publish post")


@router.post("/schedule", response_model=PostingResult)
async def schedule_post(
    request: SchedulePostRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    posting_service: PostingService = Depends(get_posting_service)
):
    """
    Schedule a post for future publishing.
    
    Adds the post to the publishing queue to be processed at the
    specified time. Returns queue item information.
    """
    try:
        return await posting_service.schedule_post(request, current_user.id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to schedule post")


@router.get("/queue/status")
async def get_queue_status(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of items to return"),
    status: Optional[str] = Query(None, description="Filter by queue status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    posting_service: PostingService = Depends(get_posting_service)
):
    """
    Get queue status for the current user.
    
    Returns information about queued posts including their status,
    scheduled times, and retry counts.
    """
    try:
        queue_items, total = await posting_service.get_queue_status(
            current_user.id, db, status, skip, limit
        )
        
        return {
            "queue_items": queue_items,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get queue status")


@router.post("/retry-failed")
async def retry_failed_posts(
    max_age_hours: int = Query(24, ge=1, le=168, description="Maximum age of failed posts to retry (hours)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    posting_service: PostingService = Depends(get_posting_service)
):
    """
    Retry failed posts within a time window.
    
    Queues failed posts for retry if they haven't exceeded their
    maximum retry count and are within the specified age limit.
    """
    try:
        stats = await posting_service.retry_failed_posts(current_user.id, db, max_age_hours)
        return {
            "message": f"Queued {stats['retried']} posts for retry",
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retry failed posts")


# Admin endpoints for queue management
@router.post("/admin/process-queue")
async def process_queue(
    background_tasks: BackgroundTasks,
    batch_size: int = Query(10, ge=1, le=50, description="Number of items to process"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    posting_service: PostingService = Depends(get_posting_service)
):
    """
    Process pending queue items (Admin only).
    
    Processes a batch of pending queue items. This endpoint would
    typically be called by a background job scheduler.
    """
    # Note: In a real application, you'd want to add admin role checking here
    try:
        async def process_queue_task():
            stats = await posting_service.process_queue(db, batch_size)
            return stats
        
        background_tasks.add_task(process_queue_task)
        
        return {"message": f"Processing up to {batch_size} queue items in background"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to process queue")


@router.get("/admin/queue/all")
async def get_all_queue_status(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of items to return"),
    status: Optional[str] = Query(None, description="Filter by queue status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    posting_service: PostingService = Depends(get_posting_service)
):
    """
    Get queue status for all users (Admin only).
    
    Returns information about all queued posts across all users.
    """
    # Note: In a real application, you'd want to add admin role checking here
    try:
        queue_items, total = await posting_service.get_queue_status(
            None, db, status, skip, limit  # None for user_id means all users
        )
        
        return {
            "queue_items": queue_items,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get queue status")


# Scheduling optimization endpoints
@router.get("/scheduling/optimal-times")
async def get_optimal_posting_times(
    platforms: List[str] = Query(..., description="List of platforms"),
    days_ahead: int = Query(7, ge=1, le=30, description="Number of days to look ahead"),
    current_user: User = Depends(get_current_user),
    scheduling_service: SchedulingService = Depends(get_scheduling_service)
):
    """
    Get optimal posting times for specified platforms.
    
    Returns recommended posting times based on platform best practices
    and general engagement patterns.
    """
    try:
        optimal_times = scheduling_service.get_optimal_posting_times(
            platforms, days_ahead=days_ahead
        )
        
        return {
            "platforms": platforms,
            "days_ahead": days_ahead,
            "optimal_times": {
                platform: [time.isoformat() for time in times]
                for platform, times in optimal_times.items()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get optimal posting times")


@router.get("/scheduling/next-optimal/{platform}")
async def get_next_optimal_time(
    platform: str,
    current_user: User = Depends(get_current_user),
    scheduling_service: SchedulingService = Depends(get_scheduling_service)
):
    """
    Get the next optimal posting time for a specific platform.
    
    Returns the next recommended posting time based on platform
    best practices.
    """
    try:
        next_time = scheduling_service.get_next_optimal_time(platform)
        
        return {
            "platform": platform,
            "next_optimal_time": next_time.isoformat(),
            "hours_from_now": (next_time - datetime.utcnow()).total_seconds() / 3600
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get next optimal time")


@router.post("/scheduling/staggered")
async def suggest_staggered_schedule(
    platforms: List[str],
    start_time: Optional[datetime] = None,
    stagger_minutes: int = Query(15, ge=5, le=60, description="Minutes between posts"),
    current_user: User = Depends(get_current_user),
    scheduling_service: SchedulingService = Depends(get_scheduling_service)
):
    """
    Suggest staggered posting times for multiple platforms.
    
    Returns a schedule that spreads posts across time to avoid
    overwhelming users and potentially improve engagement.
    """
    try:
        schedule = scheduling_service.suggest_staggered_schedule(
            platforms, start_time, stagger_minutes
        )
        
        return {
            "platforms": platforms,
            "stagger_minutes": stagger_minutes,
            "schedule": {
                platform: time.isoformat()
                for platform, time in schedule.items()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to suggest staggered schedule")


@router.get("/scheduling/analysis")
async def get_posting_analysis(
    days_back: int = Query(30, ge=7, le=90, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    scheduling_service: SchedulingService = Depends(get_scheduling_service)
):
    """
    Get posting pattern analysis and recommendations.
    
    Analyzes the user's posting history to provide personalized
    recommendations for optimal posting times and frequency.
    """
    try:
        analysis = scheduling_service.analyze_posting_patterns(
            current_user.id, db, days_back
        )
        
        return {
            "user_id": current_user.id,
            "analysis_period_days": days_back,
            "analysis": analysis
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to analyze posting patterns")