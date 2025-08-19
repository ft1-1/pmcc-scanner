"""
Configuration management for PMCC Scanner application.

Handles environment variables, validation, and different deployment environments
with type safety and comprehensive validation.
"""

import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any, Union, Tuple
from decimal import Decimal
from enum import Enum
import logging

try:
    from dotenv import load_dotenv
    from pydantic import Field, field_validator, model_validator
    from pydantic_settings import BaseSettings
except ImportError as e:
    print(f"Missing required dependency: {e}")
    print("Please install: pip install python-dotenv pydantic-settings")
    sys.exit(1)


class Environment(str, Enum):
    """Deployment environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class LogLevel(str, Enum):
    """Logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ProviderMode(str, Enum):
    """Provider system operation mode."""
    LEGACY = "legacy"       # Use legacy single-provider approach
    FACTORY = "factory"     # Use new multi-provider factory system
    HYBRID = "hybrid"       # Use hybrid approach with fallbacks


class DataProviderType(str, Enum):
    """Supported data provider types."""
    EODHD = "eodhd"
    MARKETDATA = "marketdata"
    CLAUDE = "claude"


class FallbackStrategy(str, Enum):
    """Fallback strategies for provider failures."""
    NONE = "none"                          # No fallback, fail immediately
    ROUND_ROBIN = "round_robin"            # Try all providers in order
    OPERATION_SPECIFIC = "operation_specific"  # Use best provider for each operation
    PRIMARY_SECONDARY = "primary_secondary"   # Use primary, then secondary


class AnalysisVerbosity(str, Enum):
    """Analysis verbosity levels for PMCC scanning."""
    QUIET = "quiet"         # Only show final results
    NORMAL = "normal"       # Show why stocks fail (current behavior)
    VERBOSE = "verbose"     # Show detailed analysis for each stock
    DEBUG = "debug"         # Show every option contract evaluated


class DataProviderConfig(BaseSettings):
    """Data provider configuration for multi-provider support."""
    
    # Provider mode settings
    provider_mode: ProviderMode = Field(ProviderMode.FACTORY, description="Provider system operation mode")
    
    # Provider selection
    primary_provider: DataProviderType = Field(DataProviderType.EODHD, description="Primary data provider")
    fallback_strategy: FallbackStrategy = Field(FallbackStrategy.OPERATION_SPECIFIC, description="Fallback strategy")
    
    # Operation-specific provider preferences
    preferred_stock_screener: DataProviderType = Field(DataProviderType.EODHD, description="Preferred provider for stock screening")
    preferred_options_provider: DataProviderType = Field(DataProviderType.MARKETDATA, description="Preferred provider for options data")
    preferred_quotes_provider: DataProviderType = Field(DataProviderType.MARKETDATA, description="Preferred provider for stock quotes")
    preferred_greeks_provider: DataProviderType = Field(DataProviderType.MARKETDATA, description="Preferred provider for Greeks calculations")
    
    # Health monitoring
    enable_health_checks: bool = Field(True, description="Enable provider health monitoring")
    health_check_interval_seconds: int = Field(300, description="Health check interval (5 minutes)")
    circuit_breaker_failure_threshold: int = Field(5, description="Circuit breaker failure threshold")
    circuit_breaker_recovery_timeout_seconds: int = Field(600, description="Circuit breaker recovery timeout (10 minutes)")
    
    # Performance settings
    max_concurrent_requests_per_provider: int = Field(10, description="Maximum concurrent requests per provider")
    request_timeout_seconds: int = Field(30, description="Provider request timeout")
    enable_response_caching: bool = Field(True, description="Enable response caching")
    cache_ttl_seconds: int = Field(300, description="Cache TTL (5 minutes)")
    
    # Cost optimization
    prioritize_cost_efficiency: bool = Field(True, description="Prioritize cost-efficient providers")
    max_daily_api_credits: int = Field(10000, description="Maximum daily API credits")
    alert_threshold_credits_remaining: int = Field(1000, description="Alert when credits remaining below threshold")
    
    # Auto-detection settings
    auto_detect_providers: bool = Field(True, description="Auto-detect available providers from API tokens")
    require_primary_provider: bool = Field(True, description="Require primary provider to be available")
    
    @field_validator('provider_mode', mode='before')
    def validate_provider_mode(cls, v):
        """Validate and normalize provider mode."""
        if isinstance(v, str):
            try:
                return ProviderMode(v.lower())
            except ValueError:
                raise ValueError(f'Invalid provider mode: {v}. Must be one of: {list(ProviderMode)}')
        return v
    
    @field_validator('primary_provider', mode='before')
    def validate_primary_provider(cls, v):
        """Validate and normalize primary provider."""
        if isinstance(v, str):
            try:
                return DataProviderType(v.lower())
            except ValueError:
                raise ValueError(f'Invalid primary provider: {v}. Must be one of: {list(DataProviderType)}')
        return v
    
    @field_validator('fallback_strategy', mode='before')
    def validate_fallback_strategy(cls, v):
        """Validate and normalize fallback strategy."""
        if isinstance(v, str):
            try:
                return FallbackStrategy(v.lower())
            except ValueError:
                raise ValueError(f'Invalid fallback strategy: {v}. Must be one of: {list(FallbackStrategy)}')
        return v
    
    model_config = {"env_prefix": "PROVIDER_"}


