# PMCC Scanner

A sophisticated Python application for identifying profitable Poor Man's Covered Call (PMCC) options trading opportunities through automated market scanning, AI-enhanced analysis, and comprehensive risk assessment.

## Overview

The PMCC Scanner is a cutting-edge financial technology tool that combines traditional options analysis with AI-powered market insights. It automatically scans the stock market daily, uses specialized data providers for optimal performance, and leverages Claude AI to provide enhanced opportunity analysis and market commentary.

### Key Features

- **AI-Enhanced Analysis**: Claude AI integration for intelligent market commentary and opportunity ranking
- **Automated Daily Scanning**: Scheduled scans with specialized provider routing for optimal performance
- **Advanced PMCC Analysis**: Sophisticated algorithms for identifying optimal LEAPS and short call combinations
- **Multi-Provider Architecture**: Specialized providers for options data, fundamentals, and AI analysis
- **Comprehensive Risk Assessment**: Advanced risk metrics with AI-powered insights
- **Multi-Channel Notifications**: WhatsApp and email alerts with AI commentary
- **Production-Ready**: Robust error handling, circuit breakers, and comprehensive monitoring
- **Flexible Configuration**: Environment-based settings with provider auto-detection

## Quick Start

### Prerequisites

- Python 3.11 or higher (required for modern async features)
- **Data Provider APIs**:
  - MarketData.app API token (for options chains and real-time quotes)
  - EODHD API token (for stock screening and fundamental data)
- **AI Enhancement (Optional)**:
  - Anthropic Claude API key (for AI-powered analysis and commentary)
- **Notification Services**:
  - Twilio account (for WhatsApp notifications)
  - Mailgun account (primary) or SendGrid (legacy support) for email notifications

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
# ==============================================
# DATA PROVIDER CONFIGURATION
# ==============================================
# Provider system operation mode (factory recommended for new installations)
PROVIDER_MODE=factory

# Primary data provider
PROVIDER_PRIMARY_PROVIDER=eodhd

# Fallback strategy (operation_specific recommended)
PROVIDER_FALLBACK_STRATEGY=operation_specific

# MarketData.app API (for options and quotes)
MARKETDATA_API_TOKEN=your_marketdata_token_here

# EODHD API (for screening and fundamentals)
EODHD_API_TOKEN=your_eodhd_token_here

# ==============================================
# AI ENHANCEMENT (OPTIONAL)
# ==============================================
# Claude AI Configuration
CLAUDE_API_KEY=sk-ant-your-claude-api-key-here
CLAUDE_MODEL=claude-3-5-sonnet-20241022
CLAUDE_DAILY_COST_LIMIT=10.0

# AI Enhancement Settings
SCAN_CLAUDE_ANALYSIS_ENABLED=true
SCAN_TOP_N_OPPORTUNITIES=10
SCAN_ENHANCED_DATA_COLLECTION_ENABLED=true

# ==============================================
# NOTIFICATION CONFIGURATION
# ==============================================
# Twilio (WhatsApp)
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
WHATSAPP_TO_NUMBERS=whatsapp:+1234567890

# Mailgun (Email - primary)
MAILGUN_API_KEY=your_mailgun_api_key
MAILGUN_DOMAIN=your_mailgun_domain.com
EMAIL_FROM=scanner@yourdomain.com
EMAIL_TO=alerts@yourdomain.com

# SendGrid (Email - legacy support)
# SENDGRID_API_KEY=your_sendgrid_api_key

# ==============================================
# OPERATIONAL SETTINGS
# ==============================================
# Scan Configuration
DAILY_SCAN_TIME=09:30
ENVIRONMENT=production
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

Run different scan modes:
```bash
# Single scan with AI enhancement
python src/main.py --mode once

# Test mode (configuration validation and health check)
python src/main.py --mode test

# Daemon mode (scheduled scans)
python src/main.py --mode daemon
```

### Configuration and Testing

Test your setup:
```bash
# Interactive provider configuration
python scripts/configure_providers.py

# Comprehensive health check
python scripts/health_check.py

# Test specific providers
python examples/enhanced_eodhd_demo.py         # EODHD provider
python examples/enhanced_notification_demo.py  # Notifications

# Test AI integration (requires Claude API key)
python test_claude_integration.py
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
# Comprehensive health check
python scripts/health_check.py

# Provider status
python -c "from src.api.provider_factory import SyncDataProviderFactory; factory = SyncDataProviderFactory(); print(factory.get_provider_status())"

# For cron deployment
./scripts/cron_monitor.sh status
```

View logs:
```bash
# Recent scan logs
tail -f logs/pmcc_scanner.log

# Daily scan logs
tail -f logs/daily_scan.log

# All logs
./scripts/cron_monitor.sh logs
```

## Architecture

The application follows a specialized multi-provider architecture with AI enhancement:

