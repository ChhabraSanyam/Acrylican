from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..dependencies import get_current_user
from ..models import User, Product, ProductImage
from ..schemas import ProductCreate, ProductResponse, ProductImageResponse
import uuid

router = APIRouter(
    prefix="/products",
    tags=["products"],
    responses={404: {"description": "Not found"}},
)


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new product for the authenticated user.
    
    Args:
        product_data: Product creation data
        db: Database session
        current_user: Authenticated user
        
    Returns:
        ProductResponse: Created product data
    """
    # Create new product
    product = Product(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        title=product_data.title,
        description=product_data.description
    )
    
    db.add(product)
    db.commit()
    db.refresh(product)
    
    return product


@router.get("/", response_model=List[ProductResponse])
async def list_products(
    skip: int = Query(0, ge=0, description="Number of products to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of products to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List products for the authenticated user with pagination.
    
    Args:
        skip: Number of products to skip
        limit: Maximum number of products to return
        db: Database session
        current_user: Authenticated user
        
    Returns:
        List[ProductResponse]: List of user's products
    """
    products = db.query(Product).filter(
        Product.user_id == current_user.id
    ).offset(skip).limit(limit).all()
    
    return products


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific product by ID.
    
    Args:
        product_id: Product ID
        db: Database session
        current_user: Authenticated user
        
    Returns:
        ProductResponse: Product data
        
    Raises:
        HTTPException: If product not found or not owned by user
    """
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.user_id == current_user.id
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    return product


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a specific product.
    
    Args:
        product_id: Product ID
        product_data: Updated product data
        db: Database session
        current_user: Authenticated user
        
    Returns:
        ProductResponse: Updated product data
        
    Raises:
        HTTPException: If product not found or not owned by user
    """
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.user_id == current_user.id
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Update product fields
    product.title = product_data.title
    product.description = product_data.description
    
    db.commit()
    db.refresh(product)
    
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a specific product and all associated images.
    
    Args:
        product_id: Product ID
        db: Database session
        current_user: Authenticated user
        
    Raises:
        HTTPException: If product not found or not owned by user
    """
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.user_id == current_user.id
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Delete the product (images will be cascade deleted due to relationship)
    db.delete(product)
    db.commit()


@router.get("/{product_id}/images", response_model=List[ProductImageResponse])
async def get_product_images(
    product_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all images for a specific product.
    
    Args:
        product_id: Product ID
        db: Database session
        current_user: Authenticated user
        
    Returns:
        List[ProductImageResponse]: List of product images
        
    Raises:
        HTTPException: If product not found or not owned by user
    """
    # First verify the product exists and belongs to the user
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.user_id == current_user.id
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Get all images for the product
    images = db.query(ProductImage).filter(
        ProductImage.product_id == product_id
    ).all()
    
    return images


@router.delete("/{product_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product_image(
    product_id: str,
    image_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a specific image from a product.
    
    Args:
        product_id: Product ID
        image_id: Image ID
        db: Database session
        current_user: Authenticated user
        
    Raises:
        HTTPException: If product or image not found or not owned by user
    """
    # First verify the product exists and belongs to the user
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.user_id == current_user.id
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Find and delete the image
    image = db.query(ProductImage).filter(
        ProductImage.id == image_id,
        ProductImage.product_id == product_id
    ).first()
    
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    
    db.delete(image)
    db.commit()