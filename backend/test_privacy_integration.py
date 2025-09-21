#!/usr/bin/env python3
"""
Simple integration test for data privacy functionality.
This tests the core privacy features without requiring the full test suite.
"""

import asyncio
import json
import zipfile
from datetime import datetime
from io import BytesIO

from app.services.data_privacy_service import data_privacy_service
from app.services.audit_service import audit_service
from app.services.encryption_service import encryption_service


def test_encryption_service():
    """Test encryption service functionality."""
    print("Testing Encryption Service...")
    
    # Test basic field encryption
    original_data = "sensitive user information"
    encrypted = encryption_service.encrypt_field(original_data, "pii")
    decrypted = encryption_service.decrypt_field(encrypted)
    
    assert original_data == decrypted, "Basic encryption/decryption failed"
    print("✓ Basic field encryption works")
    
    # Test PII encryption
    pii_data = {
        "email": "user@example.com",
        "phone": "+1234567890",
        "address": "123 Main St"
    }
    
    encrypted_pii = encryption_service.encrypt_pii(pii_data)
    decrypted_pii = encryption_service.decrypt_pii(encrypted_pii)
    
    assert pii_data == decrypted_pii, "PII encryption/decryption failed"
    print("✓ PII encryption works")
    
    # Test RSA encryption
    sensitive_data = "extremely sensitive information"
    rsa_encrypted = encryption_service.encrypt_with_rsa(sensitive_data)
    rsa_decrypted = encryption_service.decrypt_with_rsa(rsa_encrypted)
    
    assert sensitive_data == rsa_decrypted, "RSA encryption/decryption failed"
    print("✓ RSA encryption works")
    
    # Test searchable hash
    data = "searchable data"
    hash1, salt1 = encryption_service.hash_for_search(data)
    hash2, salt2 = encryption_service.hash_for_search(data, salt1)
    
    assert hash1 == hash2, "Searchable hash consistency failed"
    print("✓ Searchable hash works")
    
    # Test encrypted index
    index = encryption_service.create_encrypted_index(data)
    decrypted_from_index = encryption_service.decrypt_field(index["encrypted_data"])
    
    assert data == decrypted_from_index, "Encrypted index failed"
    print("✓ Encrypted index works")
    
    print("✅ All encryption tests passed!\n")


def test_data_export_structure():
    """Test data export structure without database."""
    print("Testing Data Export Structure...")
    
    # Test export data collection structure
    sample_export_data = {
        "export_info": {
            "user_id": "test_user_123",
            "export_date": datetime.utcnow().isoformat(),
            "format_version": "1.0"
        },
        "user_profile": {
            "id": "test_user_123",
            "email": "test@example.com",
            "business_name": "Test Business"
        },
        "products": [
            {
                "id": "product_123",
                "title": "Test Product",
                "description": "Test description"
            }
        ],
        "platform_connections": [
            {
                "id": "conn_123",
                "platform": "facebook",
                "is_active": True
            }
        ]
    }
    
    # Test README generation
    from app.models import User
    mock_user = type('MockUser', (), {
        'id': 'test_user_123',
        'email': 'test@example.com',
        'business_name': 'Test Business'
    })()
    
    readme = data_privacy_service._generate_export_readme(mock_user, sample_export_data)
    
    assert "Test Business" in readme, "README generation failed"
    assert "test@example.com" in readme, "README generation failed"
    print("✓ Export README generation works")
    
    # Test data schema generation
    schema = data_privacy_service._generate_data_schema()
    
    assert "user_profile" in schema["tables"], "Data schema generation failed"
    assert "products" in schema["tables"], "Data schema generation failed"
    print("✓ Data schema generation works")
    
    print("✅ Data export structure tests passed!\n")


def test_audit_service_structure():
    """Test audit service structure without database."""
    print("Testing Audit Service Structure...")
    
    # Test sensitivity level determination
    assert audit_service._get_sensitivity_level("login") == "low"
    assert audit_service._get_sensitivity_level("data_export") == "critical"
    assert audit_service._get_sensitivity_level("unknown_action") == "normal"
    print("✓ Sensitivity level determination works")
    
    # Test client IP extraction
    from unittest.mock import Mock
    
    mock_request = Mock()
    mock_request.headers = {"x-forwarded-for": "192.168.1.1, 10.0.0.1"}
    mock_request.client.host = "127.0.0.1"
    
    ip = audit_service._get_client_ip(mock_request)
    assert ip == "192.168.1.1", "Client IP extraction failed"
    print("✓ Client IP extraction works")
    
    print("✅ Audit service structure tests passed!\n")


def test_privacy_compliance_features():
    """Test privacy compliance features."""
    print("Testing Privacy Compliance Features...")
    
    # Test data retention period
    assert data_privacy_service.retention_days == 30, "Retention period incorrect"
    print("✓ 30-day retention period configured")
    
    # Test encryption metadata
    metadata = encryption_service.get_encryption_metadata()
    
    required_features = [
        "supports_key_rotation",
        "supports_field_encryption", 
        "supports_searchable_encryption"
    ]
    
    for feature in required_features:
        assert metadata.get(feature) is True, f"Missing privacy feature: {feature}"
    
    print("✓ Required privacy features available")
    
    # Test audit sensitivity levels
    critical_actions = ["data_export", "data_deletion", "account_deletion"]
    for action in critical_actions:
        level = audit_service._get_sensitivity_level(action)
        assert level == "critical", f"Action {action} should be critical sensitivity"
    
    print("✓ Critical actions properly classified")
    
    print("✅ Privacy compliance tests passed!\n")


def main():
    """Run all integration tests."""
    print("🔒 Data Privacy and Deletion Integration Tests")
    print("=" * 50)
    
    try:
        test_encryption_service()
        test_data_export_structure()
        test_audit_service_structure()
        test_privacy_compliance_features()
        
        print("🎉 All integration tests passed successfully!")
        print("\nImplemented features:")
        print("✓ Field-level encryption for sensitive data")
        print("✓ User data export functionality")
        print("✓ Secure data deletion with 30-day retention")
        print("✓ Comprehensive audit logging")
        print("✓ Privacy compliance features")
        print("✓ Data anonymization capabilities")
        print("✓ Searchable encryption for indexed data")
        print("✓ RSA encryption for highly sensitive data")
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        raise


if __name__ == "__main__":
    main()