```
src/
├── analysis/         # PMCC analysis engine with AI integration
│   ├── scanner.py               # Main orchestrator
│   ├── claude_integration.py   # AI integration manager
│   └── options_analyzer.py     # Options analysis logic
├── api/              # Multi-provider API clients with specialization
│   ├── provider_factory.py     # Operation-specific provider routing
│   ├── claude_client.py        # Claude AI client
│   ├── marketdata_client.py    # MarketData.app client (options only)
│   ├── eodhd_client.py         # EODHD client (screening only)
│   └── providers/              # Specialized provider implementations
├── models/           # Enhanced data models with AI support
├── notifications/    # Multi-channel system with AI commentary
├── config/          # Comprehensive configuration management
├── utils/           # Logging, error handling, monitoring
└── main.py          # Application entry point with health checks
```

### Core Components

1. **Multi-Provider API Integration** (`src/api/`)
   - **Provider Factory**: Operation-specific routing (MarketData.app for options, EODHD for fundamentals)
   - **Circuit Breakers**: Provider-specific fault tolerance
   - **Health Monitoring**: Continuous provider health checks
   - **Cost Optimization**: AI usage tracking and limits

2. **AI-Enhanced Analysis Engine** (`src/analysis/`)
   - **Stock Screener**: EODHD-powered market cap and liquidity filtering
   - **Options Analyzer**: MarketData.app-powered LEAPS/short call selection with Greeks
   - **Risk Calculator**: Comprehensive risk metrics with early assignment analysis
   - **Claude Integration**: AI-powered market commentary and opportunity ranking

3. **Multi-Channel Notification System** (`src/notifications/`)
   - **WhatsApp Integration**: Concise alerts with AI insights via Twilio
   - **Email System**: Comprehensive daily summaries with AI commentary
   - **Smart Formatting**: Channel-optimized message formatting
   - **Circuit Breaker**: Reliable delivery with fallback mechanisms

4. **Production Infrastructure** (`src/config/`, `src/utils/`)
   - **Pydantic Configuration**: Type-safe environment management
   - **Structured Logging**: Comprehensive logging with performance monitoring
   - **Error Handling**: Global error handling with provider-specific recovery
   - **Health Monitoring**: Built-in health checks and status endpoints

## Testing

### Test Suite

Run comprehensive tests:
```bash
# All tests
pytest

# Unit tests by component
pytest tests/unit/                    # All unit tests
pytest tests/unit/analysis/          # Analysis engine tests
pytest tests/unit/api/               # API client tests
pytest tests/unit/notifications/    # Notification system tests

# Integration tests
pytest tests/integration/            # Provider integration tests
pytest tests/providers/              # Provider-specific tests

# Coverage reporting
pytest --cov=src --cov-report=html
```

### AI and Provider Testing

Test AI integration and provider functionality:
```bash
# AI integration testing
python test_claude_integration.py           # Claude API integration
python test_phase5_comprehensive.py         # Complete AI workflow

# Provider testing
python examples/enhanced_eodhd_demo.py      # EODHD provider functionality
python examples/enhanced_notification_demo.py # Notification system

# Quick validation
python test_quick_scan.py                   # Rapid system validation
```

### Performance and Load Testing

Validate system performance:
```bash
# Performance benchmarks
python tests/integration/performance_benchmark.py

# Provider workflow testing
python tests/integration/test_provider_workflow.py

# Large-scale option chain testing
pytest tests/unit/analysis/test_scanner.py -k "test_large_option_chains"
```

## Deployment

### Production Checklist

1. **System Setup**
   ```bash
   ./scripts/setup.sh                    # Install dependencies and create venv
   cp .env.example .env                  # Create configuration file
   ```

2. **Configure Environment**
   Edit `.env` with your production values:
   - Add MarketData.app API token (required for options)
   - Add EODHD API token (required for screening)
   - Add Claude API key (optional, for AI enhancement)
   - Configure Twilio for WhatsApp notifications
   - Configure Mailgun/SendGrid for email notifications

3. **Validation and Testing**
   ```bash
   python src/main.py --mode test        # Comprehensive system validation
   python scripts/health_check.py       # Health check all components
   python scripts/configure_providers.py # Interactive provider setup
   ```

4. **Production Deployment**
   ```bash
   ./scripts/setup_cron.sh              # Set up automated scheduling
   python src/main.py --mode once       # Test production scan
   ```

5. **Monitor Initial Runs**
   - Check logs: `tail -f logs/pmcc_scanner.log`
   - Verify notifications are received
   - Monitor provider health and API costs

### Advanced Configuration

#### Provider Optimization
```bash
# Configure provider preferences for optimal performance
PROVIDER_PREFERRED_OPTIONS_PROVIDER=marketdata    # Best for options
PROVIDER_PREFERRED_QUOTES_PROVIDER=marketdata     # Fastest quotes
PROVIDER_PREFERRED_STOCK_SCREENER=eodhd          # Only screener available
```

#### AI Cost Management
```bash
# Control Claude AI usage and costs
CLAUDE_DAILY_COST_LIMIT=10.0                     # Daily spending limit
SCAN_TOP_N_OPPORTUNITIES=10                      # Limit AI analysis scope
CLAUDE_MAX_STOCKS_PER_ANALYSIS=10                # Max stocks per AI call
```

