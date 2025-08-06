"""
Email notification sender using Mailgun API.
"""

import os
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import time

import requests

from src.notifications.models import NotificationResult, NotificationChannel, NotificationStatus, NotificationTemplate


logger = logging.getLogger(__name__)


class EmailSender:
    """
    Email sender using Mailgun API.
    
    Handles HTML and plain text email formatting, delivery tracking,
    and error handling for email notifications.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize email sender.
        
        Args:
            api_key: Mailgun API key (defaults to env var)
        """
        self.api_key = api_key or os.getenv('MAILGUN_API_KEY')
        self.domain = os.getenv('MAILGUN_DOMAIN')
        self.from_email = os.getenv('EMAIL_FROM', 'pmcc-scanner@example.com')
        
        if not self.api_key:
            raise ValueError("Mailgun API key not found. Set MAILGUN_API_KEY")
        if not self.domain:
            raise ValueError("Mailgun domain not found. Set MAILGUN_DOMAIN")
        
        # Mailgun API endpoint
        self.base_url = f"https://api.mailgun.net/v3/{self.domain}/messages"
        self.auth = ('api', self.api_key)
        
        # Rate limiting for Mailgun (300 emails/hour for free tier)
        self.messages_per_second = 5  # Conservative limit
        self.last_send_time = 0
        
        logger.info("Email sender initialized with Mailgun")
    
    def send_email(self, to_email: str, template: NotificationTemplate) -> NotificationResult:
        """
        Send an email to a single recipient.
        
        Args:
            to_email: Recipient email address
            template: Email template with subject, text, and HTML content
            
        Returns:
            NotificationResult with delivery status
        """
        # Rate limiting
        self._apply_rate_limit()
        
        try:
            logger.info(f"Sending email to {to_email}")
            
            # Prepare Mailgun data
            data = {
                'from': f"PMCC Scanner <{self.from_email}>",
                'to': to_email,
                'subject': template.subject or "PMCC Opportunity Alert",
                'text': template.text_content
            }
            
            # Add HTML content if available
            if template.html_content:
                data['html'] = template.html_content
            
            # Send email via Mailgun API
            response = requests.post(
                self.base_url,
                auth=self.auth,
                data=data,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Email sent successfully to {to_email}: Status {response.status_code}")
                
                # Extract message ID from Mailgun response
                message_id = None
                try:
                    response_data = response.json()
                    message_id = response_data.get('id')
                except:
                    pass
                
                return NotificationResult(
                    channel=NotificationChannel.EMAIL,
                    status=NotificationStatus.SENT,
                    recipient=to_email,
                    message_id=message_id,
                    sent_at=datetime.now()
                )
            else:
                # Handle Mailgun error response
                error_msg = f"Mailgun HTTP error: {response.status_code}"
                try:
                    error_data = response.json()
                    if 'message' in error_data:
                        error_msg += f" - {error_data['message']}"
                except:
                    error_msg += f" - {response.text}"
                
                logger.error(f"Failed to send email to {to_email}: {error_msg}")
                
                # Determine if error is retryable
                retryable_status_codes = [429, 500, 502, 503, 504]
                status = NotificationStatus.RETRYING if response.status_code in retryable_status_codes else NotificationStatus.FAILED
                
                return NotificationResult(
                    channel=NotificationChannel.EMAIL,
                    status=status,
                    recipient=to_email,
                    error_message=error_msg
                )
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Mailgun request error: {str(e)}"
            logger.error(f"Failed to send email to {to_email}: {error_msg}")
            
            return NotificationResult(
                channel=NotificationChannel.EMAIL,
                status=NotificationStatus.RETRYING,  # Network errors are typically retryable
                recipient=to_email,
                error_message=error_msg
            )
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Failed to send email to {to_email}: {error_msg}")
            
            return NotificationResult(
                channel=NotificationChannel.EMAIL,
                status=NotificationStatus.FAILED,
                recipient=to_email,
                error_message=error_msg
            )
    
    def send_bulk_emails(self, recipients: List[str], template: NotificationTemplate) -> List[NotificationResult]:
        """
        Send emails to multiple recipients.
        
        Args:
            recipients: List of email addresses
            template: Email template with content
            
        Returns:
            List of NotificationResult objects
        """
        if len(recipients) <= 1:
            # Use single send for one recipient
            return [self.send_email(recipients[0], template)] if recipients else []
        
        # Use Mailgun's multiple recipients feature for bulk sending
        return self._send_bulk_optimized(recipients, template)
    
    def _send_bulk_optimized(self, recipients: List[str], template: NotificationTemplate) -> List[NotificationResult]:
        """
        Send bulk emails using Mailgun's multiple recipients feature.
        
        Args:
            recipients: List of email addresses
            template: Email template with content
            
        Returns:
            List of NotificationResult objects
        """
        results = []
        
        try:
            logger.info(f"Sending bulk email to {len(recipients)} recipients")
            
            # Prepare Mailgun data with multiple recipients
            data = {
                'from': f"PMCC Scanner <{self.from_email}>",
                'to': recipients,  # Mailgun accepts list of recipients
                'subject': template.subject or "PMCC Opportunity Alert",
                'text': template.text_content
            }
            
            # Add HTML content if available
            if template.html_content:
                data['html'] = template.html_content
            
            # Send bulk email via Mailgun API
            response = requests.post(
                self.base_url,
                auth=self.auth,
                data=data,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Bulk email sent successfully: Status {response.status_code}")
                
                # Extract message ID from Mailgun response
                message_id = None
                try:
                    response_data = response.json()
                    message_id = response_data.get('id')
                except:
                    pass
                
                # Create success results for all recipients
                for recipient in recipients:
                    results.append(NotificationResult(
                        channel=NotificationChannel.EMAIL,
                        status=NotificationStatus.SENT,
                        recipient=recipient,
                        message_id=message_id,
                        sent_at=datetime.now()
                    ))
            else:
                # Handle Mailgun error response
                error_msg = f"Mailgun bulk HTTP error: {response.status_code}"
                try:
                    error_data = response.json()
                    if 'message' in error_data:
                        error_msg += f" - {error_data['message']}"
                except:
                    error_msg += f" - {response.text}"
                
                logger.error(f"Failed to send bulk email: {error_msg}")
                
                # Create failure results for all recipients
                retryable_status_codes = [429, 500, 502, 503, 504]
                status = NotificationStatus.RETRYING if response.status_code in retryable_status_codes else NotificationStatus.FAILED
                
                for recipient in recipients:
                    results.append(NotificationResult(
                        channel=NotificationChannel.EMAIL,
                        status=status,
                        recipient=recipient,
                        error_message=error_msg
                    ))
                    
        except requests.exceptions.RequestException as e:
            error_msg = f"Mailgun bulk request error: {str(e)}"
            logger.error(f"Failed to send bulk email: {error_msg}")
            
            # Create failure results for all recipients
            for recipient in recipients:
                results.append(NotificationResult(
                    channel=NotificationChannel.EMAIL,
                    status=NotificationStatus.RETRYING,  # Network errors are typically retryable
                    recipient=recipient,
                    error_message=error_msg
                ))
                
        except Exception as e:
            error_msg = f"Unexpected bulk email error: {str(e)}"
            logger.error(f"Failed to send bulk email: {error_msg}")
            
            # Create failure results for all recipients
            for recipient in recipients:
                results.append(NotificationResult(
                    channel=NotificationChannel.EMAIL,
                    status=NotificationStatus.FAILED,
                    recipient=recipient,
                    error_message=error_msg
                ))
        
        success_count = sum(1 for r in results if r.is_success)
        logger.info(f"Bulk email completed: {success_count}/{len(recipients)} successful")
        
        return results
    
    def validate_email(self, email: str) -> bool:
        """
        Validate an email address format.
        
        Args:
            email: Email address to validate
            
        Returns:
            True if valid format, False otherwise
        """
        import re
        
        # Basic email validation regex
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def check_delivery_status(self, message_id: str) -> NotificationStatus:
        """
        Check delivery status using Mailgun's Events API.
        
        Args:
            message_id: Mailgun message ID
            
        Returns:
            Current delivery status
        """
        if not message_id:
            return NotificationStatus.SENT
            
        try:
            # Mailgun Events API endpoint
            events_url = f"https://api.mailgun.net/v3/{self.domain}/events"
            
            # Query for events related to this message
            params = {
                'message-id': message_id,
                'limit': 10
            }
            
            response = requests.get(
                events_url,
                auth=self.auth,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                events_data = response.json()
                events = events_data.get('items', [])
                
                # Check latest event status
                for event in events:
                    event_type = event.get('event')
                    if event_type == 'delivered':
                        return NotificationStatus.DELIVERED
                    elif event_type in ['failed', 'rejected']:
                        return NotificationStatus.FAILED
                    elif event_type == 'accepted':
                        return NotificationStatus.SENT
                        
                # Default to sent if we have the message ID but no specific status
                return NotificationStatus.SENT
            else:
                logger.warning(f"Failed to check delivery status for {message_id}: {response.status_code}")
                return NotificationStatus.SENT
                
        except Exception as e:
            logger.error(f"Error checking delivery status for {message_id}: {str(e)}")
            return NotificationStatus.SENT
    
    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """
        Get Mailgun account information.
        
        Returns:
            Dictionary with account details or None if error
        """
        try:
            # Test Mailgun connection by checking domain info
            domain_url = f"https://api.mailgun.net/v3/domains/{self.domain}"
            
            response = requests.get(
                domain_url,
                auth=self.auth,
                timeout=10
            )
            
            domain_info = {}
            if response.status_code == 200:
                domain_data = response.json()
                domain_info = {
                    'domain_verified': domain_data.get('domain', {}).get('state') == 'active',
                    'domain_name': domain_data.get('domain', {}).get('name'),
                    'receiving_enabled': domain_data.get('receiving_dns_records') is not None
                }
            
            return {
                'api_key_valid': bool(self.api_key),
                'api_key_masked': f"{self.api_key[:4]}...{self.api_key[-4:]}" if self.api_key and len(self.api_key) > 8 else "***",
                'domain': self.domain,
                'from_email': self.from_email,
                'service': 'Mailgun',
                **domain_info
            }
            
        except Exception as e:
            logger.error(f"Error fetching account info: {str(e)}")
            return {
                'api_key_valid': bool(self.api_key),
                'api_key_masked': f"{self.api_key[:4]}...{self.api_key[-4:]}" if self.api_key and len(self.api_key) > 8 else "***",
                'domain': self.domain,
                'from_email': self.from_email,
                'service': 'Mailgun',
                'error': str(e)
            }
    
    def create_html_template(self, opportunities: List[Dict[str, Any]]) -> str:
        """
        Create a rich HTML template for multiple opportunities.
        
        Args:
            opportunities: List of opportunity dictionaries
            
        Returns:
            HTML content string
        """
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>PMCC Opportunities</title>
            <style>
                body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
                .container { max-width: 800px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                .header { text-align: center; margin-bottom: 30px; }
                .header h1 { color: #2E8B57; margin: 0; font-size: 28px; }
                .header p { color: #666; margin: 5px 0; }
                .opportunity { border: 1px solid #ddd; border-radius: 8px; margin: 20px 0; padding: 20px; background-color: #fafafa; }
                .opportunity h3 { color: #2E8B57; margin-top: 0; }
                .metrics { display: flex; flex-wrap: wrap; gap: 15px; margin: 15px 0; }
                .metric { background-color: white; padding: 10px; border-radius: 5px; text-align: center; min-width: 120px; }
                .metric .label { font-size: 12px; color: #666; text-transform: uppercase; }
                .metric .value { font-size: 18px; font-weight: bold; color: #333; }
                .positive { color: #28a745; }
                .warning { color: #ffc107; }
                .footer { margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; text-align: center; }
                @media (max-width: 600px) {
                    .metrics { flex-direction: column; }
                    .metric { min-width: auto; }
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎯 PMCC Opportunity Alert</h1>
                    <p>Daily scan results from PMCC Scanner</p>
                    <p>""" + datetime.now().strftime('%B %d, %Y at %I:%M %p') + """</p>
                </div>
        """
        
        # Add opportunities
        for i, opp in enumerate(opportunities, 1):
            html += f"""
                <div class="opportunity">
                    <h3>#{i}: {opp.get('symbol', 'N/A')} - ${opp.get('underlying_price', 0):.2f}</h3>
                    <div class="metrics">
                        <div class="metric">
                            <div class="label">Net Cost</div>
                            <div class="value">${opp.get('net_debit', 0):.2f}</div>
                        </div>
                        <div class="metric">
                            <div class="label">Max Profit</div>
                            <div class="value positive">${opp.get('max_profit', 0):.2f}</div>
                        </div>
                        <div class="metric">
                            <div class="label">Return %</div>
                            <div class="value positive">{(opp.get('max_profit', 0) / max(opp.get('net_debit', 1), 1) * 100):.1f}%</div>
                        </div>
                        <div class="metric">
                            <div class="label">Score</div>
                            <div class="value">{opp.get('total_score', 0):.0f}/100</div>
                        </div>
                    </div>
                    <p><strong>Long LEAPS:</strong> ${opp.get('long_call', {}).get('strike', 0):.2f} exp {opp.get('long_call', {}).get('expiration', 'N/A')}</p>
                    <p><strong>Short Call:</strong> ${opp.get('short_call', {}).get('strike', 0):.2f} exp {opp.get('short_call', {}).get('expiration', 'N/A')}</p>
                </div>
            """
        
        html += """
                <div class="footer">
                    <p><strong>Important:</strong> This analysis is for educational purposes only and should not be considered financial advice.</p>
                    <p>Always verify option liquidity and conduct your own due diligence before trading.</p>
                    <p>Generated by PMCC Scanner</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _apply_rate_limit(self):
        """Apply rate limiting between email sends."""
        current_time = time.time()
        time_since_last = current_time - self.last_send_time
        
        if time_since_last < (1.0 / self.messages_per_second):
            sleep_time = (1.0 / self.messages_per_second) - time_since_last
            time.sleep(sleep_time)
        
        self.last_send_time = time.time()
    
    def is_email_enabled(self) -> bool:
        """
        Check if email notifications are enabled.
        
        Returns:
            True if enabled, False otherwise
        """
        return (
            os.getenv('EMAIL_ENABLED', 'true').lower() == 'true' and
            bool(self.api_key) and
            bool(self.domain)
        )
    
    @staticmethod
    def parse_recipient_list(recipients_str: str) -> List[str]:
        """
        Parse comma-separated list of email recipients.
        
        Args:
            recipients_str: Comma-separated email addresses
            
        Returns:
            List of validated email addresses
        """
        if not recipients_str:
            return []
        
        sender = EmailSender()
        recipients = []
        
        for recipient in recipients_str.split(','):
            recipient = recipient.strip()
            if recipient and sender.validate_email(recipient):
                recipients.append(recipient)
            elif recipient:
                logger.warning(f"Invalid email address: {recipient}")
        
        return recipients