# PMCC Scanner Notification System

The notification system provides robust, multi-channel alerting for PMCC (Poor Man's Covered Call) trading opportunities. It supports WhatsApp and email notifications with automatic fallback, retry logic, and comprehensive error handling.

## Features

### Multi-Channel Support
- **WhatsApp** (Primary): Real-time alerts via Twilio WhatsApp Business API
- **Email** (Fallback): Detailed HTML and text notifications via Mailgun (or SendGrid for backward compatibility)
- **Automatic Fallback**: Email backup when WhatsApp fails

### Reliability Features
- **Circuit Breakers**: Prevent cascade failures when services are down
- **Retry Logic**: Configurable retry attempts with exponential backoff
- **Rate Limiting**: Respects API limits for both Twilio and email providers
- **Delivery Tracking**: Monitor message status and delivery confirmation

### Notification Types
- **Single Opportunity Alerts**: Detailed analysis of individual PMCC setups
- **Daily Summary Reports**: Digest of all opportunities found
- **System Alerts**: Monitoring notifications for application health

## Quick Start

### 1. Environment Configuration

Set up your environment variables:

```bash
# Twilio WhatsApp Configuration
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
WHATSAPP_TO_NUMBERS=whatsapp:+1234567890,whatsapp:+0987654321

# Mailgun Email Configuration (preferred)
MAILGUN_API_KEY=your_mailgun_api_key
MAILGUN_DOMAIN=your_mailgun_domain.com
EMAIL_FROM=pmcc-scanner@yourdomain.com
EMAIL_TO=user@example.com,another@example.com

# SendGrid Email Configuration (backward compatibility)
# SENDGRID_API_KEY=your_sendgrid_api_key

# Notification Settings
NOTIFICATION_ENABLED=true
WHATSAPP_ENABLED=true
EMAIL_ENABLED=true
```

### 2. Basic Usage

```python
from src.notifications import NotificationManager

# Create notification manager
manager = NotificationManager.create_from_env()

# Test connectivity
connectivity = manager.test_connectivity()
print(f"WhatsApp: {connectivity['whatsapp']}")
print(f"Email: {connectivity['email']}")

# Send PMCC opportunity alert
results = manager.send_pmcc_opportunity(pmcc_candidate)

# Check delivery status
status = manager.get_delivery_status()
print(f"Success rate: {status['success_rate']:.1%}")
```

### 3. Integration with Scanner

```python
from src.analysis.scanner import PMCCScanner
from src.notifications import NotificationManager

# Initialize components
scanner = PMCCScanner()
notifier = NotificationManager.create_from_env()

# Run daily scan
opportunities = scanner.scan_for_opportunities()

if opportunities:
    # Send notifications
    results = notifier.send_multiple_opportunities(opportunities)
    
    # Log results
    successful = sum(1 for r in results if r.is_success)
    print(f"Notifications sent: {successful}/{len(results)}")
else:
    # Send "no opportunities" notification
    notifier.send_system_alert("No PMCC opportunities found today", "info")
```

## Configuration Options

### NotificationConfig

```python
from src.notifications import NotificationConfig, NotificationManager

config = NotificationConfig(
    max_retries=3,                    # Maximum retry attempts
    retry_delay_seconds=60,           # Delay between retries
    enable_fallback=True,             # Enable email fallback
    fallback_delay_seconds=300,       # Delay before fallback (5 min)
    whatsapp_enabled=True,            # Enable WhatsApp notifications
    email_enabled=True                # Enable email notifications
)

manager = NotificationManager(config)
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NOTIFICATION_ENABLED` | Master notification toggle | `true` |
| `WHATSAPP_ENABLED` | Enable WhatsApp notifications | `true` |
| `EMAIL_ENABLED` | Enable email notifications | `true` |
| `NOTIFICATION_MAX_RETRIES` | Maximum retry attempts | `3` |
| `NOTIFICATION_RETRY_DELAY` | Retry delay in seconds | `60` |
| `NOTIFICATION_ENABLE_FALLBACK` | Enable fallback mechanism | `true` |
| `NOTIFICATION_FALLBACK_DELAY` | Fallback delay in seconds | `300` |

## Message Formats

### WhatsApp Format (Concise)

```
🎯 PMCC Opportunity: AAPL
💰 Current Price: $155.00

📈 Long LEAPS
Strike: $150.00
Exp: Jan 17, 2025
Cost: $26.00

📉 Short Call  
Strike: $160.00
Exp: Dec 20, 2024
Credit: $3.50

💳 Position Summary
Net Cost: $22.25
Max Profit: $7.75 (34.8%)
Max Loss: $22.25
Risk/Reward: 1:0.35

📊 Liquidity Score: 85/100

⏰ Scanned at 9:30 AM
```

### Email Format (Detailed)

Email notifications include:
- **HTML Format**: Rich formatting with tables, colors, and responsive design
- **Plain Text**: Fallback for email clients that don't support HTML
- **Comprehensive Analysis**: All option details, Greeks, risk metrics
- **Important Considerations**: Risk warnings and trading tips

## API Reference

### NotificationManager

#### Methods

**`send_pmcc_opportunity(candidate: PMCCCandidate) -> List[NotificationResult]`**
- Send notification for a single PMCC opportunity
- Returns results for all channels and recipients

**`send_multiple_opportunities(candidates: List[PMCCCandidate]) -> List[NotificationResult]`**
- Send summary notification for multiple opportunities
- Formats as digest with top opportunities highlighted

**`send_system_alert(message: str, severity: str = "info") -> List[NotificationResult]`**
- Send system alert notification
- Severity levels: `info`, `warning`, `error`, `critical`

**`test_connectivity() -> Dict[str, bool]`**
- Test connectivity to all notification services
- Returns status for each channel

**`get_delivery_status() -> Dict[str, Any]`**
- Get delivery statistics and success rates
- Includes per-channel breakdowns

**`is_healthy() -> bool`**
- Check if notification system is operational
- Returns True if at least one channel is available

### WhatsAppSender

#### Methods

**`send_message(to_number: str, template: NotificationTemplate) -> NotificationResult`**
- Send single WhatsApp message
- Handles phone number formatting automatically

**`send_bulk_messages(recipients: List[str], template: NotificationTemplate) -> List[NotificationResult]`**
- Send messages to multiple recipients
- Includes rate limiting between messages

**`check_delivery_status(message_id: str) -> NotificationStatus`**
- Check delivery status of sent message
- Uses Twilio's message status API

**`validate_phone_number(phone_number: str) -> bool`**
- Validate phone number using Twilio Lookup
- Checks if number can receive WhatsApp messages

### EmailSender

#### Methods

**`send_email(to_email: str, template: NotificationTemplate) -> NotificationResult`**
- Send single email message
- Supports both HTML and plain text content

**`send_bulk_emails(recipients: List[str], template: NotificationTemplate) -> List[NotificationResult]`**
- Send emails to multiple recipients
- Uses Mailgun's bulk sending optimization (or SendGrid for backward compatibility)

**`validate_email(email: str) -> bool`**
- Validate email address format
- Uses regex pattern matching

### Formatters

#### WhatsAppFormatter

**`format_opportunity(candidate: PMCCCandidate) -> NotificationTemplate`**
- Format single opportunity for WhatsApp
- Optimized for mobile reading

**`format_multiple_opportunities(candidates: List[PMCCCandidate], limit: int = 5) -> NotificationTemplate`**
- Format multiple opportunities summary
- Shows top opportunities by score

#### EmailFormatter

**`format_opportunity(candidate: PMCCCandidate) -> NotificationTemplate`**
- Format single opportunity for email
- Includes comprehensive HTML and text versions

**`format_multiple_opportunities(candidates: List[PMCCCandidate]) -> NotificationTemplate`**
- Format opportunities summary for email
- Includes data table and detailed metrics

## Error Handling

### Exception Types

- **`NotificationError`**: Base exception for notification issues
- **`ConfigurationError`**: Missing or invalid configuration
- **`ChannelError`**: Channel-specific errors (WhatsApp/Email)
- **`RateLimitError`**: API rate limit exceeded
- **`InvalidRecipientError`**: Invalid phone number or email
- **`DeliveryError`**: Message delivery failed

### Circuit Breaker

The system includes circuit breakers to prevent cascade failures:

- **Closed**: Normal operation, requests allowed
- **Open**: Service failing, requests blocked
- **Half-Open**: Testing service recovery

```python
# Check circuit breaker status
manager = NotificationManager.create_from_env()
print(f"WhatsApp available: {manager.whatsapp_circuit.is_available()}")
print(f"Email available: {manager.email_circuit.is_available()}")

# Get detailed status
whatsapp_status = manager.whatsapp_circuit.get_status()
print(f"State: {whatsapp_status['state']}")
print(f"Failures: {whatsapp_status['failure_count']}")
```

### Retry Logic

Automatic retry for transient failures:

1. **Retryable Errors**: Network timeouts, rate limits, temporary service issues
2. **Permanent Errors**: Invalid credentials, malformed requests, invalid recipients
3. **Exponential Backoff**: Increasing delays between retry attempts

## Monitoring and Logging

### Delivery Tracking

```python
# Get comprehensive delivery statistics
status = manager.get_delivery_status()

print(f"Total messages: {status['total']}")
print(f"Success rate: {status['success_rate']:.1%}")

# Per-channel statistics
for channel, stats in status['by_channel'].items():
    print(f"{channel}: {stats['successful']}/{stats['total']}")
```

### Health Monitoring

```python
# Check system health
if manager.is_healthy():
    print("Notification system operational")
else:
    print("Notification system degraded")
    
# Test individual services
connectivity = manager.test_connectivity()
if not connectivity['whatsapp']:
    print("WhatsApp service unavailable")
if not connectivity['email']:
    print("Email service unavailable")
```

### Log Integration

The system integrates with Python's logging framework:

```python
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('src.notifications')

# Notification events are automatically logged:
# INFO: WhatsApp message sent successfully: SM1234567890
# WARNING: Email delivery failed, retrying in 60 seconds
# ERROR: Circuit breaker 'whatsapp' opened due to failures
```

## Production Deployment

### Security Considerations

1. **API Keys**: Store credentials in environment variables, never in code
2. **Webhook Validation**: Implement HMAC signature verification for webhooks
3. **Rate Limiting**: Configure appropriate limits to avoid service throttling
4. **Access Control**: Restrict who can send notifications

### Performance Optimization

1. **Batch Processing**: Use bulk APIs when sending to multiple recipients
2. **Connection Pooling**: Reuse HTTP connections for better performance
3. **Async Processing**: Consider async workflows for high-volume scenarios
4. **Caching**: Cache templates and frequently used data

### Monitoring Setup

1. **Delivery Metrics**: Track success rates and delivery times
2. **Error Alerting**: Monitor for configuration issues and service outages
3. **Usage Analytics**: Track notification volume and patterns
4. **Cost Monitoring**: Monitor API usage costs for Twilio and email provider (Mailgun/SendGrid)

## Troubleshooting

### Common Issues

**WhatsApp Messages Not Sending**
- Verify Twilio credentials and WhatsApp sandbox approval
- Check phone number format (must include country code)
- Ensure WhatsApp Business API is enabled

**Email Delivery Issues**
- Verify Mailgun API key and domain configuration (or SendGrid for legacy setups)
- Check email addresses for typos
- Review email provider delivery logs for bounces/blocks

**Circuit Breaker Tripping**
- Check service connectivity and credentials
- Review error logs for root cause
- Reset circuit breaker: `manager.whatsapp_circuit.reset()`

**Rate Limit Errors**
- Reduce message frequency
- Implement longer delays between sends
- Upgrade to higher API tier if needed

### Debug Mode

Enable debug logging for troubleshooting:

```python
import logging
logging.getLogger('src.notifications').setLevel(logging.DEBUG)

# Detailed logs will show:
# - API request/response details
# - Retry attempts and delays
# - Circuit breaker state changes
# - Message formatting steps
```

## Examples

See `examples/notification_system_demo.py` for a comprehensive demonstration of all features.

## Testing

Run the test suite:

```bash
# Unit tests
python -m pytest tests/unit/notifications/ -v

# Integration tests
python -m pytest tests/integration/test_notification_integration.py -v

# All notification tests
python -m pytest tests/ -k "notification" -v
```

## Contributing

When adding new notification channels:

1. Create a new sender class inheriting from base patterns
2. Implement circuit breaker integration
3. Add comprehensive error handling
4. Create formatter for the new channel
5. Add unit and integration tests
6. Update documentation

## License

This notification system is part of the PMCC Scanner project. See main project license for details.