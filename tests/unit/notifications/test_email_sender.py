"""
Unit tests for email sender using Mailgun.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from src.notifications.email_sender import EmailSender
from src.notifications.models import NotificationTemplate, NotificationChannel, NotificationStatus


@pytest.fixture
def mock_mailgun_response():
    """Mock successful Mailgun response."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'id': '<test_message_id@mailgun.example.com>'}
    return mock_response


@pytest.fixture
def email_sender():
    """Create email sender with mock credentials."""
    with patch.dict('os.environ', {
        'MAILGUN_API_KEY': 'test_api_key',
        'MAILGUN_DOMAIN': 'test.mailgun.com',
        'EMAIL_FROM': 'pmcc-scanner@test.mailgun.com'
    }):
        return EmailSender()


@pytest.fixture
def sample_template():
    """Sample email template."""
    return NotificationTemplate(
        subject="PMCC Opportunity Alert: AAPL",
        text_content="PMCC opportunity found for AAPL at $155.00",
        html_content="<h1>PMCC Opportunity</h1><p>AAPL at $155.00</p>"
    )


class TestEmailSender:
    """Test email sender functionality with Mailgun."""
    
    def test_initialization_success(self):
        """Test successful initialization."""
        with patch.dict('os.environ', {
            'MAILGUN_API_KEY': 'test_key',
            'MAILGUN_DOMAIN': 'test.mailgun.com',
            'EMAIL_FROM': 'test@test.mailgun.com'
        }):
            sender = EmailSender()
            assert sender.api_key == 'test_key'
            assert sender.domain == 'test.mailgun.com'
            assert sender.from_email == 'test@test.mailgun.com'
            assert sender.base_url == 'https://api.mailgun.net/v3/test.mailgun.com/messages'
            assert sender.auth == ('api', 'test_key')
    
    def test_initialization_missing_api_key(self):
        """Test initialization fails with missing API key."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="Mailgun API key not found"):
                EmailSender()
    
    def test_initialization_missing_domain(self):
        """Test initialization fails with missing domain."""
        with patch.dict('os.environ', {
            'MAILGUN_API_KEY': 'test_key'
        }, clear=True):
            with pytest.raises(ValueError, match="Mailgun domain not found"):
                EmailSender()
    
    @patch('requests.post')
    def test_send_email_success(self, mock_post, email_sender, sample_template, mock_mailgun_response):
        """Test successful email sending."""
        mock_post.return_value = mock_mailgun_response
        
        result = email_sender.send_email("test@example.com", sample_template)
        
        assert result.channel == NotificationChannel.EMAIL
        assert result.status == NotificationStatus.SENT
        assert result.recipient == "test@example.com"
        assert result.message_id == "<test_message_id@mailgun.example.com>"
        assert result.sent_at is not None
        
        # Verify Mailgun API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == email_sender.base_url
        assert call_args[1]['auth'] == ('api', 'test_api_key')
        assert call_args[1]['data']['to'] == 'test@example.com'
        assert call_args[1]['data']['subject'] == 'PMCC Opportunity Alert: AAPL'
        assert call_args[1]['data']['text'] == 'PMCC opportunity found for AAPL at $155.00'
        assert call_args[1]['data']['html'] == '<h1>PMCC Opportunity</h1><p>AAPL at $155.00</p>'
    
    @patch('requests.post')
    def test_send_email_http_error_retryable(self, mock_post, email_sender, sample_template):
        """Test handling of retryable HTTP errors."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {'message': 'Rate limit exceeded'}
        mock_response.text = 'Rate limit exceeded'
        mock_post.return_value = mock_response
        
        result = email_sender.send_email("test@example.com", sample_template)
        
        assert result.channel == NotificationChannel.EMAIL
        assert result.status == NotificationStatus.RETRYING
        assert result.recipient == "test@example.com"
        assert "429" in result.error_message
        assert "Rate limit exceeded" in result.error_message
    
    @patch('requests.post')
    def test_send_email_http_error_permanent(self, mock_post, email_sender, sample_template):
        """Test handling of permanent HTTP errors."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {'message': 'Invalid email address'}
        mock_response.text = 'Invalid email address'
        mock_post.return_value = mock_response
        
        result = email_sender.send_email("test@example.com", sample_template)
        
        assert result.status == NotificationStatus.FAILED
        assert "400" in result.error_message
        assert "Invalid email address" in result.error_message
    
    @patch('requests.post')
    def test_send_email_request_exception(self, mock_post, email_sender, sample_template):
        """Test handling of request exceptions."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Network error")
        
        result = email_sender.send_email("test@example.com", sample_template)
        
        assert result.status == NotificationStatus.RETRYING
        assert "Network error" in result.error_message
    
    @patch('requests.post')
    def test_send_email_unexpected_error(self, mock_post, email_sender, sample_template):
        """Test handling of unexpected errors."""
        mock_post.side_effect = Exception("Unexpected error")
        
        result = email_sender.send_email("test@example.com", sample_template)
        
        assert result.status == NotificationStatus.FAILED
        assert "Unexpected error" in result.error_message
    
    @patch('requests.post')
    def test_send_bulk_emails_single_recipient(self, mock_post, email_sender, sample_template, mock_mailgun_response):
        """Test bulk email with single recipient falls back to single send."""
        mock_post.return_value = mock_mailgun_response
        
        recipients = ["test@example.com"]
        results = email_sender.send_bulk_emails(recipients, sample_template)
        
        assert len(results) == 1
        assert results[0].is_success
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_send_bulk_emails_multiple_recipients(self, mock_post, email_sender, sample_template, mock_mailgun_response):
        """Test bulk email with multiple recipients."""
        mock_post.return_value = mock_mailgun_response
        
        recipients = ["test1@example.com", "test2@example.com", "test3@example.com"]
        results = email_sender.send_bulk_emails(recipients, sample_template)
        
        assert len(results) == 3
        assert all(r.is_success for r in results)
        mock_post.assert_called_once()
        
        # Verify bulk API call
        call_args = mock_post.call_args
        assert call_args[1]['data']['to'] == recipients
    
    @patch('requests.post')
    def test_send_bulk_emails_error(self, mock_post, email_sender, sample_template):
        """Test bulk email error handling."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {'message': 'Server error'}
        mock_response.text = 'Server error'
        mock_post.return_value = mock_response
        
        recipients = ["test1@example.com", "test2@example.com"]
        results = email_sender.send_bulk_emails(recipients, sample_template)
        
        assert len(results) == 2
        assert all(r.status == NotificationStatus.RETRYING for r in results)
        assert all("Server error" in r.error_message for r in results)
    
    def test_validate_email_valid(self, email_sender):
        """Test email validation with valid addresses."""
        valid_emails = [
            "test@example.com",
            "user.name+tag@domain.co.uk",
            "123@test-domain.org"
        ]
        
        for email in valid_emails:
            assert email_sender.validate_email(email) is True
    
    def test_validate_email_invalid(self, email_sender):
        """Test email validation with invalid addresses."""
        invalid_emails = [
            "invalid_email",
            "@domain.com",
            "test@",
            "test.domain.com",
            ""
        ]
        
        for email in invalid_emails:
            assert email_sender.validate_email(email) is False
    
    def test_parse_recipient_list(self):
        """Test parsing recipient list."""
        recipients_str = "test1@example.com, test2@example.com , invalid_email, test3@domain.org"
        
        with patch.dict('os.environ', {
            'MAILGUN_API_KEY': 'test_key',
            'MAILGUN_DOMAIN': 'test.mailgun.com'
        }):
            recipients = EmailSender.parse_recipient_list(recipients_str)
        
        assert len(recipients) == 3
        assert "test1@example.com" in recipients
        assert "test2@example.com" in recipients
        assert "test3@domain.org" in recipients
        assert "invalid_email" not in recipients
    
    def test_parse_recipient_list_empty(self):
        """Test parsing empty recipient list."""
        with patch.dict('os.environ', {
            'MAILGUN_API_KEY': 'test_key',
            'MAILGUN_DOMAIN': 'test.mailgun.com'
        }):
            recipients = EmailSender.parse_recipient_list("")
        
        assert recipients == []
    
    def test_create_html_template(self, email_sender):
        """Test HTML template creation."""
        opportunities = [
            {
                'symbol': 'AAPL',
                'underlying_price': 155.00,
                'net_debit': 22.25,
                'max_profit': 7.75,
                'total_score': 85,
                'long_call': {
                    'strike': 150.00,
                    'expiration': '2025-01-17'
                },
                'short_call': {
                    'strike': 160.00,
                    'expiration': '2024-12-20'
                }
            }
        ]
        
        html = email_sender.create_html_template(opportunities)
        
        assert "AAPL" in html
        assert "$155.00" in html
        assert "$22.25" in html
        assert "$7.75" in html
        assert "85/100" in html
        assert "DOCTYPE html" in html
    
    def test_is_email_enabled_true(self):
        """Test email enabled check when enabled."""
        with patch.dict('os.environ', {
            'EMAIL_ENABLED': 'true',
            'MAILGUN_API_KEY': 'test_key',
            'MAILGUN_DOMAIN': 'test.mailgun.com'
        }):
            sender = EmailSender()
            assert sender.is_email_enabled() is True
    
    def test_is_email_enabled_false(self):
        """Test email enabled check when disabled."""
        with patch.dict('os.environ', {
            'EMAIL_ENABLED': 'false',
            'MAILGUN_API_KEY': 'test_key',
            'MAILGUN_DOMAIN': 'test.mailgun.com'
        }):
            sender = EmailSender()
            assert sender.is_email_enabled() is False
    
    def test_is_email_enabled_missing_credentials(self):
        """Test email enabled check with missing credentials."""
        with patch.dict('os.environ', {
            'EMAIL_ENABLED': 'true'
        }, clear=True):
            try:
                sender = EmailSender()
                result = sender.is_email_enabled()
                assert result is False  # Should be False if no credentials
            except ValueError:
                # Expected if initialization fails
                pass
    
    @patch('time.sleep')
    @patch('time.time')
    @patch('requests.post')
    def test_rate_limiting(self, mock_post, mock_time, mock_sleep, email_sender, sample_template, mock_mailgun_response):
        """Test rate limiting functionality."""
        mock_post.return_value = mock_mailgun_response
        # Set up times: first call at 0.5s, second at 0.6s (0.1s apart, should trigger rate limit)
        mock_time.side_effect = [0.5, 0.5, 0.6, 0.6]  # time() is called twice per send_email
        
        # Initialize last_send_time to allow first email without rate limiting
        email_sender.last_send_time = 0.0
        
        # First email should not trigger rate limit (sufficient time has passed)
        email_sender.send_email("test@example.com", sample_template)
        mock_sleep.assert_not_called()
        
        # Second email should trigger rate limit (only 0.1s apart, needs 0.2s)
        email_sender.send_email("test@example.com", sample_template)
        mock_sleep.assert_called_once()
    
    @patch('requests.get')
    def test_get_account_info_success(self, mock_get, email_sender):
        """Test getting account information successfully."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'domain': {
                'name': 'test.mailgun.com',
                'state': 'active'
            },
            'receiving_dns_records': []
        }
        mock_get.return_value = mock_response
        
        account_info = email_sender.get_account_info()
        
        assert account_info is not None
        assert account_info["api_key_valid"] is True
        assert account_info["service"] == "Mailgun"
        assert account_info["domain"] == "test.mailgun.com"
        assert account_info["domain_verified"] is True
    
    @patch('requests.get')
    def test_get_account_info_error(self, mock_get, email_sender):
        """Test getting account information with error."""
        mock_get.side_effect = Exception("Connection error")
        
        account_info = email_sender.get_account_info()
        
        assert account_info is not None
        assert account_info["api_key_valid"] is True
        assert account_info["service"] == "Mailgun"
        assert "error" in account_info
    
    @patch('requests.get')
    def test_check_delivery_status_delivered(self, mock_get, email_sender):
        """Test delivery status check for delivered message."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'items': [
                {'event': 'delivered', 'timestamp': 1234567890}
            ]
        }
        mock_get.return_value = mock_response
        
        status = email_sender.check_delivery_status("test_message_id")
        assert status == NotificationStatus.DELIVERED
    
    @patch('requests.get')
    def test_check_delivery_status_failed(self, mock_get, email_sender):
        """Test delivery status check for failed message."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'items': [
                {'event': 'failed', 'timestamp': 1234567890}
            ]
        }
        mock_get.return_value = mock_response
        
        status = email_sender.check_delivery_status("test_message_id")
        assert status == NotificationStatus.FAILED
    
    @patch('requests.get')
    def test_check_delivery_status_accepted(self, mock_get, email_sender):
        """Test delivery status check for accepted message."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'items': [
                {'event': 'accepted', 'timestamp': 1234567890}
            ]
        }
        mock_get.return_value = mock_response
        
        status = email_sender.check_delivery_status("test_message_id")
        assert status == NotificationStatus.SENT
    
    @patch('requests.get')
    def test_check_delivery_status_no_message_id(self, mock_get, email_sender):
        """Test delivery status check with no message ID."""
        status = email_sender.check_delivery_status("")
        assert status == NotificationStatus.SENT
        mock_get.assert_not_called()
    
    @patch('requests.get')
    def test_check_delivery_status_api_error(self, mock_get, email_sender):
        """Test delivery status check with API error."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        
        status = email_sender.check_delivery_status("test_message_id")
        assert status == NotificationStatus.SENT  # Default fallback
    
    @patch('requests.get')
    def test_check_delivery_status_exception(self, mock_get, email_sender):
        """Test delivery status check with exception."""
        mock_get.side_effect = Exception("Network error")
        
        status = email_sender.check_delivery_status("test_message_id")
        assert status == NotificationStatus.SENT  # Default fallback
    
    def test_mailgun_specific_features(self, email_sender):
        """Test Mailgun-specific functionality."""
        # Test that Mailgun-specific configurations are set
        assert email_sender.base_url.startswith("https://api.mailgun.net/v3/")
        assert email_sender.auth[0] == 'api'
        assert email_sender.messages_per_second == 5  # Conservative rate limit
    
    @patch('requests.post')
    def test_mailgun_error_response_parsing(self, mock_post, email_sender, sample_template):
        """Test parsing of Mailgun-specific error responses."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            'message': 'Invalid domain'
        }
        mock_response.text = 'Bad Request'
        mock_post.return_value = mock_response
        
        result = email_sender.send_email("test@example.com", sample_template)
        
        assert result.status == NotificationStatus.FAILED
        assert "Invalid domain" in result.error_message
    
    @patch('requests.post')
    def test_mailgun_json_parsing_failure(self, mock_post, email_sender, sample_template):
        """Test handling when Mailgun response JSON parsing fails."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.text = 'Bad Request'
        mock_post.return_value = mock_response
        
        result = email_sender.send_email("test@example.com", sample_template)
        
        assert result.status == NotificationStatus.FAILED
        assert "Bad Request" in result.error_message
