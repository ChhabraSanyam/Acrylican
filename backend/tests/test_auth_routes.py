import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch
from app.main import app
from app.database import get_db, Base
from app.models import User
from app.auth import auth_service

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_auth.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def test_db():
    """Create test database tables."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_user_data():
    """Sample user registration data."""
    return {
        "email": "test@example.com",
        "password": "testpassword123",
        "business_name": "Test Business",
        "business_type": "Handmade Crafts",
        "business_description": "We make beautiful handmade crafts",
        "website": "https://testbusiness.com",
        "location": "Test City, Test State"
    }


@pytest.fixture
def sample_login_data():
    """Sample user login data."""
    return {
        "email": "test@example.com",
        "password": "testpassword123"
    }


class TestUserRegistration:
    """Test user registration endpoint."""
    
    def test_register_user_success(self, client, test_db, sample_user_data):
        """Test successful user registration."""
        response = client.post("/auth/register", json=sample_user_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["success"] is True
        assert data["message"] == "User registered successfully"
        assert "user" in data
        assert "tokens" in data
        
        # Check user data
        user_data = data["user"]
        assert user_data["email"] == sample_user_data["email"]
        assert user_data["business_name"] == sample_user_data["business_name"]
        assert user_data["business_type"] == sample_user_data["business_type"]
        assert user_data["is_active"] is True
        assert "id" in user_data
        assert "created_at" in user_data
        
        # Check tokens
        tokens = data["tokens"]
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"
    
    def test_register_user_duplicate_email(self, client, test_db, sample_user_data):
        """Test registration with duplicate email."""
        # Register user first time
        response1 = client.post("/auth/register", json=sample_user_data)
        assert response1.status_code == 201
        
        # Try to register same email again
        response2 = client.post("/auth/register", json=sample_user_data)
        assert response2.status_code == 400
        
        data = response2.json()
        assert "Email already registered" in data["detail"]
    
    def test_register_user_invalid_email(self, client, test_db, sample_user_data):
        """Test registration with invalid email."""
        sample_user_data["email"] = "invalid-email"
        
        response = client.post("/auth/register", json=sample_user_data)
        assert response.status_code == 422  # Validation error
    
    def test_register_user_short_password(self, client, test_db, sample_user_data):
        """Test registration with short password."""
        sample_user_data["password"] = "short"
        
        response = client.post("/auth/register", json=sample_user_data)
        assert response.status_code == 422  # Validation error
    
    def test_register_user_missing_required_fields(self, client, test_db):
        """Test registration with missing required fields."""
        incomplete_data = {
            "email": "test@example.com",
            "password": "testpassword123"
            # Missing business_name and business_type
        }
        
        response = client.post("/auth/register", json=incomplete_data)
        assert response.status_code == 422  # Validation error
    
    def test_register_user_optional_fields_none(self, client, test_db):
        """Test registration with optional fields as None."""
        minimal_data = {
            "email": "test@example.com",
            "password": "testpassword123",
            "business_name": "Test Business",
            "business_type": "Handmade Crafts",
            "business_description": None,
            "website": None,
            "location": None
        }
        
        response = client.post("/auth/register", json=minimal_data)
        assert response.status_code == 201
        
        data = response.json()
        user_data = data["user"]
        assert user_data["business_description"] is None
        assert user_data["website"] is None
        assert user_data["location"] is None


class TestUserLogin:
    """Test user login endpoint."""
    
    def test_login_success(self, client, test_db, sample_user_data, sample_login_data):
        """Test successful user login."""
        # Register user first
        client.post("/auth/register", json=sample_user_data)
        
        # Login
        response = client.post("/auth/login", json=sample_login_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Login successful"
        assert "user" in data
        assert "tokens" in data
        
        # Check tokens
        tokens = data["tokens"]
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"
    
    def test_login_invalid_email(self, client, test_db, sample_user_data):
        """Test login with non-existent email."""
        # Register user first
        client.post("/auth/register", json=sample_user_data)
        
        # Try login with different email
        login_data = {
            "email": "nonexistent@example.com",
            "password": "testpassword123"
        }
        
        response = client.post("/auth/login", json=login_data)
        assert response.status_code == 401
        
        data = response.json()
        assert "Invalid email or password" in data["detail"]
    
    def test_login_invalid_password(self, client, test_db, sample_user_data):
        """Test login with incorrect password."""
        # Register user first
        client.post("/auth/register", json=sample_user_data)
        
        # Try login with wrong password
        login_data = {
            "email": "test@example.com",
            "password": "wrongpassword"
        }
        
        response = client.post("/auth/login", json=login_data)
        assert response.status_code == 401
        
        data = response.json()
        assert "Invalid email or password" in data["detail"]
    
    def test_login_inactive_user(self, client, test_db, sample_user_data, sample_login_data):
        """Test login with inactive user."""
        # Register user first
        client.post("/auth/register", json=sample_user_data)
        
        # Manually set user as inactive
        db = TestingSessionLocal()
        user = db.query(User).filter(User.email == sample_user_data["email"]).first()
        user.is_active = False
        db.commit()
        db.close()
        
        # Try to login
        response = client.post("/auth/login", json=sample_login_data)
        assert response.status_code == 401
        
        data = response.json()
        assert "Account is inactive" in data["detail"]


class TestTokenRefresh:
    """Test token refresh endpoint."""
    
    def test_refresh_token_success(self, client, test_db, sample_user_data, sample_login_data):
        """Test successful token refresh."""
        # Register and login user
        client.post("/auth/register", json=sample_user_data)
        login_response = client.post("/auth/login", json=sample_login_data)
        login_data = login_response.json()
        
        refresh_token = login_data["tokens"]["refresh_token"]
        
        # Refresh token
        response = client.post("/auth/refresh", json={"refresh_token": refresh_token})
        assert response.status_code == 200
        
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        # Note: refresh endpoint only returns access_token, not refresh_token
    
    def test_refresh_token_invalid(self, client, test_db):
        """Test token refresh with invalid refresh token."""
        response = client.post("/auth/refresh", json={"refresh_token": "invalid.token.here"})
        assert response.status_code == 401
        
        data = response.json()
        assert "Invalid refresh token" in data["detail"]
    
    def test_refresh_token_with_access_token(self, client, test_db, sample_user_data, sample_login_data):
        """Test token refresh using access token instead of refresh token."""
        # Register and login user
        client.post("/auth/register", json=sample_user_data)
        login_response = client.post("/auth/login", json=sample_login_data)
        login_data = login_response.json()
        
        access_token = login_data["tokens"]["access_token"]
        
        # Try to refresh using access token
        response = client.post("/auth/refresh", json={"refresh_token": access_token})
        assert response.status_code == 401
        
        data = response.json()
        assert "Invalid refresh token" in data["detail"]


class TestProtectedEndpoints:
    """Test protected endpoints that require authentication."""
    
    def test_get_current_user_success(self, client, test_db, sample_user_data, sample_login_data):
        """Test getting current user info with valid token."""
        # Register and login user
        client.post("/auth/register", json=sample_user_data)
        login_response = client.post("/auth/login", json=sample_login_data)
        login_data = login_response.json()
        
        access_token = login_data["tokens"]["access_token"]
        
        # Get current user info
        headers = {"Authorization": f"Bearer {access_token}"}
        response = client.get("/auth/me", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["email"] == sample_user_data["email"]
        assert data["business_name"] == sample_user_data["business_name"]
        assert data["is_active"] is True
    
    def test_get_current_user_no_token(self, client, test_db):
        """Test getting current user info without token."""
        response = client.get("/auth/me")
        assert response.status_code == 403  # Forbidden
    
    def test_get_current_user_invalid_token(self, client, test_db):
        """Test getting current user info with invalid token."""
        headers = {"Authorization": "Bearer invalid.token.here"}
        response = client.get("/auth/me", headers=headers)
        assert response.status_code == 401
    
    def test_logout_success(self, client, test_db, sample_user_data, sample_login_data):
        """Test user logout."""
        # Register and login user
        client.post("/auth/register", json=sample_user_data)
        login_response = client.post("/auth/login", json=sample_login_data)
        login_data = login_response.json()
        
        access_token = login_data["tokens"]["access_token"]
        
        # Logout
        headers = {"Authorization": f"Bearer {access_token}"}
        response = client.post("/auth/logout", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "Logged out successfully" in data["message"]
    
    def test_delete_account_success(self, client, test_db, sample_user_data, sample_login_data):
        """Test account deletion (soft delete)."""
        # Register and login user
        client.post("/auth/register", json=sample_user_data)
        login_response = client.post("/auth/login", json=sample_login_data)
        login_data = login_response.json()
        
        access_token = login_data["tokens"]["access_token"]
        
        # Delete account
        headers = {"Authorization": f"Bearer {access_token}"}
        response = client.delete("/auth/account", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "Account deleted successfully" in data["message"]
        
        # Verify user is marked as inactive
        db = TestingSessionLocal()
        user = db.query(User).filter(User.email == sample_user_data["email"]).first()
        assert user.is_active is False
        db.close()
        
        # Verify user can't login anymore
        login_response = client.post("/auth/login", json=sample_login_data)
        assert login_response.status_code == 401


class TestAuthenticationFlow:
    """Test complete authentication flow."""
    
    def test_complete_auth_flow(self, client, test_db, sample_user_data, sample_login_data):
        """Test complete authentication flow: register -> login -> access protected -> refresh -> logout."""
        
        # 1. Register
        register_response = client.post("/auth/register", json=sample_user_data)
        assert register_response.status_code == 201
        register_data = register_response.json()
        
        # 2. Login
        login_response = client.post("/auth/login", json=sample_login_data)
        assert login_response.status_code == 200
        login_data = login_response.json()
        
        access_token = login_data["tokens"]["access_token"]
        refresh_token = login_data["tokens"]["refresh_token"]
        
        # 3. Access protected endpoint
        headers = {"Authorization": f"Bearer {access_token}"}
        me_response = client.get("/auth/me", headers=headers)
        assert me_response.status_code == 200
        
        # 4. Refresh token
        refresh_response = client.post("/auth/refresh", json={"refresh_token": refresh_token})
        assert refresh_response.status_code == 200
        new_access_token = refresh_response.json()["access_token"]
        
        # 5. Use new access token
        new_headers = {"Authorization": f"Bearer {new_access_token}"}
        me_response2 = client.get("/auth/me", headers=new_headers)
        assert me_response2.status_code == 200
        
        # 6. Logout
        logout_response = client.post("/auth/logout", headers=new_headers)
        assert logout_response.status_code == 200