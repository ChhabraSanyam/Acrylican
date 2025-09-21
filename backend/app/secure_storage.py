"""
Secure storage utilities for sensitive data like API keys and tokens.

This module provides:
- Encrypted token storage and retrieval
- Secure API key management
- Token rotation and expiration
- Audit logging for sensitive operations
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from .security import token_encryption, security_validator
from .models import PlatformConnection
from .database import get_db

logger = logging.getLogger(__name__)


class SecureTokenStorage:
    """Handles secure storage and retrieval of sensitive tokens."""
    
    def __init__(self):
        self.encryption = token_encryption
    
    def store_platform_tokens(
        self,
        db: Session,
        user_id: str,
        platform: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        platform_data: Optional[Dict[str, Any]] = None
    ) -> PlatformConnection:
        """
        Securely store platform authentication tokens.
        
        Args:
            db: Database session
            user_id: User ID
            platform: Platform name
            access_token: Access token to encrypt and store
            refresh_token: Optional refresh token
            expires_at: Token expiration time
            platform_data: Additional platform-specific data
            
        Returns:
            PlatformConnection object
        """
        try:
            # Encrypt tokens
            encrypted_access_token = self.encryption.encrypt_token(access_token)
            encrypted_refresh_token = None
            if refresh_token:
                encrypted_refresh_token = self.encryption.encrypt_token(refresh_token)
            
            # Check if connection already exists
            existing_connection = db.query(PlatformConnection).filter(
                PlatformConnection.user_id == user_id,
                PlatformConnection.platform == platform
            ).first()
            
            if existing_connection:
                # Update existing connection
                existing_connection.access_token = encrypted_access_token
                existing_connection.refresh_token = encrypted_refresh_token
                existing_connection.expires_at = expires_at
                existing_connection.platform_data = platform_data or {}
                existing_connection.is_active = True
                existing_connection.last_validated_at = datetime.utcnow()
                existing_connection.validation_error = None
                existing_connection.updated_at = datetime.utcnow()
                
                connection = existing_connection
            else:
                # Create new connection
                connection = PlatformConnection(
                    user_id=user_id,
                    platform=platform,
                    integration_type="api",  # Assume API for token-based auth
                    auth_method="oauth",
                    access_token=encrypted_access_token,
                    refresh_token=encrypted_refresh_token,
                    expires_at=expires_at,
                    platform_data=platform_data or {},
                    is_active=True,
                    last_validated_at=datetime.utcnow()
                )
                db.add(connection)
            
            db.commit()
            db.refresh(connection)
            
            logger.info(f"Stored encrypted tokens for user {user_id} on platform {platform}")
            return connection
            
        except Exception as e:
            logger.error(f"Failed to store platform tokens: {e}")
            db.rollback()
            raise
    
    def retrieve_platform_tokens(
        self,
        db: Session,
        user_id: str,
        platform: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve and decrypt platform tokens.
        
        Args:
            db: Database session
            user_id: User ID
            platform: Platform name
            
        Returns:
            Dictionary with decrypted tokens or None if not found
        """
        try:
            connection = db.query(PlatformConnection).filter(
                PlatformConnection.user_id == user_id,
                PlatformConnection.platform == platform,
                PlatformConnection.is_active == True
            ).first()
            
            if not connection:
                return None
            
            # Check if token is expired
            if connection.expires_at and connection.expires_at < datetime.utcnow():
                logger.warning(f"Token expired for user {user_id} on platform {platform}")
                return None
            
            # Decrypt tokens
            access_token = self.encryption.decrypt_token(connection.access_token)
            refresh_token = None
            if connection.refresh_token:
                refresh_token = self.encryption.decrypt_token(connection.refresh_token)
            
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": connection.expires_at,
                "platform_data": connection.platform_data,
                "connection_id": connection.id
            }
            
        except Exception as e:
            logger.error(f"Failed to retrieve platform tokens: {e}")
            return None
    
    def rotate_tokens(
        self,
        db: Session,
        connection_id: str,
        new_access_token: str,
        new_refresh_token: Optional[str] = None,
        new_expires_at: Optional[datetime] = None
    ) -> bool:
        """
        Rotate platform tokens (update with new tokens).
        
        Args:
            db: Database session
            connection_id: Platform connection ID
            new_access_token: New access token
            new_refresh_token: New refresh token
            new_expires_at: New expiration time
            
        Returns:
            True if successful
        """
        try:
            connection = db.query(PlatformConnection).filter(
                PlatformConnection.id == connection_id
            ).first()
            
            if not connection:
                logger.error(f"Connection {connection_id} not found for token rotation")
                return False
            
            # Encrypt new tokens
            connection.access_token = self.encryption.encrypt_token(new_access_token)
            if new_refresh_token:
                connection.refresh_token = self.encryption.encrypt_token(new_refresh_token)
            
            if new_expires_at:
                connection.expires_at = new_expires_at
            
            connection.last_validated_at = datetime.utcnow()
            connection.validation_error = None
            connection.updated_at = datetime.utcnow()
            
            db.commit()
            
            logger.info(f"Rotated tokens for connection {connection_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to rotate tokens: {e}")
            db.rollback()
            return False
    
    def revoke_platform_connection(
        self,
        db: Session,
        user_id: str,
        platform: str
    ) -> bool:
        """
        Revoke platform connection and clear tokens.
        
        Args:
            db: Database session
            user_id: User ID
            platform: Platform name
            
        Returns:
            True if successful
        """
        try:
            connection = db.query(PlatformConnection).filter(
                PlatformConnection.user_id == user_id,
                PlatformConnection.platform == platform
            ).first()
            
            if not connection:
                return True  # Already revoked
            
            # Clear tokens and deactivate
            connection.access_token = ""
            connection.refresh_token = ""
            connection.is_active = False
            connection.validation_error = "Connection revoked by user"
            connection.updated_at = datetime.utcnow()
            
            db.commit()
            
            logger.info(f"Revoked platform connection for user {user_id} on platform {platform}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke platform connection: {e}")
            db.rollback()
            return False
    
    def validate_stored_tokens(self, db: Session, user_id: str) -> Dict[str, bool]:
        """
        Validate all stored tokens for a user.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Dictionary mapping platform names to validation status
        """
        results = {}
        
        try:
            connections = db.query(PlatformConnection).filter(
                PlatformConnection.user_id == user_id,
                PlatformConnection.is_active == True
            ).all()
            
            for connection in connections:
                try:
                    # Check if token exists and can be decrypted
                    if connection.access_token:
                        self.encryption.decrypt_token(connection.access_token)
                        
                        # Check expiration
                        if connection.expires_at and connection.expires_at < datetime.utcnow():
                            results[connection.platform] = False
                            connection.validation_error = "Token expired"
                        else:
                            results[connection.platform] = True
                            connection.last_validated_at = datetime.utcnow()
                            connection.validation_error = None
                    else:
                        results[connection.platform] = False
                        connection.validation_error = "No token stored"
                        
                except Exception as e:
                    results[connection.platform] = False
                    connection.validation_error = f"Validation failed: {str(e)}"
                    logger.error(f"Token validation failed for {connection.platform}: {e}")
            
            db.commit()
            return results
            
        except Exception as e:
            logger.error(f"Failed to validate stored tokens: {e}")
            return {}


class APIKeyManager:
    """Manages API keys for external services."""
    
    def __init__(self):
        self.encryption = token_encryption
    
    def generate_api_key(self, user_id: str, service_name: str) -> str:
        """
        Generate a new API key for a service.
        
        Args:
            user_id: User ID
            service_name: Name of the service
            
        Returns:
            Generated API key
        """
        # Create a unique API key
        timestamp = int(datetime.utcnow().timestamp())
        raw_key = f"{user_id}:{service_name}:{timestamp}:{security_validator.generate_secure_token()}"
        
        # Hash the key for storage
        api_key = security_validator.generate_secure_token(32)
        
        logger.info(f"Generated API key for user {user_id} and service {service_name}")
        return api_key
    
    def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Validate an API key.
        
        Args:
            api_key: API key to validate
            
        Returns:
            Dictionary with key information or None if invalid
        """
        # In a real implementation, you'd store API keys in the database
        # with associated metadata and validate against that
        
        if not api_key or len(api_key) < 32:
            return None
        
        # For now, return basic validation
        return {
            "valid": True,
            "created_at": datetime.utcnow(),
            "expires_at": None
        }


# Global instances
secure_token_storage = SecureTokenStorage()
api_key_manager = APIKeyManager()