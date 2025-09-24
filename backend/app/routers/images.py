"""
Image processing API endpoints.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from typing import List, Optional
import time
import logging

from ..services.image_processing import image_service, ImageValidationError
from ..services.cloud_storage import get_storage_service, StorageError
from ..schemas import ImageUploadResponse, ImageProcessingResult
from ..dependencies import get_current_user
from ..models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/images", tags=["images"])


@router.post("/upload", response_model=ImageUploadResponse)
async def upload_image(
    file: UploadFile = File(...),
    platforms: Optional[List[str]] = Query(None, description="Platforms to optimize for"),
    product_id: Optional[str] = Query(None, description="Product ID for organizing files"),
    current_user: User = Depends(get_current_user)
):
    """
    Upload and process an image with cloud storage integration.
    
    This endpoint accepts an image file, validates it, compresses it,
    generates thumbnails, optimizes it for specified platforms, and uploads all variants to cloud storage.
    """
    try:
        start_time = time.time()
        
        # Process the image and upload to cloud storage
        result = await image_service.process_image(file, platforms, product_id)
        
        processing_time = time.time() - start_time
        
        return ImageUploadResponse(
            success=True,
            image_id=result.id,
            message=f"Image processed and uploaded successfully in {processing_time:.2f}s",
            urls={
                "original": result.original_url,
                "compressed": result.compressed_url,
                "thumbnails": result.thumbnail_urls,
                "platform_optimized": result.platform_optimized_urls
            }
        )
        
    except ImageValidationError as e:
        logger.warning(f"Image validation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except StorageError as e:
        logger.error(f"Cloud storage operation failed: {e}")
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")
    except Exception as e:
        logger.error(f"Image upload failed: {e}")
        raise HTTPException(status_code=500, detail="Image upload failed")


@router.post("/process", response_model=ImageProcessingResult)
async def process_image(
    file: UploadFile = File(...),
    platforms: Optional[List[str]] = Query(None, description="Platforms to optimize for"),
    product_id: Optional[str] = Query(None, description="Product ID for organizing files"),
    current_user: User = Depends(get_current_user)
):
    """
    Process an image and return detailed processing information with cloud storage URLs.
    
    This endpoint is useful for testing and debugging image processing functionality.
    """
    try:
        start_time = time.time()
        
        # Process the image and upload to cloud storage
        result = await image_service.process_image(file, platforms, product_id)
        
        processing_time = time.time() - start_time
        
        return ImageProcessingResult(
            id=result.id,
            original_filename=result.original_filename,
            file_size=result.file_size,
            dimensions=result.dimensions,
            format=result.format,
            processing_time=processing_time,
            platform_optimizations=list(result.platform_optimized_urls.keys()),
            urls={
                "original": result.original_url,
                "compressed": result.compressed_url,
                "thumbnails": result.thumbnail_urls,
                "platform_optimized": result.platform_optimized_urls
            }
        )
        
    except ImageValidationError as e:
        logger.warning(f"Image validation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except StorageError as e:
        logger.error(f"Cloud storage operation failed: {e}")
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")
    except Exception as e:
        logger.error(f"Image processing failed: {e}")
        raise HTTPException(status_code=500, detail="Image processing failed")


@router.get("/platforms")
async def get_supported_platforms():
    """
    Get list of supported platforms for image optimization.
    """
    return {
        "platforms": image_service.get_supported_platforms(),
        "count": len(image_service.get_supported_platforms())
    }


@router.get("/platforms/{platform}/requirements")
async def get_platform_requirements(platform: str):
    """
    Get image requirements for a specific platform.
    """
    try:
        requirements = image_service.get_platform_requirements(platform)
        return {
            "platform": platform,
            "requirements": requirements
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/validate")
async def validate_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Validate an image file without processing it.
    
    Useful for checking if an image meets requirements before uploading.
    """
    try:
        await image_service.validate_image(file)
        return {
            "valid": True,
            "filename": file.filename,
            "size": file.size,
            "message": "Image is valid"
        }
    except ImageValidationError as e:
        return {
            "valid": False,
            "filename": file.filename,
            "size": file.size,
            "error": str(e)
        }


