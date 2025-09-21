"""
Privacy API endpoints for data export, deletion, and audit operations.

This module provides endpoints for:
- User data export (GDPR compliance)
- Data deletion requests
- Audit log access
- Privacy settings management
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ..database import get_db
from ..dependencies import get_current_user
from ..models import User, AuditLog, DataDeletionRequest
from ..services.data_privacy_service import data_privacy_service
from ..services.audit_service import audit_service
from ..security import security_validator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/privacy", tags=["privacy"])


# Pydantic models for request/response
class DataExportRequest(BaseModel):
    """Request model for data export."""
    format: str = Field(default="json", description="Export format (json, csv)")
    include_images: bool = Field(default=False, description="Include image files in export")


class DataExportResponse(BaseModel):
    """Response model for data export request."""
    export_id: str
    status: str
    requested_at: datetime
    estimated_completion: Optional[datetime] = None
    download_url: Optional[str] = None


class DeletionRequest(BaseModel):
    """Request model for data deletion."""
    deletion_type: str = Field(..., description="Type of deletion: 'full_deletion' or 'anonymization'")
    reason: str = Field(..., description="Reason for deletion")
    confirmation_text: str = Field(..., description="User must type confirmation text")
    export_data_first: bool = Field(default=True, description="Export data before deletion")


class DeletionRequestResponse(BaseModel):
    """Response model for deletion request."""
    request_id: str
    status: str
    deletion_type: str
    scheduled_for: datetime
    retention_period_days: int
    verification_required: bool


class AuditLogEntry(BaseModel):
    """Response model for audit log entry."""
    id: str
    action: str
    resource_type: str
    resource_id: Optional[str]
    details: Optional[str]
    success: bool
    sensitivity_level: str
    timestamp: datetime
    ip_address: Optional[str]


class AuditLogResponse(BaseModel):
    """Response model for audit log listing."""
    entries: List[AuditLogEntry]
    total_count: int
    page: int
    page_size: int


@router.post("/export", response_model=DataExportResponse)
async def request_data_export(
    export_request: DataExportRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Request export of user data.
    
    This endpoint initiates a data export process that will collect all
    user data and make it available for download in compliance with
    data protection regulations.
    """
    try:
        # Log the export request
        await audit_service.log_privacy_action(
            db=db,
            user_id=current_user.id,
            privacy_action="export",
            request=request,
            details=f"Data export requested in {export_request.format} format",
            metadata={
                "format": export_request.format,
                "include_images": export_request.include_images
            }
        )
        
        # For now, we'll process the export immediately
        # In production, this would be queued for background processing
        export_data = await data_privacy_service.export_user_data(db, current_user.id)
        
        # In a real implementation, you'd store this in cloud storage
        # and return a secure download URL
        export_id = security_validator.generate_secure_token(16)
        
        return DataExportResponse(
            export_id=export_id,
            status="completed",
            requested_at=datetime.utcnow(),
            estimated_completion=datetime.utcnow(),
            download_url=f"/privacy/export/{export_id}/download"
        )
        
    except Exception as e:
        logger.error(f"Failed to process data export request: {e}")
        await audit_service.log_privacy_action(
            db=db,
            user_id=current_user.id,
            privacy_action="export",
            request=request,
            details="Data export failed",
            metadata={"error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process data export request"
        )


@router.get("/export/{export_id}/download")
async def download_data_export(
    export_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Download exported user data.
    
    This endpoint provides the actual data export file for download.
    The export ID must be valid and belong to the current user.
    """
    try:
        # In a real implementation, you'd validate the export_id
        # and retrieve the file from secure storage
        
        # For demo purposes, generate the export on-demand
        export_data = await data_privacy_service.export_user_data(db, current_user.id)
        
        # Log the download
        await audit_service.log_data_access(
            db=db,
            user_id=current_user.id,
            resource_type="user_data_export",
            resource_id=export_id,
            access_type="download",
            details="User data export downloaded"
        )
        
        # Return as streaming response
        def generate_file():
            yield export_data.getvalue()
        
        return StreamingResponse(
            generate_file(),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=user_data_export_{current_user.id}_{datetime.utcnow().strftime('%Y%m%d')}.zip"
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to download data export: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download data export"
        )


@router.post("/deletion-request", response_model=DeletionRequestResponse)
async def request_data_deletion(
    deletion_request: DeletionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Request deletion of user data.
    
    This endpoint initiates a data deletion process with a retention period
    during which the user can cancel the deletion request.
    """
    try:
        # Validate deletion type
        if deletion_request.deletion_type not in ["full_deletion", "anonymization"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid deletion type. Must be 'full_deletion' or 'anonymization'"
            )
        
        # Validate confirmation text
        expected_confirmation = f"DELETE {current_user.business_name}"
        if deletion_request.confirmation_text != expected_confirmation:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Confirmation text must be exactly: {expected_confirmation}"
            )
        
        # Check for existing deletion requests
        existing_request = db.query(DataDeletionRequest).filter(
            DataDeletionRequest.user_id == current_user.id,
            DataDeletionRequest.status.in_(["scheduled", "in_progress"])
        ).first()
        
        if existing_request:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A deletion request is already pending for this account"
            )
        
        # Create deletion request
        retention_days = 30  # 30-day retention period
        scheduled_for = datetime.utcnow() + timedelta(days=retention_days)
        verification_token = security_validator.generate_secure_token(32)
        
        deletion_req = DataDeletionRequest(
            user_id=current_user.id,
            deletion_type=deletion_request.deletion_type,
            reason=deletion_request.reason,
            requested_by=current_user.id,
            scheduled_for=scheduled_for,
            retention_period_days=retention_days,
            export_requested=deletion_request.export_data_first,
            verification_token=verification_token,
            request_metadata={
                "confirmation_text": deletion_request.confirmation_text,
                "user_agent": request.headers.get("user-agent", ""),
                "ip_address": request.client.host if request.client else None
            }
        )
        
        db.add(deletion_req)
        db.commit()
        db.refresh(deletion_req)
        
        # Log the deletion request
        await audit_service.log_privacy_action(
            db=db,
            user_id=current_user.id,
            privacy_action="deletion_request",
            request=request,
            details=f"Data deletion requested: {deletion_request.deletion_type}",
            metadata={
                "deletion_type": deletion_request.deletion_type,
                "reason": deletion_request.reason,
                "scheduled_for": scheduled_for.isoformat(),
                "retention_days": retention_days
            }
        )
        
        # Schedule user account for deactivation (but not deletion yet)
        await data_privacy_service.schedule_user_deletion(
            db, current_user.id, deletion_request.reason
        )
        
        return DeletionRequestResponse(
            request_id=deletion_req.id,
            status=deletion_req.status,
            deletion_type=deletion_req.deletion_type,
            scheduled_for=deletion_req.scheduled_for,
            retention_period_days=deletion_req.retention_period_days,
            verification_required=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process deletion request: {e}")
        await audit_service.log_privacy_action(
            db=db,
            user_id=current_user.id,
            privacy_action="deletion_request",
            request=request,
            details="Deletion request failed",
            metadata={"error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process deletion request"
        )


@router.delete("/deletion-request/{request_id}")
async def cancel_deletion_request(
    request_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cancel a pending data deletion request.
    
    This endpoint allows users to cancel their deletion request
    during the retention period.
    """
    try:
        # Find the deletion request
        deletion_req = db.query(DataDeletionRequest).filter(
            DataDeletionRequest.id == request_id,
            DataDeletionRequest.user_id == current_user.id,
            DataDeletionRequest.status == "scheduled"
        ).first()
        
        if not deletion_req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deletion request not found or cannot be cancelled"
            )
        
        # Cancel the request
        deletion_req.status = "cancelled"
        deletion_req.completed_at = datetime.utcnow()
        
        # Reactivate user account
        current_user.is_active = True
        current_user.updated_at = datetime.utcnow()
        
        db.commit()
        
        # Log the cancellation
        await audit_service.log_privacy_action(
            db=db,
            user_id=current_user.id,
            privacy_action="deletion_cancellation",
            request=request,
            details="Data deletion request cancelled",
            metadata={
                "request_id": request_id,
                "original_deletion_type": deletion_req.deletion_type
            }
        )
        
        return {"message": "Deletion request cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel deletion request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel deletion request"
        )


@router.get("/audit-log", response_model=AuditLogResponse)
async def get_audit_log(
    page: int = 1,
    page_size: int = 50,
    action_filter: Optional[str] = None,
    sensitivity_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get audit log entries for the current user.
    
    This endpoint provides access to the user's audit log,
    showing all actions performed on their data.
    """
    try:
        # Validate page parameters
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 50
        
        offset = (page - 1) * page_size
        
        # Get audit log entries
        entries = await audit_service.get_user_audit_log(
            db=db,
            user_id=current_user.id,
            limit=page_size,
            offset=offset,
            action_filter=action_filter,
            sensitivity_filter=sensitivity_filter
        )
        
        # Get total count for pagination
        query = db.query(AuditLog).filter(AuditLog.user_id == current_user.id)
        if action_filter:
            query = query.filter(AuditLog.action.like(f"%{action_filter}%"))
        if sensitivity_filter:
            query = query.filter(AuditLog.sensitivity_level == sensitivity_filter)
        total_count = query.count()
        
        # Convert to response format
        audit_entries = [
            AuditLogEntry(
                id=entry.id,
                action=entry.action,
                resource_type=entry.resource_type,
                resource_id=entry.resource_id,
                details=entry.details,
                success=entry.success,
                sensitivity_level=entry.sensitivity_level,
                timestamp=entry.timestamp,
                ip_address=entry.ip_address
            )
            for entry in entries
        ]
        
        return AuditLogResponse(
            entries=audit_entries,
            total_count=total_count,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Failed to get audit log: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit log"
        )


@router.get("/deletion-status")
async def get_deletion_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the status of any pending deletion requests.
    
    This endpoint returns information about pending deletion requests
    for the current user.
    """
    try:
        deletion_request = db.query(DataDeletionRequest).filter(
            DataDeletionRequest.user_id == current_user.id,
            DataDeletionRequest.status.in_(["scheduled", "in_progress"])
        ).first()
        
        if not deletion_request:
            return {"status": "none", "message": "No pending deletion requests"}
        
        return {
            "status": deletion_request.status,
            "deletion_type": deletion_request.deletion_type,
            "scheduled_for": deletion_request.scheduled_for,
            "retention_period_days": deletion_request.retention_period_days,
            "days_remaining": (deletion_request.scheduled_for - datetime.utcnow()).days,
            "can_cancel": deletion_request.status == "scheduled",
            "export_requested": deletion_request.export_requested,
            "export_completed": deletion_request.export_completed
        }
        
    except Exception as e:
        logger.error(f"Failed to get deletion status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get deletion status"
        )


@router.post("/anonymize")
async def anonymize_user_data(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Anonymize user data instead of full deletion.
    
    This endpoint provides an alternative to full deletion by
    anonymizing user data while preserving aggregated analytics.
    """
    try:
        # Log the anonymization request
        await audit_service.log_privacy_action(
            db=db,
            user_id=current_user.id,
            privacy_action="anonymization",
            request=request,
            details="User data anonymization requested"
        )
        
        # Perform anonymization
        success = await data_privacy_service.anonymize_user_data(db, current_user.id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to anonymize user data"
            )
        
        return {"message": "User data anonymized successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to anonymize user data: {e}")
        await audit_service.log_privacy_action(
            db=db,
            user_id=current_user.id,
            privacy_action="anonymization",
            request=request,
            details="Data anonymization failed",
            metadata={"error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to anonymize user data"
        )