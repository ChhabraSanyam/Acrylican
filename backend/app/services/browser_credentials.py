"""
Secure Credential Handling for Browser Automation Platforms

This module provides secure storage and management of credentials for platforms
that require browser automation, with encryption and secure session management.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import tempfile

from cryptography.fernet import Fernet
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .platform_integration import Platform, PlatformCredentials, AuthenticationMethod
from ..database import get_db
from ..models import PlatformConnection

logger = logging.getLogger(__name__)


class BrowserCredentials(PlatformCredentials):
    """Credentials for browser automation platforms."""
    username: str
    password: str
    additional_data: Dict[str, Any] = Field(default_factory=dict)
    
    def __init__(self, username: str = None, password: str = None, platform: Platform = None, **kwargs):
        # Handle both direct instantiation and deserialization
        if username is not None and password is not None:
            # Direct instantiation
            super().__init__(
                platform=platform or Platform.MEESHO,
                auth_method=kwargs.get('auth_method', AuthenticationMethod.CREDENTIALS),
                username=username,
                password=password,
                additional_data=kwargs.get('additional_data', {}),
                **{k: v for k, v in kwargs.items() if k not in ['auth_method', 'additional_data']}
            )
        else:
            # Deserialization from dict
            super().__init__(**kwargs)
    
    class Config:
        # Exclude password from serialization by default
        fields = {"password": {"write_only": True}}


class SecureCredentialStore:
    """Secure storage for browser automation credentials."""
    
    def __init__(self, encryption_key: Optional[bytes] = None):
        self.logger = logging.getLogger(__name__)
        self.encryption_key = encryption_key or self._get_or_create_encryption_key()
        self.cipher = Fernet(self.encryption_key)
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for credential storage."""
        # In production, this should be stored securely (e.g., environment variable, key management service)
        key_env = os.getenv("BROWSER_CREDENTIALS_KEY")
        if key_env:
            return key_env.encode()
        
        # For development, store in temp directory
        key_file = Path(tempfile.gettempdir()) / "browser_credentials_key"
        
        if key_file.exists():
            return key_file.read_bytes()
        
        key = Fernet.generate_key()
        key_file.write_bytes(key)
        self.logger.warning(
            "Created new encryption key in temp directory. "
            "In production, use BROWSER_CREDENTIALS_KEY environment variable."
        )
        return key
    
    def encrypt_credentials(self, credentials: BrowserCredentials) -> str:
        """Encrypt credentials for secure storage."""
        try:
            # Convert to dict and encrypt sensitive fields
            cred_dict = credentials.model_dump()
            
            # Encrypt password
            if "password" in cred_dict:
                cred_dict["password"] = self.cipher.encrypt(
                    cred_dict["password"].encode()
                ).decode()
            
            # Encrypt any additional sensitive data
            if "additional_data" in cred_dict:
                for key, value in cred_dict["additional_data"].items():
                    if isinstance(value, str) and ("password" in key.lower() or "secret" in key.lower()):
                        cred_dict["additional_data"][key] = self.cipher.encrypt(
                            value.encode()
                        ).decode()
            
            # Encrypt the entire JSON string
            json_str = json.dumps(cred_dict)
            encrypted_data = self.cipher.encrypt(json_str.encode()).decode()
            
            return encrypted_data
            
        except Exception as e:
            self.logger.error(f"Failed to encrypt credentials: {e}")
            raise
    
    def decrypt_credentials(self, encrypted_data: str) -> BrowserCredentials:
        """Decrypt credentials from secure storage."""
        try:
            # Decrypt the JSON string
            decrypted_json = self.cipher.decrypt(encrypted_data.encode()).decode()
            cred_dict = json.loads(decrypted_json)
            
            # Decrypt password
            if "password" in cred_dict:
                cred_dict["password"] = self.cipher.decrypt(
                    cred_dict["password"].encode()
                ).decode()
            
            # Decrypt additional sensitive data
            if "additional_data" in cred_dict:
                for key, value in cred_dict["additional_data"].items():
                    if isinstance(value, str) and ("password" in key.lower() or "secret" in key.lower()):
                        try:
                            cred_dict["additional_data"][key] = self.cipher.decrypt(
                                value.encode()
                            ).decode()
                        except:
                            # If decryption fails, assume it's not encrypted
                            pass
            
            return BrowserCredentials(**cred_dict)
            
        except Exception as e:
            self.logger.error(f"Failed to decrypt credentials: {e}")
            raise


