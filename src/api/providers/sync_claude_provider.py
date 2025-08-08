"""
Synchronous Claude AI provider implementation for the PMCC Scanner.

This provider implements the SyncDataProvider interface using Claude AI API
for enhanced PMCC opportunity analysis in a synchronous manner.
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, date, timedelta
from decimal import Decimal

from src.api.data_provider import SyncDataProvider, ProviderType, ProviderStatus, ProviderHealth, ScreeningCriteria
from src.api.providers.claude_provider import ClaudeProvider
from src.models.api_models import (
    StockQuote, OptionChain, OptionContract, APIResponse, APIError, APIStatus, 
    RateLimitHeaders, EnhancedStockData
)

logger = logging.getLogger(__name__)


class SyncClaudeProvider(SyncDataProvider):
    """
    Synchronous Claude AI implementation of the SyncDataProvider interface.
    
    This is a wrapper around the async ClaudeProvider that provides synchronous
    methods for legacy compatibility.
    """
    
    def __init__(self, provider_type: ProviderType, config: Dict[str, Any]):
        """Initialize synchronous Claude provider."""
        super().__init__(provider_type, config)
        
        # Create the async provider instance
        self._async_provider = ClaudeProvider(provider_type, config)
        
        logger.info("Synchronous Claude AI provider initialized")
    
    def health_check(self) -> ProviderHealth:
        """Perform synchronous health check."""
        return asyncio.run(self._async_provider.health_check())
    
    # Traditional data provider operations (not supported by Claude)
    
    def get_stock_quote(self, symbol: str) -> APIResponse:
        """Claude doesn't provide stock quotes."""
        return self._create_error_response(
            "Stock quotes not supported by Claude AI provider. Use MarketData or EODHD providers.",
            code=501
        )
    
    def get_stock_quotes(self, symbols: List[str]) -> APIResponse:
        """Claude doesn't provide stock quotes."""
        return self._create_error_response(
            "Stock quotes not supported by Claude AI provider. Use MarketData or EODHD providers.",
            code=501
        )
    
    def get_options_chain(
        self, 
        symbol: str, 
        expiration_from: Optional[date] = None,
        expiration_to: Optional[date] = None
    ) -> APIResponse:
        """Claude doesn't provide options chains."""
        return self._create_error_response(
            "Options chains not supported by Claude AI provider. Use MarketData or EODHD providers.",
            code=501
        )
    
    def screen_stocks(self, criteria: ScreeningCriteria) -> APIResponse:
        """Claude doesn't provide stock screening."""
        return self._create_error_response(
            "Stock screening not supported by Claude AI provider. Use EODHD provider.",
            code=501
        )
    
    def get_greeks(self, option_symbol: str) -> APIResponse:
        """Claude doesn't provide options Greeks."""
        return self._create_error_response(
            "Options Greeks not supported by Claude AI provider. Use MarketData provider.",
            code=501
        )
    
    # Specialized AI analysis operations
    
    def analyze_pmcc_opportunities(
        self, 
        enhanced_stock_data: List[EnhancedStockData],
        market_context: Optional[Dict[str, Any]] = None
    ) -> APIResponse:
        """
        Analyze PMCC opportunities using Claude AI (synchronous).
        
        Args:
            enhanced_stock_data: List of enhanced stock data for analysis
            market_context: Optional market context information
            
        Returns:
            APIResponse containing ClaudeAnalysisResponse or error
        """
        try:
            return asyncio.run(
                self._async_provider.analyze_pmcc_opportunities(enhanced_stock_data, market_context)
            )
        except Exception as e:
            logger.error(f"Synchronous Claude analysis failed: {e}")
            return self._create_error_response(f"Analysis failed: {str(e)}", code=500)
    
    def get_enhanced_analysis(
        self, 
        enhanced_stock_data: List[EnhancedStockData],
        market_context: Optional[Dict[str, Any]] = None
    ) -> APIResponse:
        """
        Get enhanced analysis (synchronous).
        
        Alternative name for analyze_pmcc_opportunities.
        """
        return self.analyze_pmcc_opportunities(enhanced_stock_data, market_context)
    
    # Rate limiting and quota management
    
    def get_rate_limit_info(self) -> Optional[RateLimitHeaders]:
        """Get current rate limit status."""
        return self._async_provider.get_rate_limit_info()
    
    def estimate_credits_required(self, operation: str, **kwargs) -> int:
        """Estimate API credits/cost required for an operation."""
        return self._async_provider.estimate_credits_required(operation, **kwargs)
    
    def supports_operation(self, operation: str) -> bool:
        """Check if provider supports a specific operation."""
        return self._async_provider.supports_operation(operation)
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get Claude provider information and capabilities."""
        base_info = self._async_provider.get_provider_info()
        base_info.update({
            "sync_wrapper": True,
            "async_provider_class": self._async_provider.__class__.__name__
        })
        return base_info
    
    # Helper methods (inherited from SyncDataProvider base class)
    
    def _create_error_response(self, message: str, code: Optional[int] = None) -> APIResponse:
        """Create a standardized error response."""
        return APIResponse(
            status=APIStatus.ERROR,
            error=APIError(
                code=code or 500,
                message=message
            )
        )


def create_sync_claude_provider(config: Dict[str, Any]) -> SyncClaudeProvider:
    """
    Factory function to create a synchronous Claude provider.
    
    Args:
        config: Claude provider configuration
        
    Returns:
        SyncClaudeProvider instance
    """
    return SyncClaudeProvider(ProviderType.CLAUDE, config)