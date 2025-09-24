"""
Content Generation Service using Google Gemini API.

This service handles AI-powered content generation for marketing copy,
including titles, descriptions, and hashtags optimized for different platforms.
"""

import google.generativeai as genai
import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json
import time
from ..config import settings

# Configure logging
logger = logging.getLogger(__name__)

class Platform(str, Enum):
    """Supported platforms for content generation."""
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    FACEBOOK_MARKETPLACE = "facebook_marketplace"
    ETSY = "etsy"
    PINTEREST = "pinterest"
    SHOPIFY = "shopify"

@dataclass
class ContentInput:
    """Input data for content generation."""
    description: str
    business_context: Dict[str, Any]
    target_platforms: List[str]
    product_category: Optional[str] = None
    price_range: Optional[str] = None
    target_audience: Optional[str] = None

@dataclass
class GeneratedContent:
    """Generated content for a product."""
    title: str
    description: str
    hashtags: List[str]
    variations: List[Dict[str, Any]]
    platform_specific: Dict[str, Dict[str, Any]]

class ContentGenerationError(Exception):
    """Custom exception for content generation errors."""
    pass

class ContentGenerationService:
    """Service for AI-powered content generation using Google Gemini."""
    
    def __init__(self):
        """Initialize the content generation service."""
        self.api_key = settings.gemini_api_key
        self.model_name = "gemini-2.5-flash"
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds
        
        if not self.api_key:
            logger.warning("Gemini API key not configured. Content generation will not work.")
            self.model = None
            return
            
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
            logger.info(f"Gemini API client initialized successfully with model {self.model_name}")
            
            # Test the API connection with a simple call
            test_response = self.model.generate_content("Test connection")
            if test_response and hasattr(test_response, 'text'):
                logger.info("Gemini API connection test successful")
            else:
                logger.warning("Gemini API connection test returned empty response")
                
        except Exception as e:
            logger.error(f"Failed to initialize Gemini API client: {e}")
            logger.error(f"API Key configured: {'Yes' if self.api_key else 'No'}")
            logger.error(f"API Key length: {len(self.api_key) if self.api_key else 0}")
            self.model = None
            # Don't raise here, let the service handle it gracefully
    
    async def generate_content(self, input_data: ContentInput) -> GeneratedContent:
        """
        Generate marketing content for a product.
        
        Args:
            input_data: Input data containing product description and context
            
        Returns:
            GeneratedContent: Generated marketing content
            
        Raises:
            ContentGenerationError: If content generation fails
        """
        if not self.api_key:
            raise ContentGenerationError("Gemini API key not configured")
        
        if not self.model:
            raise ContentGenerationError("Gemini API client not initialized")
        
        try:
            # Generate base content
            base_content = await self._generate_base_content(input_data)
            
            # Generate platform-specific variations
            platform_content = await self._generate_platform_variations(
                base_content, input_data.target_platforms
            )
            
            return GeneratedContent(
                title=base_content["title"],
                description=base_content["description"],
                hashtags=base_content["hashtags"],
                variations=base_content.get("variations", []),
                platform_specific=platform_content
            )
            
        except ContentGenerationError:
            # Re-raise content generation errors as-is
            raise
        except Exception as e:
            logger.error(f"Content generation failed: {e}")
            raise ContentGenerationError(f"Failed to generate content: {e}")
    
    async def _generate_base_content(self, input_data: ContentInput) -> Dict[str, Any]:
        """Generate base marketing content."""
        prompt = self._create_base_content_prompt(input_data)
        
        response = await self._call_gemini_with_retry(prompt)
        return self._parse_content_response(response)
    
    async def _generate_platform_variations(
        self, 
        base_content: Dict[str, Any], 
        platforms: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Generate platform-specific content variations."""
        platform_content = {}
        
        # Create tasks for parallel execution
        tasks = []
        valid_platforms = []
        
        for platform in platforms:
            if platform in Platform.__members__.values():
                valid_platforms.append(platform)
                task = self._generate_single_platform_content(base_content, platform)
                tasks.append(task)
        
        # Execute all platform content generation in parallel
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                platform = valid_platforms[i]
                if isinstance(result, Exception):
                    logger.warning(f"Failed to generate content for {platform}: {result}")
                    # Use base content as fallback
                    platform_content[platform] = self._format_for_platform(base_content, platform)
                else:
                    platform_content[platform] = result
        
        return platform_content
    
    async def _generate_single_platform_content(
        self, 
        base_content: Dict[str, Any], 
        platform: str
    ) -> Dict[str, Any]:
        """Generate content for a single platform."""
        try:
            # Add timeout for individual platform generation
            prompt = self._create_platform_prompt(base_content, platform)
            response = await asyncio.wait_for(
                self._call_gemini_with_retry(prompt, max_retries=2), 
                timeout=20.0  # 20 second timeout per platform
            )
            return self._parse_platform_response(response, platform)
        except asyncio.TimeoutError:
            logger.warning(f"Timeout generating content for {platform}, using fallback")
            return self._format_for_platform(base_content, platform)
        except Exception as e:
            logger.warning(f"Failed to generate content for {platform}: {e}")
            # Use base content as fallback
            return self._format_for_platform(base_content, platform)
    
    def _create_base_content_prompt(self, input_data: ContentInput) -> str:
        """Create prompt for base content generation."""
        business_info = input_data.business_context
        
        prompt = f"""
You are an expert marketing copywriter specializing in handcrafted artisan products. 
Create compelling marketing content for the following product:

Product Description: {input_data.description}

Business Context:
- Business Name: {business_info.get('business_name', 'N/A')}
- Business Type: {business_info.get('business_type', 'N/A')}
- Business Description: {business_info.get('business_description', 'N/A')}
- Location: {business_info.get('location', 'N/A')}

Additional Context:
- Product Category: {input_data.product_category or 'Not specified'}
- Price Range: {input_data.price_range or 'Not specified'}
- Target Audience: {input_data.target_audience or 'General audience'}

Generate marketing content with the following requirements:
1. Create an engaging, professional title (max 100 characters)
2. Write a compelling product description (200-500 words) that highlights:
   - Unique craftsmanship and artisan story
   - Quality materials and techniques
   - Benefits and use cases
   - Emotional connection and authenticity
3. Generate 15-20 relevant hashtags including:
   - Product-specific tags
   - Artisan/handmade tags
   - Material/technique tags
   - Lifestyle/use case tags
4. Create 3 alternative title variations for A/B testing

Format your response as valid JSON with this structure:
{{
    "title": "Main product title",
    "description": "Detailed product description",
    "hashtags": ["#hashtag1", "#hashtag2", ...],
    "variations": [
        {{"title": "Alternative title 1", "focus": "benefit-focused"}},
        {{"title": "Alternative title 2", "focus": "emotion-focused"}},
        {{"title": "Alternative title 3", "focus": "feature-focused"}}
    ]
}}

Ensure the content is authentic, engaging, and emphasizes the handcrafted nature and artisan story.
"""
        return prompt
    
    def _create_platform_prompt(self, base_content: Dict[str, Any], platform: str) -> str:
        """Create platform-specific content prompt."""
        platform_specs = self._get_platform_specifications(platform)
        
        prompt = f"""
Quickly adapt this marketing content for {platform.upper()}:

Original: Title: {base_content['title']}
Description: {base_content['description'][:200]}...
Hashtags: {', '.join(base_content['hashtags'][:10])}

{platform_specs}

Adapt for {platform.upper()} - be concise and direct. Return only JSON:
{{
    "title": "Platform-optimized title",
    "description": "Platform-optimized description", 
    "hashtags": ["#hashtag1", "#hashtag2"],
    "call_to_action": "Platform CTA",
    "character_count": {{"title": 0, "description": 0}},
    "optimization_notes": "Brief notes"
}}
"""
        return prompt
    
    def _get_platform_specifications(self, platform: str) -> str:
        """Get platform-specific content specifications."""
        specs = {
            Platform.FACEBOOK: """
- Title: 60-100 characters for optimal engagement
- Description: 1-2 paragraphs, conversational tone
- Hashtags: 3-5 hashtags maximum, avoid over-tagging
- Focus: Community engagement, storytelling
- CTA: Encourage comments, shares, or page visits
""",
            Platform.INSTAGRAM: """
- Title: Can be longer, first 125 characters show in feed
- Description: Up to 2,200 characters, use line breaks for readability
- Hashtags: 20-30 hashtags, mix popular and niche tags
- Focus: Visual storytelling, lifestyle integration
- CTA: Encourage saves, shares, or profile visits
""",
            Platform.FACEBOOK_MARKETPLACE: """
- Title: 80 characters max, clear and descriptive
- Description: Detailed product info, condition, materials
- Hashtags: Not typically used, focus on keywords in description
- Focus: Product details, pricing, local appeal
- CTA: Clear purchase or contact information
""",
            Platform.ETSY: """
- Title: 140 characters, SEO-optimized with keywords
- Description: Detailed product story, materials, dimensions, care instructions
- Hashtags: Use as tags, 13 tags maximum, focus on searchable terms
- Focus: Craftsmanship, uniqueness, gift potential
- CTA: Encourage favorites, reviews, or custom orders
""",
            Platform.PINTEREST: """
- Title: 100 characters max, keyword-rich for search
- Description: 500 characters max, include keywords and benefits
- Hashtags: 2-5 hashtags, focus on searchable terms
- Focus: Inspiration, DIY appeal, seasonal relevance
- CTA: Encourage saves, clicks to website
""",
            Platform.SHOPIFY: """
- Title: SEO-optimized product name, clear and descriptive
- Description: Comprehensive product details, benefits, specifications
- Hashtags: Use as product tags for internal organization
- Focus: Product benefits, quality, customer satisfaction
- CTA: Clear purchase path, related products
""",

        }
        
        return specs.get(platform, "General social media best practices apply.")
    
    async def _call_gemini_with_retry(self, prompt: str, max_retries: int = None) -> str:
        """Call Gemini API with retry logic."""
        retries = max_retries if max_retries is not None else self.max_retries
        last_exception = None
        
        for attempt in range(retries):
            try:
                # Add delay between retries (exponential backoff)
                if attempt > 0:
                    delay = self.retry_delay * (2 ** (attempt - 1))
                    logger.info(f"Retrying Gemini API call in {delay} seconds (attempt {attempt + 1})")
                    await asyncio.sleep(delay)
                
                logger.info(f"Making Gemini API call (attempt {attempt + 1}/{retries})")
                
                # Make the API call
                response = await asyncio.to_thread(
                    self.model.generate_content, prompt
                )
                
                logger.info(f"Gemini API response received: {type(response)}")
                
                if response and hasattr(response, 'text') and response.text:
                    logger.info("Successfully extracted text from response")
                    return response.text
                elif response and hasattr(response, 'candidates') and response.candidates:
                    logger.info(f"Response has {len(response.candidates)} candidates")
                    # Handle case where response has candidates but no direct text
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'content') and candidate.content:
                        if hasattr(candidate.content, 'parts') and candidate.content.parts:
                            text = candidate.content.parts[0].text
                            logger.info("Successfully extracted text from candidate")
                            return text
                    logger.error("Response candidate has no text content")
                    raise ContentGenerationError("Response candidate has no text content")
                else:
                    logger.error(f"Empty or invalid response: {response}")
                    raise ContentGenerationError("Empty or invalid response from Gemini API")
                    
            except Exception as e:
                last_exception = e
                logger.warning(f"Gemini API call attempt {attempt + 1} failed: {type(e).__name__}: {e}")
                
                # Check for specific API errors
                error_str = str(e).lower()
                if "api_key_invalid" in error_str or "authentication" in error_str or "401" in error_str:
                    raise ContentGenerationError(f"Invalid Gemini API key: {e}")
                elif "quota" in error_str or "rate limit" in error_str or "429" in error_str:
                    raise ContentGenerationError(f"Gemini API quota exceeded: {e}")
                elif "safety" in error_str or "blocked" in error_str:
                    raise ContentGenerationError(f"Content blocked by safety filters: {e}")
                elif "404" in error_str or "not found" in error_str:
                    raise ContentGenerationError(f"Gemini model not found - check model name: {e}")
                
                if attempt == retries - 1:
                    logger.error(f"All {retries} attempts failed")
                    break
        
        raise ContentGenerationError(f"Gemini API call failed after {retries} attempts: {last_exception}")
    
    def _parse_content_response(self, response: str) -> Dict[str, Any]:
        """Parse and validate the content generation response."""
        try:
            # Clean the response (remove markdown code blocks if present)
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()
            
            # Parse JSON
            content = json.loads(cleaned_response)
            
            # Validate required fields
            required_fields = ["title", "description", "hashtags"]
            for field in required_fields:
                if field not in content:
                    raise ValueError(f"Missing required field: {field}")
            
            # Ensure hashtags is a list
            if not isinstance(content["hashtags"], list):
                content["hashtags"] = []
            
            # Ensure variations is a list
            if "variations" not in content:
                content["variations"] = []
            
            return content
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response content: {response}")
            raise ContentGenerationError(f"Invalid JSON response from Gemini API: {e}")
        except Exception as e:
            logger.error(f"Failed to validate response: {e}")
            raise ContentGenerationError(f"Invalid response format: {e}")
    
    def _parse_platform_response(self, response: str, platform: str) -> Dict[str, Any]:
        """Parse platform-specific content response."""
        try:
            # Clean and parse JSON response
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()
            
            content = json.loads(cleaned_response)
            
            # Validate and set defaults
            content.setdefault("title", "")
            content.setdefault("description", "")
            content.setdefault("hashtags", [])
            content.setdefault("call_to_action", "")
            content.setdefault("character_count", {"title": 0, "description": 0})
            content.setdefault("optimization_notes", "")
            
            return content
            
        except Exception as e:
            logger.warning(f"Failed to parse platform response for {platform}: {e}")
            # Return empty structure as fallback
            return {
                "title": "",
                "description": "",
                "hashtags": [],
                "call_to_action": "",
                "character_count": {"title": 0, "description": 0},
                "optimization_notes": f"Failed to generate platform-specific content: {e}"
            }
    
    def _format_for_platform(self, base_content: Dict[str, Any], platform: str) -> Dict[str, Any]:
        """Format base content for a specific platform as fallback."""
        # Basic platform-specific formatting rules
        title = base_content["title"]
        description = base_content["description"]
        hashtags = base_content["hashtags"][:10]  # Limit hashtags
        
        # Platform-specific adjustments
        if platform == Platform.FACEBOOK:
            hashtags = hashtags[:5]  # Facebook prefers fewer hashtags
        elif platform == Platform.INSTAGRAM:
            hashtags = base_content["hashtags"][:20]  # Instagram allows more hashtags
        elif platform == Platform.FACEBOOK_MARKETPLACE:
            hashtags = []  # Marketplace doesn't use hashtags
        
        return {
            "title": title,
            "description": description,
            "hashtags": hashtags,
            "call_to_action": "Learn more about this handcrafted item!",
            "character_count": {
                "title": len(title),
                "description": len(description)
            },
            "optimization_notes": f"Fallback formatting applied for {platform}"
        }

# Global service instance
content_generation_service = ContentGenerationService()