class MarketDataConfig(BaseSettings):
    """MarketData.app API configuration."""
    
    api_token: str = Field(..., description="MarketData.app API token")
    base_url: str = Field("https://api.marketdata.app", description="API base URL")
    timeout_seconds: int = Field(30, description="Request timeout in seconds")
    
    # Rate limiting
    requests_per_minute: int = Field(100, description="API requests per minute limit")
    requests_per_day: int = Field(100000, description="API requests per day limit")
    
    # Retry configuration
    max_retries: int = Field(3, description="Maximum retry attempts")
    retry_backoff_factor: float = Field(2.0, description="Exponential backoff factor")
    retry_max_delay: int = Field(60, description="Maximum retry delay in seconds")
    
    @field_validator('api_token')
    def api_token_must_not_be_empty(cls, v):
        if not v or v.strip() == "":
            raise ValueError('MarketData API token cannot be empty')
        return v.strip()
    
    @field_validator('base_url')
    def base_url_must_be_valid(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('Base URL must start with http:// or https://')
        return v.rstrip('/')
    
    @property
    def is_configured(self) -> bool:
        """Check if MarketData is properly configured."""
        return bool(self.api_token and self.api_token.strip() and 
                   self.api_token != "your_marketdata_api_token_here")
    
    model_config = {"env_prefix": "MARKETDATA_"}


class EODHDConfig(BaseSettings):
    """EODHD Screener API configuration."""
    
    api_token: str = Field(..., description="EODHD API token")
    base_url: str = Field("https://eodhd.com/api", description="EODHD API base URL")
    timeout_seconds: int = Field(30, description="Request timeout in seconds")
    
    # Rate limiting (EODHD screener consumes 5 API calls per request)
    requests_per_minute: int = Field(20, description="Screener requests per minute limit")
    requests_per_day: int = Field(2000, description="Screener requests per day limit")
    credits_per_request: int = Field(5, description="API credits consumed per screener request")
    
    # Retry configuration
    max_retries: int = Field(3, description="Maximum retry attempts")
    retry_backoff_factor: float = Field(2.0, description="Exponential backoff factor")
    retry_max_delay: int = Field(60, description="Maximum retry delay in seconds")
    
    # Comprehensive PMCC options fetching configuration
    pmcc_batch_size: int = Field(10, description="Batch size for comprehensive PMCC option requests")
    pmcc_batch_delay: float = Field(1.0, description="Delay in seconds between PMCC option batches")
    pmcc_concurrent_requests: int = Field(10, description="Maximum concurrent requests per batch")
    pmcc_min_success_rate: float = Field(50.0, description="Minimum success rate (%) to proceed with analysis")
    pmcc_retry_failed_batches: bool = Field(True, description="Retry failed option requests")
    pmcc_enable_caching: bool = Field(True, description="Enable caching for PMCC option data")
    pmcc_cache_ttl_minutes: int = Field(60, description="Cache TTL for PMCC options in minutes")
    
    @field_validator('api_token')
    def api_token_must_not_be_empty(cls, v):
        if not v or v.strip() == "":
            raise ValueError('EODHD API token cannot be empty')
        return v.strip()
    
    @field_validator('base_url')
    def base_url_must_be_valid(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('Base URL must start with http:// or https://')
        return v.rstrip('/')
    
    @property
    def is_configured(self) -> bool:
        """Check if EODHD is properly configured."""
        return bool(self.api_token and self.api_token.strip() and 
                   self.api_token != "your_eodhd_api_token_here")
    
    model_config = {"env_prefix": "EODHD_"}


class ClaudeConfig(BaseSettings):
    """Claude AI API configuration."""
    
    api_key: str = Field(..., description="Anthropic Claude API key")
    model: str = Field("claude-3-5-sonnet-20241022", description="Claude model to use")
    max_tokens: int = Field(4000, description="Maximum tokens in response")
    temperature: float = Field(0.1, description="Response randomness (0.0 to 1.0)")
    timeout_seconds: int = Field(60, description="Request timeout in seconds")
    
    # Analysis configuration
    max_stocks_per_analysis: int = Field(20, description="Maximum stocks to analyze per request")
    min_data_completeness_threshold: float = Field(60.0, description="Minimum data completeness % for analysis")
    
    # Cost management
    daily_cost_limit: float = Field(10.0, description="Daily cost limit in USD")
    
    # Retry configuration
    max_retries: int = Field(3, description="Maximum retry attempts")
    retry_backoff_factor: float = Field(2.0, description="Exponential backoff factor")
    retry_max_delay: int = Field(60, description="Maximum retry delay in seconds")
    
    @field_validator('api_key')
    def api_key_must_not_be_empty(cls, v):
        if not v or v.strip() == "":
            raise ValueError('Claude API key cannot be empty')
        return v.strip()
    
    @field_validator('temperature')
    def temperature_must_be_valid(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('Temperature must be between 0.0 and 1.0')
        return v
    
    @field_validator('max_tokens')
    def max_tokens_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Max tokens must be positive')
        return v
    
    @field_validator('daily_cost_limit')
    def daily_cost_limit_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Daily cost limit must be positive')
        return v
    
    @property
    def is_configured(self) -> bool:
        """Check if Claude is properly configured."""
        return bool(self.api_key and self.api_key.strip() and 
                   self.api_key != "your_claude_api_key_here")
    
    model_config = {"env_prefix": "CLAUDE_"}


class NotificationConfig(BaseSettings):
    """Notification system configuration."""
    
    # WhatsApp (Twilio) settings
    whatsapp_enabled: bool = Field(True, description="Enable WhatsApp notifications")
    twilio_account_sid: Optional[str] = Field(None, description="Twilio account SID", alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: Optional[str] = Field(None, description="Twilio auth token", alias="TWILIO_AUTH_TOKEN")
    twilio_phone_number: Optional[str] = Field(None, description="Twilio WhatsApp phone number", alias="TWILIO_PHONE_NUMBER")
    whatsapp_to_numbers: str = Field("", description="Comma-separated WhatsApp recipient numbers", alias="WHATSAPP_TO_NUMBERS")
    
    # Email settings (Mailgun preferred, SendGrid for backward compatibility)
    email_enabled: bool = Field(True, description="Enable email notifications")
    
    # Mailgun settings (preferred)
    mailgun_api_key: Optional[str] = Field(None, description="Mailgun API key", alias="MAILGUN_API_KEY")
    mailgun_domain: Optional[str] = Field(None, description="Mailgun domain", alias="MAILGUN_DOMAIN")
    
    # SendGrid settings (backward compatibility)
    sendgrid_api_key: Optional[str] = Field(None, description="SendGrid API key (deprecated - use Mailgun)", alias="SENDGRID_API_KEY")
    
    # Common email settings
    email_from: Optional[str] = Field(None, description="From email address", alias="EMAIL_FROM")
    email_from_name: str = Field("PMCC Scanner", description="From name", alias="EMAIL_FROM_NAME")
    email_to: str = Field("", description="Comma-separated email recipients", alias="EMAIL_TO")
    
    # Email notification behavior
    email_send_daily_summary: bool = Field(True, description="Enable comprehensive daily summary emails")
    email_send_individual_notifications: bool = Field(False, description="Enable legacy individual email notifications")
    
    # Notification content settings
    notification_include_all_opportunities: bool = Field(True, description="Include all opportunities vs top N only")
    
    # Notification behavior
    max_retries: int = Field(3, description="Maximum retry attempts")
    retry_delay_seconds: int = Field(60, description="Delay between retries")
    enable_fallback: bool = Field(True, description="Enable fallback channels")
    fallback_delay_seconds: int = Field(300, description="Delay before fallback activation")
    
    # Circuit breaker settings
    whatsapp_failure_threshold: int = Field(3, description="WhatsApp circuit breaker failure threshold")
    whatsapp_timeout_seconds: int = Field(300, description="WhatsApp circuit breaker timeout")
    email_failure_threshold: int = Field(5, description="Email circuit breaker failure threshold")
    email_timeout_seconds: int = Field(180, description="Email circuit breaker timeout")
    
    @model_validator(mode='after')
    def validate_notification_channels(self):
        """Ensure at least one notification channel is properly configured."""
        if not self.whatsapp_enabled and not self.email_enabled:
            raise ValueError('At least one notification channel must be enabled')
        
        # Validate WhatsApp configuration
        if self.whatsapp_enabled:
            if not self.twilio_account_sid or not self.twilio_auth_token or not self.twilio_phone_number:
                raise ValueError('WhatsApp enabled but missing required Twilio credentials')
        
        # Validate email configuration (Mailgun preferred, SendGrid for backward compatibility)
        if self.email_enabled:
            # Check if we have either Mailgun or SendGrid configured
            has_mailgun = (self.mailgun_api_key and 
                          self.mailgun_domain and
                          str(self.mailgun_api_key).strip() != "" and
                          str(self.mailgun_domain).strip() != "" and
                          self.mailgun_api_key != "your_mailgun_api_key" and
                          self.mailgun_domain != "your_mailgun_domain.com")
            
            has_sendgrid = (self.sendgrid_api_key and
                           str(self.sendgrid_api_key).strip() != "" and
                           self.sendgrid_api_key != "your_sendgrid_api_key")
            
            has_email_config = has_mailgun or has_sendgrid
            
            if (not has_email_config or 
                not self.email_from or 
                str(self.email_from).strip() == "" or
                self.email_from == "scanner@yourdomain.com"):
                import os
                environment = os.getenv('ENVIRONMENT', 'development').lower()
                if environment == 'production':
                    if not has_email_config:
                        raise ValueError('Email enabled but missing required email provider credentials (Mailgun or SendGrid)')
                    else:
                        raise ValueError('Email enabled but missing required email from address')
                else:
                    # In development, just log warning but allow the configuration
                    import logging
                    logging.warning(f"Email enabled in development but missing proper configuration. Has Mailgun: {has_mailgun}, Has SendGrid: {has_sendgrid}, Email from: {self.email_from}")
                    if not has_email_config:
                        logging.warning("No email provider configured - email notifications will be disabled")
                        self.email_enabled = False
        
        return self
    
    @property
    def email_provider(self) -> str:
        """Determine which email provider is configured."""
        if self.mailgun_api_key and self.mailgun_domain:
            if (self.mailgun_api_key != "your_mailgun_api_key" and
                self.mailgun_domain != "your_mailgun_domain.com"):
                return "mailgun"
        
        if self.sendgrid_api_key and self.sendgrid_api_key != "your_sendgrid_api_key":
            return "sendgrid"
        
        return "none"
    
    @property 
    def has_mailgun_config(self) -> bool:
        """Check if Mailgun is properly configured."""
        return (self.mailgun_api_key is not None and 
                self.mailgun_domain is not None and
                self.mailgun_api_key != "your_mailgun_api_key" and
                self.mailgun_domain != "your_mailgun_domain.com")
    
    @property
    def has_sendgrid_config(self) -> bool:
        """Check if SendGrid is properly configured."""
        return (self.sendgrid_api_key is not None and
                self.sendgrid_api_key != "your_sendgrid_api_key")
    
    @property
    def should_send_daily_summary(self) -> bool:
        """Check if daily summary emails should be sent."""
        return self.email_enabled and self.email_send_daily_summary
    
    @property
    def should_send_individual_notifications(self) -> bool:
        """Check if individual notification emails should be sent."""
        return self.email_enabled and self.email_send_individual_notifications
    
    model_config = {"env_prefix": "NOTIFICATION_"}


class ScanConfig(BaseSettings):
    """PMCC scanning configuration."""
    
    # Schedule settings
    schedule_enabled: bool = Field(True, description="Enable scheduled scanning")
    scan_time: str = Field("09:30", description="Daily scan time (HH:MM format)")
    timezone: str = Field("US/Eastern", description="Timezone for scheduling")
    
    # Universe settings
    default_universe: str = Field("SP500", description="Default stock universe")
    max_stocks_to_screen: int = Field(100, description="Maximum stocks to screen per scan")
    custom_symbols: Optional[str] = Field(None, description="Comma-separated custom symbol list")
    
    # PMCC criteria
    min_stock_price: Decimal = Field(Decimal('20.00'), description="Minimum stock price")
    max_stock_price: Decimal = Field(Decimal('500.00'), description="Maximum stock price")
    min_volume: int = Field(1000000, description="Minimum daily volume")
    min_market_cap: Optional[Decimal] = Field(Decimal('1000000000'), description="Minimum market cap")
    max_market_cap: Optional[Decimal] = Field(Decimal('5000000000'), description="Maximum market cap")
    
    # LEAPS criteria
    leaps_min_dte: int = Field(180, description="Minimum days to expiration for LEAPS")
    leaps_max_dte: int = Field(365, description="Maximum days to expiration for LEAPS")
    leaps_min_delta: Decimal = Field(Decimal('0.70'), description="Minimum delta for LEAPS")
    leaps_max_delta: Decimal = Field(Decimal('0.95'), description="Maximum delta for LEAPS")
    leaps_max_premium_pct: Decimal = Field(Decimal('0.20'), description="Maximum LEAPS premium as percentage of stock price (0.20 = 20%)")
    leaps_min_open_interest: int = Field(100, description="Minimum open interest for LEAPS")
    leaps_min_volume: int = Field(0, description="Minimum daily volume for LEAPS (set to 0 to disable)")
    leaps_max_bid_ask_spread_pct: Decimal = Field(Decimal('0.05'), description="Maximum bid-ask spread for LEAPS (0.05 = 5%, set to 0 or negative to disable)")
    leaps_max_extrinsic_pct: Decimal = Field(Decimal('0.15'), description="Maximum extrinsic value as percentage of option price (0.15 = 15%, set to 0 or negative to disable)")
    
    # Short call criteria
    short_min_dte: int = Field(30, description="Minimum days to expiration for short calls")
    short_max_dte: int = Field(45, description="Maximum days to expiration for short calls")
    short_min_delta: Decimal = Field(Decimal('0.15'), description="Minimum delta for short calls")
    short_max_delta: Decimal = Field(Decimal('0.40'), description="Maximum delta for short calls")
    short_min_open_interest: int = Field(200, description="Minimum open interest for short calls")
    short_min_volume: int = Field(10, description="Minimum daily volume for short calls")
    short_max_bid_ask_spread_pct: Decimal = Field(Decimal('0.05'), description="Maximum bid-ask spread for short calls (0.05 = 5%, set to 0 or negative to disable)")
    short_min_premium_coverage_ratio: Decimal = Field(Decimal('0.50'), description="Minimum ratio of short premium to LEAPS extrinsic (0.50 = 50%, set to 0 or negative to disable)")
    
    # Risk management
    max_risk_per_trade: Decimal = Field(Decimal('0.02'), description="Maximum risk per trade (as fraction)")
    risk_free_rate: Decimal = Field(Decimal('0.05'), description="Risk-free rate for calculations")
    min_liquidity_score: Decimal = Field(Decimal('60'), description="Minimum liquidity score")
    min_total_score: Decimal = Field(Decimal('70'), description="Minimum total score for opportunities")
    
    # Output settings
    max_opportunities: int = Field(25, description="Maximum opportunities to return")
    best_per_symbol_only: bool = Field(True, description="Only keep best opportunity per stock")
    export_results: bool = Field(True, description="Export results to file")
    export_format: str = Field("json", description="Export format (json, csv)")
    
    # CSV export configuration
    export_csv_enabled: bool = Field(True, description="Enable CSV export alongside JSON")
    export_csv_detailed: bool = Field(False, description="Enable detailed CSV with sub-scores and additional metrics")
    
    # Analysis verbosity
    analysis_verbosity: AnalysisVerbosity = Field(AnalysisVerbosity.NORMAL, description="Analysis logging verbosity level")
    
    # Data source settings
    options_source: str = Field("marketdata", description="Options data source (marketdata, eodhd)")
    use_hybrid_flow: bool = Field(False, description="Use hybrid flow (EODHD stocks -> MarketData quotes -> EODHD options)")
    
    # Tradetime filtering settings
    enable_tradetime_filtering: bool = Field(True, description="Enable/disable tradetime filtering globally")
    tradetime_lookback_days: int = Field(5, description="Number of days to look back for trading dates")
    custom_tradetime_date: Optional[str] = Field(None, description="Override tradetime filter date for testing (YYYY-MM-DD format)")
    
    # AI Enhancement settings
    claude_analysis_enabled: bool = Field(True, description="Enable Claude AI analysis (auto-detects based on API key)")
    top_n_opportunities: int = Field(10, description="Number of top opportunities to select after AI analysis")
    min_claude_confidence: float = Field(60.0, description="Minimum Claude confidence threshold for recommendations")
    min_combined_score: float = Field(70.0, description="Minimum combined (PMCC + Claude) score threshold")
    enhanced_data_collection_enabled: bool = Field(True, description="Enable enhanced data collection with fundamentals, calendar events, etc.")
    require_all_data_sources: bool = Field(False, description="Require all data sources (fundamental, calendar, technical) for AI analysis")
    
    # Scoring Weight Configuration
    traditional_pmcc_weight: float = Field(0.6, description="Weight for traditional PMCC analysis in combined scoring (0.0-1.0)")
    ai_analysis_weight: float = Field(0.4, description="Weight for AI analysis in combined scoring (0.0-1.0)")
    
    @field_validator('scan_time')
    def validate_scan_time(cls, v):
        """Validate scan time format."""
        try:
            hour, minute = v.split(':')
            hour, minute = int(hour), int(minute)
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError('Invalid time')
            return v
        except:
            raise ValueError('Scan time must be in HH:MM format (24-hour)')
    
    @field_validator('export_format')
    def validate_export_format(cls, v):
        """Validate export format."""
        if v.lower() not in ['json', 'csv', 'both']:
            raise ValueError('Export format must be json, csv, or both')
        return v.lower()
    
    @field_validator('analysis_verbosity', mode='before')
    def validate_analysis_verbosity(cls, v):
        """Validate and normalize analysis verbosity."""
        if isinstance(v, str):
            try:
                return AnalysisVerbosity(v.lower())
            except ValueError:
                raise ValueError(f'Invalid analysis verbosity: {v}. Must be one of: {list(AnalysisVerbosity)}')
        return v
    
    @field_validator('custom_tradetime_date')
    def validate_custom_tradetime_date(cls, v):
        """Validate custom tradetime date format."""
        if v is not None and v != "":
            import re
            from datetime import datetime
            # Check YYYY-MM-DD format
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', v):
                raise ValueError('Custom tradetime date must be in YYYY-MM-DD format')
            # Validate it's a real date
            try:
                datetime.strptime(v, '%Y-%m-%d')
            except ValueError:
                raise ValueError('Custom tradetime date must be a valid date in YYYY-MM-DD format')
        return v
    
    @field_validator('tradetime_lookback_days')
    def validate_tradetime_lookback_days(cls, v):
        """Validate tradetime lookback days."""
        if v < 1 or v > 30:
            raise ValueError('Tradetime lookback days must be between 1 and 30')
        return v
    
    @field_validator('top_n_opportunities')
    def validate_top_n_opportunities(cls, v):
        """Validate top N opportunities count."""
        if v < 1 or v > 50:
            raise ValueError('Top N opportunities must be between 1 and 50')
        return v
    
    @field_validator('min_claude_confidence')
    def validate_min_claude_confidence(cls, v):
        """Validate minimum Claude confidence threshold."""
        if not 0.0 <= v <= 100.0:
            raise ValueError('Minimum Claude confidence must be between 0.0 and 100.0')
        return v
    
    @field_validator('min_combined_score')
    def validate_min_combined_score(cls, v):
        """Validate minimum combined score threshold."""
        if not 0.0 <= v <= 100.0:
            raise ValueError('Minimum combined score must be between 0.0 and 100.0')
        return v
        
    @field_validator('traditional_pmcc_weight')
    def validate_traditional_pmcc_weight(cls, v):
        """Validate traditional PMCC weight."""
        if not 0.0 <= v <= 1.0:
            raise ValueError('Traditional PMCC weight must be between 0.0 and 1.0')
        return v
        
    @field_validator('ai_analysis_weight')
    def validate_ai_analysis_weight(cls, v):
        """Validate AI analysis weight."""
        if not 0.0 <= v <= 1.0:
            raise ValueError('AI analysis weight must be between 0.0 and 1.0')
        return v
    
    @model_validator(mode='after')
    def validate_scoring_weights_sum(self):
        """Ensure scoring weights sum to approximately 1.0."""
        weight_sum = self.traditional_pmcc_weight + self.ai_analysis_weight
        if not (0.99 <= weight_sum <= 1.01):  # Allow for small floating point precision errors
            raise ValueError(f'Traditional PMCC weight ({self.traditional_pmcc_weight}) and AI analysis weight ({self.ai_analysis_weight}) must sum to 1.0 (current sum: {weight_sum})')
        return self
    
    @model_validator(mode='after')
    def validate_export_settings(self):
        """Validate export configuration to ensure at least one format is enabled."""
        if self.export_results:
            # Check if we have at least one export format enabled
            has_json = self.export_format.lower() in ['json', 'both']
            has_csv = self.export_csv_enabled or self.export_format.lower() in ['csv', 'both']
            
            if not (has_json or has_csv):
                raise ValueError('At least one export format must be enabled when export_results is True')
        
        return self
    
    @property
    def should_export_json(self) -> bool:
        """Check if JSON export should be enabled."""
        return self.export_results and self.export_format.lower() in ['json', 'both']
    
    @property
    def should_export_csv(self) -> bool:
        """Check if CSV export should be enabled."""
        return (self.export_results and 
                (self.export_csv_enabled or self.export_format.lower() in ['csv', 'both']))
    
    @property
    def should_export_detailed_csv(self) -> bool:
        """Check if detailed CSV export should be enabled."""
        return self.should_export_csv and self.export_csv_detailed
    
    model_config = {"env_prefix": "SCAN_"}


class DatabaseConfig(BaseSettings):
    """Database configuration (for future use)."""
    
    enabled: bool = Field(False, description="Enable database storage")
    url: Optional[str] = Field(None, description="Database URL")
    max_connections: int = Field(10, description="Maximum database connections")
    connection_timeout: int = Field(30, description="Connection timeout in seconds")
    
    model_config = {"env_prefix": "DATABASE_"}


class LoggingConfig(BaseSettings):
    """Logging configuration."""
    
    level: LogLevel = Field(LogLevel.INFO, description="Default log level")
    format: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string"
    )
    
    # File logging
    enable_file_logging: bool = Field(True, description="Enable file logging")
    log_file: str = Field("logs/pmcc_scanner.log", description="Log file path")
    max_bytes: int = Field(10 * 1024 * 1024, description="Maximum log file size in bytes")
    backup_count: int = Field(5, description="Number of backup log files")
    
    # Console logging
    enable_console_logging: bool = Field(True, description="Enable console logging")
    console_level: LogLevel = Field(LogLevel.INFO, description="Console log level")
    
    # Structured logging
    enable_json_logging: bool = Field(False, description="Enable JSON structured logging")
    include_extra_fields: bool = Field(True, description="Include extra fields in logs")
    
    # External logging (for production)
    syslog_enabled: bool = Field(False, description="Enable syslog")
    syslog_host: Optional[str] = Field(None, description="Syslog host")
    syslog_port: int = Field(514, description="Syslog port")
    
    model_config = {"env_prefix": "LOG_"}


class MonitoringConfig(BaseSettings):
    """Monitoring and metrics configuration."""
    
    enabled: bool = Field(False, description="Enable monitoring")
    
    # Health checks
    health_check_enabled: bool = Field(True, description="Enable health checks")
    health_check_port: int = Field(8080, description="Health check HTTP port")
    health_check_path: str = Field("/health", description="Health check endpoint path")
    
    # Metrics
    metrics_enabled: bool = Field(False, description="Enable metrics collection")
    metrics_port: int = Field(9090, description="Metrics HTTP port")
    metrics_path: str = Field("/metrics", description="Metrics endpoint path")
    
    # Performance tracking
    track_performance: bool = Field(True, description="Track performance metrics")
    slow_query_threshold_seconds: float = Field(5.0, description="Slow query threshold")
    
    model_config = {"env_prefix": "MONITORING_"}


class Settings(BaseSettings):
    """Main application settings."""
    
    # Environment and basic settings
    environment: Environment = Field(Environment.DEVELOPMENT, description="Deployment environment")
    debug: bool = Field(False, description="Enable debug mode")
    app_name: str = Field("PMCC Scanner", description="Application name")
    app_version: str = Field("1.0.0", description="Application version")
    
    # Working directory
    working_dir: str = Field(".", description="Working directory for file operations")
    data_dir: str = Field("data", description="Data directory for scan results")
    temp_dir: str = Field("tmp", description="Temporary directory")
    
    # Component configurations - these will be instantiated in __init__
    marketdata: Optional[MarketDataConfig] = Field(default=None, description="MarketData.app API configuration (optional)")
    eodhd: Optional[EODHDConfig] = Field(default=None, description="EODHD API configuration (optional)")
    claude: Optional[ClaudeConfig] = Field(default=None, description="Claude AI API configuration (optional)")
    providers: DataProviderConfig = Field(default_factory=DataProviderConfig)
    notifications: NotificationConfig = Field(default_factory=NotificationConfig)
    scan: ScanConfig = Field(default_factory=ScanConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    
    # Development and feature flags
    reload_on_change: bool = Field(False, description="Reload on file changes (dev only)")
    enable_enhanced_providers: bool = Field(False, description="Enable enhanced provider implementations (AI-powered features)")
    
    @field_validator('environment', mode='before')
    def validate_environment(cls, v):
        """Validate and normalize environment."""
        if isinstance(v, str):
            try:
                return Environment(v.lower())
            except ValueError:
                raise ValueError(f'Invalid environment: {v}. Must be one of: {list(Environment)}')
        return v
    
    @model_validator(mode='after')
    def validate_environment_settings(self):
        """Apply environment-specific validation and defaults."""
        
        # Auto-detect and configure providers based on available API tokens
        self._configure_providers()
        
        # Validate provider configuration
        self._validate_provider_configuration()
        
        # Apply backward compatibility settings
        self._apply_backward_compatibility()
        
        # Production environment validation
        if self.environment == Environment.PRODUCTION:
            if self.debug:
                raise ValueError('Debug mode cannot be enabled in production')
            
            # Ensure secure settings for production
            if self.marketdata and not self.marketdata.base_url.startswith('https://'):
                raise ValueError('Production environment requires HTTPS for API calls')
            if self.eodhd and not self.eodhd.base_url.startswith('https://'):
                raise ValueError('Production environment requires HTTPS for API calls')
        
        # Development defaults
        elif self.environment == Environment.DEVELOPMENT:
            self.debug = True
            self.reload_on_change = True
        
        return self
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == Environment.DEVELOPMENT
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == Environment.PRODUCTION
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing mode."""
        return self.environment == Environment.TESTING
    
    # Backward compatibility properties for direct API token access
    @property
    def api_token(self) -> Optional[str]:
        """Get MarketData API token (backward compatibility)."""
        return self.marketdata.api_token if self.marketdata else None
    
    @property
    def eodhd_api_token(self) -> Optional[str]:
        """Get EODHD API token (backward compatibility)."""
        return self.eodhd.api_token if self.eodhd else None
    
    @property
    def claude_api_key(self) -> Optional[str]:
        """Get Claude API key (backward compatibility)."""
        return self.claude.api_key if self.claude else None
    
    # Backward compatibility properties for notification settings
    @property
    def whatsapp_enabled(self) -> bool:
        """Get WhatsApp enabled status (backward compatibility)."""
        return self.notifications.whatsapp_enabled
    
    @property
    def email_enabled(self) -> bool:
        """Get email enabled status (backward compatibility)."""
        return self.notifications.email_enabled
    
    def create_directories(self):
        """Create required directories if they don't exist."""
        directories = [
            self.working_dir,
            self.data_dir,
            self.temp_dir,
            os.path.dirname(self.logging.log_file) if self.logging.enable_file_logging else None
        ]
        
        for directory in directories:
            if directory:
                Path(directory).mkdir(parents=True, exist_ok=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary (for debugging)."""
        # Remove sensitive information
        sensitive_fields = [
            'marketdata.api_token',
            'eodhd.api_token',
            'claude.api_key',
            'notifications.twilio_auth_token',
            'notifications.mailgun_api_key',
            'notifications.sendgrid_api_key',
            'database.url'
        ]
        
        data = self.dict()
        
        # Mask sensitive fields
        for field_path in sensitive_fields:
            parts = field_path.split('.')
            current = data
            for part in parts[:-1]:
                if part in current:
                    current = current[part]
                else:
                    break
            else:
                if parts[-1] in current and current[parts[-1]]:
                    current[parts[-1]] = "***MASKED***"
        
        return data
    
    def get_available_providers(self) -> List[str]:
        """Get list of available (configured) providers."""
        providers = []
        if self.marketdata and self.marketdata.is_configured:
            providers.append("MarketData")
        if self.eodhd and self.eodhd.is_configured:
            providers.append("EODHD")
        if self.claude and self.claude.is_configured:
            providers.append("Claude")
        return providers
    
    def _configure_providers(self) -> None:
        """Configure providers based on available API tokens."""
        # Handle MarketData configuration
        marketdata_token = os.getenv('MARKETDATA_API_TOKEN', '').strip()
        if marketdata_token and marketdata_token != "your_marketdata_api_token_here":
            try:
                self.marketdata = MarketDataConfig()
                logging.info("MarketData.app provider configured")
            except Exception as e:
                logging.warning(f"Failed to create MarketData configuration: {e}")
                self.marketdata = None
        else:
            self.marketdata = None
        
        # Handle EODHD configuration
        eodhd_token = os.getenv('EODHD_API_TOKEN', '').strip()
        if eodhd_token and eodhd_token != "your_eodhd_api_token_here":
            try:
                self.eodhd = EODHDConfig()
                logging.info("EODHD provider configured")
            except Exception as e:
                logging.warning(f"Failed to create EODHD configuration: {e}")
                self.eodhd = None
        else:
            self.eodhd = None
        
        # Handle Claude configuration
        claude_key = os.getenv('CLAUDE_API_KEY', '').strip()
        if claude_key and claude_key != "your_claude_api_key_here":
            try:
                self.claude = ClaudeConfig()
                logging.info("Claude AI provider configured")
            except Exception as e:
                logging.warning(f"Failed to create Claude configuration: {e}")
                self.claude = None
        else:
            self.claude = None
    
    def _validate_provider_configuration(self) -> None:
        """Validate provider configuration and adjust settings as needed."""
        if self.providers.auto_detect_providers:
            # Auto-adjust provider preferences based on what's available
            available_providers = self.get_available_providers()
            
            if not available_providers:
                raise ValueError("No data providers configured. At least one API token (EODHD or MarketData) is required.")
            
            # Adjust primary provider if not available
            if self.providers.primary_provider.value not in [p.lower() for p in available_providers]:
                # Set primary to first available provider
                first_available = available_providers[0].lower()
                self.providers.primary_provider = DataProviderType(first_available)
                logging.warning(f"Primary provider adjusted to {first_available} (original not available)")
            
            # Adjust operation preferences based on capabilities
            if "eodhd" not in [p.lower() for p in available_providers]:
                # EODHD not available, need to adjust screener preference
                if self.providers.preferred_stock_screener == DataProviderType.EODHD:
                    logging.warning("EODHD not available but set as preferred screener. Stock screening may be limited.")
            
            if "marketdata" not in [p.lower() for p in available_providers]:
                # MarketData not available, adjust preferences to EODHD
                if self.providers.preferred_options_provider == DataProviderType.MARKETDATA:
                    self.providers.preferred_options_provider = DataProviderType.EODHD
                if self.providers.preferred_quotes_provider == DataProviderType.MARKETDATA:
                    self.providers.preferred_quotes_provider = DataProviderType.EODHD
                if self.providers.preferred_greeks_provider == DataProviderType.MARKETDATA:
                    self.providers.preferred_greeks_provider = DataProviderType.EODHD
                logging.info("MarketData not available, adjusted provider preferences to EODHD")
    
    def _apply_backward_compatibility(self) -> None:
        """Apply backward compatibility settings for legacy configurations."""
        # Check if user is using legacy provider mode based on existing settings
        if (hasattr(self.scan, 'options_source') and 
            self.scan.options_source in ['eodhd', 'marketdata'] and
            self.providers.provider_mode == ProviderMode.FACTORY):
            
            # Auto-detect if user wants legacy mode based on single provider setup
            available_providers = self.get_available_providers()
            if len(available_providers) == 1:
                # Only one provider available, suggest legacy mode might be preferred
                logging.info(f"Single provider ({available_providers[0]}) detected. Provider factory mode enabled with single provider.")
    
    def get_provider_mode_recommendation(self) -> Tuple[ProviderMode, str]:
        """Get recommended provider mode based on available providers and configuration."""
        available_providers = self.get_available_providers()
        
        if len(available_providers) == 0:
            return ProviderMode.LEGACY, "No providers configured"
        elif len(available_providers) == 1:
            provider = available_providers[0].lower()
            return ProviderMode.LEGACY, f"Single provider ({provider}) - legacy mode sufficient"
        else:
            return ProviderMode.FACTORY, "Multiple providers available - factory mode recommended for optimal performance"
    
    def validate_provider_configuration(self) -> List[str]:
        """
        Validate provider configuration and return list of issues.
        
        Returns:
            List of validation error/warning messages
        """
        issues = []
        
        # Check if at least one provider is configured
        available_providers = self.get_available_providers()
        if not available_providers:
            issues.append("CRITICAL: No data providers configured - need at least one API token (EODHD or MarketData)")
            return issues  # Can't continue validation without providers
        
        # Check provider mode compatibility
        if self.providers.provider_mode == ProviderMode.FACTORY and len(available_providers) == 1:
            provider = available_providers[0]
            issues.append(f"INFO: Factory mode with single provider ({provider}) - consider legacy mode for simplicity")
        
        # Check primary provider availability
        if self.providers.primary_provider.value.upper() not in [p.upper() for p in available_providers]:
            issues.append(f"WARNING: Primary provider ({self.providers.primary_provider.value}) not configured - will auto-adjust to available provider")
        
        # Check operation preferences vs capabilities
        provider_lower = [p.lower() for p in available_providers]
        
        # Stock screening validation
        if (self.providers.preferred_stock_screener == DataProviderType.MARKETDATA and 
            "marketdata" in provider_lower):
            issues.append("WARNING: MarketData selected for stock screening but doesn't support screening - EODHD required")
        
        if (self.providers.preferred_stock_screener == DataProviderType.EODHD and 
            "eodhd" not in provider_lower):
            issues.append("ERROR: EODHD selected for stock screening but not configured - stock screening will fail")
        
        # Options provider validation
        if (self.providers.preferred_options_provider.value.lower() not in provider_lower):
            issues.append(f"WARNING: Preferred options provider ({self.providers.preferred_options_provider.value}) not configured")
        
        # Check for optimal configuration recommendations
        if len(available_providers) == 2:
            issues.append("INFO: Both providers configured - optimal setup for performance and redundancy")
        elif "eodhd" in provider_lower and "marketdata" not in provider_lower:
            issues.append("INFO: Only EODHD configured - consider adding MarketData for better options performance")
        elif "marketdata" in provider_lower and "eodhd" not in provider_lower:
            issues.append("INFO: Only MarketData configured - stock screening capabilities limited")
        
        # Validate fallback strategy
        if (self.providers.fallback_strategy != FallbackStrategy.NONE and 
            len(available_providers) == 1):
            issues.append("INFO: Fallback strategy configured but only one provider available")
        
        return issues
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get comprehensive configuration summary for debugging and validation."""
        available_providers = self.get_available_providers()
        mode_recommendation = self.get_provider_mode_recommendation()
        validation_issues = self.validate_provider_configuration()
        
        return {
            "environment": self.environment.value,
            "debug_mode": self.debug,
            "provider_configuration": {
                "mode": self.providers.provider_mode.value,
                "available_providers": available_providers,
                "primary_provider": self.providers.primary_provider.value,
                "fallback_strategy": self.providers.fallback_strategy.value,
                "auto_detect_enabled": self.providers.auto_detect_providers,
                "health_checks_enabled": self.providers.enable_health_checks,
            },
            "operation_routing": {
                "stock_screener": self.providers.preferred_stock_screener.value,
                "options_provider": self.providers.preferred_options_provider.value,
                "quotes_provider": self.providers.preferred_quotes_provider.value,
                "greeks_provider": self.providers.preferred_greeks_provider.value,
            },
            "provider_status": {
                "eodhd_configured": self.eodhd is not None and self.eodhd.is_configured if self.eodhd else False,
                "marketdata_configured": self.marketdata is not None and self.marketdata.is_configured if self.marketdata else False,
            },
            "notifications": {
                "whatsapp_configured": self.notifications.is_whatsapp_configured,
                "email_configured": self.notifications.is_email_configured,
                "channels_enabled": {
                    "whatsapp": self.notifications.whatsapp_enabled,
                    "email": self.notifications.email_enabled,
                }
            },
            "recommendations": {
                "provider_mode": mode_recommendation[0].value,
                "reason": mode_recommendation[1],
            },
            "validation_issues": validation_issues,
        }
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"
    }


def load_settings(env_file: Optional[str] = None) -> Settings:
    """
    Load application settings from environment variables and .env file.
    
    Args:
        env_file: Optional path to .env file
        
    Returns:
        Configured Settings instance
        
    Raises:
        ValueError: If configuration is invalid
        FileNotFoundError: If required configuration files are missing
    """
    # Load environment variables from .env file
    if env_file:
        if not os.path.exists(env_file):
            raise FileNotFoundError(f"Environment file not found: {env_file}")
        load_dotenv(env_file, override=True)
    else:
        # Try to load from default locations
        for possible_env_file in [".env", ".env.local", f".env.{os.getenv('ENVIRONMENT', 'development')}"]:
            if os.path.exists(possible_env_file):
                load_dotenv(possible_env_file, override=False)
    
    try:
        # Load and validate settings
        settings = Settings()
        
        # Create required directories
        settings.create_directories()
        
        return settings
        
    except Exception as e:
        print(f"Error loading settings: {e}")
        print("\nPlease check your environment variables and .env file configuration.")
        print("Required environment variables:")
        print("- At least one API token: MARKETDATA_API_TOKEN or EODHD_API_TOKEN")
        print("- MARKETDATA_API_TOKEN: Your MarketData.app API token (optional)")
        print("- EODHD_API_TOKEN: Your EODHD API token (optional)")
        print("- NOTIFICATION_*: Notification service configuration")
        print("\nProvider Configuration:")
        print("- PROVIDER_MODE: legacy, factory, or hybrid (default: factory)")
        print("- PROVIDER_PRIMARY_PROVIDER: eodhd or marketdata (default: eodhd)")
        print("- PROVIDER_FALLBACK_STRATEGY: none, round_robin, operation_specific, or primary_secondary")
        raise


def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Returns:
        Settings instance
    """
    if not hasattr(get_settings, '_cached_settings'):
        get_settings._cached_settings = load_settings()
    
    return get_settings._cached_settings


def reload_settings() -> Settings:
    """
    Reload settings (clears cache).
    
    Returns:
        Fresh Settings instance
    """
    if hasattr(get_settings, '_cached_settings'):
        delattr(get_settings, '_cached_settings')
    
    return get_settings()


# Create default settings instance for easy importing
try:
    settings = get_settings()
except Exception:
    # Allow import even if settings are not properly configured
    # This helps with testing and development
    settings = None


if __name__ == "__main__":
    """CLI for configuration management."""
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="PMCC Scanner Configuration")
    parser.add_argument("--validate", action="store_true", help="Validate configuration")
    parser.add_argument("--show", action="store_true", help="Show current configuration")
    parser.add_argument("--env-file", help="Path to .env file")
    
    args = parser.parse_args()
    
    try:
        settings = load_settings(args.env_file)
        
        if args.validate:
            print("✓ Configuration loaded successfully")
            print(f"Environment: {settings.environment.value}")
            print(f"Debug mode: {settings.debug}")
            
            # Validate provider configuration
            validation_issues = settings.validate_provider_configuration()
            if validation_issues:
                print("\nProvider Configuration Issues:")
                for issue in validation_issues:
                    level = issue.split(":")[0]
                    if level == "CRITICAL":
                        print(f"❌ {issue}")
                    elif level == "ERROR":
                        print(f"⚠️  {issue}")
                    elif level == "WARNING":
                        print(f"⚠️  {issue}")
                    else:
                        print(f"ℹ️  {issue}")
            else:
                print("✓ Provider configuration is valid")
            
            # Show provider mode recommendation
            mode_rec, reason = settings.get_provider_mode_recommendation()
            print(f"\nRecommended provider mode: {mode_rec.value}")
            print(f"Reason: {reason}")
            
        if args.show:
            print("\nCurrent Configuration:")
            print(json.dumps(settings.to_dict(), indent=2, default=str))
            
            print("\nConfiguration Summary:")
            summary = settings.get_configuration_summary()
            print(json.dumps(summary, indent=2, default=str))
            
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        sys.exit(1)