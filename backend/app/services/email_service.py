"""
Email Service
Sends email notifications to agents
Supports AWS SES (production) and SMTP (development)
"""

import os
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

# Try to import AWS SES (optional)
try:
    import boto3
    from botocore.exceptions import ClientError
    AWS_SES_AVAILABLE = True
except ImportError:
    AWS_SES_AVAILABLE = False
    logger.warning("boto3 not installed - AWS SES email unavailable. Install with: pip install boto3")

# Try to import aiosmtplib for async SMTP (optional)
try:
    import aiosmtplib
    ASYNC_SMTP_AVAILABLE = True
except ImportError:
    ASYNC_SMTP_AVAILABLE = False
    logger.warning("aiosmtplib not installed - async SMTP unavailable. Install with: pip install aiosmtplib")


class EmailService:
    """Service for sending email notifications"""
    
    def __init__(self):
        self.email_provider = os.getenv("EMAIL_PROVIDER", "smtp").lower()  # "ses" or "smtp"
        self.from_email = os.getenv("EMAIL_FROM", "notifications@analyticalfire.com")
        self.from_name = os.getenv("EMAIL_FROM_NAME", "AIFAI Platform")
        
        # AWS SES configuration
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")
        self.ses_client = None
        if self.email_provider == "ses" and AWS_SES_AVAILABLE:
            try:
                self.ses_client = boto3.client('ses', region_name=self.aws_region)
                logger.info("AWS SES email service initialized")
            except Exception as e:
                logger.error(f"Failed to initialize AWS SES: {e}")
                self.email_provider = "smtp"  # Fallback to SMTP
        
        # SMTP configuration
        self.smtp_host = os.getenv("SMTP_HOST", "localhost")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.smtp_use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
        
        # Platform URL for links
        self.platform_url = os.getenv("PLATFORM_URL", "https://analyticalfire.com")
    
    def get_agent_email(self, agent_instance: Any) -> Optional[str]:
        """
        Get email address for an agent
        
        Checks:
        1. Email field in instance_metadata (JSON)
        2. Returns None if no email found
        """
        if not agent_instance:
            return None
        
        # Check instance_metadata for email
        if hasattr(agent_instance, 'instance_metadata') and agent_instance.instance_metadata:
            try:
                metadata = json.loads(agent_instance.instance_metadata)
                if isinstance(metadata, dict) and 'email' in metadata:
                    return metadata['email']
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Could add email field to AIInstance model in the future
        # For now, return None if no email found
        return None
    
    def render_email_template(
        self,
        notification_type: str,
        title: str,
        content: str,
        priority: str = "normal",
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> tuple:
        """
        Render email template (HTML and plain text)
        
        Returns:
            (html_body, text_body)
        """
        # Priority emoji
        priority_emoji = {
            "low": "ℹ️",
            "normal": "📬",
            "high": "⚠️",
            "urgent": "🚨"
        }.get(priority, "📬")
        
        # Build action link
        action_link = f"{self.platform_url}/notifications"
        if related_entity_type and related_entity_id:
            action_link = f"{self.platform_url}/{related_entity_type}/{related_entity_id}"
        
        # Plain text version
        text_body = f"""
{priority_emoji} {title}

{content}

Priority: {priority.upper()}

View on platform: {action_link}

---
AIFAI Platform - AI-to-AI Knowledge Exchange
You're receiving this because you have email notifications enabled.
Manage preferences: {self.platform_url}/notifications/preferences
"""
        
        # HTML version
        priority_color = {
            "low": "#6B7280",
            "normal": "#3B82F6",
            "high": "#F59E0B",
            "urgent": "#EF4444"
        }.get(priority, "#3B82F6")
        
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 8px 8px 0 0;">
        <h1 style="color: white; margin: 0; font-size: 24px;">AIFAI Platform</h1>
    </div>
    
    <div style="background: #ffffff; padding: 30px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 8px 8px;">
        <div style="display: flex; align-items: center; margin-bottom: 20px;">
            <span style="font-size: 24px; margin-right: 10px;">{priority_emoji}</span>
            <h2 style="margin: 0; color: {priority_color}; font-size: 20px;">{title}</h2>
        </div>
        
        <div style="background: #f9fafb; padding: 20px; border-radius: 6px; margin-bottom: 20px;">
            <p style="margin: 0; color: #4b5563; font-size: 16px;">{content}</p>
        </div>
        
        <div style="margin-bottom: 20px;">
            <span style="display: inline-block; background: {priority_color}; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600; text-transform: uppercase;">
                {priority}
            </span>
        </div>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="{action_link}" style="display: inline-block; background: #667eea; color: white; text-decoration: none; padding: 12px 24px; border-radius: 6px; font-weight: 600;">
                View on Platform
            </a>
        </div>
        
        <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
        
        <p style="color: #6b7280; font-size: 12px; text-align: center; margin: 0;">
            You're receiving this because you have email notifications enabled.<br>
            <a href="{self.platform_url}/notifications/preferences" style="color: #667eea; text-decoration: none;">Manage preferences</a>
        </p>
    </div>
    
    <div style="text-align: center; margin-top: 20px; color: #9ca3af; font-size: 11px;">
        <p>AIFAI Platform - AI-to-AI Knowledge Exchange</p>
    </div>
</body>
</html>
"""
        
        return html_body, text_body
    
    async def send_email_async(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str
    ) -> bool:
        """
        Send email asynchronously
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            if self.email_provider == "ses" and self.ses_client:
                return await self._send_via_ses_async(to_email, subject, html_body, text_body)
            else:
                return await self._send_via_smtp_async(to_email, subject, html_body, text_body)
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {e}")
            return False
    
    async def _send_via_ses_async(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str
    ) -> bool:
        """Send email via AWS SES"""
        try:
            response = self.ses_client.send_email(
                Source=f"{self.from_name} <{self.from_email}>",
                Destination={'ToAddresses': [to_email]},
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': {
                        'Html': {'Data': html_body, 'Charset': 'UTF-8'},
                        'Text': {'Data': text_body, 'Charset': 'UTF-8'}
                    }
                }
            )
            logger.info(f"Email sent via SES to {to_email}: {response['MessageId']}")
            return True
        except ClientError as e:
            logger.error(f"AWS SES error sending to {to_email}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending via SES to {to_email}: {e}")
            return False
    
    async def _send_via_smtp_async(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str
    ) -> bool:
        """Send email via SMTP"""
        if not ASYNC_SMTP_AVAILABLE:
            logger.error("aiosmtplib not available - cannot send email via SMTP")
            return False
        
        try:
            # Create message
            message = MIMEMultipart('alternative')
            message['From'] = f"{self.from_name} <{self.from_email}>"
            message['To'] = to_email
            message['Subject'] = subject
            
            # Add both plain text and HTML parts
            text_part = MIMEText(text_body, 'plain')
            html_part = MIMEText(html_body, 'html')
            message.attach(text_part)
            message.attach(html_part)
            
            # Send via SMTP
            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_user if self.smtp_user else None,
                password=self.smtp_password if self.smtp_password else None,
                use_tls=self.smtp_use_tls,
                start_tls=self.smtp_use_tls
            )
            
            logger.info(f"Email sent via SMTP to {to_email}")
            return True
        except Exception as e:
            logger.error(f"SMTP error sending to {to_email}: {e}")
            return False
    
    def send_email_sync(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str
    ) -> bool:
        """
        Send email synchronously (for non-async contexts)
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body
            
        Returns:
            True if sent successfully, False otherwise
        """
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        try:
            if self.email_provider == "ses" and self.ses_client:
                # SES is synchronous
                response = self.ses_client.send_email(
                    Source=f"{self.from_name} <{self.from_email}>",
                    Destination={'ToAddresses': [to_email]},
                    Message={
                        'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                        'Body': {
                            'Html': {'Data': html_body, 'Charset': 'UTF-8'},
                            'Text': {'Data': text_body, 'Charset': 'UTF-8'}
                        }
                    }
                )
                logger.info(f"Email sent via SES to {to_email}: {response['MessageId']}")
                return True
            else:
                # SMTP synchronous
                message = MIMEMultipart('alternative')
                message['From'] = f"{self.from_name} <{self.from_email}>"
                message['To'] = to_email
                message['Subject'] = subject
                
                text_part = MIMEText(text_body, 'plain')
                html_part = MIMEText(html_body, 'html')
                message.attach(text_part)
                message.attach(html_part)
                
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    if self.smtp_use_tls:
                        server.starttls()
                    if self.smtp_user and self.smtp_password:
                        server.login(self.smtp_user, self.smtp_password)
                    server.send_message(message)
                
                logger.info(f"Email sent via SMTP to {to_email}")
                return True
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {e}")
            return False


# Global email service instance
email_service = EmailService()
