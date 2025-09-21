import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.models import User, Product, ProductImage
from app.auth import auth_service
import uuid


@pytest.fixture
def test_user(db_session: Session):
    """Create a test user."""
    user = User(
        id=str(uuid.uuid4()),
        email="testuser@example.com",
        password_hash=auth_service.hash_password("testpassword123"),
        business_name="Test Business",
        business_type="Artisan",
        business_description="Test business description"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User):
    """Create authentication headers for test user."""
    tokens = auth_service.create_tokens(test_user.id)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.fixture
def test_product(db_session: Session, test_user: User):
    """Create a test product."""
    product = Product(
        id=str(uuid.uuid4()),
        user_id=test_user.id,
        title="Test Product",
        description="This is a test product description"
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    return product


class TestProductAPI:
    """Test cases for product management API endpoints."""

    def test_create_product_success(self, client: TestClient, auth_headers: dict):
        """Test successful product creation."""
        product_data = {
            "title": "Handmade Ceramic Vase",
            "description": "Beautiful handcrafted ceramic vase with unique glaze patterns"
        }
        
        response = client.post("/products/", json=product_data, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == product_data["title"]
        assert data["description"] == product_data["description"]
        assert "id" in data
        assert "user_id" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert data["images"] == []

    def test_create_product_validation_error(self, client: TestClient, auth_headers: dict):
        """Test product creation with validation errors."""
        # Test empty title
        product_data = {
            "title": "",
            "description": "Valid description"
        }
        
        response = client.post("/products/", json=product_data, headers=auth_headers)
        assert response.status_code == 422

        # Test title too long
        product_data = {
            "title": "x" * 256,  # Exceeds 255 character limit
            "description": "Valid description"
        }
        
        response = client.post("/products/", json=product_data, headers=auth_headers)
        assert response.status_code == 422

        # Test empty description
        product_data = {
            "title": "Valid title",
            "description": ""
        }
        
        response = client.post("/products/", json=product_data, headers=auth_headers)
        assert response.status_code == 422

    def test_create_product_unauthorized(self, client: TestClient):
        """Test product creation without authentication."""
        product_data = {
            "title": "Test Product",
            "description": "Test description"
        }
        
        response = client.post("/products/", json=product_data)
        assert response.status_code == 401

    def test_list_products_success(self, client: TestClient, auth_headers: dict, test_product: Product):
        """Test successful product listing."""
        response = client.get("/products/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # Check if our test product is in the list
        product_ids = [p["id"] for p in data]
        assert test_product.id in product_ids

    def test_list_products_pagination(self, client: TestClient, auth_headers: dict, db_session: Session, test_user: User):
        """Test product listing with pagination."""
        # Create multiple products
        products = []
        for i in range(5):
            product = Product(
                id=str(uuid.uuid4()),
                user_id=test_user.id,
                title=f"Test Product {i}",
                description=f"Description {i}"
            )
            products.append(product)
            db_session.add(product)
        db_session.commit()

        # Test pagination
        response = client.get("/products/?skip=0&limit=3", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 3

        response = client.get("/products/?skip=3&limit=3", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 3

    def test_get_product_success(self, client: TestClient, auth_headers: dict, test_product: Product):
        """Test successful product retrieval."""
        response = client.get(f"/products/{test_product.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_product.id
        assert data["title"] == test_product.title
        assert data["description"] == test_product.description

    def test_get_product_not_found(self, client: TestClient, auth_headers: dict):
        """Test product retrieval with non-existent ID."""
        fake_id = str(uuid.uuid4())
        response = client.get(f"/products/{fake_id}", headers=auth_headers)
        
        assert response.status_code == 404

    def test_get_product_unauthorized(self, client: TestClient, test_product: Product):
        """Test product retrieval without authentication."""
        response = client.get(f"/products/{test_product.id}")
        assert response.status_code == 401

    def test_update_product_success(self, client: TestClient, auth_headers: dict, test_product: Product):
        """Test successful product update."""
        update_data = {
            "title": "Updated Product Title",
            "description": "Updated product description"
        }
        
        response = client.put(f"/products/{test_product.id}", json=update_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_product.id
        assert data["title"] == update_data["title"]
        assert data["description"] == update_data["description"]

    def test_update_product_not_found(self, client: TestClient, auth_headers: dict):
        """Test product update with non-existent ID."""
        fake_id = str(uuid.uuid4())
        update_data = {
            "title": "Updated Title",
            "description": "Updated description"
        }
        
        response = client.put(f"/products/{fake_id}", json=update_data, headers=auth_headers)
        assert response.status_code == 404

    def test_delete_product_success(self, client: TestClient, auth_headers: dict, test_product: Product):
        """Test successful product deletion."""
        response = client.delete(f"/products/{test_product.id}", headers=auth_headers)
        
        assert response.status_code == 204

        # Verify product is deleted
        response = client.get(f"/products/{test_product.id}", headers=auth_headers)
        assert response.status_code == 404

    def test_delete_product_not_found(self, client: TestClient, auth_headers: dict):
        """Test product deletion with non-existent ID."""
        fake_id = str(uuid.uuid4())
        response = client.delete(f"/products/{fake_id}", headers=auth_headers)
        
        assert response.status_code == 404

    def test_get_product_images_success(self, client: TestClient, auth_headers: dict, test_product: Product, db_session: Session):
        """Test successful product images retrieval."""
        # Create test images
        image1 = ProductImage(
            id=str(uuid.uuid4()),
            product_id=test_product.id,
            original_filename="test1.jpg",
            original_url="https://example.com/original1.jpg",
            compressed_url="https://example.com/compressed1.jpg",
            thumbnail_urls={"small": "https://example.com/thumb1_small.jpg"},
            storage_paths={"original": "path/to/original1.jpg"},
            file_size=1024,
            dimensions={"width": 800, "height": 600},
            format="JPEG"
        )
        image2 = ProductImage(
            id=str(uuid.uuid4()),
            product_id=test_product.id,
            original_filename="test2.jpg",
            original_url="https://example.com/original2.jpg",
            compressed_url="https://example.com/compressed2.jpg",
            thumbnail_urls={"small": "https://example.com/thumb2_small.jpg"},
            storage_paths={"original": "path/to/original2.jpg"},
            file_size=2048,
            dimensions={"width": 1024, "height": 768},
            format="JPEG"
        )
        db_session.add_all([image1, image2])
        db_session.commit()

        response = client.get(f"/products/{test_product.id}/images", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_delete_product_image_success(self, client: TestClient, auth_headers: dict, test_product: Product, db_session: Session):
        """Test successful product image deletion."""
        # Create test image
        image = ProductImage(
            id=str(uuid.uuid4()),
            product_id=test_product.id,
            original_filename="test.jpg",
            original_url="https://example.com/original.jpg",
            compressed_url="https://example.com/compressed.jpg",
            thumbnail_urls={"small": "https://example.com/thumb_small.jpg"},
            storage_paths={"original": "path/to/original.jpg"},
            file_size=1024,
            dimensions={"width": 800, "height": 600},
            format="JPEG"
        )
        db_session.add(image)
        db_session.commit()

        response = client.delete(f"/products/{test_product.id}/images/{image.id}", headers=auth_headers)
        
        assert response.status_code == 204

        # Verify image is deleted
        response = client.get(f"/products/{test_product.id}/images", headers=auth_headers)
        data = response.json()
        image_ids = [img["id"] for img in data]
        assert image.id not in image_ids

    def test_user_isolation(self, client: TestClient, db_session: Session):
        """Test that users can only access their own products."""
        # Create two users
        user1 = User(
            id=str(uuid.uuid4()),
            email="user1@example.com",
            password_hash=auth_service.hash_password("password123"),
            business_name="Business 1",
            business_type="Artisan"
        )
        user2 = User(
            id=str(uuid.uuid4()),
            email="user2@example.com",
            password_hash=auth_service.hash_password("password123"),
            business_name="Business 2",
            business_type="Artisan"
        )
        db_session.add_all([user1, user2])
        db_session.commit()

        # Create product for user1
        product = Product(
            id=str(uuid.uuid4()),
            user_id=user1.id,
            title="User 1 Product",
            description="Product belonging to user 1"
        )
        db_session.add(product)
        db_session.commit()

        # Create auth headers for user2
        user2_tokens = auth_service.create_tokens(user2.id)
        user2_headers = {"Authorization": f"Bearer {user2_tokens['access_token']}"}

        # User2 should not be able to access user1's product
        response = client.get(f"/products/{product.id}", headers=user2_headers)
        assert response.status_code == 404

        # User2 should not be able to update user1's product
        response = client.put(f"/products/{product.id}", 
                            json={"title": "Hacked", "description": "Hacked"}, 
                            headers=user2_headers)
        assert response.status_code == 404

        # User2 should not be able to delete user1's product
        response = client.delete(f"/products/{product.id}", headers=user2_headers)
        assert response.status_code == 404