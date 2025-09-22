"""
Platform Management Routes

This module provides API endpoints for managing platform connections,
including setup wizards, connection testing, and platform preferences.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from ..database import get_db
from ..dependencies import get_current_user
from ..models import User, PlatformConnection
from ..services.platform_service import get_platform_service, PlatformService
from ..services.oauth_service import get_oauth_service, OAuthService
from ..services.platform_integration import Platform, IntegrationType, AuthenticationMethod
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/platforms", tags=["platform-management"])


class PlatformInfo(BaseModel):
    """Platform information model"""
    platform: str
    name: str
    description: str
    integration_type: str
    auth_method: str
    enabled: bool
    connected: bool
    connection_status: Optional[str] = None
    platform_username: Optional[str] = None
    connected_at: Optional[str] = None
    last_validated_at: Optional[str] = None
    expires_at: Optional[str] = None
    validation_error: Optional[str] = None
    setup_required: bool = False
    setup_instructions: Optional[str] = None


class PlatformConnectionRequest(BaseModel):
    """Request model for platform connection"""
    platform: str
    credentials: Optional[Dict[str, Any]] = None
    shop_domain: Optional[str] = None  # For Shopify


class PlatformPreferences(BaseModel):
    """Platform preferences model"""
    platform: str
    enabled: bool
    auto_post: bool = True
    default_template: Optional[str] = None
    posting_schedule: Optional[Dict[str, Any]] = None


class ConnectionTestResult(BaseModel):
    """Connection test result model"""
    platform: str
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None


@router.get("/", response_model=List[PlatformInfo])
async def get_all_platforms(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    platform_service: PlatformService = Depends(get_platform_service)
):
    """Get information about all available platforms"""
    
    # Get all platform configurations
    platform_configs = platform_service.get_all_platform_info()
    
    # Get user's connections
    user_connections = {}
    connections = db.query(PlatformConnection).filter(
        PlatformConnection.user_id == current_user.id
    ).all()
    
    for conn in connections:
        user_connections[conn.platform] = conn
    
    # Build platform info list
    platforms = []
    
    platform_names = {
        Platform.FACEBOOK.value: "Facebook",
        Platform.INSTAGRAM.value: "Instagram", 
        Platform.FACEBOOK_MARKETPLACE.value: "Facebook Marketplace",
        Platform.ETSY.value: "Etsy",
        Platform.PINTEREST.value: "Pinterest",
        Platform.SHOPIFY.value: "Shopify"
    }
    
    platform_descriptions = {
        Platform.FACEBOOK.value: "Connect to Facebook for posting and engagement metrics",
        Platform.INSTAGRAM.value: "Connect to Instagram Business for content publishing",
        Platform.FACEBOOK_MARKETPLACE.value: "List products on Facebook Marketplace",
        Platform.ETSY.value: "Connect to Etsy for marketplace listings",
        Platform.PINTEREST.value: "Connect to Pinterest for pin creation and management",
        Platform.SHOPIFY.value: "Connect to Shopify store for product management"
    }
    
    setup_instructions = {
        Platform.FACEBOOK.value: "Click 'Connect' to authorize via Facebook OAuth",
        Platform.INSTAGRAM.value: "Click 'Connect' to authorize via Facebook OAuth (requires Business account)",
        Platform.FACEBOOK_MARKETPLACE.value: "Connect Facebook first, then enable Marketplace posting",
        Platform.ETSY.value: "Click 'Connect' to authorize via Etsy OAuth",
        Platform.PINTEREST.value: "Click 'Connect' to authorize via Pinterest Business OAuth",
        Platform.SHOPIFY.value: "Enter your shop domain and click 'Connect' to authorize via Shopify OAuth"
    }
    
    for platform_enum in Platform:
        platform_key = platform_enum.value
        config = platform_configs.get(platform_key, {})
        connection = user_connections.get(platform_key)
        
        # Determine if setup is required
        setup_required = False
        if not connection:
            setup_required = True
        elif not connection.is_active:
            setup_required = True
        
        platform_info = PlatformInfo(
            platform=platform_key,
            name=platform_names.get(platform_key, platform_key.title()),
            description=platform_descriptions.get(platform_key, f"Connect to {platform_key}"),
            integration_type=config.get("integration_type", "unknown"),
            auth_method=config.get("auth_method", "unknown"),
            enabled=config.get("enabled", True),
            connected=connection is not None and connection.is_active,
            connection_status="active" if connection and connection.is_active else "inactive" if connection else "not_connected",
            platform_username=connection.platform_username if connection else None,
            connected_at=connection.connected_at.isoformat() if connection and connection.connected_at else None,
            last_validated_at=connection.last_validated_at.isoformat() if connection and connection.last_validated_at else None,
            expires_at=connection.expires_at.isoformat() if connection and connection.expires_at else None,
            validation_error=connection.validation_error if connection else None,
            setup_required=setup_required,
            setup_instructions=setup_instructions.get(platform_key)
        )
        
        platforms.append(platform_info)
    
    return platforms


@router.get("/{platform}", response_model=PlatformInfo)
async def get_platform_info(
    platform: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    platform_service: PlatformService = Depends(get_platform_service)
):
    """Get detailed information about a specific platform"""
    
    try:
        platform_enum = Platform(platform)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
    
    # Get platform configuration
    config = platform_service.get_platform_info(platform_enum)
    if not config:
        raise HTTPException(status_code=404, detail=f"Platform {platform} not found")
    
    # Get user's connection
    connection = db.query(PlatformConnection).filter(
        PlatformConnection.user_id == current_user.id,
        PlatformConnection.platform == platform
    ).first()
    
    platform_names = {
        Platform.FACEBOOK.value: "Facebook",
        Platform.INSTAGRAM.value: "Instagram",
        Platform.FACEBOOK_MARKETPLACE.value: "Facebook Marketplace", 
        Platform.ETSY.value: "Etsy",
        Platform.PINTEREST.value: "Pinterest",
        Platform.SHOPIFY.value: "Shopify"
    }
    
    platform_descriptions = {
        Platform.FACEBOOK.value: "Connect to Facebook for posting and engagement metrics",
        Platform.INSTAGRAM.value: "Connect to Instagram Business for content publishing",
        Platform.FACEBOOK_MARKETPLACE.value: "List products on Facebook Marketplace",
        Platform.ETSY.value: "Connect to Etsy for marketplace listings", 
        Platform.PINTEREST.value: "Connect to Pinterest for pin creation and management",
        Platform.SHOPIFY.value: "Connect to Shopify store for product management"
    }
    
    setup_instructions = {
        Platform.FACEBOOK.value: "Click 'Connect' to authorize via Facebook OAuth",
        Platform.INSTAGRAM.value: "Click 'Connect' to authorize via Facebook OAuth (requires Business account)",
        Platform.FACEBOOK_MARKETPLACE.value: "Connect Facebook first, then enable Marketplace posting",
        Platform.ETSY.value: "Click 'Connect' to authorize via Etsy OAuth",
        Platform.PINTEREST.value: "Click 'Connect' to authorize via Pinterest Business OAuth",
        Platform.SHOPIFY.value: "Enter your shop domain and click 'Connect' to authorize via Shopify OAuth"
    }
    
    # Determine if setup is required
    setup_required = False
    if not connection:
        setup_required = True
    elif not connection.is_active:
        setup_required = True
    
    return PlatformInfo(
        platform=platform,
        name=platform_names.get(platform, platform.title()),
        description=platform_descriptions.get(platform, f"Connect to {platform}"),
        integration_type=config["integration_type"],
        auth_method=config["auth_method"],
        enabled=config["enabled"],
        connected=connection is not None and connection.is_active,
        connection_status="active" if connection and connection.is_active else "inactive" if connection else "not_connected",
        platform_username=connection.platform_username if connection else None,
        connected_at=connection.connected_at.isoformat() if connection and connection.connected_at else None,
        last_validated_at=connection.last_validated_at.isoformat() if connection and connection.last_validated_at else None,
        expires_at=connection.expires_at.isoformat() if connection and connection.expires_at else None,
        validation_error=connection.validation_error if connection else None,
        setup_required=setup_required,
        setup_instructions=setup_instructions.get(platform)
    )


@router.post("/{platform}/test", response_model=ConnectionTestResult)
async def test_platform_connection(
    platform: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    platform_service: PlatformService = Depends(get_platform_service)
):
    """Test a platform connection"""
    
    try:
        platform_enum = Platform(platform)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
    
    # Check if connection exists
    connection = db.query(PlatformConnection).filter(
        PlatformConnection.user_id == current_user.id,
        PlatformConnection.platform == platform,
        PlatformConnection.is_active == True
    ).first()
    
    if not connection:
        return ConnectionTestResult(
            platform=platform,
            success=False,
            message="No active connection found for this platform"
        )
    
    # Test the connection
    try:
        is_valid = await platform_service.validate_platform_connection(
            platform_enum,
            current_user.id
        )
        
        if is_valid:
            return ConnectionTestResult(
                platform=platform,
                success=True,
                message="Connection is working properly",
                details={
                    "last_validated": connection.last_validated_at.isoformat() if connection.last_validated_at else None,
                    "platform_username": connection.platform_username
                }
            )
        else:
            return ConnectionTestResult(
                platform=platform,
                success=False,
                message=connection.validation_error or "Connection validation failed",
                details={
                    "last_validated": connection.last_validated_at.isoformat() if connection.last_validated_at else None
                }
            )
            
    except Exception as e:
        logger.error(f"Connection test failed for {platform}: {e}")
        return ConnectionTestResult(
            platform=platform,
            success=False,
            message=f"Connection test failed: {str(e)}"
        )


@router.post("/{platform}/enable")
async def enable_platform(
    platform: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Enable a platform for posting"""
    
    try:
        platform_enum = Platform(platform)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
    
    # Check if connection exists
    connection = db.query(PlatformConnection).filter(
        PlatformConnection.user_id == current_user.id,
        PlatformConnection.platform == platform
    ).first()
    
    if not connection:
        raise HTTPException(
            status_code=404, 
            detail=f"No connection found for {platform}. Please connect first."
        )
    
    # Enable the connection
    connection.is_active = True
    db.commit()
    
    logger.info(f"Enabled platform {platform} for user {current_user.id}")
    
    return {"message": f"Successfully enabled {platform}"}


