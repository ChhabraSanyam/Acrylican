"""
OAuth Authentication Routes

This module provides API endpoints for OAuth authentication flows with
various social media and marketplace platforms.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from ..dependencies import get_current_user
from ..models import User, PlatformConnection
from ..services.oauth_service import get_oauth_service, OAuthService
from ..services.platform_integration import Platform
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["oauth"])


class PlatformConnectionResponse(BaseModel):
    """Response model for platform connection"""
    id: str
    platform: str
    platform_username: Optional[str]
    is_active: bool
    connected_at: str
    last_validated_at: Optional[str]
    expires_at: Optional[str]
    
    class Config:
        from_attributes = True


class AuthorizationUrlResponse(BaseModel):
    """Response model for authorization URL"""
    authorization_url: str
    state: str


@router.get("/platforms")
async def get_supported_platforms():
    """Get list of supported OAuth platforms"""
    return {
        "platforms": [
            {
                "id": Platform.FACEBOOK.value,
                "name": "Facebook",
                "description": "Connect to Facebook for posting and engagement metrics"
            },
            {
                "id": Platform.INSTAGRAM.value,
                "name": "Instagram",
                "description": "Connect to Instagram Business for content publishing"
            },
            {
                "id": Platform.ETSY.value,
                "name": "Etsy",
                "description": "Connect to Etsy for marketplace listings"
            },
            {
                "id": Platform.PINTEREST.value,
                "name": "Pinterest",
                "description": "Connect to Pinterest for pin creation and management"
            },
            {
                "id": Platform.SHOPIFY.value,
                "name": "Shopify",
                "description": "Connect to Shopify store for product management"
            }
        ]
    }


@router.get("/connections", response_model=List[PlatformConnectionResponse])
async def get_user_connections(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    oauth_service: OAuthService = Depends(get_oauth_service)
):
    """Get all platform connections for the current user"""
    connections = await oauth_service.get_user_connections(current_user.id, db)
    
    return [
        PlatformConnectionResponse(
            id=conn.id,
            platform=conn.platform,
            platform_username=conn.platform_username,
            is_active=conn.is_active,
            connected_at=conn.connected_at.isoformat(),
            last_validated_at=conn.last_validated_at.isoformat() if conn.last_validated_at else None,
            expires_at=conn.expires_at.isoformat() if conn.expires_at else None
        )
        for conn in connections
    ]


@router.post("/{platform}/connect", response_model=AuthorizationUrlResponse)
async def initiate_oauth_flow(
    platform: str,
    shop_domain: Optional[str] = Query(None, description="Required for Shopify connections"),
    current_user: User = Depends(get_current_user),
    oauth_service: OAuthService = Depends(get_oauth_service)
):
    """Initiate OAuth flow for a platform"""
    try:
        platform_enum = Platform(platform)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
    
    # Validate Shopify requirements
    if platform_enum == Platform.SHOPIFY and not shop_domain:
        raise HTTPException(
            status_code=400, 
            detail="shop_domain parameter is required for Shopify connections"
        )
    
    try:
        authorization_url, state = await oauth_service.get_authorization_url(
            platform_enum, 
            current_user.id,
            shop_domain
        )
        
        return AuthorizationUrlResponse(
            authorization_url=authorization_url,
            state=state
        )
        
    except Exception as e:
        logger.error(f"Failed to initiate OAuth flow for {platform}: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate OAuth flow")


@router.get("/{platform}/callback")
async def oauth_callback(
    platform: str,
    code: str = Query(..., description="Authorization code from OAuth provider"),
    state: str = Query(..., description="State parameter for CSRF protection"),
    shop: Optional[str] = Query(None, description="Shop domain for Shopify"),
    db: Session = Depends(get_db),
    oauth_service: OAuthService = Depends(get_oauth_service)
):
    """Handle OAuth callback from platform"""
    try:
        platform_enum = Platform(platform)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
    
    try:
        connection = await oauth_service.handle_oauth_callback(
            platform_enum,
            code,
            state,
            shop
        )
        
        if connection:
            # Redirect to frontend success page
            return RedirectResponse(
                url=f"/dashboard?connected={platform}&status=success",
                status_code=302
            )
        else:
            # Redirect to frontend error page
            return RedirectResponse(
                url=f"/dashboard?connected={platform}&status=error",
                status_code=302
            )
            
    except Exception as e:
        logger.error(f"OAuth callback failed for {platform}: {e}")
        return RedirectResponse(
            url=f"/dashboard?connected={platform}&status=error&message={str(e)}",
            status_code=302
        )


@router.post("/{platform}/disconnect")
async def disconnect_platform(
    platform: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    oauth_service: OAuthService = Depends(get_oauth_service)
):
    """Disconnect from a platform"""
    try:
        platform_enum = Platform(platform)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
    
    success = await oauth_service.disconnect_platform(
        current_user.id,
        platform_enum,
        db
    )
    
    if success:
        return {"message": f"Successfully disconnected from {platform}"}
    else:
        raise HTTPException(status_code=500, detail=f"Failed to disconnect from {platform}")


@router.post("/{platform}/validate")
async def validate_platform_connection(
    platform: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    oauth_service: OAuthService = Depends(get_oauth_service)
):
    """Validate a platform connection"""
    try:
        platform_enum = Platform(platform)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
    
    # Get connection
    connection = db.query(PlatformConnection).filter(
        PlatformConnection.user_id == current_user.id,
        PlatformConnection.platform == platform_enum.value,
        PlatformConnection.is_active == True
    ).first()
    
    if not connection:
        raise HTTPException(status_code=404, detail=f"No active connection found for {platform}")
    
    is_valid = await oauth_service.validate_connection(connection, db)
    
    return {
        "platform": platform,
        "is_valid": is_valid,
        "last_validated_at": connection.last_validated_at.isoformat() if connection.last_validated_at else None,
        "validation_error": connection.validation_error
    }


@router.post("/validate-all")
async def validate_all_connections(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    oauth_service: OAuthService = Depends(get_oauth_service)
):
    """Validate all platform connections for the current user"""
    connections = await oauth_service.get_user_connections(current_user.id, db)
    
    results = []
    for connection in connections:
        is_valid = await oauth_service.validate_connection(connection, db)
        results.append({
            "platform": connection.platform,
            "is_valid": is_valid,
            "last_validated_at": connection.last_validated_at.isoformat() if connection.last_validated_at else None,
            "validation_error": connection.validation_error
        })
    
    return {"results": results}


@router.get("/{platform}/status")
async def get_platform_status(
    platform: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get connection status for a specific platform"""
    try:
        platform_enum = Platform(platform)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
    
    connection = db.query(PlatformConnection).filter(
        PlatformConnection.user_id == current_user.id,
        PlatformConnection.platform == platform_enum.value
    ).first()
    
    if not connection:
        return {
            "platform": platform,
            "connected": False,
            "status": "not_connected"
        }
    
    return {
        "platform": platform,
        "connected": connection.is_active,
        "status": "active" if connection.is_active else "inactive",
        "platform_username": connection.platform_username,
        "connected_at": connection.connected_at.isoformat(),
        "last_validated_at": connection.last_validated_at.isoformat() if connection.last_validated_at else None,
        "expires_at": connection.expires_at.isoformat() if connection.expires_at else None,
        "validation_error": connection.validation_error
    }