"""
Browser Platform Registry

Registration module for browser automation platform integrations.
Registers Meesho, Snapdeal, and IndiaMART integrations with the platform registry.
"""

import logging
from typing import Dict, List

from .platform_registry import get_platform_registry, register_platform
from .platform_integration import Platform

# Import the browser automation integrations
from .meesho_integration import MeeshoIntegration, MEESHO_CONFIG
from .snapdeal_integration import SnapdealIntegration, SNAPDEAL_CONFIG
from .indiamart_integration import IndiaMARTIntegration, INDIAMART_CONFIG

logger = logging.getLogger(__name__)


def register_browser_automation_platforms() -> Dict[Platform, bool]:
    """
    Register all browser automation platform integrations.
    
    Returns:
        Dict mapping platforms to registration success status
    """
    registry = get_platform_registry()
    registration_results = {}
    
    # Platform integrations to register
    platforms_to_register = [
        (Platform.MEESHO, MeeshoIntegration, MEESHO_CONFIG),
        (Platform.SNAPDEAL, SnapdealIntegration, SNAPDEAL_CONFIG),
        (Platform.INDIAMART, IndiaMARTIntegration, INDIAMART_CONFIG),
    ]
    
    for platform, integration_class, config in platforms_to_register:
        try:
            register_platform(platform, integration_class, config)
            registration_results[platform] = True
            logger.info(f"Successfully registered {platform.value} browser automation integration")
        except Exception as e:
            registration_results[platform] = False
            logger.error(f"Failed to register {platform.value} integration: {e}")
    
    return registration_results


def get_browser_automation_platforms() -> List[Platform]:
    """
    Get list of platforms that use browser automation.
    
    Returns:
        List of browser automation platforms
    """
    return [Platform.MEESHO, Platform.SNAPDEAL, Platform.INDIAMART]


def is_browser_automation_platform(platform: Platform) -> bool:
    """
    Check if a platform uses browser automation.
    
    Args:
        platform: Platform to check
        
    Returns:
        True if platform uses browser automation
    """
    return platform in get_browser_automation_platforms()


def get_platform_requirements(platform: Platform) -> Dict[str, any]:
    """
    Get requirements for a specific browser automation platform.
    
    Args:
        platform: Platform to get requirements for
        
    Returns:
        Dictionary of platform requirements
    """
    requirements_map = {
        Platform.MEESHO: {
            "required_fields": ["title", "description", "price", "category"],
            "optional_fields": ["brand", "color", "size", "discount", "stock_quantity"],
            "max_images": 5,
            "max_title_length": 100,
            "max_description_length": 2000,
            "supported_categories": [
                "Fashion", "Electronics", "Home & Kitchen", "Beauty & Personal Care",
                "Sports & Fitness", "Books", "Toys & Games", "Automotive"
            ],
            "authentication_method": "credentials",
            "session_duration_hours": 24
        },
        Platform.SNAPDEAL: {
            "required_fields": ["title", "description", "price", "mrp", "category", "brand"],
            "optional_fields": ["color", "size", "weight", "dimensions", "stock_quantity"],
            "max_images": 8,
            "max_title_length": 150,
            "max_description_length": 3000,
            "supported_categories": [
                "Fashion & Accessories", "Electronics", "Home & Kitchen", "Sports & Fitness",
                "Books & Media", "Toys & Games", "Automotive", "Health & Beauty"
            ],
            "authentication_method": "credentials",
            "session_duration_hours": 24,
            "supports_variants": True,
            "supports_bulk_upload": True
        },
        Platform.INDIAMART: {
            "required_fields": ["title", "description", "price", "unit", "minimum_order", "category"],
            "optional_fields": [
                "brand", "model", "material", "color", "size", "weight", 
                "country_of_origin", "payment_terms", "delivery_time"
            ],
            "max_images": 10,
            "max_title_length": 200,
            "max_description_length": 5000,
            "supported_categories": [
                "Industrial Supplies", "Machinery", "Electronics", "Chemicals",
                "Textiles", "Agriculture", "Construction", "Automotive Parts",
                "Medical Equipment", "Food & Beverages"
            ],
            "supported_units": [
                "Piece", "Set", "Pair", "Dozen", "Kilogram", "Gram", "Liter",
                "Meter", "Square Meter", "Cubic Meter", "Ton", "Box", "Carton"
            ],
            "authentication_method": "credentials",
            "session_duration_hours": 24,
            "b2b_focused": True,
            "supports_inquiries": True,
            "supports_specifications": True
        }
    }
    
    return requirements_map.get(platform, {})


