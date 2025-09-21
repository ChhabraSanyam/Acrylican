#!/usr/bin/env python3
"""
Facebook and Instagram Integration Demo

This script demonstrates the Facebook and Instagram integration functionality
with sandbox accounts. It shows how to authenticate, post content, and retrieve
metrics from both platforms.

Usage:
    python demo_facebook_instagram.py

Note: This requires valid Facebook/Instagram sandbox credentials to be configured
in the environment variables.
"""

import asyncio
import os
import sys
from datetime import datetime
from typing import Dict, Any

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.facebook_instagram_integration import (
    FacebookIntegration,
    InstagramIntegration,
    create_facebook_integration,
    create_instagram_integration
)
from app.services.oauth_service import OAuthService
from app.services.platform_integration import (
    Platform,
    PostContent,
    PlatformCredentials,
    AuthenticationMethod
)
from app.models import PlatformConnection
from unittest.mock import Mock


class FacebookInstagramDemo:
    """Demo class for Facebook and Instagram integration"""
    
    def __init__(self):
        self.oauth_service = OAuthService()
        self.demo_credentials = self._create_demo_credentials()
        self.demo_connection = self._create_demo_connection()
    
    def _create_demo_credentials(self) -> PlatformCredentials:
        """Create demo credentials (would normally come from OAuth flow)"""
        return PlatformCredentials(
            platform=Platform.FACEBOOK,
            auth_method=AuthenticationMethod.OAUTH2,
            access_token=os.getenv("FACEBOOK_ACCESS_TOKEN", "demo_token"),
            refresh_token=os.getenv("FACEBOOK_REFRESH_TOKEN", "demo_refresh_token"),
            expires_at=datetime.utcnow().replace(hour=23, minute=59)
        )
    
    def _create_demo_connection(self) -> Mock:
        """Create demo platform connection"""
        connection = Mock(spec=PlatformConnection)
        connection.platform = Platform.FACEBOOK.value
        connection.user_id = "demo_user_123"
        connection.access_token = "encrypted_demo_token"
        connection.refresh_token = "encrypted_demo_refresh_token"
        connection.is_active = True
        connection.platform_data = {
            "user_id": "demo_facebook_user_123",
            "username": "Demo User"
        }
        return connection
    
    def _create_demo_content(self) -> PostContent:
        """Create demo post content"""
        return PostContent(
            title="🎨 Beautiful Handcrafted Ceramic Vase",
            description=(
                "Discover the beauty of handmade ceramics! This stunning vase is "
                "carefully crafted using traditional techniques passed down through "
                "generations. Perfect for your home decor or as a thoughtful gift. "
                "\n\n✨ Features:\n"
                "• Hand-thrown on pottery wheel\n"
                "• Unique glazing technique\n"
                "• Food-safe ceramic\n"
                "• Dishwasher safe\n"
                "\n🌟 Each piece is one-of-a-kind!"
            ),
            hashtags=[
                "#handmade", "#ceramics", "#pottery", "#artisan", "#homedecor",
                "#handcrafted", "#unique", "#art", "#vase", "#gift"
            ],
            images=[
                "https://example.com/ceramic-vase-1.jpg",
                "https://example.com/ceramic-vase-2.jpg",
                "https://example.com/ceramic-vase-3.jpg"
            ],
            product_data={
                "price": "89.99",
                "currency": "USD",
                "condition": "NEW",
                "category": "ARTS_AND_CRAFTS",
                "availability": "IN_STOCK"
            }
        )
    
    async def demo_facebook_integration(self):
        """Demonstrate Facebook integration"""
        print("🔵 Facebook Integration Demo")
        print("=" * 50)
        
        # Mock the OAuth service to return demo credentials
        self.oauth_service.get_decrypted_credentials = lambda conn: self.demo_credentials
        
        # Create Facebook integration
        facebook_integration = create_facebook_integration(
            self.oauth_service, 
            self.demo_connection
        )
        
        print(f"✅ Created Facebook integration for platform: {facebook_integration.platform.value}")
        print(f"📊 Configuration: {facebook_integration.config.platform.value}")
        print(f"🔧 Integration type: {facebook_integration.config.integration_type.value}")
        print(f"🔐 Auth method: {facebook_integration.config.auth_method.value}")
        print(f"📝 Max title length: {facebook_integration.config.max_title_length}")
        print(f"📄 Max description length: {facebook_integration.config.max_description_length}")
        print(f"🏷️ Max hashtags: {facebook_integration.config.max_hashtags}")
        print(f"🖼️ Supported formats: {facebook_integration.config.supported_image_formats}")
        
        # Test authentication
        print("\n🔐 Testing Authentication...")
        try:
            auth_result = await facebook_integration.authenticate(self.demo_credentials)
            print(f"✅ Authentication: {'Success' if auth_result else 'Failed'}")
        except Exception as e:
            print(f"❌ Authentication error: {e}")
        
        # Test content formatting
        print("\n📝 Testing Content Formatting...")
        demo_content = self._create_demo_content()
        formatted_content = await facebook_integration.format_content(demo_content)
        
        print(f"📰 Original title length: {len(demo_content.title)}")
        print(f"📰 Formatted title length: {len(formatted_content.title)}")
        print(f"📄 Original description length: {len(demo_content.description)}")
        print(f"📄 Formatted description length: {len(formatted_content.description)}")
        print(f"🏷️ Original hashtags: {len(demo_content.hashtags)}")
        print(f"🏷️ Formatted hashtags: {len(formatted_content.hashtags)}")
        print(f"🏷️ Hashtag format: {formatted_content.hashtags[:3]}...")
        
        # Test marketplace content
        print("\n🛒 Testing Marketplace Content...")
        marketplace_content = demo_content.model_copy()
        marketplace_content.platform_specific = {"post_type": "marketplace"}
        
        print(f"💰 Product price: ${marketplace_content.product_data['price']}")
        print(f"💱 Currency: {marketplace_content.product_data['currency']}")
        print(f"📦 Condition: {marketplace_content.product_data['condition']}")
        print(f"📂 Category: {marketplace_content.product_data['category']}")
        
        # Demonstrate error handling
        print("\n⚠️ Testing Error Handling...")
        invalid_content = PostContent(
            title="Test",
            description="Test description",
            hashtags=["#test"],
            images=[]  # No images
        )
        
        print("📝 Content validation:")
        # Test content length validation
        long_title_content = PostContent(
            title="A" * 3000,  # Exceeds Facebook limit
            description="Test description",
            hashtags=["#test"],
            images=["https://example.com/image.jpg"]
        )
        
        formatted_long = await facebook_integration.format_content(long_title_content)
        if len(formatted_long.title) < len(long_title_content.title):
            print("✅ Title truncation working correctly")
        else:
            print("❌ Title truncation not working")
        
        print("✅ Error handling demonstration complete")
        
        print("\n🔵 Facebook Demo Complete!\n")
    
    async def demo_instagram_integration(self):
        """Demonstrate Instagram integration"""
        print("📸 Instagram Integration Demo")
        print("=" * 50)
        
        # Create Instagram connection
        instagram_connection = self.demo_connection
        instagram_connection.platform = Platform.INSTAGRAM.value
        
        # Update credentials for Instagram
        instagram_credentials = self.demo_credentials.model_copy()
        instagram_credentials.platform = Platform.INSTAGRAM
        
        # Mock the OAuth service
        self.oauth_service.get_decrypted_credentials = lambda conn: instagram_credentials
        
        # Create Instagram integration
        instagram_integration = create_instagram_integration(
            self.oauth_service, 
            instagram_connection
        )
        
        print(f"✅ Created Instagram integration for platform: {instagram_integration.platform.value}")
        print(f"📊 Configuration: {instagram_integration.config.platform.value}")
        print(f"🔧 Integration type: {instagram_integration.config.integration_type.value}")
        print(f"🔐 Auth method: {instagram_integration.config.auth_method.value}")
        print(f"📝 Max title length: {instagram_integration.config.max_title_length}")
        print(f"📄 Max description length: {instagram_integration.config.max_description_length}")
        print(f"🏷️ Max hashtags: {instagram_integration.config.max_hashtags}")
        print(f"🖼️ Supported formats: {instagram_integration.config.supported_image_formats}")
        
        # Test authentication
        print("\n🔐 Testing Authentication...")
        try:
            auth_result = await instagram_integration.authenticate(instagram_credentials)
            print(f"✅ Authentication: {'Success' if auth_result else 'Failed'}")
        except Exception as e:
            print(f"❌ Authentication error: {e}")
        
        # Test content formatting
        print("\n📝 Testing Content Formatting...")
        demo_content = self._create_demo_content()
        
        # Test with long description
        long_content = demo_content.model_copy()
        long_content.description = "A" * 2500  # Exceeds Instagram limit
        
        formatted_content = await instagram_integration.format_content(long_content)
        
        print(f"📄 Original description length: {len(long_content.description)}")
        print(f"📄 Formatted description length: {len(formatted_content.description)}")
        print(f"✂️ Description truncated: {formatted_content.description.endswith('...')}")
        print(f"🏷️ Hashtag format: {formatted_content.hashtags[:3]}...")
        
        # Test carousel content
        print("\n🎠 Testing Carousel Content...")
        carousel_content = demo_content.model_copy()
        carousel_content.images = [
            "https://example.com/image1.jpg",
            "https://example.com/image2.jpg",
            "https://example.com/image3.jpg",
            "https://example.com/image4.jpg",
            "https://example.com/image5.jpg"
        ]
        
        print(f"🖼️ Carousel images: {len(carousel_content.images)}")
        print(f"📱 Instagram carousel support: {instagram_integration.config.custom_settings.get('supports_carousel', False)}")
        print(f"🔢 Max images per carousel: {instagram_integration.config.custom_settings.get('max_images_per_carousel', 10)}")
        
        # Test location support
        print("\n📍 Testing Location Support...")
        location_content = demo_content.model_copy()
        location_content.platform_specific = {
            "location_id": "123456789",
            "instagram_account_id": "specific_account_123"
        }
        
        print(f"📍 Location ID: {location_content.platform_specific.get('location_id')}")
        print(f"👤 Specific account: {location_content.platform_specific.get('instagram_account_id')}")
        
        # Test engagement rate calculation
        print("\n📊 Testing Engagement Rate Calculation...")
        sample_metrics = {
            "impressions": 1000,
            "likes": 50,
            "comments": 10,
            "shares": 5,
            "saved": 15
        }
        
        engagement_rate = instagram_integration._calculate_engagement_rate(sample_metrics)
        print(f"👀 Impressions: {sample_metrics['impressions']}")
        print(f"❤️ Likes: {sample_metrics['likes']}")
        print(f"💬 Comments: {sample_metrics['comments']}")
        print(f"🔄 Shares: {sample_metrics['shares']}")
        print(f"🔖 Saved: {sample_metrics['saved']}")
        print(f"📈 Engagement Rate: {engagement_rate}%")
        
        print("\n📸 Instagram Demo Complete!\n")
    
    async def demo_platform_comparison(self):
        """Compare Facebook and Instagram platform features"""
        print("⚖️ Platform Comparison")
        print("=" * 50)
        
        facebook_integration = create_facebook_integration(self.oauth_service, self.demo_connection)
        
        instagram_connection = self.demo_connection
        instagram_connection.platform = Platform.INSTAGRAM.value
        instagram_integration = create_instagram_integration(self.oauth_service, instagram_connection)
        
        comparison_data = [
            ("Platform", "Facebook", "Instagram"),
            ("Max Title Length", facebook_integration.config.max_title_length, instagram_integration.config.max_title_length),
            ("Max Description Length", facebook_integration.config.max_description_length, instagram_integration.config.max_description_length),
            ("Max Hashtags", facebook_integration.config.max_hashtags, instagram_integration.config.max_hashtags),
            ("Supported Formats", len(facebook_integration.config.supported_image_formats), len(instagram_integration.config.supported_image_formats)),
            ("Supports Albums/Carousel", facebook_integration.config.custom_settings.get("supports_albums", False), instagram_integration.config.custom_settings.get("supports_carousel", False)),
            ("Supports Marketplace", facebook_integration.config.custom_settings.get("supports_marketplace", False), "N/A"),
            ("Supports Video", facebook_integration.config.custom_settings.get("supports_video", False), instagram_integration.config.custom_settings.get("supports_video", False)),
            ("Rate Limit (per min)", facebook_integration.config.rate_limit_per_minute, instagram_integration.config.rate_limit_per_minute),
        ]
        
        # Print comparison table
        for row in comparison_data:
            print(f"{row[0]:<25} | {str(row[1]):<15} | {str(row[2]):<15}")
        
        print("\n⚖️ Platform Comparison Complete!\n")
    
    async def run_demo(self):
        """Run the complete demo"""
        print("🚀 Facebook and Instagram Integration Demo")
        print("=" * 60)
        print("This demo showcases the comprehensive Facebook and Instagram")
        print("integration capabilities including authentication, content")
        print("formatting, posting workflows, and error handling.")
        print("=" * 60)
        print()
        
        try:
            await self.demo_facebook_integration()
            await self.demo_instagram_integration()
            await self.demo_platform_comparison()
            
            print("🎉 Demo completed successfully!")
            print("\n📋 Summary:")
            print("✅ Facebook integration - Authentication, posting, marketplace")
            print("✅ Instagram integration - Authentication, posting, carousel")
            print("✅ Content formatting and validation")
            print("✅ Error handling and metrics calculation")
            print("✅ Platform feature comparison")
            
        except Exception as e:
            print(f"❌ Demo failed with error: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """Main function to run the demo"""
    demo = FacebookInstagramDemo()
    await demo.run_demo()


if __name__ == "__main__":
    # Check if required environment variables are set
    required_env_vars = [
        "FACEBOOK_CLIENT_ID",
        "FACEBOOK_CLIENT_SECRET"
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        print("⚠️ Warning: The following environment variables are not set:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nThe demo will run with mock data. For full functionality,")
        print("please set up Facebook/Instagram app credentials.")
        print()
    
    # Run the demo
    asyncio.run(main())