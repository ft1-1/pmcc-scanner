"""
EODHD provider implementation for the PMCC Scanner.

This provider implements the DataProvider interface using EODHD API with
optimizations for PMCC strategy requirements including:
- Native stock screening API with market cap filtering (EODHD's strength)
- Options chain data with Greeks for PMCC analysis
- End-of-day stock quotes and fundamental data
- Proper error handling and rate limiting (5 credits per screener request)

Key features:
- Leverages EODHD's excellent stock screener API for efficient market cap filtering
- Uses EODHD Options API for comprehensive options data with Greeks
- Implements PMCC-specific date range optimization for options fetching
- Maintains backward compatibility with existing EODHDClient functionality
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
from src.api.eodhd_client import EODHDClient, EODHDError, EODHDRateLimitError, EODHDQuotaError
from src.models.api_models import (
    StockQuote, OptionChain, OptionContract, APIResponse, APIError, APIStatus, 
    RateLimitHeaders, ProviderMetadata, EODHDScreenerResponse
)

logger = logging.getLogger(__name__)


class EODHDProvider(DataProvider):
    """
    EODHD implementation of the DataProvider interface.
    
    This provider is optimized for PMCC scanning with EODHD's native stock
    screening capabilities and comprehensive options data with Greeks.
    """
    
    def __init__(self, provider_type: ProviderType, config: Dict[str, Any]):
        """
        Initialize EODHD provider.
        
        Args:
            provider_type: Should be ProviderType.EODHD
            config: Configuration dictionary with API credentials and settings
        """
        super().__init__(provider_type, config)
        
        # Initialize EODHD client with config
        self.client = EODHDClient(
            api_token=config.get('api_token'),
            base_url=config.get('base_url'),
            timeout=config.get('timeout', 30.0),
            max_retries=config.get('max_retries', 3),
            retry_backoff=config.get('retry_backoff', 1.0),
            enable_tradetime_filtering=config.get('enable_tradetime_filtering', True),
            tradetime_lookback_days=config.get('tradetime_lookback_days', 5),
            custom_tradetime_date=config.get('custom_tradetime_date')
        )
        
        # Provider capabilities
        self._supported_operations = {
            'get_stock_quote', 'get_stock_quotes', 'get_options_chain', 
            'screen_stocks', 'get_greeks'
        }
        
        # Rate limiting tracking
        self._last_rate_limit: Optional[RateLimitHeaders] = None
        self._request_count = 0
        self._error_count = 0
        
        # Cache for screening results (EODHD screening is expensive at 5 credits per request)
        self._screening_cache: Dict[str, Dict[str, Any]] = {}
        self._screening_cache_ttl_hours = config.get('screening_cache_ttl_hours', 24)
        
        logger.info("EODHD provider initialized")
    
    async def health_check(self) -> ProviderHealth:
        """
        Perform health check by testing a simple API call.
        
        Returns:
            ProviderHealth with current status
        """
        start_time = time.time()
        
        try:
            # Test with a minimal screener request (cheapest health check)
            response = await self.client.screen_stocks(
                filters=[["exchange", "=", "NYSE"]],
                limit=1
            )
            latency_ms = (time.time() - start_time) * 1000
            
            if response.is_success:
                self._health.status = ProviderStatus.HEALTHY
                self._health.latency_ms = latency_ms
                self._health.error_message = None
                
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
            logger.error(f"EODHD health check failed: {e}")
        
        self._health.last_check = datetime.now()
        return self._health
    
    async def get_stock_quote(self, symbol: str) -> APIResponse:
        """
        Get real-time or delayed stock quote using EODHD EOD data.
        
        Args:
            symbol: Stock symbol (e.g., "AAPL")
            
        Returns:
            APIResponse containing StockQuote data or error
        """
        start_time = time.time()
        
        try:
            response = await self.client.get_stock_quote_eod(symbol)
            latency_ms = (time.time() - start_time) * 1000
            
            # Update health and tracking
            self._update_health_from_response(response, latency_ms)
            self._request_count += 1
            if not response.is_success:
                self._error_count += 1
            
            # Add provider metadata
            metadata = ProviderMetadata.for_eodhd(latency_ms)
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
        Get multiple stock quotes using concurrent EODHD EOD requests.
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            APIResponse containing list of StockQuote data or error
        """
        start_time = time.time()
        
        try:
            logger.info(f"Fetching EOD quotes for {len(symbols)} symbols")
            
            # Make concurrent requests with rate limiting consideration
            async def get_quote_safe(symbol: str) -> tuple[str, APIResponse]:
                try:
                    response = await self.client.get_stock_quote_eod(symbol)
                    return symbol, response
                except Exception as e:
                    error_response = APIResponse(
                        status=APIStatus.ERROR,
                        error=APIError(500, f"Error getting quote for {symbol}: {e}")
                    )
                    return symbol, error_response
            
            # Process symbols in batches to avoid overwhelming the API
            batch_size = 20  # Conservative batch size for EODHD
            all_quotes = []
            failed_symbols = []
            
            for i in range(0, len(symbols), batch_size):
                batch_symbols = symbols[i:i + batch_size]
                tasks = [get_quote_safe(symbol) for symbol in batch_symbols]
                
                # Execute batch with timeout
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in results:
                    if isinstance(result, Exception):
                        logger.warning(f"Quote request failed with exception: {result}")
                        continue
                    
                    symbol, response = result
                    if response.is_success and response.data:
                        all_quotes.append(response.data)
                    else:
                        failed_symbols.append(symbol)
                        if response.error:
                            logger.warning(f"Failed to get quote for {symbol}: {response.error}")
                
                # Small delay between batches
                if i + batch_size < len(symbols):
                    await asyncio.sleep(0.2)  # 200ms delay
            
            latency_ms = (time.time() - start_time) * 1000
            self._request_count += len(symbols)
            self._error_count += len(failed_symbols)
            
            # Create response
            if all_quotes:
                # Update health based on success rate
                success_rate = len(all_quotes) / len(symbols)
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
                
                metadata = ProviderMetadata.for_eodhd(latency_ms)
                return APIResponse(
                    status=APIStatus.OK,
                    data=all_quotes,
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
        Get options chain for a stock using EODHD Options API.
        
        This method leverages EODHD's comprehensive options data with Greeks
        and implements PMCC-optimized filtering for better performance.
        
        Args:
            symbol: Stock symbol
            expiration_from: Minimum expiration date (optional)
            expiration_to: Maximum expiration date (optional)
            
        Returns:
            APIResponse containing OptionChain data or error
        """
        start_time = time.time()
        
        try:
            logger.debug(f"Fetching options chain for {symbol} from EODHD")
            
            # Convert date filters to string format for EODHD API
            exp_date_from = expiration_from.strftime('%Y-%m-%d') if expiration_from else None
            exp_date_to = expiration_to.strftime('%Y-%m-%d') if expiration_to else None
            
            # Use the existing EODHD client method which is already optimized
            response = await self.client.get_option_chain_eodhd(symbol)
            
            # If we have date filters, apply additional filtering
            if response.is_success and response.data and (expiration_from or expiration_to):
                chain = response.data
                filtered_contracts = []
                
                for contract in chain.contracts:
                    if expiration_from and contract.expiration < expiration_from:
                        continue
                    if expiration_to and contract.expiration > expiration_to:
                        continue
                    filtered_contracts.append(contract)
                
                # Create new chain with filtered contracts
                chain.contracts = filtered_contracts
                logger.debug(f"Filtered options chain: {len(filtered_contracts)} contracts")
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Update health and tracking
            self._update_health_from_response(response, latency_ms)
            self._request_count += 1
            if not response.is_success:
                self._error_count += 1
            
            # Add provider metadata
            metadata = ProviderMetadata.for_eodhd(latency_ms)
            return response.with_provider_metadata(metadata)
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self._error_count += 1
            logger.error(f"Error getting options chain for {symbol}: {e}")
            
            return self._create_error_response(
                f"Failed to get options chain for {symbol}: {str(e)}"
            )
    
    async def screen_stocks(self, criteria: ScreeningCriteria) -> APIResponse:
        """
        Screen stocks using EODHD's native screener API.
        
        This method leverages EODHD's excellent screening capabilities,
        particularly for market cap filtering which is EODHD's strength.
        
        Note: Each screening request consumes 5 API credits, so results
        are cached for the configured TTL period.
        
        Args:
            criteria: Screening criteria
            
        Returns:
            APIResponse containing screening results or error
        """
        start_time = time.time()
        
        try:
            # Skip cache for now to ensure we get fresh results with new logic
            # TODO: Re-enable cache after confirming split-range approach works
            cache_key = self._generate_screening_cache_key(criteria)
            
            logger.info("Performing EODHD stock screening (5 API credits)")
            
            # Convert criteria to EODHD filters
            eodhd_params = criteria.to_eodhd_filters()
            
            # Exchange filters - screen both NYSE and NASDAQ for US stocks
            if not criteria.exchanges or any(ex.upper() in ['US', 'NYSE', 'NASDAQ'] for ex in criteria.exchanges):
                # EODHD has a 1000 result limit per query, so we split by market cap ranges
                # to ensure we get ALL stocks between our min and max market cap
                all_results = []
                
                # Determine market cap ranges to query
                min_cap = int(criteria.min_market_cap) if criteria.min_market_cap else 50000000
                max_cap = int(criteria.max_market_cap) if criteria.max_market_cap else 5000000000
                
                # Define market cap ranges that make sense for our criteria
                # Split into ranges that are likely to have <1000 stocks each
                market_cap_ranges = []
                if max_cap >= 4000000000:
                    market_cap_ranges.append((4000000000, min(max_cap, 5000000000)))
                if max_cap >= 3000000000 and min_cap < 4000000000:
                    market_cap_ranges.append((max(min_cap, 3000000000), min(max_cap, 4000000000)))
                if max_cap >= 2000000000 and min_cap < 3000000000:
                    market_cap_ranges.append((max(min_cap, 2000000000), min(max_cap, 3000000000)))
                if max_cap >= 1000000000 and min_cap < 2000000000:
                    market_cap_ranges.append((max(min_cap, 1000000000), min(max_cap, 2000000000)))
                if max_cap >= 500000000 and min_cap < 1000000000:
                    market_cap_ranges.append((max(min_cap, 500000000), min(max_cap, 1000000000)))
                if max_cap >= 250000000 and min_cap < 500000000:
                    market_cap_ranges.append((max(min_cap, 250000000), min(max_cap, 500000000)))
                if max_cap >= 100000000 and min_cap < 250000000:
                    market_cap_ranges.append((max(min_cap, 100000000), min(max_cap, 250000000)))
                if min_cap < 100000000:
                    market_cap_ranges.append((min_cap, min(max_cap, 100000000)))
                
                logger.info(f"Screening stocks in {len(market_cap_ranges)} market cap ranges to bypass API limits")
                
                for range_min, range_max in market_cap_ranges:
                    range_label = f"${range_min/1000000:.0f}M-${range_max/1000000:.0f}M"
                    logger.info(f"Screening {range_label} range...")
                    
                    # Build filters for this range
                    range_filters = []
                    range_filters.append(["market_capitalization", ">=", range_min])
                    range_filters.append(["market_capitalization", "<=", range_max])
                    if criteria.min_price:
                        range_filters.append(["adjusted_close", ">=", float(criteria.min_price)])
                    if criteria.max_price:
                        range_filters.append(["adjusted_close", "<=", float(criteria.max_price)])
                    if criteria.min_volume:
                        range_filters.append(["avgvol_1d", ">=", criteria.min_volume])
                    if criteria.min_avg_volume:
                        range_filters.append(["avgvol_200d", ">=", criteria.min_avg_volume])
                    
                    # Screen NYSE for this range
                    nyse_filters = range_filters + [["exchange", "=", "NYSE"]]
                    nyse_count = 0
                    nyse_offset = 0
                    nyse_limit = 100
                    
                    while True:
                        nyse_response = await self.client.screen_stocks(
                            filters=nyse_filters,
                            sort="market_capitalization.desc",
                            limit=nyse_limit,
                            offset=nyse_offset
                        )
                        
                        if nyse_response and nyse_response.is_success and nyse_response.data:
                            if hasattr(nyse_response.data, 'results') and nyse_response.data.results:
                                batch_size = len(nyse_response.data.results)
                                all_results.extend(nyse_response.data.results)
                                nyse_count += batch_size
                                
                                if batch_size < nyse_limit or nyse_offset >= 900:  # Stop before 1000 limit
                                    break
                                else:
                                    nyse_offset += nyse_limit
                            else:
                                break
                        else:
                            if nyse_response and nyse_response.error and "422" in str(nyse_response.error):
                                logger.debug(f"NYSE {range_label}: Hit API limit at offset {nyse_offset}")
                            break
                    
                    # Screen NASDAQ for this range
                    nasdaq_filters = range_filters + [["exchange", "=", "NASDAQ"]]
                    nasdaq_count = 0
                    nasdaq_offset = 0
                    nasdaq_limit = 100
                    
                    while True:
                        nasdaq_response = await self.client.screen_stocks(
                            filters=nasdaq_filters,
                            sort="market_capitalization.desc",
                            limit=nasdaq_limit,
                            offset=nasdaq_offset
                        )
                        
                        if nasdaq_response and nasdaq_response.is_success and nasdaq_response.data:
                            if hasattr(nasdaq_response.data, 'results') and nasdaq_response.data.results:
                                batch_size = len(nasdaq_response.data.results)
                                all_results.extend(nasdaq_response.data.results)
                                nasdaq_count += batch_size
                                
                                if batch_size < nasdaq_limit or nasdaq_offset >= 900:  # Stop before 1000 limit
                                    break
                                else:
                                    nasdaq_offset += nasdaq_limit
                            else:
                                break
                        else:
                            if nasdaq_response and nasdaq_response.error and "422" in str(nasdaq_response.error):
                                logger.debug(f"NASDAQ {range_label}: Hit API limit at offset {nasdaq_offset}")
                            break
                    
                    logger.info(f"  {range_label}: NYSE={nyse_count}, NASDAQ={nasdaq_count}, Total={nyse_count + nasdaq_count}")
                
                logger.info("=" * 60)
                logger.info(f"✅ Total screening complete: {len(all_results)} stocks found across all ranges")
                logger.info("=" * 60)
                
                logger.info("=" * 60)
                logger.info(f"✅ Total screening complete: {len(all_results)} stocks found across all ranges")
                logger.info("=" * 60)
                
                # Create combined response
                if all_results:
                    # Sort by market cap descending
                    all_results.sort(
                        key=lambda x: getattr(x, 'market_capitalization', 0) or 0, 
                        reverse=True
                    )
                    
                    # Don't limit results - we want ALL stocks
                    
                    combined_response = EODHDScreenerResponse(
                        results=all_results,
                        total_count=len(all_results),
                        limit=len(all_results)
                    )
                    
                    response = APIResponse(
                        status=APIStatus.OK,
                        data=combined_response
                    )
                else:
                    response = APIResponse(
                        status=APIStatus.NO_DATA,
                        error=APIError(404, "No stocks found matching criteria")
                    )
            else:
                # Use specified exchanges
                if criteria.exchanges:
                    exchange_filter = ",".join(criteria.exchanges)
                    filters.append(["exchange", "=", exchange_filter])
                
                response = await self.client.screen_stocks(
                    filters=filters,
                    sort="market_capitalization.desc",
                    limit=eodhd_params.get('limit', 1000)
                )
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Update health and tracking
            self._update_health_from_response(response, latency_ms)
            self._request_count += 1
            if not response.is_success:
                self._error_count += 1
            
            # Cache successful results
            if response.is_success and response.data:
                self._cache_screening_result(cache_key, response.data)
                logger.info(f"Cached screening results for {self._screening_cache_ttl_hours} hours")
            
            # Add provider metadata
            metadata = ProviderMetadata.for_eodhd(latency_ms)
            return response.with_provider_metadata(metadata)
            
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
        
        EODHD includes Greeks in the options data, so this method
        extracts Greeks for a specific contract from the options chain.
        
        Args:
            option_symbol: Option contract symbol
            
        Returns:
            APIResponse containing option contract with Greeks or error
        """
        start_time = time.time()
        
        try:
            # Parse option symbol to get underlying
            underlying = self._parse_underlying_from_option_symbol(option_symbol)
            
            if not underlying:
                return self._create_error_response(
                    f"Cannot parse underlying symbol from option symbol: {option_symbol}"
                )
            
            # Get options chain (which includes Greeks in EODHD)
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
            metadata = ProviderMetadata.for_eodhd(latency_ms)
            
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
        Get current rate limit status.
        
        EODHD handles rate limiting server-side, so this returns
        basic information based on recent responses.
        
        Returns:
            RateLimitHeaders object or None if not available
        """
        return self._last_rate_limit  # Will be None for EODHD as they handle server-side
    
    def estimate_credits_required(self, operation: str, **kwargs) -> int:
        """
        Estimate API credits required for an operation.
        
        EODHD credit costs:
        - Stock screening: 5 credits per request (expensive!)
        - Options data: 1 credit per request
        - EOD quotes: 1 credit per request
        - Other endpoints: 1 credit per request
        
        Args:
            operation: Type of operation
            **kwargs: Operation-specific parameters
            
        Returns:
            Estimated number of API credits required
        """
        if operation == 'screen_stocks':
            # EODHD screening is expensive - 5 credits per request
            # If screening both NYSE and NASDAQ, it's 10 credits total
            exchanges = kwargs.get('criteria', ScreeningCriteria()).exchanges or ['NYSE', 'NASDAQ']
            if not exchanges or any(ex.upper() in ['US', 'NYSE', 'NASDAQ'] for ex in exchanges):
                return 10  # Both NYSE and NASDAQ
            else:
                return 5   # Single exchange
        
        elif operation == 'get_stock_quote':
            return 1
        
        elif operation == 'get_stock_quotes':
            symbols = kwargs.get('symbols', [])
            return len(symbols)
        
        elif operation == 'get_options_chain':
            return 1
        
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
    
    def _generate_screening_cache_key(self, criteria: ScreeningCriteria) -> str:
        """Generate cache key for screening criteria."""
        import hashlib
        import json
        
        # Create a stable representation of criteria
        criteria_dict = {
            'min_market_cap': str(criteria.min_market_cap) if criteria.min_market_cap else None,
            'max_market_cap': str(criteria.max_market_cap) if criteria.max_market_cap else None,
            'min_price': str(criteria.min_price) if criteria.min_price else None,
            'max_price': str(criteria.max_price) if criteria.max_price else None,
            'min_volume': criteria.min_volume,
            'min_avg_volume': criteria.min_avg_volume,
            'exchanges': sorted(criteria.exchanges) if criteria.exchanges else None,
            'exclude_etfs': criteria.exclude_etfs,
            'exclude_penny_stocks': criteria.exclude_penny_stocks
        }
        
        criteria_str = json.dumps(criteria_dict, sort_keys=True)
        return hashlib.md5(criteria_str.encode()).hexdigest()
    
    def _get_cached_screening_result(self, cache_key: str) -> Optional[Any]:
        """Get cached screening result if still valid."""
        if cache_key not in self._screening_cache:
            return None
        
        cache_entry = self._screening_cache[cache_key]
        cached_time = datetime.fromisoformat(cache_entry['timestamp'])
        age_hours = (datetime.now() - cached_time).total_seconds() / 3600
        
        if age_hours < self._screening_cache_ttl_hours:
            logger.debug(f"Using cached screening result (age: {age_hours:.1f} hours)")
            return cache_entry['data']
        else:
            # Remove expired entry
            del self._screening_cache[cache_key]
            return None
    
    def _cache_screening_result(self, cache_key: str, data: Any):
        """Cache screening result with timestamp."""
        self._screening_cache[cache_key] = {
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
    
    def _parse_underlying_from_option_symbol(self, option_symbol: str) -> Optional[str]:
        """
        Parse underlying symbol from option symbol.
        
        EODHD option symbols typically follow standard format.
        """
        try:
            # Simple parsing - find the first digit to separate underlying from rest
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
        # Clear caches
        self._screening_cache.clear()
        logger.info("EODHD provider closed")