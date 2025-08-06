# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the PMCC (Poor Man's Covered Call) Scanner application - a financial technology tool designed to identify and analyze options trading opportunities using the Poor Man's Covered Call strategy. The application runs daily scans to find profitable PMCC opportunities and sends notifications to users.

## Architecture & Key Components

### Modern Multi-Provider Architecture
- **Provider Factory Pattern**: Multi-provider data access with automatic fallback
- **Circuit Breaker Pattern**: Prevents cascading failures across providers
- **Configuration Management**: Sophisticated Pydantic-based settings system
- **Notification System**: WhatsApp + Email with circuit breakers and daily summaries
- **Error Handling**: Comprehensive global error handler with performance monitoring
- **Health Monitoring**: Built-in health checks and status endpoints

### Specialized Agents
The project uses a multi-agent architecture with specialized Claude agents for different aspects of development:

- **pmcc-project-lead**: Central coordinator for project planning, task delegation, architectural decisions, and change management
- **eodhd-api-specialist**: Handles integration with EODHD API for fetching stock screening, options chains, and fundamental data
- **options-quant-strategist**: Implements options analysis, Greeks calculations, and PMCC strategy validation
- **notification-systems-architect**: Manages multi-channel notification systems (WhatsApp, SMS, email)
- **backend-systems-architect**: Designs scalable backend architecture and deployment strategies
- **pmcc-qa-tester**: Performs comprehensive testing and quality assurance

### Data Provider Architecture
- **Multi-provider system** with automatic fallback and intelligent routing
- **MarketData.app**: Primary for options chains, quotes, and Greeks calculations
- **EODHD**: Primary for stock screening and fallback for options data
- **Provider Factory**: Handles circuit breakers, health monitoring, and automatic failover
- **Intelligent Routing**: Optimizes provider selection based on data type and performance

## Configuration System
- **Pydantic-based settings** with comprehensive validation
- **Provider auto-detection** based on available API tokens
- **Environment-specific configurations** (development, staging, production)
- **Provider routing preferences** for optimal performance and cost
- **Dynamic configuration** with runtime provider switching capabilities

## Development Commands

### Python Project
```bash
# Install dependencies
pip install -r requirements.txt

# Run the scanner
python src/main.py --mode once          # Single scan
python src/main.py --mode daemon        # Scheduled runs
python src/main.py --mode test          # Test mode

# Run tests
pytest

# Lint code
ruff check .
black --check .

# Format code
black .
ruff check . --fix

# Type checking
mypy .
```

### Configuration Management
```bash
# Validate configuration
python src/config/settings.py --validate

# Show current configuration
python src/config/settings.py --show

# Test provider connectivity
python src/main.py --mode test
```

### Provider Configuration
```bash
# Check provider status
python -c "from src.config import get_settings; print(get_settings().get_configuration_summary())"
```

## Key Implementation Considerations

### PMCC Strategy Requirements
- LEAPS selection: Deep ITM options with delta 0.70-0.95, 6-12 months to expiration
- Short call selection: OTM calls with 30-45 DTE, delta 0.15-0.40, strike above LEAPS strike + premium
- Risk metrics: Calculate max loss, breakeven points, probability of profit
- Scoring system: Minimum 70/100 threshold for opportunities

### Multi-Provider API Integration
- **Provider Factory**: Centralized provider management with automatic selection
- **Circuit Breakers**: Prevent cascading failures with configurable thresholds
- **Rate Limiting**: Provider-specific rate limiting with automatic backoff
- **Error Recovery**: Automatic fallback to secondary providers on failure
- **Data Caching**: Intelligent caching to minimize API calls across providers
- **Health Monitoring**: Continuous provider health checks with status reporting

### System Design Priorities
1. **Reliability**: Robust error handling with multi-provider fallback
2. **Performance**: Efficient data processing with provider optimization
3. **Scalability**: Design for handling large option chains and stock universes
4. **Security**: Never expose API keys or sensitive data
5. **Modularity**: Provider-agnostic interfaces with pluggable implementations
6. **Monitoring**: Comprehensive logging and metrics for all providers

