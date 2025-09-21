#!/usr/bin/env python3
"""
Pinterest Integration Demo

This script demonstrates the Pinterest Business API integration functionality,
including pin creation, board management, Rich Pins, and analytics retrieval.

Note: This is a demo script that shows the integration capabilities.
For actual usage, you would need valid Pinterest API credentials.
"""

import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from app.services.pinterest_integration import PinterestIntegration, PinterestBoardData
from app.services.platform_integration import PostContent, PlatformCredentials, Platform
from app.models import PlatformConnection


async def demo_pinterest_integration():
    """Demonstrate Pinterest integration capabilities"""
    
    print("🎨 Pinterest Business API Integration Demo")
    print("=" * 50)
    
    # Mock OAuth service and connection for demo
    mock_oauth_service = Mock()
    mock_oauth_service.get_decrypted_credentials.return_value = PlatformCredentials(
        platform=Platform.PINTEREST,
        auth_method="oauth2",
        access_token="demo_access_token",
        refresh_token="demo_refresh_token"
    )
    
    mock_connection = Mock(spec=PlatformConnection)
    mock_connection.platform = "pinterest"
    mock_connection.is_active = True
    
    # Create Pinterest integration instance
    pinterest = PinterestIntegration(mock_oauth_service, mock_connection)
    
    print("✅ Pinterest integration initialized")
    print(f"   Platform: {pinterest.platform.value}")
    print(f"   API Base URL: {pinterest.config.api_base_url}")
    print(f"   Max Title Length: {pinterest.config.max_title_length}")
    print(f"   Max Description Length: {pinterest.config.max_description_length}")
    print(f"   Supports Rich Pins: {pinterest.config.custom_settings['supports_rich_pins']}")
    print()
    
    # Demo 1: Content Formatting
    print("📝 Demo 1: Content Formatting for Pinterest")
    print("-" * 40)
    
    sample_content = PostContent(
        title="Beautiful Handmade Ceramic Vase - Perfect for Home Decor and Special Occasions",
        description="This stunning ceramic vase is handcrafted with love and attention to detail. Made from high-quality clay and finished with a beautiful glaze, it's perfect for displaying fresh flowers or as a standalone decorative piece. Each vase is unique and tells its own story.",
        hashtags=["handmade", "ceramic", "vase", "homedecor", "artisan", "pottery", "unique", "gift", "flowers", "decor"],
        images=["https://example.com/ceramic-vase.jpg"],
        product_data={
            "price": "89.99",
            "currency": "USD",
            "category": "home_decor",
            "availability": "in stock",
            "brand": "Artisan Pottery Studio"
        }
    )
    
    formatted_content = await pinterest.format_content(sample_content)
    
    print(f"Original title length: {len(sample_content.title)} chars")
    print(f"Formatted title: {formatted_content.title}")
    print(f"Formatted title length: {len(formatted_content.title)} chars")
    print()
    print(f"Original description length: {len(sample_content.description)} chars")
    print(f"Formatted description (with hashtags): {formatted_content.description[:100]}...")
    print(f"Formatted description length: {len(formatted_content.description)} chars")
    print()
    
    # Demo 2: Board Management (Mocked)
    print("📌 Demo 2: Board Management")
    print("-" * 40)
    
    # Mock board creation
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "demo_board_123",
            "name": "Handmade Ceramics",
            "description": "Beautiful handcrafted ceramic pieces",
            "privacy": "PUBLIC",
            "pin_count": 0,
            "follower_count": 0,
            "created_at": datetime.utcnow().isoformat(),
            "board_url": "https://pinterest.com/user/handmade-ceramics"
        }
        
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        
        new_board = await pinterest.create_board(
            name="Handmade Ceramics",
            description="Beautiful handcrafted ceramic pieces",
            privacy="PUBLIC"
        )
        
        if new_board:
            print(f"✅ Board created successfully!")
            print(f"   Board ID: {new_board.id}")
            print(f"   Board Name: {new_board.name}")
            print(f"   Privacy: {new_board.privacy}")
            print(f"   URL: {new_board.board_url}")
        else:
            print("❌ Board creation failed")
    print()
    
    # Demo 3: Pin Creation with Rich Pins (Mocked)
    print("📍 Demo 3: Pin Creation with Rich Pins")
    print("-" * 40)
    
    with patch('httpx.AsyncClient') as mock_client:
        # Mock boards response
        mock_boards_response = Mock()
        mock_boards_response.status_code = 200
        mock_boards_response.json.return_value = {
            "items": [
                {
                    "id": "demo_board_123",
                    "name": "Handmade Ceramics",
                    "description": "Beautiful handcrafted ceramic pieces",
                    "privacy": "PUBLIC"
                }
            ]
        }
        
        # Mock pin creation response
        mock_pin_response = Mock()
        mock_pin_response.status_code = 201
        mock_pin_response.json.return_value = {
            "id": "demo_pin_456",
            "title": formatted_content.title,
            "description": formatted_content.description,
            "url": "https://pinterest.com/pin/demo_pin_456",
            "board_id": "demo_board_123",
            "created_at": datetime.utcnow().isoformat()
        }
        
        mock_client_instance = mock_client.return_value.__aenter__.return_value
        mock_client_instance.get = AsyncMock(return_value=mock_boards_response)
        mock_client_instance.post = AsyncMock(return_value=mock_pin_response)
        
        result = await pinterest.post_content(formatted_content)
        
        if result.status.value == "success":
            print(f"✅ Pin created successfully!")
            print(f"   Pin ID: {result.post_id}")
            print(f"   Pin URL: {result.url}")
            print(f"   Board ID: {result.metadata['board_id']}")
            print(f"   Rich Pins Enabled: {result.metadata['rich_pin_enabled']}")
            print(f"   Image Optimized: {result.metadata['image_optimized']}")
        else:
            print(f"❌ Pin creation failed: {result.error_message}")
    print()
    
    # Demo 4: Analytics Retrieval (Mocked)
    print("📊 Demo 4: Analytics Retrieval")
    print("-" * 40)
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_analytics_response = Mock()
        mock_analytics_response.status_code = 200
        mock_analytics_response.json.return_value = {
            "all_time": {
                "IMPRESSION": [{"value": 2450}],
                "OUTBOUND_CLICK": [{"value": 89}],
                "PIN_CLICK": [{"value": 156}],
                "SAVE": [{"value": 67}]
            }
        }
        
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_analytics_response)
        
        metrics = await pinterest.get_post_metrics("demo_pin_456")
        
        if metrics:
            print(f"✅ Analytics retrieved successfully!")
            print(f"   Pin ID: {metrics.post_id}")
            print(f"   Views (Impressions): {metrics.views:,}")
            print(f"   Saves: {metrics.shares:,}")
            print(f"   Reach: {metrics.reach:,}")
            print(f"   Retrieved at: {metrics.retrieved_at}")
        else:
            print("❌ Analytics retrieval failed")
    print()
    
    # Demo 5: Pin Search (Mocked)
    print("🔍 Demo 5: Pin Search for Inspiration")
    print("-" * 40)
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_search_response = Mock()
        mock_search_response.status_code = 200
        mock_search_response.json.return_value = {
            "items": [
                {
                    "id": "inspiration_pin_1",
                    "title": "Handmade Ceramic Bowl Set",
                    "description": "Beautiful ceramic bowls perfect for serving",
                    "board_id": "other_board_123"
                },
                {
                    "id": "inspiration_pin_2", 
                    "title": "Artisan Pottery Collection",
                    "description": "Unique pottery pieces handcrafted with care",
                    "board_id": "other_board_456"
                }
            ]
        }
        
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_search_response)
        
        search_results = await pinterest.search_pins("handmade ceramic", limit=5)
        
        if search_results:
            print(f"✅ Found {len(search_results)} inspiration pins!")
            for i, pin in enumerate(search_results, 1):
                print(f"   {i}. {pin.title}")
                print(f"      Description: {pin.description[:50]}...")
                print(f"      Pin ID: {pin.id}")
        else:
            print("❌ Pin search failed")
    print()
    
    # Demo 6: Pinterest-Specific Features
    print("🎯 Demo 6: Pinterest-Specific Features")
    print("-" * 40)
    
    print("Pinterest Integration Features:")
    print("✅ Pin creation with proper board management")
    print("✅ Pinterest-specific image optimization")
    print("✅ Rich Pins functionality for product information")
    print("✅ Board creation and management")
    print("✅ Content formatting for Pinterest requirements")
    print("✅ Analytics and metrics retrieval")
    print("✅ Pin search for competitive analysis")
    print("✅ Pin updates and modifications")
    print("✅ Hashtag integration in descriptions")
    print("✅ Image dimension and format validation")
    print()
    
    print("Rich Pins Support:")
    print("• Product Rich Pins with pricing and availability")
    print("• Automatic meta tag preparation")
    print("• Enhanced product information display")
    print("• Better click-through rates")
    print()
    
    print("Content Optimization:")
    print(f"• Title limit: {pinterest.config.max_title_length} characters")
    print(f"• Description limit: {pinterest.config.max_description_length} characters")
    print(f"• Recommended hashtags: up to {pinterest.config.max_hashtags}")
    print(f"• Supported formats: {', '.join(pinterest.config.supported_image_formats)}")
    print(f"• Minimum image size: {pinterest.config.custom_settings['min_image_width']}x{pinterest.config.custom_settings['min_image_height']}px")
    print()
    
    print("🎉 Pinterest Integration Demo Complete!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(demo_pinterest_integration())