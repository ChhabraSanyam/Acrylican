# Etsy Marketplace Integration

This document provides comprehensive information about the Etsy marketplace integration implementation for the Artisan Promotion Platform.

## Overview

The Etsy integration provides full marketplace functionality including:

- **OAuth 2.0 Authentication**: Secure authentication with Etsy's API
- **Product Listing Management**: Create, update, and manage Etsy listings
- **Content Formatting**: Automatic formatting for Etsy's requirements
- **Inventory Synchronization**: Sync pricing and quantity data
- **Metrics Collection**: Retrieve listing performance data
- **Comprehensive Validation**: Ensure content meets Etsy's standards

## Architecture

### Core Components

1. **EtsyIntegration**: Main integration class with full functionality
2. **EtsyOAuthIntegration**: Wrapper for compatibility with platform framework
3. **EtsyListingData**: Data structure for listing information
4. **EtsyShopData**: Data structure for shop information
5. **EtsyAPIError**: Custom exception for Etsy-specific errors

### Integration Flow

```
User Content → Content Formatting → Validation → API Call → Etsy Listing
     ↓              ↓                    ↓           ↓           ↓
PostContent → format_content() → validate() → post_content() → PostResult
```

## Features

### 1. OAuth 2.0 Authentication

The integration uses Etsy's OAuth 2.0 flow for secure authentication:

```python
# Authentication is handled automatically through the OAuth service
integration = EtsyIntegration(oauth_service, connection)
is_authenticated = await integration.authenticate(credentials)
```

**Configuration Required:**
- `ETSY_CLIENT_ID`: Your Etsy app's client ID
- `ETSY_CLIENT_SECRET`: Your Etsy app's client secret

### 2. Product Listing Creation

Create new Etsy listings with comprehensive product data:

```python
content = PostContent(
    title="Handmade Ceramic Mug",
    description="Beautiful handcrafted ceramic mug...",
    hashtags=["handmade", "ceramic", "pottery"],
    images=["https://example.com/image1.jpg"],
    product_data={
        "price": "25.00",
        "quantity": 5,
        "category": "handmade"
    }
)

result = await integration.post_content(content)
```

### 3. Content Formatting

Automatic formatting ensures content meets Etsy's requirements:

- **Title**: Maximum 140 characters, automatically truncated
- **Description**: Maximum 13,000 characters, automatically truncated
- **Materials/Tags**: Maximum 13 items, hashtag symbols removed
- **Images**: Maximum 10 images, excess images removed

### 4. Listing Management

Update existing listings with new content, pricing, or inventory:

```python
result = await integration.update_listing(
    listing_id="123456",
    content=updated_content,
    price=Decimal("30.00"),
    quantity=10
)
```

### 5. Inventory Synchronization

Bulk update multiple listings with new inventory data:

```python
listings_data = [
    {"listing_id": "123456", "quantity": 10, "price": "25.00"},
    {"listing_id": "789012", "quantity": 5, "price": "15.00"}
]

results = await integration.sync_inventory(listings_data)
```

### 6. Metrics Collection

Retrieve performance metrics for listings:

```python
metrics = await integration.get_post_metrics("123456")
print(f"Views: {metrics.views}, Favorites: {metrics.likes}")
```

## API Limits and Constraints

### Etsy API Limits

- **Rate Limit**: 100 requests per minute
- **Title Length**: 140 characters maximum
- **Description Length**: 13,000 characters maximum
- **Materials/Tags**: 13 items maximum
- **Images**: 10 images maximum per listing
- **Price Range**: $0.20 to $50,000.00

### Content Requirements

1. **Title**: Required, non-empty, ≤ 140 characters
2. **Description**: Required, non-empty, ≤ 13,000 characters
3. **Price**: Required, between $0.20 and $50,000.00
4. **Images**: At least 1 image recommended
5. **Materials**: Optional, maximum 13 items

## Error Handling

The integration provides comprehensive error handling:

### Error Types

1. **EtsyAPIError**: Etsy-specific API errors
2. **AuthenticationError**: OAuth authentication failures
3. **ValidationError**: Content validation failures
4. **PostingError**: Listing creation/update failures

### Error Codes

- `USER_INFO_FAILED`: Failed to retrieve user information
- `SHOPS_ACCESS_FAILED`: Failed to access user's shops
- `NO_SHOPS_FOUND`: No Etsy shops found for user
- `CONTENT_VALIDATION_FAILED`: Content doesn't meet requirements
- `LISTING_CREATION_FAILED`: Failed to create listing
- `LISTING_UPDATE_FAILED`: Failed to update listing

## Configuration

### Environment Variables

```bash
# Required for OAuth authentication
ETSY_CLIENT_ID=your_etsy_client_id
ETSY_CLIENT_SECRET=your_etsy_client_secret

# Optional: Custom API settings
ETSY_API_BASE_URL=https://openapi.etsy.com/v3
ETSY_RATE_LIMIT=100
```

### Platform Configuration

```python
config = PlatformConfig(
    platform=Platform.ETSY,
    integration_type=IntegrationType.API,
    auth_method=AuthenticationMethod.OAUTH2,
    api_base_url="https://openapi.etsy.com/v3",
    max_title_length=140,
    max_description_length=13000,
    max_hashtags=13,
    supported_image_formats=["jpg", "jpeg", "png", "gif", "webp"],
    rate_limit_per_minute=100,
    max_retries=3
)
```

## Testing

### Unit Tests

Run the comprehensive test suite:

```bash
# Run all Etsy integration tests
python -m pytest tests/test_etsy_integration.py -v

# Run specific test categories
python -m pytest tests/test_etsy_integration.py::TestEtsyIntegration -v
python -m pytest tests/test_etsy_integration.py::TestEtsyAPIError -v
```

### Integration Tests

For testing with Etsy's sandbox environment:

```bash
# Run integration tests (requires sandbox credentials)
python -m pytest tests/test_etsy_integration.py -m integration -v
```

### Manual Testing

Use the manual test script for quick verification:

```bash
python test_etsy_manual.py
```

## Usage Examples

### Basic Listing Creation

```python
from app.services.etsy_integration import create_etsy_integration
from app.services.platform_integration import PostContent

# Create integration
integration = create_etsy_integration(oauth_service, connection)

# Create content
content = PostContent(
    title="Handmade Wooden Bowl",
    description="Beautiful handcrafted wooden bowl made from sustainable oak wood. Perfect for serving salads or as a decorative piece.",
    hashtags=["handmade", "wooden", "bowl", "sustainable", "oak"],
    images=[
        "https://example.com/bowl1.jpg",
        "https://example.com/bowl2.jpg"
    ],
    product_data={
        "price": "45.00",
        "quantity": 3,
        "category": "home_living"
    }
)

# Post to Etsy
result = await integration.post_content(content)

if result.status == PostStatus.SUCCESS:
    print(f"Listing created: {result.url}")
    print(f"Listing ID: {result.post_id}")
else:
    print(f"Error: {result.error_message}")
```

### Bulk Inventory Update

```python
# Get current listings
listings = await integration.get_shop_listings(state="active", limit=50)

# Prepare inventory updates
inventory_updates = []
for listing in listings:
    inventory_updates.append({
        "listing_id": listing.listing_id,
        "quantity": listing.quantity + 5,  # Add 5 to current quantity
        "price": str(float(listing.price) * 1.1)  # Increase price by 10%
    })

# Sync inventory
results = await integration.sync_inventory(inventory_updates)
print(f"Updated: {results['updated']}, Failed: {results['failed']}")
```

### Content Validation

```python
# Validate content before posting
errors = await integration._validate_listing_content(content)

if errors:
    print("Content validation failed:")
    for error in errors:
        print(f"  - {error}")
else:
    print("Content is valid for Etsy")
    result = await integration.post_content(content)
```

