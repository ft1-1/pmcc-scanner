"""
Provider-specific configuration for data providers in the PMCC Scanner.

This module defines configuration classes and settings for each supported data provider
(EODHD, MarketData.app) and manages provider selection and fallback strategies.

Key features:
- Provider-specific settings and capabilities
- Operation routing preferences
- Rate limiting and quota management
- Fallback and health check configuration
- Environment-specific provider selection
"""

import os
from typing import Dict, List, Optional, Any, Type, Union
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
import logging

try:
    from pydantic import Field, field_validator
    from pydantic_settings import BaseSettings
except ImportError:
    # Fallback for environments without pydantic
    BaseSettings = object
    Field = lambda *args, **kwargs: None
    field_validator = lambda *args, **kwargs: lambda func: func

from src.api.data_provider import ProviderType, DataProvider, SyncDataProvider, ProviderHealth, ProviderStatus
from src.api.provider_factory import FallbackStrategy, ProviderConfig

logger = logging.getLogger(__name__)


class ProviderPriority(Enum):
    """Provider priority levels."""
    PRIMARY = 100
    SECONDARY = 50
    FALLBACK = 10
    DISABLED = 0


@dataclass
class ProviderCapabilities:
    """Capabilities and limitations of a data provider."""
    
    # Core operations
    supports_stock_quotes: bool = True
    supports_batch_quotes: bool = False
    supports_options_chains: bool = True
    supports_stock_screening: bool = False
    supports_greeks: bool = True
    supports_real_time_data: bool = False
    
    # Data quality and coverage
    max_symbols_per_request: int = 1
    max_options_per_chain: int = 1000
    historical_data_years: int = 10
    supports_extended_hours: bool = False
    
    # Rate limiting
    requests_per_second: int = 1
    requests_per_minute: int = 60
    requests_per_hour: int = 3600
    requests_per_day: int = 100000
    credits_per_stock_quote: int = 1
    credits_per_options_chain: int = 1
    credits_per_screening_request: int = 5
    
    # Latency and reliability
    typical_latency_ms: int = 500
    uptime_percentage: float = 99.0
    data_freshness_minutes: int = 15


class EODHDProviderConfig(BaseSettings):
    """Configuration for EODHD data provider."""
    
    # Authentication
    api_token: str = Field(..., description="EODHD API token")
    
    # API endpoints
    base_url: str = Field("https://eodhd.com/api", description="EODHD API base URL")
    screener_endpoint: str = Field("/screener", description="Screener API endpoint")
    eod_endpoint: str = Field("/eod", description="End-of-day data endpoint")
    options_endpoint: str = Field("/options", description="Options data endpoint")
    
    # Request settings
    timeout_seconds: int = Field(30, description="Request timeout")
    max_retries: int = Field(3, description="Maximum retry attempts")
    retry_backoff_factor: float = Field(2.0, description="Exponential backoff factor")
    
    # Rate limiting (EODHD-specific)
    screener_credits_per_request: int = Field(5, description="API credits per screener request")
    max_screener_requests_per_day: int = Field(2000, description="Daily screener request limit")
    options_credits_per_request: int = Field(1, description="API credits per options request")
    
    # Screening configuration
    default_screening_limit: int = Field(1000, description="Default screening result limit")
    max_market_cap_filter: Decimal = Field(Decimal('5000000000'), description="Max market cap filter (5B)")
    min_market_cap_filter: Decimal = Field(Decimal('50000000'), description="Min market cap filter (50M)")
    
    # Options configuration
    comprehensive_pmcc_batch_size: int = Field(10, description="Batch size for comprehensive PMCC requests")
    max_option_chains_per_batch: int = Field(5, description="Max option chains per batch")
    option_expiration_range_days: int = Field(730, description="Default option expiration range (2 years)")
    
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
    
    def get_capabilities(self) -> ProviderCapabilities:
        """Get EODHD provider capabilities."""
        return ProviderCapabilities(
            supports_stock_quotes=True,
            supports_batch_quotes=False,
            supports_options_chains=True,
            supports_stock_screening=True,  # EODHD's key strength
            supports_greeks=True,
            supports_real_time_data=False,
            
            max_symbols_per_request=1,
            max_options_per_chain=5000,
            historical_data_years=20,
            supports_extended_hours=False,
            
            requests_per_second=2,
            requests_per_minute=60,
            requests_per_hour=3600,
            requests_per_day=100000,
            credits_per_stock_quote=1,
            credits_per_options_chain=1,
            credits_per_screening_request=5,
            
            typical_latency_ms=800,
            uptime_percentage=99.5,
            data_freshness_minutes=60  # End-of-day data
        )
    
    model_config = {"env_prefix": "EODHD_"}


