"""
Content Generation Router.

This module handles API endpoints for AI-powered content generation
using Google Gemini API for creating marketing copy.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import time
import logging
from typing import Dict, Any

from ..database import get_db
from ..models import User
from ..schemas import (
    ContentGenerationInput, 
    ContentGenerationResult, 
    GeneratedContentResponse,
    ContentVariation,
    PlatformContent
)
from ..dependencies import get_current_user
from ..services.content_generation import (
    content_generation_service, 
    ContentInput, 
    ContentGenerationError
)

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/content", tags=["content-generation"])


@router.post("/generate", response_model=ContentGenerationResult)
async def generate_content(
    content_input: ContentGenerationInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate AI-powered marketing content for a product.
    
    This endpoint uses Google Gemini API to create professional marketing copy
    including titles, descriptions, and hashtags optimized for different platforms.
    
    Args:
        content_input: Content generation input data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        ContentGenerationResult: Generated content with platform variations
        
    Raises:
        HTTPException: If content generation fails or API is not configured
    """
    start_time = time.time()
    
    try:
        # Prepare business context from user data
        business_context = {
            "business_name": current_user.business_name,
            "business_type": current_user.business_type,
            "business_description": current_user.business_description,
            "location": current_user.location,
            "website": current_user.website
        }
        
        # Create content input for the service
        service_input = ContentInput(
            description=content_input.description,
            business_context=business_context,
            target_platforms=content_input.target_platforms,
            product_category=content_input.product_category,
            price_range=content_input.price_range,
            target_audience=content_input.target_audience
        )
        
        # Generate content using the service
        generated_content = await content_generation_service.generate_content(service_input)
        
        # Convert to response format
        variations = [
            ContentVariation(title=var["title"], focus=var["focus"])
            for var in generated_content.variations
        ]
        
        platform_specific = {
            platform: PlatformContent(
                title=content["title"],
                description=content["description"],
                hashtags=content["hashtags"],
                call_to_action=content["call_to_action"],
                character_count=content["character_count"],
                optimization_notes=content["optimization_notes"]
            )
            for platform, content in generated_content.platform_specific.items()
        }
        
        response_content = GeneratedContentResponse(
            title=generated_content.title,
            description=generated_content.description,
            hashtags=generated_content.hashtags,
            variations=variations,
            platform_specific=platform_specific
        )
        
        processing_time = time.time() - start_time
        
        logger.info(f"Content generated successfully for user {current_user.id} in {processing_time:.2f}s")
        
        return ContentGenerationResult(
            success=True,
            content=response_content,
            message="Content generated successfully",
            processing_time=processing_time
        )
        
    except ContentGenerationError as e:
        logger.error(f"Content generation error for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error during content generation for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during content generation"
        )


@router.get("/platforms")
async def get_supported_platforms():
    """
    Get list of supported platforms for content generation.
    
    Returns:
        dict: List of supported platforms with their specifications
    """
    platforms = {
        "facebook": {
            "name": "Facebook",
            "type": "social_media",
            "title_max_length": 100,
            "description_max_length": 8000,
            "hashtag_limit": 5,
            "features": ["posts", "pages", "groups"]
        },
        "instagram": {
            "name": "Instagram",
            "type": "social_media",
            "title_max_length": 125,
            "description_max_length": 2200,
            "hashtag_limit": 30,
            "features": ["posts", "stories", "reels"]
        },
        "facebook_marketplace": {
            "name": "Facebook Marketplace",
            "type": "marketplace",
            "title_max_length": 80,
            "description_max_length": 8000,
            "hashtag_limit": 0,
            "features": ["product_listings"]
        },
        "etsy": {
            "name": "Etsy",
            "type": "marketplace",
            "title_max_length": 140,
            "description_max_length": 5000,
            "hashtag_limit": 13,
            "features": ["product_listings", "shop_management"]
        },
        "pinterest": {
            "name": "Pinterest",
            "type": "social_media",
            "title_max_length": 100,
            "description_max_length": 500,
            "hashtag_limit": 5,
            "features": ["pins", "boards"]
        },
        "shopify": {
            "name": "Shopify",
            "type": "ecommerce",
            "title_max_length": 255,
            "description_max_length": 65535,
            "hashtag_limit": 250,
            "features": ["product_listings", "store_management"]
        }
    }
    
    return {
        "success": True,
        "platforms": platforms,
        "total_count": len(platforms)
    }


@router.post("/validate")
async def validate_content(
    validation_data: dict
):
    """
    Validate content against platform-specific requirements.
    
    Args:
        validation_data: Dictionary containing platform, title, description, and hashtags
        
    Returns:
        dict: Validation result with any issues found
    """
    # Extract data from request
    platform = validation_data.get("platform")
    title = validation_data.get("title", "")
    description = validation_data.get("description", "")
    hashtags = validation_data.get("hashtags", [])
    
    if not platform:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Platform is required"
        )
    
    # Get platform specifications
    platforms_response = await get_supported_platforms()
    platforms = platforms_response["platforms"]
    
    if platform not in platforms:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported platform: {platform}"
        )
    
    platform_spec = platforms[platform]
    issues = []
    
    # Validate title length
    if len(title) > platform_spec["title_max_length"]:
        issues.append({
            "field": "title",
            "issue": f"Title exceeds maximum length of {platform_spec['title_max_length']} characters",
            "current_length": len(title),
            "max_length": platform_spec["title_max_length"]
        })
    
    # Validate description length
    if len(description) > platform_spec["description_max_length"]:
        issues.append({
            "field": "description",
            "issue": f"Description exceeds maximum length of {platform_spec['description_max_length']} characters",
            "current_length": len(description),
            "max_length": platform_spec["description_max_length"]
        })
    
    # Validate hashtag count
    if len(hashtags) > platform_spec["hashtag_limit"] and platform_spec["hashtag_limit"] > 0:
        issues.append({
            "field": "hashtags",
            "issue": f"Too many hashtags. Maximum allowed: {platform_spec['hashtag_limit']}",
            "current_count": len(hashtags),
            "max_count": platform_spec["hashtag_limit"]
        })
    
    return {
        "success": True,
        "valid": len(issues) == 0,
        "platform": platform,
        "issues": issues,
        "character_counts": {
            "title": len(title),
            "description": len(description),
            "hashtag_count": len(hashtags)
        }
    }


@router.get("/health")
async def content_service_health():
    """
    Check the health of the content generation service.
    
    Returns:
        dict: Service health status
    """
    try:
        # Check if Gemini API is configured
        api_configured = bool(content_generation_service.api_key)
        
        return {
            "success": True,
            "service": "content_generation",
            "status": "healthy" if api_configured else "degraded",
            "api_configured": api_configured,
            "model": content_generation_service.model_name if api_configured else None,
            "message": "Service is operational" if api_configured else "Gemini API not configured"
        }
        
    except Exception as e:
        logger.error(f"Content service health check failed: {e}")
        return {
            "success": False,
            "service": "content_generation",
            "status": "unhealthy",
            "api_configured": False,
            "error": str(e)
        }