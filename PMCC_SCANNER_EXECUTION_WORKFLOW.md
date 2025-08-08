# PMCC Scanner Application Execution Workflow

## Overview

This document provides a comprehensive step-by-step breakdown of the PMCC Scanner application execution flow, from initialization to final notification delivery. The application supports three primary execution modes and follows a sophisticated multi-provider architecture with AI enhancement capabilities.

## Execution Modes

The PMCC Scanner can be executed in three distinct modes:

1. **`python src/main.py --mode once`** - Single scan execution
2. **`python src/main.py --mode daemon`** - Continuous daemon with scheduled scans
3. **`python src/main.py --mode test`** - Configuration validation and health check

---

## 1. Application Initialization Phase

### 1.1 Command Line Processing
- **Parse arguments**: mode, config overrides, environment, log level, notification settings
- **Apply configuration overrides**: Environment variables set based on CLI arguments
- **Create application instance**: `PMCCApplication(config_override)`

### 1.2 PMCCApplication Constructor
```python
PMCCApplication.__init__()
```
- **Apply configuration overrides** from CLI arguments to environment variables
- **Create application container** using `create_app()` factory method
- **Initialize core components**:
  - Settings loaded via Pydantic configuration system
  - Logger initialization with structured logging
  - Performance logger for metrics tracking
  - Global error handler with comprehensive error tracking
- **Setup signal handlers** for graceful shutdown (SIGINT, SIGTERM)
- **Record startup time** and initialize application state

### 1.3 Application Container Creation
```python
ApplicationContainer.create_app()
```
- **Environment detection**: Development, production, or testing
- **Settings initialization**: Load and validate Pydantic-based configuration
- **Component factory setup**: Prepare dependency injection container

---

## 2. Provider and Component Initialization

### 2.1 Component Initialization (`app.initialize()`)
```python
ApplicationContainer.initialize()
```

#### Core Component Setup:
1. **Error Handler**: Initialize global error monitoring and performance tracking
2. **Logger Configuration**: 
   - File logging with rotation
   - Console logging with configurable levels
   - JSON structured logging (optional)
   - Syslog integration (optional)
3. **Provider Factory System**:
   - **ProviderConfigurationManager**: Analyze available API tokens
   - **SyncDataProviderFactory**: Create provider factory with operation-specific routing
   - **Provider Health Checks**: Validate connectivity to all configured providers

#### Provider Specialization Setup:
- **MarketData.app**: Options chains, real-time quotes, Greeks calculations ONLY
- **EODHD**: Stock screening, fundamental data, calendar events, technical indicators ONLY  
- **Claude AI**: Market analysis, commentary, and opportunity ranking ONLY
- **Circuit Breakers**: Per-provider failure detection and automatic failover

### 2.2 Scanner Initialization
```python
PMCCScanner.create_with_provider_factory()
```
- **Provider factory integration**: Connect scanner to multi-provider system
- **Analysis components setup**:
  - `StockScreener`: EODHD-based stock filtering
  - `OptionsAnalyzer`: Multi-provider options chain analysis
  - `RiskCalculator`: Comprehensive risk metric calculations
  - `ClaudeIntegrationManager`: AI analysis coordination (if enabled)
- **Enhanced workflow components** (if configured):
  - `EnhancedEODHDProvider`: Fundamental and calendar data collection
  - `ClaudeClient`: AI analysis client
- **Validation**: Ensure all required providers are available and healthy

### 2.3 Notification Manager Setup
```python
NotificationManager.create_from_env()
```
- **Channel initialization**:
  - **WhatsApp**: Twilio-based messaging (primary channel)
  - **Email**: Mailgun/SendGrid integration (fallback channel)
- **Circuit breaker setup**: Per-channel failure detection and recovery
- **Connectivity testing**: Validate all configured notification channels
- **Formatter initialization**: Channel-specific message formatting

### 2.4 Scheduler Setup (Daemon Mode Only)
```python
create_daily_scan_scheduler()
```
- **Job scheduler creation**: APScheduler-based cron scheduling
- **Default schedule**: 9:30 AM Eastern daily (configurable)
- **Timezone handling**: Market timezone awareness
- **Scan function binding**: Connect scheduler to scanner execution

---

## 3. Execution Flow by Mode

