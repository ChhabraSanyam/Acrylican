"""
Tests for data privacy and deletion functionality.

This module tests:
- User data export functionality
- Secure data deletion with retention
- Data encryption for sensitive information
- Audit logging for data access and modifications
"""

import json
import pytest
import zipfile
from datetime import datetime, timedelta
from io import BytesIO
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from app.models import (
    User, Product, ProductImage, PlatformConnection, Post, 
    SaleEvent, EngagementMetrics, AuditLog, DataDeletionRequest
)
from app.services.data_privacy_service import data_privacy_service
from app.services.audit_service import audit_service
from app.services.encryption_service import encryption_service
from app.security import security_validator


class TestDataPrivacyService:
    """Test data privacy service functionality."""
    
    @pytest.fixture
    def sample_user_data(self, db_session: Session):
        """Create sample user data for testing."""
        # Create user
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
            business_name="Test Business",
            business_type="Artisan",
            business_description="Test business description",
            website="https://test.com",
            location="Test City"
        )
        db_session.add(user)
        db_session.flush()
        
        # Create product
        product = Product(
            user_id=user.id,
            title="Test Product",
            description="Test product description",
            generated_content={"title": "Generated Title", "description": "Generated Description"}
        )
        db_session.add(product)
        db_session.flush()
        
        # Create product image
        image = ProductImage(
            product_id=product.id,
            original_filename="test.jpg",
            original_url="https://storage.com/original.jpg",
            compressed_url="https://storage.com/compressed.jpg",
            thumbnail_urls={"small": "https://storage.com/thumb_small.jpg"},
            storage_paths={"original": "path/to/original.jpg"},
            file_size=1024,
            dimensions={"width": 800, "height": 600},
            format="JPEG"
        )
        db_session.add(image)
        
        # Create platform connection
        connection = PlatformConnection(
            user_id=user.id,
            platform="facebook",
            integration_type="api",
            auth_method="oauth",
            access_token="encrypted_token",
            is_active=True
        )
        db_session.add(connection)
        
        # Create post
        post = Post(
            user_id=user.id,
            product_id=product.id,
            title="Test Post",
            description="Test post description",
            hashtags=["#test", "#product"],
            target_platforms=["facebook", "instagram"],
            status="published"
        )
        db_session.add(post)
        
        # Create sale event
        sale = SaleEvent(
            user_id=user.id,
            product_id=product.id,
            platform="facebook",
            order_id="ORDER123",
            amount=29.99,
            currency="USD",
            product_title="Test Product",
            quantity=1,
            occurred_at=datetime.utcnow()
        )
        db_session.add(sale)
        
        # Create engagement metrics
        metrics = EngagementMetrics(
            user_id=user.id,
            post_id=post.id,
            platform="facebook",
            platform_post_id="FB123",
            likes=10,
            shares=5,
            comments=2,
            views=100,
            reach=500,
            metrics_date=datetime.utcnow()
        )
        db_session.add(metrics)
        
        db_session.commit()
        return user
    
    @pytest.mark.asyncio
    async def test_export_user_data(self, db_session: Session, sample_user_data: User):
        """Test user data export functionality."""
        user = sample_user_data
        
        # Export user data
        export_zip = await data_privacy_service.export_user_data(db_session, user.id)
        
        # Verify ZIP file was created
        assert isinstance(export_zip, BytesIO)
        assert export_zip.getvalue()  # Has content
        
        # Extract and verify ZIP contents
        with zipfile.ZipFile(export_zip, 'r') as zip_file:
            file_list = zip_file.namelist()
            
            # Check required files
            assert "user_data.json" in file_list
            assert "README.txt" in file_list
            assert "data_schema.json" in file_list
            
            # Verify user data content
            user_data_content = zip_file.read("user_data.json")
            user_data = json.loads(user_data_content)
            
            # Check export info
            assert "export_info" in user_data
            assert user_data["export_info"]["user_id"] == user.id
            assert "export_date" in user_data["export_info"]
            
            # Check user profile
            assert "user_profile" in user_data
            profile = user_data["user_profile"]
            assert profile["email"] == user.email
            assert profile["business_name"] == user.business_name
            
            # Check products
            assert "products" in user_data
            assert len(user_data["products"]) == 1
            product = user_data["products"][0]
            assert product["title"] == "Test Product"
            assert len(product["images"]) == 1
            
            # Check platform connections (tokens should be excluded)
            assert "platform_connections" in user_data
            assert len(user_data["platform_connections"]) == 1
            connection = user_data["platform_connections"][0]
            assert connection["platform"] == "facebook"
            assert "access_token" not in connection  # Sensitive data excluded
            
            # Check posts
            assert "posts" in user_data
            assert len(user_data["posts"]) == 1
            
            # Check sales
            assert "sales" in user_data
            assert len(user_data["sales"]) == 1
            
            # Check engagement metrics
            assert "engagement_metrics" in user_data
            assert len(user_data["engagement_metrics"]) == 1
    
    @pytest.mark.asyncio
    async def test_export_nonexistent_user(self, db_session: Session):
        """Test export for non-existent user."""
        with pytest.raises(ValueError, match="User .* not found"):
            await data_privacy_service.export_user_data(db_session, "nonexistent_id")
    
    @pytest.mark.asyncio
    async def test_schedule_user_deletion(self, db_session: Session, sample_user_data: User):
        """Test scheduling user for deletion."""
        user = sample_user_data
        
        # Schedule deletion
        success = await data_privacy_service.schedule_user_deletion(
            db_session, user.id, "user_request"
        )
        
        assert success
        
        # Verify user is marked as inactive
        db_session.refresh(user)
        assert not user.is_active
    
    @pytest.mark.asyncio
    async def test_execute_user_deletion(self, db_session: Session, sample_user_data: User):
        """Test permanent user data deletion."""
        user = sample_user_data
        user_id = user.id
        
        # Execute deletion
        success = await data_privacy_service.execute_user_deletion(db_session, user_id)
        
        assert success
        
        # Verify all user data is deleted
        assert db_session.query(User).filter(User.id == user_id).first() is None
        assert db_session.query(Product).filter(Product.user_id == user_id).count() == 0
        assert db_session.query(PlatformConnection).filter(PlatformConnection.user_id == user_id).count() == 0
        assert db_session.query(Post).filter(Post.user_id == user_id).count() == 0
        assert db_session.query(SaleEvent).filter(SaleEvent.user_id == user_id).count() == 0
        assert db_session.query(EngagementMetrics).filter(EngagementMetrics.user_id == user_id).count() == 0
    
    @pytest.mark.asyncio
    async def test_anonymize_user_data(self, db_session: Session, sample_user_data: User):
        """Test user data anonymization."""
        user = sample_user_data
        original_email = user.email
        
        # Anonymize data
        success = await data_privacy_service.anonymize_user_data(db_session, user.id)
        
        assert success
        
        # Verify user data is anonymized
        db_session.refresh(user)
        assert user.email != original_email
        assert user.email.startswith("anonymized_")
        assert user.business_name == "Anonymized Business"
        assert user.business_description is None
        assert not user.is_active
        
        # Verify products are anonymized
        products = db_session.query(Product).filter(Product.user_id == user.id).all()
        for product in products:
            assert product.title == "Anonymized Product"
            assert "removed for privacy" in product.description
        
        # Verify platform connections are removed
        connections = db_session.query(PlatformConnection).filter(PlatformConnection.user_id == user.id).count()
        assert connections == 0


