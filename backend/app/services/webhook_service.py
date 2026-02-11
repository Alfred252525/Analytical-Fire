"""
Webhook Service
Sends notification webhooks to agent endpoints
Includes retry logic, signature verification, and error handling
"""

import os
import json
import hmac
import hashlib
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)

# Webhook configuration
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "change-me-in-production")
WEBHOOK_TIMEOUT = int(os.getenv("WEBHOOK_TIMEOUT", "10"))  # seconds
WEBHOOK_MAX_RETRIES = int(os.getenv("WEBHOOK_MAX_RETRIES", "3"))
WEBHOOK_RETRY_DELAY = float(os.getenv("WEBHOOK_RETRY_DELAY", "1.0"))  # seconds


class WebhookService:
    """Service for sending webhook notifications"""
    
    def __init__(self):
        self.secret = WEBHOOK_SECRET
        self.timeout = WEBHOOK_TIMEOUT
        self.max_retries = WEBHOOK_MAX_RETRIES
        self.retry_delay = WEBHOOK_RETRY_DELAY
    
    def generate_signature(self, payload: str) -> str:
        """
        Generate HMAC signature for webhook payload
        
        Args:
            payload: JSON string of webhook payload
            
        Returns:
            HMAC SHA256 signature
        """
        return hmac.new(
            self.secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def build_webhook_payload(
        self,
        notification: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build webhook payload from notification
        
        Args:
            notification: Notification object
            metadata: Additional metadata (optional)
            
        Returns:
            Webhook payload dictionary
        """
        import json as json_module
        
        # Parse notification metadata if present
        notification_metadata = None
        if notification.notification_metadata:
            try:
                notification_metadata = json_module.loads(notification.notification_metadata)
            except (json_module.JSONDecodeError, TypeError):
                pass
        
        payload = {
            "event": "notification",
            "notification": {
                "id": notification.id,
                "notification_type": notification.notification_type.value if hasattr(notification.notification_type, 'value') else str(notification.notification_type),
                "title": notification.title,
                "content": notification.content,
                "priority": notification.priority,
                "read": notification.read,
                "created_at": notification.created_at.isoformat() if notification.created_at else None,
                "read_at": notification.read_at.isoformat() if notification.read_at else None,
                "related_entity_type": notification.related_entity_type,
                "related_entity_id": notification.related_entity_id,
                "metadata": notification_metadata or metadata
            },
            "timestamp": datetime.utcnow().isoformat(),
            "platform": "aifai"
        }
        
        return payload
    
    async def send_webhook_async(
        self,
        webhook_url: str,
        payload: Dict[str, Any],
        retry_count: int = 0
    ) -> tuple:
        """
        Send webhook asynchronously with retry logic
        
        Args:
            webhook_url: Webhook endpoint URL
            payload: Webhook payload
            retry_count: Current retry attempt (default: 0)
            
        Returns:
            (success: bool, error_message: Optional[str])
        """
        try:
            # Convert payload to JSON string for signature
            payload_json = json.dumps(payload, sort_keys=True)
            
            # Generate signature
            signature = self.generate_signature(payload_json)
            
            # Prepare headers
            headers = {
                "Content-Type": "application/json",
                "X-AIFAI-Signature": f"sha256={signature}",
                "X-AIFAI-Event": "notification",
                "User-Agent": "AIFAI-Webhook/1.0"
            }
            
            # Send webhook
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    webhook_url,
                    json=payload,
                    headers=headers
                )
                
                # Check response
                if response.status_code >= 200 and response.status_code < 300:
                    logger.info(f"Webhook sent successfully to {webhook_url}: {response.status_code}")
                    return True, None
                else:
                    error_msg = f"Webhook returned status {response.status_code}: {response.text[:200]}"
                    logger.warning(f"Webhook failed to {webhook_url}: {error_msg}")
                    
                    # Retry on server errors (5xx) or rate limiting (429)
                    if (response.status_code >= 500 or response.status_code == 429) and retry_count < self.max_retries:
                        import asyncio
                        await asyncio.sleep(self.retry_delay * (retry_count + 1))  # Exponential backoff
                        return await self.send_webhook_async(webhook_url, payload, retry_count + 1)
                    
                    return False, error_msg
                    
        except httpx.TimeoutException:
            error_msg = f"Webhook timeout to {webhook_url}"
            logger.warning(error_msg)
            
            # Retry on timeout
            if retry_count < self.max_retries:
                import asyncio
                await asyncio.sleep(self.retry_delay * (retry_count + 1))
                return await self.send_webhook_async(webhook_url, payload, retry_count + 1)
            
            return False, error_msg
            
        except httpx.RequestError as e:
            error_msg = f"Webhook request error to {webhook_url}: {str(e)}"
            logger.error(error_msg)
            
            # Retry on connection errors
            if retry_count < self.max_retries:
                import asyncio
                await asyncio.sleep(self.retry_delay * (retry_count + 1))
                return await self.send_webhook_async(webhook_url, payload, retry_count + 1)
            
            return False, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error sending webhook to {webhook_url}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def verify_webhook_signature(self, payload: str, signature: str) -> bool:
        """
        Verify webhook signature (for incoming webhooks)
        
        Args:
            payload: JSON string of webhook payload
            signature: Signature from X-AIFAI-Signature header (format: "sha256=...")
            
        Returns:
            True if signature is valid
        """
        try:
            # Extract signature from "sha256=..." format
            if signature.startswith("sha256="):
                received_signature = signature[7:]
            else:
                received_signature = signature
            
            # Generate expected signature
            expected_signature = self.generate_signature(payload)
            
            # Constant-time comparison to prevent timing attacks
            return hmac.compare_digest(received_signature, expected_signature)
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {e}")
            return False


# Global webhook service instance
webhook_service = WebhookService()
