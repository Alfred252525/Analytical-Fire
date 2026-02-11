"""
Security Alert Service
Sends email alerts directly when security thresholds are exceeded
Uses AWS SES (free tier) or SMTP - no SNS required
"""

import os
import logging
from typing import Optional
from datetime import datetime, timedelta
from collections import defaultdict

from app.services.email_service import email_service
from app.core.config import settings

# Try to import Redis for threshold tracking
try:
    import redis
    try:
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        redis_client.ping()
        REDIS_AVAILABLE = True
    except Exception:
        REDIS_AVAILABLE = False
        redis_client = None
except ImportError:
    REDIS_AVAILABLE = False
    redis_client = None

logger = logging.getLogger(__name__)

# Alert thresholds (5-minute windows)
THRESHOLDS = {
    "failed_logins": 10,  # Alert if >10 failed logins in 5 minutes
    "rate_limit_exceeded": 50,  # Alert if >50 rate limit hits in 5 minutes
    "security_events": 5,  # Alert if >5 high-severity security events in 5 minutes
}

# Alert email recipient
ALERT_EMAIL = os.getenv("SECURITY_ALERT_EMAIL", "greg@analyticalinsider.com")

# Track last alert time to avoid spam (don't alert more than once per 15 minutes)
LAST_ALERT_TIME = {}
ALERT_COOLDOWN_MINUTES = 15