## 3.1 Test Mode (`--mode test`)

### Health Check Sequence:
1. **Application initialization** without full startup
2. **Component health validation**:
   - Provider connectivity tests
   - API token validation
   - Database/file system access checks
   - Circuit breaker status verification
3. **Status reporting**:
   - ✅ Healthy components with details
   - ❌ Unhealthy components with error information
   - Overall system health determination
4. **Exit with status code** (0 = healthy, 1 = issues detected)

## 3.2 Single Scan Mode (`--mode once`)

### Execution Sequence:
1. **Application initialization** (`app.initialize()`)
2. **Single scan execution** (`app.run_once()`)
3. **Results display** with summary statistics
4. **Graceful shutdown** and exit

## 3.3 Daemon Mode (`--mode daemon`)

### Daemon Lifecycle:
1. **Full application startup** (`app.start()`)
2. **Scheduler activation** for automated scans
3. **Continuous operation** with signal handling
4. **Health check server** (HTTP endpoint on configurable port)
5. **Graceful shutdown** on signal or error

---

## 4. Core Scanning Workflow (`run_scan()`)

### 4.1 Scan Initialization
```python
PMCCScanner.scan(config)
```
- **Generate unique scan ID**: `pmcc_scan_YYYYMMDD_HHMMSS`
- **Initialize ScanResults**: Track all scan metrics and outcomes
- **Provider usage tracking**: Monitor API calls per provider
- **Configuration validation**: Ensure all scan parameters are valid

### 4.2 Step 1: Stock Screening
```
🔍 STEP 1: SCREENING STOCKS
```
**Provider Used**: EODHD (specialized for fundamental screening)

#### Screening Process:
1. **Universe selection**:
   - SP500, NASDAQ100, or EODHD_PMCC predefined lists
   - Custom symbol lists from configuration
   - Demo mode with curated symbols
2. **Market cap filtering**: $50M - $5B default range (configurable)
3. **Price filtering**: $10 - $300 per share typical range
4. **Volume filtering**: Minimum daily trading volume requirements
5. **Market data validation**: Ensure recent trading activity

#### Provider Operation:
```python
provider_factory.screen_stocks(criteria)
```
- **Circuit breaker check**: Verify EODHD provider health
- **API call execution**: Batch screening request to EODHD
- **Response validation**: Verify data quality and completeness
- **Usage tracking**: Record API calls and response times

### 4.3 Step 2: Options Analysis
```
📊 STEP 2: ANALYZING OPTIONS (using marketdata/eodhd)
```
**Provider Used**: MarketData.app (preferred) or EODHD (fallback)

#### Analysis Process:
For each stock that passed screening:

1. **Real-time quote validation**:
   - **Provider**: MarketData.app for current price
   - **Validation**: Confirm stock is actively trading
   - **Quote freshness**: Ensure recent price data

2. **Options chain retrieval**:
   - **Provider**: MarketData.app (primary) or EODHD (fallback)
   - **LEAPS options**: 270-720 days to expiration
   - **Short-term options**: 21-45 days to expiration
   - **Greeks calculation**: Delta, gamma, theta, vega, rho

3. **PMCC opportunity identification**:
   - **LEAPS selection**: Deep ITM calls (0.75-0.90 delta)
   - **Short call selection**: OTM calls (0.20-0.35 delta)
   - **Strike price validation**: Short strike > LEAPS strike + net premium
   - **Liquidity requirements**: Minimum bid-ask spreads and open interest

#### Provider Circuit Breaker Logic:
```python
if marketdata_circuit.is_open():
    fallback_to_eodhd()
else:
    try_marketdata_first()
```

### 4.4 Step 3: Risk Calculation
```
🎯 STEP 3: CALCULATING RISK METRICS
```
**Component**: Internal RiskCalculator (no external API)

#### Risk Metrics Computed:
1. **Basic PMCC metrics**:
   - Net debit/credit for strategy setup
   - Maximum risk (limited to net debit)
   - Maximum profit potential
   - Breakeven prices at expiration

2. **Advanced risk analysis**:
   - **Greeks exposure**: Combined position delta, gamma, theta decay
   - **Probability analysis**: Statistical profit probability
   - **Scenario modeling**: Performance under different price movements
   - **Early assignment risk**: Dividend date analysis and ITM probability

