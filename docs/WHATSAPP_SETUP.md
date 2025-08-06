# WhatsApp Setup Guide for PMCC Scanner

This guide explains how to set up WhatsApp notifications for the PMCC Scanner using Twilio's WhatsApp Business API.

## Quick Fix Summary

The critical WhatsApp notification failure (Code: 63007) was caused by:

1. **Missing Configuration**: The code expected `TWILIO_WHATSAPP_FROM` but the .env file only had `TWILIO_PHONE_NUMBER`
2. **Wrong Format**: WhatsApp numbers require the `whatsapp:` prefix

### ✅ Fixed Configuration

The `.env` file now includes:
```bash
# Twilio/WhatsApp Settings
TWILIO_ACCOUNT_SID=your_twilio_account_sid_here
TWILIO_AUTH_TOKEN=your_twilio_auth_token_here
TWILIO_PHONE_NUMBER=+1234567890
# WhatsApp sender number with required whatsapp: prefix
TWILIO_WHATSAPP_FROM=whatsapp:+1234567890
WHATSAPP_TO_NUMBERS=+1234567890
```

## Twilio WhatsApp Setup Process

### 1. Twilio Account Setup

1. **Create Twilio Account**: Sign up at [twilio.com](https://www.twilio.com)
2. **Get Account Credentials**:
   - Account SID: Found in Twilio Console dashboard
   - Auth Token: Found in Twilio Console dashboard

### 2. WhatsApp Configuration Options

#### Option A: WhatsApp Sandbox (Development/Testing)

**Recommended for testing and development**

1. **Enable WhatsApp Sandbox**:
   - Go to Twilio Console → Messaging → Try WhatsApp
   - Follow the setup instructions
   - Join the sandbox by sending a message to the provided number

2. **Sandbox Configuration**:
   ```bash
   # Use Twilio's sandbox number
   TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
   ```

3. **Test Recipients**:
   - Recipients must join the sandbox first
   - Send the join code to Twilio's sandbox number
   - Then they can receive messages

#### Option B: Production WhatsApp Number

**Required for production use**

1. **Request WhatsApp Business Number**:
   - Go to Twilio Console → Messaging → Services
   - Create a new messaging service
   - Add WhatsApp as a channel
   - Submit your business information for approval

2. **Business Verification**:
   - Provide business documentation
   - Wait for Facebook/Meta approval (can take several days)
   - Once approved, you'll get a production WhatsApp number

3. **Production Configuration**:
   ```bash
   # Use your approved business number
   TWILIO_WHATSAPP_FROM=whatsapp:+1YOUR_APPROVED_NUMBER
   ```

### 3. Current Setup Analysis

Based on the current configuration:

- **Number**: +17819735171
- **Status**: Likely a regular Twilio phone number, not yet WhatsApp-enabled
- **Action Needed**: Enable WhatsApp for this number or use sandbox

## Configuration Requirements

### Environment Variables

```bash
# Required Twilio credentials
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token

# WhatsApp sender (MUST include whatsapp: prefix)
TWILIO_WHATSAPP_FROM=whatsapp:+1234567890

# Recipients (can be comma-separated list)
WHATSAPP_TO_NUMBERS=+1234567890,+0987654321

# Optional: Enable/disable WhatsApp notifications
NOTIFICATION_WHATSAPP_ENABLED=true
```

### Important Format Rules

1. **Sender Number**: MUST start with `whatsapp:`
   - ✅ Correct: `whatsapp:+17819735171`
   - ❌ Wrong: `+17819735171`

2. **Recipient Numbers**: Can be with or without `whatsapp:` prefix
   - ✅ Accepted: `+14038040786`
   - ✅ Also accepted: `whatsapp:+14038040786`

3. **International Format**: Always use E.164 format
   - ✅ Correct: `+1234567890`
   - ❌ Wrong: `1234567890` or `(123) 456-7890`

## Testing Your Setup

### 1. Run Configuration Test

```bash
python3 test_whatsapp_fix.py
```

This script will:
- Validate your configuration
- Test number formatting
- Check Twilio account connectivity
- Optionally send a test message

### 2. Manual Testing

```python
from src.notifications.whatsapp_sender import WhatsAppSender
from src.notifications.models import NotificationTemplate

# Initialize sender
sender = WhatsAppSender()

# Create test message
template = NotificationTemplate(
    text_content="Test message from PMCC Scanner"
)

# Send message
result = sender.send_message("+14038040786", template)
print(f"Status: {result.status}")
```

## Error Codes and Troubleshooting

### Common Error Codes

#### 63007: Channel Not Found
- **Cause**: The `from` number is not WhatsApp-enabled
- **Solution**: 
  1. Check `TWILIO_WHATSAPP_FROM` has `whatsapp:` prefix
  2. Verify the number is WhatsApp-enabled in Twilio console
  3. For testing, use sandbox number: `whatsapp:+14155238886`

#### 63016: Recipient Not Available
- **Cause**: Recipient not on WhatsApp or not approved
- **Solution**:
  1. For sandbox: Recipient must join sandbox first
  2. For production: Recipient must have WhatsApp installed
  3. Check if your business account is approved for this recipient

#### 20429: Rate Limit Exceeded
- **Cause**: Sending too many messages too quickly
- **Solution**: The system automatically retries with backoff

### Troubleshooting Steps

1. **Check Configuration**:
   ```bash
   # Verify environment variables are set
   echo $TWILIO_WHATSAPP_FROM
   ```

2. **Validate Number Format**:
   - Ensure `whatsapp:` prefix on sender
   - Use E.164 format for all numbers

3. **Test Twilio Connectivity**:
   ```bash
   python3 test_whatsapp_fix.py
   ```

4. **Check Twilio Console**:
   - Verify account status
   - Check WhatsApp channel configuration
   - Review message logs

## Current Number Status Check

To check if +17819735171 is WhatsApp-enabled:

1. **Twilio Console Method**:
   - Go to Twilio Console → Phone Numbers → Manage → Active numbers
   - Click on +17819735171
   - Check if WhatsApp is listed in "Capabilities"

2. **API Method**:
   ```python
   from twilio.rest import Client
   
   client = Client(account_sid, auth_token)
   number = client.incoming_phone_numbers.list(phone_number='+17819735171')[0]
   print(f"Capabilities: {number.capabilities}")
   ```

## Recommendations

### For Immediate Testing
1. Use Twilio WhatsApp Sandbox:
   ```bash
   TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
   ```
2. Join sandbox with test recipients
3. Verify messages work end-to-end

### For Production
1. Submit business verification to enable +17819735171 for WhatsApp
2. Or purchase a new number specifically for WhatsApp
3. Complete Facebook Business verification process
4. Test thoroughly before deploying

## Message Templates and Best Practices

### Template Guidelines
- Keep messages under 1600 characters
- Use clear, actionable content
- Include relevant emojis sparingly
- Provide value to recipients

### Example PMCC Notification Template
```
🎯 PMCC Opportunity Alert

Symbol: {symbol}
Current Price: ${price}
LEAPS Strike: ${leaps_strike}
Short Strike: ${short_strike}
Max Profit: ${max_profit}
Risk/Reward: {risk_reward_ratio}

Expires: {expiration_date}

🔗 View Details: {analysis_link}
```

## Monitoring and Alerting

### Key Metrics to Track
- Message delivery rate
- Error frequency by type
- Response times
- Cost per message

### Logging Configuration
The system logs all WhatsApp activities:
- Message sent/failed
- Error codes and descriptions
- Delivery confirmations
- Rate limiting events

Check logs in: `logs/pmcc_scanner.log`

## Cost Considerations

### Twilio WhatsApp Pricing
- **Sandbox**: Free for testing
- **Production**: $0.005 - $0.09 per message (varies by country)
- **Template Messages**: Different pricing than session messages

### Cost Optimization
- Use message templates when possible
- Batch notifications for multiple opportunities
- Implement user preferences for notification frequency
- Monitor and alert on unusual usage patterns

## Support and Resources

- **Twilio WhatsApp Documentation**: https://www.twilio.com/docs/whatsapp
- **WhatsApp Business API**: https://developers.facebook.com/docs/whatsapp
- **Twilio Console**: https://console.twilio.com
- **Rate Limits**: https://www.twilio.com/docs/usage/rate-limits

For issues with this implementation, check:
1. Application logs: `logs/pmcc_scanner.log`
2. Test script output: `python3 test_whatsapp_fix.py`
3. Twilio Console message logs