"""
Audit Service for logging data access and modifications.

This service provides comprehensive audit logging for:
- Data access events
- Data modifications
- Privacy-related actions
- Security events
- System actions
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from fastapi import Request
from ..models import AuditLog, User
from ..security import input_sanitizer

logger = logging.getLogger(__name__)


class AuditService:
    """Handles audit logging for data access and modifications."""
    
    # Sensitivity levels for different types of actions
    SENSITIVITY_LEVELS = {
        "low": ["login", "logout", "profile_view"],
        "normal": ["product_create", "product_update", "post_create", "settings_update"],
        "high": ["platform_connect", "token_refresh", "data_export_request"],
        "critical": ["data_export", "data_deletion", "account_deletion", "admin_access"]
    }
    
    def __init__(self):
        self.sanitizer = input_sanitizer
    
    async def log_action(
        self,
        db: Session,
        action: str,
        resource_type: str,
        user_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> AuditLog:
        """
        Log an audit event.
        
        Args:
            db: Database session
            action: Action being performed
            resource_type: Type of resource being accessed
            user_id: ID of user performing action
            resource_id: ID of resource being accessed
            details: Human-readable details
            metadata: Structured metadata
            request: FastAPI request object
            success: Whether action was successful
            error_message: Error message if action failed
            
        Returns:
            Created AuditLog entry
        """
        try:
            # Determine sensitivity level
            sensitivity_level = self._get_sensitivity_level(action)
            
            # Extract request information
            ip_address = None
            user_agent = None
            request_method = None
            request_path = None
            
            if request:
                ip_address = self._get_client_ip(request)
                user_agent = request.headers.get("user-agent", "")[:500]  # Limit length
                request_method = request.method
                request_path = str(request.url.path)[:500]  # Limit length
            
            # Sanitize inputs
            if details:
                details = self.sanitizer.sanitize_string(details, max_length=2000)
            
            if error_message:
                error_message = self.sanitizer.sanitize_string(error_message, max_length=1000)
            
            # Create audit log entry
            audit_entry = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                request_method=request_method,
                request_path=request_path,
                details=details,
                action_metadata=metadata or {},
                success=success,
                error_message=error_message,
                sensitivity_level=sensitivity_level,
                timestamp=datetime.utcnow()
            )
            
            db.add(audit_entry)
            db.commit()
            db.refresh(audit_entry)
            
            # Log to application logger for immediate visibility
            log_level = logging.WARNING if not success else logging.INFO
            if sensitivity_level == "critical":
                log_level = logging.ERROR if not success else logging.WARNING
            
            logger.log(
                log_level,
                f"AUDIT: {action} on {resource_type} by user {user_id} - "
                f"Success: {success} - IP: {ip_address}"
            )
            
            return audit_entry
            
        except Exception as e:
            logger.error(f"Failed to create audit log entry: {e}")
            # Don't let audit logging failures break the main operation
            # Create a minimal entry in the application log
            logger.error(
                f"AUDIT_FAILURE: {action} on {resource_type} by user {user_id} - "
                f"Audit logging failed: {str(e)}"
            )
            raise
    
    def _get_sensitivity_level(self, action: str) -> str:
        """
        Determine sensitivity level for an action.
        
        Args:
            action: Action being performed
            
        Returns:
            Sensitivity level string
        """
        for level, actions in self.SENSITIVITY_LEVELS.items():
            if action in actions:
                return level
        
        # Default to normal for unknown actions
        return "normal"
    
    def _get_client_ip(self, request: Request) -> Optional[str]:
        """
        Extract client IP address from request.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Client IP address or None
        """
        # Check for forwarded headers (common in load balancer setups)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()
        
        # Check for real IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        
        # Fall back to direct client IP
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return None
    
    async def log_data_access(
        self,
        db: Session,
        user_id: str,
        resource_type: str,
        resource_id: str,
        access_type: str = "read",
        request: Optional[Request] = None,
        details: Optional[str] = None
    ) -> AuditLog:
        """
        Log data access event.
        
        Args:
            db: Database session
            user_id: User accessing data
            resource_type: Type of resource accessed
            resource_id: ID of resource accessed
            access_type: Type of access (read, write, delete)
            request: FastAPI request object
            details: Additional details
            
        Returns:
            Created AuditLog entry
        """
        action = f"data_{access_type}"
        
        metadata = {
            "access_type": access_type,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return await self.log_action(
            db=db,
            action=action,
            resource_type=resource_type,
            user_id=user_id,
            resource_id=resource_id,
            details=details,
            action_metadata=metadata,
            request=request
        )
    
    async def log_privacy_action(
        self,
        db: Session,
        user_id: str,
        privacy_action: str,
        request: Optional[Request] = None,
        details: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """
        Log privacy-related action.
        
        Args:
            db: Database session
            user_id: User ID
            privacy_action: Privacy action (export, deletion, anonymization)
            request: FastAPI request object
            details: Additional details
            metadata: Additional metadata
            
        Returns:
            Created AuditLog entry
        """
        action_map = {
            "export": "data_export",
            "deletion": "data_deletion",
            "anonymization": "data_anonymization",
            "deletion_request": "deletion_request",
            "deletion_cancellation": "deletion_cancellation"
        }
        
        action = action_map.get(privacy_action, f"privacy_{privacy_action}")
        
        privacy_metadata = {
            "privacy_action": privacy_action,
            "timestamp": datetime.utcnow().isoformat(),
            **(metadata or {})
        }
        
        return await self.log_action(
            db=db,
            action=action,
            resource_type="user_data",
            user_id=user_id,
            resource_id=user_id,
            details=details,
            action_metadata=privacy_metadata,
            request=request
        )
    
    async def log_security_event(
        self,
        db: Session,
        event_type: str,
        user_id: Optional[str] = None,
        request: Optional[Request] = None,
        details: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> AuditLog:
        """
        Log security-related event.
        
        Args:
            db: Database session
            event_type: Type of security event
            user_id: User ID (if applicable)
            request: FastAPI request object
            details: Additional details
            metadata: Additional metadata
            success: Whether event was successful
            error_message: Error message if failed
            
        Returns:
            Created AuditLog entry
        """
        action = f"security_{event_type}"
        
        security_metadata = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            **(metadata or {})
        }
        
        return await self.log_action(
            db=db,
            action=action,
            resource_type="security",
            user_id=user_id,
            details=details,
            action_metadata=security_metadata,
            request=request,
            success=success,
            error_message=error_message
        )
    
    async def get_user_audit_log(
        self,
        db: Session,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
        action_filter: Optional[str] = None,
        sensitivity_filter: Optional[str] = None
    ) -> List[AuditLog]:
        """
        Get audit log entries for a specific user.
        
        Args:
            db: Database session
            user_id: User ID
            limit: Maximum number of entries to return
            offset: Number of entries to skip
            action_filter: Filter by action type
            sensitivity_filter: Filter by sensitivity level
            
        Returns:
            List of AuditLog entries
        """
        query = db.query(AuditLog).filter(AuditLog.user_id == user_id)
        
        if action_filter:
            query = query.filter(AuditLog.action.like(f"%{action_filter}%"))
        
        if sensitivity_filter:
            query = query.filter(AuditLog.sensitivity_level == sensitivity_filter)
        
        return query.order_by(desc(AuditLog.timestamp)).offset(offset).limit(limit).all()
    
    async def get_critical_events(
        self,
        db: Session,
        hours: int = 24,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Get critical security events from the last N hours.
        
        Args:
            db: Database session
            hours: Number of hours to look back
            limit: Maximum number of entries to return
            
        Returns:
            List of critical AuditLog entries
        """
        since = datetime.utcnow() - timedelta(hours=hours)
        
        return db.query(AuditLog).filter(
            and_(
                AuditLog.sensitivity_level == "critical",
                AuditLog.timestamp >= since
            )
        ).order_by(desc(AuditLog.timestamp)).limit(limit).all()
    
    async def get_failed_actions(
        self,
        db: Session,
        hours: int = 24,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Get failed actions from the last N hours.
        
        Args:
            db: Database session
            hours: Number of hours to look back
            limit: Maximum number of entries to return
            
        Returns:
            List of failed AuditLog entries
        """
        since = datetime.utcnow() - timedelta(hours=hours)
        
        return db.query(AuditLog).filter(
            and_(
                AuditLog.success == False,
                AuditLog.timestamp >= since
            )
        ).order_by(desc(AuditLog.timestamp)).limit(limit).all()
    
    async def cleanup_old_logs(
        self,
        db: Session,
        retention_days: int = 365
    ) -> int:
        """
        Clean up old audit log entries.
        
        Args:
            db: Database session
            retention_days: Number of days to retain logs
            
        Returns:
            Number of entries deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        # Keep critical events longer (2x retention period)
        critical_cutoff = datetime.utcnow() - timedelta(days=retention_days * 2)
        
        # Delete non-critical old entries
        deleted_count = db.query(AuditLog).filter(
            and_(
                AuditLog.timestamp < cutoff_date,
                AuditLog.sensitivity_level != "critical"
            )
        ).delete()
        
        # Delete very old critical entries
        deleted_count += db.query(AuditLog).filter(
            and_(
                AuditLog.timestamp < critical_cutoff,
                AuditLog.sensitivity_level == "critical"
            )
        ).delete()
        
        db.commit()
        
        logger.info(f"Cleaned up {deleted_count} old audit log entries")
        return deleted_count


# Global instance
audit_service = AuditService()