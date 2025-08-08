"""
Abstract base class for data providers in the PMCC Scanner.

This module defines the common interface that all data providers (EODHD, MarketData.app, etc.)
must implement. It ensures consistent behavior across different data sources and enables
easy switching between providers with automatic fallback support.

Key features:
- Standardized interface for all market data operations
- Consistent error handling and retry mechanisms
- Provider health monitoring and status tracking
- Rate limiting awareness and credit management
- Support for both sync and async operations
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Union, TYPE_CHECKING
from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
import logging

if TYPE_CHECKING:
    from typing import Generic, TypeVar
    T = TypeVar('T')
else:
    # For runtime compatibility with Python < 3.9
    Generic = object
    T = Any

from src.models.api_models import (
    StockQuote, OptionChain, OptionContract, EODHDScreenerResponse,
    APIResponse, APIError, APIStatus, RateLimitHeaders
)

logger = logging.getLogger(__name__)


class ProviderType(Enum):
    """Supported data provider types."""
    EODHD = "eodhd"
    MARKETDATA = "marketdata"
    CLAUDE = "claude"
    

class ProviderStatus(Enum):
    """Provider operational status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"  # Working but with issues (high latency, rate limits)
    UNHEALTHY = "unhealthy"  # Not working
    MAINTENANCE = "maintenance"  # Provider in maintenance mode


@dataclass
class ProviderHealth:
    """Provider health status information."""
    status: ProviderStatus
    last_check: datetime
    latency_ms: Optional[float] = None
    success_rate: Optional[float] = None  # Last 100 requests
    rate_limit_remaining: Optional[int] = None
    rate_limit_reset: Optional[datetime] = None
    error_message: Optional[str] = None
    

@dataclass
class ScreeningCriteria:
    """Stock screening criteria for filtering stocks."""
    
    # Market cap filters (in USD)
    min_market_cap: Optional[Decimal] = None
    max_market_cap: Optional[Decimal] = None
    
    # Price filters
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    
    # Volume filters
    min_volume: Optional[int] = None
    min_avg_volume: Optional[int] = None  # Average daily volume
    
    # Exchange filters
    exchanges: Optional[List[str]] = None  # e.g., ["NYSE", "NASDAQ"]
    
    # Sector/Industry filters
    sectors: Optional[List[str]] = None
    industries: Optional[List[str]] = None
    
    # Financial metrics
    min_earnings_per_share: Optional[Decimal] = None
    max_dividend_yield: Optional[Decimal] = None
    
    # Options-specific filters
    has_options: bool = True
    has_weekly_options: Optional[bool] = None
    min_option_volume: Optional[int] = None
    
    # Result limit
    limit: Optional[int] = None  # Maximum number of results to return
    
    # Additional filters
    exclude_etfs: bool = True
    exclude_penny_stocks: bool = True
    exclude_recent_ipos: Optional[int] = None  # Days since IPO
    
    def to_eodhd_filters(self) -> Dict[str, Any]:
        """Convert criteria to EODHD screener API filters."""
        filters = []
        
        if self.min_market_cap:
            filters.append(f"market_capitalization::gte::{self.min_market_cap}")
        if self.max_market_cap:
            filters.append(f"market_capitalization::lte::{self.max_market_cap}")
        if self.min_price:
            filters.append(f"close::gte::{self.min_price}")
        if self.max_price:
            filters.append(f"close::lte::{self.max_price}")
        if self.min_volume:
            filters.append(f"volume::gte::{self.min_volume}")
        if self.exchanges:
            # EODHD uses exchange codes
            exchanges_str = ",".join(self.exchanges)
            filters.append(f"exchange::{exchanges_str}")
        
        return {
            "filters": filters,
            "sort": "market_capitalization.desc",
            "limit": 1000  # EODHD default
        }
    
    def to_marketdata_params(self) -> Dict[str, Any]:
        """Convert criteria to MarketData.app API parameters."""
        # MarketData.app doesn't have a screener API
        # This would be used if they add one in the future
        return {
            "min_price": self.min_price,
            "max_price": self.max_price,
            "min_volume": self.min_volume
        }


