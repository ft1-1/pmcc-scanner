# PMCC Scanner

A sophisticated Python application for identifying profitable Poor Man's Covered Call (PMCC) options trading opportunities through automated market scanning and analysis.

## Overview

The PMCC Scanner is a financial technology tool designed to automatically scan the stock market daily, identify high-quality PMCC opportunities, and notify users via WhatsApp and email. It uses advanced options analysis algorithms to evaluate potential trades based on configurable criteria.

### Key Features

- **Automated Daily Scanning**: Scheduled scans of the entire options market
- **Advanced PMCC Analysis**: Sophisticated algorithms for identifying optimal LEAPS and short call combinations
- **Risk Assessment**: Comprehensive risk metrics including early assignment probability
- **Multi-Channel Notifications**: WhatsApp (primary) and email (fallback) alerts
- **Production-Ready**: Robust error handling, logging, and monitoring
- **Flexible Configuration**: Environment-based settings for easy deployment

## Quick Start

### Prerequisites

- Python 3.8 or higher
- MarketData.app API token
- Twilio account (for WhatsApp notifications)
- Mailgun account (for email notifications) or SendGrid for backward compatibility

### Installation

1. Clone the repository and navigate to the project directory:
```bash
cd /home/deployuser/stock-options/pmcc-scanner
```

2. Run the setup script:
```bash
./scripts/setup.sh
```

This will:
- Create a Python virtual environment
- Install all dependencies
- Set up the directory structure
- Create configuration templates

3. Configure your environment:
```bash
cp .env.example .env
# Edit .env with your API keys and settings
vim .env
```

4. Activate the virtual environment:
```bash
source venv/bin/activate
```

5. Run tests to verify installation:
```bash
pytest
```

## Configuration

### Required Environment Variables

```bash
# MarketData.app API
MARKETDATA_API_TOKEN=your_token_here

# Twilio (WhatsApp)
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
WHATSAPP_TO_NUMBERS=whatsapp:+1234567890

# Mailgun (Email - preferred)
MAILGUN_API_KEY=your_mailgun_api_key
MAILGUN_DOMAIN=your_mailgun_domain.com
EMAIL_FROM=scanner@yourdomain.com
EMAIL_TO=alerts@yourdomain.com

# SendGrid (Email - backward compatibility)
# SENDGRID_API_KEY=your_sendgrid_api_key

# Scan Configuration
DAILY_SCAN_TIME=09:30
```

### PMCC Strategy Parameters

Configure the strategy parameters in your `.env` file:

```bash
# LEAPS Selection
LEAPS_MIN_DTE=270      # Minimum days to expiration (9 months)
LEAPS_MAX_DTE=720      # Maximum days to expiration (24 months)
LEAPS_MIN_DELTA=0.75   # Minimum delta (deep ITM)
LEAPS_MAX_DELTA=0.90   # Maximum delta

# Short Call Selection
SHORT_CALL_MIN_DTE=21      # Minimum days (3 weeks)
SHORT_CALL_MAX_DTE=45      # Maximum days (6 weeks)
SHORT_CALL_MIN_DELTA=0.20  # Minimum delta
SHORT_CALL_MAX_DELTA=0.35  # Maximum delta

# Stock Screening
MIN_MARKET_CAP=50000000      # $50M minimum
MAX_MARKET_CAP=5000000000    # $5B maximum
MIN_DAILY_VOLUME=100000      # Minimum liquidity
```

## Usage

### Manual Scan

Run a one-time scan:
```bash
python scripts/run_daily_scan.py
```

### Scheduled Operation

Set up automated daily scanning:

**Option 1: Using Cron (Recommended)**
```bash
./scripts/setup_cron.sh
```

**Option 2: Using SystemD**
```bash
./scripts/setup_systemd.sh
```

### Monitoring

Check system status:
```bash
# For cron deployment
./scripts/cron_monitor.sh status

# Health check
python scripts/health_check.py
```

View logs:
```bash
# Recent scan logs
tail -f logs/daily_scan.log

# All logs
./scripts/cron_monitor.sh logs
```

## Architecture

The application follows a modular architecture:

```
src/
├── api/              # MarketData.app integration
├── analysis/         # PMCC analysis engine
├── notifications/    # Alert system
├── config/          # Configuration management
├── utils/           # Logging, scheduling, error handling
└── main.py          # Application entry point
```

### Core Components

1. **API Integration** (`src/api/`)
   - Rate-limited MarketData.app client
   - Automatic retry logic
   - Token bucket rate limiting

2. **Analysis Engine** (`src/analysis/`)
   - Stock screener (market cap, liquidity)
   - Options analyzer (LEAPS/short call selection)
   - Risk calculator (max loss, breakeven, Greeks)

3. **Notification System** (`src/notifications/`)
   - Multi-channel delivery (WhatsApp, email)
   - Circuit breaker for reliability
   - Template-based formatting

4. **Backend Infrastructure** (`src/config/`, `src/utils/`)
   - Environment-based configuration
   - Structured logging with rotation
   - APScheduler integration
   - Global error handling

## Testing

Run the test suite:
```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/

# Integration tests
pytest tests/integration/

# With coverage
pytest --cov=src --cov-report=html
```

## Deployment

### Production Checklist

1. Install dependencies: `./scripts/setup.sh`
2. Configure environment: Edit `.env` with production values
3. Run health check: `python scripts/health_check.py`
4. Set up scheduling: `./scripts/setup_cron.sh`
5. Monitor initial runs: Check logs and notifications

### Security Notes

- API keys are stored in environment variables
- Configuration files have restricted permissions (600)
- No sensitive data is logged
- All external API calls use HTTPS

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError**
   - Solution: Run `./scripts/setup.sh` to install dependencies

2. **API Authentication Failed**
   - Check MARKETDATA_API_TOKEN in .env
   - Verify token is active and has proper permissions

3. **No Notifications Received**
   - Check Twilio/Mailgun credentials (or SendGrid if using legacy setup)
   - Verify phone numbers/emails in configuration
   - Review notification logs

### Debug Mode

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
python scripts/run_daily_scan.py
```

## Development

### Adding New Features

1. Create feature branch
2. Implement with tests
3. Run QA validation
4. Submit for review

### Code Style

- Follow PEP 8
- Use type hints
- Write comprehensive docstrings
- Maintain test coverage above 80%

## Support

For issues or questions:
- Check logs in `logs/` directory
- Run health check: `python scripts/health_check.py`
- Review configuration in `.env`

## License

This project is proprietary software. All rights reserved.