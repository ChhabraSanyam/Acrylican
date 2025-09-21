"""
Tests for platform preferences functionality
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime
from passlib.context import CryptContext

from app.main import app
from app.models import User, PlatformPreferences, ContentTemplate
from app.services.platform_integration import Platform
from app.services.preferences_service import PreferencesService

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        email="test@example.com",
        password_hash=pwd_context.hash("testpassword123"),
        business_name="Test Artisan Shop",
        business_type="Handmade Crafts"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


class TestPlatformPreferences:
    """Test platform preferences management"""

    def test_get_all_platform_preferences_creates_defaults(self, client: TestClient, test_user: User, db_session: Session):
        """Test that getting all preferences creates defaults for missing platforms"""
        
        # Login user
        login_response = client.post("/auth/login", json={
            "email": test_user.email,
            "password": "testpassword123"
        })
        token = login_response.json()["tokens"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get all preferences (should create defaults)
        response = client.get("/preferences/platforms", headers=headers)
        
        assert response.status_code == 200
        preferences_list = response.json()
        
        # Should have preferences for all platforms
        platform_names = {pref["platform"] for pref in preferences_list}
        expected_platforms = {platform.value for platform in Platform}
        assert platform_names == expected_platforms
        
        # Check that preferences were created in database
        db_preferences = db_session.query(PlatformPreferences).filter(
            PlatformPreferences.user_id == test_user.id
        ).all()
        assert len(db_preferences) == len(Platform)

    def test_get_platform_preferences_creates_default_if_missing(self, client: TestClient, test_user: User, db_session: Session):
        """Test that getting specific platform preferences creates default if missing"""
        
        # Login user
        login_response = client.post("/auth/login", json={
            "email": test_user.email,
            "password": "testpassword123"
        })
        token = login_response.json()["tokens"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get preferences for Facebook (should create default)
        response = client.get("/preferences/platforms/facebook", headers=headers)
        
        assert response.status_code == 200
        preferences = response.json()
        
        assert preferences["platform"] == "facebook"
        assert preferences["enabled"] is True
        assert preferences["auto_post"] is True
        assert preferences["content_style"] == "professional"
        assert preferences["hashtag_strategy"] == "branded"
        assert preferences["max_hashtags"] == 5
        
        # Check that preferences were created in database
        db_preferences = db_session.query(PlatformPreferences).filter(
            PlatformPreferences.user_id == test_user.id,
            PlatformPreferences.platform == "facebook"
        ).first()
        assert db_preferences is not None

    def test_create_platform_preferences(self, client: TestClient, test_user: User):
        """Test creating platform preferences"""
        
        # Login user
        login_response = client.post("/auth/login", json={
            "email": test_user.email,
            "password": "testpassword123"
        })
        token = login_response.json()["tokens"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create preferences
        preferences_data = {
            "platform": "instagram",
            "enabled": True,
            "auto_post": False,
            "priority": 5,
            "content_style": "storytelling",
            "hashtag_strategy": "trending",
            "max_hashtags": 30,
            "posting_schedule": {
                "monday": ["11:00", "19:00"],
                "tuesday": ["11:00", "19:00"]
            },
            "timezone": "America/New_York",
            "auto_schedule": True,
            "optimal_times_enabled": True,
            "include_branding": False,
            "include_call_to_action": True
        }
        
        response = client.post("/preferences/platforms/instagram", json=preferences_data, headers=headers)
        
        assert response.status_code == 200
        preferences = response.json()
        
        assert preferences["platform"] == "instagram"
        assert preferences["enabled"] is True
        assert preferences["auto_post"] is False
        assert preferences["priority"] == 5
        assert preferences["content_style"] == "storytelling"
        assert preferences["hashtag_strategy"] == "trending"
        assert preferences["max_hashtags"] == 30
        assert preferences["timezone"] == "America/New_York"
        assert preferences["auto_schedule"] is True
        assert preferences["include_branding"] is False

    def test_update_platform_preferences(self, client: TestClient, test_user: User, db_session: Session):
        """Test updating platform preferences"""
        
        # Create initial preferences
        preferences = PlatformPreferences(
            user_id=test_user.id,
            platform="pinterest",
            enabled=True,
            auto_post=True,
            priority=0,
            content_style="professional",
            hashtag_strategy="category",
            max_hashtags=20
        )
        db_session.add(preferences)
        db_session.commit()
        
        # Login user
        login_response = client.post("/auth/login", json={
            "email": test_user.email,
            "password": "testpassword123"
        })
        token = login_response.json()["tokens"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Update preferences
        update_data = {
            "enabled": False,
            "priority": 8,
            "content_style": "promotional",
            "max_hashtags": 15
        }
        
        response = client.put("/preferences/platforms/pinterest", json=update_data, headers=headers)
        
        assert response.status_code == 200
        updated_preferences = response.json()
        
        assert updated_preferences["enabled"] is False
        assert updated_preferences["priority"] == 8
        assert updated_preferences["content_style"] == "promotional"
        assert updated_preferences["max_hashtags"] == 15
        # Unchanged fields should remain the same
        assert updated_preferences["auto_post"] is True
        assert updated_preferences["hashtag_strategy"] == "category"

    def test_reset_platform_preferences(self, client: TestClient, test_user: User, db_session: Session):
        """Test resetting platform preferences to defaults"""
        
        # Create custom preferences
        preferences = PlatformPreferences(
            user_id=test_user.id,
            platform="etsy",
            enabled=False,
            auto_post=False,
            priority=10,
            content_style="casual",
            hashtag_strategy="trending",
            max_hashtags=50
        )
        db_session.add(preferences)
        db_session.commit()
        
        # Login user
        login_response = client.post("/auth/login", json={
            "email": test_user.email,
            "password": "testpassword123"
        })
        token = login_response.json()["tokens"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Reset preferences
        response = client.delete("/preferences/platforms/etsy", headers=headers)
        
        assert response.status_code == 200
        
        # Get preferences to verify reset
        get_response = client.get("/preferences/platforms/etsy", headers=headers)
        reset_preferences = get_response.json()
        
        # Should have default values for Etsy
        assert reset_preferences["enabled"] is True
        assert reset_preferences["auto_post"] is True
        assert reset_preferences["priority"] == 0
        assert reset_preferences["content_style"] == "professional"
        assert reset_preferences["hashtag_strategy"] == "category"
        assert reset_preferences["max_hashtags"] == 13

    def test_invalid_platform_returns_400(self, client: TestClient, test_user: User):
        """Test that invalid platform returns 400 error"""
        
        # Login user
        login_response = client.post("/auth/login", json={
            "email": test_user.email,
            "password": "testpassword123"
        })
        token = login_response.json()["tokens"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Try to get preferences for invalid platform
        response = client.get("/preferences/platforms/invalid_platform", headers=headers)
        
        assert response.status_code == 400
        assert "Unsupported platform" in response.json()["detail"]


class TestContentTemplates:
    """Test content template management"""

    def test_get_content_templates(self, client: TestClient, test_user: User, db_session: Session):
        """Test getting content templates"""
        
        # Create test templates
        user_template = ContentTemplate(
            user_id=test_user.id,
            name="My Custom Template",
            title_template="✨ {title} ✨",
            description_template="{description}\n\nCustom footer",
            platforms=["facebook", "instagram"],
            style="professional",
            is_system_template=False
        )
        
        system_template = ContentTemplate(
            user_id="system",
            name="System Template",
            title_template="{title}",
            description_template="{description}",
            platforms=["facebook"],
            style="professional",
            is_system_template=True
        )
        
        db_session.add_all([user_template, system_template])
        db_session.commit()
        
        # Login user
        login_response = client.post("/auth/login", json={
            "email": test_user.email,
            "password": "testpassword123"
        })
        token = login_response.json()["tokens"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get all templates
        response = client.get("/preferences/templates", headers=headers)
        
        assert response.status_code == 200
        templates = response.json()
        
        # Should include both user and system templates
        template_names = {t["name"] for t in templates}
        assert "My Custom Template" in template_names
        assert "System Template" in template_names

    def test_get_content_templates_with_filters(self, client: TestClient, test_user: User, db_session: Session):
        """Test getting content templates with filters"""
        
        # Create test templates
        facebook_template = ContentTemplate(
            user_id=test_user.id,
            name="Facebook Template",
            title_template="{title}",
            description_template="{description}",
            platforms=["facebook"],
            style="professional",
            category="jewelry"
        )
        
        instagram_template = ContentTemplate(
            user_id=test_user.id,
            name="Instagram Template",
            title_template="{title}",
            description_template="{description}",
            platforms=["instagram"],
            style="casual",
            category="clothing"
        )
        
        db_session.add_all([facebook_template, instagram_template])
        db_session.commit()
        
        # Login user
        login_response = client.post("/auth/login", json={
            "email": test_user.email,
            "password": "testpassword123"
        })
        token = login_response.json()["tokens"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Filter by platform
        response = client.get("/preferences/templates?platform=facebook", headers=headers)
        assert response.status_code == 200
        templates = response.json()
        assert len(templates) == 1
        assert templates[0]["name"] == "Facebook Template"
        
        # Filter by style
        response = client.get("/preferences/templates?style=casual", headers=headers)
        assert response.status_code == 200
        templates = response.json()
        assert len(templates) == 1
        assert templates[0]["name"] == "Instagram Template"
        
        # Filter by category
        response = client.get("/preferences/templates?category=jewelry", headers=headers)
        assert response.status_code == 200
        templates = response.json()
        assert len(templates) == 1
        assert templates[0]["name"] == "Facebook Template"

    def test_create_content_template(self, client: TestClient, test_user: User):
        """Test creating a content template"""
        
        # Login user
        login_response = client.post("/auth/login", json={
            "email": test_user.email,
            "password": "testpassword123"
        })
        token = login_response.json()["tokens"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create template
        template_data = {
            "name": "New Template",
            "description": "A test template",
            "title_template": "🌟 {title} 🌟",
            "description_template": "{description}\n\n✅ Quality Guaranteed",
            "hashtag_template": "#handmade #quality",
            "platforms": ["facebook", "instagram"],
            "category": "accessories",
            "style": "promotional",
            "is_default": True
        }
        
        response = client.post("/preferences/templates", json=template_data, headers=headers)
        
        assert response.status_code == 200
        template = response.json()
        
        assert template["name"] == "New Template"
        assert template["description"] == "A test template"
        assert template["title_template"] == "🌟 {title} 🌟"
        assert template["platforms"] == ["facebook", "instagram"]
        assert template["category"] == "accessories"
        assert template["style"] == "promotional"
        assert template["is_default"] is True
        assert template["is_system_template"] is False

    def test_update_content_template(self, client: TestClient, test_user: User, db_session: Session):
        """Test updating a content template"""
        
        # Create template
        template = ContentTemplate(
            user_id=test_user.id,
            name="Original Template",
            title_template="{title}",
            description_template="{description}",
            platforms=["facebook"],
            style="professional"
        )
        db_session.add(template)
        db_session.commit()
        db_session.refresh(template)
        
        # Login user
        login_response = client.post("/auth/login", json={
            "email": test_user.email,
            "password": "testpassword123"
        })
        token = login_response.json()["tokens"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Update template
        update_data = {
            "name": "Updated Template",
            "style": "casual",
            "platforms": ["facebook", "instagram"]
        }
        
        response = client.put(f"/preferences/templates/{template.id}", json=update_data, headers=headers)
        
        assert response.status_code == 200
        updated_template = response.json()
        
        assert updated_template["name"] == "Updated Template"
        assert updated_template["style"] == "casual"
        assert updated_template["platforms"] == ["facebook", "instagram"]
        # Unchanged fields should remain the same
        assert updated_template["title_template"] == "{title}"
        assert updated_template["description_template"] == "{description}"

    def test_delete_content_template(self, client: TestClient, test_user: User, db_session: Session):
        """Test deleting a content template"""
        
        # Create template
        template = ContentTemplate(
            user_id=test_user.id,
            name="Template to Delete",
            title_template="{title}",
            description_template="{description}",
            platforms=["facebook"],
            style="professional"
        )
        db_session.add(template)
        db_session.commit()
        db_session.refresh(template)
        
        # Login user
        login_response = client.post("/auth/login", json={
            "email": test_user.email,
            "password": "testpassword123"
        })
        token = login_response.json()["tokens"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Delete template
        response = client.delete(f"/preferences/templates/{template.id}", headers=headers)
        
        assert response.status_code == 200
        assert "deleted" in response.json()["message"]
        
        # Verify template is deleted
        get_response = client.get(f"/preferences/templates/{template.id}", headers=headers)
        assert get_response.status_code == 404

    def test_cannot_delete_system_template(self, client: TestClient, test_user: User, db_session: Session):
        """Test that system templates cannot be deleted"""
        
        # Create system template
        template = ContentTemplate(
            user_id="system",
            name="System Template",
            title_template="{title}",
            description_template="{description}",
            platforms=["facebook"],
            style="professional",
            is_system_template=True
        )
        db_session.add(template)
        db_session.commit()
        db_session.refresh(template)
        
        # Login user
        login_response = client.post("/auth/login", json={
            "email": test_user.email,
            "password": "testpassword123"
        })
        token = login_response.json()["tokens"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Try to delete system template
        response = client.delete(f"/preferences/templates/{template.id}", headers=headers)
        
        assert response.status_code == 400
        assert "Cannot delete system templates" in response.json()["detail"]

    def test_use_content_template(self, client: TestClient, test_user: User, db_session: Session):
        """Test marking a template as used"""
        
        # Create template
        template = ContentTemplate(
            user_id=test_user.id,
            name="Template to Use",
            title_template="{title}",
            description_template="{description}",
            platforms=["facebook"],
            style="professional",
            usage_count=0
        )
        db_session.add(template)
        db_session.commit()
        db_session.refresh(template)
        
        # Login user
        login_response = client.post("/auth/login", json={
            "email": test_user.email,
            "password": "testpassword123"
        })
        token = login_response.json()["tokens"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Use template
        response = client.post(f"/preferences/templates/{template.id}/use", headers=headers)
        
        assert response.status_code == 200
        
        # Verify usage count increased
        db_session.refresh(template)
        assert template.usage_count == 1


class TestPreferencesService:
    """Test preferences service functionality"""

    def test_create_default_preferences(self, db_session: Session, test_user: User):
        """Test creating default preferences for a platform"""
        
        service = PreferencesService(db_session)
        
        # Create default preferences for Facebook
        preferences = service.create_default_preferences(test_user.id, Platform.FACEBOOK)
        
        assert preferences.user_id == test_user.id
        assert preferences.platform == Platform.FACEBOOK.value
        assert preferences.enabled is True
        assert preferences.auto_post is True
        assert preferences.content_style == "professional"
        assert preferences.hashtag_strategy == "branded"
        assert preferences.max_hashtags == 5
        assert "monday" in preferences.posting_schedule
        assert preferences.timezone == "UTC"

    def test_get_posting_schedule(self, db_session: Session, test_user: User):
        """Test getting posting schedule for a platform"""
        
        service = PreferencesService(db_session)
        
        # Create preferences with custom schedule
        custom_schedule = {
            "monday": ["10:00", "16:00"],
            "tuesday": ["11:00"]
        }
        
        preferences = PlatformPreferences(
            user_id=test_user.id,
            platform=Platform.INSTAGRAM.value,
            posting_schedule=custom_schedule
        )
        db_session.add(preferences)
        db_session.commit()
        
        # Get schedule
        schedule = service.get_posting_schedule(test_user.id, Platform.INSTAGRAM)
        
        assert schedule == custom_schedule

    def test_should_auto_post(self, db_session: Session, test_user: User):
        """Test checking if auto-posting is enabled"""
        
        service = PreferencesService(db_session)
        
        # Create preferences with auto_post disabled
        preferences = PlatformPreferences(
            user_id=test_user.id,
            platform=Platform.PINTEREST.value,
            auto_post=False
        )
        db_session.add(preferences)
        db_session.commit()
        
        # Check auto-post setting
        should_auto_post = service.should_auto_post(test_user.id, Platform.PINTEREST)
        
        assert should_auto_post is False

    def test_format_content_for_platform(self, db_session: Session, test_user: User):
        """Test formatting content according to platform preferences"""
        
        service = PreferencesService(db_session)
        
        # Create preferences with custom formatting
        preferences = PlatformPreferences(
            user_id=test_user.id,
            platform=Platform.FACEBOOK.value,
            title_format="✨ {title} ✨",
            description_format="{description}\n\nVisit our page!",
            include_branding=True,
            include_call_to_action=True
        )
        db_session.add(preferences)
        db_session.commit()
        
        # Format content
        formatted = service.format_content_for_platform(
            test_user.id,
            Platform.FACEBOOK,
            "Test Product",
            "This is a test product description."
        )
        
        assert formatted["title"] == "✨ Test Product ✨"
        assert "This is a test product description." in formatted["description"]
        assert "Visit our page!" in formatted["description"]
        assert test_user.business_name.replace(' ', '') in formatted["description"]

    def test_get_default_template(self, db_session: Session, test_user: User):
        """Test getting default template for a platform"""
        
        service = PreferencesService(db_session)
        
        # Create default template
        template = ContentTemplate(
            user_id=test_user.id,
            name="Default Template",
            title_template="{title}",
            description_template="{description}",
            platforms=[Platform.FACEBOOK.value],
            style="professional",
            is_default=True
        )
        db_session.add(template)
        db_session.commit()
        
        # Get default template
        default_template = service.get_default_template(test_user.id, Platform.FACEBOOK)
        
        assert default_template is not None
        assert default_template.name == "Default Template"
        assert default_template.is_default is True