#### Performance Tuning
```bash
# Provider performance settings
PROVIDER_MAX_CONCURRENT_REQUESTS_PER_PROVIDER=10
PROVIDER_REQUEST_TIMEOUT_SECONDS=30
PROVIDER_ENABLE_RESPONSE_CACHING=true
```

### Security Notes

- **API Key Security**: All API keys stored in environment variables only
- **File Permissions**: Configuration files have restricted permissions (600)
- **Logging Safety**: No sensitive data (API keys, tokens) logged
- **Secure Communication**: All external API calls use HTTPS/TLS
- **Provider Isolation**: Each provider operates in isolation with circuit breakers

## Troubleshooting

### Common Issues

1. **Provider Configuration Issues**
   ```bash
   # Run provider configuration wizard
   python scripts/configure_providers.py
   
   # Check provider status
   python src/main.py --mode test
   ```

2. **API Authentication Failed**
   - **MarketData.app**: Check `MARKETDATA_API_TOKEN` in `.env`
   - **EODHD**: Check `EODHD_API_TOKEN` in `.env`
   - **Claude AI**: Check `CLAUDE_API_KEY` in `.env`
   - Verify all tokens are active and have proper permissions

3. **No Notifications Received**
   ```bash
   # Test notification system
   python examples/enhanced_notification_demo.py
   ```
   - Check Twilio credentials for WhatsApp
   - Verify Mailgun/SendGrid configuration for email
   - Review notification logs: `tail -f logs/pmcc_scanner.log`

4. **Provider Health Issues**
   ```bash
   # Check provider health
   python -c "from src.api.provider_factory import SyncDataProviderFactory; factory = SyncDataProviderFactory(); print(factory.get_provider_status())"
   ```

5. **AI Enhancement Not Working**
   - Verify Claude API key is valid
   - Check daily cost limits haven't been exceeded
   - Ensure `SCAN_CLAUDE_ANALYSIS_ENABLED=true`

### Debug Mode

Enable comprehensive debugging:
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with debug mode
python src/main.py --mode once --log-level DEBUG

# Test specific components
python test_claude_integration.py         # AI integration
python test_quick_scan.py                # Quick validation
```

### Health Monitoring

Monitor system health:
```bash
# Comprehensive health check
python scripts/health_check.py

# Provider-specific health
python examples/enhanced_eodhd_demo.py    # EODHD provider
python -c "from src.api.marketdata_client import SyncMarketDataClient; client = SyncMarketDataClient(); print(client.test_connection())"

# Check logs for issues
tail -f logs/pmcc_scanner.log
grep "ERROR\|CRITICAL" logs/pmcc_scanner.log
```

## Development

### Adding New Features

1. **Create feature branch** from the current development branch
2. **Implement with comprehensive tests** (unit, integration, provider-specific)
3. **Run full test suite**: `pytest` and provider validation
4. **Validate AI integration** (if applicable): `python test_claude_integration.py`
5. **Run QA validation**: Comprehensive testing across all components
6. **Submit for review** with test results and documentation updates

### Code Style and Standards

- **Follow PEP 8** for Python code formatting
- **Use comprehensive type hints** for all function signatures
- **Write detailed docstrings** for all public methods and classes
- **Maintain test coverage above 85%** for all new code
- **Provider-specific testing** for any API integration changes
- **Performance testing** for analysis engine modifications

### Development Tools

```bash
# Code formatting and linting
black .                    # Format code
ruff check .              # Check code style
mypy .                    # Type checking

# Testing and validation
pytest --cov=src --cov-report=html    # Coverage report
python scripts/health_check.py        # System health
python src/main.py --mode test        # Full validation
```

### Architecture Guidelines

- **Provider Separation**: Maintain strict separation between provider responsibilities
- **Operation-Specific Routing**: Ensure new operations are routed to appropriate providers
- **AI Cost Management**: Include cost controls for any AI-related features
- **Circuit Breaker Patterns**: Implement fault tolerance for all external API calls
- **Comprehensive Logging**: Add structured logging for debugging and monitoring

## Support and Documentation

### Getting Help

1. **Check system health**: `python scripts/health_check.py`
2. **Review logs**: Check `logs/` directory for detailed error information
3. **Validate configuration**: `python src/main.py --mode test`
4. **Test components**: Use examples in `examples/` directory

### Documentation

- **CLAUDE.md**: Development guidance and architecture details
- **docs/CLAUDE_AI_INTEGRATION.md**: Comprehensive AI integration guide
- **docs/API_INTEGRATION.md**: API provider integration details
- **docs/NOTIFICATION_SYSTEM.md**: Notification system configuration

### Key Resources

- Provider configuration wizard: `python scripts/configure_providers.py`
- Health monitoring: `python scripts/health_check.py`
- AI integration testing: `python test_claude_integration.py`
- Performance benchmarking: `python tests/integration/performance_benchmark.py`

## License

This project is proprietary software. All rights reserved.