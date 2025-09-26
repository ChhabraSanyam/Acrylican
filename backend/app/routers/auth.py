from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ..database import get_db
from ..models import User
from ..schemas import UserRegistration, UserLogin, UserResponse, TokenResponse, AccessTokenResponse, TokenRefresh, AuthResult
from ..auth import auth_service
from ..dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=AuthResult, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserRegistration, db: Session = Depends(get_db)):
    """
    Register a new user.
    
    Args:
        user_data: User registration data
        db: Database session
        
    Returns:
        AuthResult: Registration result with user data and tokens
        
    Raises:
        HTTPException: If email already exists or registration fails
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    try:
        # Hash password
        hashed_password = auth_service.hash_password(user_data.password)
        
        # Create new user
        new_user = User(
            email=user_data.email,
            password_hash=hashed_password,
            business_name=user_data.business_name,
            business_type=user_data.business_type,
            business_description=user_data.business_description,
            website=user_data.website,
            location=user_data.location
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Create tokens
        tokens = auth_service.create_tokens(new_user.id)
        
        return AuthResult(
            success=True,
            user=UserResponse.model_validate(new_user),
            tokens=TokenResponse(**tokens),
            message="User registered successfully"
        )
        
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=AuthResult)
async def login_user(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate user and return tokens.
    
    Args:
        user_credentials: User login credentials
        db: Database session
        
    Returns:
        AuthResult: Login result with user data and tokens
        
    Raises:
        HTTPException: If credentials are invalid
    """
    # Find user by email
    user = db.query(User).filter(User.email == user_credentials.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not auth_service.verify_password(user_credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive"
        )
    
    # Create tokens
    tokens = auth_service.create_tokens(user.id)
    
    return AuthResult(
        success=True,
        user=UserResponse.model_validate(user),
        tokens=TokenResponse(**tokens),
        message="Login successful"
    )


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_token(token_data: TokenRefresh):
    """
    Refresh access token using refresh token.
    
    Args:
        token_data: Refresh token data
        
    Returns:
        TokenResponse: New access token
        
    Raises:
        HTTPException: If refresh token is invalid
    """
    new_tokens = auth_service.refresh_access_token(token_data.refresh_token)
    
    if not new_tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    return AccessTokenResponse(**new_tokens)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current user information.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        UserResponse: Current user data
    """
    return UserResponse.model_validate(current_user)


@router.post("/logout")
async def logout_user(current_user: User = Depends(get_current_user)):
    """
    Logout user (client should discard tokens).
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        dict: Logout confirmation
    """
    # In a more sophisticated implementation, you might want to:
    # 1. Add tokens to a blacklist stored in database
    # 2. Track active sessions
    # For now, we rely on the client to discard the tokens
    
    return {"message": "Logged out successfully"}


@router.delete("/account")
async def delete_account(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Delete user account (soft delete by setting is_active to False).
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        dict: Account deletion confirmation
    """
    try:
        # Soft delete - set user as inactive
        current_user.is_active = False
        db.commit()
        
        return {"message": "Account deleted successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete account"
        )