class MarketDataProviderConfig(BaseSettings):
    """Configuration for MarketData.app data provider."""
    
    # Authentication
    api_token: str = Field(..., description="MarketData.app API token")
    
    # API endpoints
    base_url: str = Field("https://api.marketdata.app", description="MarketData.app API base URL")
    stocks_endpoint: str = Field("/v1/stocks", description="Stocks API endpoint")
    options_endpoint: str = Field("/v1/options", description="Options API endpoint")
    
    # Request settings
    timeout_seconds: int = Field(30, description="Request timeout")
    max_retries: int = Field(3, description="Maximum retry attempts")
    retry_backoff_factor: float = Field(2.0, description="Exponential backoff factor")
    
    # Rate limiting
    requests_per_minute: int = Field(100, description="Requests per minute limit")
    requests_per_day: int = Field(100000, description="Daily request limit")
    
    # Batch processing
    max_symbols_per_batch: int = Field(50, description="Maximum symbols per batch request")
    batch_processing_enabled: bool = Field(True, description="Enable batch processing")
    
    # Options configuration
    options_chain_credits: int = Field(1, description="Credits per options chain (full chain)")
    support_real_time_greeks: bool = Field(True, description="Supports real-time Greeks")
    default_expiration_range_days: int = Field(365, description="Default expiration range")
    
    @field_validator('api_token')
    def api_token_must_not_be_empty(cls, v):
        if not v or v.strip() == "":
            raise ValueError('MarketData.app API token cannot be empty')
        return v.strip()
    
    @field_validator('base_url')
    def base_url_must_be_valid(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('Base URL must start with http:// or https://')
        return v.rstrip('/')
    
    def get_capabilities(self) -> ProviderCapabilities:
        """Get MarketData.app provider capabilities."""
        return ProviderCapabilities(
            supports_stock_quotes=True,
            supports_batch_quotes=True,  # MarketData.app's key strength
            supports_options_chains=True,
            supports_stock_screening=False,  # No screener API
            supports_greeks=True,
            supports_real_time_data=True,
            
            max_symbols_per_request=50,
            max_options_per_chain=10000,
            historical_data_years=10,
            supports_extended_hours=True,
            
            requests_per_second=5,
            requests_per_minute=100,
            requests_per_hour=6000,
            requests_per_day=100000,
            credits_per_stock_quote=1,
            credits_per_options_chain=1,  # Full chain for 1 credit
            credits_per_screening_request=0,  # Not supported
            
            typical_latency_ms=200,
            uptime_percentage=99.9,
            data_freshness_minutes=1  # Near real-time
        )
    
    model_config = {"env_prefix": "MARKETDATA_"}


@dataclass
class DataProviderSettings:
    """Overall data provider settings for the PMCC Scanner."""
    
    # Primary strategy
    primary_provider: ProviderType = ProviderType.EODHD
    fallback_strategy: FallbackStrategy = FallbackStrategy.OPERATION_SPECIFIC
    
    # Operation routing preferences
    preferred_stock_screener: ProviderType = ProviderType.EODHD
    preferred_options_provider: ProviderType = ProviderType.MARKETDATA
    preferred_quotes_provider: ProviderType = ProviderType.MARKETDATA
    preferred_greeks_provider: ProviderType = ProviderType.MARKETDATA
    
    # Health monitoring
    health_check_interval_seconds: int = 300  # 5 minutes
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout_seconds: int = 600  # 10 minutes
    
    # Performance settings
    max_concurrent_requests_per_provider: int = 10
    request_timeout_seconds: int = 30
    enable_response_caching: bool = True
    cache_ttl_seconds: int = 300
    
    # Cost optimization
    prioritize_cost_efficiency: bool = True
    max_daily_api_credits: int = 10000
    alert_threshold_credits_remaining: int = 1000


class ProviderConfigurationManager:
    """
    Manages provider configurations and creates provider instances.
    
    This class handles:
    - Loading provider configurations from environment
    - Creating provider instances with proper configuration
    - Setting up operation routing preferences
    - Managing provider priorities and capabilities
    """
    
    def __init__(self, settings: Optional[DataProviderSettings] = None):
        """
        Initialize the provider configuration manager.
        
        Args:
            settings: Data provider settings (uses defaults if not provided)
        """
        self.settings = settings or DataProviderSettings()
        self.eodhd_config: Optional[EODHDProviderConfig] = None
        self.marketdata_config: Optional[MarketDataProviderConfig] = None
        
        # Load configurations
        self._load_configurations()
    
    def _load_configurations(self) -> None:
        """Load provider configurations from environment."""
        try:
            # Try to load EODHD configuration
            if os.getenv('EODHD_API_TOKEN'):
                self.eodhd_config = EODHDProviderConfig()
                logger.info("Loaded EODHD provider configuration")
            else:
                logger.warning("EODHD API token not found in environment")
        except Exception as e:
            logger.error(f"Failed to load EODHD configuration: {e}")
        
        try:
            # Try to load MarketData.app configuration
            if os.getenv('MARKETDATA_API_TOKEN'):
                self.marketdata_config = MarketDataProviderConfig()
                logger.info("Loaded MarketData.app provider configuration")
            else:
                logger.warning("MarketData.app API token not found in environment")
        except Exception as e:
            logger.error(f"Failed to load MarketData.app configuration: {e}")
    
    def get_provider_configs(self) -> List[ProviderConfig]:
        """
        Get list of provider configurations for the factory.
        
        Returns:
            List of ProviderConfig objects for available providers
        """
        configs = []
        
        # EODHD Provider Configuration
        if self.eodhd_config:
            # Import here to avoid circular imports
            try:
                # Use the actual sync provider implementation
                from src.api.providers.sync_eodhd_provider import SyncEODHDProvider
                
                configs.append(ProviderConfig(
                    provider_type=ProviderType.EODHD,
                    provider_class=SyncEODHDProvider,
                    config=self._get_eodhd_config_dict(),
                    priority=self._get_provider_priority(ProviderType.EODHD),
                    max_concurrent_requests=self.settings.max_concurrent_requests_per_provider,
                    timeout_seconds=self.eodhd_config.timeout_seconds,
                    preferred_operations=self._get_preferred_operations(ProviderType.EODHD),
                    supported_operations=[
                        "get_stock_quote", "get_stock_quotes", "get_options_chain",
                        "screen_stocks", "get_greeks"
                    ]
                ))
            except ImportError:
                logger.error("EODHDClient not available")
        
        # MarketData.app Provider Configuration
        if self.marketdata_config:
            try:
                # Use the actual sync provider implementation
                from src.api.providers.sync_marketdata_provider import SyncMarketDataProvider
                
                configs.append(ProviderConfig(
                    provider_type=ProviderType.MARKETDATA,
                    provider_class=SyncMarketDataProvider,
                    config=self._get_marketdata_config_dict(),
                    priority=self._get_provider_priority(ProviderType.MARKETDATA),
                    max_concurrent_requests=self.settings.max_concurrent_requests_per_provider,
                    timeout_seconds=self.marketdata_config.timeout_seconds,
                    preferred_operations=self._get_preferred_operations(ProviderType.MARKETDATA),
                    supported_operations=[
                        "get_stock_quote", "get_stock_quotes", "get_options_chain", "get_greeks"
                        # Note: MarketData.app doesn't support stock screening
                    ]
                ))
            except ImportError:
                logger.error("SyncMarketDataClient not available")
        
        return configs
    
    def _get_eodhd_config_dict(self) -> Dict[str, Any]:
        """Get EODHD configuration as dictionary."""
        if not self.eodhd_config:
            return {}
        
        return {
            "api_token": self.eodhd_config.api_token,
            "base_url": self.eodhd_config.base_url,
            "timeout_seconds": self.eodhd_config.timeout_seconds,
            "max_retries": self.eodhd_config.max_retries,
            "retry_backoff_factor": self.eodhd_config.retry_backoff_factor,
            "screener_credits_per_request": self.eodhd_config.screener_credits_per_request,
            "comprehensive_pmcc_batch_size": self.eodhd_config.comprehensive_pmcc_batch_size,
            "capabilities": self.eodhd_config.get_capabilities()
        }
    
    def _get_marketdata_config_dict(self) -> Dict[str, Any]:
        """Get MarketData.app configuration as dictionary."""
        if not self.marketdata_config:
            return {}
        
        return {
            "api_token": self.marketdata_config.api_token,
            "base_url": self.marketdata_config.base_url,
            "timeout_seconds": self.marketdata_config.timeout_seconds,
            "max_retries": self.marketdata_config.max_retries,
            "retry_backoff_factor": self.marketdata_config.retry_backoff_factor,
            "max_symbols_per_batch": self.marketdata_config.max_symbols_per_batch,
            "batch_processing_enabled": self.marketdata_config.batch_processing_enabled,
            "capabilities": self.marketdata_config.get_capabilities()
        }
    
    def _get_provider_priority(self, provider_type: ProviderType) -> int:
        """Get priority for a provider type."""
        if provider_type == self.settings.primary_provider:
            return ProviderPriority.PRIMARY.value
        else:
            return ProviderPriority.SECONDARY.value
    
    def _get_preferred_operations(self, provider_type: ProviderType) -> List[str]:
        """Get list of operations this provider is preferred for."""
        preferred = []
        
        if provider_type == self.settings.preferred_stock_screener:
            preferred.append("screen_stocks")
        
        if provider_type == self.settings.preferred_options_provider:
            preferred.append("get_options_chain")
        
        if provider_type == self.settings.preferred_quotes_provider:
            preferred.extend(["get_stock_quote", "get_stock_quotes"])
        
        if provider_type == self.settings.preferred_greeks_provider:
            preferred.append("get_greeks")
        
        return preferred
    
    def get_provider_summary(self) -> Dict[str, Any]:
        """Get summary of available providers and their configurations."""
        summary = {
            "settings": {
                "primary_provider": self.settings.primary_provider.value,
                "fallback_strategy": self.settings.fallback_strategy.value,
                "health_check_interval": self.settings.health_check_interval_seconds,
                "max_concurrent_requests": self.settings.max_concurrent_requests_per_provider
            },
            "routing_preferences": {
                "stock_screener": self.settings.preferred_stock_screener.value,
                "options_provider": self.settings.preferred_options_provider.value,
                "quotes_provider": self.settings.preferred_quotes_provider.value,
                "greeks_provider": self.settings.preferred_greeks_provider.value
            },
            "providers": {}
        }
        
        # Add EODHD info
        if self.eodhd_config:
            capabilities = self.eodhd_config.get_capabilities()
            summary["providers"]["eodhd"] = {
                "available": True,
                "base_url": self.eodhd_config.base_url,
                "supports_screening": capabilities.supports_stock_screening,
                "supports_options": capabilities.supports_options_chains,
                "supports_batch_quotes": capabilities.supports_batch_quotes,
                "typical_latency_ms": capabilities.typical_latency_ms,
                "credits_per_screening": capabilities.credits_per_screening_request
            }
        else:
            summary["providers"]["eodhd"] = {"available": False, "reason": "No API token configured"}
        
        # Add MarketData.app info
        if self.marketdata_config:
            capabilities = self.marketdata_config.get_capabilities()
            summary["providers"]["marketdata"] = {
                "available": True,
                "base_url": self.marketdata_config.base_url,
                "supports_screening": capabilities.supports_stock_screening,
                "supports_options": capabilities.supports_options_chains,
                "supports_batch_quotes": capabilities.supports_batch_quotes,
                "max_symbols_per_batch": capabilities.max_symbols_per_request,
                "typical_latency_ms": capabilities.typical_latency_ms,
                "supports_real_time": capabilities.supports_real_time_data
            }
        else:
            summary["providers"]["marketdata"] = {"available": False, "reason": "No API token configured"}
        
        return summary
    
    def validate_configuration(self) -> List[str]:
        """
        Validate provider configurations and return list of issues.
        
        Returns:
            List of validation error messages
        """
        issues = []
        
        # Check if at least one provider is configured
        if not self.eodhd_config and not self.marketdata_config:
            issues.append("No data providers configured - need at least one API token")
        
        # Check if preferred providers are available
        if self.settings.preferred_stock_screener == ProviderType.EODHD and not self.eodhd_config:
            issues.append("Preferred stock screener (EODHD) is not configured")
        
        if self.settings.preferred_options_provider == ProviderType.MARKETDATA and not self.marketdata_config:
            issues.append("Preferred options provider (MarketData.app) is not configured")
        
        # Check for conflicting settings
        if (self.settings.preferred_stock_screener == ProviderType.MARKETDATA and 
            self.marketdata_config and 
            not self.marketdata_config.get_capabilities().supports_stock_screening):
            issues.append("MarketData.app does not support stock screening but is set as preferred screener")
        
        return issues