"""
Notification manager for coordinating multi-channel notifications.
"""

import os
import logging
import asyncio
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import time

from src.models.pmcc_models import PMCCCandidate
from src.notifications.models import (
    NotificationResult, NotificationChannel, NotificationStatus, 
    NotificationConfig, NotificationRequest, NotificationTemplate
)
from src.notifications.whatsapp_sender import WhatsAppSender
from src.notifications.email_sender import EmailSender
from src.notifications.formatters import WhatsAppFormatter, EmailFormatter
from src.notifications.circuit_breaker import CircuitBreaker
from src.notifications.exceptions import NotificationError, ConfigurationError, ChannelError


logger = logging.getLogger(__name__)


class NotificationManager:
    """
    Main notification manager that coordinates multi-channel notifications
    with retry logic, fallback mechanisms, and delivery tracking.
    """
    
    def __init__(self, config: Optional[NotificationConfig] = None):
        """
        Initialize notification manager.
        
        Args:
            config: Notification configuration settings
        """
        self.config = config or NotificationConfig()
        
        # Initialize senders
        self.whatsapp_sender = None
        self.email_sender = None
        
        # Initialize circuit breakers
        self.whatsapp_circuit = CircuitBreaker(
            name="whatsapp",
            failure_threshold=3,
            timeout_seconds=300  # 5 minutes
        )
        
        self.email_circuit = CircuitBreaker(
            name="email", 
            failure_threshold=5,
            timeout_seconds=180  # 3 minutes
        )
        
        try:
            if self.config.whatsapp_enabled:
                self.whatsapp_sender = WhatsAppSender()
                logger.info("WhatsApp sender initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize WhatsApp sender: {e}")
        
        try:
            if self.config.email_enabled:
                self.email_sender = EmailSender()
                logger.info("Email sender initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize email sender: {e}")
        
        if not self.whatsapp_sender and not self.email_sender:
            raise ConfigurationError("No notification channels available")
        
        # Delivery tracking
        self.delivery_history: List[NotificationResult] = []
        
        logger.info("Notification manager initialized")
    
    def send_pmcc_opportunity(self, candidate: PMCCCandidate) -> List[NotificationResult]:
        """
        Send notification about a single PMCC opportunity.
        
        Args:
            candidate: PMCC opportunity to notify about
            
        Returns:
            List of notification results from all channels
        """
        logger.info(f"Sending PMCC opportunity notification for {candidate.symbol}")
        
        results = []
        
        # Get recipients from environment
        whatsapp_recipients = self._get_whatsapp_recipients()
        email_recipients = self._get_email_recipients()
        
        # Send WhatsApp notifications (primary channel)
        if whatsapp_recipients and self.whatsapp_sender:
            whatsapp_template = WhatsAppFormatter.format_opportunity(candidate)
            whatsapp_results = self._send_with_retry(
                channel=NotificationChannel.WHATSAPP,
                recipients=whatsapp_recipients,
                template=whatsapp_template
            )
            results.extend(whatsapp_results)
        
        # Send email notifications (fallback or parallel)
        if email_recipients and self.email_sender:
            email_template = EmailFormatter.format_opportunity(candidate)
            
            # Check if WhatsApp failed and this is fallback
            whatsapp_failed = any(r.is_failure for r in results if r.channel == NotificationChannel.WHATSAPP)
            
            if not whatsapp_recipients or whatsapp_failed or not self.config.enable_fallback:
                # Send immediately
                email_results = self._send_with_retry(
                    channel=NotificationChannel.EMAIL,
                    recipients=email_recipients,
                    template=email_template
                )
                results.extend(email_results)
            else:
                # Schedule as fallback
                logger.info("Scheduling email as fallback after delay")
                time.sleep(self.config.fallback_delay_seconds)
                
                # Check WhatsApp delivery status
                whatsapp_delivered = any(
                    r.status in [NotificationStatus.SENT, NotificationStatus.DELIVERED] 
                    for r in results if r.channel == NotificationChannel.WHATSAPP
                )
                
                if not whatsapp_delivered:
                    email_results = self._send_with_retry(
                        channel=NotificationChannel.EMAIL,
                        recipients=email_recipients,
                        template=email_template
                    )
                    results.extend(email_results)
        
        # Store delivery history
        self.delivery_history.extend(results)
        
        # Log summary
        self._log_delivery_summary(results)
        
        return results
    
    def send_multiple_opportunities(
        self, 
        candidates: List[PMCCCandidate], 
        scan_metadata: Optional[Dict[str, Any]] = None
    ) -> List[NotificationResult]:
        """
        Send comprehensive daily summary notification with all PMCC opportunities.
        
        Args:
            candidates: List of all PMCC opportunities found
            scan_metadata: Optional metadata about the scan (duration, stocks screened, etc.)
            
        Returns:
            List of notification results from all channels
        """
        if not candidates:
            logger.info("No PMCC opportunities to notify about")
        else:
            logger.info(f"Sending daily summary notification for {len(candidates)} PMCC opportunities")
        
        results = []
        
        # Get recipients
        whatsapp_recipients = self._get_whatsapp_recipients()
        email_recipients = self._get_email_recipients()
        
        # Send WhatsApp summary (concise summary for urgent/mobile viewing)
        if whatsapp_recipients and self.whatsapp_sender:
            whatsapp_template = WhatsAppFormatter.format_multiple_opportunities(candidates)
            whatsapp_results = self._send_with_retry(
                channel=NotificationChannel.WHATSAPP,
                recipients=whatsapp_recipients,
                template=whatsapp_template
            )
            results.extend(whatsapp_results)
        
        # Send comprehensive daily email summary (contains ALL opportunities)
        if email_recipients and self.email_sender:
            email_template = EmailFormatter.format_daily_summary(candidates, scan_metadata)
            email_results = self._send_with_retry(
                channel=NotificationChannel.EMAIL,
                recipients=email_recipients,
                template=email_template
            )
            results.extend(email_results)
        
        # Store delivery history
        self.delivery_history.extend(results)
        
        # Log summary
        self._log_delivery_summary(results)
        
        return results
    
    def send_system_alert(self, message: str, severity: str = "info") -> List[NotificationResult]:
        """
        Send system alert notification.
        
        Args:
            message: Alert message
            severity: Alert severity (info, warning, error, critical)
            
        Returns:
            List of notification results
        """
        logger.info(f"Sending system alert: {severity} - {message}")
        
        # Create templates
        subject = f"PMCC Scanner Alert [{severity.upper()}]"
        
        whatsapp_content = f"🔔 *PMCC Scanner Alert*\n\nSeverity: {severity.upper()}\n\n{message}\n\nTime: {datetime.now().strftime('%I:%M %p')}"
        
        email_content = f"""
        PMCC Scanner System Alert
        
        Severity: {severity.upper()}
        Timestamp: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
        
        Message:
        {message}
        
        ---
        PMCC Scanner Monitoring System
        """
        
        whatsapp_template = NotificationTemplate(text_content=whatsapp_content)
        email_template = NotificationTemplate(
            subject=subject,
            text_content=email_content,
            html_content=f"<h3>PMCC Scanner Alert</h3><p><strong>Severity:</strong> {severity}</p><p>{message}</p>"
        )
        
        results = []
        
        # Send to appropriate channels based on severity
        if severity in ["error", "critical"]:
            # Send to all channels for critical alerts
            whatsapp_recipients = self._get_whatsapp_recipients()
            email_recipients = self._get_email_recipients()
            
            if whatsapp_recipients and self.whatsapp_sender:
                results.extend(self._send_with_retry(
                    channel=NotificationChannel.WHATSAPP,
                    recipients=whatsapp_recipients,
                    template=whatsapp_template
                ))
            
            if email_recipients and self.email_sender:
                results.extend(self._send_with_retry(
                    channel=NotificationChannel.EMAIL,
                    recipients=email_recipients,
                    template=email_template
                ))
        else:
            # Send to email only for info/warning
            email_recipients = self._get_email_recipients()
            if email_recipients and self.email_sender:
                results.extend(self._send_with_retry(
                    channel=NotificationChannel.EMAIL,
                    recipients=email_recipients,
                    template=email_template
                ))
        
        self.delivery_history.extend(results)
        return results
    
    def _send_with_retry(self, channel: NotificationChannel, recipients: List[str], 
                        template: NotificationTemplate) -> List[NotificationResult]:
        """
        Send notifications with retry logic.
        
        Args:
            channel: Notification channel
            recipients: List of recipients
            template: Message template
            
        Returns:
            List of notification results
        """
        all_results = []
        
        for recipient in recipients:
            result = self._send_single_with_retry(channel, recipient, template)
            all_results.append(result)
        
        return all_results
    
    def _send_single_with_retry(self, channel: NotificationChannel, recipient: str, 
                               template: NotificationTemplate) -> NotificationResult:
        """
        Send single notification with retry logic.
        
        Args:
            channel: Notification channel
            recipient: Single recipient
            template: Message template
            
        Returns:
            Final notification result
        """
        last_result = None
        
        for attempt in range(1, self.config.max_retries + 1):
            try:
                # Check circuit breaker before attempting
                if channel == NotificationChannel.WHATSAPP:
                    if not self.whatsapp_circuit.is_available():
                        return NotificationResult(
                            channel=channel,
                            status=NotificationStatus.FAILED,
                            recipient=recipient,
                            error_message="WhatsApp circuit breaker is open"
                        )
                    
                    if self.whatsapp_sender:
                        result = self.whatsapp_circuit.call(
                            self.whatsapp_sender.send_message, recipient, template
                        )
                    else:
                        return NotificationResult(
                            channel=channel,
                            status=NotificationStatus.FAILED,
                            recipient=recipient,
                            error_message="WhatsApp sender not available"
                        )
                        
                elif channel == NotificationChannel.EMAIL:
                    if not self.email_circuit.is_available():
                        return NotificationResult(
                            channel=channel,
                            status=NotificationStatus.FAILED,
                            recipient=recipient,
                            error_message="Email circuit breaker is open"
                        )
                    
                    if self.email_sender:
                        result = self.email_circuit.call(
                            self.email_sender.send_email, recipient, template
                        )
                    else:
                        return NotificationResult(
                            channel=channel,
                            status=NotificationStatus.FAILED,
                            recipient=recipient,
                            error_message="Email sender not available"
                        )
                else:
                    return NotificationResult(
                        channel=channel,
                        status=NotificationStatus.FAILED,
                        recipient=recipient,
                        error_message="Channel not available"
                    )
                
                result.attempt_count = attempt
                
                # Success or permanent failure
                if result.is_success or result.is_failure:
                    return result
                
                # Temporary failure - retry if more attempts available
                if attempt < self.config.max_retries:
                    logger.info(f"Retrying {channel.value} to {recipient} (attempt {attempt + 1})")
                    time.sleep(self.config.retry_delay_seconds)
                
                last_result = result
                
            except Exception as e:
                logger.error(f"Error sending {channel.value} to {recipient}: {str(e)}")
                last_result = NotificationResult(
                    channel=channel,
                    status=NotificationStatus.FAILED,
                    recipient=recipient,
                    error_message=str(e),
                    attempt_count=attempt
                )
        
        # All retries exhausted
        if last_result:
            last_result.status = NotificationStatus.FAILED
            return last_result
        
        return NotificationResult(
            channel=channel,
            status=NotificationStatus.FAILED,
            recipient=recipient,
            error_message="All retry attempts failed"
        )
    
    def get_delivery_status(self) -> Dict[str, Any]:
        """
        Get delivery status summary.
        
        Returns:
            Dictionary with delivery statistics
        """
        if not self.delivery_history:
            return {"total": 0, "successful": 0, "failed": 0, "pending": 0}
        
        total = len(self.delivery_history)
        successful = sum(1 for r in self.delivery_history if r.is_success)
        failed = sum(1 for r in self.delivery_history if r.is_failure)
        pending = total - successful - failed
        
        by_channel = {}
        for channel in NotificationChannel:
            channel_results = [r for r in self.delivery_history if r.channel == channel]
            if channel_results:
                by_channel[channel.value] = {
                    "total": len(channel_results),
                    "successful": sum(1 for r in channel_results if r.is_success),
                    "failed": sum(1 for r in channel_results if r.is_failure)
                }
        
        return {
            "total": total,
            "successful": successful,
            "failed": failed,
            "pending": pending,
            "success_rate": successful / total if total > 0 else 0,
            "by_channel": by_channel,
            "last_updated": datetime.now().isoformat()
        }
    
    def test_connectivity(self) -> Dict[str, bool]:
        """
        Test connectivity to all notification services.
        
        Returns:
            Dictionary with connectivity status for each service
        """
        results = {}
        
        # Test WhatsApp (Twilio)
        if self.whatsapp_sender:
            try:
                account_info = self.whatsapp_sender.get_account_info()
                results["whatsapp"] = account_info is not None
            except Exception as e:
                logger.error(f"WhatsApp connectivity test failed: {e}")
                results["whatsapp"] = False
        else:
            results["whatsapp"] = False
        
        # Test Email (SendGrid)
        if self.email_sender:
            try:
                account_info = self.email_sender.get_account_info()
                results["email"] = account_info is not None
            except Exception as e:
                logger.error(f"Email connectivity test failed: {e}")
                results["email"] = False
        else:
            results["email"] = False
        
        return results
    
    def _get_whatsapp_recipients(self) -> List[str]:
        """Get WhatsApp recipients from environment."""
        recipients_str = os.getenv('WHATSAPP_TO_NUMBERS', '')
        return WhatsAppSender.parse_recipient_list(recipients_str)
    
    def _get_email_recipients(self) -> List[str]:
        """Get email recipients from environment."""
        recipients_str = os.getenv('EMAIL_TO', '')
        return EmailSender.parse_recipient_list(recipients_str)
    
    def _log_delivery_summary(self, results: List[NotificationResult]):
        """Log summary of delivery results."""
        if not results:
            return
        
        by_channel = {}
        for result in results:
            channel = result.channel.value
            if channel not in by_channel:
                by_channel[channel] = {"sent": 0, "failed": 0}
            
            if result.is_success:
                by_channel[channel]["sent"] += 1
            else:
                by_channel[channel]["failed"] += 1
        
        for channel, stats in by_channel.items():
            logger.info(f"{channel.title()}: {stats['sent']} sent, {stats['failed']} failed")
    
    def cleanup_old_history(self, days: int = 7):
        """
        Clean up old delivery history.
        
        Args:
            days: Number of days to keep history
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        original_count = len(self.delivery_history)
        self.delivery_history = [
            r for r in self.delivery_history 
            if r.sent_at and r.sent_at > cutoff_date
        ]
        
        removed_count = original_count - len(self.delivery_history)
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old delivery records")
    
    def is_healthy(self) -> bool:
        """
        Check if notification system is healthy.
        
        Returns:
            True if at least one channel is available
        """
        connectivity = self.test_connectivity()
        return any(connectivity.values())
    
    @staticmethod
    def create_from_env() -> 'NotificationManager':
        """
        Create notification manager from environment variables.
        
        Returns:
            Configured NotificationManager instance
        """
        config = NotificationConfig(
            max_retries=int(os.getenv('NOTIFICATION_MAX_RETRIES', '3')),
            retry_delay_seconds=int(os.getenv('NOTIFICATION_RETRY_DELAY', '60')),
            enable_fallback=os.getenv('NOTIFICATION_ENABLE_FALLBACK', 'true').lower() == 'true',
            fallback_delay_seconds=int(os.getenv('NOTIFICATION_FALLBACK_DELAY', '300')),
            whatsapp_enabled=os.getenv('WHATSAPP_ENABLED', 'true').lower() == 'true',
            email_enabled=os.getenv('EMAIL_ENABLED', 'true').lower() == 'true'
        )
        
        return NotificationManager(config)