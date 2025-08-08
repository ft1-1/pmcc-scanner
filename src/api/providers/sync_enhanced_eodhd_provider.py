"""
Synchronous wrapper for EnhancedEODHDProvider implementation.

This provider wraps the async EnhancedEODHDProvider to provide synchronous access
to all enhanced EODHD functionality for backward compatibility with the existing
synchronous scanner architecture.

Key features:
- Synchronous wrapper around async EnhancedEODHDProvider
- Full support for enhanced operations (fundamentals, calendar events, technical indicators)
- Maintains all AI enhancement capabilities
- Backward compatibility for existing synchronous code
- Same error handling and circuit breaker patterns
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, date
from decimal import Decimal
import time

from src.api.data_provider import SyncDataProvider, ProviderType, ProviderStatus, ProviderHealth, ScreeningCriteria
from src.api.providers.enhanced_eodhd_provider import EnhancedEODHDProvider
from src.models.api_models import (
    StockQuote, OptionChain, OptionContract, APIResponse, APIError, APIStatus, 
    RateLimitHeaders, ProviderMetadata, FundamentalMetrics, CalendarEvent,
    TechnicalIndicators, RiskMetrics, EnhancedStockData
)

logger = logging.getLogger(__name__)


class SyncEnhancedEODHDProvider(SyncDataProvider):
    """
    Synchronous wrapper for EnhancedEODHDProvider.
    
    This provider wraps the async EnhancedEODHDProvider to provide synchronous access
    to all enhanced EODHD functionality including fundamental data, calendar events,
    technical indicators, and risk metrics for AI-enhanced PMCC analysis.
    """
    
    def __init__(self, provider_type: ProviderType, config: Dict[str, Any]):
        """
        Initialize synchronous enhanced EODHD provider.
        
        Args:
            provider_type: Should be ProviderType.EODHD
            config: Configuration dictionary with API credentials and settings
        """
        super().__init__(provider_type, config)
        
        # Create async provider instance
        self.async_provider = EnhancedEODHDProvider(provider_type, config)
        
        # Track if we're in an async context to avoid nested event loops
        self._loop = None
        
        logger.info(f"Initialized SyncEnhancedEODHDProvider with config: {list(config.keys())}")
    
    def _run_async(self, coro):
        """
        Run an async coroutine synchronously.
        
        Args:
            coro: Async coroutine to run
            
        Returns:
            Result of the coroutine
        """
        try:
            # Try to get current event loop
            loop = asyncio.get_running_loop()
            # If we're already in an async context, we need to run in a thread
            import concurrent.futures
            import threading
            
            def run_in_new_loop():
                """Run coroutine in a new event loop in a separate thread."""
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(coro)
                finally:
                    new_loop.close()
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_new_loop)
                return future.result()
        except RuntimeError:
            # No event loop running, we can create one
            return asyncio.run(coro)
    
    def health_check(self) -> ProviderHealth:
        """Synchronous health check."""
        return self._run_async(self.async_provider.health_check())
    
    def get_stock_quote(self, symbol: str) -> APIResponse:
        """Get synchronous stock quote."""
        return self._run_async(self.async_provider.get_stock_quote(symbol))
    
    def get_stock_quotes(self, symbols: List[str]) -> APIResponse:
        """Get synchronous stock quotes for multiple symbols."""
        return self._run_async(self.async_provider.get_stock_quotes(symbols))
    
    def get_options_chain(
        self,
        symbol: str,
        expiration_date: Optional[Union[str, date]] = None,
        option_type: Optional[str] = None
    ) -> APIResponse:
        """Get synchronous options chain."""
        return self._run_async(
            self.async_provider.get_options_chain(symbol, expiration_date, option_type)
        )
    
    def screen_stocks(self, criteria: ScreeningCriteria) -> APIResponse:
        """Screen stocks synchronously using EODHD's native screener."""
        return self._run_async(self.async_provider.screen_stocks(criteria))
    
    def get_fundamental_data(self, symbol: str) -> APIResponse:
        """Get synchronous fundamental data."""
        return self._run_async(self.async_provider.get_fundamental_data(symbol))
    
    def get_calendar_events(self, symbol: str, days_ahead: int = 30) -> APIResponse:
        """Get synchronous calendar events."""
        return self._run_async(self.async_provider.get_calendar_events(symbol, days_ahead))
    
    def get_technical_indicators(self, symbol: str) -> APIResponse:
        """Get synchronous technical indicators."""
        return self._run_async(self.async_provider.get_technical_indicators(symbol))
    
    def get_technical_indicators_comprehensive(self, symbol: str) -> APIResponse:
        """Get synchronous comprehensive technical indicators."""
        return self._run_async(self.async_provider.get_technical_indicators_comprehensive(symbol))
    
    def get_risk_metrics(self, symbol: str) -> APIResponse:
        """Get synchronous risk metrics."""
        return self._run_async(self.async_provider.get_risk_metrics(symbol))
    
    def get_enhanced_stock_data(self, symbol: str) -> APIResponse:
        """Get synchronous enhanced stock data with all metrics."""
        return self._run_async(self.async_provider.get_enhanced_stock_data(symbol))
    
    def get_comprehensive_enhanced_data(self, symbol: str) -> APIResponse:
        """Get synchronous comprehensive enhanced data for full analysis."""
        return self._run_async(self.async_provider.get_comprehensive_enhanced_data(symbol))
    
    def get_greeks(self, option_symbol: str) -> APIResponse:
        """Get synchronous option Greeks."""
        return self._run_async(self.async_provider.get_greeks(option_symbol))
    
    def get_rate_limit_info(self) -> Optional[RateLimitHeaders]:
        """Get current rate limit information."""
        return self.async_provider.get_rate_limit_info()
    
    def estimate_credits_required(self, operation: str, **kwargs) -> int:
        """Estimate credits required for an operation."""
        return self.async_provider.estimate_credits_required(operation, **kwargs)
    
    def supports_operation(self, operation: str) -> bool:
        """Check if the provider supports a specific operation."""
        return self.async_provider.supports_operation(operation)
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get provider information."""
        base_info = self.async_provider.get_provider_info()
        base_info.update({
            "sync_wrapper": True,
            "wrapped_provider": "EnhancedEODHDProvider"
        })
        return base_info
    
    def get_pmcc_universe(self, limit: int = 100) -> List[str]:
        """Get PMCC universe of stocks synchronously."""
        response = self._run_async(self.async_provider.get_pmcc_universe_async(limit))
        if response.is_success and response.data:
            return response.data
        return []
    
    def get_pmcc_options_optimized(self, symbol: str, current_price: Optional[float] = None) -> APIResponse:
        """Get PMCC-optimized options data synchronously."""
        return self._run_async(
            self.async_provider.get_pmcc_options_optimized(symbol, current_price)
        )
    
    def get_screening_stats(self) -> Dict[str, Any]:
        """Get screening statistics."""
        return self.async_provider.get_screening_stats()
    
    def clear_screening_cache(self):
        """Clear screening cache."""
        self.async_provider.clear_screening_cache()
    
    def close(self):
        """Close provider and cleanup resources."""
        if hasattr(self.async_provider, 'close'):
            self._run_async(self.async_provider.close())


def create_sync_enhanced_eodhd_provider(config: Dict[str, Any]) -> SyncEnhancedEODHDProvider:
    """
    Factory function to create SyncEnhancedEODHDProvider instance.
    
    Args:
        config: Provider configuration
        
    Returns:
        Configured SyncEnhancedEODHDProvider instance
    """
    return SyncEnhancedEODHDProvider(ProviderType.EODHD, config)