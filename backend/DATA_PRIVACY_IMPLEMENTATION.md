# Data Privacy and Deletion Implementation

This document describes the comprehensive data privacy and deletion functionality implemented for the Artisan Promotion Platform, ensuring compliance with data protection regulations like GDPR.

## Overview

The implementation provides:
- **User Data Export**: Complete data export in structured format
- **Secure Data Deletion**: 30-day retention period with permanent deletion
- **Data Encryption**: Field-level encryption for sensitive information
- **Audit Logging**: Comprehensive logging of data access and modifications
- **Privacy Compliance**: GDPR-compliant data handling

## Components

### 1. Data Privacy Service (`app/services/data_privacy_service.py`)

**Key Features:**
- Complete user data export with ZIP packaging
- Scheduled deletion with retention period
- Data anonymization as alternative to deletion
- Comprehensive audit logging integration

**Main Methods:**
- `export_user_data()`: Exports all user data in JSON format with documentation
- `schedule_user_deletion()`: Schedules user for deletion after retention period
- `execute_user_deletion()`: Permanently deletes all user data
- `anonymize_user_data()`: Anonymizes user data while preserving analytics

### 2. Audit Service (`app/services/audit_service.py`)

**Key Features:**
- Comprehensive audit logging for all data operations
- Sensitivity level classification (low, normal, high, critical)
- Request tracking with IP addresses and user agents
- Privacy-specific action logging

**Main Methods:**
- `log_action()`: General audit logging
- `log_privacy_action()`: Privacy-specific actions (export, deletion)
- `log_security_event()`: Security-related events
- `get_user_audit_log()`: Retrieve user's audit history

### 3. Encryption Service (`app/services/encryption_service.py`)

**Key Features:**
- Field-level encryption using Fernet (AES 128)
- RSA encryption for highly sensitive data
- Searchable encryption for indexed data
- Key rotation support with MultiFernet
- PII-specific encryption utilities

**Main Methods:**
- `encrypt_field()` / `decrypt_field()`: General field encryption
- `encrypt_pii()` / `decrypt_pii()`: PII-specific encryption
- `encrypt_with_rsa()` / `decrypt_with_rsa()`: RSA encryption
- `create_encrypted_index()`: Searchable encrypted data

### 4. Privacy API (`app/routers/privacy.py`)

**Endpoints:**
- `POST /privacy/export`: Request data export
- `GET /privacy/export/{export_id}/download`: Download exported data
- `POST /privacy/deletion-request`: Request data deletion
- `DELETE /privacy/deletion-request/{request_id}`: Cancel deletion request
- `GET /privacy/audit-log`: View audit log
- `GET /privacy/deletion-status`: Check deletion status
- `POST /privacy/anonymize`: Anonymize user data

## Database Models

### AuditLog
Tracks all data access and modification events:
```sql
- id: Unique identifier
- user_id: User performing action
- action: Action type (data_export, data_deletion, etc.)
- resource_type: Type of resource accessed
- resource_id: ID of specific resource
- ip_address: Client IP address
- user_agent: Client user agent
- details: Human-readable description
- action_metadata: Structured metadata
- success: Whether action succeeded
- sensitivity_level: Security classification
- timestamp: When action occurred
```

### DataDeletionRequest
Manages data deletion requests with retention:
```sql
- id: Unique identifier
- user_id: User requesting deletion
- deletion_type: 'full_deletion' or 'anonymization'
- reason: Reason for deletion
- scheduled_for: When deletion will occur
- retention_period_days: Retention period (default 30)
- status: 'scheduled', 'in_progress', 'completed', 'cancelled'
- export_requested: Whether to export data first
- verification_token: Token for verification
- request_metadata: Additional request data
```

## Security Features

### Encryption
- **Symmetric Encryption**: AES-128 via Fernet for general data
- **Asymmetric Encryption**: RSA-2048 for highly sensitive data
- **Key Derivation**: PBKDF2 with SHA-256 (100,000 iterations)
- **Key Rotation**: MultiFernet supports seamless key rotation
- **Searchable Encryption**: Deterministic hashing for encrypted search

### Audit Logging
- **Comprehensive Tracking**: All data operations logged
- **Sensitivity Classification**: Actions classified by security impact
- **Request Context**: IP addresses, user agents, timestamps
- **Tamper Resistance**: Immutable audit trail
- **Retention Policy**: Critical events retained longer

### Access Control
- **Authentication Required**: All endpoints require valid JWT
- **User Isolation**: Users can only access their own data
- **Rate Limiting**: Protection against abuse
- **Input Validation**: All inputs sanitized and validated

