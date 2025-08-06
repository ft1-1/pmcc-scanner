"""
Synchronous EODHD provider implementation for the PMCC Scanner.

This provider implements the SyncDataProvider interface using EODHD API
with the same capabilities as the async version but with synchronous methods
for backward compatibility and gradual migration scenarios.

Key features:
- Synchronous wrapper around async EODHD functionality
- Maintains all EODHD strengths (native screening, comprehensive options data)
- Backward compatibility for existing synchronous code
- Same error handling and rate limiting as async version
- Easy migration path to async when ready
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, date
from decimal import Decimal
import time

from src.api.data_provider import SyncDataProvider, ProviderType, ProviderStatus, ProviderHealth, ScreeningCriteria
from src.api.providers.eodhd_provider import EODHDProvider
from src.models.api_models import (
    StockQuote, OptionChain, OptionContract, APIResponse, APIError, APIStatus, 
    RateLimitHeaders, ProviderMetadata
)

logger = logging.getLogger(__name__)


class SyncEODHDProvider(SyncDataProvider):
    """
    Synchronous EODHD implementation of the SyncDataProvider interface.
    
    This provider wraps the async EODHDProvider to provide synchronous access
    to EODHD's capabilities for backward compatibility.
    """
    
    def __init__(self, provider_type: ProviderType, config: Dict[str, Any]):
        """
        Initialize synchronous EODHD provider.
        
        Args:
            provider_type: Should be ProviderType.EODHD
            config: Configuration dictionary with API credentials and settings
        """
        super().__init__(provider_type, config)
        
        # Create async provider instance
        self._async_provider = EODHDProvider(provider_type, config)
        
        # Event loop management for sync operations
        self._loop = None
        self._loop_thread = None
        
        logger.info("Synchronous EODHD provider initialized")
    
    def _run_async(self, coro):
        """
        Run an async coroutine synchronously.
        
        This method handles the event loop creation and management
        for synchronous execution of async operations.
        """
        try:
            # Try to get existing event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, we need to run in a new thread
                import concurrent.futures
                import threading
                
                def run_in_thread():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(coro)
                    finally:
                        new_loop.close()
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_thread)
                    return future.result()
            else:
                # Loop exists but not running, use it
                return loop.run_until_complete(coro)
        except RuntimeError:
            # No event loop exists, create one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()
    
    def health_check(self) -> ProviderHealth:
        """
        Perform synchronous health check.
        
        Returns:
            ProviderHealth with current status
        """
        return self._run_async(self._async_provider.health_check())
    
    def get_stock_quote(self, symbol: str) -> APIResponse:
        """
        Get stock quote synchronously.
        
        Args:
            symbol: Stock symbol (e.g., "AAPL")
            
        Returns:
            APIResponse containing StockQuote data or error
        """
        return self._run_async(self._async_provider.get_stock_quote(symbol))
    
    def get_stock_quotes(self, symbols: List[str]) -> APIResponse:
        """
        Get multiple stock quotes synchronously.
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            APIResponse containing list of StockQuote data or error
        """
        return self._run_async(self._async_provider.get_stock_quotes(symbols))
    
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
        return self._run_async(
            self._async_provider.get_options_chain(symbol, expiration_from, expiration_to)
        )
    
    def screen_stocks(self, criteria: ScreeningCriteria) -> APIResponse:
        """
        Screen stocks synchronously using EODHD's native screener.
        
        Args:
            criteria: Screening criteria
            
        Returns:
            APIResponse containing screening results or error
        """
        return self._run_async(self._async_provider.screen_stocks(criteria))
    
    def get_greeks(self, option_symbol: str) -> APIResponse:
        """
        Get option Greeks synchronously.
        
        Args:
            option_symbol: Option contract symbol
            
        Returns:
            APIResponse containing option contract with Greeks or error
        """
        return self._run_async(self._async_provider.get_greeks(option_symbol))
    
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
        Check if operation is supported.
        
        Args:
            operation: Operation name
            
        Returns:
            True if operation is supported
        """
        return self._async_provider.supports_operation(operation)
    
    def get_provider_info(self) -> Dict[str, Any]:
        """
        Get provider information and capabilities.
        
        Returns:
            Dictionary containing provider metadata
        """
        return self._async_provider.get_provider_info()
    
    # Additional synchronous methods specific to EODHD
    
    def get_pmcc_universe(self, limit: int = 100) -> List[str]:
        """
        Get list of stock symbols suitable for PMCC strategy synchronously.
        
        This is a convenience method that returns just the symbols
        for use with options analysis.
        
        Args:
            limit: Maximum number of symbols to return
            
        Returns:
            List of stock ticker symbols
        """
        return self._run_async(self._async_provider.client.get_pmcc_universe(limit))
    
    def get_pmcc_options_optimized(self, symbol: str, current_price: Optional[float] = None) -> APIResponse:
        """
        Get PMCC-relevant options using optimized filtering strategy synchronously.
        
        Args:
            symbol: Stock symbol to analyze
            current_price: Current stock price for strike filtering
            
        Returns:
            APIResponse containing PMCC-suitable options
        """
        return self._run_async(
            self._async_provider.client.get_pmcc_options_optimized(symbol, current_price)
        )
    
    def get_screening_stats(self) -> Dict[str, Any]:
        """
        Get statistics about screening cache and usage.
        
        Returns:
            Dictionary with screening statistics
        """
        cache_size = len(self._async_provider._screening_cache)
        return {
            'cache_size': cache_size,
            'cache_ttl_hours': self._async_provider._screening_cache_ttl_hours,
            'request_count': self._async_provider._request_count,
            'error_count': self._async_provider._error_count,
            'success_rate': (
                (self._async_provider._request_count - self._async_provider._error_count) / 
                self._async_provider._request_count * 100
                if self._async_provider._request_count > 0 else 0
            )
        }
    
    def clear_screening_cache(self):
        """Clear the screening results cache."""
        self._async_provider._screening_cache.clear()
        logger.info("Screening cache cleared")
    
    def close(self):
        """Close the provider and cleanup resources."""
        try:
            self._run_async(self._async_provider.close())
        except Exception as e:
            logger.warning(f"Error closing async provider: {e}")
        
        logger.info("Synchronous EODHD provider closed")


# Convenience factory function
def create_sync_eodhd_provider(
    api_token: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout: float = 30.0,
    max_retries: int = 3,
    screening_cache_ttl_hours: int = 24,
    enable_tradetime_filtering: bool = True,
    tradetime_lookback_days: int = 5
) -> SyncEODHDProvider:
    """
    Create a synchronous EODHD provider with common configuration.
    
    Args:
        api_token: EODHD API token
        base_url: API base URL (optional)
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts
        screening_cache_ttl_hours: How long to cache screening results
        enable_tradetime_filtering: Enable tradetime filtering for options
        tradetime_lookback_days: Days to look back for trading dates
        
    Returns:
        Configured SyncEODHDProvider instance
    """
    config = {
        'api_token': api_token,
        'base_url': base_url,
        'timeout': timeout,
        'max_retries': max_retries,
        'screening_cache_ttl_hours': screening_cache_ttl_hours,
        'enable_tradetime_filtering': enable_tradetime_filtering,
        'tradetime_lookback_days': tradetime_lookback_days
    }
    
    return SyncEODHDProvider(ProviderType.EODHD, config)