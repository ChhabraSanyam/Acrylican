"""
Shopify E-commerce Integration

This module provides comprehensive integration with Shopify's Admin API for creating and managing
products, handling inventory synchronization, order tracking, and retrieving sales metrics.
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Union
import httpx
from sqlalchemy.orm import Session

from .platform_integration import (
    APIBasedIntegration,
    Platform,
    PlatformConfig,
    PostContent,
    PostResult,
    PostStatus,
    PlatformMetrics,
    PlatformCredentials,
    AuthenticationMethod,
    IntegrationType,
    PlatformIntegrationError
)
from .oauth_service import OAuthService
from ..models import PlatformConnection
import logging

logger = logging.getLogger(__name__)


class ShopifyAPIError(PlatformIntegrationError):
    """Shopify-specific API error"""
    
    def __init__(self, message: str, status_code: Optional[int] = None, error_code: Optional[str] = None):
        super().__init__(message, Platform.SHOPIFY, error_code)
        self.status_code = status_code


class ShopifyProductData:
    """Data structure for Shopify product information"""
    
    def __init__(self, data: Dict[str, Any]):
        self.product_id = data.get("id")
        self.title = data.get("title")
        self.body_html = data.get("body_html")
        self.vendor = data.get("vendor")
        self.product_type = data.get("product_type")
        self.handle = data.get("handle")
        self.status = data.get("status")  # active, archived, draft
        self.published_at = data.get("published_at")
        self.created_at = data.get("created_at")
        self.updated_at = data.get("updated_at")
        self.tags = data.get("tags", "").split(",") if data.get("tags") else []
        self.variants = data.get("variants", [])
        self.images = data.get("images", [])
        self.options = data.get("options", [])
        
        # Extract pricing from first variant
        if self.variants:
            first_variant = self.variants[0]
            self.price = first_variant.get("price")
            self.compare_at_price = first_variant.get("compare_at_price")
            self.inventory_quantity = first_variant.get("inventory_quantity", 0)
            self.sku = first_variant.get("sku")
            self.barcode = first_variant.get("barcode")
            self.weight = first_variant.get("weight")
            self.weight_unit = first_variant.get("weight_unit")
        else:
            self.price = None
            self.compare_at_price = None
            self.inventory_quantity = 0
            self.sku = None
            self.barcode = None
            self.weight = None
            self.weight_unit = None


class ShopifyShopData:
    """Data structure for Shopify shop information"""
    
    def __init__(self, data: Dict[str, Any]):
        shop_data = data.get("shop", data)  # Handle both wrapped and unwrapped responses
        self.shop_id = shop_data.get("id")
        self.name = shop_data.get("name")
        self.email = shop_data.get("email")
        self.domain = shop_data.get("domain")
        self.myshopify_domain = shop_data.get("myshopify_domain")
        self.currency = shop_data.get("currency")
        self.money_format = shop_data.get("money_format")
        self.timezone = shop_data.get("timezone")
        self.plan_name = shop_data.get("plan_name")
        self.plan_display_name = shop_data.get("plan_display_name")
        self.country_code = shop_data.get("country_code")
        self.country_name = shop_data.get("country_name")
        self.province_code = shop_data.get("province_code")
        self.province = shop_data.get("province")
        self.created_at = shop_data.get("created_at")
        self.updated_at = shop_data.get("updated_at")


class ShopifyOrderData:
    """Data structure for Shopify order information"""
    
    def __init__(self, data: Dict[str, Any]):
        self.order_id = data.get("id")
        self.order_number = data.get("order_number")
        self.name = data.get("name")  # Order name like #1001
        self.email = data.get("email")
        self.created_at = data.get("created_at")
        self.updated_at = data.get("updated_at")
        self.cancelled_at = data.get("cancelled_at")
        self.closed_at = data.get("closed_at")
        self.processed_at = data.get("processed_at")
        
        # Financial information
        self.currency = data.get("currency")
        self.total_price = data.get("total_price")
        self.subtotal_price = data.get("subtotal_price")
        self.total_tax = data.get("total_tax")
        self.total_discounts = data.get("total_discounts")
        self.total_shipping = data.get("total_shipping_price_set", {}).get("shop_money", {}).get("amount")
        
        # Status information
        self.financial_status = data.get("financial_status")  # pending, authorized, paid, etc.
        self.fulfillment_status = data.get("fulfillment_status")  # fulfilled, partial, unfulfilled
        
        # Line items
        self.line_items = data.get("line_items", [])
        
        # Customer information
        self.customer = data.get("customer", {})


class ShopifyIntegration(APIBasedIntegration):
    """
    Comprehensive Shopify e-commerce integration.
    
    Provides full functionality for:
    - OAuth 2.0 authentication
    - Product creation and management
    - Inventory synchronization
    - Order tracking and sales metrics
    - Content formatting and validation
    """
    
    # Shopify API constants
    API_VERSION = "2023-10"
    
    # Shopify product limits and constraints
    MAX_TITLE_LENGTH = 255
    MAX_DESCRIPTION_LENGTH = 65535  # HTML description
    MAX_TAGS = 250
    MAX_IMAGES = 250
    MIN_PRICE = Decimal("0.01")
    MAX_PRICE = Decimal("999999.99")
    MAX_VARIANTS = 100
    
    # Shopify product statuses
    PRODUCT_STATUSES = ["active", "archived", "draft"]
    
    def __init__(self, oauth_service: OAuthService, connection: PlatformConnection):
        # Extract shop domain from connection data
        shop_domain = None
        if connection.platform_data:
            shop_domain = connection.platform_data.get("shop_domain")
        
        if not shop_domain:
            raise ValueError("Shop domain is required for Shopify integration")
        
        base_url = f"https://{shop_domain}.myshopify.com/admin/api/{self.API_VERSION}"
        
        config = PlatformConfig(
            platform=Platform.SHOPIFY,
            integration_type=IntegrationType.API,
            auth_method=AuthenticationMethod.OAUTH2,
            api_base_url=base_url,
            api_version=self.API_VERSION,
            max_title_length=self.MAX_TITLE_LENGTH,
            max_description_length=self.MAX_DESCRIPTION_LENGTH,
            max_hashtags=self.MAX_TAGS,
            supported_image_formats=["jpg", "jpeg", "png", "gif", "webp"],
            rate_limit_per_minute=40,  # Shopify rate limit (2 requests per second)
            max_retries=3,
            retry_delay_seconds=2,
            custom_settings={"shop_domain": shop_domain}
        )
        super().__init__(config)
        self.oauth_service = oauth_service
        self.connection = connection
        self.shop_domain = shop_domain
        self._shop_data: Optional[ShopifyShopData] = None
    
    async def authenticate(self, credentials: PlatformCredentials) -> bool:
        """
        Authenticate with Shopify using OAuth 2.0.
        
        Args:
            credentials: OAuth credentials
            
        Returns:
            True if authentication successful
        """
        try:
            # Validate connection by making a test API call
            return await self.validate_connection()
        except Exception as e:
            self.logger.error(f"Shopify authentication failed: {e}")
            return False
    
    async def validate_connection(self) -> bool:
        """
        Validate Shopify connection by testing API access.
        
        Returns:
            True if connection is valid
        """
        if not self.connection:
            return False
        
        try:
            credentials = self.oauth_service.get_decrypted_credentials(self.connection)
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.api_base_url}/shop.json",
                    headers=self._get_auth_headers(credentials.access_token),
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    # Cache shop data for later use
                    shop_data = response.json()
                    self._shop_data = ShopifyShopData(shop_data)
                    return True
                else:
                    self.logger.warning(f"Shopify connection validation failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Shopify connection validation failed: {e}")
            return False
    
    async def post_content(self, content: PostContent) -> PostResult:
        """
        Create a new Shopify product from content.
        
        Args:
            content: Content to post as product
            
        Returns:
            PostResult with product creation status
        """
        try:
            credentials = self.oauth_service.get_decrypted_credentials(self.connection)
            
            # Ensure we have shop data
            if not self._shop_data:
                await self.validate_connection()
            
            if not self._shop_data:
                return PostResult(
                    platform=self.platform,
                    status=PostStatus.FAILED,
                    error_message="Unable to load Shopify shop data",
                    error_code="SHOP_DATA_UNAVAILABLE"
                )
            
            # Format content for Shopify
            formatted_content = await self.format_content(content)
            
            # Validate content
            validation_errors = await self._validate_product_content(formatted_content)
            if validation_errors:
                return PostResult(
                    platform=self.platform,
                    status=PostStatus.FAILED,
                    error_message=f"Content validation failed: {'; '.join(validation_errors)}",
                    error_code="CONTENT_VALIDATION_FAILED"
                )
            
            # Create the product
            product_data = await self._prepare_product_data(formatted_content)
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.config.api_base_url}/products.json",
                    headers=self._get_auth_headers(credentials.access_token),
                    json={"product": product_data},
                    timeout=60.0
                )
                
                if response.status_code == 201:
                    result_data = response.json()
                    product = result_data["product"]
                    product_id = product["id"]
                    handle = product["handle"]
                    
                    return PostResult(
                        platform=self.platform,
                        status=PostStatus.SUCCESS,
                        post_id=str(product_id),
                        url=f"https://{self.shop_domain}.myshopify.com/products/{handle}",
                        published_at=datetime.utcnow(),
                        metadata={
                            "shop_domain": self.shop_domain,
                            "shop_name": self._shop_data.name,
                            "product_handle": handle,
                            "product_status": product.get("status"),
                            "variants_created": len(product.get("variants", [])),
                            "images_uploaded": len(product.get("images", []))
                        }
                    )
                else:
                    error_data = response.json() if response.content else {}
                    return PostResult(
                        platform=self.platform,
                        status=PostStatus.FAILED,
                        error_message=f"Shopify product creation failed: {error_data.get('errors', response.text)}",
                        error_code="PRODUCT_CREATION_FAILED"
                    )
                    
        except Exception as e:
            self.logger.error(f"Shopify product creation failed: {e}")
            return PostResult(
                platform=self.platform,
                status=PostStatus.FAILED,
                error_message=str(e),
                error_code="POSTING_EXCEPTION"
            )
    
    async def get_post_metrics(self, post_id: str) -> Optional[PlatformMetrics]:
        """
        Get metrics for a Shopify product.
        
        Args:
            post_id: Shopify product ID
            
        Returns:
            PlatformMetrics with product performance data
        """
        try:
            credentials = self.oauth_service.get_decrypted_credentials(self.connection)
            
            # Get product data
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.api_base_url}/products/{post_id}.json",
                    headers=self._get_auth_headers(credentials.access_token),
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    product = ShopifyProductData(data["product"])
                    
                    # Get sales data for this product (last 30 days)
                    sales_data = await self._get_product_sales(credentials.access_token, post_id)
                    
                    return PlatformMetrics(
                        platform=self.platform,
                        post_id=post_id,
                        views=sales_data.get("views", 0),  # Shopify doesn't provide view metrics directly
                        retrieved_at=datetime.utcnow()
                    )
                else:
                    self.logger.warning(f"Failed to get Shopify product metrics: {response.status_code}")
                    
        except Exception as e:
            self.logger.error(f"Shopify metrics retrieval failed: {e}")
            
        return None
    
    async def format_content(self, content: PostContent) -> PostContent:
        """
        Format content according to Shopify requirements.
        
        Args:
            content: Original content
            
        Returns:
            Formatted content for Shopify
        """
        formatted_content = content.model_copy()
        
        # Format title (max 255 characters)
        if len(formatted_content.title) > self.MAX_TITLE_LENGTH:
            formatted_content.title = formatted_content.title[:252] + "..."
        
        # Format description as HTML (max 65,535 characters)
        description = formatted_content.description
        if len(description) > self.MAX_DESCRIPTION_LENGTH:
            description = description[:self.MAX_DESCRIPTION_LENGTH - 3] + "..."
        
        # Convert plain text to basic HTML
        if not description.startswith('<'):
            description = description.replace('\n', '<br>')
            description = f"<p>{description}</p>"
        
        formatted_content.description = description
        
        # Format tags (Shopify uses comma-separated tags, not hashtags)
        formatted_content.hashtags = [
            tag.lstrip('#').strip() for tag in content.hashtags[:self.MAX_TAGS]
        ]
        
        # Limit images to reasonable number (Shopify supports up to 250)
        if len(formatted_content.images) > 20:  # Practical limit for initial creation
            formatted_content.images = formatted_content.images[:20]
        
        return formatted_content
    
    async def update_product(
        self,
        product_id: str,
        content: PostContent,
        price: Optional[Decimal] = None,
        inventory_quantity: Optional[int] = None
    ) -> PostResult:
        """
        Update an existing Shopify product.
        
        Args:
            product_id: Shopify product ID to update
            content: Updated content
            price: New price (optional)
            inventory_quantity: New inventory quantity (optional)
            
        Returns:
            PostResult with update status
        """
        try:
            credentials = self.oauth_service.get_decrypted_credentials(self.connection)
            
            # Format content
            formatted_content = await self.format_content(content)
            
            # Prepare update data
            update_data = {
                "title": formatted_content.title,
                "body_html": formatted_content.description,
                "tags": ", ".join(formatted_content.hashtags)
            }
            
            # Update product
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{self.config.api_base_url}/products/{product_id}.json",
                    headers=self._get_auth_headers(credentials.access_token),
                    json={"product": update_data},
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    result_data = response.json()
                    product = result_data["product"]
                    
                    # Update variant pricing/inventory if specified
                    if price is not None or inventory_quantity is not None:
                        variants = product.get("variants", [])
                        if variants:
                            variant_id = variants[0]["id"]
                            await self._update_variant(
                                credentials.access_token,
                                variant_id,
                                price,
                                inventory_quantity
                            )
                    
                    return PostResult(
                        platform=self.platform,
                        status=PostStatus.SUCCESS,
                        post_id=product_id,
                        url=f"https://{self.shop_domain}.myshopify.com/products/{product['handle']}",
                        published_at=datetime.utcnow(),
                        metadata={"action": "update"}
                    )
                else:
                    error_data = response.json() if response.content else {}
                    return PostResult(
                        platform=self.platform,
                        status=PostStatus.FAILED,
                        error_message=f"Product update failed: {error_data.get('errors', response.text)}",
                        error_code="PRODUCT_UPDATE_FAILED"
                    )
                    
        except Exception as e:
            self.logger.error(f"Shopify product update failed: {e}")
            return PostResult(
                platform=self.platform,
                status=PostStatus.FAILED,
                error_message=str(e),
                error_code="UPDATE_EXCEPTION"
            )
    
    async def get_products(
        self,
        status: str = "active",
        limit: int = 50,
        since_id: Optional[str] = None
    ) -> List[ShopifyProductData]:
        """
        Get products from the Shopify store.
        
        Args:
            status: Product status (active, archived, draft)
            limit: Number of products to retrieve (max 250)
            since_id: Retrieve products after this ID
            
        Returns:
            List of ShopifyProductData objects
        """
        try:
            credentials = self.oauth_service.get_decrypted_credentials(self.connection)
            
            params = {
                "status": status,
                "limit": min(limit, 250)  # Shopify max limit
            }
            
            if since_id:
                params["since_id"] = since_id
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.api_base_url}/products.json",
                    headers=self._get_auth_headers(credentials.access_token),
                    params=params,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return [ShopifyProductData(product) for product in data.get("products", [])]
                else:
                    self.logger.warning(f"Failed to get products: {response.status_code}")
                    return []
                    
        except Exception as e:
            self.logger.error(f"Failed to get products: {e}")
            return []
    
    async def sync_inventory(self, products_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Synchronize inventory data with Shopify products.
        
        Args:
            products_data: List of product data with inventory updates
            
        Returns:
            Dictionary with sync results
        """
        results = {
            "updated": 0,
            "failed": 0,
            "errors": []
        }
        
        try:
            credentials = self.oauth_service.get_decrypted_credentials(self.connection)
            
            for product_data in products_data:
                product_id = product_data.get("product_id")
                variant_id = product_data.get("variant_id")
                inventory_quantity = product_data.get("inventory_quantity")
                price = product_data.get("price")
                
                if not product_id:
                    results["failed"] += 1
                    results["errors"].append("Missing product_id")
                    continue
                
                try:
                    # If no variant_id provided, get the first variant
                    if not variant_id:
                        variant_id = await self._get_first_variant_id(credentials.access_token, product_id)
                    
                    if variant_id:
                        success = await self._update_variant(
                            credentials.access_token,
                            variant_id,
                            price,
                            inventory_quantity
                        )
                        
                        if success:
                            results["updated"] += 1
                        else:
                            results["failed"] += 1
                            results["errors"].append(f"Product {product_id}: Update failed")
                    else:
                        results["failed"] += 1
                        results["errors"].append(f"Product {product_id}: No variants found")
                    
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append(f"Product {product_id}: {str(e)}")
                    
        except Exception as e:
            self.logger.error(f"Inventory sync failed: {e}")
            results["errors"].append(f"General error: {str(e)}")
        
        return results
    
    async def get_orders(
        self,
        status: str = "any",
        financial_status: str = "any",
        fulfillment_status: str = "any",
        created_at_min: Optional[datetime] = None,
        created_at_max: Optional[datetime] = None,
        limit: int = 50
    ) -> List[ShopifyOrderData]:
        """
        Get orders from the Shopify store.
        
        Args:
            status: Order status (open, closed, cancelled, any)
            financial_status: Financial status (authorized, pending, paid, etc.)
            fulfillment_status: Fulfillment status (shipped, partial, unshipped, any)
            created_at_min: Minimum creation date
            created_at_max: Maximum creation date
            limit: Number of orders to retrieve (max 250)
            
        Returns:
            List of ShopifyOrderData objects
        """
        try:
            credentials = self.oauth_service.get_decrypted_credentials(self.connection)
            
            params = {
                "status": status,
                "financial_status": financial_status,
                "fulfillment_status": fulfillment_status,
                "limit": min(limit, 250)
            }
            
            if created_at_min:
                params["created_at_min"] = created_at_min.isoformat()
            
            if created_at_max:
                params["created_at_max"] = created_at_max.isoformat()
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.api_base_url}/orders.json",
                    headers=self._get_auth_headers(credentials.access_token),
                    params=params,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return [ShopifyOrderData(order) for order in data.get("orders", [])]
                else:
                    self.logger.warning(f"Failed to get orders: {response.status_code}")
                    return []
                    
        except Exception as e:
            self.logger.error(f"Failed to get orders: {e}")
            return []
    
    def _get_auth_headers(self, access_token: str) -> Dict[str, str]:
        """Get authentication headers for Shopify API requests"""
        return {
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json"
        }
    
    async def _validate_product_content(self, content: PostContent) -> List[str]:
        """Validate product content against Shopify requirements"""
        errors = []
        
        # Title validation
        if not content.title or len(content.title.strip()) == 0:
            errors.append("Title is required")
        elif len(content.title) > self.MAX_TITLE_LENGTH:
            errors.append(f"Title exceeds {self.MAX_TITLE_LENGTH} characters")
        
        # Description validation
        if not content.description or len(content.description.strip()) == 0:
            errors.append("Description is required")
        elif len(content.description) > self.MAX_DESCRIPTION_LENGTH:
            errors.append(f"Description exceeds {self.MAX_DESCRIPTION_LENGTH} characters")
        
        # Price validation
        if content.product_data:
            price_str = content.product_data.get("price")
            if price_str:
                try:
                    price = Decimal(str(price_str))
                    if price < self.MIN_PRICE:
                        errors.append(f"Price must be at least ${self.MIN_PRICE}")
                    elif price > self.MAX_PRICE:
                        errors.append(f"Price cannot exceed ${self.MAX_PRICE}")
                except (ValueError, TypeError):
                    errors.append("Invalid price format")
        
        return errors
    
    async def _prepare_product_data(self, content: PostContent) -> Dict[str, Any]:
        """Prepare product data for Shopify API"""
        # Get price from product data or use default
        price = "10.00"  # Default price
        if content.product_data and content.product_data.get("price"):
            price = str(content.product_data["price"])
        
        # Get inventory quantity from product data or use default
        inventory_quantity = 1
        if content.product_data and content.product_data.get("quantity"):
            inventory_quantity = int(content.product_data["quantity"])
        
        # Get product type and vendor from product data
        product_type = ""
        vendor = self._shop_data.name if self._shop_data else ""
        
        if content.product_data:
            product_type = content.product_data.get("product_type", "")
            vendor = content.product_data.get("vendor", vendor)
        
        # Create product data
        product_data = {
            "title": content.title,
            "body_html": content.description,
            "vendor": vendor,
            "product_type": product_type,
            "tags": ", ".join(content.hashtags),
            "status": "active",
            "variants": [
                {
                    "price": price,
                    "inventory_quantity": inventory_quantity,
                    "inventory_management": "shopify",
                    "inventory_policy": "deny"  # Don't allow overselling
                }
            ]
        }
        
        # Add images if provided
        if content.images:
            product_data["images"] = [
                {"src": image_url} for image_url in content.images
            ]
        
        # Add SEO fields if provided in product data
        if content.product_data:
            if content.product_data.get("seo_title"):
                product_data["seo_title"] = content.product_data["seo_title"]
            
            if content.product_data.get("seo_description"):
                product_data["seo_description"] = content.product_data["seo_description"]
            
            # Add weight if provided
            if content.product_data.get("weight"):
                product_data["variants"][0]["weight"] = content.product_data["weight"]
                product_data["variants"][0]["weight_unit"] = content.product_data.get("weight_unit", "kg")
            
            # Add SKU if provided
            if content.product_data.get("sku"):
                product_data["variants"][0]["sku"] = content.product_data["sku"]
        
        return product_data
    
    async def _get_product_sales(self, access_token: str, product_id: str) -> Dict[str, Any]:
        """Get sales data for a specific product"""
        try:
            # Get orders containing this product (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.api_base_url}/orders.json",
                    headers=self._get_auth_headers(access_token),
                    params={
                        "status": "any",
                        "created_at_min": thirty_days_ago.isoformat(),
                        "limit": 250
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    orders = data.get("orders", [])
                    
                    # Count sales for this product
                    sales_count = 0
                    total_revenue = Decimal("0")
                    
                    for order in orders:
                        for line_item in order.get("line_items", []):
                            if str(line_item.get("product_id")) == str(product_id):
                                sales_count += line_item.get("quantity", 0)
                                total_revenue += Decimal(str(line_item.get("price", "0"))) * line_item.get("quantity", 0)
                    
                    return {
                        "sales_count": sales_count,
                        "total_revenue": float(total_revenue),
                        "views": 0  # Shopify doesn't provide view metrics
                    }
                    
        except Exception as e:
            self.logger.error(f"Failed to get product sales data: {e}")
        
        return {"sales_count": 0, "total_revenue": 0, "views": 0}
    
    async def _update_variant(
        self,
        access_token: str,
        variant_id: str,
        price: Optional[Decimal] = None,
        inventory_quantity: Optional[int] = None
    ) -> bool:
        """Update a product variant"""
        try:
            update_data = {}
            
            if price is not None:
                update_data["price"] = str(price)
            
            if inventory_quantity is not None:
                update_data["inventory_quantity"] = inventory_quantity
            
            if not update_data:
                return True  # Nothing to update
            
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{self.config.api_base_url}/variants/{variant_id}.json",
                    headers=self._get_auth_headers(access_token),
                    json={"variant": update_data},
                    timeout=30.0
                )
                
                return response.status_code == 200
                
        except Exception as e:
            self.logger.error(f"Failed to update variant {variant_id}: {e}")
            return False
    
    async def _get_first_variant_id(self, access_token: str, product_id: str) -> Optional[str]:
        """Get the first variant ID for a product"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.api_base_url}/products/{product_id}.json",
                    headers=self._get_auth_headers(access_token),
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    variants = data.get("product", {}).get("variants", [])
                    if variants:
                        return str(variants[0]["id"])
                        
        except Exception as e:
            self.logger.error(f"Failed to get variant for product {product_id}: {e}")
        
        return None


# Configuration for platform registry
SHOPIFY_CONFIG = PlatformConfig(
    platform=Platform.SHOPIFY,
    integration_type=IntegrationType.API,
    auth_method=AuthenticationMethod.OAUTH2,
    api_base_url="https://{shop}.myshopify.com/admin/api/2023-10",
    api_version="2023-10",
    max_title_length=255,
    max_description_length=65535,
    max_hashtags=250,
    supported_image_formats=["jpg", "jpeg", "png", "gif", "webp"],
    rate_limit_per_minute=40,
    max_retries=3,
    retry_delay_seconds=2
)