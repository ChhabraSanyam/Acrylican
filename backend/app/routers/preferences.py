"""
Platform Preferences Routes

This module provides API endpoints for managing platform-specific preferences,
including posting preferences, content templates, and scheduling settings.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..database import get_db
from ..dependencies import get_current_user
from ..models import User, PlatformPreferences, ContentTemplate
from ..schemas import (
    PlatformPreferencesCreate,
    PlatformPreferencesUpdate,
    PlatformPreferencesResponse,
    ContentTemplateCreate,
    ContentTemplateUpdate,
    ContentTemplateResponse
)
from ..services.platform_integration import Platform
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/preferences", tags=["platform-preferences"])


@router.get("/platforms", response_model=List[PlatformPreferencesResponse])
async def get_all_platform_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get platform preferences for all platforms"""
    
    preferences = db.query(PlatformPreferences).filter(
        PlatformPreferences.user_id == current_user.id
    ).all()
    
    # Create default preferences for platforms that don't have them
    existing_platforms = {pref.platform for pref in preferences}
    all_platforms = {platform.value for platform in Platform}
    
    for platform in all_platforms:
        if platform not in existing_platforms:
            default_prefs = _create_default_preferences(platform, current_user.id)
            db.add(default_prefs)
            preferences.append(default_prefs)
    
    db.commit()
    return preferences


@router.get("/platforms/{platform}", response_model=PlatformPreferencesResponse)
async def get_platform_preferences(
    platform: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get preferences for a specific platform"""
    
    # Validate platform
    try:
        platform_enum = Platform(platform)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
    
    preferences = db.query(PlatformPreferences).filter(
        PlatformPreferences.user_id == current_user.id,
        PlatformPreferences.platform == platform
    ).first()
    
    if not preferences:
        # Create default preferences
        preferences = _create_default_preferences(platform, current_user.id)
        db.add(preferences)
        db.commit()
        db.refresh(preferences)
    
    return preferences


@router.post("/platforms/{platform}", response_model=PlatformPreferencesResponse)
async def create_platform_preferences(
    platform: str,
    preferences_data: PlatformPreferencesCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create or update preferences for a specific platform"""
    
    # Validate platform
    try:
        platform_enum = Platform(platform)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
    
    # Check if preferences already exist
    existing_prefs = db.query(PlatformPreferences).filter(
        PlatformPreferences.user_id == current_user.id,
        PlatformPreferences.platform == platform
    ).first()
    
    if existing_prefs:
        # Update existing preferences
        for field, value in preferences_data.model_dump(exclude_unset=True).items():
            if field != "platform":  # Don't update platform field
                setattr(existing_prefs, field, value)
        
        existing_prefs.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing_prefs)
        return existing_prefs
    
    # Create new preferences
    preferences = PlatformPreferences(
        user_id=current_user.id,
        platform=platform,
        **preferences_data.model_dump(exclude={"platform"})
    )
    
    db.add(preferences)
    db.commit()
    db.refresh(preferences)
    
    logger.info(f"Created platform preferences for {platform} for user {current_user.id}")
    return preferences