@router.post("/presigned-upload")
async def generate_presigned_upload_url(
    filename: str = Query(..., description="Original filename"),
    content_type: str = Query(..., description="MIME type of the file"),
    image_type: str = Query("original", description="Type of image (original, compressed, etc.)"),
    current_user: User = Depends(get_current_user)
):
    """
    Generate a presigned URL for direct client upload to cloud storage.
    
    This allows clients to upload files directly to cloud storage without going through the server,
    which is more efficient for large files.
    """
    try:
        presigned_data = await image_service.generate_presigned_upload_url(
            filename, content_type, image_type
        )
        
        return {
            "success": True,
            "upload_data": presigned_data,
            "message": "Presigned upload URL generated successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to generate presigned URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate upload URL")


@router.get("/download/{storage_path:path}")
async def generate_presigned_download_url(
    storage_path: str,
    expires_in: int = Query(3600, description="URL expiration time in seconds"),
    current_user: User = Depends(get_current_user)
):
    """
    Generate a presigned URL for secure file download.
    
    This provides temporary access to files stored in cloud storage.
    """
    try:
        storage_service = get_storage_service()
        download_url = await storage_service.generate_presigned_download_url(
            storage_path, expires_in
        )
        
        return {
            "success": True,
            "download_url": download_url,
            "expires_in": expires_in,
            "message": "Presigned download URL generated successfully"
        }
        
    except StorageError as e:
        logger.error(f"Failed to generate presigned download URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate download URL")


@router.delete("/{storage_path:path}")
async def delete_image(
    storage_path: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete an image from cloud storage.
    
    This permanently removes the file from cloud storage.
    """
    try:
        storage_service = get_storage_service()
        success = await storage_service.delete_file(storage_path)
        
        if success:
            return {
                "success": True,
                "message": "Image deleted successfully"
            }
        else:
            raise HTTPException(status_code=404, detail="Image not found or could not be deleted")
            
    except StorageError as e:
        logger.error(f"Failed to delete image: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete image")


@router.get("/user/images")
async def list_user_images(
    limit: int = Query(100, description="Maximum number of images to return"),
    current_user: User = Depends(get_current_user)
):
    """
    List all images uploaded by the current user.
    """
    try:
        storage_service = get_storage_service()
        images = await storage_service.list_user_images(current_user.id, limit)
        
        return {
            "success": True,
            "images": [
                {
                    "file_id": img.file_id,
                    "filename": img.filename,
                    "url": img.url,
                    "size": img.size,
                    "content_type": img.content_type,
                    "created_at": img.created_at.isoformat()
                }
                for img in images
            ],
            "count": len(images)
        }
        
    except StorageError as e:
        logger.error(f"Failed to list user images: {e}")
        raise HTTPException(status_code=500, detail="Failed to list images")


@router.post("/by-ids")
async def get_images_by_ids(
    request: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Get images by their IDs.
    """
    try:
        image_ids = request.get("image_ids", [])
        if not image_ids:
            return {"success": True, "images": []}
        
        storage_service = get_storage_service()
        images = await storage_service.get_images_by_ids(current_user.id, image_ids)
        
        return {
            "success": True,
            "images": [
                {
                    "id": img.file_id,
                    "original_url": img.url,
                    "compressed_url": img.url,  # For now, same as original
                    "thumbnail_url": img.url,   # For now, same as original
                    "file_size": img.size,
                    "dimensions": {"width": 0, "height": 0},  # Placeholder
                    "file_name": img.filename,
                    "created_at": img.created_at.isoformat()
                }
                for img in images
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get images by IDs: {e}")
        # Fallback to empty list
        return {"success": True, "images": []}


@router.get("/storage/stats")
async def get_storage_stats(
    current_user: User = Depends(get_current_user)
):
    """
    Get storage usage statistics.
    
    This endpoint provides information about storage usage across the platform.
    """
    try:
        storage_service = get_storage_service()
        stats = await storage_service.get_storage_stats()
        
        return {
            "success": True,
            "stats": stats,
            "message": "Storage statistics retrieved successfully"
        }
        
    except StorageError as e:
        logger.error(f"Failed to get storage stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get storage statistics")