"""
Unit tests for the content generation service.

Tests the AI-powered content generation functionality including
Gemini API integration, error handling, and retry logic.
"""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from dataclasses import asdict

from app.services.content_generation import (
    ContentGenerationService,
    ContentInput,
    GeneratedContent,
    ContentGenerationError,
    Platform
)


class TestContentGenerationService:
    """Test cases for ContentGenerationService."""
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings with API key."""
        with patch('app.services.content_generation.settings') as mock:
            mock.gemini_api_key = "test-api-key"
            yield mock
    
    @pytest.fixture
    def mock_genai(self):
        """Mock Google Generative AI module."""
        with patch('app.services.content_generation.genai') as mock:
            yield mock
    
    @pytest.fixture
    def content_input(self):
        """Sample content input for testing."""
        return ContentInput(
            description="Beautiful handcrafted wooden bowl made from sustainable oak",
            business_context={
                "business_name": "Artisan Woodworks",
                "business_type": "Handcrafted Furniture",
                "business_description": "Creating beautiful wooden items since 2010",
                "location": "Portland, Oregon"
            },
            target_platforms=["facebook", "instagram", "etsy"],
            product_category="Home Decor",
            price_range="$50-100",
            target_audience="Home decor enthusiasts"
        )
    
    @pytest.fixture
    def mock_gemini_response(self):
        """Mock Gemini API response."""
        return '''```json
{
    "title": "Handcrafted Oak Wooden Bowl - Sustainable Artisan Made",
    "description": "Transform your dining experience with this stunning handcrafted wooden bowl, meticulously carved from sustainable oak by skilled artisans. Each piece tells a unique story through its natural grain patterns and smooth, food-safe finish. Perfect for serving salads, fruits, or as a beautiful centerpiece that brings warmth and authenticity to your home.",
    "hashtags": ["#handcrafted", "#woodenbowl", "#sustainablewood", "#artisanmade", "#homedecor", "#kitchenware", "#oakwood", "#handmade", "#ecofriendly", "#uniquegifts"],
    "variations": [
        {"title": "Sustainable Oak Bowl - Handcrafted Kitchen Essential", "focus": "benefit-focused"},
        {"title": "Artisan Wooden Bowl - Brings Nature to Your Table", "focus": "emotion-focused"},
        {"title": "Premium Oak Wood Bowl - Hand-Carved by Skilled Artisans", "focus": "feature-focused"}
    ]
}
```'''
    
    @pytest.fixture
    def mock_platform_response(self):
        """Mock platform-specific response."""
        return '''```json
{
    "title": "Handcrafted Oak Bowl 🌿 Sustainable Kitchen Art",
    "description": "✨ Transform your kitchen with this stunning handcrafted oak bowl! Each piece is lovingly carved by skilled artisans using sustainable wood practices. The natural grain patterns make every bowl unique - perfect for your morning smoothie bowls or as a gorgeous centerpiece! 🏡\\n\\n🌱 Sustainably sourced oak\\n🎨 Hand-carved by artisans\\n🍽️ Food-safe finish\\n💚 Eco-friendly choice\\n\\nBring nature's beauty to your table! #SustainableLiving #HandmadeWithLove",
    "hashtags": ["#handcrafted", "#sustainablewood", "#artisanmade", "#homedecor", "#kitchenware", "#oakwood", "#handmade", "#ecofriendly", "#uniquegifts", "#woodenbowl"],
    "call_to_action": "Double-tap if you love sustainable home decor! 💚",
    "character_count": {"title": 52, "description": 487},
    "optimization_notes": "Optimized for Instagram with emojis, line breaks, and engaging tone"
}
```'''
    
    def test_init_with_api_key(self, mock_settings, mock_genai):
        """Test service initialization with valid API key."""
        mock_model = Mock()
        mock_genai.GenerativeModel.return_value = mock_model
        
        service = ContentGenerationService()
        
        assert service.api_key == "test-api-key"
        assert service.model_name == "gemini-pro"
        assert service.max_retries == 3
        mock_genai.configure.assert_called_once_with(api_key="test-api-key")
        mock_genai.GenerativeModel.assert_called_once_with("gemini-pro")
    
    def test_init_without_api_key(self):
        """Test service initialization without API key."""
        with patch('app.services.content_generation.settings') as mock_settings:
            mock_settings.gemini_api_key = ""
            
            service = ContentGenerationService()
            
            assert service.api_key == ""
    
    def test_init_with_api_error(self, mock_settings, mock_genai):
        """Test service initialization with API configuration error."""
        mock_genai.configure.side_effect = Exception("API configuration failed")
        
        with pytest.raises(ContentGenerationError, match="Failed to initialize Gemini API"):
            ContentGenerationService()
    
    @pytest.mark.asyncio
    async def test_generate_content_success(self, mock_settings, mock_genai, content_input, mock_gemini_response, mock_platform_response):
        """Test successful content generation."""
        # Setup mocks
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = mock_gemini_response
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        service = ContentGenerationService()
        
        # Mock the platform-specific generation
        with patch.object(service, '_call_gemini_with_retry') as mock_call:
            mock_call.side_effect = [mock_gemini_response, mock_platform_response, mock_platform_response, mock_platform_response]
            
            result = await service.generate_content(content_input)
            
            assert isinstance(result, GeneratedContent)
            assert result.title == "Handcrafted Oak Wooden Bowl - Sustainable Artisan Made"
            assert "handcrafted" in result.description.lower()
            assert len(result.hashtags) == 10
            assert len(result.variations) == 3
            assert "facebook" in result.platform_specific
            assert "instagram" in result.platform_specific
            assert "etsy" in result.platform_specific
    
    @pytest.mark.asyncio
    async def test_generate_content_no_api_key(self, content_input):
        """Test content generation without API key."""
        with patch('app.services.content_generation.settings') as mock_settings:
            mock_settings.gemini_api_key = ""
            
            service = ContentGenerationService()
            
            with pytest.raises(ContentGenerationError, match="Gemini API key not configured"):
                await service.generate_content(content_input)
    
    @pytest.mark.asyncio
    async def test_generate_content_api_failure(self, mock_settings, mock_genai, content_input):
        """Test content generation with API failure."""
        mock_model = Mock()
        mock_genai.GenerativeModel.return_value = mock_model
        
        service = ContentGenerationService()
        
        with patch.object(service, '_call_gemini_with_retry') as mock_call:
            mock_call.side_effect = ContentGenerationError("API call failed")
            
            with pytest.raises(ContentGenerationError, match="Failed to generate content"):
                await service.generate_content(content_input)
    
    @pytest.mark.asyncio
    async def test_call_gemini_with_retry_success(self, mock_settings, mock_genai, mock_gemini_response):
        """Test successful Gemini API call."""
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = mock_gemini_response
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        service = ContentGenerationService()
        
        result = await service._call_gemini_with_retry("test prompt")
        
        assert result == mock_gemini_response
    
    @pytest.mark.asyncio
    async def test_call_gemini_with_retry_failure(self, mock_settings, mock_genai):
        """Test Gemini API call with retries and final failure."""
        mock_model = Mock()
        mock_model.generate_content.side_effect = Exception("API error")
        mock_genai.GenerativeModel.return_value = mock_model
        
        service = ContentGenerationService()
        service.max_retries = 2  # Reduce for faster testing
        
        with pytest.raises(ContentGenerationError, match="Gemini API call failed after 2 attempts"):
            await service._call_gemini_with_retry("test prompt")
        
        # Verify retries were attempted
        assert mock_model.generate_content.call_count == 2
    
    @pytest.mark.asyncio
    async def test_call_gemini_with_retry_success_after_failure(self, mock_settings, mock_genai, mock_gemini_response):
        """Test Gemini API call succeeding after initial failures."""
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = mock_gemini_response
        
        # First call fails, second succeeds
        mock_model.generate_content.side_effect = [Exception("Temporary error"), mock_response]
        mock_genai.GenerativeModel.return_value = mock_model
        
        service = ContentGenerationService()
        
        result = await service._call_gemini_with_retry("test prompt")
        
        assert result == mock_gemini_response
        assert mock_model.generate_content.call_count == 2
    
    def test_parse_content_response_success(self, mock_settings, mock_genai, mock_gemini_response):
        """Test successful parsing of content response."""
        mock_model = Mock()
        mock_genai.GenerativeModel.return_value = mock_model
        
        service = ContentGenerationService()
        
        result = service._parse_content_response(mock_gemini_response)
        
        assert result["title"] == "Handcrafted Oak Wooden Bowl - Sustainable Artisan Made"
        assert isinstance(result["hashtags"], list)
        assert len(result["hashtags"]) == 10
        assert isinstance(result["variations"], list)
        assert len(result["variations"]) == 3
    
    def test_parse_content_response_invalid_json(self, mock_settings, mock_genai):
        """Test parsing of invalid JSON response."""
        mock_model = Mock()
        mock_genai.GenerativeModel.return_value = mock_model
        
        service = ContentGenerationService()
        
        with pytest.raises(ContentGenerationError, match="Invalid JSON response"):
            service._parse_content_response("invalid json content")
    
    def test_parse_content_response_missing_fields(self, mock_settings, mock_genai):
        """Test parsing of response with missing required fields."""
        mock_model = Mock()
        mock_genai.GenerativeModel.return_value = mock_model
        
        service = ContentGenerationService()
        
        incomplete_response = '{"title": "Test Title"}'  # Missing description and hashtags
        
        with pytest.raises(ContentGenerationError, match="Missing required field"):
            service._parse_content_response(incomplete_response)
    
    def test_parse_platform_response_success(self, mock_settings, mock_genai, mock_platform_response):
        """Test successful parsing of platform-specific response."""
        mock_model = Mock()
        mock_genai.GenerativeModel.return_value = mock_model
        
        service = ContentGenerationService()
        
        result = service._parse_platform_response(mock_platform_response, "instagram")
        
        assert result["title"] == "Handcrafted Oak Bowl 🌿 Sustainable Kitchen Art"
        assert isinstance(result["hashtags"], list)
        assert result["call_to_action"] == "Double-tap if you love sustainable home decor! 💚"
        assert "character_count" in result
    
    def test_parse_platform_response_failure(self, mock_settings, mock_genai):
        """Test parsing of invalid platform response with fallback."""
        mock_model = Mock()
        mock_genai.GenerativeModel.return_value = mock_model
        
        service = ContentGenerationService()
        
        result = service._parse_platform_response("invalid json", "facebook")
        
        # Should return fallback structure
        assert result["title"] == ""
        assert result["description"] == ""
        assert isinstance(result["hashtags"], list)
        assert "optimization_notes" in result
    
    def test_format_for_platform_facebook(self, mock_settings, mock_genai):
        """Test platform formatting for Facebook."""
        mock_model = Mock()
        mock_genai.GenerativeModel.return_value = mock_model
        
        service = ContentGenerationService()
        
        base_content = {
            "title": "Test Product",
            "description": "Test description",
            "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5", "#tag6"]
        }
        
        result = service._format_for_platform(base_content, Platform.FACEBOOK)
        
        assert result["title"] == "Test Product"
        assert len(result["hashtags"]) == 5  # Facebook limit
    
    def test_format_for_platform_instagram(self, mock_settings, mock_genai):
        """Test platform formatting for Instagram."""
        mock_model = Mock()
        mock_genai.GenerativeModel.return_value = mock_model
        
        service = ContentGenerationService()
        
        base_content = {
            "title": "Test Product",
            "description": "Test description",
            "hashtags": ["#tag" + str(i) for i in range(25)]  # 25 hashtags
        }
        
        result = service._format_for_platform(base_content, Platform.INSTAGRAM)
        
        assert result["title"] == "Test Product"
        assert len(result["hashtags"]) == 20  # Instagram limit
    
    def test_format_for_platform_marketplace(self, mock_settings, mock_genai):
        """Test platform formatting for Facebook Marketplace."""
        mock_model = Mock()
        mock_genai.GenerativeModel.return_value = mock_model
        
        service = ContentGenerationService()
        
        base_content = {
            "title": "Test Product",
            "description": "Test description",
            "hashtags": ["#tag1", "#tag2", "#tag3"]
        }
        
        result = service._format_for_platform(base_content, Platform.FACEBOOK_MARKETPLACE)
        
        assert result["title"] == "Test Product"
        assert len(result["hashtags"]) == 0  # Marketplace doesn't use hashtags
    
    def test_create_base_content_prompt(self, mock_settings, mock_genai, content_input):
        """Test creation of base content prompt."""
        mock_model = Mock()
        mock_genai.GenerativeModel.return_value = mock_model
        
        service = ContentGenerationService()
        
        prompt = service._create_base_content_prompt(content_input)
        
        assert "Beautiful handcrafted wooden bowl" in prompt
        assert "Artisan Woodworks" in prompt
        assert "Portland, Oregon" in prompt
        assert "Home Decor" in prompt
        assert "$50-100" in prompt
        assert "JSON" in prompt
    
    def test_create_platform_prompt(self, mock_settings, mock_genai):
        """Test creation of platform-specific prompt."""
        mock_model = Mock()
        mock_genai.GenerativeModel.return_value = mock_model
        
        service = ContentGenerationService()
        
        base_content = {
            "title": "Test Product",
            "description": "Test description",
            "hashtags": ["#tag1", "#tag2"]
        }
        
        prompt = service._create_platform_prompt(base_content, "instagram")
        
        assert "INSTAGRAM" in prompt
        assert "Test Product" in prompt
        assert "Test description" in prompt
        assert "#tag1" in prompt
        assert "JSON" in prompt
    
    def test_get_platform_specifications(self, mock_settings, mock_genai):
        """Test getting platform specifications."""
        mock_model = Mock()
        mock_genai.GenerativeModel.return_value = mock_model
        
        service = ContentGenerationService()
        
        # Test known platform
        specs = service._get_platform_specifications(Platform.FACEBOOK)
        assert "60-100 characters" in specs
        assert "conversational tone" in specs
        
        # Test unknown platform
        specs = service._get_platform_specifications("unknown_platform")
        assert "General social media best practices" in specs


class TestContentGenerationIntegration:
    """Integration tests for content generation functionality."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_content_generation(self):
        """Test complete content generation flow with mocked API."""
        # Mock the entire flow
        mock_response = {
            "title": "Handcrafted Wooden Bowl",
            "description": "Beautiful artisan-made wooden bowl",
            "hashtags": ["#handcrafted", "#wooden", "#artisan"],
            "variations": [
                {"title": "Premium Wooden Bowl", "focus": "quality"}
            ]
        }
        
        with patch('app.services.content_generation.settings') as mock_settings:
            mock_settings.gemini_api_key = "test-key"
            
            with patch('app.services.content_generation.genai') as mock_genai:
                mock_model = Mock()
                mock_genai.GenerativeModel.return_value = mock_model
                
                service = ContentGenerationService()
                
                with patch.object(service, '_call_gemini_with_retry') as mock_call:
                    mock_call.return_value = json.dumps(mock_response)
                    
                    content_input = ContentInput(
                        description="Test product",
                        business_context={"business_name": "Test Business"},
                        target_platforms=["facebook"]
                    )
                    
                    result = await service.generate_content(content_input)
                    
                    assert result.title == "Handcrafted Wooden Bowl"
                    assert len(result.hashtags) == 3
                    assert "facebook" in result.platform_specific