3. **Portfolio integration**:
   - Position sizing based on account risk tolerance
   - Correlation analysis with existing positions
   - Risk-adjusted return calculations

### 4.5 Step 4: Opportunity Ranking
```
🏆 STEP 4: RANKING TOP OPPORTUNITIES
```
**Component**: Internal scoring algorithm

#### Scoring System (0-100 scale):
1. **Profitability Score (40%)**:
   - Return on risk ratio
   - Profit probability
   - Risk-adjusted returns

2. **Risk Score (30%)**:
   - Maximum loss potential
   - Greeks stability
   - Early assignment risk

3. **Liquidity Score (20%)**:
   - Bid-ask spreads
   - Open interest levels
   - Daily volume

4. **Technical Score (10%)**:
   - Chart patterns
   - Support/resistance levels
   - Momentum indicators

#### Filtering Process:
- **Minimum score threshold**: Default 60/100 (configurable)
- **Best per symbol**: Keep only highest-scored opportunity per stock
- **Maximum results**: Top 25 opportunities (configurable)

---

## 5. Enhanced AI Workflow (Phase 3)

### 5.1 AI Enhancement Initialization
```python
enhanced_available = _initialize_enhanced_workflow(config)
```
- **Claude API validation**: Verify API key and connectivity
- **Enhanced EODHD provider setup**: For fundamental data collection
- **Claude integration manager**: Coordinate AI analysis workflow
- **Cost controls**: Daily limits and token management

### 5.2 Step 5: AI-Enhanced Analysis
```
🧠 STEP 5: AI-ENHANCED ANALYSIS
```
**Conditional execution**: Only if Claude API configured and traditional opportunities found

#### Sub-step 5a: Enhanced Data Collection
**Provider Used**: EODHD (specialized for fundamental data)

For each top-ranked opportunity:
1. **Fundamental data retrieval**:
   - Financial metrics (P/E, EPS growth, debt ratios)
   - Revenue and earnings trends
   - Dividend history and sustainability
   - Competitive positioning metrics

2. **Calendar events analysis**:
   - Upcoming earnings announcements
   - Ex-dividend dates affecting strategy
   - Corporate actions and events
   - Economic event impacts

3. **Technical indicators**:
   - Moving averages and trend analysis
   - Volume patterns and momentum
   - Support and resistance levels
   - Volatility measurements

#### Sub-step 5b: Claude AI Analysis
**Provider Used**: Anthropic Claude API

1. **Market context preparation**:
   - Analysis date and market conditions
   - Overall opportunity count and quality
   - Market sentiment indicators
   - Volatility regime assessment

2. **AI analysis request**:
   ```python
   claude_client.analyze_pmcc_opportunities(
       opportunities=enhanced_stock_data,
       market_context=market_context,
       analysis_type="comprehensive"
   )
   ```

3. **AI response processing**:
   - **Individual opportunity analysis**: Company-specific insights
   - **Risk assessment**: AI-powered risk evaluation
   - **Market timing**: Optimal entry/exit recommendations
   - **Strategic recommendations**: Position sizing and management
   - **Confidence scoring**: AI confidence in each analysis

#### Sub-step 5c: Integration and Top N Selection
**Component**: ClaudeIntegrationManager

1. **Analysis integration**:
   - Combine traditional PMCC scores with AI insights
   - **Weighted scoring**: 60% traditional + 40% AI insights
   - **Confidence filtering**: Minimum AI confidence thresholds
   - **Quality assurance**: Validate AI recommendations

2. **Top N selection**:
   - **Default selection**: Top 10 opportunities (configurable)
   - **Diversity optimization**: Ensure sector/style diversification
   - **Risk balancing**: Optimize overall portfolio risk
   - **Final ranking**: Combined score with AI enhancement

3. **Enhanced result packaging**:
   - Traditional PMCC analysis preserved
   - AI commentary and insights added
   - Combined confidence scores
   - Strategic recommendations included

---

## 6. Result Processing and Export

### 6.1 Result Compilation
```python
ScanResults.finalize()
```
- **Duration calculation**: Total scan time and per-step timing
- **Statistics compilation**:
  - Stocks screened vs. passed screening
  - Options analyzed vs. viable opportunities
  - Provider usage statistics and performance
  - Error and warning summaries