def validate_content_for_platform(platform: Platform, content: dict) -> Dict[str, List[str]]:
    """
    Validate content against platform requirements.
    
    Args:
        platform: Platform to validate for
        content: Content dictionary to validate
        
    Returns:
        Dictionary with 'errors' and 'warnings' lists
    """
    requirements = get_platform_requirements(platform)
    errors = []
    warnings = []
    
    if not requirements:
        errors.append(f"Platform {platform.value} not supported")
        return {"errors": errors, "warnings": warnings}
    
    # Check required fields
    required_fields = requirements.get("required_fields", [])
    for field in required_fields:
        if not content.get(field):
            errors.append(f"Required field '{field}' is missing")
    
    # Check content length limits
    if content.get("title"):
        max_title_length = requirements.get("max_title_length", 100)
        if len(content["title"]) > max_title_length:
            errors.append(f"Title exceeds maximum length of {max_title_length} characters")
    
    if content.get("description"):
        max_description_length = requirements.get("max_description_length", 1000)
        if len(content["description"]) > max_description_length:
            errors.append(f"Description exceeds maximum length of {max_description_length} characters")
    
    # Check image count
    images = content.get("images", [])
    max_images = requirements.get("max_images", 5)
    if len(images) > max_images:
        warnings.append(f"Too many images ({len(images)}). Maximum allowed: {max_images}")
    
    # Platform-specific validations
    if platform == Platform.SNAPDEAL:
        if content.get("price") and content.get("mrp"):
            if float(content["price"]) > float(content["mrp"]):
                errors.append("Selling price cannot be higher than MRP")
    
    elif platform == Platform.INDIAMART:
        if content.get("unit"):
            supported_units = requirements.get("supported_units", [])
            if content["unit"] not in supported_units:
                warnings.append(f"Unit '{content['unit']}' may not be supported. Supported units: {', '.join(supported_units)}")
        
        if "minimum_order" in content:
            try:
                min_order = int(content["minimum_order"])
                if min_order < 1:
                    errors.append("Minimum order quantity must be at least 1")
            except (ValueError, TypeError):
                errors.append("Minimum order quantity must be a valid number")
    
    return {"errors": errors, "warnings": warnings}


def get_platform_posting_tips(platform: Platform) -> List[str]:
    """
    Get posting tips for a specific platform.
    
    Args:
        platform: Platform to get tips for
        
    Returns:
        List of posting tips
    """
    tips_map = {
        Platform.MEESHO: [
            "Use clear, descriptive titles that include key product features",
            "Include high-quality images from multiple angles",
            "Set competitive prices as Meesho customers are price-sensitive",
            "Use relevant hashtags to improve discoverability",
            "Ensure accurate product descriptions to reduce returns",
            "Consider offering discounts to attract more buyers"
        ],
        Platform.SNAPDEAL: [
            "Include brand name in the title for better visibility",
            "Provide detailed product specifications in the description",
            "Set both MRP and selling price correctly",
            "Use high-resolution images (minimum 500x500 pixels)",
            "Include product variants if available (size, color, etc.)",
            "Mention key features and benefits prominently",
            "Ensure fast shipping to improve seller ratings"
        ],
        Platform.INDIAMART: [
            "Focus on business buyers with professional product descriptions",
            "Include detailed specifications and technical details",
            "Set appropriate minimum order quantities for B2B sales",
            "Mention payment terms and delivery timelines",
            "Use business-focused keywords and industry terminology",
            "Include certifications and quality standards if applicable",
            "Respond quickly to buyer inquiries to improve conversion",
            "Consider offering bulk pricing and customization options"
        ]
    }
    
    return tips_map.get(platform, [])


# Initialize browser automation platforms on module import
def initialize_browser_platforms():
    """Initialize browser automation platforms."""
    try:
        results = register_browser_automation_platforms()
        successful_registrations = sum(1 for success in results.values() if success)
        total_platforms = len(results)
        
        logger.info(
            f"Browser automation platform registration complete: "
            f"{successful_registrations}/{total_platforms} platforms registered successfully"
        )
        
        if successful_registrations < total_platforms:
            failed_platforms = [
                platform.value for platform, success in results.items() 
                if not success
            ]
            logger.warning(f"Failed to register platforms: {', '.join(failed_platforms)}")
        
        return results
        
    except Exception as e:
        logger.error(f"Failed to initialize browser automation platforms: {e}")
        return {}


# Auto-initialize when module is imported
_initialization_results = initialize_browser_platforms()