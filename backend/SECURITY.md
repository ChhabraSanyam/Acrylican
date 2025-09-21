# Security Implementation Guide

## Overview

The Artisan Promotion Platform implements comprehensive security measures to protect user data, prevent attacks, and ensure secure operation. This document outlines the security features and best practices implemented in the system.

## Security Features

### 1. Input Validation and Sanitization

**Implementation**: `app/security.py` - `InputSanitizer` class

**Features**:
- XSS (Cross-Site Scripting) protection
- SQL injection prevention
- HTML sanitization
- URL validation
- Email validation
- Dictionary sanitization with depth limits

**Usage**:
```python
from app.security import input_sanitizer

# Sanitize user input
safe_string = input_sanitizer.sanitize_string(user_input)
safe_email = input_sanitizer.sanitize_email(email)
safe_url = input_sanitizer.sanitize_url(url)
```

### 2. Rate Limiting

**Implementation**: `app/middleware.py` - `SecurityMiddleware`

**Features**:
- Per-endpoint rate limiting
- IP-based throttling
- Automatic IP blocking for excessive requests
- Configurable limits based on security level

**Configuration**:
```python
# Rate limits are configured in security_config.py
rate_limits = {
    "/auth/login": {"max_requests": 5, "window_minutes": 15},
    "/auth/register": {"max_requests": 3, "window_minutes": 60},
    "default": {"max_requests": 100, "window_minutes": 15}
}
```

### 3. Token Encryption

**Implementation**: `app/security.py` - `TokenEncryption` class

**Features**:
- AES-256-GCM encryption for sensitive tokens
- Secure key derivation using PBKDF2
- Token encryption detection
- Secure storage of OAuth tokens

**Usage**:
```python
from app.security import token_encryption

# Encrypt sensitive token
encrypted_token = token_encryption.encrypt_token(access_token)

# Decrypt when needed
decrypted_token = token_encryption.decrypt_token(encrypted_token)
```

### 4. Password Security

**Implementation**: `app/security.py` - `SecurityValidator` class

**Features**:
- Strong password requirements
- Bcrypt hashing with configurable rounds
- Common password detection
- Password strength validation

**Requirements**:
- Minimum 8 characters (12 for critical security level)
- Uppercase and lowercase letters
- Numbers and special characters
- Not in common password list

### 5. Security Headers

**Implementation**: `app/middleware.py` - `SecurityMiddleware`

