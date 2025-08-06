"""
WhatsApp notification sender using Twilio WhatsApp Business API.
"""

import os
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import time

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from src.notifications.models import NotificationResult, NotificationChannel, NotificationStatus, NotificationTemplate


logger = logging.getLogger(__name__)


class WhatsAppSender:
    """
    WhatsApp message sender using Twilio WhatsApp Business API.
    
    Handles message formatting, delivery tracking, and error handling
    for WhatsApp notifications.
    """
    
    def __init__(self, account_sid: Optional[str] = None, auth_token: Optional[str] = None):
        """
        Initialize WhatsApp sender.
        
        Args:
            account_sid: Twilio account SID (defaults to env var)
            auth_token: Twilio auth token (defaults to env var)
        """
        self.account_sid = account_sid or os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = auth_token or os.getenv('TWILIO_AUTH_TOKEN')
        self.from_number = os.getenv('TWILIO_WHATSAPP_FROM', 'whatsapp:+14155238886')
        
        # Validate credentials
        if not self.account_sid or not self.auth_token:
            raise ValueError("Twilio credentials not found. Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN")
        
        # Validate WhatsApp from number format
        self._validate_from_number()
        
        self.client = Client(self.account_sid, self.auth_token)
        
        # Rate limiting - Twilio WhatsApp has specific limits
        self.messages_per_second = 1  # Conservative rate limit
        self.last_send_time = 0
        
        logger.info(f"WhatsApp sender initialized with from_number: {self.from_number}")
    
    def send_message(self, to_number: str, template: NotificationTemplate) -> NotificationResult:
        """
        Send a WhatsApp message to a single recipient.
        
        Args:
            to_number: Recipient phone number in WhatsApp format (whatsapp:+1234567890)
            template: Message template with content
            
        Returns:
            NotificationResult with delivery status
        """
        # Ensure proper WhatsApp format
        if not to_number.startswith('whatsapp:'):
            to_number = f"whatsapp:{to_number}"
        
        # Rate limiting
        self._apply_rate_limit()
        
        try:
            logger.info(f"Sending WhatsApp message to {to_number}")
            
            # Send message via Twilio
            message = self.client.messages.create(
                body=template.text_content,
                from_=self.from_number,
                to=to_number
            )
            
            logger.info(f"WhatsApp message sent successfully: {message.sid}")
            
            return NotificationResult(
                channel=NotificationChannel.WHATSAPP,
                status=NotificationStatus.SENT,
                recipient=to_number,
                message_id=message.sid,
                sent_at=datetime.now()
            )
            
        except TwilioRestException as e:
            error_msg = f"Twilio error: {e.msg} (Code: {e.code})"
            
            # Add specific guidance for common errors
            if e.code == 63007:
                error_msg += ". This usually means the 'from' number is not WhatsApp-enabled. " \
                           "Check that TWILIO_WHATSAPP_FROM is set correctly with 'whatsapp:' prefix " \
                           "and that the number is registered for WhatsApp in your Twilio console."
            elif e.code == 63016:
                error_msg += ". The recipient number may not be registered for WhatsApp or " \
                           "your Twilio number is not approved for sending to this recipient."
            
            logger.error(f"Failed to send WhatsApp message to {to_number}: {error_msg}")
            
            # Determine if error is retryable
            retryable_codes = [20429, 21610, 21611, 30007]  # Rate limit, queue full, etc.
            status = NotificationStatus.RETRYING if e.code in retryable_codes else NotificationStatus.FAILED
            
            return NotificationResult(
                channel=NotificationChannel.WHATSAPP,
                status=status,
                recipient=to_number,
                error_message=error_msg
            )
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Failed to send WhatsApp message to {to_number}: {error_msg}")
            
            return NotificationResult(
                channel=NotificationChannel.WHATSAPP,
                status=NotificationStatus.FAILED,
                recipient=to_number,
                error_message=error_msg
            )
    
    def send_bulk_messages(self, recipients: List[str], template: NotificationTemplate) -> List[NotificationResult]:
        """
        Send WhatsApp messages to multiple recipients.
        
        Args:
            recipients: List of phone numbers in WhatsApp format
            template: Message template with content
            
        Returns:
            List of NotificationResult objects
        """
        results = []
        
        logger.info(f"Sending WhatsApp messages to {len(recipients)} recipients")
        
        for recipient in recipients:
            result = self.send_message(recipient, template)
            results.append(result)
            
            # Small delay between messages to respect rate limits
            time.sleep(0.1)
        
        success_count = sum(1 for r in results if r.is_success)
        logger.info(f"WhatsApp bulk send completed: {success_count}/{len(recipients)} successful")
        
        return results
    
    def check_delivery_status(self, message_id: str) -> NotificationStatus:
        """
        Check the delivery status of a sent message.
        
        Args:
            message_id: Twilio message SID
            
        Returns:
            Updated notification status
        """
        try:
            message = self.client.messages(message_id).fetch()
            
            # Map Twilio status to our status
            status_mapping = {
                'queued': NotificationStatus.PENDING,
                'sending': NotificationStatus.PENDING,
                'sent': NotificationStatus.SENT,
                'delivered': NotificationStatus.DELIVERED,
                'undelivered': NotificationStatus.FAILED,
                'failed': NotificationStatus.FAILED
            }
            
            return status_mapping.get(message.status, NotificationStatus.PENDING)
            
        except TwilioRestException as e:
            logger.error(f"Error checking message status {message_id}: {e.msg}")
            return NotificationStatus.FAILED
        
        except Exception as e:
            logger.error(f"Unexpected error checking message status {message_id}: {str(e)}")
            return NotificationStatus.FAILED
    
    def get_message_details(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a sent message.
        
        Args:
            message_id: Twilio message SID
            
        Returns:
            Dictionary with message details or None if error
        """
        try:
            message = self.client.messages(message_id).fetch()
            
            return {
                'sid': message.sid,
                'status': message.status,
                'direction': message.direction,
                'from': message.from_,
                'to': message.to,
                'body': message.body,
                'date_created': message.date_created,
                'date_updated': message.date_updated,
                'date_sent': message.date_sent,
                'price': message.price,
                'price_unit': message.price_unit,
                'error_code': message.error_code,
                'error_message': message.error_message
            }
            
        except Exception as e:
            logger.error(f"Error fetching message details {message_id}: {str(e)}")
            return None
    
    def validate_phone_number(self, phone_number: str) -> bool:
        """
        Validate a phone number for WhatsApp delivery.
        
        Args:
            phone_number: Phone number to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Remove whatsapp: prefix if present
            clean_number = phone_number.replace('whatsapp:', '')
            
            # Use Twilio lookup to validate
            from twilio.rest.lookups.v1.phone_number import PhoneNumberInstance
            
            lookup = self.client.lookups.v1.phone_numbers(clean_number).fetch()
            return lookup.phone_number is not None
            
        except Exception as e:
            logger.warning(f"Could not validate phone number {phone_number}: {str(e)}")
            return False
    
    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """
        Get Twilio account information for monitoring.
        
        Returns:
            Dictionary with account details or None if error
        """
        try:
            account = self.client.api.accounts(self.account_sid).fetch()
            
            return {
                'account_sid': account.sid,
                'friendly_name': account.friendly_name,
                'status': account.status,
                'type': account.type,
                'date_created': account.date_created,
                'date_updated': account.date_updated
            }
            
        except Exception as e:
            logger.error(f"Error fetching account info: {str(e)}")
            return None
    
    def _apply_rate_limit(self):
        """Apply rate limiting between message sends."""
        current_time = time.time()
        time_since_last = current_time - self.last_send_time
        
        if time_since_last < (1.0 / self.messages_per_second):
            sleep_time = (1.0 / self.messages_per_second) - time_since_last
            time.sleep(sleep_time)
        
        self.last_send_time = time.time()
    
    def _validate_from_number(self):
        """
        Validate the WhatsApp from number configuration.
        
        Raises:
            ValueError: If the from number is not properly formatted
        """
        if not self.from_number:
            raise ValueError(
                "TWILIO_WHATSAPP_FROM not configured. Set this to your WhatsApp-enabled "
                "Twilio number with 'whatsapp:' prefix (e.g., 'whatsapp:+1234567890')"
            )
        
        if not self.from_number.startswith('whatsapp:'):
            raise ValueError(
                f"TWILIO_WHATSAPP_FROM must start with 'whatsapp:' prefix. "
                f"Current value: '{self.from_number}'. "
                f"Use format: 'whatsapp:+1234567890'"
            )
        
        # Extract phone number part and validate basic format
        phone_part = self.from_number.replace('whatsapp:', '')
        if not phone_part.startswith('+') or len(phone_part) < 10:
            raise ValueError(
                f"Invalid WhatsApp number format: '{self.from_number}'. "
                f"Use format: 'whatsapp:+1234567890'"
            )
        
        logger.info(f"WhatsApp from number validated: {self.from_number}")
    
    def format_phone_number(self, phone_number: str) -> str:
        """
        Format phone number for WhatsApp.
        
        Args:
            phone_number: Raw phone number
            
        Returns:
            Properly formatted WhatsApp number
        """
        # Remove all non-numeric characters except +
        import re
        clean_number = re.sub(r'[^\d+]', '', phone_number)
        
        # Add + if not present
        if not clean_number.startswith('+'):
            if clean_number.startswith('1') and len(clean_number) == 11:
                clean_number = '+' + clean_number
            else:
                clean_number = '+1' + clean_number
        
        return f"whatsapp:{clean_number}"
    
    def is_whatsapp_enabled(self) -> bool:
        """
        Check if WhatsApp notifications are enabled.
        
        Returns:
            True if enabled, False otherwise
        """
        return (
            os.getenv('WHATSAPP_ENABLED', 'true').lower() == 'true' and
            bool(self.account_sid) and
            bool(self.auth_token)
        )
    
    @staticmethod
    def parse_recipient_list(recipients_str: str) -> List[str]:
        """
        Parse comma-separated list of recipients.
        
        Args:
            recipients_str: Comma-separated phone numbers
            
        Returns:
            List of formatted phone numbers
        """
        if not recipients_str:
            return []
        
        sender = WhatsAppSender()
        recipients = []
        
        for recipient in recipients_str.split(','):
            recipient = recipient.strip()
            if recipient:
                formatted = sender.format_phone_number(recipient)
                recipients.append(formatted)
        
        return recipients