class BrowserCredentialManager:
    """Manager for browser automation platform credentials."""
    
    def __init__(self, credential_store: Optional[SecureCredentialStore] = None):
        self.credential_store = credential_store or SecureCredentialStore()
        self.logger = logging.getLogger(__name__)
        
        # Platforms that support browser automation
        self.browser_platforms = {
            Platform.MEESHO,
            Platform.SNAPDEAL,
            Platform.INDIAMART,
        }
    
    def is_browser_platform(self, platform: Platform) -> bool:
        """Check if a platform uses browser automation."""
        return platform in self.browser_platforms
    
    async def store_credentials(
        self,
        platform: Platform,
        user_id: str,
        credentials: BrowserCredentials
    ) -> bool:
        """Store encrypted credentials for a platform."""
        if not self.is_browser_platform(platform):
            raise ValueError(f"Platform {platform.value} does not use browser automation")
        
        try:
            # Encrypt credentials
            encrypted_data = self.credential_store.encrypt_credentials(credentials)
            
            # Store in database
            db = next(get_db())
            try:
                # Check if connection already exists
                existing_connection = db.query(PlatformConnection).filter(
                    PlatformConnection.user_id == user_id,
                    PlatformConnection.platform == platform.value
                ).first()
                
                if existing_connection:
                    # Update existing connection
                    existing_connection.access_token = encrypted_data
                    existing_connection.integration_type = "browser_automation"
                    existing_connection.auth_method = "credentials"
                    existing_connection.is_active = True
                    existing_connection.updated_at = datetime.now()
                else:
                    # Create new connection
                    connection = PlatformConnection(
                        user_id=user_id,
                        platform=platform.value,
                        integration_type="browser_automation",
                        auth_method="credentials",
                        access_token=encrypted_data,
                        is_active=True
                    )
                    db.add(connection)
                
                db.commit()
                self.logger.info(f"Stored credentials for {platform.value} user {user_id}")
                return True
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Failed to store credentials for {platform.value}: {e}")
            return False
    
    async def get_credentials(
        self,
        platform: Platform,
        user_id: str
    ) -> Optional[BrowserCredentials]:
        """Retrieve and decrypt credentials for a platform."""
        if not self.is_browser_platform(platform):
            return None
        
        try:
            db = next(get_db())
            try:
                connection = db.query(PlatformConnection).filter(
                    PlatformConnection.user_id == user_id,
                    PlatformConnection.platform == platform.value,
                    PlatformConnection.integration_type == "browser_automation",
                    PlatformConnection.is_active == True
                ).first()
                
                if not connection or not connection.access_token:
                    return None
                
                # Decrypt credentials
                credentials = self.credential_store.decrypt_credentials(connection.access_token)
                return credentials
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Failed to retrieve credentials for {platform.value}: {e}")
            return None
    
    async def update_credentials(
        self,
        platform: Platform,
        user_id: str,
        credentials: BrowserCredentials
    ) -> bool:
        """Update existing credentials for a platform."""
        return await self.store_credentials(platform, user_id, credentials)
    
    async def delete_credentials(
        self,
        platform: Platform,
        user_id: str
    ) -> bool:
        """Delete credentials for a platform."""
        try:
            db = next(get_db())
            try:
                connection = db.query(PlatformConnection).filter(
                    PlatformConnection.user_id == user_id,
                    PlatformConnection.platform == platform.value,
                    PlatformConnection.integration_type == "browser_automation"
                ).first()
                
                if connection:
                    connection.is_active = False
                    connection.access_token = None
                    connection.updated_at = datetime.now()
                    db.commit()
                    
                    self.logger.info(f"Deleted credentials for {platform.value} user {user_id}")
                    return True
                
                return False
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Failed to delete credentials for {platform.value}: {e}")
            return False
    
    async def list_user_connections(self, user_id: str) -> List[Dict[str, Any]]:
        """List all browser automation connections for a user."""
        try:
            db = next(get_db())
            try:
                connections = db.query(PlatformConnection).filter(
                    PlatformConnection.user_id == user_id,
                    PlatformConnection.integration_type == "browser_automation",
                    PlatformConnection.is_active == True
                ).all()
                
                result = []
                for conn in connections:
                    result.append({
                        "platform": conn.platform,
                        "connected_at": conn.connected_at,
                        "last_validated_at": conn.last_validated_at,
                        "is_active": conn.is_active,
                        "has_credentials": bool(conn.access_token)
                    })
                
                return result
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Failed to list connections for user {user_id}: {e}")
            return []
    
    async def validate_credentials(
        self,
        platform: Platform,
        credentials: BrowserCredentials
    ) -> bool:
        """Validate credentials format and required fields."""
        try:
            # Basic validation
            if not credentials.username or not credentials.password:
                return False
            
            # Platform-specific validation
            if platform == Platform.MEESHO:
                # Meesho typically uses email/phone + password
                if "@" not in credentials.username and not credentials.username.isdigit():
                    return False
            
            elif platform == Platform.SNAPDEAL:
                # Snapdeal uses email + password
                if "@" not in credentials.username:
                    return False
            
            elif platform == Platform.INDIAMART:
                # IndiaMART uses email + password
                if "@" not in credentials.username:
                    return False
            
            # Password strength check (basic)
            if len(credentials.password) < 6:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Credential validation failed: {e}")
            return False
    
    async def cleanup_inactive_connections(self, days_inactive: int = 30) -> int:
        """Clean up inactive connections older than specified days."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_inactive)
            
            db = next(get_db())
            try:
                # Find inactive connections
                inactive_connections = db.query(PlatformConnection).filter(
                    PlatformConnection.integration_type == "browser_automation",
                    PlatformConnection.is_active == False,
                    PlatformConnection.updated_at < cutoff_date
                ).all()
                
                count = len(inactive_connections)
                
                # Delete inactive connections
                for conn in inactive_connections:
                    db.delete(conn)
                
                db.commit()
                
                if count > 0:
                    self.logger.info(f"Cleaned up {count} inactive browser automation connections")
                
                return count
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup inactive connections: {e}")
            return 0


# Global credential manager instance
_credential_manager: Optional[BrowserCredentialManager] = None


def get_browser_credential_manager() -> BrowserCredentialManager:
    """Get the global browser credential manager instance."""
    global _credential_manager
    
    if _credential_manager is None:
        _credential_manager = BrowserCredentialManager()
    
    return _credential_manager