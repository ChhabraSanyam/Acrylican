"""
OAuth Service

This module provides OAuth authentication flows for various social media and
marketplace platforms. It handles OAuth 2.0 and OAuth 1.0a flows, token
management, and secure credential storage.
"""

import asyncio
import base64
import json
import secrets
import urllib.parse
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urlencode, parse_qs

import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client, AsyncOAuth1Client
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import PlatformConnection, User
from .platform_integration import Platform, AuthenticationMethod, PlatformCredentials
import logging

logger = logging.getLogger(__name__)


class OAuthConfig:
    """OAuth configuration for different platforms"""
    
    PLATFORM_CONFIGS = {
        Platform.FACEBOOK: {
            "auth_method": AuthenticationMethod.OAUTH2,
            "client_id_env": "FACEBOOK_CLIENT_ID",
            "client_secret_env": "FACEBOOK_CLIENT_SECRET",
            "auth_url": "https://www.facebook.com/v18.0/dialog/oauth",
            "token_url": "https://graph.facebook.com/v18.0/oauth/access_token",
            "scope": "pages_manage_posts,pages_read_engagement,instagram_basic,instagram_content_publish",
            "redirect_uri": "/auth/facebook/callback"
        },
        Platform.INSTAGRAM: {
            "auth_method": AuthenticationMethod.OAUTH2,
            "client_id_env": "FACEBOOK_CLIENT_ID",  # Instagram uses Facebook OAuth
            "client_secret_env": "FACEBOOK_CLIENT_SECRET",
            "auth_url": "https://www.facebook.com/v18.0/dialog/oauth",
            "token_url": "https://graph.facebook.com/v18.0/oauth/access_token",
            "scope": "instagram_basic,instagram_content_publish",
            "redirect_uri": "/auth/instagram/callback"
        },
        Platform.ETSY: {
            "auth_method": AuthenticationMethod.OAUTH2,
            "client_id_env": "ETSY_CLIENT_ID",
            "client_secret_env": "ETSY_CLIENT_SECRET",
            "auth_url": "https://www.etsy.com/oauth/connect",
            "token_url": "https://api.etsy.com/v3/public/oauth/token",
            "scope": "listings_r listings_w profile_r",
            "redirect_uri": "/auth/etsy/callback"
        },
        Platform.PINTEREST: {
            "auth_method": AuthenticationMethod.OAUTH2,
            "client_id_env": "PINTEREST_CLIENT_ID",
            "client_secret_env": "PINTEREST_CLIENT_SECRET",
            "auth_url": "https://www.pinterest.com/oauth/",
            "token_url": "https://api.pinterest.com/v5/oauth/token",
            "scope": "boards:read,pins:read,pins:write",
            "redirect_uri": "/auth/pinterest/callback"
        },
        Platform.SHOPIFY: {
            "auth_method": AuthenticationMethod.OAUTH2,
            "client_id_env": "SHOPIFY_CLIENT_ID",
            "client_secret_env": "SHOPIFY_CLIENT_SECRET",
            "auth_url": "https://{shop}.myshopify.com/admin/oauth/authorize",
            "token_url": "https://{shop}.myshopify.com/admin/oauth/access_token",
            "scope": "write_products,read_products,write_inventory,read_inventory",
            "redirect_uri": "/auth/shopify/callback"
        }
    }


class TokenEncryption:
    """Handles encryption and decryption of OAuth tokens"""
    
    def __init__(self, encryption_key: Optional[str] = None):
        if encryption_key:
            self.fernet = Fernet(encryption_key.encode())
        else:
            # Generate a key for development - in production, this should come from environment
            self.fernet = Fernet(Fernet.generate_key())
    
    def encrypt_token(self, token: str) -> str:
        """Encrypt a token for secure storage"""
        if not token:
            return ""
        return self.fernet.encrypt(token.encode()).decode()
    
    def decrypt_token(self, encrypted_token: str) -> str:
        """Decrypt a token for use"""
        if not encrypted_token:
            return ""
        return self.fernet.decrypt(encrypted_token.encode()).decode()