class DataProvider(ABC):
    """
    Abstract base class for all data providers.
    
    This class defines the standard interface that all data providers must implement
    to ensure consistent behavior across different data sources.
    """
    
    def __init__(self, provider_type: ProviderType, config: Dict[str, Any]):
        """
        Initialize the data provider.
        
        Args:
            provider_type: Type of provider (EODHD, MarketData.app, etc.)
            config: Provider-specific configuration dictionary
        """
        self.provider_type = provider_type
        self.config = config
        self._health = ProviderHealth(
            status=ProviderStatus.HEALTHY,
            last_check=datetime.now()
        )
        
    @property
    def health(self) -> ProviderHealth:
        """Get current provider health status."""
        return self._health
    
    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        """
        Perform a health check on the provider.
        
        Returns:
            ProviderHealth object with current status
        """
        pass
    
    @abstractmethod
    async def get_stock_quote(self, symbol: str) -> APIResponse:
        """
        Get real-time or delayed stock quote.
        
        Args:
            symbol: Stock symbol (e.g., "AAPL")
            
        Returns:
            APIResponse containing StockQuote data or error
        """
        pass
    
    @abstractmethod
    async def get_stock_quotes(self, symbols: List[str]) -> APIResponse:
        """
        Get multiple stock quotes in a single request.
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            APIResponse containing list of StockQuote data or error
        """
        pass
    
    async def get_options_chain(
        self, 
        symbol: str, 
        expiration_from: Optional[date] = None,
        expiration_to: Optional[date] = None
    ) -> APIResponse:
        """
        Get options chain for a stock.
        
        Default implementation for providers that don't support options.
        Override in providers that support options (e.g., MarketData.app).
        
        Args:
            symbol: Stock symbol
            expiration_from: Minimum expiration date (optional)
            expiration_to: Maximum expiration date (optional)
            
        Returns:
            APIResponse containing OptionChain data or error
        """
        return self._create_error_response(
            f"Provider {self.provider_type.value} does not support options data"
        )
    
    @abstractmethod
    async def screen_stocks(self, criteria: ScreeningCriteria) -> APIResponse:
        """
        Screen stocks based on specified criteria.
        
        Args:
            criteria: Screening criteria (market cap, price, volume, etc.)
            
        Returns:
            APIResponse containing screening results or error
        """
        pass
    
    async def get_greeks(self, option_symbol: str) -> APIResponse:
        """
        Get Greeks and analytics for a specific option contract.
        
        Default implementation for providers that don't support options.
        Override in providers that support options (e.g., MarketData.app).
        
        Args:
            option_symbol: Option contract symbol
            
        Returns:
            APIResponse containing option contract with Greeks or error
        """
        return self._create_error_response(
            f"Provider {self.provider_type.value} does not support options data"
        )
    
    # Rate limiting and quota management
    @abstractmethod
    def get_rate_limit_info(self) -> Optional[RateLimitHeaders]:
        """
        Get current rate limit status.
        
        Returns:
            RateLimitHeaders object or None if not available
        """
        pass
    
    @abstractmethod
    def estimate_credits_required(self, operation: str, **kwargs) -> int:
        """
        Estimate API credits required for an operation.
        
        Args:
            operation: Type of operation ('quote', 'options_chain', 'screen', etc.)
            **kwargs: Operation-specific parameters
            
        Returns:
            Estimated number of API credits required
        """
        pass
    
    # Provider-specific capabilities
    @abstractmethod
    def supports_operation(self, operation: str) -> bool:
        """
        Check if provider supports a specific operation.
        
        Args:
            operation: Operation name ('screen_stocks', 'get_greeks', etc.)
            
        Returns:
            True if operation is supported
        """
        pass
    
    # Enhanced data operations (optional - not all providers may implement these)
    
    async def get_fundamental_data(self, symbol: str) -> APIResponse:
        """
        Get comprehensive fundamental data for a stock.
        
        This is an optional enhanced operation. Providers that don't support
        enhanced data should return an error indicating the operation is not supported.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            APIResponse containing FundamentalMetrics data or error
        """
        return self._create_error_response("Enhanced fundamental data not supported by this provider")
    
    async def get_calendar_events(
        self, 
        symbol: str, 
        event_types: Optional[List[str]] = None,
        date_from: Optional['date'] = None,
        date_to: Optional['date'] = None
    ) -> APIResponse:
        """
        Get calendar events (earnings, dividends) for a stock.
        
        This is an optional enhanced operation.
        
        Args:
            symbol: Stock symbol
            event_types: Types of events to fetch ('earnings', 'dividends')
            date_from: Start date for events
            date_to: End date for events
            
        Returns:
            APIResponse containing list of CalendarEvent data or error
        """
        return self._create_error_response("Enhanced calendar data not supported by this provider")
    
    async def get_technical_indicators(self, symbol: str) -> APIResponse:
        """
        Get technical indicators for a stock.
        
        This is an optional enhanced operation.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            APIResponse containing TechnicalIndicators data or error
        """
        return self._create_error_response("Enhanced technical indicators not supported by this provider")
    
    async def get_risk_metrics(self, symbol: str) -> APIResponse:
        """
        Get risk assessment metrics for a stock.
        
        This is an optional enhanced operation.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            APIResponse containing RiskMetrics data or error
        """
        return self._create_error_response("Enhanced risk metrics not supported by this provider")
    
    async def get_enhanced_stock_data(self, symbol: str) -> APIResponse:
        """
        Get comprehensive enhanced stock data combining all available data sources.
        
        This is an optional enhanced operation that combines quote, fundamental,
        calendar, technical, and risk data into a single comprehensive response.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            APIResponse containing EnhancedStockData with all available data
        """
        return self._create_error_response("Enhanced stock data not supported by this provider")
    
    def get_provider_info(self) -> Dict[str, Any]:
        """
        Get provider information and capabilities.
        
        Returns:
            Dictionary containing provider metadata
        """
        return {
            "type": self.provider_type.value,
            "name": self.__class__.__name__,
            "health": self.health,
            "supports_screening": self.supports_operation("screen_stocks"),
            "supports_greeks": self.supports_operation("get_greeks"),
            "supports_batch_quotes": self.supports_operation("get_stock_quotes"),
            "rate_limit": self.get_rate_limit_info()
        }
    
    # Error handling utilities
    def _create_error_response(self, message: str, code: Optional[int] = None) -> APIResponse:
        """Create a standardized error response."""
        return APIResponse(
            status=APIStatus.ERROR,
            error=APIError(
                code=code or 500,
                message=message
            )
        )
    
    def _create_success_response(self, data: Any) -> APIResponse:
        """Create a standardized success response."""
        return APIResponse(
            status=APIStatus.OK,
            data=data
        )
    
    def _update_health_from_response(self, response: APIResponse, latency_ms: float):
        """Update provider health based on API response."""
        if response.is_success:
            self._health.status = ProviderStatus.HEALTHY
            self._health.error_message = None
        elif response.is_rate_limited:
            self._health.status = ProviderStatus.DEGRADED
            self._health.error_message = "Rate limited"
        else:
            self._health.status = ProviderStatus.UNHEALTHY
            self._health.error_message = str(response.error) if response.error else "Unknown error"
        
        self._health.last_check = datetime.now()
        self._health.latency_ms = latency_ms
        
        if response.rate_limit:
            self._health.rate_limit_remaining = response.rate_limit.remaining
            self._health.rate_limit_reset = response.rate_limit.reset_datetime


