"""
Synchronous wrapper for the async MarketDataClient.

This wrapper allows the existing synchronous code to work with the async API client
without requiring a complete rewrite of all analysis modules.
"""

import asyncio
from typing import Optional, List, Dict
from functools import wraps

from src.api.marketdata_client import MarketDataClient
from src.models.api_models import APIResponse


def run_async(coro):
    """Run an async coroutine in a sync context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    if loop.is_running():
        # If we're already in an async context, create a new task
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    else:
        # Run directly if no loop is running
        return loop.run_until_complete(coro)


class SyncMarketDataClient:
    """
    Synchronous wrapper for MarketDataClient.
    
    Provides the same interface but with synchronous methods for compatibility
    with existing code that expects synchronous API calls.
    """
    
    def __init__(self, api_token: str, plan_type: str = 'free', base_url: Optional[str] = None):
        """Initialize the sync wrapper with an async client."""
        self._async_client = MarketDataClient(
            api_token=api_token,
            plan_type=plan_type,
            base_url=base_url
        )
        self._context_manager = None
    
    def __enter__(self):
        """Enter context manager."""
        self._context_manager = run_async(self._async_client.__aenter__())
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        run_async(self._async_client.__aexit__(exc_type, exc_val, exc_tb))
    
    def get_quote(self, symbol: str) -> APIResponse:
        """Get stock quote (sync wrapper for get_stock_quote)."""
        return run_async(self._async_client.get_stock_quote(symbol))
    
    def get_stock_quote(self, symbol: str) -> APIResponse:
        """Get stock quote for a single symbol."""
        return run_async(self._async_client.get_stock_quote(symbol))
    
    def get_stock_quotes(self, symbols: List[str]) -> Dict[str, APIResponse]:
        """Get stock quotes for multiple symbols."""
        return run_async(self._async_client.get_stock_quotes(symbols))
    
    def get_option_chain(self, symbol: str, expiration: Optional[str] = None) -> APIResponse:
        """Get option chain for a symbol."""
        return run_async(self._async_client.get_option_chain(symbol, expiration))
    
    def get_option_expirations(self, symbol: str) -> APIResponse:
        """Get available option expiration dates."""
        return run_async(self._async_client.get_option_expirations(symbol))
    
    def get_market_status(self) -> APIResponse:
        """Get current market status."""
        return run_async(self._async_client.get_market_status())
    
    @property
    def daily_requests_used(self) -> int:
        """Get number of daily requests used."""
        return self._async_client.daily_requests_used
    
    @property
    def daily_requests_remaining(self) -> int:
        """Get number of daily requests remaining."""
        return self._async_client.daily_requests_remaining