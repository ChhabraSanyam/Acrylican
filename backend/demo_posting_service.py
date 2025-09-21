#!/usr/bin/env python3
"""
Demo script for the unified posting service.

This script demonstrates the key features of the posting service including:
- Post creation and management
- Scheduling optimization
- Queue processing simulation
- Platform integration
"""

import asyncio
from datetime import datetime, timedelta
from app.services.posting_service import PostingService
from app.services.queue_processor import SchedulingService
from app.services.platform_integration import Platform, PostContent, PostResult, PostStatus
from app.schemas import PostCreate


def demo_scheduling_service():
    """Demonstrate scheduling service functionality."""
    print("=== Scheduling Service Demo ===")
    
    scheduling_service = SchedulingService()
    
    # 1. Get optimal posting times
    platforms = ["facebook", "instagram", "etsy", "pinterest"]
    print(f"\n1. Getting optimal posting times for: {', '.join(platforms)}")
    
    optimal_times = scheduling_service.get_optimal_posting_times(platforms, days_ahead=3)
    
    for platform, times in optimal_times.items():
        print(f"\n{platform.upper()}:")
        for i, time in enumerate(times[:3]):  # Show first 3 times
            hours_from_now = (time - datetime.utcnow()).total_seconds() / 3600
            print(f"  {time.strftime('%Y-%m-%d %H:%M')} ({hours_from_now:.1f}h from now)")
    
    # 2. Get next optimal time for a specific platform
    print(f"\n2. Next optimal time for Facebook:")
    next_time = scheduling_service.get_next_optimal_time("facebook")
    hours_from_now = (next_time - datetime.utcnow()).total_seconds() / 3600
    print(f"   {next_time.strftime('%Y-%m-%d %H:%M')} ({hours_from_now:.1f}h from now)")
    
    # 3. Suggest staggered schedule
    print(f"\n3. Staggered schedule for multiple platforms:")
    start_time = datetime.utcnow() + timedelta(hours=2)
    staggered = scheduling_service.suggest_staggered_schedule(
        platforms, start_time, stagger_minutes=20
    )
    
    for platform, time in staggered.items():
        print(f"   {platform}: {time.strftime('%H:%M')}")
    
    # 4. Get posting recommendations
    print(f"\n4. General posting recommendations:")
    mock_db = None  # In real usage, this would be a database session
    analysis = scheduling_service.analyze_posting_patterns("demo_user", mock_db)
    
    for recommendation in analysis["recommendations"][:3]:
        print(f"   • {recommendation}")


def demo_post_content():
    """Demonstrate post content creation and formatting."""
    print("\n=== Post Content Demo ===")
    
    # Create sample post content
    content = PostContent(
        title="Handcrafted Silver Jewelry Set",
        description="Beautiful handmade silver jewelry featuring intricate patterns inspired by traditional craftsmanship. Perfect for special occasions or as a thoughtful gift.",
        hashtags=["#handmade", "#silver", "#jewelry", "#artisan", "#crafted", "#traditional"],
        images=[
            "https://example.com/jewelry-set-1.jpg",
            "https://example.com/jewelry-set-2.jpg",
            "https://example.com/jewelry-detail.jpg"
        ],
        product_data={
            "price": "$89.99",
            "category": "Jewelry",
            "materials": ["Sterling Silver", "Natural Stones"],
            "dimensions": "Necklace: 18 inches, Earrings: 1.5 inches"
        }
    )
    
    print(f"Title: {content.title}")
    print(f"Description: {content.description[:100]}...")
    print(f"Hashtags: {', '.join(content.hashtags)}")
    print(f"Images: {len(content.images)} images")
    print(f"Price: {content.product_data['price']}")
    print(f"Category: {content.product_data['category']}")


