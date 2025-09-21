"""
Platform Preferences Service

This service handles platform-specific preferences, content templates,
and posting schedule management.
"""

from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime, time
try:
    import pytz
except ImportError:
    pytz = None

from ..models import PlatformPreferences, ContentTemplate, User
from ..services.platform_integration import Platform


class PreferencesService:
    """Service for managing platform preferences and content templates"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_preferences(self, user_id: str, platform: Platform) -> Optional[PlatformPreferences]:
        """Get user preferences for a specific platform"""
        return self.db.query(PlatformPreferences).filter(
            PlatformPreferences.user_id == user_id,
            PlatformPreferences.platform == platform.value
        ).first()
    
    def get_all_user_preferences(self, user_id: str) -> List[PlatformPreferences]:
        """Get all platform preferences for a user"""
        return self.db.query(PlatformPreferences).filter(
            PlatformPreferences.user_id == user_id
        ).all()
    
    def create_default_preferences(self, user_id: str, platform: Platform) -> PlatformPreferences:
        """Create default preferences for a platform"""
        
        # Platform-specific defaults
        defaults = self._get_platform_defaults(platform)
        
        preferences = PlatformPreferences(
            user_id=user_id,
            platform=platform.value,
            **defaults
        )
        
        self.db.add(preferences)
        self.db.commit()
        self.db.refresh(preferences)
        
        return preferences
    
    def update_preferences(
        self, 
        user_id: str, 
        platform: Platform, 
        updates: Dict[str, Any]
    ) -> PlatformPreferences:
        """Update platform preferences"""
        
        preferences = self.get_user_preferences(user_id, platform)
        if not preferences:
            preferences = self.create_default_preferences(user_id, platform)
        
        for field, value in updates.items():
            if hasattr(preferences, field):
                setattr(preferences, field, value)
        
        preferences.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(preferences)
        
        return preferences
    
    def get_posting_schedule(self, user_id: str, platform: Platform) -> Dict[str, List[str]]:
        """Get posting schedule for a platform"""
        preferences = self.get_user_preferences(user_id, platform)
        if preferences and preferences.posting_schedule:
            return preferences.posting_schedule
        
        # Return default schedule
        defaults = self._get_platform_defaults(platform)
        return defaults.get("posting_schedule", {})
    
    def get_optimal_posting_times(
        self, 
        user_id: str, 
        platform: Platform, 
        timezone: str = "UTC"
    ) -> List[time]:
        """Get optimal posting times for a platform based on user preferences"""
        
        preferences = self.get_user_preferences(user_id, platform)
        if not preferences or not preferences.optimal_times_enabled:
            return []
        
        # Get today's schedule
        if pytz:
            today = datetime.now(pytz.timezone(timezone)).strftime("%A").lower()
        else:
            today = datetime.now().strftime("%A").lower()
        schedule = self.get_posting_schedule(user_id, platform)
        
        if today not in schedule:
            return []
        
        # Convert time strings to time objects
        times = []
        for time_str in schedule[today]:
            try:
                hour, minute = map(int, time_str.split(":"))
                times.append(time(hour, minute))
            except (ValueError, AttributeError):
                continue
        
        return times
    
    def should_auto_post(self, user_id: str, platform: Platform) -> bool:
        """Check if auto-posting is enabled for a platform"""
        preferences = self.get_user_preferences(user_id, platform)
        return preferences.auto_post if preferences else True
    
    def is_platform_enabled(self, user_id: str, platform: Platform) -> bool:
        """Check if a platform is enabled for posting"""
        preferences = self.get_user_preferences(user_id, platform)
        return preferences.enabled if preferences else True
    
    def get_platform_priority(self, user_id: str, platform: Platform) -> int:
        """Get posting priority for a platform"""
        preferences = self.get_user_preferences(user_id, platform)
        return preferences.priority if preferences else 0
    
    def get_content_style(self, user_id: str, platform: Platform) -> str:
        """Get content style preference for a platform"""
        preferences = self.get_user_preferences(user_id, platform)
        if preferences and preferences.content_style:
            return preferences.content_style
        
        # Return platform default
        defaults = self._get_platform_defaults(platform)
        return defaults.get("content_style", "professional")
    
    def get_hashtag_strategy(self, user_id: str, platform: Platform) -> str:
        """Get hashtag strategy for a platform"""
        preferences = self.get_user_preferences(user_id, platform)
        if preferences and preferences.hashtag_strategy:
            return preferences.hashtag_strategy
        
        # Return platform default
        defaults = self._get_platform_defaults(platform)
        return defaults.get("hashtag_strategy", "mixed")
    
    def get_max_hashtags(self, user_id: str, platform: Platform) -> int:
        """Get maximum hashtags for a platform"""
        preferences = self.get_user_preferences(user_id, platform)
        if preferences and preferences.max_hashtags:
            return preferences.max_hashtags
        
        # Return platform default
        defaults = self._get_platform_defaults(platform)
        return defaults.get("max_hashtags", 10)
    
    def get_platform_settings(self, user_id: str, platform: Platform) -> Dict[str, Any]:
        """Get platform-specific settings"""
        preferences = self.get_user_preferences(user_id, platform)
        if preferences and preferences.platform_settings:
            return preferences.platform_settings
        
        # Return platform defaults
        defaults = self._get_platform_defaults(platform)
        return defaults.get("platform_settings", {})
    
    def format_content_for_platform(
        self, 
        user_id: str, 
        platform: Platform, 
        title: str, 
        description: str
    ) -> Dict[str, str]:
        """Format content according to platform preferences"""
        
        preferences = self.get_user_preferences(user_id, platform)
        
        # Get format templates
        title_format = preferences.title_format if preferences else "{title}"
        description_format = preferences.description_format if preferences else "{description}"
        
        # Apply formatting
        formatted_title = title_format.format(title=title)
        formatted_description = description_format.format(description=description)
        
        # Add branding if enabled
        if preferences and preferences.include_branding:
            user = self.db.query(User).filter(User.id == user_id).first()
            if user and user.business_name:
                formatted_description += f"\n\n#{user.business_name.replace(' ', '')}"
        
        # Add call-to-action if enabled
        if preferences and preferences.include_call_to_action:
            cta_templates = {
                Platform.FACEBOOK: "Visit our page for more amazing products!",
                Platform.INSTAGRAM: "DM us for orders! 💫",
                Platform.PINTEREST: "Click to shop now!",
                Platform.ETSY: "Available in our Etsy shop!",
                Platform.SHOPIFY: "Shop now on our website!"
            }
            
            cta = cta_templates.get(platform, "Contact us for more information!")
            formatted_description += f"\n\n{cta}"
        
        return {
            "title": formatted_title,
            "description": formatted_description
        }
    
    def get_user_templates(
        self, 
        user_id: str, 
        platform: Optional[Platform] = None,
        category: Optional[str] = None,
        style: Optional[str] = None,
        include_system: bool = True
    ) -> List[ContentTemplate]:
        """Get content templates for a user"""
        
        query = self.db.query(ContentTemplate).filter(
            (ContentTemplate.user_id == user_id) |
            (ContentTemplate.is_system_template == True if include_system else False)
        )
        
        if platform:
            query = query.filter(ContentTemplate.platforms.contains([platform.value]))
        
        if category:
            query = query.filter(ContentTemplate.category == category)
        
        if style:
            query = query.filter(ContentTemplate.style == style)
        
        return query.order_by(
            ContentTemplate.is_system_template.desc(),
            ContentTemplate.is_default.desc(),
            ContentTemplate.usage_count.desc(),
            ContentTemplate.created_at.desc()
        ).all()
    
    def get_default_template(
        self, 
        user_id: str, 
        platform: Platform, 
        category: Optional[str] = None
    ) -> Optional[ContentTemplate]:
        """Get default template for a platform and category"""
        
        query = self.db.query(ContentTemplate).filter(
            (ContentTemplate.user_id == user_id) |
            (ContentTemplate.is_system_template == True),
            ContentTemplate.is_default == True,
            ContentTemplate.platforms.contains([platform.value])
        )
        
        if category:
            query = query.filter(ContentTemplate.category == category)
        
        return query.first()
    
    def create_system_templates(self):
        """Create default system templates for all platforms"""
        
        system_templates = [
            {
                "name": "Professional Product Showcase",
                "description": "Professional template for showcasing products",
                "title_template": "✨ {title} ✨",
                "description_template": "{description}\n\n🔹 High Quality\n🔹 Fast Shipping\n🔹 Customer Satisfaction Guaranteed",
                "hashtag_template": "#handmade #artisan #quality #unique #shoplocal",
                "platforms": [p.value for p in Platform],
                "style": "professional",
                "category": None,
                "is_system_template": True,
                "is_default": True
            },
            {
                "name": "Casual Social Media Post",
                "description": "Casual template for social media engagement",
                "title_template": "Check out this amazing {title}! 😍",
                "description_template": "Hey everyone! 👋\n\n{description}\n\nWhat do you think? Let me know in the comments! 💬",
                "hashtag_template": "#love #amazing #beautiful #follow #like",
                "platforms": [Platform.FACEBOOK.value, Platform.INSTAGRAM.value],
                "style": "casual",
                "category": None,
                "is_system_template": True,
                "is_default": False
            },
            {
                "name": "Marketplace Listing",
                "description": "Template optimized for marketplace platforms",
                "title_template": "{title} - Premium Quality",
                "description_template": "Product Details:\n{description}\n\n✅ Ready to Ship\n✅ Secure Packaging\n✅ Money Back Guarantee",
                "hashtag_template": "#forsale #quality #shipping #guarantee",
                "platforms": [Platform.ETSY.value, Platform.FACEBOOK_MARKETPLACE.value, Platform.SHOPIFY.value],
                "style": "professional",
                "category": None,
                "is_system_template": True,
                "is_default": False
            },
            {
                "name": "Story-driven Post",
                "description": "Template that tells the story behind the product",
                "title_template": "The Story Behind {title}",
                "description_template": "Every piece has a story... 📖\n\n{description}\n\nCrafted with love and attention to detail. Each item is unique, just like you! ✨",
                "hashtag_template": "#story #handcrafted #unique #artisan #passion",
                "platforms": [Platform.INSTAGRAM.value, Platform.PINTEREST.value, Platform.FACEBOOK.value],
                "style": "storytelling",
                "category": None,
                "is_system_template": True,
                "is_default": False
            }
        ]
        
        for template_data in system_templates:
            # Check if template already exists
            existing = self.db.query(ContentTemplate).filter(
                ContentTemplate.name == template_data["name"],
                ContentTemplate.is_system_template == True
            ).first()
            
            if not existing:
                template = ContentTemplate(
                    user_id="system",  # System templates have special user_id
                    **template_data
                )
                self.db.add(template)
        
        self.db.commit()
    
    def _get_platform_defaults(self, platform: Platform) -> Dict[str, Any]:
        """Get default settings for a platform"""
        
        defaults = {
            Platform.FACEBOOK: {
                "enabled": True,
                "auto_post": True,
                "priority": 0,
                "content_style": "professional",
                "hashtag_strategy": "branded",
                "max_hashtags": 5,
                "posting_schedule": {
                    "monday": ["09:00", "15:00"],
                    "tuesday": ["09:00", "15:00"],
                    "wednesday": ["09:00", "15:00"],
                    "thursday": ["09:00", "15:00"],
                    "friday": ["09:00", "15:00"],
                    "saturday": ["10:00"],
                    "sunday": ["10:00"]
                },
                "timezone": "UTC",
                "auto_schedule": False,
                "optimal_times_enabled": True,
                "platform_settings": {
                    "page_posting": True,
                    "story_posting": False,
                    "marketplace_posting": False
                },
                "title_format": "{title}",
                "description_format": "{description}",
                "include_branding": True,
                "include_call_to_action": True,
                "image_optimization": True,
                "watermark_enabled": False
            },
            Platform.INSTAGRAM: {
                "enabled": True,
                "auto_post": True,
                "priority": 0,
                "content_style": "storytelling",
                "hashtag_strategy": "trending",
                "max_hashtags": 30,
                "posting_schedule": {
                    "monday": ["11:00", "19:00"],
                    "tuesday": ["11:00", "19:00"],
                    "wednesday": ["11:00", "19:00"],
                    "thursday": ["11:00", "19:00"],
                    "friday": ["11:00", "19:00"],
                    "saturday": ["12:00", "20:00"],
                    "sunday": ["12:00", "20:00"]
                },
                "timezone": "UTC",
                "auto_schedule": False,
                "optimal_times_enabled": True,
                "platform_settings": {
                    "feed_posting": True,
                    "story_posting": True,
                    "reel_posting": False
                },
                "title_format": "{title}",
                "description_format": "{description}",
                "include_branding": True,
                "include_call_to_action": True,
                "image_optimization": True,
                "watermark_enabled": False
            },
            Platform.PINTEREST: {
                "enabled": True,
                "auto_post": True,
                "priority": 0,
                "content_style": "promotional",
                "hashtag_strategy": "category",
                "max_hashtags": 20,
                "posting_schedule": {
                    "monday": ["08:00", "20:00"],
                    "tuesday": ["08:00", "20:00"],
                    "wednesday": ["08:00", "20:00"],
                    "thursday": ["08:00", "20:00"],
                    "friday": ["08:00", "20:00"],
                    "saturday": ["08:00", "20:00"],
                    "sunday": ["08:00", "20:00"]
                },
                "timezone": "UTC",
                "auto_schedule": False,
                "optimal_times_enabled": True,
                "platform_settings": {
                    "rich_pins": True,
                    "board_auto_create": True
                },
                "title_format": "{title}",
                "description_format": "{description}",
                "include_branding": True,
                "include_call_to_action": True,
                "image_optimization": True,
                "watermark_enabled": False
            },
            Platform.ETSY: {
                "enabled": True,
                "auto_post": True,
                "priority": 0,
                "content_style": "professional",
                "hashtag_strategy": "category",
                "max_hashtags": 13,
                "posting_schedule": {
                    "monday": ["10:00"],
                    "tuesday": ["10:00"],
                    "wednesday": ["10:00"],
                    "thursday": ["10:00"],
                    "friday": ["10:00"],
                    "saturday": ["10:00"],
                    "sunday": ["10:00"]
                },
                "timezone": "UTC",
                "auto_schedule": False,
                "optimal_times_enabled": True,
                "platform_settings": {
                    "auto_renew": True,
                    "processing_time": "1-3 business days"
                },
                "title_format": "{title}",
                "description_format": "{description}",
                "include_branding": True,
                "include_call_to_action": True,
                "image_optimization": True,
                "watermark_enabled": False
            }
        }
        
        # Return platform-specific defaults or general defaults
        return defaults.get(platform, {
            "enabled": True,
            "auto_post": True,
            "priority": 0,
            "content_style": "professional",
            "hashtag_strategy": "mixed",
            "max_hashtags": 10,
            "posting_schedule": {
                "monday": ["09:00"],
                "tuesday": ["09:00"],
                "wednesday": ["09:00"],
                "thursday": ["09:00"],
                "friday": ["09:00"],
                "saturday": ["10:00"],
                "sunday": ["10:00"]
            },
            "timezone": "UTC",
            "auto_schedule": False,
            "optimal_times_enabled": True,
            "platform_settings": {},
            "title_format": "{title}",
            "description_format": "{description}",
            "include_branding": True,
            "include_call_to_action": True,
            "image_optimization": True,
            "watermark_enabled": False
        })


def get_preferences_service(db: Session = None) -> PreferencesService:
    """Dependency to get preferences service"""
    return PreferencesService(db)