class TestAuditService:
    """Test audit logging service."""
    
    @pytest.fixture
    def mock_request(self):
        """Create mock FastAPI request."""
        request = Mock()
        request.client.host = "192.168.1.1"
        request.method = "POST"
        request.url.path = "/api/test"
        request.headers = {"user-agent": "Test Agent"}
        return request
    
    @pytest.mark.asyncio
    async def test_log_action(self, db_session: Session, mock_request):
        """Test basic audit logging."""
        # Create test user
        user = User(
            email="test@example.com",
            password_hash="hashed",
            business_name="Test",
            business_type="Artisan"
        )
        db_session.add(user)
        db_session.commit()
        
        # Log an action
        audit_entry = await audit_service.log_action(
            db=db_session,
            action="test_action",
            resource_type="test_resource",
            user_id=user.id,
            resource_id="resource123",
            details="Test action performed",
            metadata={"key": "value"},
            request=mock_request,
            success=True
        )
        
        # Verify audit entry
        assert audit_entry.action == "test_action"
        assert audit_entry.resource_type == "test_resource"
        assert audit_entry.user_id == user.id
        assert audit_entry.resource_id == "resource123"
        assert audit_entry.details == "Test action performed"
        assert audit_entry.action_metadata == {"key": "value"}
        assert audit_entry.success is True
        assert audit_entry.ip_address == "192.168.1.1"
        assert audit_entry.user_agent == "Test Agent"
        assert audit_entry.request_method == "POST"
        assert audit_entry.request_path == "/api/test"
        assert audit_entry.sensitivity_level == "normal"
    
    @pytest.mark.asyncio
    async def test_log_privacy_action(self, db_session: Session, mock_request):
        """Test privacy action logging."""
        # Create test user
        user = User(
            email="test@example.com",
            password_hash="hashed",
            business_name="Test",
            business_type="Artisan"
        )
        db_session.add(user)
        db_session.commit()
        
        # Log privacy action
        audit_entry = await audit_service.log_privacy_action(
            db=db_session,
            user_id=user.id,
            privacy_action="export",
            request=mock_request,
            details="Data export requested",
            metadata={"format": "json"}
        )
        
        # Verify audit entry
        assert audit_entry.action == "data_export"
        assert audit_entry.resource_type == "user_data"
        assert audit_entry.sensitivity_level == "critical"
        assert audit_entry.action_metadata["privacy_action"] == "export"
        assert audit_entry.action_metadata["format"] == "json"
    
    @pytest.mark.asyncio
    async def test_log_security_event(self, db_session: Session, mock_request):
        """Test security event logging."""
        # Log security event
        audit_entry = await audit_service.log_security_event(
            db=db_session,
            event_type="failed_login",
            request=mock_request,
            details="Failed login attempt",
            metadata={"attempts": 3},
            success=False,
            error_message="Invalid credentials"
        )
        
        # Verify audit entry
        assert audit_entry.action == "security_failed_login"
        assert audit_entry.resource_type == "security"
        assert audit_entry.success is False
        assert audit_entry.error_message == "Invalid credentials"
        assert audit_entry.action_metadata["event_type"] == "failed_login"
        assert audit_entry.action_metadata["attempts"] == 3
    
    @pytest.mark.asyncio
    async def test_get_user_audit_log(self, db_session: Session):
        """Test retrieving user audit log."""
        # Create test user
        user = User(
            email="test@example.com",
            password_hash="hashed",
            business_name="Test",
            business_type="Artisan"
        )
        db_session.add(user)
        db_session.commit()
        
        # Create multiple audit entries
        for i in range(5):
            await audit_service.log_action(
                db=db_session,
                action=f"test_action_{i}",
                resource_type="test",
                user_id=user.id,
                success=True
            )
        
        # Retrieve audit log
        entries = await audit_service.get_user_audit_log(
            db=db_session,
            user_id=user.id,
            limit=3
        )
        
        # Verify results
        assert len(entries) == 3
        assert all(entry.user_id == user.id for entry in entries)
        # Should be ordered by timestamp descending
        assert entries[0].timestamp >= entries[1].timestamp >= entries[2].timestamp