def demo_post_results():
    """Demonstrate post result tracking."""
    print("\n=== Post Results Demo ===")
    
    # Simulate posting results from different platforms
    results = [
        PostResult(
            platform=Platform.FACEBOOK,
            status=PostStatus.SUCCESS,
            post_id="fb_123456789",
            url="https://facebook.com/post/123456789",
            published_at=datetime.utcnow(),
            metadata={"likes": 45, "shares": 12, "comments": 8}
        ),
        PostResult(
            platform=Platform.INSTAGRAM,
            status=PostStatus.SUCCESS,
            post_id="ig_987654321",
            url="https://instagram.com/p/987654321",
            published_at=datetime.utcnow(),
            metadata={"likes": 127, "comments": 23}
        ),
        PostResult(
            platform=Platform.ETSY,
            status=PostStatus.FAILED,
            error_message="Product category not allowed",
            error_code="CATEGORY_RESTRICTED",
            retry_count=1
        ),
        PostResult(
            platform=Platform.PINTEREST,
            status=PostStatus.SUCCESS,
            post_id="pin_456789123",
            url="https://pinterest.com/pin/456789123",
            published_at=datetime.utcnow(),
            metadata={"saves": 89, "clicks": 156}
        )
    ]
    
    successful = [r for r in results if r.status == PostStatus.SUCCESS]
    failed = [r for r in results if r.status == PostStatus.FAILED]
    
    print(f"Posting Results Summary:")
    print(f"  ✅ Successful: {len(successful)}/{len(results)} platforms")
    print(f"  ❌ Failed: {len(failed)}/{len(results)} platforms")
    
    print(f"\nDetailed Results:")
    for result in results:
        status_icon = "✅" if result.status == PostStatus.SUCCESS else "❌"
        print(f"  {status_icon} {result.platform.value.upper()}")
        
        if result.status == PostStatus.SUCCESS:
            print(f"     Post ID: {result.post_id}")
            if result.metadata:
                engagement = []
                if "likes" in result.metadata:
                    engagement.append(f"{result.metadata['likes']} likes")
                if "shares" in result.metadata:
                    engagement.append(f"{result.metadata['shares']} shares")
                if "comments" in result.metadata:
                    engagement.append(f"{result.metadata['comments']} comments")
                if "saves" in result.metadata:
                    engagement.append(f"{result.metadata['saves']} saves")
                if engagement:
                    print(f"     Engagement: {', '.join(engagement)}")
        else:
            print(f"     Error: {result.error_message}")
            if result.retry_count > 0:
                print(f"     Retries: {result.retry_count}")


def demo_platform_coverage():
    """Demonstrate platform coverage and capabilities."""
    print("\n=== Platform Coverage Demo ===")
    
    platforms_info = {
        "facebook": {
            "type": "Social Media",
            "integration": "API (Graph API)",
            "auth": "OAuth 2.0",
            "features": ["Posts", "Marketplace", "Pages"]
        },
        "instagram": {
            "type": "Social Media", 
            "integration": "API (Graph API)",
            "auth": "OAuth 2.0",
            "features": ["Posts", "Stories", "Business Profile"]
        },
        "etsy": {
            "type": "Marketplace",
            "integration": "API (REST API)",
            "auth": "OAuth 1.0a",
            "features": ["Product Listings", "Shop Management"]
        },
        "pinterest": {
            "type": "Social Media",
            "integration": "API (Business API)",
            "auth": "OAuth 2.0", 
            "features": ["Pins", "Boards", "Rich Pins"]
        },
        "shopify": {
            "type": "E-commerce",
            "integration": "API (Admin API)",
            "auth": "OAuth 2.0",
            "features": ["Products", "Inventory", "Orders"]
        },
        "meesho": {
            "type": "Marketplace",
            "integration": "Browser Automation",
            "auth": "Session-based",
            "features": ["Product Listings", "Seller Dashboard"]
        },
        "snapdeal": {
            "type": "Marketplace",
            "integration": "Browser Automation", 
            "auth": "Session-based",
            "features": ["Product Listings", "Inventory Management"]
        },
        "indiamart": {
            "type": "B2B Marketplace",
            "integration": "Browser Automation",
            "auth": "Session-based", 
            "features": ["Product Catalog", "Business Listings"]
        }
    }
    
    print(f"Supported Platforms ({len(platforms_info)} total):")
    print()
    
    # Group by integration type
    api_platforms = []
    automation_platforms = []
    
    for platform, info in platforms_info.items():
        if "API" in info["integration"]:
            api_platforms.append((platform, info))
        else:
            automation_platforms.append((platform, info))
    
    print("📡 API-Based Platforms:")
    for platform, info in api_platforms:
        print(f"   {platform.upper()}")
        print(f"     Type: {info['type']}")
        print(f"     Integration: {info['integration']}")
        print(f"     Auth: {info['auth']}")
        print(f"     Features: {', '.join(info['features'])}")
        print()
    
    print("🤖 Browser Automation Platforms:")
    for platform, info in automation_platforms:
        print(f"   {platform.upper()}")
        print(f"     Type: {info['type']}")
        print(f"     Integration: {info['integration']}")
        print(f"     Auth: {info['auth']}")
        print(f"     Features: {', '.join(info['features'])}")
        print()