## Best Practices

### 1. Content Optimization

- **SEO-Friendly Titles**: Use relevant keywords within 140 characters
- **Detailed Descriptions**: Include materials, dimensions, care instructions
- **High-Quality Images**: Use all 10 image slots for better visibility
- **Relevant Tags**: Use all 13 tag slots with specific, searchable terms

### 2. Error Handling

```python
try:
    result = await integration.post_content(content)
    if result.status == PostStatus.SUCCESS:
        # Handle success
        pass
    else:
        # Handle API errors
        logger.error(f"Etsy posting failed: {result.error_message}")
except EtsyAPIError as e:
    # Handle Etsy-specific errors
    logger.error(f"Etsy API error: {e}")
except Exception as e:
    # Handle unexpected errors
    logger.error(f"Unexpected error: {e}")
```

### 3. Rate Limiting

The integration automatically handles rate limiting, but for high-volume operations:

```python
import asyncio

# Add delays between bulk operations
for batch in batches:
    await process_batch(batch)
    await asyncio.sleep(1)  # 1-second delay between batches
```

### 4. Content Formatting

Always format content before validation:

```python
# Format content for Etsy requirements
formatted_content = await integration.format_content(raw_content)

# Validate formatted content
errors = await integration._validate_listing_content(formatted_content)

if not errors:
    result = await integration.post_content(formatted_content)
```

## Troubleshooting

### Common Issues

1. **Authentication Failures**
   - Verify `ETSY_CLIENT_ID` and `ETSY_CLIENT_SECRET`
   - Check OAuth token expiration
   - Ensure proper scopes: `listings_r listings_w profile_r`

2. **Content Validation Errors**
   - Check title length (≤ 140 characters)
   - Verify price range ($0.20 - $50,000.00)
   - Ensure description is not empty

3. **API Rate Limiting**
   - Implement exponential backoff
   - Monitor rate limit headers
   - Use bulk operations when possible

4. **Image Upload Failures**
   - Verify image URLs are accessible
   - Check supported formats: JPG, PNG, GIF, WebP
   - Ensure images are under 10MB

### Debug Mode

Enable debug logging for detailed API interactions:

```python
import logging

logging.getLogger('app.services.etsy_integration').setLevel(logging.DEBUG)
```

## Security Considerations

1. **Token Storage**: OAuth tokens are encrypted at rest
2. **API Key Protection**: Never expose API keys in client-side code
3. **HTTPS Only**: All API communications use HTTPS
4. **Scope Limitation**: Request only necessary OAuth scopes
5. **Token Refresh**: Automatic token refresh prevents expiration

## Performance Optimization

1. **Connection Pooling**: Reuse HTTP connections for multiple requests
2. **Batch Operations**: Use bulk APIs when available
3. **Caching**: Cache shop data and shipping templates
4. **Async Operations**: All API calls are asynchronous
5. **Error Recovery**: Automatic retry with exponential backoff

## Support and Resources

- **Etsy API Documentation**: https://developers.etsy.com/documentation
- **OAuth 2.0 Guide**: https://developers.etsy.com/documentation/essentials/authentication
- **Rate Limiting**: https://developers.etsy.com/documentation/essentials/rate_limiting
- **Sandbox Environment**: https://developers.etsy.com/documentation/essentials/sandbox

## Changelog

### Version 1.0.0 (Current)

- ✅ OAuth 2.0 authentication
- ✅ Product listing creation and management
- ✅ Content formatting and validation
- ✅ Inventory synchronization
- ✅ Metrics collection
- ✅ Comprehensive error handling
- ✅ Unit and integration tests
- ✅ Documentation and examples

### Future Enhancements

- [ ] Webhook support for real-time updates
- [ ] Advanced analytics and reporting
- [ ] Bulk listing import/export
- [ ] Template-based listing creation
- [ ] Multi-language support