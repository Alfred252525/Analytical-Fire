"""
Audit logging for security and compliance
Logs all security-relevant events for SOC 2 and HIPAA compliance
"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import Request
from sqlalchemy.orm import Session

from app.core.config import settings

# Import security alert service for email alerts
try:
    from app.services.security_alerts import security_alerts
    SECURITY_ALERTS_AVAILABLE = True
except ImportError:
    SECURITY_ALERTS_AVAILABLE = False
    security_alerts = None

# Try to import boto3 for CloudWatch metrics (optional)
try:
    import boto3
    cloudwatch = boto3.client('cloudwatch', region_name=settings.AWS_REGION if hasattr(settings, 'AWS_REGION') else 'us-east-1')
    CLOUDWATCH_AVAILABLE = True
except ImportError:
    CLOUDWATCH_AVAILABLE = False
    cloudwatch = None
except Exception:
    CLOUDWATCH_AVAILABLE = False
    cloudwatch = None

# Set up audit logger
audit_logger = logging.getLogger("audit")
audit_logger.setLevel(logging.INFO)

# Create handler for CloudWatch (or file in local dev)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
handler.setFormatter(formatter)
audit_logger.addHandler(handler)

class AuditLog:
    """Audit log entry structure"""
    
    @staticmethod
    def log_event(
        event_type: str,
        instance_id: Optional[str] = None,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        resource: Optional[str] = None,
        resource_id: Optional[int] = None,
        status: str = "success",
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """
        Log an audit event
        
        Args:
            event_type: Type of event (auth, access, data_access, security, etc.)
            instance_id: AI instance ID
            user_id: Database user ID
            action: Action performed (login, create, read, update, delete)
            resource: Resource type (knowledge_entry, message, decision, etc.)
            resource_id: ID of the resource accessed
            status: success, failure, denied
            details: Additional details as dict
            ip_address: Client IP address
            user_agent: Client user agent
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "instance_id": instance_id,
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "resource_id": resource_id,
            "status": status,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "details": details or {}
        }
        
        # Log as JSON for easy parsing
        audit_logger.info(json.dumps(log_entry))
        
        # Publish metrics to CloudWatch for monitoring (if available)
        if CLOUDWATCH_AVAILABLE and cloudwatch:
            try:
                namespace = "AIFAI/Security"
                
                # Publish event type metric
                cloudwatch.put_metric_data(
                    Namespace=namespace,
                    MetricData=[
                        {
                            'MetricName': f'{event_type.title()}Events',
                            'Value': 1,
                            'Unit': 'Count',
                            'Timestamp': datetime.utcnow()
                        }
                    ]
                )
                
                # Publish status-specific metrics for authentication events
                if event_type == "authentication" and status == "failure":
                    cloudwatch.put_metric_data(
                        Namespace=namespace,
                        MetricData=[
                            {
                                'MetricName': 'FailedLoginAttempts',
                                'Value': 1,
                                'Unit': 'Count',
                                'Timestamp': datetime.utcnow()
                            }
                        ]
                    )
                    
                    # Check and send email alert if threshold exceeded
                    if SECURITY_ALERTS_AVAILABLE and security_alerts:
                        try:
                            details = f"Instance: {instance_id}, IP: {ip_address}" if instance_id or ip_address else None
                            security_alerts.check_and_alert_failed_logins(details)
                        except Exception as e:
                            audit_logger.warning(f"Failed to send security alert: {e}")
                
                # Publish security event metrics
                if event_type == "security":
                    severity_value = {"low": 1, "medium": 2, "high": 3, "critical": 4}.get(status, 1)
                    
                    # Build metric data list
                    metric_data = [
                        {
                            'MetricName': 'SecurityEvents',
                            'Value': severity_value,
                            'Unit': 'Count',
                            'Timestamp': datetime.utcnow(),
                            'Dimensions': [
                                {'Name': 'Severity', 'Value': status}
                            ]
                        }
                    ]
                    
                    # Add specific metric for rate limit exceeded events
                    if action == "rate_limit_exceeded":
                        metric_data.append({
                            'MetricName': 'RateLimitExceeded',
                            'Value': 1,
                            'Unit': 'Count',
                            'Timestamp': datetime.utcnow()
                        })
                        
                        # Check and send email alert if threshold exceeded
                        if SECURITY_ALERTS_AVAILABLE and security_alerts:
                            try:
                                details = f"Instance: {instance_id}, IP: {ip_address}" if instance_id or ip_address else None
                                security_alerts.check_and_alert_rate_limit(details)
                            except Exception as e:
                                audit_logger.warning(f"Failed to send security alert: {e}")
                    
                    cloudwatch.put_metric_data(
                        Namespace=namespace,
                        MetricData=metric_data
                    )
                    
                    # Check and send email alert for high-severity security events
                    if event_type == "security" and status in ["high", "critical"]:
                        if SECURITY_ALERTS_AVAILABLE and security_alerts:
                            try:
                                details = f"Event: {action}, Severity: {status}, Instance: {instance_id}, IP: {ip_address}" if instance_id or ip_address else f"Event: {action}, Severity: {status}"
                                security_alerts.check_and_alert_security_events(details)
                            except Exception as e:
                                audit_logger.warning(f"Failed to send security alert: {e}")
            except Exception as e:
                # Don't fail the request if metrics fail
                audit_logger.warning(f"Failed to publish CloudWatch metrics: {e}")
    
    @staticmethod
    def log_authentication(
        instance_id: str,
        action: str,  # "login", "logout", "register", "token_refresh"
        status: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log authentication events"""
        AuditLog.log_event(
            event_type="authentication",
            instance_id=instance_id,
            action=action,
            status=status,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details
        )
    
    @staticmethod
    def log_data_access(
        instance_id: str,
        user_id: int,
        action: str,  # "read", "create", "update", "delete"
        resource: str,
        resource_id: Optional[int] = None,
        status: str = "success",
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log data access events"""
        AuditLog.log_event(
            event_type="data_access",
            instance_id=instance_id,
            user_id=user_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            status=status,
            ip_address=ip_address,
            details=details
        )
    
    @staticmethod
    def log_security_event(
        instance_id: Optional[str],
        event: str,  # "failed_auth", "rate_limit", "suspicious_activity", etc.
        severity: str = "medium",  # low, medium, high, critical
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log security-relevant events"""
        AuditLog.log_event(
            event_type="security",
            instance_id=instance_id,
            action=event,
            status=severity,
            ip_address=ip_address,
            details=details
        )
    
    @staticmethod
    def log_api_request(
        request: Request,
        instance_id: Optional[str],
        user_id: Optional[int],
        method: str,
        path: str,
        status_code: int,
        response_time_ms: Optional[float] = None
    ):
        """Log API request for audit trail"""
        # Only log authenticated requests or sensitive endpoints
        sensitive_paths = ["/api/v1/auth", "/api/v1/knowledge", "/api/v1/messaging", "/api/v1/decisions"]
        if instance_id or any(path.startswith(p) for p in sensitive_paths):
            AuditLog.log_event(
                event_type="api_request",
                instance_id=instance_id,
                user_id=user_id,
                action=method,
                resource=path,
                status="success" if 200 <= status_code < 400 else "failure",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                details={
                    "status_code": status_code,
                    "response_time_ms": response_time_ms
                }
            )
