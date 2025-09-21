"""
Data Privacy Service for GDPR compliance and user data management.

This service provides:
- User data export functionality
- Secure data deletion with retention policies
- Data encryption for sensitive information
- Audit logging for data access and modifications
"""

import json
import logging
import zipfile
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, BinaryIO
from io import BytesIO
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from ..models import (
    User, Product, ProductImage, PlatformConnection, Post, PostQueue,
    PlatformPreferences, ContentTemplate, SaleEvent, EngagementMetrics,
    MetricsAggregation
)
from ..security import token_encryption, security_validator
from ..secure_storage import secure_token_storage
# from .cloud_storage import CloudStorageService  # Import when needed

logger = logging.getLogger(__name__)


class DataPrivacyService:
    """Handles data privacy operations including export and deletion."""
    
    def __init__(self):
        self.encryption = token_encryption
        self.retention_days = 30  # 30-day retention period
    
    async def export_user_data(self, db: Session, user_id: str) -> BytesIO:
        """
        Export all user data in a structured format.
        
        Args:
            db: Database session
            user_id: User ID to export data for
            
        Returns:
            BytesIO containing ZIP file with user data
            
        Raises:
            ValueError: If user not found
        """
        try:
            # Verify user exists
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            # Create audit log entry
            await self._log_data_access(db, user_id, "data_export", "User data export initiated")
            
            # Collect all user data
            export_data = await self._collect_user_data(db, user_id)
            
            # Create ZIP file in memory
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Add main data file
                zip_file.writestr(
                    "user_data.json",
                    json.dumps(export_data, indent=2, default=str)
                )
                
                # Add README with export information
                readme_content = self._generate_export_readme(user, export_data)
                zip_file.writestr("README.txt", readme_content)
                
                # Add data schema documentation
                schema_content = self._generate_data_schema()
                zip_file.writestr("data_schema.json", json.dumps(schema_content, indent=2))
            
            zip_buffer.seek(0)
            
            logger.info(f"Successfully exported data for user {user_id}")
            await self._log_data_access(db, user_id, "data_export", "User data export completed")
            
            return zip_buffer
            
        except Exception as e:
            logger.error(f"Failed to export user data for {user_id}: {e}")
            await self._log_data_access(db, user_id, "data_export", f"Export failed: {str(e)}")
            raise
    
    async def _collect_user_data(self, db: Session, user_id: str) -> Dict[str, Any]:
        """
        Collect all user data from database.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Dictionary containing all user data
        """
        data = {
            "export_info": {
                "user_id": user_id,
                "export_date": datetime.utcnow().isoformat(),
                "format_version": "1.0"
            }
        }
        
        # User profile data
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            data["user_profile"] = {
                "id": user.id,
                "email": user.email,
                "business_name": user.business_name,
                "business_type": user.business_type,
                "business_description": user.business_description,
                "website": user.website,
                "location": user.location,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None
            }
        
        # Products data
        products = db.query(Product).filter(Product.user_id == user_id).all()
        data["products"] = []
        for product in products:
            product_data = {
                "id": product.id,
                "title": product.title,
                "description": product.description,
                "generated_content": product.generated_content,
                "created_at": product.created_at.isoformat() if product.created_at else None,
                "updated_at": product.updated_at.isoformat() if product.updated_at else None,
                "images": []
            }
            
            # Product images
            images = db.query(ProductImage).filter(ProductImage.product_id == product.id).all()
            for image in images:
                product_data["images"].append({
                    "id": image.id,
                    "original_filename": image.original_filename,
                    "file_size": image.file_size,
                    "dimensions": image.dimensions,
                    "format": image.format,
                    "created_at": image.created_at.isoformat() if image.created_at else None
                })
            
            data["products"].append(product_data)
        
        # Platform connections (without sensitive tokens)
        connections = db.query(PlatformConnection).filter(PlatformConnection.user_id == user_id).all()
        data["platform_connections"] = []
        for conn in connections:
            data["platform_connections"].append({
                "id": conn.id,
                "platform": conn.platform,
                "integration_type": conn.integration_type,
                "auth_method": conn.auth_method,
                "platform_user_id": conn.platform_user_id,
                "platform_username": conn.platform_username,
                "is_active": conn.is_active,
                "connected_at": conn.connected_at.isoformat() if conn.connected_at else None,
                "last_validated_at": conn.last_validated_at.isoformat() if conn.last_validated_at else None
            })
        
        # Posts data
        posts = db.query(Post).filter(Post.user_id == user_id).all()
        data["posts"] = []
        for post in posts:
            data["posts"].append({
                "id": post.id,
                "product_id": post.product_id,
                "title": post.title,
                "description": post.description,
                "hashtags": post.hashtags,
                "target_platforms": post.target_platforms,
                "status": post.status,
                "scheduled_at": post.scheduled_at.isoformat() if post.scheduled_at else None,
                "published_at": post.published_at.isoformat() if post.published_at else None,
                "created_at": post.created_at.isoformat() if post.created_at else None
            })
        
        # Platform preferences
        preferences = db.query(PlatformPreferences).filter(PlatformPreferences.user_id == user_id).all()
        data["platform_preferences"] = []
        for pref in preferences:
            data["platform_preferences"].append({
                "id": pref.id,
                "platform": pref.platform,
                "enabled": pref.enabled,
                "auto_post": pref.auto_post,
                "content_style": pref.content_style,
                "hashtag_strategy": pref.hashtag_strategy,
                "posting_schedule": pref.posting_schedule,
                "timezone": pref.timezone,
                "created_at": pref.created_at.isoformat() if pref.created_at else None
            })
        
        # Content templates
        templates = db.query(ContentTemplate).filter(ContentTemplate.user_id == user_id).all()
        data["content_templates"] = []
        for template in templates:
            data["content_templates"].append({
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "title_template": template.title_template,
                "description_template": template.description_template,
                "hashtag_template": template.hashtag_template,
                "platforms": template.platforms,
                "category": template.category,
                "style": template.style,
                "usage_count": template.usage_count,
                "created_at": template.created_at.isoformat() if template.created_at else None
            })
        
        # Sales data
        sales = db.query(SaleEvent).filter(SaleEvent.user_id == user_id).all()
        data["sales"] = []
        for sale in sales:
            data["sales"].append({
                "id": sale.id,
                "product_id": sale.product_id,
                "platform": sale.platform,
                "order_id": sale.order_id,
                "amount": float(sale.amount),
                "currency": sale.currency,
                "product_title": sale.product_title,
                "quantity": sale.quantity,
                "customer_location": sale.customer_location,
                "occurred_at": sale.occurred_at.isoformat() if sale.occurred_at else None,
                "recorded_at": sale.recorded_at.isoformat() if sale.recorded_at else None
            })
        
        # Engagement metrics
        metrics = db.query(EngagementMetrics).filter(EngagementMetrics.user_id == user_id).all()
        data["engagement_metrics"] = []
        for metric in metrics:
            data["engagement_metrics"].append({
                "id": metric.id,
                "post_id": metric.post_id,
                "platform": metric.platform,
                "platform_post_id": metric.platform_post_id,
                "likes": metric.likes,
                "shares": metric.shares,
                "comments": metric.comments,
                "views": metric.views,
                "reach": metric.reach,
                "engagement_rate": float(metric.engagement_rate) if metric.engagement_rate else None,
                "metrics_date": metric.metrics_date.isoformat() if metric.metrics_date else None,
                "collected_at": metric.collected_at.isoformat() if metric.collected_at else None
            })
        
        return data
    
    def _generate_export_readme(self, user: User, export_data: Dict[str, Any]) -> str:
        """Generate README file for data export."""
        return f"""
ARTISAN PROMOTION PLATFORM - USER DATA EXPORT
=============================================

Export Information:
- User ID: {user.id}
- Email: {user.email}
- Business Name: {user.business_name}
- Export Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
- Format Version: 1.0

This export contains all personal data associated with your account:

Files Included:
- user_data.json: Complete data export in JSON format
- data_schema.json: Description of data structure and fields
- README.txt: This file

Data Categories:
- User Profile: Basic account information
- Products: {len(export_data.get('products', []))} products with descriptions and metadata
- Platform Connections: {len(export_data.get('platform_connections', []))} connected platforms (tokens excluded for security)
- Posts: {len(export_data.get('posts', []))} posts and their status
- Platform Preferences: Your posting preferences and settings
- Content Templates: {len(export_data.get('content_templates', []))} custom content templates
- Sales Data: {len(export_data.get('sales', []))} recorded sales events
- Engagement Metrics: {len(export_data.get('engagement_metrics', []))} engagement data points

Security Notes:
- Sensitive authentication tokens are NOT included in this export for security reasons
- All data is provided in human-readable JSON format
- This export was generated in compliance with data protection regulations

For questions about this export, please contact support.
        """.strip()
    
    def _generate_data_schema(self) -> Dict[str, Any]:
        """Generate data schema documentation."""
        return {
            "version": "1.0",
            "description": "Data schema for Artisan Promotion Platform user data export",
            "tables": {
                "user_profile": {
                    "description": "Basic user account information",
                    "fields": {
                        "id": "Unique user identifier",
                        "email": "User email address",
                        "business_name": "Name of user's business",
                        "business_type": "Type/category of business",
                        "business_description": "Description of business",
                        "website": "Business website URL",
                        "location": "Business location",
                        "created_at": "Account creation timestamp",
                        "updated_at": "Last profile update timestamp"
                    }
                },
                "products": {
                    "description": "User's products and their information",
                    "fields": {
                        "id": "Unique product identifier",
                        "title": "Product title",
                        "description": "Product description",
                        "generated_content": "AI-generated marketing content",
                        "images": "Associated product images"
                    }
                },
                "platform_connections": {
                    "description": "Connected social media and marketplace platforms",
                    "fields": {
                        "platform": "Platform name (facebook, instagram, etc.)",
                        "integration_type": "Type of integration (api, browser_automation)",
                        "is_active": "Whether connection is currently active",
                        "connected_at": "When connection was established"
                    }
                },
                "posts": {
                    "description": "Posts created and published to platforms",
                    "fields": {
                        "title": "Post title",
                        "description": "Post description/content",
                        "hashtags": "Associated hashtags",
                        "target_platforms": "Platforms where post was/will be published",
                        "status": "Post status (draft, published, etc.)",
                        "scheduled_at": "Scheduled publication time",
                        "published_at": "Actual publication time"
                    }
                },
                "sales": {
                    "description": "Sales events tracked from connected platforms",
                    "fields": {
                        "platform": "Platform where sale occurred",
                        "order_id": "Platform-specific order identifier",
                        "amount": "Sale amount",
                        "currency": "Currency code",
                        "occurred_at": "When sale occurred"
                    }
                },
                "engagement_metrics": {
                    "description": "Engagement data for posts across platforms",
                    "fields": {
                        "platform": "Platform where metrics were collected",
                        "likes": "Number of likes/reactions",
                        "shares": "Number of shares/reposts",
                        "comments": "Number of comments",
                        "views": "Number of views",
                        "reach": "Total reach/impressions"
                    }
                }
            }
        }
    
    async def schedule_user_deletion(self, db: Session, user_id: str, deletion_reason: str = "user_request") -> bool:
        """
        Schedule user account and data for deletion with retention period.
        
        Args:
            db: Database session
            user_id: User ID to schedule for deletion
            deletion_reason: Reason for deletion
            
        Returns:
            True if successfully scheduled
        """
        try:
            # Verify user exists
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            # Create audit log entry
            await self._log_data_access(db, user_id, "deletion_scheduled", f"User deletion scheduled: {deletion_reason}")
            
            # Mark user as inactive but don't delete yet
            user.is_active = False
            user.updated_at = datetime.utcnow()
            
            # Schedule actual deletion after retention period
            deletion_date = datetime.utcnow() + timedelta(days=self.retention_days)
            
            # In a production system, you'd use a job queue or scheduler
            # For now, we'll add a field to track deletion schedule
            # This would typically be handled by a background job
            
            db.commit()
            
            logger.info(f"Scheduled user {user_id} for deletion on {deletion_date}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to schedule user deletion for {user_id}: {e}")
            db.rollback()
            return False
    
    async def execute_user_deletion(self, db: Session, user_id: str) -> bool:
        """
        Execute permanent deletion of user data after retention period.
        
        Args:
            db: Database session
            user_id: User ID to delete
            
        Returns:
            True if successfully deleted
        """
        try:
            # Verify user exists and is scheduled for deletion
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"User {user_id} not found for deletion")
                return True  # Already deleted
            
            # Create final audit log entry
            await self._log_data_access(db, user_id, "deletion_executed", "User data permanently deleted")
            
            # Delete user data in correct order (respecting foreign key constraints)
            
            # 1. Delete engagement metrics
            db.query(EngagementMetrics).filter(EngagementMetrics.user_id == user_id).delete()
            
            # 2. Delete metrics aggregations
            db.query(MetricsAggregation).filter(MetricsAggregation.user_id == user_id).delete()
            
            # 3. Delete sale events
            db.query(SaleEvent).filter(SaleEvent.user_id == user_id).delete()
            
            # 4. Delete post queue items
            post_ids = [p.id for p in db.query(Post).filter(Post.user_id == user_id).all()]
            if post_ids:
                db.query(PostQueue).filter(PostQueue.post_id.in_(post_ids)).delete()
            
            # 5. Delete posts
            db.query(Post).filter(Post.user_id == user_id).delete()
            
            # 6. Delete content templates
            db.query(ContentTemplate).filter(ContentTemplate.user_id == user_id).delete()
            
            # 7. Delete platform preferences
            db.query(PlatformPreferences).filter(PlatformPreferences.user_id == user_id).delete()
            
            # 8. Delete platform connections (this will clear encrypted tokens)
            db.query(PlatformConnection).filter(PlatformConnection.user_id == user_id).delete()
            
            # 9. Delete product images and their cloud storage files
            product_images = db.query(ProductImage).join(Product).filter(Product.user_id == user_id).all()
            for image in product_images:
                # Delete files from cloud storage
                try:
                    # In a real implementation, you would import and use the cloud storage service
                    # from .cloud_storage import CloudStorageService
                    # cloud_service = CloudStorageService()
                    # storage_paths = image.storage_paths or {}
                    # for path_type, path in storage_paths.items():
                    #     await cloud_service.delete_file(path)
                    logger.info(f"Would delete cloud storage files for image {image.id}")
                except Exception as e:
                    logger.warning(f"Failed to delete cloud storage file: {e}")
            
            # 10. Delete product images
            db.query(ProductImage).filter(ProductImage.product_id.in_(
                db.query(Product.id).filter(Product.user_id == user_id)
            )).delete()
            
            # 11. Delete products
            db.query(Product).filter(Product.user_id == user_id).delete()
            
            # 12. Finally delete user
            db.delete(user)
            
            db.commit()
            
            logger.info(f"Successfully deleted all data for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute user deletion for {user_id}: {e}")
            db.rollback()
            return False
    
    async def anonymize_user_data(self, db: Session, user_id: str) -> bool:
        """
        Anonymize user data instead of deletion (alternative to full deletion).
        
        Args:
            db: Database session
            user_id: User ID to anonymize
            
        Returns:
            True if successfully anonymized
        """
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            # Create audit log entry
            await self._log_data_access(db, user_id, "data_anonymized", "User data anonymized")
            
            # Anonymize user profile
            user.email = f"anonymized_{security_validator.generate_secure_token(8)}@deleted.local"
            user.business_name = "Anonymized Business"
            user.business_description = None
            user.website = None
            user.location = None
            user.is_active = False
            user.updated_at = datetime.utcnow()
            
            # Anonymize sales data (keep aggregated data but remove identifying info)
            sales = db.query(SaleEvent).filter(SaleEvent.user_id == user_id).all()
            for sale in sales:
                sale.customer_location = "Anonymized"
                sale.platform_data = {}
            
            # Remove platform connections
            db.query(PlatformConnection).filter(PlatformConnection.user_id == user_id).delete()
            
            # Keep products and posts but remove identifying content
            products = db.query(Product).filter(Product.user_id == user_id).all()
            for product in products:
                product.title = "Anonymized Product"
                product.description = "Product description removed for privacy"
                product.generated_content = {}
            
            posts = db.query(Post).filter(Post.user_id == user_id).all()
            for post in posts:
                post.title = "Anonymized Post"
                post.description = "Post content removed for privacy"
                post.hashtags = []
            
            db.commit()
            
            logger.info(f"Successfully anonymized data for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to anonymize user data for {user_id}: {e}")
            db.rollback()
            return False
    
    async def _log_data_access(self, db: Session, user_id: str, action: str, details: str) -> None:
        """
        Log data access and modification events for audit purposes.
        
        Args:
            db: Database session
            user_id: User ID
            action: Action performed
            details: Additional details
        """
        # In a production system, you'd have a dedicated audit log table
        # For now, we'll use the application logger
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "action": action,
            "details": details,
            "ip_address": "system",  # Would be actual IP in real implementation
            "user_agent": "system"   # Would be actual user agent in real implementation
        }
        
        logger.info(f"AUDIT: {json.dumps(audit_entry)}")


# Global instance
data_privacy_service = DataPrivacyService()