class SyncDataProvider(ABC):
    """
    Synchronous version of DataProvider for legacy compatibility.
    
    This provides the same interface as DataProvider but with synchronous methods.
    Useful for gradual migration from sync to async code.
    """
    
    def __init__(self, provider_type: ProviderType, config: Dict[str, Any]):
        """Initialize the synchronous data provider."""
        self.provider_type = provider_type
        self.config = config
        self._health = ProviderHealth(
            status=ProviderStatus.HEALTHY,
            last_check=datetime.now()
        )
    
    @property
    def health(self) -> ProviderHealth:
        """Get current provider health status."""
        return self._health
    
    @abstractmethod
    def health_check(self) -> ProviderHealth:
        """Perform a synchronous health check."""
        pass
    
    @abstractmethod
    def get_stock_quote(self, symbol: str) -> APIResponse:
        """Get stock quote synchronously."""
        pass
    
    @abstractmethod
    def get_stock_quotes(self, symbols: List[str]) -> APIResponse:
        """Get multiple stock quotes synchronously."""
        pass
    
    @abstractmethod
    def get_options_chain(
        self, 
        symbol: str, 
        expiration_from: Optional[date] = None,
        expiration_to: Optional[date] = None
    ) -> APIResponse:
        """Get options chain synchronously."""
        pass
    
    @abstractmethod
    def screen_stocks(self, criteria: ScreeningCriteria) -> APIResponse:
        """Screen stocks synchronously."""
        pass
    
    @abstractmethod
    def get_greeks(self, option_symbol: str) -> APIResponse:
        """Get option Greeks synchronously."""
        pass
    
    @abstractmethod
    def get_rate_limit_info(self) -> Optional[RateLimitHeaders]:
        """Get rate limit information."""
        pass
    
    @abstractmethod
    def estimate_credits_required(self, operation: str, **kwargs) -> int:
        """Estimate API credits required."""
        pass
    
    @abstractmethod
    def supports_operation(self, operation: str) -> bool:
        """Check if operation is supported."""
        pass