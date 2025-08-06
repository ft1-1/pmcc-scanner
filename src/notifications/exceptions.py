"""
Custom exceptions for the notification system.
"""


class NotificationError(Exception):
    """Base exception for notification system errors."""
    pass


class ConfigurationError(NotificationError):
    """Raised when notification system is misconfigured."""
    pass


class ChannelError(NotificationError):
    """Base exception for channel-specific errors."""
    
    def __init__(self, message: str, channel: str, retryable: bool = False):
        super().__init__(message)
        self.channel = channel
        self.retryable = retryable


class WhatsAppError(ChannelError):
    """Exception for WhatsApp-specific errors."""
    
    def __init__(self, message: str, error_code: int = None, retryable: bool = False):
        super().__init__(message, "whatsapp", retryable)
        self.error_code = error_code


class EmailError(ChannelError):
    """Exception for email-specific errors."""
    
    def __init__(self, message: str, status_code: int = None, retryable: bool = False):
        super().__init__(message, "email", retryable)
        self.status_code = status_code


class RateLimitError(NotificationError):
    """Raised when rate limits are exceeded."""
    
    def __init__(self, message: str, retry_after: int = None):
        super().__init__(message)
        self.retry_after = retry_after


class InvalidRecipientError(NotificationError):
    """Raised when recipient information is invalid."""
    
    def __init__(self, message: str, recipient: str):
        super().__init__(message)
        self.recipient = recipient


class TemplateError(NotificationError):
    """Raised when template formatting fails."""
    pass


class DeliveryError(NotificationError):
    """Raised when message delivery fails."""
    
    def __init__(self, message: str, permanent: bool = False):
        super().__init__(message)
        self.permanent = permanent