@router.put("/platforms/{platform}", response_model=PlatformPreferencesResponse)
async def update_platform_preferences(
    platform: str,
    preferences_data: PlatformPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update preferences for a specific platform"""
    
    # Validate platform
    try:
        platform_enum = Platform(platform)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
    
    preferences = db.query(PlatformPreferences).filter(
        PlatformPreferences.user_id == current_user.id,
        PlatformPreferences.platform == platform
    ).first()
    
    if not preferences:
        raise HTTPException(
            status_code=404,
            detail=f"Preferences not found for platform {platform}"
        )
    
    # Update preferences
    update_data = preferences_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(preferences, field, value)
    
    preferences.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(preferences)
    
    logger.info(f"Updated platform preferences for {platform} for user {current_user.id}")
    return preferences


@router.delete("/platforms/{platform}")
async def reset_platform_preferences(
    platform: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reset platform preferences to defaults"""
    
    # Validate platform
    try:
        platform_enum = Platform(platform)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
    
    preferences = db.query(PlatformPreferences).filter(
        PlatformPreferences.user_id == current_user.id,
        PlatformPreferences.platform == platform
    ).first()
    
    if preferences:
        db.delete(preferences)
    
    # Create new default preferences
    default_prefs = _create_default_preferences(platform, current_user.id)
    db.add(default_prefs)
    db.commit()
    db.refresh(default_prefs)
    
    logger.info(f"Reset platform preferences for {platform} for user {current_user.id}")
    return {"message": f"Platform preferences for {platform} have been reset to defaults"}


@router.get("/templates", response_model=List[ContentTemplateResponse])
async def get_content_templates(
    platform: Optional[str] = Query(None, description="Filter by platform"),
    category: Optional[str] = Query(None, description="Filter by category"),
    style: Optional[str] = Query(None, description="Filter by style"),
    include_system: bool = Query(True, description="Include system templates"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get content templates"""
    
    query = db.query(ContentTemplate).filter(
        (ContentTemplate.user_id == current_user.id) |
        (ContentTemplate.is_system_template == True if include_system else False)
    )
    
    if platform:
        # Validate platform
        try:
            Platform(platform)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
        
        query = query.filter(ContentTemplate.platforms.contains([platform]))
    
    if category:
        query = query.filter(ContentTemplate.category == category)
    
    if style:
        query = query.filter(ContentTemplate.style == style)
    
    templates = query.order_by(
        ContentTemplate.is_system_template.desc(),
        ContentTemplate.is_default.desc(),
        ContentTemplate.usage_count.desc(),
        ContentTemplate.created_at.desc()
    ).all()
    
    return templates


@router.get("/templates/{template_id}", response_model=ContentTemplateResponse)
async def get_content_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific content template"""
    
    template = db.query(ContentTemplate).filter(
        ContentTemplate.id == template_id,
        (ContentTemplate.user_id == current_user.id) |
        (ContentTemplate.is_system_template == True)
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return template


@router.post("/templates", response_model=ContentTemplateResponse)
async def create_content_template(
    template_data: ContentTemplateCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new content template"""
    
    # Validate platforms
    for platform in template_data.platforms:
        try:
            Platform(platform)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
    
    # Check if setting as default
    if template_data.is_default:
        # Unset other default templates for the same platforms and category
        existing_defaults = db.query(ContentTemplate).filter(
            ContentTemplate.user_id == current_user.id,
            ContentTemplate.is_default == True,
            ContentTemplate.category == template_data.category
        ).all()
        
        for template in existing_defaults:
            # Check if there's platform overlap
            if any(platform in template.platforms for platform in template_data.platforms):
                template.is_default = False
    
    template = ContentTemplate(
        user_id=current_user.id,
        **template_data.model_dump()
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    logger.info(f"Created content template {template.name} for user {current_user.id}")
    return template


@router.put("/templates/{template_id}", response_model=ContentTemplateResponse)
async def update_content_template(
    template_id: str,
    template_data: ContentTemplateUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a content template"""
    
    template = db.query(ContentTemplate).filter(
        ContentTemplate.id == template_id,
        ContentTemplate.user_id == current_user.id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Validate platforms if provided
    if template_data.platforms:
        for platform in template_data.platforms:
            try:
                Platform(platform)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
    
    # Handle default template logic
    if template_data.is_default is True:
        # Unset other default templates for the same platforms and category
        platforms_to_check = template_data.platforms or template.platforms
        category_to_check = template_data.category or template.category
        
        existing_defaults = db.query(ContentTemplate).filter(
            ContentTemplate.user_id == current_user.id,
            ContentTemplate.is_default == True,
            ContentTemplate.category == category_to_check,
            ContentTemplate.id != template_id
        ).all()
        
        for existing_template in existing_defaults:
            # Check if there's platform overlap
            if any(platform in existing_template.platforms for platform in platforms_to_check):
                existing_template.is_default = False
    
    # Update template
    update_data = template_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)
    
    template.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(template)
    
    logger.info(f"Updated content template {template.name} for user {current_user.id}")
    return template


@router.delete("/templates/{template_id}")
async def delete_content_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a content template"""
    
    template = db.query(ContentTemplate).filter(
        ContentTemplate.id == template_id,
        ContentTemplate.user_id == current_user.id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    if template.is_system_template:
        raise HTTPException(status_code=400, detail="Cannot delete system templates")
    
    template_name = template.name
    db.delete(template)
    db.commit()
    
    logger.info(f"Deleted content template {template_name} for user {current_user.id}")
    return {"message": f"Template '{template_name}' has been deleted"}


@router.post("/templates/{template_id}/use")
async def use_content_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a template as used (increment usage count)"""
    
    template = db.query(ContentTemplate).filter(
        ContentTemplate.id == template_id,
        (ContentTemplate.user_id == current_user.id) |
        (ContentTemplate.is_system_template == True)
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    template.usage_count += 1
    db.commit()
    
    return {"message": "Template usage recorded"}


def _create_default_preferences(platform: str, user_id: str) -> PlatformPreferences:
    """Create default preferences for a platform"""
    
    # Platform-specific defaults
    platform_defaults = {
        Platform.FACEBOOK.value: {
            "content_style": "professional",
            "hashtag_strategy": "branded",
            "max_hashtags": 5,
            "posting_schedule": {
                "monday": ["09:00", "15:00"],
                "tuesday": ["09:00", "15:00"],
                "wednesday": ["09:00", "15:00"],
                "thursday": ["09:00", "15:00"],
                "friday": ["09:00", "15:00"],
                "saturday": ["10:00"],
                "sunday": ["10:00"]
            },
            "platform_settings": {
                "page_posting": True,
                "story_posting": False,
                "marketplace_posting": False
            }
        },
        Platform.INSTAGRAM.value: {
            "content_style": "storytelling",
            "hashtag_strategy": "trending",
            "max_hashtags": 30,
            "posting_schedule": {
                "monday": ["11:00", "19:00"],
                "tuesday": ["11:00", "19:00"],
                "wednesday": ["11:00", "19:00"],
                "thursday": ["11:00", "19:00"],
                "friday": ["11:00", "19:00"],
                "saturday": ["12:00", "20:00"],
                "sunday": ["12:00", "20:00"]
            },
            "platform_settings": {
                "feed_posting": True,
                "story_posting": True,
                "reel_posting": False
            }
        },
        Platform.PINTEREST.value: {
            "content_style": "promotional",
            "hashtag_strategy": "category",
            "max_hashtags": 20,
            "posting_schedule": {
                "monday": ["08:00", "20:00"],
                "tuesday": ["08:00", "20:00"],
                "wednesday": ["08:00", "20:00"],
                "thursday": ["08:00", "20:00"],
                "friday": ["08:00", "20:00"],
                "saturday": ["08:00", "20:00"],
                "sunday": ["08:00", "20:00"]
            },
            "platform_settings": {
                "rich_pins": True,
                "board_auto_create": True
            }
        },
        Platform.ETSY.value: {
            "content_style": "professional",
            "hashtag_strategy": "category",
            "max_hashtags": 13,
            "posting_schedule": {
                "monday": ["10:00"],
                "tuesday": ["10:00"],
                "wednesday": ["10:00"],
                "thursday": ["10:00"],
                "friday": ["10:00"],
                "saturday": ["10:00"],
                "sunday": ["10:00"]
            },
            "platform_settings": {
                "auto_renew": True,
                "processing_time": "1-3 business days"
            }
        }
    }
    
    # Get platform-specific defaults or use general defaults
    defaults = platform_defaults.get(platform, {
        "content_style": "professional",
        "hashtag_strategy": "mixed",
        "max_hashtags": 10,
        "posting_schedule": {
            "monday": ["09:00"],
            "tuesday": ["09:00"],
            "wednesday": ["09:00"],
            "thursday": ["09:00"],
            "friday": ["09:00"],
            "saturday": ["10:00"],
            "sunday": ["10:00"]
        },
        "platform_settings": {}
    })
    
    return PlatformPreferences(
        user_id=user_id,
        platform=platform,
        enabled=True,
        auto_post=True,
        priority=0,
        content_style=defaults["content_style"],
        hashtag_strategy=defaults["hashtag_strategy"],
        max_hashtags=defaults["max_hashtags"],
        posting_schedule=defaults["posting_schedule"],
        timezone="UTC",
        auto_schedule=False,
        optimal_times_enabled=True,
        platform_settings=defaults["platform_settings"],
        title_format="{title}",
        description_format="{description}",
        include_branding=True,
        include_call_to_action=True,
        image_optimization=True,
        watermark_enabled=False
    )