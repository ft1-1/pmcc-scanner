"""
Claude AI provider implementation for the PMCC Scanner.

This provider implements the DataProvider interface using Claude AI API
for enhanced PMCC opportunity analysis. Unlike traditional data providers,
this provider focuses on AI-powered analysis rather than raw data fetching.

Key features:
- AI-enhanced PMCC opportunity analysis
- Risk assessment and fundamental analysis integration
- Market context awareness
- Cost-efficient API usage with smart prompting
- Comprehensive error handling and retry logic
"""

import asyncio
import logging
import time
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, date, timedelta
from decimal import Decimal

from src.api.data_provider import DataProvider, ProviderType, ProviderStatus, ProviderHealth, ScreeningCriteria
from src.api.claude_client import ClaudeClient, ClaudeError, AuthenticationError, RateLimitError
from src.models.api_models import (
    StockQuote, OptionChain, OptionContract, APIResponse, APIError, APIStatus, 
    RateLimitHeaders, ProviderMetadata, EnhancedStockData, ClaudeAnalysisResponse,
    DataProviderType
)

logger = logging.getLogger(__name__)


class ClaudeProvider(DataProvider):
    """
    Claude AI implementation of the DataProvider interface.
    
    This provider is specialized for AI-enhanced PMCC analysis and does not
    provide traditional market data operations like quotes or options chains.
    Instead, it analyzes existing data to provide intelligent insights.
    """
    
    def __init__(self, provider_type: ProviderType, config: Dict[str, Any]):
        """
        Initialize Claude AI provider.
        
        Args:
            provider_type: Should be ProviderType.CLAUDE
            config: Configuration dictionary with API credentials and settings
        """
        super().__init__(provider_type, config)
        
        # Initialize Claude client with config
        self.client = ClaudeClient(
            api_key=config.get('api_key'),
            model=config.get('model', 'claude-3-5-sonnet-20241022'),
            max_tokens=config.get('max_tokens', 4000),
            temperature=config.get('temperature', 0.1),
            timeout=config.get('timeout', 60.0),
            max_retries=config.get('max_retries', 3),
            retry_backoff=config.get('retry_backoff', 1.0)
        )
        
        # Provider capabilities - Claude is specialized for analysis
        self._supported_operations = {
            'analyze_pmcc_opportunities',        # Batch analysis operation
            'get_enhanced_analysis',             # Alternative name for batch analysis
            'analyze_single_pmcc_opportunity'    # Single opportunity analysis
        }
        
        # Analysis settings
        self.max_stocks_per_analysis = config.get('max_stocks_per_analysis', 20)
        self.min_data_completeness_threshold = config.get('min_data_completeness_threshold', 60.0)
        
        # Cost tracking
        self._daily_cost_limit = config.get('daily_cost_limit', 10.0)  # $10 default
        self._daily_cost_used = 0.0
        self._last_cost_reset = datetime.now().date()
        
        logger.info("Claude AI provider initialized")
    
    async def health_check(self) -> ProviderHealth:
        """
        Perform health check by testing the Claude API.
        
        Returns:
            ProviderHealth with current status
        """
        start_time = time.time()
        
        try:
            # Test with a simple health check request
            is_healthy = await self.client.health_check()
            latency_ms = (time.time() - start_time) * 1000
            
            if is_healthy:
                self._health.status = ProviderStatus.HEALTHY
                self._health.latency_ms = latency_ms
                self._health.error_message = None
            else:
                self._health.status = ProviderStatus.UNHEALTHY
                self._health.error_message = "Health check failed"
                
        except AuthenticationError as e:
            self._health.status = ProviderStatus.UNHEALTHY
            self._health.error_message = f"Authentication error: {str(e)}"
            
        except RateLimitError as e:
            self._health.status = ProviderStatus.DEGRADED
            self._health.error_message = f"Rate limited: {str(e)}"
            
        except Exception as e:
            self._health.status = ProviderStatus.UNHEALTHY
            self._health.error_message = f"Health check failed: {str(e)}"
        
        self._health.last_check = datetime.now()
        return self._health
    
    # Traditional data provider operations (not supported by Claude)
    
    async def get_stock_quote(self, symbol: str) -> APIResponse:
        """Claude doesn't provide stock quotes."""
        return self._create_error_response(
            "Stock quotes not supported by Claude AI provider. Use MarketData or EODHD providers.",
            code=501
        )
    
    async def get_stock_quotes(self, symbols: List[str]) -> APIResponse:
        """Claude doesn't provide stock quotes."""
        return self._create_error_response(
            "Stock quotes not supported by Claude AI provider. Use MarketData or EODHD providers.",
            code=501
        )
    
    async def get_options_chain(
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
    
    async def screen_stocks(self, criteria: ScreeningCriteria) -> APIResponse:
        """Claude doesn't provide stock screening."""
        return self._create_error_response(
            "Stock screening not supported by Claude AI provider. Use EODHD provider.",
            code=501
        )
    
    async def get_greeks(self, option_symbol: str) -> APIResponse:
        """Claude doesn't provide options Greeks."""
        return self._create_error_response(
            "Options Greeks not supported by Claude AI provider. Use MarketData provider.",
            code=501
        )
    
    # Specialized AI analysis operations
    
    async def analyze_pmcc_opportunities(
        self, 
        enhanced_stock_data: List[EnhancedStockData],
        market_context: Optional[Dict[str, Any]] = None
    ) -> APIResponse:
        """
        Analyze PMCC opportunities using Claude AI.
        
        This is the primary operation for the Claude provider, providing
        AI-enhanced analysis of PMCC opportunities based on comprehensive
        stock data.
        
        Args:
            enhanced_stock_data: List of enhanced stock data for analysis
            market_context: Optional market context information
            
        Returns:
            APIResponse containing ClaudeAnalysisResponse or error
        """
        if not enhanced_stock_data:
            return self._create_error_response("No stock data provided for analysis", code=400)
        
        try:
            # Check cost limits
            if not self._check_cost_limits():
                return self._create_error_response(
                    f"Daily cost limit of ${self._daily_cost_limit} exceeded", 
                    code=429
                )
            
            # Filter stocks with sufficient data quality
            quality_stocks = self._filter_by_data_quality(enhanced_stock_data)
            
            if not quality_stocks:
                return self._create_error_response(
                    f"No stocks meet minimum data completeness threshold of {self.min_data_completeness_threshold}%",
                    code=400
                )
            
            # Limit the number of stocks for cost control
            analysis_stocks = quality_stocks[:self.max_stocks_per_analysis]
            
            if len(analysis_stocks) < len(quality_stocks):
                logger.info(f"Limited analysis to top {len(analysis_stocks)} stocks out of {len(quality_stocks)} to control costs")
            
            # Perform the AI analysis
            start_time = time.time()
            response = await self.client.analyze_pmcc_opportunities(analysis_stocks, market_context)
            latency_ms = (time.time() - start_time) * 1000
            
            # Update health based on response
            self._update_health_from_response(response, latency_ms)
            
            # Update cost tracking
            if response.is_success and response.data:
                self._update_cost_tracking(response.data)
            
            # Add provider metadata
            if response.data:
                response.data.analysis_timestamp = datetime.now()
            
            return response.with_provider_metadata(
                ProviderMetadata.for_claude(latency_ms)
            )
            
        except ClaudeError as e:
            logger.error(f"Claude API error: {e}")
            return self._create_error_response(f"Claude analysis failed: {str(e)}", code=500)
        
        except Exception as e:
            logger.error(f"Unexpected error in Claude analysis: {e}")
            return self._create_error_response(f"Analysis failed: {str(e)}", code=500)
    
    async def get_enhanced_analysis(
        self, 
        enhanced_stock_data: List[EnhancedStockData],
        market_context: Optional[Dict[str, Any]] = None
    ) -> APIResponse:
        """
        Alternative name for analyze_pmcc_opportunities.
        
        This provides a more generic interface name that could be extended
        for other types of analysis in the future.
        """
        return await self.analyze_pmcc_opportunities(enhanced_stock_data, market_context)
    
    async def analyze_single_pmcc_opportunity(
        self,
        opportunity_data: Dict[str, Any],
        enhanced_stock_data: Dict[str, Any],
        market_context: Optional[Dict[str, Any]] = None
    ) -> APIResponse:
        """
        Analyze a single PMCC opportunity using Claude AI.
        
        This method provides focused analysis on one opportunity with complete data package
        including PMCC details, option chain data, and all 8 types of EODHD enhanced data.
        Each opportunity is scored individually from 0-100.
        
        Args:
            opportunity_data: PMCC opportunity data with strikes, Greeks, risk metrics
            enhanced_stock_data: Complete enhanced stock data package (8 EODHD data types)
            market_context: Optional market context information
            
        Returns:
            APIResponse containing single opportunity analysis with 0-100 score
        """
        if not opportunity_data or not enhanced_stock_data:
            return self._create_error_response(
                "Missing opportunity or enhanced stock data for analysis", 
                code=400
            )
        
        try:
            # Check cost limits
            if not self._check_cost_limits():
                return self._create_error_response(
                    f"Daily cost limit of ${self._daily_cost_limit} exceeded", 
                    code=429
                )
            
            # Extract symbol for logging
            symbol = opportunity_data.get('symbol', 'Unknown')
            logger.info(f"Analyzing single PMCC opportunity for {symbol}")
            
            # Perform the AI analysis using the client
            start_time = time.time()
            response = await self.client.analyze_single_opportunity(
                opportunity_data, enhanced_stock_data, market_context
            )
            latency_ms = (time.time() - start_time) * 1000
            
            # Update health based on response
            if response.is_success:
                self._health.status = ProviderStatus.HEALTHY
                self._health.latency_ms = latency_ms
                self._health.error_message = None
                
                # Update cost tracking if we have usage data
                if response.data and response.data.get('usage'):
                    usage = response.data['usage']
                    input_cost = usage.get('input_tokens', 0) * 0.000003
                    output_cost = usage.get('output_tokens', 0) * 0.000015
                    total_cost = input_cost + output_cost
                    self._daily_cost_used += total_cost
                    logger.info(f"Single opportunity analysis cost: ${total_cost:.4f}")
            else:
                self._health.status = ProviderStatus.DEGRADED
                self._health.error_message = str(response.error)
            
            self._health.last_check = datetime.now()
            
            # Add provider metadata
            if response.is_success and response.data:
                response.data['provider_metadata'] = {
                    'provider_type': 'claude',
                    'provider_name': 'Claude AI',
                    'analysis_type': 'single_opportunity',
                    'latency_ms': latency_ms,
                    'api_version': '2024-10-22'
                }
            
            return response
            
        except Exception as e:
            logger.error(f"Error in single opportunity analysis for {opportunity_data.get('symbol', 'unknown')}: {e}")
            return self._create_error_response(f"Single opportunity analysis failed: {str(e)}", code=500)
    
    # Rate limiting and quota management
    
    def get_rate_limit_info(self) -> Optional[RateLimitHeaders]:
        """
        Get current rate limit status for Claude API.
        
        Claude uses a different rate limiting model, so we estimate
        based on our usage patterns.
        """
        # Claude doesn't provide detailed rate limit headers like other APIs
        # We estimate based on tier limits and usage
        return RateLimitHeaders(
            limit=1000,  # Estimated daily request limit for typical tier
            remaining=max(0, 1000 - self.client.get_stats()['total_requests']),
            reset=None,   # Claude doesn't provide reset time
            consumed=self.client.get_stats()['total_requests']
        )
    
    def estimate_credits_required(self, operation: str, **kwargs) -> int:
        """
        Estimate API credits/cost required for an operation.
        
        For Claude, we estimate based on tokens rather than credits.
        
        Args:
            operation: Type of operation
            **kwargs: Operation-specific parameters
            
        Returns:
            Estimated cost in cents (1 credit = 1 cent)
        """
        if operation in ['analyze_pmcc_opportunities', 'get_enhanced_analysis']:
            # Estimate based on number of stocks
            num_stocks = len(kwargs.get('enhanced_stock_data', []))
            limited_stocks = min(num_stocks, self.max_stocks_per_analysis)
            
            # Rough estimation: ~2000 input tokens + 1000 output tokens per 10 stocks
            estimated_input_tokens = max(1000, limited_stocks * 200)
            estimated_output_tokens = max(500, limited_stocks * 100)
            
            # Claude 3.5 Sonnet pricing: $3/1M input, $15/1M output
            input_cost = estimated_input_tokens * 0.000003
            output_cost = estimated_output_tokens * 0.000015
            
            return int((input_cost + output_cost) * 100)  # Convert to cents
        
        return 0  # Other operations not supported
    
    def supports_operation(self, operation: str) -> bool:
        """
        Check if provider supports a specific operation.
        
        Claude only supports AI analysis operations.
        """
        return operation in self._supported_operations
    
    # Helper methods
    
    def _filter_by_data_quality(self, enhanced_stock_data: List[EnhancedStockData]) -> List[EnhancedStockData]:
        """Filter stocks by data completeness score."""
        quality_stocks = []
        
        for stock in enhanced_stock_data:
            completeness = stock.calculate_completeness_score()
            if completeness >= self.min_data_completeness_threshold:
                quality_stocks.append(stock)
            else:
                logger.debug(f"Filtered out {stock.symbol} due to low data completeness: {completeness}%")
        
        # Sort by completeness score (best first)
        return sorted(quality_stocks, key=lambda s: s.data_completeness_score or 0, reverse=True)
    
    def _check_cost_limits(self) -> bool:
        """Check if we're within daily cost limits."""
        current_date = datetime.now().date()
        
        # Reset daily counter if it's a new day
        if current_date > self._last_cost_reset:
            self._daily_cost_used = 0.0
            self._last_cost_reset = current_date
        
        return self._daily_cost_used < self._daily_cost_limit
    
    def _update_cost_tracking(self, analysis_response: ClaudeAnalysisResponse):
        """Update cost tracking based on usage."""
        if analysis_response.input_tokens and analysis_response.output_tokens:
            # Calculate actual cost
            input_cost = analysis_response.input_tokens * 0.000003
            output_cost = analysis_response.output_tokens * 0.000015
            total_cost = input_cost + output_cost
            
            self._daily_cost_used += total_cost
            
            logger.info(f"Claude analysis cost: ${total_cost:.4f} (daily total: ${self._daily_cost_used:.4f})")
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get Claude provider information and capabilities."""
        base_info = super().get_provider_info()
        
        # Add Claude-specific information
        claude_info = {
            **base_info,
            "specialization": "AI-enhanced PMCC analysis",
            "model": self.client.model,
            "max_stocks_per_analysis": self.max_stocks_per_analysis,
            "daily_cost_limit": self._daily_cost_limit,
            "daily_cost_used": self._daily_cost_used,
            "stats": self.client.get_stats(),
            "supported_operations": list(self._supported_operations)
        }
        
        return claude_info


# Add ProviderMetadata factory method for Claude
def _add_claude_metadata_factory():
    """Add Claude factory method to ProviderMetadata."""
    def for_claude(cls, latency_ms: Optional[float] = None) -> ProviderMetadata:
        """Create metadata for Claude provider."""
        return cls(
            provider_type=DataProviderType.CLAUDE,
            provider_name="Claude AI",
            request_timestamp=datetime.now(),
            response_latency_ms=latency_ms,
            api_version="2024-10-22"
        )
    
    # Add the method to the ProviderMetadata class
    ProviderMetadata.for_claude = classmethod(for_claude)


# Initialize the factory method
_add_claude_metadata_factory()