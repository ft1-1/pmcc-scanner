"""
Unit tests for notification manager.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal

from src.notifications.notification_manager import NotificationManager
from src.notifications.models import (
    NotificationConfig, NotificationResult, NotificationChannel, 
    NotificationStatus, NotificationTemplate
)
from src.notifications.exceptions import ConfigurationError
from src.models.pmcc_models import PMCCCandidate, PMCCAnalysis, RiskMetrics
from src.models.api_models import OptionContract, StockQuote, OptionSide


@pytest.fixture
def mock_config():
    """Mock notification configuration."""
    return NotificationConfig(
        max_retries=2,
        retry_delay_seconds=1,
        enable_fallback=True,
        fallback_delay_seconds=2,
        whatsapp_enabled=True,
        email_enabled=True
    )


@pytest.fixture
def sample_pmcc_candidate():
    """Create a sample PMCC candidate for testing."""
    # Create mock option contracts
    long_call = OptionContract(
        option_symbol="AAPL250117C00150000",
        underlying_symbol="AAPL",
        strike=Decimal("150.00"),
        expiration=datetime(2025, 1, 17),
        side=OptionSide.CALL,
        bid=Decimal("25.50"),
        ask=Decimal("26.00"),
        delta=Decimal("0.80"),
        dte=90
    )
    
    short_call = OptionContract(
        option_symbol="AAPL241220C00160000",
        underlying_symbol="AAPL",
        strike=Decimal("160.00"),
        expiration=datetime(2024, 12, 20),
        side=OptionSide.CALL,
        bid=Decimal("3.50"),
        ask=Decimal("3.75"),
        delta=Decimal("0.30"),
        dte=30
    )
    
    underlying = StockQuote(
        symbol="AAPL",
        price=Decimal("155.00"),
        timestamp=datetime.now()
    )
    
    # Create analysis
    analysis = PMCCAnalysis(
        long_call=long_call,
        short_call=short_call,
        underlying=underlying,
        net_debit=Decimal("22.25"),
        risk_metrics=RiskMetrics(
            max_loss=Decimal("22.25"),
            max_profit=Decimal("7.75"),
            breakeven=Decimal("172.25")
        )
    )
    
    return PMCCCandidate(
        symbol="AAPL",
        underlying_price=Decimal("155.00"),
        analysis=analysis,
        liquidity_score=Decimal("85"),
        total_score=Decimal("82")
    )


class TestNotificationManager:
    """Test notification manager functionality."""
    
    @patch.dict('os.environ', {
        'TWILIO_ACCOUNT_SID': 'test_sid',
        'TWILIO_AUTH_TOKEN': 'test_token',
        'MAILGUN_API_KEY': 'test_key',
        'MAILGUN_DOMAIN': 'test.mailgun.com'
    })
    def test_initialization_success(self, mock_config):
        """Test successful initialization."""
        with patch('src.notifications.notification_manager.WhatsAppSender'), \
             patch('src.notifications.notification_manager.EmailSender'):
            manager = NotificationManager(mock_config)
            assert manager.config == mock_config
            assert manager.whatsapp_sender is not None
            assert manager.email_sender is not None
    
    def test_initialization_no_channels(self):
        """Test initialization fails when no channels available."""
        config = NotificationConfig(whatsapp_enabled=False, email_enabled=False)
        
        with pytest.raises(ConfigurationError):
            NotificationManager(config)
    
    @patch.dict('os.environ', {
        'WHATSAPP_TO_NUMBERS': 'whatsapp:+1234567890',
        'EMAIL_TO': 'test@example.com'
    })
    def test_send_pmcc_opportunity_success(self, mock_config, sample_pmcc_candidate):
        """Test sending PMCC opportunity notification."""
        # Mock senders
        mock_whatsapp = Mock()
        mock_email = Mock()
        
        mock_whatsapp.send_message.return_value = NotificationResult(
            channel=NotificationChannel.WHATSAPP,
            status=NotificationStatus.SENT,
            recipient="whatsapp:+1234567890"
        )
        
        mock_email.send_email.return_value = NotificationResult(
            channel=NotificationChannel.EMAIL,
            status=NotificationStatus.SENT,
            recipient="test@example.com"
        )
        
        with patch('src.notifications.notification_manager.WhatsAppSender', return_value=mock_whatsapp), \
             patch('src.notifications.notification_manager.EmailSender', return_value=mock_email):
            
            manager = NotificationManager(mock_config)
            results = manager.send_pmcc_opportunity(sample_pmcc_candidate)
            
            assert len(results) == 2
            assert all(r.is_success for r in results)
            mock_whatsapp.send_message.assert_called_once()
            mock_email.send_email.assert_called_once()
    
    @patch.dict('os.environ', {
        'WHATSAPP_TO_NUMBERS': 'whatsapp:+1234567890',
        'EMAIL_TO': 'test@example.com'
    })
    def test_send_pmcc_opportunity_whatsapp_fails_email_fallback(self, mock_config, sample_pmcc_candidate):
        """Test email fallback when WhatsApp fails."""
        # Mock WhatsApp to fail
        mock_whatsapp = Mock()
        mock_email = Mock()
        
        mock_whatsapp.send_message.return_value = NotificationResult(
            channel=NotificationChannel.WHATSAPP,
            status=NotificationStatus.FAILED,
            recipient="whatsapp:+1234567890",
            error_message="Network error"
        )
        
        mock_email.send_email.return_value = NotificationResult(
            channel=NotificationChannel.EMAIL,
            status=NotificationStatus.SENT,
            recipient="test@example.com"
        )
        
        with patch('src.notifications.notification_manager.WhatsAppSender', return_value=mock_whatsapp), \
             patch('src.notifications.notification_manager.EmailSender', return_value=mock_email), \
             patch('time.sleep'):  # Mock sleep to speed up test
            
            manager = NotificationManager(mock_config)
            results = manager.send_pmcc_opportunity(sample_pmcc_candidate)
            
            # Should have results from both channels
            assert len(results) == 2
            whatsapp_result = next(r for r in results if r.channel == NotificationChannel.WHATSAPP)
            email_result = next(r for r in results if r.channel == NotificationChannel.EMAIL)
            
            assert whatsapp_result.is_failure
            assert email_result.is_success
    
    def test_send_multiple_opportunities(self, mock_config, sample_pmcc_candidate):
        """Test sending multiple opportunities."""
        candidates = [sample_pmcc_candidate, sample_pmcc_candidate]
        
        mock_whatsapp = Mock()
        mock_email = Mock()
        
        mock_whatsapp.send_message.return_value = NotificationResult(
            channel=NotificationChannel.WHATSAPP,
            status=NotificationStatus.SENT,
            recipient="whatsapp:+1234567890"
        )
        
        mock_email.send_bulk_emails.return_value = [
            NotificationResult(
                channel=NotificationChannel.EMAIL,
                status=NotificationStatus.SENT,
                recipient="test@example.com"
            )
        ]
        
        with patch.dict('os.environ', {'WHATSAPP_TO_NUMBERS': 'whatsapp:+1234567890', 'EMAIL_TO': 'test@example.com'}), \
             patch('src.notifications.notification_manager.WhatsAppSender', return_value=mock_whatsapp), \
             patch('src.notifications.notification_manager.EmailSender', return_value=mock_email):
            
            manager = NotificationManager(mock_config)
            results = manager.send_multiple_opportunities(candidates)
            
            assert len(results) >= 1  # At least one result
            mock_whatsapp.send_message.assert_called_once()
            mock_email.send_bulk_emails.assert_called_once()
    
    def test_send_system_alert(self, mock_config):
        """Test sending system alert."""
        mock_email = Mock()
        mock_email.send_email.return_value = NotificationResult(
            channel=NotificationChannel.EMAIL,
            status=NotificationStatus.SENT,
            recipient="test@example.com"
        )
        
        with patch.dict('os.environ', {'EMAIL_TO': 'test@example.com'}), \
             patch('src.notifications.notification_manager.EmailSender', return_value=mock_email):
            
            manager = NotificationManager(mock_config)
            results = manager.send_system_alert("Test alert", "warning")
            
            assert len(results) == 1
            assert results[0].is_success
            mock_email.send_email.assert_called_once()
    
    def test_retry_logic(self, mock_config):
        """Test retry logic for failed notifications."""
        mock_whatsapp = Mock()
        
        # First attempt fails with retryable error, second succeeds
        mock_whatsapp.send_message.side_effect = [
            NotificationResult(
                channel=NotificationChannel.WHATSAPP,
                status=NotificationStatus.RETRYING,
                recipient="whatsapp:+1234567890",
                error_message="Rate limited"
            ),
            NotificationResult(
                channel=NotificationChannel.WHATSAPP,
                status=NotificationStatus.SENT,
                recipient="whatsapp:+1234567890"
            )
        ]
        
        with patch.dict('os.environ', {'WHATSAPP_TO_NUMBERS': 'whatsapp:+1234567890'}), \
             patch('src.notifications.notification_manager.WhatsAppSender', return_value=mock_whatsapp), \
             patch('time.sleep'):  # Mock sleep
            
            manager = NotificationManager(mock_config)
            template = NotificationTemplate(text_content="Test message")
            
            result = manager._send_single_with_retry(
                NotificationChannel.WHATSAPP, 
                "whatsapp:+1234567890", 
                template
            )
            
            assert result.is_success
            assert result.attempt_count == 2
            assert mock_whatsapp.send_message.call_count == 2
    
    def test_circuit_breaker_integration(self, mock_config):
        """Test circuit breaker prevents requests when open."""
        mock_whatsapp = Mock()
        
        with patch.dict('os.environ', {'WHATSAPP_TO_NUMBERS': 'whatsapp:+1234567890'}), \
             patch('src.notifications.notification_manager.WhatsAppSender', return_value=mock_whatsapp):
            
            manager = NotificationManager(mock_config)
            
            # Manually open circuit breaker
            manager.whatsapp_circuit.state = manager.whatsapp_circuit.CircuitState.OPEN
            
            template = NotificationTemplate(text_content="Test message")
            result = manager._send_single_with_retry(
                NotificationChannel.WHATSAPP,
                "whatsapp:+1234567890",
                template
            )
            
            assert result.is_failure
            assert "circuit breaker is open" in result.error_message
            mock_whatsapp.send_message.assert_not_called()
    
    def test_get_delivery_status(self, mock_config):
        """Test delivery status reporting."""
        with patch('src.notifications.notification_manager.WhatsAppSender'), \
             patch('src.notifications.notification_manager.EmailSender'):
            
            manager = NotificationManager(mock_config)
            
            # Add some mock results
            manager.delivery_history = [
                NotificationResult(
                    channel=NotificationChannel.WHATSAPP,
                    status=NotificationStatus.SENT,
                    recipient="whatsapp:+1234567890"
                ),
                NotificationResult(
                    channel=NotificationChannel.EMAIL,
                    status=NotificationStatus.FAILED,
                    recipient="test@example.com"
                )
            ]
            
            status = manager.get_delivery_status()
            
            assert status["total"] == 2
            assert status["successful"] == 1
            assert status["failed"] == 1
            assert status["success_rate"] == 0.5
            assert "whatsapp" in status["by_channel"]
            assert "email" in status["by_channel"]
    
    def test_test_connectivity(self, mock_config):
        """Test connectivity testing."""
        mock_whatsapp = Mock()
        mock_email = Mock()
        
        mock_whatsapp.get_account_info.return_value = {"status": "active"}
        mock_email.get_account_info.return_value = {"api_key_valid": True}
        
        with patch('src.notifications.notification_manager.WhatsAppSender', return_value=mock_whatsapp), \
             patch('src.notifications.notification_manager.EmailSender', return_value=mock_email):
            
            manager = NotificationManager(mock_config)
            connectivity = manager.test_connectivity()
            
            assert connectivity["whatsapp"] is True
            assert connectivity["email"] is True
    
    def test_cleanup_old_history(self, mock_config):
        """Test cleanup of old delivery history."""
        with patch('src.notifications.notification_manager.WhatsAppSender'), \
             patch('src.notifications.notification_manager.EmailSender'):
            
            manager = NotificationManager(mock_config)
            
            # Add old and new results
            old_time = datetime.now() - timedelta(days=10)
            new_time = datetime.now()
            
            manager.delivery_history = [
                NotificationResult(
                    channel=NotificationChannel.WHATSAPP,
                    status=NotificationStatus.SENT,
                    recipient="whatsapp:+1234567890",
                    sent_at=old_time
                ),
                NotificationResult(
                    channel=NotificationChannel.EMAIL,
                    status=NotificationStatus.SENT,
                    recipient="test@example.com",
                    sent_at=new_time
                )
            ]
            
            manager.cleanup_old_history(days=7)
            
            assert len(manager.delivery_history) == 1
            assert manager.delivery_history[0].sent_at == new_time
    
    @patch.dict('os.environ', {
        'NOTIFICATION_MAX_RETRIES': '5',
        'NOTIFICATION_RETRY_DELAY': '30',
        'WHATSAPP_ENABLED': 'true',
        'EMAIL_ENABLED': 'false'
    })
    def test_create_from_env(self):
        """Test creating manager from environment variables."""
        with patch('src.notifications.notification_manager.WhatsAppSender'):
            manager = NotificationManager.create_from_env()
            
            assert manager.config.max_retries == 5
            assert manager.config.retry_delay_seconds == 30
            assert manager.config.whatsapp_enabled is True
            assert manager.config.email_enabled is False