**Headers Applied**:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Content-Security-Policy` (configurable)
- `Strict-Transport-Security` (HTTPS only)
- `Referrer-Policy: strict-origin-when-cross-origin`

### 6. File Upload Security

**Implementation**: `app/security.py` - `SecurityValidator.validate_file_upload`

**Features**:
- File type validation
- File size limits
- Dangerous extension detection
- Double extension protection
- MIME type verification

**Allowed Types**:
- `image/jpeg`
- `image/png`
- `image/webp`

### 7. HTTPS Enforcement

**Implementation**: `app/middleware.py` - `SecurityMiddleware`

**Features**:
- Automatic HTTPS redirect in production
- HSTS headers for browsers
- Secure cookie settings

### 8. Authentication Security

**Implementation**: `app/auth.py` and `app/dependencies.py`

**Features**:
- JWT token-based authentication
- Secure token generation and validation
- Token expiration handling
- Refresh token mechanism
- User session management

## Security Configuration

### Environment-Based Security Levels

The system automatically adjusts security measures based on the environment:

**Development** (`SecurityLevel.LOW`):
- Relaxed rate limits
- Debug logging enabled
- Less strict validation

**Testing** (`SecurityLevel.MEDIUM`):
- Moderate security measures
- Balanced performance and security

**Staging** (`SecurityLevel.HIGH`):
- Strict security measures
- Enhanced monitoring
- Production-like settings

**Production** (`SecurityLevel.CRITICAL`):
- Maximum security measures
- HTTPS enforcement
- Strict CSP policies
- Enhanced logging and monitoring

### Configuration Files

**Main Configuration**: `app/config.py`
- Database settings
- JWT configuration
- CORS settings
- File upload limits

**Security Configuration**: `app/security_config.py`
- Security level determination
- Rate limit configuration
- Password requirements
- Security headers

## Security Middleware

The application uses multiple middleware layers for security:

1. **SecurityMiddleware**: Core security features
2. **RequestValidationMiddleware**: Input validation
3. **LoggingMiddleware**: Security event logging
4. **CSRFProtectionMiddleware**: CSRF protection

## Secure Storage

### Token Storage

**Implementation**: `app/secure_storage.py`

**Features**:
- Encrypted storage of OAuth tokens
- Secure token rotation
- Token expiration handling
- Connection management

### API Key Management

**Features**:
- Secure API key generation
- Key validation and rotation
- Encrypted storage

## Security Testing

### Automated Tests

**Test File**: `tests/test_security.py`

**Coverage**:
- Input sanitization tests
- Token encryption tests
- Rate limiting tests
- Password validation tests
- File upload security tests
- Vulnerability assessment tests

### Security Audit

**Audit Script**: `scripts/security_audit.py`

**Checks**:
- Dependency vulnerability scanning
- Configuration security review
- Code security analysis
- API security testing
- Database security checks

**Usage**:
```bash
python scripts/security_audit.py
```

### Security Validation

**Validation Script**: `scripts/validate_security.py`

**Tests**:
- Input sanitization
- Token encryption
- Rate limiting
- Password validation
- Security configuration
- File upload validation

**Usage**:
```bash
python scripts/validate_security.py
```

## Security Best Practices

### For Developers

1. **Always validate input**: Use `InputSanitizer` for all user inputs
2. **Use parameterized queries**: SQLAlchemy ORM provides protection
3. **Encrypt sensitive data**: Use `TokenEncryption` for tokens and API keys
4. **Implement proper error handling**: Don't leak sensitive information
5. **Follow principle of least privilege**: Limit access to necessary resources
6. **Keep dependencies updated**: Regularly run security audits

### For Deployment

1. **Use HTTPS in production**: Set `environment=production`
2. **Set strong JWT secret**: Use `JWT_SECRET_KEY` environment variable
3. **Configure proper CORS**: Limit origins to trusted domains
4. **Use production database**: Avoid SQLite in production
5. **Enable security logging**: Monitor for suspicious activity
6. **Regular security audits**: Run automated security checks

### For Operations

1. **Monitor security logs**: Watch for failed authentication attempts
2. **Set up alerting**: Get notified of security events
3. **Regular backups**: Ensure data recovery capabilities
4. **Access control**: Limit administrative access
5. **Incident response plan**: Have procedures for security incidents

## Security Monitoring

### Logging

**Security Events Logged**:
- Authentication attempts (success/failure)
- Rate limit violations
- Input validation failures
- File upload attempts
- API access patterns
- Error conditions

**Log Levels**:
- `INFO`: Normal security events
- `WARNING`: Suspicious activity
- `ERROR`: Security violations
- `CRITICAL`: Security breaches

### Metrics

**Tracked Metrics**:
- Authentication success/failure rates
- Rate limit hit rates
- File upload patterns
- API usage patterns
- Error rates

## Compliance

### Data Protection

**Features**:
- Data encryption at rest and in transit
- Secure token storage
- User data isolation
- Audit logging
- Data retention policies

### Privacy

**Features**:
- User consent management
- Data anonymization options
- Right to deletion
- Data export capabilities
- Privacy-by-design architecture

## Incident Response

### Security Incident Procedures

1. **Detection**: Monitor logs and alerts
2. **Assessment**: Determine severity and impact
3. **Containment**: Isolate affected systems
4. **Investigation**: Analyze the incident
5. **Recovery**: Restore normal operations
6. **Lessons Learned**: Update security measures

### Emergency Contacts

- **Security Team**: [security@company.com]
- **Development Team**: [dev@company.com]
- **Operations Team**: [ops@company.com]

## Security Updates

### Regular Maintenance

- **Weekly**: Dependency updates
- **Monthly**: Security audit
- **Quarterly**: Penetration testing
- **Annually**: Security architecture review

### Version Control

- All security changes are tracked in version control
- Security patches are prioritized
- Emergency security updates follow fast-track process

## Reporting Security Issues

If you discover a security vulnerability, please report it to:

**Email**: security@company.com
**Subject**: Security Vulnerability Report
**Include**:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if known)

**Response Time**: We aim to respond within 24 hours and provide a fix within 7 days for critical issues.

## Security Checklist

### Pre-Deployment

- [ ] JWT secret key configured
- [ ] HTTPS enabled
- [ ] CORS properly configured
- [ ] Rate limiting enabled
- [ ] Security headers configured
- [ ] Input validation implemented
- [ ] File upload restrictions in place
- [ ] Database security configured
- [ ] Logging enabled
- [ ] Security tests passing

### Post-Deployment

- [ ] Security monitoring active
- [ ] Alerts configured
- [ ] Backup procedures tested
- [ ] Incident response plan ready
- [ ] Security audit completed
- [ ] Documentation updated
- [ ] Team trained on security procedures

## Resources

### Documentation

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Python Security Best Practices](https://python.org/dev/security/)

### Tools

- [Safety](https://pyup.io/safety/) - Dependency vulnerability scanner
- [Bandit](https://bandit.readthedocs.io/) - Python security linter
- [OWASP ZAP](https://www.zaproxy.org/) - Web application security scanner

### Training

- Security awareness training for all team members
- Regular security workshops and updates
- Incident response drills