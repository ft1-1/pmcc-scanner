"""
Tests for NotificationManager daily summary functionality.
Tests the new daily email summary features and WhatsApp integration.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date
from decimal import Decimal
from typing import List

import sys
sys.path.append('src')

from src.notifications.notification_manager import NotificationManager
from src.notifications.models import NotificationConfig, NotificationResult, NotificationStatus, NotificationChannel
from src.models.pmcc_models import PMCCCandidate, PMCCAnalysis, RiskMetrics
from src.models.api_models import OptionContract


class TestNotificationManagerDailySummary:
    """Test cases for NotificationManager daily summary functionality."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock notification configuration."""
        config = NotificationConfig()
        config.whatsapp_enabled = True
        config.email_enabled = True
        config.whatsapp_recipients = ["whatsapp:+1234567890"]
        config.email_recipients = ["test@example.com"]
        return config
    
    @pytest.fixture
    def sample_pmcc_candidates(self):
        """Create sample PMCC candidates for testing."""
        candidates = []
        
        for i in range(3):
            long_call = OptionContract(
                symbol=f"STOCK{i}",
                option_symbol=f"STOCK{i}250117C00150000",
                strike=Decimal("150.00"),
                expiration=date(2025, 1, 17),
                option_type="call",
                bid=Decimal("8.50"),
                ask=Decimal("8.75"),
                last=Decimal("8.60"),
                volume=1250,
                open_interest=5000,
                delta=0.65
            )
            
            short_call = OptionContract(
                symbol=f"STOCK{i}",
                option_symbol=f"STOCK{i}241220C00160000",
                strike=Decimal("160.00"),
                expiration=date(2024, 12, 20),
                option_type="call",
                bid=Decimal("2.30"),
                ask=Decimal("2.45"),
                last=Decimal("2.35"),
                volume=800,
                open_interest=2500,
                delta=0.25
            )
            
            risk_metrics = RiskMetrics(
                max_profit=Decimal("625.00"),
                max_loss=Decimal("575.00"),
                breakeven=Decimal("156.25"),
                profit_probability=0.68
            )
            
            analysis = PMCCAnalysis(
                long_call=long_call,
                short_call=short_call,
                net_debit=Decimal("625.00"),
                strike_width=Decimal("10.00"),
                risk_metrics=risk_metrics,
                analyzed_at=datetime(2024, 8, 3, 14, 30, 0)
            )
            
            candidate = PMCCCandidate(
                symbol=f"STOCK{i}",
                underlying_price=Decimal(f"{155 + i}.00"),
                analysis=analysis,
                total_score=85.0 - (i * 2),  # Descending scores
                liquidity_score=85.0,
                risk_reward_ratio=1.09,
                discovered_at=datetime(2024, 8, 3, 14, 25, 0)
            )
            
            candidates.append(candidate)
        
        return candidates
    
    @pytest.fixture
    def notification_manager(self, mock_config):
        """Create notification manager with mocked dependencies."""
        manager = NotificationManager(mock_config)
        
        # Mock the senders
        manager.whatsapp_sender = Mock()
        manager.email_sender = Mock()
        
        # Mock successful sending
        manager.whatsapp_sender.send_message.return_value = NotificationResult(
            channel=NotificationChannel.WHATSAPP,
            recipient="whatsapp:+1234567890",
            status=NotificationStatus.SUCCESS,
            message_id="test_id"
        )
        
        manager.email_sender.send_email.return_value = NotificationResult(
            channel=NotificationChannel.EMAIL,
            recipient="test@example.com",
            status=NotificationStatus.SUCCESS,
            message_id="email_test_id"
        )
        
        return manager
    
    def test_send_multiple_opportunities_daily_summary(self, notification_manager, sample_pmcc_candidates):
        """Test that send_multiple_opportunities uses daily summary format for email."""
        scan_metadata = {
            'duration_seconds': 45.7,
            'stocks_screened': 1250,
            'stocks_passed_screening': 85,
            'scan_id': 'test-scan-123'
        }
        
        # Send notifications
        results = notification_manager.send_multiple_opportunities(
            sample_pmcc_candidates,
            scan_metadata=scan_metadata
        )
        
        # Verify that email sender was called
        assert notification_manager.email_sender.send_email.called
        
        # Get the email call arguments
        email_call = notification_manager.email_sender.send_email.call_args
        email_template = email_call[1]['template']  # Assuming template is keyword argument
        
        # Verify email template contains daily summary content
        assert "PMCC Daily Summary" in email_template.subject
        assert "3 Opportunities" in email_template.subject
        
        # Verify HTML content contains all opportunities
        assert "STOCK0" in email_template.html_content
        assert "STOCK1" in email_template.html_content
        assert "STOCK2" in email_template.html_content
        
        # Verify metadata is included
        assert "45.7s" in email_template.html_content or "45s" in email_template.html_content
        assert "1,250" in email_template.html_content or "1250" in email_template.html_content
        
        # Verify WhatsApp still gets summary format (not individual messages)
        assert notification_manager.whatsapp_sender.send_message.called
        whatsapp_call = notification_manager.whatsapp_sender.send_message.call_args
        whatsapp_template = whatsapp_call[1]['template']
        
        # WhatsApp should get summary, not individual opportunity format
        assert "opportunities found" in whatsapp_template.text_content.lower()
    
    def test_send_multiple_opportunities_no_opportunities(self, notification_manager):
        """Test daily summary with no opportunities found."""
        scan_metadata = {
            'duration_seconds': 32.1,
            'stocks_screened': 1500,
            'stocks_passed_screening': 95,
            'scan_id': 'test-scan-empty'
        }
        
        # Send notifications with empty list
        results = notification_manager.send_multiple_opportunities(
            [],
            scan_metadata=scan_metadata
        )
        
        # Verify email was still sent
        assert notification_manager.email_sender.send_email.called
        
        email_call = notification_manager.email_sender.send_email.call_args
        email_template = email_call[1]['template']
        
        # Verify subject reflects no opportunities
        assert "No Opportunities" in email_template.subject
        
        # Verify content shows scan was performed
        assert "1,500" in email_template.html_content or "1500" in email_template.html_content
        assert "0 opportunities" in email_template.html_content.lower()
    
    def test_send_multiple_opportunities_large_dataset(self, notification_manager):
        """Test daily summary with large number of opportunities (50+)."""
        # Create 52 opportunities
        large_candidates = []
        for i in range(52):
            candidate = PMCCCandidate(
                symbol=f"LARGE{i:02d}",
                underlying_price=Decimal(f"{100 + i}.50"),
                analysis=Mock(),  # Simplified for this test
                total_score=90.0 - (i * 0.5),
                liquidity_score=85.0,
                risk_reward_ratio=1.2
            )
            large_candidates.append(candidate)
        
        scan_metadata = {
            'duration_seconds': 185.3,
            'stocks_screened': 5000,
            'stocks_passed_screening': 450,
            'scan_id': 'test-scan-large'
        }
        
        # Send notifications
        results = notification_manager.send_multiple_opportunities(
            large_candidates,
            scan_metadata=scan_metadata
        )
        
        # Verify email was sent
        assert notification_manager.email_sender.send_email.called
        
        email_call = notification_manager.email_sender.send_email.call_args
        email_template = email_call[1]['template']
        
        # Verify subject shows correct count
        assert "52 Opportunities" in email_template.subject
        
        # Verify HTML contains all opportunities (not truncated)
        for i in range(52):
            assert f"LARGE{i:02d}" in email_template.html_content
        
        # Verify performance metadata
        assert "185.3s" in email_template.html_content or "3m 5s" in email_template.html_content
    
    def test_single_daily_email_not_multiple(self, notification_manager, sample_pmcc_candidates):
        """Test that only ONE email is sent for daily summary, not multiple individual emails."""
        scan_metadata = {
            'duration_seconds': 45.7,
            'stocks_screened': 1250,
            'stocks_passed_screening': 85,
            'scan_id': 'test-scan-123'
        }
        
        # Send notifications
        results = notification_manager.send_multiple_opportunities(
            sample_pmcc_candidates,
            scan_metadata=scan_metadata
        )
        
        # Verify email sender was called exactly ONCE
        assert notification_manager.email_sender.send_email.call_count == 1
        
        # Verify WhatsApp sender was called exactly ONCE
        assert notification_manager.whatsapp_sender.send_message.call_count == 1
        
        # Verify results contain expected number of notifications
        email_results = [r for r in results if r.channel == NotificationChannel.EMAIL]
        whatsapp_results = [r for r in results if r.channel == NotificationChannel.WHATSAPP]
        
        assert len(email_results) == 1  # One email per recipient
        assert len(whatsapp_results) == 1  # One WhatsApp per recipient
    
    def test_email_fallback_when_whatsapp_fails(self, notification_manager, sample_pmcc_candidates):
        """Test that email still works when WhatsApp fails."""
        # Mock WhatsApp failure
        notification_manager.whatsapp_sender.send_message.return_value = NotificationResult(
            channel=NotificationChannel.WHATSAPP,
            recipient="whatsapp:+1234567890",
            status=NotificationStatus.FAILED,
            error_message="WhatsApp API error"
        )
        
        scan_metadata = {
            'duration_seconds': 45.7,
            'stocks_screened': 1250,
            'stocks_passed_screening': 85,
            'scan_id': 'test-scan-123'
        }
        
        # Send notifications
        results = notification_manager.send_multiple_opportunities(
            sample_pmcc_candidates,
            scan_metadata=scan_metadata
        )
        
        # Verify both were attempted
        assert notification_manager.whatsapp_sender.send_message.called
        assert notification_manager.email_sender.send_email.called
        
        # Verify results show WhatsApp failure and email success
        whatsapp_results = [r for r in results if r.channel == NotificationChannel.WHATSAPP]
        email_results = [r for r in results if r.channel == NotificationChannel.EMAIL]
        
        assert len(whatsapp_results) == 1
        assert whatsapp_results[0].status == NotificationStatus.FAILED
        
        assert len(email_results) == 1
        assert email_results[0].status == NotificationStatus.SUCCESS
    
    def test_notification_delivery_tracking(self, notification_manager, sample_pmcc_candidates):
        """Test that notification delivery is properly tracked."""
        scan_metadata = {
            'duration_seconds': 45.7,
            'stocks_screened': 1250,
            'stocks_passed_screening': 85,
            'scan_id': 'test-scan-123'
        }
        
        # Send notifications
        results = notification_manager.send_multiple_opportunities(
            sample_pmcc_candidates,
            scan_metadata=scan_metadata
        )
        
        # Verify delivery history is updated
        assert len(notification_manager.delivery_history) > 0
        
        # Verify delivery status can be retrieved
        status = notification_manager.get_delivery_status()
        assert isinstance(status, dict)
        assert 'total_sent' in status
        assert 'successful_deliveries' in status
        assert 'failed_deliveries' in status
    
    def test_notification_configuration_validation(self, mock_config):
        """Test that notification manager validates configuration properly."""
        # Test with email disabled
        mock_config.email_enabled = False
        mock_config.whatsapp_enabled = True
        
        manager = NotificationManager(mock_config)
        manager.whatsapp_sender = Mock()
        manager.whatsapp_sender.send_message.return_value = NotificationResult(
            channel=NotificationChannel.WHATSAPP,
            recipient="whatsapp:+1234567890",
            status=NotificationStatus.SUCCESS,
            message_id="test_id"
        )
        
        candidates = [Mock()]  # Simplified candidate
        
        # Send notifications
        results = manager.send_multiple_opportunities(candidates, {})
        
        # Should only have WhatsApp results
        channels = [r.channel for r in results]
        assert NotificationChannel.WHATSAPP in channels
        assert NotificationChannel.EMAIL not in channels
    
    def test_notification_error_handling_and_logging(self, notification_manager, sample_pmcc_candidates):
        """Test error handling and logging for notification sending."""
        # Mock email sender to raise exception
        notification_manager.email_sender.send_email.side_effect = Exception("Email service unavailable")
        
        scan_metadata = {
            'duration_seconds': 45.7,
            'stocks_screened': 1250,
            'stocks_passed_screening': 85,
            'scan_id': 'test-scan-123'
        }
        
        # Send notifications (should handle errors gracefully)
        with patch('logging.Logger.error') as mock_logger:
            results = notification_manager.send_multiple_opportunities(
                sample_pmcc_candidates,
                scan_metadata=scan_metadata
            )
            
            # Verify error was logged
            assert mock_logger.called
        
        # WhatsApp should still work
        whatsapp_results = [r for r in results if r.channel == NotificationChannel.WHATSAPP]
        assert len(whatsapp_results) == 1
        assert whatsapp_results[0].status == NotificationStatus.SUCCESS
    
    def test_notification_retry_mechanism(self, notification_manager, sample_pmcc_candidates):
        """Test retry mechanism for failed notifications."""
        # Mock initial failure then success
        notification_manager.email_sender.send_email.side_effect = [
            Exception("Temporary failure"),
            NotificationResult(
                channel=NotificationChannel.EMAIL,
                recipient="test@example.com",
                status=NotificationStatus.SUCCESS,
                message_id="retry_success_id"
            )
        ]
        
        scan_metadata = {
            'duration_seconds': 45.7,
            'stocks_screened': 1250,
            'stocks_passed_screening': 85,
            'scan_id': 'test-scan-123'
        }
        
        # Send notifications
        results = notification_manager.send_multiple_opportunities(
            sample_pmcc_candidates,
            scan_metadata=scan_metadata
        )
        
        # Verify retry was attempted (email sender called multiple times)
        assert notification_manager.email_sender.send_email.call_count >= 2
        
        # Verify final result is success
        email_results = [r for r in results if r.channel == NotificationChannel.EMAIL]
        if email_results:  # If retry succeeded
            assert email_results[0].status == NotificationStatus.SUCCESS