- **Quality metrics**: Success rates and data completeness

### 6.2 Data Export
```python
scanner.export_results(results, format=["json", "csv"])
```
- **JSON export**: Complete structured data with all metadata
- **CSV export**: Tabular format for spreadsheet analysis
- **File naming**: Timestamp-based with scan ID
- **Directory management**: Organized by date with cleanup policies
- **Historical preservation**: Maintain scan history for trend analysis

### 6.3 Export File Structure
**JSON Format**:
```json
{
  "scan_id": "pmcc_scan_20240807_093045",
  "metadata": {
    "started_at": "2024-08-07T09:30:45Z",
    "completed_at": "2024-08-07T09:35:22Z",
    "duration_seconds": 277.3,
    "configuration": {...}
  },
  "statistics": {
    "stocks_screened": 2847,
    "stocks_passed_screening": 156,
    "options_analyzed": 156,
    "opportunities_found": 23,
    "ai_enhanced_opportunities": 10
  },
  "opportunities": [
    {
      "symbol": "AAPL",
      "pmcc_analysis": {...},
      "risk_metrics": {...},
      "ai_insights": {...}
    }
  ],
  "provider_usage": {...},
  "errors": [...],
  "warnings": [...]
}
```

---

## 7. Notification Delivery

### 7.1 Notification Preparation
```python
notification_manager.send_multiple_opportunities()
```

#### Message Formatting:
1. **WhatsApp format** (Primary channel):
   ```
   📊 PMCC DAILY SCAN RESULTS
   🗓️ Wednesday, Aug 07, 2024 - 9:35 AM

   🎯 FOUND 10 OPPORTUNITIES (AI-Enhanced)
   📈 Scanned 2,847 stocks in 4.6 minutes

   TOP OPPORTUNITIES:
   🥇 AAPL - Score: 87.5 (AI: 89.2)
      📊 Net Debit: $12.50 | Max Profit: $37.50
      🎯 Return: 300% | Risk: $1,250
      🤖 AI: "Strong technical setup with earnings catalyst"
   
   [Additional opportunities...]
   
   ⚡ Powered by Claude AI Analysis
   ```

2. **Email format** (Fallback channel):
   - HTML formatted with tables and charts
   - Detailed opportunity breakdown
   - Risk analysis summaries
   - Historical performance comparisons
   - Downloadable attachments (JSON/CSV)

### 7.2 Multi-Channel Delivery
```python
NotificationManager.send_to_all_channels()
```

#### Delivery Sequence:
1. **Primary channel (WhatsApp)**:
   - Circuit breaker check
   - Message formatting and sending
   - Delivery confirmation
   - Error handling and retry logic

2. **Fallback channel (Email)**:
   - Automatic fallback if WhatsApp fails
   - Manual fallback for detailed analysis
   - Delivery tracking and confirmation
   - SMTP error handling

#### Circuit Breaker Logic:
```python
# WhatsApp Circuit Breaker
if whatsapp_failures >= 3:
    open_whatsapp_circuit()  # 5-minute timeout
    fallback_to_email()

# Email Circuit Breaker  
if email_failures >= 5:
    open_email_circuit()     # 3-minute timeout
    log_critical_error()
```

### 7.3 Delivery Tracking
- **Delivery confirmation**: Track successful sends per channel
- **Failure logging**: Record and analyze delivery failures
- **Performance metrics**: Message delivery times and success rates
- **Historical tracking**: Maintain delivery history for reliability analysis

---

## 8. System Monitoring and Health Checks

### 8.1 Performance Monitoring
```python
error_handler.get_performance_summary()
```
- **API response times**: Per-provider performance tracking
- **Memory usage**: Application resource consumption
- **Processing times**: Per-step execution timing
- **Success rates**: Overall system reliability metrics

### 8.2 Error Handling and Recovery
```python
GlobalErrorHandler.handle_error()
```

#### Error Categories:
1. **API Errors**: Provider connectivity and rate limiting
2. **Data Errors**: Malformed responses and validation failures
3. **Processing Errors**: Calculation and analysis failures
4. **Notification Errors**: Delivery failures and formatting issues

