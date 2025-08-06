"""
Data models for the notification system.
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime


class NotificationChannel(Enum):
    """Supported notification channels."""
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    SMS = "sms"


class NotificationStatus(Enum):
    """Status of a notification delivery attempt."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class NotificationResult:
    """Result of a notification delivery attempt."""
    channel: NotificationChannel
    status: NotificationStatus
    recipient: str
    message_id: Optional[str] = None
    error_message: Optional[str] = None
    attempt_count: int = 1
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    
    @property
    def is_success(self) -> bool:
        """Check if notification was successfully sent."""
        return self.status in [NotificationStatus.SENT, NotificationStatus.DELIVERED]
    
    @property
    def is_failure(self) -> bool:
        """Check if notification permanently failed."""
        return self.status == NotificationStatus.FAILED
    
    @property
    def should_retry(self) -> bool:
        """Check if notification should be retried."""
        return self.status == NotificationStatus.RETRYING


@dataclass
class NotificationConfig:
    """Configuration for notification delivery."""
    max_retries: int = 3
    retry_delay_seconds: int = 60
    enable_fallback: bool = True
    fallback_delay_seconds: int = 300  # 5 minutes
    
    # Channel-specific settings
    whatsapp_enabled: bool = True
    email_enabled: bool = True
    sms_enabled: bool = False


@dataclass
class NotificationTemplate:
    """Template for notification content."""
    subject: Optional[str] = None
    text_content: str = ""
    html_content: Optional[str] = None
    
    def format(self, **kwargs) -> 'NotificationTemplate':
        """Format template with provided variables."""
        formatted_subject = self.subject.format(**kwargs) if self.subject else None
        formatted_text = self.text_content.format(**kwargs)
        formatted_html = self.html_content.format(**kwargs) if self.html_content else None
        
        return NotificationTemplate(
            subject=formatted_subject,
            text_content=formatted_text,
            html_content=formatted_html
        )


@dataclass
class NotificationRequest:
    """Request to send a notification."""
    recipients: List[str]
    template: NotificationTemplate
    priority: str = "normal"  # low, normal, high, urgent
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if not self.recipients:
            raise ValueError("At least one recipient is required")
        if not self.template.text_content:
            raise ValueError("Text content is required")