class OAuthService:
    """Service for handling OAuth authentication flows"""
    
    def __init__(self, base_url: str = "http://localhost:8000", encryption_key: Optional[str] = None):
        self.base_url = base_url
        self.token_encryption = TokenEncryption(encryption_key)
        self.logger = logging.getLogger(__name__)
        
        # Store OAuth clients for reuse
        self._oauth_clients: Dict[str, Any] = {}
    
    def _get_platform_config(self, platform: Platform) -> Dict[str, Any]:
        """Get OAuth configuration for a platform"""
        config = OAuthConfig.PLATFORM_CONFIGS.get(platform)
        if not config:
            raise ValueError(f"OAuth configuration not found for platform: {platform.value}")
        return config
    
    def _get_oauth_client(self, platform: Platform, shop_domain: Optional[str] = None) -> AsyncOAuth2Client:
        """Get or create OAuth client for a platform"""
        import os
        
        config = self._get_platform_config(platform)
        
        client_id = os.getenv(config["client_id_env"])
        client_secret = os.getenv(config["client_secret_env"])
        
        if not client_id or not client_secret:
            raise ValueError(f"OAuth credentials not configured for {platform.value}")
        
        # Handle Shopify shop-specific URLs
        if platform == Platform.SHOPIFY and shop_domain:
            auth_url = config["auth_url"].format(shop=shop_domain)
            token_url = config["token_url"].format(shop=shop_domain)
        else:
            auth_url = config["auth_url"]
            token_url = config["token_url"]
        
        client_key = f"{platform.value}_{shop_domain or 'default'}"
        
        if client_key not in self._oauth_clients:
            self._oauth_clients[client_key] = AsyncOAuth2Client(
                client_id=client_id,
                client_secret=client_secret,
                token_endpoint=token_url
            )
        
        return self._oauth_clients[client_key]
    
    async def get_authorization_url(
        self, 
        platform: Platform, 
        user_id: str,
        shop_domain: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Generate OAuth authorization URL for a platform
        
        Args:
            platform: Platform to authenticate with
            user_id: User identifier
            shop_domain: Shop domain for Shopify (required for Shopify)
            
        Returns:
            Tuple of (authorization_url, state)
        """
        config = self._get_platform_config(platform)
        
        # Generate state parameter for CSRF protection
        state = secrets.token_urlsafe(32)
        
        # Store state in cache/session for validation (simplified for now)
        # In production, this should be stored in Redis or database
        
        redirect_uri = f"{self.base_url}{config['redirect_uri']}"
        
        # Handle Shopify shop-specific URLs
        if platform == Platform.SHOPIFY:
            if not shop_domain:
                raise ValueError("shop_domain is required for Shopify OAuth")
            auth_url = config["auth_url"].format(shop=shop_domain)
        else:
            auth_url = config["auth_url"]
        
        params = {
            "client_id": self._get_oauth_client(platform, shop_domain).client_id,
            "redirect_uri": redirect_uri,
            "scope": config["scope"],
            "response_type": "code",
            "state": f"{user_id}:{state}"  # Include user_id in state
        }
        
        authorization_url = f"{auth_url}?{urlencode(params)}"
        
        self.logger.info(f"Generated authorization URL for {platform.value} (user: {user_id})")
        
        return authorization_url, state
    
    async def handle_oauth_callback(
        self,
        platform: Platform,
        code: str,
        state: str,
        shop_domain: Optional[str] = None
    ) -> Optional[PlatformConnection]:
        """
        Handle OAuth callback and exchange code for tokens
        
        Args:
            platform: Platform being authenticated
            code: Authorization code from callback
            state: State parameter for CSRF validation
            shop_domain: Shop domain for Shopify
            
        Returns:
            PlatformConnection object if successful, None otherwise
        """
        try:
            # Extract user_id from state
            if ":" not in state:
                raise ValueError("Invalid state parameter")
            
            user_id, csrf_state = state.split(":", 1)
            
            # In production, validate CSRF state against stored value
            
            config = self._get_platform_config(platform)
            client = self._get_oauth_client(platform, shop_domain)
            
            redirect_uri = f"{self.base_url}{config['redirect_uri']}"
            
            # Exchange code for tokens
            token_response = await client.fetch_token(
                url=client.token_endpoint,
                code=code,
                redirect_uri=redirect_uri
            )
            
            access_token = token_response.get("access_token")
            refresh_token = token_response.get("refresh_token")
            expires_in = token_response.get("expires_in")
            
            if not access_token:
                raise ValueError("No access token received")
            
            # Calculate expiration time
            expires_at = None
            if expires_in:
                expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))
            
            # Get platform user info
            platform_user_info = await self._get_platform_user_info(
                platform, access_token, shop_domain
            )
            
            # Store connection in database
            db = next(get_db())
            try:
                connection = await self._store_platform_connection(
                    db=db,
                    user_id=user_id,
                    platform=platform,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_at=expires_at,
                    platform_user_info=platform_user_info,
                    shop_domain=shop_domain
                )
                
                self.logger.info(f"Successfully connected {platform.value} for user {user_id}")
                return connection
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"OAuth callback error for {platform.value}: {e}")
            return None
    
    async def _get_platform_user_info(
        self,
        platform: Platform,
        access_token: str,
        shop_domain: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get user information from platform API"""
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        try:
            async with httpx.AsyncClient() as client:
                if platform == Platform.FACEBOOK:
                    response = await client.get(
                        "https://graph.facebook.com/v18.0/me?fields=id,name,email",
                        headers=headers
                    )
                elif platform == Platform.INSTAGRAM:
                    response = await client.get(
                        "https://graph.facebook.com/v18.0/me?fields=id,username",
                        headers=headers
                    )
                elif platform == Platform.ETSY:
                    response = await client.get(
                        "https://openapi.etsy.com/v3/application/users/me",
                        headers=headers
                    )
                elif platform == Platform.PINTEREST:
                    response = await client.get(
                        "https://api.pinterest.com/v5/user_account",
                        headers=headers
                    )
                elif platform == Platform.SHOPIFY:
                    if not shop_domain:
                        raise ValueError("shop_domain required for Shopify")
                    response = await client.get(
                        f"https://{shop_domain}.myshopify.com/admin/api/2023-10/shop.json",
                        headers=headers
                    )
                else:
                    return {}
                
                if response.status_code == 200:
                    return response.json()
                else:
                    self.logger.warning(f"Failed to get user info from {platform.value}: {response.status_code}")
                    return {}
                    
        except Exception as e:
            self.logger.error(f"Error getting user info from {platform.value}: {e}")
            return {}
    
    async def _store_platform_connection(
        self,
        db: Session,
        user_id: str,
        platform: Platform,
        access_token: str,
        refresh_token: Optional[str],
        expires_at: Optional[datetime],
        platform_user_info: Dict[str, Any],
        shop_domain: Optional[str] = None
    ) -> PlatformConnection:
        """Store platform connection in database"""
        
        # Check if connection already exists
        existing_connection = db.query(PlatformConnection).filter(
            PlatformConnection.user_id == user_id,
            PlatformConnection.platform == platform.value
        ).first()
        
        if existing_connection:
            # Update existing connection
            existing_connection.access_token = self.token_encryption.encrypt_token(access_token)
            if refresh_token:
                existing_connection.refresh_token = self.token_encryption.encrypt_token(refresh_token)
            existing_connection.expires_at = expires_at
            existing_connection.platform_user_id = platform_user_info.get("id")
            existing_connection.platform_username = platform_user_info.get("name") or platform_user_info.get("username")
            existing_connection.platform_data = platform_user_info
            existing_connection.is_active = True
            existing_connection.last_validated_at = datetime.utcnow()
            existing_connection.validation_error = None
            existing_connection.updated_at = datetime.utcnow()
            
            if shop_domain:
                existing_connection.platform_data = {
                    **platform_user_info,
                    "shop_domain": shop_domain
                }
            
            connection = existing_connection
        else:
            # Create new connection
            platform_data = platform_user_info.copy()
            if shop_domain:
                platform_data["shop_domain"] = shop_domain
            
            connection = PlatformConnection(
                user_id=user_id,
                platform=platform.value,
                integration_type="api",
                auth_method=AuthenticationMethod.OAUTH2.value,
                access_token=self.token_encryption.encrypt_token(access_token),
                refresh_token=self.token_encryption.encrypt_token(refresh_token) if refresh_token else None,
                expires_at=expires_at,
                platform_user_id=platform_user_info.get("id"),
                platform_username=platform_user_info.get("name") or platform_user_info.get("username"),
                platform_data=platform_data,
                is_active=True,
                last_validated_at=datetime.utcnow()
            )
            
            db.add(connection)
        
        db.commit()
        db.refresh(connection)
        
        return connection
    
    async def refresh_access_token(
        self,
        connection: PlatformConnection,
        db: Session
    ) -> bool:
        """
        Refresh access token for a platform connection
        
        Args:
            connection: Platform connection to refresh
            db: Database session
            
        Returns:
            True if refresh successful, False otherwise
        """
        try:
            platform = Platform(connection.platform)
            
            if not connection.refresh_token:
                self.logger.warning(f"No refresh token available for {platform.value}")
                return False
            
            refresh_token = self.token_encryption.decrypt_token(connection.refresh_token)
            
            config = self._get_platform_config(platform)
            shop_domain = None
            
            if platform == Platform.SHOPIFY and connection.platform_data:
                shop_domain = connection.platform_data.get("shop_domain")
            
            client = self._get_oauth_client(platform, shop_domain)
            
            # Refresh token
            token_response = await client.refresh_token(
                url=client.token_endpoint,
                refresh_token=refresh_token
            )
            
            new_access_token = token_response.get("access_token")
            new_refresh_token = token_response.get("refresh_token", refresh_token)
            expires_in = token_response.get("expires_in")
            
            if not new_access_token:
                raise ValueError("No access token received from refresh")
            
            # Update connection
            connection.access_token = self.token_encryption.encrypt_token(new_access_token)
            connection.refresh_token = self.token_encryption.encrypt_token(new_refresh_token)
            
            if expires_in:
                connection.expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))
            
            connection.last_validated_at = datetime.utcnow()
            connection.validation_error = None
            connection.updated_at = datetime.utcnow()
            
            db.commit()
            
            self.logger.info(f"Successfully refreshed token for {platform.value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Token refresh failed for {connection.platform}: {e}")
            
            # Update connection with error
            connection.validation_error = str(e)
            connection.updated_at = datetime.utcnow()
            db.commit()
            
            return False
    
    async def validate_connection(
        self,
        connection: PlatformConnection,
        db: Session
    ) -> bool:
        """
        Validate that a platform connection is still active
        
        Args:
            connection: Platform connection to validate
            db: Database session
            
        Returns:
            True if connection is valid, False otherwise
        """
        try:
            platform = Platform(connection.platform)
            
            # Check if token is expired
            if connection.expires_at and connection.expires_at <= datetime.utcnow():
                # Try to refresh token
                if await self.refresh_access_token(connection, db):
                    # Refresh successful, connection is valid
                    return True
                else:
                    # Refresh failed, connection is invalid
                    connection.is_active = False
                    connection.validation_error = "Token expired and refresh failed"
                    db.commit()
                    return False
            
            # Test API call to validate token
            access_token = self.token_encryption.decrypt_token(connection.access_token)
            shop_domain = None
            
            if platform == Platform.SHOPIFY and connection.platform_data:
                shop_domain = connection.platform_data.get("shop_domain")
            
            user_info = await self._get_platform_user_info(platform, access_token, shop_domain)
            
            if user_info:
                # Update last validated time
                connection.last_validated_at = datetime.utcnow()
                connection.validation_error = None
                db.commit()
                return True
            else:
                # API call failed, connection might be invalid
                connection.validation_error = "API validation failed"
                db.commit()
                return False
                
        except Exception as e:
            self.logger.error(f"Connection validation failed for {connection.platform}: {e}")
            
            connection.validation_error = str(e)
            connection.updated_at = datetime.utcnow()
            db.commit()
            
            return False
    
    async def disconnect_platform(
        self,
        user_id: str,
        platform: Platform,
        db: Session
    ) -> bool:
        """
        Disconnect a platform for a user
        
        Args:
            user_id: User identifier
            platform: Platform to disconnect
            db: Database session
            
        Returns:
            True if disconnection successful
        """
        try:
            connection = db.query(PlatformConnection).filter(
                PlatformConnection.user_id == user_id,
                PlatformConnection.platform == platform.value
            ).first()
            
            if connection:
                # Mark as inactive instead of deleting for audit purposes
                connection.is_active = False
                connection.updated_at = datetime.utcnow()
                db.commit()
                
                self.logger.info(f"Disconnected {platform.value} for user {user_id}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Disconnection failed for {platform.value}: {e}")
            return False
    
    async def get_user_connections(
        self,
        user_id: str,
        db: Session,
        active_only: bool = True
    ) -> List[PlatformConnection]:
        """
        Get all platform connections for a user
        
        Args:
            user_id: User identifier
            db: Database session
            active_only: Only return active connections
            
        Returns:
            List of platform connections
        """
        query = db.query(PlatformConnection).filter(
            PlatformConnection.user_id == user_id
        )
        
        if active_only:
            query = query.filter(PlatformConnection.is_active == True)
        
        return query.all()
    
    def get_decrypted_credentials(self, connection: PlatformConnection) -> PlatformCredentials:
        """
        Get decrypted credentials for a platform connection
        
        Args:
            connection: Platform connection
            
        Returns:
            PlatformCredentials with decrypted tokens
        """
        return PlatformCredentials(
            platform=Platform(connection.platform),
            auth_method=AuthenticationMethod(connection.auth_method),
            access_token=self.token_encryption.decrypt_token(connection.access_token),
            refresh_token=self.token_encryption.decrypt_token(connection.refresh_token) if connection.refresh_token else None,
            expires_at=connection.expires_at
        )


# Global service instance
oauth_service = OAuthService()


def get_oauth_service() -> OAuthService:
    """Get the global OAuth service instance"""
    return oauth_service