#### Recovery Strategies:
- **Automatic retry**: Exponential backoff for transient failures
- **Provider fallback**: Seamless switching between data sources
- **Graceful degradation**: Continue operation with reduced functionality
- **Circuit breaker**: Prevent cascade failures across providers

### 8.3 Health Check Endpoints (Daemon Mode)
**HTTP Server**: `http://localhost:8080/health` (configurable port)

```json
{
  "healthy": true,
  "timestamp": "2024-08-07T14:30:45Z",
  "components": {
    "scanner": {"healthy": true, "status": "operational"},
    "providers": {"healthy": true, "available": ["eodhd", "marketdata", "claude"]},
    "notifications": {"healthy": true, "channels": ["whatsapp", "email"]},
    "scheduler": {"healthy": true, "next_run": "2024-08-08T09:30:00Z"}
  },
  "system_health": {
    "error_rate_24h": 0.02,
    "avg_response_time": 1.23,
    "memory_usage_mb": 245
  }
}
```

---

## 9. Error Scenarios and Handling

### 9.1 Provider Failure Scenarios

#### EODHD API Failure:
- **Impact**: Stock screening disabled
- **Fallback**: Use cached symbol lists or predefined universes
- **Recovery**: Circuit breaker timeout and automatic retry

#### MarketData.app API Failure:
- **Impact**: Options chain retrieval affected
- **Fallback**: Automatic switch to EODHD options data
- **Recovery**: Continue with reduced data quality

#### Claude AI Failure:
- **Impact**: AI enhancement disabled
- **Fallback**: Continue with traditional PMCC analysis only
- **Recovery**: Graceful degradation, maintain core functionality

### 9.2 System Recovery Procedures

#### Critical Failure Response:
1. **Error logging**: Comprehensive error context capture
2. **Notification**: System alert to administrators
3. **Fallback mode**: Switch to minimal viable functionality
4. **Recovery monitoring**: Track system restoration progress

#### Performance Degradation:
1. **Circuit breaker activation**: Isolate failing components
2. **Load shedding**: Reduce processing intensity
3. **Provider rebalancing**: Shift load to healthy providers
4. **Gradual recovery**: Systematic restoration of full functionality

---

## 10. Configuration and Customization

### 10.1 Environment Configuration
**File**: `.env` (development) or environment variables (production)

#### Core Settings:
```bash
# Environment
ENVIRONMENT=production
DEBUG=false

# API Keys (required)
EODHD_API_TOKEN=your_eodhd_token
MARKETDATA_API_TOKEN=your_marketdata_token
ANTHROPIC_API_KEY=your_claude_token

# Notification Settings
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
NOTIFICATION_WHATSAPP_TO=+1234567890

# Scan Configuration
SCAN_MAX_OPPORTUNITIES=25
SCAN_MIN_TOTAL_SCORE=70
SCAN_USE_HYBRID_FLOW=true
```

### 10.2 Runtime Configuration Override
```python
# CLI Override Examples
python src/main.py --mode once --log-level DEBUG --no-notifications
python src/main.py --mode daemon --env production
```

### 10.3 Provider Configuration
**Auto-detection**: System automatically detects available providers based on API tokens
**Manual override**: Force specific provider usage through configuration
**Health-based routing**: Automatic provider selection based on current health status

---

## 11. Deployment and Operational Considerations

### 11.1 Production Deployment
- **Schedule**: Daily execution at 9:30 AM Eastern (after market open)
- **Resource requirements**: 512MB RAM, 1 CPU core minimum
- **Network**: Reliable internet for API access (rate limits: ~100 req/min per provider)
- **Storage**: 1GB minimum for logs and result history

### 11.2 Monitoring and Maintenance
- **Log rotation**: Automatic cleanup of old log files
- **Result archival**: Automatic cleanup of old scan results (configurable retention)
- **Health monitoring**: Built-in HTTP health check endpoints
- **Error alerting**: System notifications for critical failures

### 11.3 Security Considerations
- **API key protection**: Never log or expose API credentials
- **Network security**: HTTPS for all external API calls
- **Data privacy**: No persistent storage of sensitive financial data
- **Access control**: Restrict health check endpoints in production

---

This comprehensive workflow document covers the complete execution flow of the PMCC Scanner application across all operating modes, providing both high-level understanding and detailed technical implementation insights for operational teams and developers.