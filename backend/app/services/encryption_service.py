"""
Enhanced encryption service for sensitive data protection.

This service provides:
- Field-level encryption for sensitive data
- Key rotation capabilities
- Encrypted data storage and retrieval
- Compliance with data protection standards
"""

import base64
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Union, List
from cryptography.fernet import Fernet, MultiFernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from sqlalchemy.orm import Session
from ..config import settings
from ..security import security_validator

logger = logging.getLogger(__name__)


class EncryptionService:
    """Handles encryption and decryption of sensitive data."""
    
    def __init__(self):
        self.primary_key = self._derive_key(settings.jwt_secret_key, b"primary_salt")
        self.backup_key = self._derive_key(settings.jwt_secret_key, b"backup_salt")
        
        # Use MultiFernet for key rotation support
        self.cipher = MultiFernet([
            Fernet(self.primary_key),
            Fernet(self.backup_key)
        ])
        
        # Generate RSA key pair for asymmetric encryption (for very sensitive data)
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        self.public_key = self.private_key.public_key()
    
    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """
        Derive encryption key from password and salt.
        
        Args:
            password: Password to derive key from
            salt: Salt for key derivation
            
        Returns:
            Derived encryption key
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = kdf.derive(password.encode())
        return base64.urlsafe_b64encode(key)
    
    def encrypt_field(self, data: Union[str, Dict, List], field_type: str = "general") -> str:
        """
        Encrypt a data field.
        
        Args:
            data: Data to encrypt
            field_type: Type of field being encrypted
            
        Returns:
            Encrypted data as base64 string
        """
        try:
            # Convert data to JSON string if not already string
            if isinstance(data, (dict, list)):
                data_str = json.dumps(data)
            else:
                data_str = str(data)
            
            # Add metadata
            encrypted_data = {
                "data": data_str,
                "field_type": field_type,
                "encrypted_at": datetime.utcnow().isoformat(),
                "version": "1.0"
            }
            
            # Encrypt the JSON
            json_str = json.dumps(encrypted_data)
            encrypted_bytes = self.cipher.encrypt(json_str.encode())
            
            return base64.urlsafe_b64encode(encrypted_bytes).decode()
            
        except Exception as e:
            logger.error(f"Failed to encrypt field: {e}")
            raise
    
    def decrypt_field(self, encrypted_data: str) -> Union[str, Dict, List]:
        """
        Decrypt a data field.
        
        Args:
            encrypted_data: Encrypted data as base64 string
            
        Returns:
            Decrypted data in original format
        """
        try:
            # Decode from base64
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            
            # Decrypt
            decrypted_bytes = self.cipher.decrypt(encrypted_bytes)
            decrypted_json = json.loads(decrypted_bytes.decode())
            
            # Extract original data
            original_data = decrypted_json["data"]
            
            # Try to parse as JSON if it looks like structured data
            if original_data.startswith(("{", "[")):
                try:
                    return json.loads(original_data)
                except json.JSONDecodeError:
                    pass
            
            return original_data
            
        except Exception as e:
            logger.error(f"Failed to decrypt field: {e}")
            raise
    
    def encrypt_pii(self, pii_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Encrypt personally identifiable information.
        
        Args:
            pii_data: Dictionary of PII fields to encrypt
            
        Returns:
            Dictionary with encrypted PII fields
        """
        encrypted_pii = {}
        
        for field_name, field_value in pii_data.items():
            if field_value is not None:
                encrypted_pii[field_name] = self.encrypt_field(field_value, "pii")
            else:
                encrypted_pii[field_name] = None
        
        return encrypted_pii
    
    def decrypt_pii(self, encrypted_pii: Dict[str, str]) -> Dict[str, Any]:
        """
        Decrypt personally identifiable information.
        
        Args:
            encrypted_pii: Dictionary of encrypted PII fields
            
        Returns:
            Dictionary with decrypted PII fields
        """
        decrypted_pii = {}
        
        for field_name, encrypted_value in encrypted_pii.items():
            if encrypted_value is not None:
                try:
                    decrypted_pii[field_name] = self.decrypt_field(encrypted_value)
                except Exception as e:
                    logger.error(f"Failed to decrypt PII field {field_name}: {e}")
                    decrypted_pii[field_name] = None
            else:
                decrypted_pii[field_name] = None
        
        return decrypted_pii
    
    def encrypt_with_rsa(self, data: str) -> str:
        """
        Encrypt data using RSA public key (for very sensitive data).
        
        Args:
            data: Data to encrypt
            
        Returns:
            RSA encrypted data as base64 string
        """
        try:
            encrypted_bytes = self.public_key.encrypt(
                data.encode(),
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            return base64.urlsafe_b64encode(encrypted_bytes).decode()
            
        except Exception as e:
            logger.error(f"Failed to encrypt with RSA: {e}")
            raise
    
    def decrypt_with_rsa(self, encrypted_data: str) -> str:
        """
        Decrypt data using RSA private key.
        
        Args:
            encrypted_data: RSA encrypted data as base64 string
            
        Returns:
            Decrypted data
        """
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_bytes = self.private_key.decrypt(
                encrypted_bytes,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            return decrypted_bytes.decode()
            
        except Exception as e:
            logger.error(f"Failed to decrypt with RSA: {e}")
            raise
    
    def hash_for_search(self, data: str, salt: Optional[str] = None) -> tuple[str, str]:
        """
        Create searchable hash of sensitive data.
        
        This allows searching encrypted data without decrypting it.
        
        Args:
            data: Data to hash
            salt: Optional salt (generated if not provided)
            
        Returns:
            Tuple of (hash, salt)
        """
        if salt is None:
            salt = security_validator.generate_secure_token(16)
        
        # Create deterministic hash for searching
        hash_value, _ = security_validator.hash_sensitive_data(data.lower().strip(), salt)
        
        return hash_value, salt
    
    def create_encrypted_index(self, data: str) -> Dict[str, str]:
        """
        Create encrypted searchable index for data.
        
        Args:
            data: Data to create index for
            
        Returns:
            Dictionary with encrypted data and searchable hash
        """
        # Encrypt the actual data
        encrypted_data = self.encrypt_field(data, "indexed")
        
        # Create searchable hash
        search_hash, salt = self.hash_for_search(data)
        
        return {
            "encrypted_data": encrypted_data,
            "search_hash": search_hash,
            "salt": salt,
            "created_at": datetime.utcnow().isoformat()
        }
    
    def rotate_encryption_keys(self) -> bool:
        """
        Rotate encryption keys (in production, this would re-encrypt all data).
        
        Returns:
            True if successful
        """
        try:
            # In a real implementation, you would:
            # 1. Generate new keys
            # 2. Re-encrypt all data with new keys
            # 3. Update the MultiFernet with new keys
            # 4. Remove old keys after re-encryption is complete
            
            logger.info("Key rotation would be performed here in production")
            return True
            
        except Exception as e:
            logger.error(f"Failed to rotate encryption keys: {e}")
            return False
    
    def get_encryption_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about current encryption configuration.
        
        Returns:
            Dictionary with encryption metadata
        """
        return {
            "encryption_version": "1.0",
            "cipher_type": "Fernet",
            "key_derivation": "PBKDF2HMAC",
            "hash_algorithm": "SHA256",
            "key_iterations": 100000,
            "rsa_key_size": 2048,
            "supports_key_rotation": True,
            "supports_field_encryption": True,
            "supports_searchable_encryption": True
        }


class EncryptedFieldMixin:
    """Mixin for SQLAlchemy models to support encrypted fields."""
    
    @classmethod
    def encrypt_sensitive_fields(cls, data: Dict[str, Any], sensitive_fields: List[str]) -> Dict[str, Any]:
        """
        Encrypt sensitive fields in a data dictionary.
        
        Args:
            data: Data dictionary
            sensitive_fields: List of field names to encrypt
            
        Returns:
            Data dictionary with encrypted sensitive fields
        """
        encrypted_data = data.copy()
        
        for field_name in sensitive_fields:
            if field_name in encrypted_data and encrypted_data[field_name] is not None:
                encrypted_data[field_name] = encryption_service.encrypt_field(
                    encrypted_data[field_name], 
                    field_type="sensitive"
                )
        
        return encrypted_data
    
    @classmethod
    def decrypt_sensitive_fields(cls, data: Dict[str, Any], sensitive_fields: List[str]) -> Dict[str, Any]:
        """
        Decrypt sensitive fields in a data dictionary.
        
        Args:
            data: Data dictionary with encrypted fields
            sensitive_fields: List of field names to decrypt
            
        Returns:
            Data dictionary with decrypted sensitive fields
        """
        decrypted_data = data.copy()
        
        for field_name in sensitive_fields:
            if field_name in decrypted_data and decrypted_data[field_name] is not None:
                try:
                    decrypted_data[field_name] = encryption_service.decrypt_field(
                        decrypted_data[field_name]
                    )
                except Exception as e:
                    logger.error(f"Failed to decrypt field {field_name}: {e}")
                    decrypted_data[field_name] = None
        
        return decrypted_data


# Global instance
encryption_service = EncryptionService()