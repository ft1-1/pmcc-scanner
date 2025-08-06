"""
Unit tests for WhatsApp sender.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.notifications.whatsapp_sender import WhatsAppSender
from src.notifications.models import NotificationTemplate, NotificationChannel, NotificationStatus
from twilio.base.exceptions import TwilioRestException


@pytest.fixture
def mock_twilio_client():
    """Mock Twilio client."""
    mock_client = Mock()
    mock_message = Mock()
    mock_message.sid = "test_message_id"
    mock_message.status = "queued"
    mock_client.messages.create.return_value = mock_message
    return mock_client


@pytest.fixture
def whatsapp_sender():
    """Create WhatsApp sender with mock credentials."""
    with patch.dict('os.environ', {
        'TWILIO_ACCOUNT_SID': 'test_sid',
        'TWILIO_AUTH_TOKEN': 'test_token',
        'TWILIO_WHATSAPP_FROM': 'whatsapp:+14155238886'
    }):
        with patch('src.notifications.whatsapp_sender.Client'):
            return WhatsAppSender()


@pytest.fixture
def sample_template():
    """Sample WhatsApp message template."""
    return NotificationTemplate(
        text_content="🎯 PMCC Opportunity: AAPL\nPrice: $155.00\nProfit: $7.75"
    )


class TestWhatsAppSender:
    """Test WhatsApp sender functionality."""
    
    def test_initialization_success(self):
        """Test successful initialization."""
        with patch.dict('os.environ', {
            'TWILIO_ACCOUNT_SID': 'test_sid',
            'TWILIO_AUTH_TOKEN': 'test_token'
        }):
            with patch('src.notifications.whatsapp_sender.Client') as mock_client:
                sender = WhatsAppSender()
                assert sender.account_sid == 'test_sid'
                assert sender.auth_token == 'test_token'
                mock_client.assert_called_once_with('test_sid', 'test_token')
    
    def test_initialization_missing_credentials(self):
        """Test initialization fails with missing credentials."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="Twilio credentials not found"):
                WhatsAppSender()
    
    def test_send_message_success(self, whatsapp_sender, sample_template, mock_twilio_client):
        """Test successful message sending."""
        whatsapp_sender.client = mock_twilio_client
        
        result = whatsapp_sender.send_message("whatsapp:+1234567890", sample_template)
        
        assert result.channel == NotificationChannel.WHATSAPP
        assert result.status == NotificationStatus.SENT
        assert result.recipient == "whatsapp:+1234567890"
        assert result.message_id == "test_message_id"
        assert result.sent_at is not None
        
        mock_twilio_client.messages.create.assert_called_once_with(
            body=sample_template.text_content,
            from_="whatsapp:+14155238886",
            to="whatsapp:+1234567890"
        )
    
    def test_send_message_auto_format_number(self, whatsapp_sender, sample_template, mock_twilio_client):
        """Test automatic formatting of phone number."""
        whatsapp_sender.client = mock_twilio_client
        
        result = whatsapp_sender.send_message("+1234567890", sample_template)
        
        assert result.recipient == "whatsapp:+1234567890"
        mock_twilio_client.messages.create.assert_called_once_with(
            body=sample_template.text_content,
            from_="whatsapp:+14155238886",
            to="whatsapp:+1234567890"
        )
    
    def test_send_message_twilio_error_retryable(self, whatsapp_sender, sample_template):
        """Test handling of retryable Twilio errors."""
        mock_client = Mock()
        twilio_error = TwilioRestException(
            status=429,
            uri="test_uri",
            msg="Rate limit exceeded"
        )
        twilio_error.code = 20429
        mock_client.messages.create.side_effect = twilio_error
        whatsapp_sender.client = mock_client
        
        result = whatsapp_sender.send_message("whatsapp:+1234567890", sample_template)
        
        assert result.channel == NotificationChannel.WHATSAPP
        assert result.status == NotificationStatus.RETRYING
        assert result.recipient == "whatsapp:+1234567890"
        assert "Rate limit exceeded" in result.error_message
    
    def test_send_message_twilio_error_permanent(self, whatsapp_sender, sample_template):
        """Test handling of permanent Twilio errors."""
        mock_client = Mock()
        twilio_error = TwilioRestException(
            status=400,
            uri="test_uri",
            msg="Invalid phone number"
        )
        twilio_error.code = 21211
        mock_client.messages.create.side_effect = twilio_error
        whatsapp_sender.client = mock_client
        
        result = whatsapp_sender.send_message("whatsapp:+1234567890", sample_template)
        
        assert result.channel == NotificationChannel.WHATSAPP
        assert result.status == NotificationStatus.FAILED
        assert "Invalid phone number" in result.error_message
    
    def test_send_message_unexpected_error(self, whatsapp_sender, sample_template):
        """Test handling of unexpected errors."""
        mock_client = Mock()
        mock_client.messages.create.side_effect = Exception("Network error")
        whatsapp_sender.client = mock_client
        
        result = whatsapp_sender.send_message("whatsapp:+1234567890", sample_template)
        
        assert result.status == NotificationStatus.FAILED
        assert "Network error" in result.error_message
    
    def test_send_bulk_messages(self, whatsapp_sender, sample_template):
        """Test sending bulk messages."""
        mock_client = Mock()
        mock_message = Mock()
        mock_message.sid = "test_message_id"
        mock_client.messages.create.return_value = mock_message
        whatsapp_sender.client = mock_client
        
        recipients = ["whatsapp:+1234567890", "whatsapp:+0987654321"]
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            results = whatsapp_sender.send_bulk_messages(recipients, sample_template)
        
        assert len(results) == 2
        assert all(r.is_success for r in results)
        assert mock_client.messages.create.call_count == 2
    
    def test_check_delivery_status_success(self, whatsapp_sender):
        """Test checking delivery status."""
        mock_client = Mock()
        mock_message = Mock()
        mock_message.status = "delivered"
        mock_client.messages.return_value.fetch.return_value = mock_message
        whatsapp_sender.client = mock_client
        
        status = whatsapp_sender.check_delivery_status("test_message_id")
        
        assert status == NotificationStatus.DELIVERED
        mock_client.messages.assert_called_once_with("test_message_id")
    
    def test_check_delivery_status_error(self, whatsapp_sender):
        """Test handling error when checking delivery status."""
        mock_client = Mock()
        twilio_error = TwilioRestException(
            status=404,
            uri="test_uri",
            msg="Message not found"
        )
        mock_client.messages.return_value.fetch.side_effect = twilio_error
        whatsapp_sender.client = mock_client
        
        status = whatsapp_sender.check_delivery_status("invalid_id")
        
        assert status == NotificationStatus.FAILED
    
    def test_get_message_details(self, whatsapp_sender):
        """Test getting message details."""
        mock_client = Mock()
        mock_message = Mock()
        mock_message.sid = "test_id"
        mock_message.status = "delivered"
        mock_message.direction = "outbound-api"
        mock_message.from_ = "whatsapp:+14155238886"
        mock_message.to = "whatsapp:+1234567890"
        mock_message.body = "Test message"
        mock_message.date_created = datetime.now()
        mock_message.date_updated = datetime.now()
        mock_message.date_sent = datetime.now()
        mock_message.price = "0.005"
        mock_message.price_unit = "USD"
        mock_message.error_code = None
        mock_message.error_message = None
        
        mock_client.messages.return_value.fetch.return_value = mock_message
        whatsapp_sender.client = mock_client
        
        details = whatsapp_sender.get_message_details("test_id")
        
        assert details is not None
        assert details["sid"] == "test_id"
        assert details["status"] == "delivered"
        assert details["from"] == "whatsapp:+14155238886"
    
    def test_validate_phone_number_valid(self, whatsapp_sender):
        """Test phone number validation with valid number."""
        mock_client = Mock()
        mock_lookup = Mock()
        mock_lookup.phone_number = "+1234567890"
        mock_client.lookups.v1.phone_numbers.return_value.fetch.return_value = mock_lookup
        whatsapp_sender.client = mock_client
        
        is_valid = whatsapp_sender.validate_phone_number("whatsapp:+1234567890")
        
        assert is_valid is True
    
    def test_validate_phone_number_invalid(self, whatsapp_sender):
        """Test phone number validation with invalid number."""
        mock_client = Mock()
        mock_client.lookups.v1.phone_numbers.return_value.fetch.side_effect = Exception("Invalid")
        whatsapp_sender.client = mock_client
        
        is_valid = whatsapp_sender.validate_phone_number("invalid_number")
        
        assert is_valid is False
    
    def test_format_phone_number(self, whatsapp_sender):
        """Test phone number formatting."""
        test_cases = [
            ("1234567890", "whatsapp:+11234567890"),
            ("+1234567890", "whatsapp:+1234567890"),
            ("(123) 456-7890", "whatsapp:+11234567890"),
            ("123-456-7890", "whatsapp:+11234567890")
        ]
        
        for input_number, expected in test_cases:
            result = whatsapp_sender.format_phone_number(input_number)
            assert result == expected
    
    def test_parse_recipient_list(self):
        """Test parsing recipient list."""
        recipients_str = "whatsapp:+1234567890, +0987654321, (555) 123-4567"
        
        with patch.dict('os.environ', {
            'TWILIO_ACCOUNT_SID': 'test_sid',
            'TWILIO_AUTH_TOKEN': 'test_token'
        }):
            recipients = WhatsAppSender.parse_recipient_list(recipients_str)
        
        assert len(recipients) == 3
        assert "whatsapp:+1234567890" in recipients
        assert "whatsapp:+0987654321" in recipients
        assert "whatsapp:+15551234567" in recipients
    
    def test_is_whatsapp_enabled_true(self):
        """Test WhatsApp enabled check when enabled."""
        with patch.dict('os.environ', {
            'WHATSAPP_ENABLED': 'true',
            'TWILIO_ACCOUNT_SID': 'test_sid',
            'TWILIO_AUTH_TOKEN': 'test_token'
        }):
            with patch('src.notifications.whatsapp_sender.Client'):
                sender = WhatsAppSender()
                assert sender.is_whatsapp_enabled() is True
    
    def test_is_whatsapp_enabled_false(self):
        """Test WhatsApp enabled check when disabled."""
        with patch.dict('os.environ', {
            'WHATSAPP_ENABLED': 'false',
            'TWILIO_ACCOUNT_SID': 'test_sid',
            'TWILIO_AUTH_TOKEN': 'test_token'
        }):
            with patch('src.notifications.whatsapp_sender.Client'):
                sender = WhatsAppSender()
                assert sender.is_whatsapp_enabled() is False
    
    def test_rate_limiting(self, whatsapp_sender, sample_template):
        """Test rate limiting functionality."""
        mock_client = Mock()
        mock_message = Mock()
        mock_message.sid = "test_id"
        mock_client.messages.create.return_value = mock_message
        whatsapp_sender.client = mock_client
        
        with patch('time.time', side_effect=[0, 0.5, 1.1, 1.6]) as mock_time, \
             patch('time.sleep') as mock_sleep:
            
            # First message should not trigger rate limit
            whatsapp_sender.send_message("whatsapp:+1234567890", sample_template)
            mock_sleep.assert_not_called()
            
            # Second message should trigger rate limit
            whatsapp_sender.send_message("whatsapp:+1234567890", sample_template)
            mock_sleep.assert_called_once()