def demo_queue_processing():
    """Demonstrate queue processing concepts."""
    print("\n=== Queue Processing Demo ===")
    
    # Simulate queue items
    queue_items = [
        {
            "id": "queue_001",
            "post_id": "post_123",
            "platform": "facebook",
            "status": "pending",
            "scheduled_at": datetime.utcnow() + timedelta(minutes=30),
            "priority": 5
        },
        {
            "id": "queue_002", 
            "post_id": "post_123",
            "platform": "instagram",
            "status": "pending",
            "scheduled_at": datetime.utcnow() + timedelta(minutes=45),
            "priority": 5
        },
        {
            "id": "queue_003",
            "post_id": "post_124", 
            "platform": "etsy",
            "status": "failed",
            "scheduled_at": datetime.utcnow() - timedelta(minutes=15),
            "priority": 3,
            "retry_count": 1,
            "error": "Rate limit exceeded"
        },
        {
            "id": "queue_004",
            "post_id": "post_125",
            "platform": "pinterest", 
            "status": "completed",
            "scheduled_at": datetime.utcnow() - timedelta(hours=2),
            "priority": 2,
            "completed_at": datetime.utcnow() - timedelta(hours=1, minutes=45)
        }
    ]
    
    print("Queue Status:")
    print()
    
    # Group by status
    pending = [item for item in queue_items if item["status"] == "pending"]
    failed = [item for item in queue_items if item["status"] == "failed"]
    completed = [item for item in queue_items if item["status"] == "completed"]
    
    print(f"📋 Pending Items ({len(pending)}):")
    for item in pending:
        time_until = item["scheduled_at"] - datetime.utcnow()
        minutes_until = time_until.total_seconds() / 60
        print(f"   {item['platform'].upper()} - Priority {item['priority']} - In {minutes_until:.0f} minutes")
    
    print(f"\n❌ Failed Items ({len(failed)}):")
    for item in failed:
        print(f"   {item['platform'].upper()} - Retry {item['retry_count']} - {item['error']}")
    
    print(f"\n✅ Completed Items ({len(completed)}):")
    for item in completed:
        completed_ago = datetime.utcnow() - item["completed_at"]
        hours_ago = completed_ago.total_seconds() / 3600
        print(f"   {item['platform'].upper()} - Completed {hours_ago:.1f}h ago")
    
    print(f"\nQueue Statistics:")
    print(f"   Total Items: {len(queue_items)}")
    print(f"   Success Rate: {len(completed)}/{len(queue_items)} ({len(completed)/len(queue_items)*100:.1f}%)")
    print(f"   Items Needing Attention: {len(failed)}")


def main():
    """Run all demos."""
    print("🚀 Unified Posting Service Demo")
    print("=" * 50)
    
    demo_scheduling_service()
    demo_post_content()
    demo_post_results()
    demo_platform_coverage()
    demo_queue_processing()
    
    print("\n" + "=" * 50)
    print("✨ Demo completed! The unified posting service provides:")
    print("   • Intelligent scheduling across 8+ platforms")
    print("   • Queue management with retry logic")
    print("   • Both API and browser automation support")
    print("   • Comprehensive result tracking")
    print("   • Optimal timing recommendations")


if __name__ == "__main__":
    main()