class TestEncryptionService:
    """Test encryption service functionality."""
    
    def test_encrypt_decrypt_field(self):
        """Test field encryption and decryption."""
        original_data = "sensitive information"
        
        # Encrypt
        encrypted = encryption_service.encrypt_field(original_data, "test")
        assert encrypted != original_data
        assert isinstance(encrypted, str)
        
        # Decrypt
        decrypted = encryption_service.decrypt_field(encrypted)
        assert decrypted == original_data
    
    def test_encrypt_decrypt_dict(self):
        """Test dictionary encryption and decryption."""
        original_data = {"name": "John Doe", "ssn": "123-45-6789"}
        
        # Encrypt
        encrypted = encryption_service.encrypt_field(original_data, "pii")
        assert encrypted != str(original_data)
        
        # Decrypt
        decrypted = encryption_service.decrypt_field(encrypted)
        assert decrypted == original_data
    
    def test_encrypt_decrypt_pii(self):
        """Test PII encryption and decryption."""
        pii_data = {
            "email": "user@example.com",
            "phone": "+1234567890",
            "address": "123 Main St",
            "empty_field": None
        }
        
        # Encrypt PII
        encrypted_pii = encryption_service.encrypt_pii(pii_data)
        
        # Verify encryption
        assert encrypted_pii["email"] != pii_data["email"]
        assert encrypted_pii["phone"] != pii_data["phone"]
        assert encrypted_pii["address"] != pii_data["address"]
        assert encrypted_pii["empty_field"] is None
        
        # Decrypt PII
        decrypted_pii = encryption_service.decrypt_pii(encrypted_pii)
        
        # Verify decryption
        assert decrypted_pii == pii_data
    
    def test_rsa_encryption(self):
        """Test RSA encryption for very sensitive data."""
        sensitive_data = "extremely sensitive information"
        
        # Encrypt with RSA
        encrypted = encryption_service.encrypt_with_rsa(sensitive_data)
        assert encrypted != sensitive_data
        
        # Decrypt with RSA
        decrypted = encryption_service.decrypt_with_rsa(encrypted)
        assert decrypted == sensitive_data
    
    def test_searchable_hash(self):
        """Test searchable hash creation."""
        data = "searchable data"
        
        # Create hash
        hash1, salt1 = encryption_service.hash_for_search(data)
        hash2, salt2 = encryption_service.hash_for_search(data, salt1)
        
        # Same data with same salt should produce same hash
        assert hash1 == hash2
        assert salt1 == salt2
        
        # Different salt should produce different hash
        hash3, salt3 = encryption_service.hash_for_search(data)
        assert hash1 != hash3
        assert salt1 != salt3
    
    def test_encrypted_index(self):
        """Test encrypted searchable index creation."""
        data = "indexable data"
        
        # Create encrypted index
        index = encryption_service.create_encrypted_index(data)
        
        # Verify index structure
        assert "encrypted_data" in index
        assert "search_hash" in index
        assert "salt" in index
        assert "created_at" in index
        
        # Verify encrypted data can be decrypted
        decrypted = encryption_service.decrypt_field(index["encrypted_data"])
        assert decrypted == data
        
        # Verify search hash is consistent
        test_hash, _ = encryption_service.hash_for_search(data, index["salt"])
        assert test_hash == index["search_hash"]
    
    def test_encryption_metadata(self):
        """Test encryption metadata retrieval."""
        metadata = encryption_service.get_encryption_metadata()
        
        # Verify metadata structure
        assert "encryption_version" in metadata
        assert "cipher_type" in metadata
        assert "key_derivation" in metadata
        assert "supports_key_rotation" in metadata
        assert metadata["supports_field_encryption"] is True
        assert metadata["supports_searchable_encryption"] is True