@router.post("/{platform}/disable")
async def disable_platform(
    platform: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disable a platform for posting"""
    
    try:
        platform_enum = Platform(platform)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
    
    # Check if connection exists
    connection = db.query(PlatformConnection).filter(
        PlatformConnection.user_id == current_user.id,
        PlatformConnection.platform == platform
    ).first()
    
    if not connection:
        raise HTTPException(status_code=404, detail=f"No connection found for {platform}")
    
    # Disable the connection
    connection.is_active = False
    db.commit()
    
    logger.info(f"Disabled platform {platform} for user {current_user.id}")
    
    return {"message": f"Successfully disabled {platform}"}


@router.get("/{platform}/setup-wizard")
async def get_setup_wizard_info(
    platform: str,
    current_user: User = Depends(get_current_user),
    platform_service: PlatformService = Depends(get_platform_service)
):
    """Get setup wizard information for a platform"""
    
    try:
        platform_enum = Platform(platform)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
    
    config = platform_service.get_platform_info(platform_enum)
    if not config:
        raise HTTPException(status_code=404, detail=f"Platform {platform} not found")
    
    # Define setup steps for each platform
    setup_steps = {
        Platform.FACEBOOK.value: [
            {
                "step": 1,
                "title": "Facebook Authorization",
                "description": "Authorize the application to access your Facebook account",
                "action": "oauth",
                "required_fields": []
            }
        ],
        Platform.INSTAGRAM.value: [
            {
                "step": 1,
                "title": "Instagram Business Account",
                "description": "Ensure you have an Instagram Business account connected to a Facebook Page",
                "action": "info",
                "required_fields": []
            },
            {
                "step": 2,
                "title": "Facebook Authorization",
                "description": "Authorize via Facebook to access your Instagram Business account",
                "action": "oauth",
                "required_fields": []
            }
        ],
        Platform.ETSY.value: [
            {
                "step": 1,
                "title": "Etsy Shop",
                "description": "Ensure you have an active Etsy shop",
                "action": "info",
                "required_fields": []
            },
            {
                "step": 2,
                "title": "Etsy Authorization",
                "description": "Authorize the application to manage your Etsy listings",
                "action": "oauth",
                "required_fields": []
            }
        ],
        Platform.PINTEREST.value: [
            {
                "step": 1,
                "title": "Pinterest Business Account",
                "description": "Convert to or create a Pinterest Business account",
                "action": "info",
                "required_fields": []
            },
            {
                "step": 2,
                "title": "Pinterest Authorization",
                "description": "Authorize the application to create pins and manage boards",
                "action": "oauth",
                "required_fields": []
            }
        ],
        Platform.SHOPIFY.value: [
            {
                "step": 1,
                "title": "Shop Domain",
                "description": "Enter your Shopify shop domain",
                "action": "form",
                "required_fields": [
                    {
                        "name": "shop_domain",
                        "label": "Shop Domain",
                        "type": "text",
                        "placeholder": "your-shop-name",
                        "help": "Enter just the shop name (without .myshopify.com)"
                    }
                ]
            },
            {
                "step": 2,
                "title": "Shopify Authorization",
                "description": "Authorize the application to manage your Shopify products",
                "action": "oauth",
                "required_fields": []
            }
        ]
    }
    
    return {
        "platform": platform,
        "platform_name": config.get("platform", platform).title(),
        "integration_type": config["integration_type"],
        "auth_method": config["auth_method"],
        "steps": setup_steps.get(platform, [])
    }


@router.post("/test-all")
async def test_all_connections(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    platform_service: PlatformService = Depends(get_platform_service)
):
    """Test all platform connections for the current user"""
    
    connections = db.query(PlatformConnection).filter(
        PlatformConnection.user_id == current_user.id,
        PlatformConnection.is_active == True
    ).all()
    
    results = []
    
    for connection in connections:
        try:
            platform_enum = Platform(connection.platform)
            is_valid = await platform_service.validate_platform_connection(
                platform_enum,
                current_user.id
            )
            
            results.append(ConnectionTestResult(
                platform=connection.platform,
                success=is_valid,
                message="Connection is working properly" if is_valid else (
                    connection.validation_error or "Connection validation failed"
                ),
                details={
                    "last_validated": connection.last_validated_at.isoformat() if connection.last_validated_at else None,
                    "platform_username": connection.platform_username
                }
            ))
            
        except Exception as e:
            logger.error(f"Connection test failed for {connection.platform}: {e}")
            results.append(ConnectionTestResult(
                platform=connection.platform,
                success=False,
                message=f"Connection test failed: {str(e)}"
            ))
    
    return {"results": results}