## Privacy Compliance

### GDPR Compliance
- **Right to Access**: Complete data export functionality
- **Right to Erasure**: Secure deletion with retention period
- **Right to Rectification**: Data can be updated/corrected
- **Right to Portability**: Data exported in machine-readable format
- **Privacy by Design**: Encryption and audit logging built-in

### Data Retention
- **30-Day Retention**: Deleted data retained for 30 days
- **Secure Deletion**: Cryptographic erasure of sensitive data
- **Audit Trail**: All privacy actions logged permanently
- **Anonymization Option**: Alternative to full deletion

### Data Minimization
- **Field-Level Encryption**: Only sensitive fields encrypted
- **Selective Export**: Users control what data is exported
- **Automatic Cleanup**: Old audit logs automatically cleaned up
- **Anonymization**: Preserves analytics while removing PII

## Usage Examples

### Export User Data
```python
from app.services.data_privacy_service import data_privacy_service

# Export all user data
export_zip = await data_privacy_service.export_user_data(db, user_id)

# ZIP contains:
# - user_data.json: Complete data export
# - README.txt: Human-readable summary
# - data_schema.json: Data structure documentation
```

### Schedule Data Deletion
```python
# Schedule deletion with 30-day retention
success = await data_privacy_service.schedule_user_deletion(
    db, user_id, "user_request"
)

# User account deactivated immediately
# Actual deletion occurs after retention period
```

### Encrypt Sensitive Data
```python
from app.services.encryption_service import encryption_service

# Encrypt PII data
pii_data = {"email": "user@example.com", "phone": "+1234567890"}
encrypted_pii = encryption_service.encrypt_pii(pii_data)

# Decrypt when needed
decrypted_pii = encryption_service.decrypt_pii(encrypted_pii)
```

### Log Privacy Actions
```python
from app.services.audit_service import audit_service

# Log data export
await audit_service.log_privacy_action(
    db=db,
    user_id=user_id,
    privacy_action="export",
    details="User data exported",
    metadata={"format": "json"}
)
```

## Testing

### Integration Tests
Run the privacy integration tests:
```bash
cd backend
python test_privacy_integration.py
```

### Unit Tests
Run comprehensive unit tests:
```bash
cd backend
python -m pytest tests/test_data_privacy.py -v
```

### Test Coverage
- ✅ Data export functionality
- ✅ Secure deletion with retention
- ✅ Data encryption/decryption
- ✅ Audit logging
- ✅ Privacy API endpoints
- ✅ Database models
- ✅ Error handling
- ✅ Security validation

## Deployment Considerations

### Database Migration
Run the migration to create audit and deletion tables:
```bash
alembic upgrade head
```

### Environment Variables
Ensure these are set in production:
```bash
JWT_SECRET_KEY=<strong-secret-key>  # Used for encryption key derivation
DATABASE_URL=<production-database>
ENVIRONMENT=production
```

### Background Jobs
In production, implement background jobs for:
- Processing data exports
- Executing scheduled deletions
- Cleaning up old audit logs
- Key rotation

### Monitoring
Monitor these metrics:
- Data export requests
- Deletion requests
- Failed privacy operations
- Audit log growth
- Encryption/decryption performance

## Compliance Checklist

- ✅ **Data Export**: Complete, machine-readable export
- ✅ **Data Deletion**: Secure deletion with retention
- ✅ **Audit Logging**: Comprehensive activity tracking
- ✅ **Encryption**: Field-level encryption for sensitive data
- ✅ **Access Control**: Authentication and authorization
- ✅ **Data Minimization**: Only necessary data collected
- ✅ **Anonymization**: Alternative to full deletion
- ✅ **User Control**: Users control their data
- ✅ **Transparency**: Clear documentation and processes
- ✅ **Security**: Industry-standard encryption and security

## Future Enhancements

### Planned Features
- **Automated Key Rotation**: Scheduled encryption key rotation
- **Data Classification**: Automatic PII detection and classification
- **Consent Management**: Granular consent tracking
- **Cross-Border Compliance**: Region-specific data handling
- **Advanced Analytics**: Privacy-preserving analytics

### Performance Optimizations
- **Async Processing**: Background processing for large exports
- **Streaming Exports**: Memory-efficient large data exports
- **Compressed Storage**: Efficient encrypted data storage
- **Caching**: Encrypted caching for frequently accessed data

This implementation provides a robust foundation for data privacy compliance while maintaining system performance and user experience.