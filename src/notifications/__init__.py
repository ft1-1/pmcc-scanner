"""
Notification system for PMCC Scanner.

This module provides multi-channel notification capabilities for alerting users
about profitable PMCC opportunities. It supports WhatsApp (primary) and email
(fallback) with automatic retry logic and delivery tracking.
"""

from src.notifications.notification_manager import NotificationManager
from src.notifications.whatsapp_sender import WhatsAppSender
from src.notifications.email_sender import EmailSender
from src.notifications.formatters import WhatsAppFormatter, EmailFormatter
from src.notifications.models import (
    NotificationResult, NotificationChannel, NotificationStatus,
    NotificationConfig, NotificationTemplate, NotificationRequest
)
from src.notifications.circuit_breaker import CircuitBreaker
from src.notifications.exceptions import (
    NotificationError, ConfigurationError, ChannelError,
    WhatsAppError, EmailError, RateLimitError, InvalidRecipientError,
    TemplateError, DeliveryError
)

__all__ = [
    'NotificationManager',
    'WhatsAppSender',
    'EmailSender',
    'WhatsAppFormatter',
    'EmailFormatter',
    'NotificationResult',
    'NotificationChannel',
    'NotificationStatus',
    'NotificationConfig',
    'NotificationTemplate',
    'NotificationRequest',
    'CircuitBreaker',
    'NotificationError',
    'ConfigurationError',
    'ChannelError',
    'WhatsAppError',
    'EmailError',
    'RateLimitError',
    'InvalidRecipientError',
    'TemplateError',
    'DeliveryError'
]