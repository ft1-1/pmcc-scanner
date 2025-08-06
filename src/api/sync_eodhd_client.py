"""
Synchronous wrapper for EODHD API client.

Provides synchronous access to EODHD stock screening and options data
for compatibility with the existing PMCC scanner workflow.
"""

import asyncio
import logging
import threading
from typing import Optional, List, Dict, Any, Union
from functools import wraps
import concurrent.futures

from src.api.eodhd_client import EODHDClient, EODHDError
from src.models.api_models import APIResponse, OptionChain

logger = logging.getLogger(__name__)


def async_to_sync(func):
    """
    Decorator to convert async method to sync.
    
    This decorator handles the async/sync event loop conflicts by:
    1. Checking if there's an existing running event loop
    2. If there is, running the async code in a separate thread with its own loop
    3. If there isn't, using the current thread's loop or creating a new one
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            # Check if there's already a running event loop in the current thread
            try:
                current_loop = asyncio.get_running_loop()
                # If we get here, there's a running loop - we need to run in a separate thread
                logger.debug(f"Running {func.__name__} in separate thread due to existing event loop")
                
                def run_in_thread():
                    # Create a new event loop for this thread
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(func(self, *args, **kwargs))
                    finally:
                        new_loop.close()
                
                # Use ThreadPoolExecutor to run the async code in a separate thread
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(run_in_thread)
                    return future.result()
                    
            except RuntimeError:
                # No running event loop - we can run directly
                try:
                    # Try to get the event loop for this thread
                    loop = asyncio.get_event_loop()
                    if loop.is_closed():
                        raise RuntimeError("Event loop is closed")
                except RuntimeError:
                    # No event loop exists, create a new one
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # Run the async method
                return loop.run_until_complete(func(self, *args, **kwargs))
                
        except Exception as e:
            logger.error(f"Error in sync wrapper for {func.__name__}: {e}")
            raise
    return wrapper


class SyncEODHDClient:
    """
    Synchronous wrapper for EODHDClient.
    
    Provides the same interface as the async client but with synchronous methods
    for compatibility with existing code that expects sync operations.
    """
    
    def __init__(self, 
                 api_token: Optional[str] = None,
                 base_url: Optional[str] = None,
                 timeout: float = 30.0,
                 max_retries: int = 3,
                 retry_backoff: float = 1.0):
        """
        Initialize synchronous EODHD client.
        
        Args match those of the async EODHDClient.
        """
        self._client = EODHDClient(
            api_token=api_token,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            retry_backoff=retry_backoff
        )
        self._session_active = False
        self._lock = threading.Lock()  # Thread safety for session management
        
        logger.info("Synchronous EODHD client initialized")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def close(self):
        """Close the underlying client."""
        with self._lock:
            if self._session_active:
                try:
                    # Use the same logic as async_to_sync for cleanup
                    try:
                        current_loop = asyncio.get_running_loop()
                        # Running loop exists - use thread to close
                        def close_in_thread():
                            new_loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(new_loop)
                            try:
                                return new_loop.run_until_complete(self._client.close())
                            finally:
                                new_loop.close()
                        
                        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                            future = executor.submit(close_in_thread)
                            future.result()
                            
                    except RuntimeError:
                        # No running loop - can close directly
                        try:
                            loop = asyncio.get_event_loop()
                            if loop.is_closed():
                                raise RuntimeError("Event loop is closed")
                        except RuntimeError:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                        
                        loop.run_until_complete(self._client.close())
                        
                except Exception as e:
                    logger.warning(f"Error closing EODHD client: {e}")
                finally:
                    self._session_active = False
    
    @async_to_sync
    async def screen_stocks(self, 
                           filters: Optional[List[List[Any]]] = None,
                           sort: Optional[str] = None,
                           limit: int = 50,
                           offset: int = 0) -> APIResponse:
        """Screen stocks using EODHD Screener API."""
        async with self._client:
            self._session_active = True
            return await self._client.screen_stocks(filters, sort, limit, offset)
    
    @async_to_sync
    async def screen_by_market_cap(self, 
                                 min_market_cap: int = 50_000_000,
                                 max_market_cap: int = 5_000_000_000,
                                 exchange: str = "us",
                                 min_volume: int = 100_000,
                                 limit: int = 100) -> APIResponse:
        """Screen US stocks by market capitalization range."""
        async with self._client:
            self._session_active = True
            return await self._client.screen_by_market_cap(
                min_market_cap, max_market_cap, exchange, min_volume, limit
            )
    
    @async_to_sync
    async def get_pmcc_universe(self, limit: int = 100) -> List[str]:
        """Get list of stock symbols suitable for PMCC strategy."""
        async with self._client:
            self._session_active = True
            return await self._client.get_pmcc_universe(limit)
    
    @async_to_sync
    async def get_options_eod(self,
                             symbol: str,
                             option_type: Optional[str] = None,
                             exp_date_from: Optional[str] = None,
                             exp_date_to: Optional[str] = None,
                             strike_from: Optional[float] = None,
                             strike_to: Optional[float] = None,
                             tradetime_from: Optional[str] = None,
                             limit: int = 1000) -> APIResponse:
        """Get end-of-day options data from EODHD Options API."""
        async with self._client:
            self._session_active = True
            return await self._client.get_options_eod(
                symbol, option_type, exp_date_from, exp_date_to,
                strike_from, strike_to, tradetime_from, limit
            )
    
    @async_to_sync
    async def get_pmcc_options_optimized(self,
                                       symbol: str,
                                       current_price: Optional[float] = None) -> APIResponse:
        """Get PMCC-relevant options using optimized filtering strategy."""
        async with self._client:
            self._session_active = True
            return await self._client.get_pmcc_options_optimized(symbol, current_price)
    
    @async_to_sync
    async def get_pmcc_options_comprehensive(self,
                                           symbol: str,
                                           current_price: Optional[float] = None,
                                           config=None) -> APIResponse:
        """Get comprehensive PMCC options using targeted retrieval strategy."""
        async with self._client:
            self._session_active = True
            
            # Extract configuration if provided
            kwargs = {}
            if config:
                kwargs.update({
                    'batch_size': getattr(config, 'pmcc_batch_size', 10),
                    'batch_delay': getattr(config, 'pmcc_batch_delay', 1.0),
                    'min_success_rate': getattr(config, 'pmcc_min_success_rate', 50.0),
                    'retry_failed': getattr(config, 'pmcc_retry_failed_batches', True),
                    'enable_caching': getattr(config, 'pmcc_enable_caching', True),
                    'cache_ttl_minutes': getattr(config, 'pmcc_cache_ttl_minutes', 60)
                })
            
            return await self._client.get_pmcc_options_comprehensive(symbol, current_price, **kwargs)
    
    @async_to_sync
    async def get_option_chain_eodhd(self, symbol: str) -> APIResponse:
        """
        Get option chain from EODHD in OptionChain format for compatibility.
        
        This method provides compatibility with existing code that expects
        an OptionChain object from the options analyzer.
        """
        async with self._client:
            self._session_active = True
            return await self._client.get_option_chain_eodhd(symbol)
    
    @async_to_sync
    async def get_eod_latest(self, symbol: str) -> APIResponse:
        """Get latest end-of-day quote for a symbol."""
        async with self._client:
            self._session_active = True
            return await self._client.get_eod_latest(symbol)
    
    @async_to_sync
    async def get_eod_historical(self, 
                                symbol: str,
                                from_date: Optional[str] = None,
                                to_date: Optional[str] = None,
                                period: str = 'd') -> APIResponse:
        """Get historical end-of-day data for a symbol."""
        async with self._client:
            self._session_active = True
            return await self._client.get_eod_historical(symbol, from_date, to_date, period)
    
    @async_to_sync
    async def get_stock_quote_eod(self, symbol: str) -> APIResponse:
        """
        Get stock quote from EODHD EOD data in StockQuote-compatible format.
        
        This method fetches the latest EOD data and converts it to a format
        compatible with the existing StockQuote model for use in the hybrid flow.
        """
        async with self._client:
            self._session_active = True
            return await self._client.get_stock_quote_eod(symbol)
    
    # Compatibility methods to match MarketData client interface
    def get_option_chain(self, symbol: str) -> APIResponse:
        """
        Get option chain (compatibility method).
        
        This method provides the same interface as MarketDataClient.get_option_chain()
        to allow drop-in replacement in the options analyzer.
        """
        return self.get_option_chain_eodhd(symbol)
    
    def get_quote(self, symbol: str) -> APIResponse:
        """
        Get stock quote (compatibility method).
        
        This method provides the same interface as MarketDataClient.get_quote()
        but returns EOD data instead of real-time quotes.
        """
        return self.get_stock_quote_eod(symbol)
    
    def get_stock_quote(self, symbol: str) -> APIResponse:
        """
        Get stock quote (compatibility method).
        
        This method provides the same interface as MarketDataClient.get_stock_quote()
        but returns EOD data instead of real-time quotes.
        """
        return self.get_stock_quote_eod(symbol)
    
    @async_to_sync
    async def health_check(self) -> bool:
        """Perform a health check of the API connection."""
        async with self._client:
            self._session_active = True
            return await self._client.health_check()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        return self._client.get_stats()