class SecurityAlertService:
    """Service for sending security alerts via email"""
    
    def __init__(self):
        self.redis_client = redis_client
        self.redis_available = REDIS_AVAILABLE
        
        # In-memory fallback if Redis unavailable
        self.counts: dict = defaultdict(int)
        self.window_start: dict = {}
        self.window_duration = timedelta(minutes=5)
    
    def _get_redis_key(self, alert_type: str) -> str:
        """Get Redis key for tracking counts"""
        return f"security:alert:{alert_type}"
    
    def _increment_count(self, alert_type: str) -> int:
        """Increment count for alert type and return current count"""
        if self.redis_available and self.redis_client:
            try:
                key = self._get_redis_key(alert_type)
                # Increment and set TTL to 5 minutes (300 seconds)
                count = self.redis_client.incr(key)
                if count == 1:
                    # First increment, set TTL
                    self.redis_client.expire(key, 300)
                return count
            except Exception as e:
                logger.warning(f"Redis error tracking {alert_type}: {e}")
                # Fallback to in-memory
                return self._increment_count_memory(alert_type)
        else:
            return self._increment_count_memory(alert_type)
    
    def _increment_count_memory(self, alert_type: str) -> int:
        """Increment count using in-memory storage (fallback)"""
        now = datetime.utcnow()
        key = alert_type
        
        # Reset window if expired
        if key not in self.window_start or now - self.window_start[key] > self.window_duration:
            self.counts[key] = 0
            self.window_start[key] = now
        
        self.counts[key] += 1
        return self.counts[key]
    
    def _should_send_alert(self, alert_type: str) -> bool:
        """Check if we should send an alert (cooldown check)"""
        now = datetime.utcnow()
        last_alert = LAST_ALERT_TIME.get(alert_type)
        
        if last_alert:
            time_since_last = now - last_alert
            if time_since_last < timedelta(minutes=ALERT_COOLDOWN_MINUTES):
                return False  # Still in cooldown
        
        return True
    
    def _send_alert_email(
        self,
        alert_type: str,
        count: int,
        threshold: int,
        details: Optional[str] = None
    ) -> bool:
        """Send alert email"""
        if not self._should_send_alert(alert_type):
            logger.debug(f"Alert {alert_type} skipped (cooldown)")
            return False
        
        # Update last alert time
        LAST_ALERT_TIME[alert_type] = datetime.utcnow()
        
        # Format alert details
        alert_titles = {
            "failed_logins": "🚨 Failed Login Attempts Alert",
            "rate_limit_exceeded": "⚠️ Rate Limit Exceeded Alert",
            "security_events": "🔒 Security Events Alert"
        }
        
        alert_descriptions = {
            "failed_logins": f"Multiple failed login attempts detected. This could indicate a brute force attack.",
            "rate_limit_exceeded": f"High rate of rate limit violations detected. This could indicate abuse or DDoS attempt.",
            "security_events": f"Multiple high-severity security events detected. Review immediately."
        }
        
        title = alert_titles.get(alert_type, "Security Alert")
        description = alert_descriptions.get(alert_type, "Security threshold exceeded")
        
        # Build email content
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #EF4444 0%, #DC2626 100%); padding: 30px; text-align: center; border-radius: 8px 8px 0 0;">
        <h1 style="color: white; margin: 0; font-size: 24px;">Security Alert</h1>
    </div>
    
    <div style="background: #ffffff; padding: 30px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 8px 8px;">
        <h2 style="color: #EF4444; margin-top: 0;">{title}</h2>
        
        <div style="background: #FEF2F2; padding: 20px; border-left: 4px solid #EF4444; border-radius: 4px; margin-bottom: 20px;">
            <p style="margin: 0; color: #991B1B; font-size: 16px;"><strong>{description}</strong></p>
        </div>
        
        <div style="background: #F9FAFB; padding: 20px; border-radius: 6px; margin-bottom: 20px;">
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; color: #6B7280; font-weight: 600;">Alert Type:</td>
                    <td style="padding: 8px 0; color: #111827;">{alert_type.replace('_', ' ').title()}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #6B7280; font-weight: 600;">Current Count:</td>
                    <td style="padding: 8px 0; color: #EF4444; font-weight: 700;">{count}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #6B7280; font-weight: 600;">Threshold:</td>
                    <td style="padding: 8px 0; color: #111827;">{threshold}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #6B7280; font-weight: 600;">Time Window:</td>
                    <td style="padding: 8px 0; color: #111827;">5 minutes</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #6B7280; font-weight: 600;">Timestamp:</td>
                    <td style="padding: 8px 0; color: #111827;">{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</td>
                </tr>
            </table>
        </div>
        
        {f'<div style="background: #F3F4F6; padding: 15px; border-radius: 4px; margin-bottom: 20px;"><p style="margin: 0; color: #374151; font-size: 14px;"><strong>Details:</strong> {details}</p></div>' if details else ''}
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="{settings.PLATFORM_URL}/api/v1/stats/public" style="display: inline-block; background: #EF4444; color: white; text-decoration: none; padding: 12px 24px; border-radius: 6px; font-weight: 600;">
                View Platform Status
            </a>
        </div>
        
        <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
        
        <p style="color: #6b7280; font-size: 12px; text-align: center; margin: 0;">
            This is an automated security alert from AIFAI Platform.<br>
            Platform: <a href="{settings.PLATFORM_URL}" style="color: #667eea; text-decoration: none;">{settings.PLATFORM_URL}</a>
        </p>
    </div>
</body>
</html>
"""
        
        text_body = f"""
{title}

{description}

Alert Type: {alert_type.replace('_', ' ').title()}
Current Count: {count}
Threshold: {threshold}
Time Window: 5 minutes
Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

{f'Details: {details}' if details else ''}

View Platform Status: {settings.PLATFORM_URL}/api/v1/stats/public

---
This is an automated security alert from AIFAI Platform.
Platform: {settings.PLATFORM_URL}
"""
        
        # Send email synchronously (alerts are time-sensitive)
        try:
            success = email_service.send_email_sync(
                to_email=ALERT_EMAIL,
                subject=f"{title} - {count} events (threshold: {threshold})",
                html_body=html_body,
                text_body=text_body
            )
            
            if success:
                logger.info(f"Security alert email sent to {ALERT_EMAIL} for {alert_type} (count: {count})")
            else:
                logger.error(f"Failed to send security alert email for {alert_type}")
            
            return success
        except Exception as e:
            logger.error(f"Error sending security alert email: {e}")
            return False
    
    def check_and_alert_failed_logins(self, details: Optional[str] = None) -> bool:
        """Check failed login count and send alert if threshold exceeded"""
        count = self._increment_count("failed_logins")
        threshold = THRESHOLDS["failed_logins"]
        
        if count > threshold:
            return self._send_alert_email("failed_logins", count, threshold, details)
        return False
    
    def check_and_alert_rate_limit(self, details: Optional[str] = None) -> bool:
        """Check rate limit exceeded count and send alert if threshold exceeded"""
        count = self._increment_count("rate_limit_exceeded")
        threshold = THRESHOLDS["rate_limit_exceeded"]
        
        if count > threshold:
            return self._send_alert_email("rate_limit_exceeded", count, threshold, details)
        return False
    
    def check_and_alert_security_events(self, details: Optional[str] = None) -> bool:
        """Check security events count and send alert if threshold exceeded"""
        count = self._increment_count("security_events")
        threshold = THRESHOLDS["security_events"]
        
        if count > threshold:
            return self._send_alert_email("security_events", count, threshold, details)
        return False


# Global security alert service instance
security_alerts = SecurityAlertService()