class TestDataDeletionRequest:
    """Test data deletion request functionality."""
    
    @pytest.fixture
    def sample_user(self, db_session: Session):
        """Create sample user for testing."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
            business_name="Test Business",
            business_type="Artisan"
        )
        db_session.add(user)
        db_session.commit()
        return user
    
    def test_create_deletion_request(self, db_session: Session, sample_user: User):
        """Test creating a data deletion request."""
        deletion_request = DataDeletionRequest(
            user_id=sample_user.id,
            deletion_type="full_deletion",
            reason="user_request",
            requested_by=sample_user.id,
            scheduled_for=datetime.utcnow() + timedelta(days=30),
            retention_period_days=30,
            verification_token=security_validator.generate_secure_token(32)
        )
        
        db_session.add(deletion_request)
        db_session.commit()
        
        # Verify deletion request
        assert deletion_request.id is not None
        assert deletion_request.status == "scheduled"
        assert deletion_request.deletion_type == "full_deletion"
        assert deletion_request.retention_period_days == 30
        assert deletion_request.verification_token is not None
    
    def test_deletion_request_relationships(self, db_session: Session, sample_user: User):
        """Test deletion request relationships."""
        deletion_request = DataDeletionRequest(
            user_id=sample_user.id,
            deletion_type="anonymization",
            reason="gdpr_request",
            requested_by=sample_user.id,
            scheduled_for=datetime.utcnow() + timedelta(days=30)
        )
        
        db_session.add(deletion_request)
        db_session.commit()
        
        # Test relationship
        assert deletion_request.user == sample_user
        assert deletion_request in sample_user.deletion_requests


@pytest.mark.integration
class TestPrivacyIntegration:
    """Integration tests for privacy functionality."""
    
    @pytest.mark.asyncio
    async def test_full_privacy_workflow(self, db_session: Session):
        """Test complete privacy workflow from export to deletion."""
        # Create user with data
        user = User(
            email="privacy@example.com",
            password_hash="hashed",
            business_name="Privacy Test",
            business_type="Artisan"
        )
        db_session.add(user)
        db_session.commit()
        
        # Add some user data
        product = Product(
            user_id=user.id,
            title="Privacy Product",
            description="Test product for privacy"
        )
        db_session.add(product)
        db_session.commit()
        
        # 1. Export user data
        export_zip = await data_privacy_service.export_user_data(db_session, user.id)
        assert export_zip is not None
        
        # 2. Schedule deletion
        success = await data_privacy_service.schedule_user_deletion(
            db_session, user.id, "privacy_test"
        )
        assert success
        
        # 3. Verify user is deactivated but data still exists
        db_session.refresh(user)
        assert not user.is_active
        assert db_session.query(Product).filter(Product.user_id == user.id).count() == 1
        
        # 4. Execute deletion
        success = await data_privacy_service.execute_user_deletion(db_session, user.id)
        assert success
        
        # 5. Verify all data is deleted
        assert db_session.query(User).filter(User.id == user.id).first() is None
        assert db_session.query(Product).filter(Product.user_id == user.id).count() == 0