"""
Synchronous MarketData.app provider implementation for the PMCC Scanner.

This provider implements the SyncDataProvider interface using MarketData.app API
with the same features as the async version but for synchronous usage.

Key features:
- Uses cached feed for options chains to minimize costs
- Filters options by expiration date ranges for LEAPS and short calls
- Implements stock screening using batch quotes
- Comprehensive error handling with retry logic
- Rate limiting awareness and credit estimation
"""

import logging
import time
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, date, timedelta
from decimal import Decimal
import asyncio

from src.api.data_provider import SyncDataProvider, ProviderType, ProviderStatus, ProviderHealth, ScreeningCriteria
from src.api.providers.marketdata_provider import MarketDataProvider
from src.models.api_models import (
    StockQuote, OptionChain, OptionContract, APIResponse, APIError, APIStatus, 
    RateLimitHeaders, ProviderMetadata
)

logger = logging.getLogger(__name__)


class SyncMarketDataProvider(SyncDataProvider):
    """
    Synchronous MarketData.app implementation of the SyncDataProvider interface.
    
    This is a wrapper around the async MarketDataProvider that provides
    synchronous access to the same functionality.
    """
    
    def __init__(self, provider_type: ProviderType, config: Dict[str, Any]):
        """
        Initialize synchronous MarketData.app provider.
        
        Args:
            provider_type: Should be ProviderType.MARKETDATA
            config: Configuration dictionary with API credentials and settings
        """
        super().__init__(provider_type, config)
        
        # Create async provider instance
        self._async_provider = MarketDataProvider(provider_type, config)
        
        # Event loop for running async operations
        self._loop = None
        
        logger.info("Synchronous MarketData.app provider initialized")
    
    def _get_event_loop(self):
        """Get or create event loop for async operations."""
        if self._loop is None or self._loop.is_closed():
            try:
                # Try to get existing loop
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                # Create new loop if none exists
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
        return self._loop
    
    def _run_async(self, coro):
        """Run async coroutine synchronously."""
        loop = self._get_event_loop()
        try:
            return loop.run_until_complete(coro)
        except RuntimeError as e:
            if "This event loop is already running" in str(e):
                # If we're in an async context, we need to use a different approach
                # This can happen in Jupyter notebooks or other async environments
                logger.warning("Event loop already running, using asyncio.create_task")
                return asyncio.create_task(coro)
            raise
    
    def health_check(self) -> ProviderHealth:
        """
        Perform health check synchronously.
        
        Returns:
            ProviderHealth with current status
        """
        try:
            return self._run_async(self._async_provider.health_check())
        except Exception as e:
            logger.error(f"Sync health check failed: {e}")
            return ProviderHealth(
                status=ProviderStatus.UNHEALTHY,
                last_check=datetime.now(),
                error_message=f"Health check failed: {str(e)}"
            )
    
    def get_stock_quote(self, symbol: str) -> APIResponse:
        """
        Get stock quote synchronously.
        
        Args:
            symbol: Stock symbol (e.g., "AAPL")
            
        Returns:
            APIResponse containing StockQuote data or error
        """
        try:
            return self._run_async(self._async_provider.get_stock_quote(symbol))
        except Exception as e:
            logger.error(f"Sync get_stock_quote failed: {e}")
            return self._create_error_response(
                f"Failed to get stock quote for {symbol}: {str(e)}"
            )
    
    def get_stock_quotes(self, symbols: List[str]) -> APIResponse:
        """
        Get multiple stock quotes synchronously.
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            APIResponse containing list of StockQuote data or error
        """
        try:
            return self._run_async(self._async_provider.get_stock_quotes(symbols))
        except Exception as e:
            logger.error(f"Sync get_stock_quotes failed: {e}")
            return self._create_error_response(
                f"Failed to get stock quotes: {str(e)}"
            )
    
    def get_options_chain(
        self, 
        symbol: str, 
        expiration_from: Optional[date] = None,
        expiration_to: Optional[date] = None
    ) -> APIResponse:
        """
        Get options chain synchronously.
        
        Args:
            symbol: Stock symbol
            expiration_from: Minimum expiration date (optional)
            expiration_to: Maximum expiration date (optional)
            
        Returns:
            APIResponse containing OptionChain data or error
        """
        try:
            return self._run_async(
                self._async_provider.get_options_chain(symbol, expiration_from, expiration_to)
            )
        except Exception as e:
            logger.error(f"Sync get_options_chain failed: {e}")
            return self._create_error_response(
                f"Failed to get options chain for {symbol}: {str(e)}"
            )
    
    def get_pmcc_optimized_chains(self, symbol: str) -> APIResponse:
        """
        Get PMCC-optimized option chains synchronously.
        
        Makes 2 targeted API calls for LEAPS and short calls separately.
        Much more efficient than fetching the entire chain.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            APIResponse containing combined OptionChain
        """
        try:
            return self._run_async(
                self._async_provider.get_pmcc_optimized_chains(symbol)
            )
        except Exception as e:
            logger.error(f"Sync get_pmcc_optimized_chains failed: {e}")
            return self._create_error_response(
                f"Failed to get PMCC chains for {symbol}: {str(e)}"
            )
    
    def screen_stocks(self, criteria: ScreeningCriteria) -> APIResponse:
        """
        Screen stocks synchronously.
        
        Args:
            criteria: Screening criteria
            
        Returns:
            APIResponse containing screening results or error
        """
        try:
            return self._run_async(self._async_provider.screen_stocks(criteria))
        except Exception as e:
            logger.error(f"Sync screen_stocks failed: {e}")
            return self._create_error_response(
                f"Failed to screen stocks: {str(e)}"
            )
    
    def get_greeks(self, option_symbol: str) -> APIResponse:
        """
        Get option Greeks synchronously.
        
        Args:
            option_symbol: Option contract symbol
            
        Returns:
            APIResponse containing option contract with Greeks or error
        """
        try:
            return self._run_async(self._async_provider.get_greeks(option_symbol))
        except Exception as e:
            logger.error(f"Sync get_greeks failed: {e}")
            return self._create_error_response(
                f"Failed to get Greeks for {option_symbol}: {str(e)}"
            )
    
    def get_rate_limit_info(self) -> Optional[RateLimitHeaders]:
        """
        Get current rate limit status.
        
        Returns:
            RateLimitHeaders object or None if not available
        """
        return self._async_provider.get_rate_limit_info()
    
    def estimate_credits_required(self, operation: str, **kwargs) -> int:
        """
        Estimate API credits required for an operation.
        
        Args:
            operation: Type of operation
            **kwargs: Operation-specific parameters
            
        Returns:
            Estimated number of API credits required
        """
        return self._async_provider.estimate_credits_required(operation, **kwargs)
    
    def supports_operation(self, operation: str) -> bool:
        """
        Check if provider supports a specific operation.
        
        Args:
            operation: Operation name
            
        Returns:
            True if operation is supported
        """
        return self._async_provider.supports_operation(operation)
    
    @property
    def health(self) -> ProviderHealth:
        """Get current provider health status."""
        return self._async_provider.health
    
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
            "rate_limit": self.get_rate_limit_info(),
            "is_sync": True
        }
    
    def _create_error_response(self, message: str, code: Optional[int] = None) -> APIResponse:
        """Create a standardized error response."""
        return APIResponse(
            status=APIStatus.ERROR,
            error=APIError(
                code=code or 500,
                message=message
            )
        )
    
    def close(self):
        """Close the provider and cleanup resources."""
        try:
            # Close the async provider
            if self._async_provider:
                self._run_async(self._async_provider.close())
            
            # Don't close event loop if it's the main thread's loop
            # Only close if we explicitly created a new one
            if self._loop and not self._loop.is_closed() and not self._loop.is_running():
                self._loop.close()
                
        except Exception as e:
            logger.warning(f"Minor issue closing sync MarketData provider: {e}")
        
        logger.info("Synchronous MarketData.app provider closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()