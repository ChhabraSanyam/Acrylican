# OAuth Authentication Setup

This document explains how to set up and use OAuth authentication for social media and marketplace platforms in the Artisan Promotion Platform.

## Supported Platforms

The following platforms support OAuth authentication:

- **Facebook** - OAuth 2.0 with Graph API
- **Instagram** - OAuth 2.0 via Facebook Graph API
- **Etsy** - OAuth 2.0 with Etsy API v3
- **Pinterest** - OAuth 2.0 with Pinterest Business API
- **Shopify** - OAuth 2.0 with Shopify Admin API

## Environment Variables

Set up the following environment variables for each platform you want to support:

### Facebook & Instagram
```bash
FACEBOOK_CLIENT_ID=your_facebook_app_id
FACEBOOK_CLIENT_SECRET=your_facebook_app_secret
```

### Etsy
```bash
ETSY_CLIENT_ID=your_etsy_keystring
ETSY_CLIENT_SECRET=your_etsy_shared_secret
```

### Pinterest
```bash
PINTEREST_CLIENT_ID=your_pinterest_app_id
PINTEREST_CLIENT_SECRET=your_pinterest_app_secret
```

### Shopify
```bash
SHOPIFY_CLIENT_ID=your_shopify_api_key
SHOPIFY_CLIENT_SECRET=your_shopify_secret_key
```

## API Endpoints

### Get Supported Platforms
```http
GET /auth/platforms
```

### Get User Connections
```http
GET /auth/connections
Authorization: Bearer <jwt_token>
```

### Initiate OAuth Flow
```http
POST /auth/{platform}/connect
Authorization: Bearer <jwt_token>

# For Shopify, include shop domain:
POST /auth/shopify/connect?shop_domain=your-shop-name
```

### OAuth Callback (handled automatically)
```http
GET /auth/{platform}/callback?code=<auth_code>&state=<state>
```

### Disconnect Platform
```http
POST /auth/{platform}/disconnect
Authorization: Bearer <jwt_token>
```

### Validate Connection
```http
POST /auth/{platform}/validate
Authorization: Bearer <jwt_token>
```

### Get Platform Status
```http
GET /auth/{platform}/status
Authorization: Bearer <jwt_token>
```

## OAuth Flow

1. **Initiate Connection**: User clicks "Connect to Facebook" in frontend
2. **Get Authorization URL**: Frontend calls `/auth/facebook/connect`
3. **User Authorization**: User is redirected to Facebook to authorize
4. **Callback Handling**: Facebook redirects to `/auth/facebook/callback`
5. **Token Storage**: System exchanges code for tokens and stores securely
6. **Connection Active**: User can now post to Facebook via the platform

## Security Features

- **Token Encryption**: All OAuth tokens are encrypted before database storage
- **CSRF Protection**: State parameter prevents cross-site request forgery
- **Token Refresh**: Automatic refresh of expired access tokens
- **Secure Storage**: Tokens stored with encryption, never exposed in logs
- **Connection Validation**: Regular validation of platform connections

## Platform-Specific Notes

### Facebook & Instagram
- Requires Facebook Business account for Instagram posting
- Uses Facebook Graph API for both platforms
- Supports posting to Facebook Pages and Instagram Business accounts

### Etsy
- Requires Etsy seller account
- Creates product listings in user's Etsy shop
- Supports up to 10 images per listing

### Pinterest
- Requires Pinterest Business account
- Creates pins in user's Pinterest boards
- Supports Rich Pins for product information

### Shopify
- Requires Shopify store
- Creates products in user's Shopify store
- Requires shop domain parameter during connection

## Error Handling

The OAuth system includes comprehensive error handling:

- **Invalid Credentials**: Clear error messages for configuration issues
- **Expired Tokens**: Automatic refresh attempts
- **API Errors**: Detailed error codes and messages
- **Connection Failures**: Graceful degradation and retry logic

## Testing

Run OAuth tests:
```bash
# Test OAuth service
python -m pytest tests/test_oauth_service.py -v

# Test OAuth routes
python -m pytest tests/test_oauth_routes.py -v

# Test platform integrations
python -m pytest tests/test_platform_oauth_integrations.py -v
```

## Database Schema

The OAuth system uses the `platform_connections` table:

```sql
CREATE TABLE platform_connections (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    platform VARCHAR NOT NULL,
    integration_type VARCHAR NOT NULL,
    auth_method VARCHAR NOT NULL,
    access_token TEXT,  -- Encrypted
    refresh_token TEXT, -- Encrypted
    token_type VARCHAR DEFAULT 'Bearer',
    expires_at TIMESTAMP,
    scope VARCHAR,
    platform_user_id VARCHAR,
    platform_username VARCHAR,
    platform_data JSON,
    is_active BOOLEAN DEFAULT TRUE,
    last_validated_at TIMESTAMP,
    validation_error TEXT,
    connected_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

## Integration with Platform Service

The OAuth system integrates seamlessly with the existing platform service:

```python
from app.services.platform_service import get_platform_service

platform_service = get_platform_service()

# Post content using OAuth if available, fallback to other methods
result = await platform_service.post_to_platform(
    Platform.FACEBOOK,
    user_id="user123",
    content=post_content
)
```

## Monitoring and Maintenance

- **Connection Health**: Regular validation of platform connections
- **Token Refresh**: Automatic handling of token expiration
- **Error Tracking**: Comprehensive logging of OAuth operations
- **Performance Metrics**: Tracking of OAuth flow success rates