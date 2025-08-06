"""
MarketData.app provider implementation for the PMCC Scanner.

This provider implements the DataProvider interface using MarketData.app API
with optimizations for PMCC strategy requirements including:
- Efficient options chain fetching using cached feed (1 credit per call)
- Batch stock quote processing for screening
- Greeks calculation and PMCC-specific filtering
- Proper error handling and rate limiting

Key features:
- Uses cached feed for options chains to minimize costs
- Filters options by expiration date ranges for LEAPS and short calls
- Implements stock screening using batch quotes (MarketData.app has no screener API)
- Comprehensive error handling with retry logic
- Rate limiting awareness and credit estimation
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, date, timedelta
from decimal import Decimal
import time

from src.api.data_provider import DataProvider, ProviderType, ProviderStatus, ProviderHealth, ScreeningCriteria
from src.api.marketdata_client import MarketDataClient, MarketDataError, RateLimitError, APIQuotaError
from src.models.api_models import (
    StockQuote, OptionChain, OptionContract, APIResponse, APIError, APIStatus, 
    RateLimitHeaders, ProviderMetadata
)

logger = logging.getLogger(__name__)


class MarketDataProvider(DataProvider):
    """
    MarketData.app implementation of the DataProvider interface.
    
    This provider is optimized for PMCC scanning with efficient options chain
    fetching and batch quote processing for stock screening.
    """
    
    def __init__(self, provider_type: ProviderType, config: Dict[str, Any]):
        """
        Initialize MarketData.app provider.
        
        Args:
            provider_type: Should be ProviderType.MARKETDATA
            config: Configuration dictionary with API credentials and settings
        """
        super().__init__(provider_type, config)
        
        # Initialize MarketData client with config
        self.client = MarketDataClient(
            api_token=config.get('api_token'),
            base_url=config.get('base_url'),
            timeout=config.get('timeout', 30.0),
            max_retries=config.get('max_retries', 3),
            retry_backoff=config.get('retry_backoff', 1.0)
        )
        
        # Provider capabilities
        self._supported_operations = {
            'get_stock_quote', 'get_stock_quotes', 'get_options_chain', 
            'screen_stocks', 'get_greeks'
        }
        
        # Since MarketData.app doesn't have a native screener, we need a stock universe
        # for screening. This can be populated from various sources.
        self._stock_universe: List[str] = config.get('stock_universe', [])
        self._max_screening_batch_size = config.get('max_screening_batch_size', 100)
        
        # Rate limiting tracking
        self._last_rate_limit: Optional[RateLimitHeaders] = None
        self._request_count = 0
        self._error_count = 0
        
        logger.info("MarketData.app provider initialized")
    
    async def health_check(self) -> ProviderHealth:
        """
        Perform health check by testing a simple API call.
        
        Returns:
            ProviderHealth with current status
        """
        start_time = time.time()
        
        try:
            # Test with a simple quote request for AAPL
            response = await self.client.get_stock_quote('AAPL')
            latency_ms = (time.time() - start_time) * 1000
            
            if response.is_success:
                self._health.status = ProviderStatus.HEALTHY
                self._health.latency_ms = latency_ms
                self._health.error_message = None
                
                # Update rate limit info if available
                if response.rate_limit:
                    self._health.rate_limit_remaining = response.rate_limit.remaining
                    self._health.rate_limit_reset = response.rate_limit.reset_datetime
                    
            elif response.is_rate_limited:
                self._health.status = ProviderStatus.DEGRADED
                self._health.latency_ms = latency_ms
                self._health.error_message = "Rate limited"
                
            else:
                self._health.status = ProviderStatus.UNHEALTHY
                self._health.latency_ms = latency_ms
                self._health.error_message = str(response.error) if response.error else "Unknown error"
                
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self._health.status = ProviderStatus.UNHEALTHY
            self._health.latency_ms = latency_ms
            self._health.error_message = f"Health check failed: {str(e)}"
            logger.error(f"MarketData.app health check failed: {e}")
        
        self._health.last_check = datetime.now()
        return self._health
    
    async def get_stock_quote(self, symbol: str) -> APIResponse:
        """
        Get real-time or delayed stock quote.
        
        Args:
            symbol: Stock symbol (e.g., "AAPL")
            
        Returns:
            APIResponse containing StockQuote data or error
        """
        start_time = time.time()
        
        try:
            response = await self.client.get_stock_quote(symbol)
            latency_ms = (time.time() - start_time) * 1000
            
            # Update health and tracking
            self._update_health_from_response(response, latency_ms)
            self._request_count += 1
            if not response.is_success:
                self._error_count += 1
            
            # Add provider metadata
            metadata = ProviderMetadata.for_marketdata(latency_ms)
            return response.with_provider_metadata(metadata)
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self._error_count += 1
            logger.error(f"Error getting stock quote for {symbol}: {e}")
            
            return self._create_error_response(
                f"Failed to get stock quote for {symbol}: {str(e)}"
            )
    
    async def get_stock_quotes(self, symbols: List[str]) -> APIResponse:
        """
        Get multiple stock quotes efficiently.
        
        MarketData.app doesn't have a bulk quotes endpoint, so we make
        concurrent individual requests with rate limiting consideration.
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            APIResponse containing list of StockQuote data or error
        """
        start_time = time.time()
        
        try:
            logger.info(f"Fetching quotes for {len(symbols)} symbols")
            
            # Use the client's batch method which handles concurrency
            quote_responses = await self.client.get_stock_quotes(symbols)
            
            # Process results
            successful_quotes = []
            failed_symbols = []
            
            for symbol, response in quote_responses.items():
                if response.is_success and response.data:
                    successful_quotes.append(response.data)
                else:
                    failed_symbols.append(symbol)
                    if response.error:
                        logger.warning(f"Failed to get quote for {symbol}: {response.error}")
            
            latency_ms = (time.time() - start_time) * 1000
            self._request_count += len(symbols)
            self._error_count += len(failed_symbols)
            
            # Create response
            if successful_quotes:
                # Update health based on success rate
                success_rate = len(successful_quotes) / len(symbols)
                if success_rate >= 0.8:
                    status = ProviderStatus.HEALTHY
                elif success_rate >= 0.5:
                    status = ProviderStatus.DEGRADED
                else:
                    status = ProviderStatus.UNHEALTHY
                
                self._health.status = status
                self._health.latency_ms = latency_ms
                self._health.success_rate = success_rate * 100
                self._health.last_check = datetime.now()
                
                metadata = ProviderMetadata.for_marketdata(latency_ms)
                return APIResponse(
                    status=APIStatus.OK,
                    data=successful_quotes,
                    provider_metadata=metadata
                )
            else:
                return self._create_error_response(
                    f"Failed to get quotes for all {len(symbols)} symbols"
                )
                
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self._error_count += len(symbols)
            logger.error(f"Error getting stock quotes: {e}")
            
            return self._create_error_response(
                f"Failed to get stock quotes: {str(e)}"
            )
    
    async def get_options_chain(
        self, 
        symbol: str, 
        expiration_from: Optional[date] = None,
        expiration_to: Optional[date] = None
    ) -> APIResponse:
        """
        Get options chain for a stock using cached feed for efficiency.
        
        This method is optimized for PMCC scanning by:
        - Using cached feed (1 credit per call vs 1 credit per contract)
        - Filtering by expiration date ranges
        - Including Greeks in the response
        
        Args:
            symbol: Stock symbol
            expiration_from: Minimum expiration date (optional)
            expiration_to: Maximum expiration date (optional)
            
        Returns:
            APIResponse containing OptionChain data or error
        """
        start_time = time.time()
        
        try:
            logger.debug(f"Fetching options chain for {symbol}")
            
            # Convert date objects to ISO format strings for API
            from_date = expiration_from.isoformat() if expiration_from else None
            to_date = expiration_to.isoformat() if expiration_to else None
            
            # Log the API call
            print(f"   📡 MarketData.app: Fetching option chain for {symbol}...")
            logger.debug(f"MarketData.app: Fetching option chain for {symbol}")
            
            # Fetch options chain using optimized parameters
            response = await self.client.get_option_chain(
                symbol=symbol,
                from_date=from_date,
                to_date=to_date,
                side='call',  # PMCC only uses calls
                delta_range='.15-.95',  # Cover both LEAPS (.70-.95) and short calls (.15-.40)
                min_open_interest=5,  # Filter out illiquid options
                use_cached_feed=True  # 1 credit per call vs 1 credit per contract
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Update health and tracking
            self._update_health_from_response(response, latency_ms)
            self._request_count += 1
            if not response.is_success:
                self._error_count += 1
            
            # Add provider metadata
            metadata = ProviderMetadata.for_marketdata(latency_ms)
            return response.with_provider_metadata(metadata)
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self._error_count += 1
            logger.error(f"Error getting options chain for {symbol}: {e}")
            
            return self._create_error_response(
                f"Failed to get options chain for {symbol}: {str(e)}"
            )
    
    async def get_pmcc_optimized_chains(self, symbol: str) -> APIResponse:
        """
        Get highly optimized option chains specifically for PMCC analysis.
        
        This method makes 2 targeted API calls instead of fetching the entire chain:
        1. LEAPS calls only (deep ITM, 6-12 months)
        2. Short calls only (OTM, 21-45 days)
        
        This reduces data transfer and improves performance significantly.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            APIResponse containing combined OptionChain with both LEAPS and short calls
        """
        start_time = time.time()
        
        try:
            logger.debug(f"Fetching PMCC-optimized chains for {symbol}")
            
            # Use the optimized PMCC method that makes 2 targeted calls
            chains = await self.client.get_pmcc_option_chains(symbol)
            
            # Combine both chains into a single OptionChain object
            all_contracts = []
            
            if chains['leaps'].is_success and chains['leaps'].data:
                leaps_chain = chains['leaps'].data
                if hasattr(leaps_chain, 'contracts') and leaps_chain.contracts:
                    all_contracts.extend(leaps_chain.contracts)
                    logger.debug(f"Found {len(leaps_chain.contracts)} LEAPS contracts")
            
            if chains['short'].is_success and chains['short'].data:
                short_chain = chains['short'].data
                if hasattr(short_chain, 'contracts') and short_chain.contracts:
                    all_contracts.extend(short_chain.contracts)
                    logger.debug(f"Found {len(short_chain.contracts)} short call contracts")
            
            # Create combined chain
            combined_chain = OptionChain(
                underlying=symbol,
                contracts=all_contracts
            )
            
            # Set updated timestamp
            combined_chain.updated = datetime.now()
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Update health and tracking
            self._request_count += 2  # We made 2 API calls
            self._health.status = ProviderStatus.HEALTHY
            self._health.latency_ms = latency_ms
            self._health.success_rate = 100.0
            self._health.last_check = datetime.now()
            
            # Add provider metadata
            metadata = ProviderMetadata.for_marketdata(latency_ms)
            metadata.api_credits_used = 2  # 2 credits for 2 cached calls
            
            return APIResponse(
                status=APIStatus.OK,
                data=combined_chain,
                provider_metadata=metadata
            )
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self._error_count += 1
            logger.error(f"Error getting PMCC chains for {symbol}: {e}")
            
            return self._create_error_response(
                f"Failed to get PMCC chains for {symbol}: {str(e)}"
            )
    
    async def screen_stocks(self, criteria: ScreeningCriteria) -> APIResponse:
        """
        Screen stocks based on criteria.
        
        Since MarketData.app doesn't have a screener API, this method:
        1. Uses a predefined stock universe (from config)
        2. Fetches quotes for all symbols in batches
        3. Filters quotes based on screening criteria
        4. Returns filtered results
        
        Note: This approach is less efficient than a dedicated screener API
        but provides the same functionality.
        
        Args:
            criteria: Screening criteria
            
        Returns:
            APIResponse containing screening results or error
        """
        start_time = time.time()
        
        try:
            if not self._stock_universe:
                return self._create_error_response(
                    "No stock universe configured for screening. "
                    "MarketData.app doesn't have a native screener API."
                )
            
            logger.info(f"Screening {len(self._stock_universe)} stocks with MarketData.app")
            
            # Process stock universe in batches to avoid overwhelming the API
            all_quotes = []
            batch_size = self._max_screening_batch_size
            
            for i in range(0, len(self._stock_universe), batch_size):
                batch_symbols = self._stock_universe[i:i + batch_size]
                logger.debug(f"Processing batch {i//batch_size + 1}: {len(batch_symbols)} symbols")
                
                # Get quotes for this batch
                batch_response = await self.get_stock_quotes(batch_symbols)
                
                if batch_response.is_success and batch_response.data:
                    all_quotes.extend(batch_response.data)
                else:
                    logger.warning(f"Failed to get quotes for batch: {batch_response.error}")
                
                # Rate limiting: small delay between batches
                if i + batch_size < len(self._stock_universe):
                    await asyncio.sleep(0.1)  # 100ms delay
            
            # Filter quotes based on screening criteria
            filtered_quotes = self._filter_quotes_by_criteria(all_quotes, criteria)
            
            latency_ms = (time.time() - start_time) * 1000
            logger.info(f"Screening completed: {len(filtered_quotes)} stocks match criteria")
            
            # Update health
            self._health.status = ProviderStatus.HEALTHY
            self._health.latency_ms = latency_ms
            self._health.last_check = datetime.now()
            
            # Convert to screening response format
            screening_results = {
                'count': len(filtered_quotes),
                'data': [
                    {
                        'symbol': quote.symbol,
                        'last_price': float(quote.last) if quote.last else None,
                        'volume': quote.volume,
                        'market_cap': None,  # Would need additional API call
                        'bid': float(quote.bid) if quote.bid else None,
                        'ask': float(quote.ask) if quote.ask else None
                    }
                    for quote in filtered_quotes
                ]
            }
            
            metadata = ProviderMetadata.for_marketdata(latency_ms)
            return APIResponse(
                status=APIStatus.OK,
                data=screening_results,
                provider_metadata=metadata
            )
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self._error_count += 1
            logger.error(f"Error screening stocks: {e}")
            
            return self._create_error_response(
                f"Failed to screen stocks: {str(e)}"
            )
    
    async def get_greeks(self, option_symbol: str) -> APIResponse:
        """
        Get Greeks for a specific option contract.
        
        MarketData.app includes Greeks in the options chain response,
        so this method extracts Greeks for a specific contract.
        
        Args:
            option_symbol: Option contract symbol
            
        Returns:
            APIResponse containing option contract with Greeks or error
        """
        start_time = time.time()
        
        try:
            # Parse option symbol to get underlying and expiration
            # Option symbols typically follow format: AAPL240119C150000
            underlying = self._parse_underlying_from_option_symbol(option_symbol)
            
            if not underlying:
                return self._create_error_response(
                    f"Cannot parse underlying symbol from option symbol: {option_symbol}"
                )
            
            # Get options chain (which includes Greeks)
            chain_response = await self.get_options_chain(underlying)
            
            if not chain_response.is_success or not chain_response.data:
                return chain_response
            
            # Find the specific contract
            chain = chain_response.data
            target_contract = None
            
            for contract in chain.contracts:
                if contract.option_symbol == option_symbol:
                    target_contract = contract
                    break
            
            if not target_contract:
                return self._create_error_response(
                    f"Option contract not found: {option_symbol}"
                )
            
            latency_ms = (time.time() - start_time) * 1000
            metadata = ProviderMetadata.for_marketdata(latency_ms)
            
            return APIResponse(
                status=APIStatus.OK,
                data=target_contract,
                provider_metadata=metadata
            )
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self._error_count += 1
            logger.error(f"Error getting Greeks for {option_symbol}: {e}")
            
            return self._create_error_response(
                f"Failed to get Greeks for {option_symbol}: {str(e)}"
            )
    
    def get_rate_limit_info(self) -> Optional[RateLimitHeaders]:
        """
        Get current rate limit status from last API response.
        
        Returns:
            RateLimitHeaders object or None if not available
        """
        return self._last_rate_limit
    
    def estimate_credits_required(self, operation: str, **kwargs) -> int:
        """
        Estimate API credits required for an operation.
        
        MarketData.app credit costs:
        - Cached options chain: 1 credit per call
        - Live options chain: 1 credit per contract (can be thousands)
        - Stock quotes: 1 credit per quote
        - Other endpoints: 1 credit per call
        
        Args:
            operation: Type of operation
            **kwargs: Operation-specific parameters
            
        Returns:
            Estimated number of API credits required
        """
        if operation == 'get_stock_quote':
            return 1
        
        elif operation == 'get_stock_quotes':
            symbols = kwargs.get('symbols', [])
            return len(symbols)
        
        elif operation == 'get_options_chain':
            # Using cached feed = 1 credit per call
            return 1
        
        elif operation == 'screen_stocks':
            # Screening requires getting quotes for all symbols in universe
            return len(self._stock_universe)
        
        elif operation == 'get_greeks':
            # Requires options chain call
            return 1
        
        else:
            return 1
    
    def supports_operation(self, operation: str) -> bool:
        """
        Check if provider supports a specific operation.
        
        Args:
            operation: Operation name
            
        Returns:
            True if operation is supported
        """
        return operation in self._supported_operations
    
    # Private helper methods
    
    def _filter_quotes_by_criteria(self, quotes: List[StockQuote], criteria: ScreeningCriteria) -> List[StockQuote]:
        """Filter stock quotes based on screening criteria."""
        filtered = []
        
        for quote in quotes:
            # Price filters
            if criteria.min_price and (not quote.last or quote.last < criteria.min_price):
                continue
            if criteria.max_price and (not quote.last or quote.last > criteria.max_price):
                continue
            
            # Volume filters
            if criteria.min_volume and (not quote.volume or quote.volume < criteria.min_volume):
                continue
            
            # Exclude penny stocks if requested
            if criteria.exclude_penny_stocks and quote.last and quote.last < Decimal('5.00'):
                continue
            
            # Basic liquidity check (bid-ask spread)
            if quote.bid and quote.ask:
                spread = quote.ask - quote.bid
                if spread > quote.last * Decimal('0.10'):  # > 10% spread
                    continue
            
            filtered.append(quote)
        
        return filtered
    
    def _parse_underlying_from_option_symbol(self, option_symbol: str) -> Optional[str]:
        """
        Parse underlying symbol from option symbol.
        
        Standard option symbol format: AAPL240119C150000
        - AAPL: underlying
        - 240119: expiration date (YYMMDD)
        - C: call (P for put)
        - 150000: strike price * 1000
        """
        try:
            # Simple parsing - find the first digit
            for i, char in enumerate(option_symbol):
                if char.isdigit():
                    return option_symbol[:i]
            return None
        except Exception:
            return None
    
    async def close(self):
        """Close the provider and cleanup resources."""
        if self.client:
            await self.client.close()
        logger.info("MarketData.app provider closed")