## Working with Agents

When implementing features, consider using the specialized agents:
- For high-level planning and task breakdown, consult with pmcc-project-lead
- For API integration tasks, use eodhd-api-specialist
- For options analysis logic, engage options-quant-strategist
- For notification features, use notification-systems-architect
- For system architecture decisions, consult backend-systems-architect
- For testing new features, employ pmcc-qa-tester

## Development Methodology

### Iterative Development with QA Integration
This project follows a quality-first development approach:

1. **Project Lead Orchestration**: All major development decisions flow through pmcc-project-lead
2. **Specialist Implementation**: Individual agents implement their domain expertise
3. **Continuous QA**: pmcc-qa-tester validates each component before integration
4. **Bug Resolution Loop**: QA reports issues → Project Lead assigns fixes → Agents implement → Retest
5. **Integration Testing**: Full system testing after all components are validated

### Change Management Protocol
- All major changes (API switches, architecture modifications) must go through pmcc-project-lead
- Impact analysis required for any system-wide changes
- All affected agents must be briefed on changes
- Documentation must be updated to reflect current system state

### Daily Operation Focus
- Application designed to run **once daily** as scheduled job (9:30 AM Eastern default)
- Emphasis on reliability over real-time performance
- Comprehensive logging and error recovery
- Production-ready from day one

## Current Project State

**System Architecture:** Complete and operational
- Python-based backend with multi-provider API integration
- Daily scanning workflow: Stock screening → Quote validation → Options analysis → PMCC scoring → Notifications
- Multi-channel notification system (WhatsApp primary, Email fallback)
- Comprehensive logging and error handling with circuit breakers
- Provider factory with automatic fallback and health monitoring

**Current Workflow:**
1. Provider Factory selects optimal data source based on configuration
2. Stock screening via EODHD or MarketData.app based on availability
3. Quote validation with automatic provider failover
4. Options chain analysis using MarketData.app (primary) with EODHD fallback
5. PMCC strategy evaluation with comprehensive scoring
6. Multi-channel notifications with circuit breaker protection

**Technology Stack:** 
- Python 3.11+ with async support
- Pydantic for configuration and data validation
- Multi-provider architecture (MarketData.app + EODHD)
- Twilio for WhatsApp notifications
- Mailgun/SendGrid for email delivery
- Circuit breaker pattern for fault tolerance

## Quality Assurance Integration

### Testing Requirements
- All new features must pass pmcc-qa-tester validation before integration
- Bug reports include reproduction steps and severity classification
- Fixes require QA re-verification and regression testing
- No component integration without QA approval
- Provider-specific tests for each data source

### Error-Free Operation Standard
- Application must start and run without errors
- Comprehensive logging for monitoring and debugging
- Graceful handling of all API failures and edge cases
- Performance validation under realistic data loads
- Multi-provider failover testing

## Data Flow Architecture

```
Provider Factory → Stock Screening → Quote Validation → 
Options Chain Analysis → PMCC Evaluation → Scoring → 
Circuit Breaker Check → Multi-Channel Notifications
```

## Key Configuration

The scanner is highly configurable via `.env`:
- Provider selection and API credentials
- Market cap range: $50M-$5B 
- PMCC criteria (DTE ranges, delta thresholds)
- Notification preferences (WhatsApp/Email)
- Circuit breaker thresholds
- Schedule settings

## Testing Strategy

- Unit tests for all calculation functions (especially Greeks and strategy metrics)
- Integration tests for multi-provider API interactions
- End-to-end tests for complete PMCC screening workflows
- Mock external API calls in tests to ensure reliability
- Test edge cases like early assignment risk and dividend dates
- Provider failover scenario testing
- Circuit breaker behavior validation

## Directory Structure

```
src/
├── analysis/          # PMCC analysis engine
├── api/              # Multi-provider API clients
│   └── providers/    # Provider implementations
├── config/           # Configuration management
├── models/           # Data models
├── notifications/    # Notification system
└── utils/            # Utilities and helpers

tests/                # Organized test suite
examples/             # Example scripts and demos
docs/                 # Documentation
```

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.