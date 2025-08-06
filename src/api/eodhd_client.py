"""
EODHD Screener API client implementation.

This client handles authentication, rate limiting, error handling, and retry logic
for the EODHD Screener API as documented in eodhd-screener.md.

Key features:
- API token authentication
- Automatic rate limiting and retry logic
- Comprehensive error handling
- Support for stock screening by market cap and other criteria
- Filter-based screening for PMCC scanner requirements
"""

import asyncio
import logging
import os
import json
import urllib.parse
from typing import Optional, List, Dict, Any, Union
from urllib.parse import urljoin, urlencode
from decimal import Decimal
from datetime import datetime, timedelta
import concurrent.futures
import math
import hashlib

import aiohttp

# Rate limiting is handled server-side by EODHD - no local rate limiting needed
from src.models.api_models import (
    EODHDScreenerResponse, EODHDScreenerResult, APIResponse, APIError, APIStatus,
    OptionChain, OptionContract
)

logger = logging.getLogger(__name__)


class EODHDError(Exception):
    """Base exception for EODHD API errors."""
    
    def __init__(self, message: str, code: Optional[int] = None, 
                 retry_after: Optional[float] = None):
        super().__init__(message)
        self.code = code
        self.retry_after = retry_after


class EODHDAuthenticationError(EODHDError):
    """Authentication-related errors."""
    pass


class EODHDRateLimitError(EODHDError):
    """Rate limit exceeded errors."""
    pass


class EODHDQuotaError(EODHDError):
    """API quota/plan limit errors."""
    pass


class EODHDClient:
    """
    Async client for EODHD Screener API.
    
    Handles authentication, rate limiting, error handling, and provides
    methods for screening stocks by various criteria.
    """
    
    def __init__(self, 
                 api_token: Optional[str] = None,
                 base_url: Optional[str] = None,
                 timeout: float = 30.0,
                 max_retries: int = 3,
                 retry_backoff: float = 1.0,
                 enable_tradetime_filtering: bool = True,
                 tradetime_lookback_days: int = 5,
                 custom_tradetime_date: Optional[str] = None):
        """
        Initialize EODHD API client.
        
        Args:
            api_token: API authentication token. If None, will try to load from environment
            base_url: API base URL. Defaults to official EODHD API
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_backoff: Initial backoff delay for retries (exponential backoff)
            enable_tradetime_filtering: Enable/disable tradetime filtering globally
            tradetime_lookback_days: Number of days to look back for trading dates
            custom_tradetime_date: Override tradetime filter date for testing (YYYY-MM-DD format)
        """
        # API configuration
        self.api_token = api_token or os.getenv('EODHD_API_TOKEN')
        if not self.api_token:
            logger.warning("No EODHD API token provided. Screener requests will fail.")
        
        self.base_url = base_url or os.getenv('EODHD_API_BASE_URL', 
                                            'https://eodhd.com/api')
        if not self.base_url.endswith('/'):
            self.base_url += '/'
        
        # Request configuration
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        
        # Tradetime filtering configuration
        self.enable_tradetime_filtering = enable_tradetime_filtering
        self.tradetime_lookback_days = tradetime_lookback_days
        self.custom_tradetime_date = custom_tradetime_date
        
        # EODHD handles rate limiting server-side
        # No local rate limiting needed as per requirements
        
        # HTTP session (created lazily)
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Request statistics
        self._stats = {
            'requests_made': 0,
            'requests_failed': 0,
            'rate_limit_hits': 0,
            'retries_attempted': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        # Simple cache for options data to avoid redundant API calls
        self._options_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl_minutes = 60  # Default cache TTL
        
        logger.info("EODHD client initialized")
    
    def _get_tradetime_filter(self) -> Optional[str]:
        """
        Get tradetime filter date based on configuration settings.
        
        Returns:
            Tradetime filter date string or None if filtering is disabled
        """
        if not self.enable_tradetime_filtering:
            return None
        
        # Use custom date if provided
        if self.custom_tradetime_date:
            logger.debug(f"Using custom tradetime filter: {self.custom_tradetime_date}")
            return self.custom_tradetime_date
        
        # Use automatic date calculation
        try:
            from src.utils.trading_dates import get_eodhd_filter_date
            tradetime_from = get_eodhd_filter_date(lookback_days=self.tradetime_lookback_days)
            logger.debug(f"Using automatic tradetime filter (lookback {self.tradetime_lookback_days} days): {tradetime_from}")
            return tradetime_from
        except Exception as e:
            logger.warning(f"Could not get trading date filter, proceeding without: {e}")
            return None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def _ensure_session(self):
        """Ensure HTTP session is created."""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(
                limit=10,
                limit_per_host=10,
                ttl_dns_cache=300,
                use_dns_cache=True
            )
            
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=self.timeout,
                headers={
                    'User-Agent': 'PMCC-Scanner/1.0',
                    'Accept': 'application/json'
                }
            )
    
    async def close(self):
        """Close HTTP session and cleanup resources."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    def _build_filters(self, filters: List[List[Any]]) -> str:
        """
        Build EODHD filters parameter from filter list.
        
        Args:
            filters: List of filters in format [["field", "operation", value], ...]
            
        Returns:
            JSON-encoded filter string for EODHD API
        """
        try:
            return json.dumps(filters)
        except TypeError as e:
            logger.error(f"Failed to JSON encode filters {filters}: {e}")
            # Try to convert Decimal values
            converted_filters = []
            for f in filters:
                field, op, value = f
                if hasattr(value, '__float__'):
                    value = float(value)
                elif hasattr(value, '__int__'):
                    value = int(value)
                converted_filters.append([field, op, value])
            return json.dumps(converted_filters)
    
    def _create_api_error(self, status: int, data: Dict[str, Any]) -> APIError:
        """Create APIError from response data."""
        message = "Unknown API error"
        details = None
        
        if isinstance(data, dict):
            message = data.get('error', data.get('message', message))
            details = data.get('details')
        elif isinstance(data, str):
            message = data
        
        return APIError(
            code=status,
            message=str(message),
            details=str(details) if details else None
        )
    
    async def _make_request(self, 
                          endpoint: str, 
                          params: Optional[Dict[str, Any]] = None) -> APIResponse:
        """
        Make authenticated API request with rate limiting and error handling.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            APIResponse object with parsed data or error
        """
        await self._ensure_session()
        
        url = urljoin(self.base_url, endpoint)
        
        # Prepare request parameters
        request_params = params or {}
        request_params['api_token'] = self.api_token
        
        # Attempt request with retries
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                # EODHD handles rate limiting server-side
                # Make the request
                async with self._session.get(url, params=request_params) as response:
                    
                    # Update statistics
                    self._stats['requests_made'] += 1
                    
                    # Parse response
                    try:
                        response_data = await response.json()
                    except Exception:
                        # Handle non-JSON responses
                        response_text = await response.text()
                        response_data = {'error': f'Invalid JSON response: {response_text[:200]}'}
                    
                    # Handle response based on status code
                    if response.status == 200:
                        # Success
                        return APIResponse(
                            status=APIStatus.OK,
                            data=response_data,
                            raw_response=response_data
                        )
                    
                    elif response.status == 401:
                        # Authentication error
                        error = self._create_api_error(response.status, response_data)
                        raise EODHDAuthenticationError(
                            f"Authentication failed: {error.message}",
                            code=response.status
                        )
                    
                    elif response.status == 402:
                        # Payment required / plan limit
                        error = self._create_api_error(response.status, response_data)
                        raise EODHDQuotaError(
                            f"Plan limit exceeded: {error.message}",
                            code=response.status
                        )
                    
                    elif response.status == 429:
                        # Rate limit exceeded
                        self._stats['rate_limit_hits'] += 1
                        error = self._create_api_error(response.status, response_data)
                        
                        # Extract retry-after from headers
                        retry_after = None
                        if 'Retry-After' in response.headers:
                            try:
                                retry_after = float(response.headers['Retry-After'])
                            except ValueError:
                                retry_after = 60  # Default to 1 minute
                        
                        raise EODHDRateLimitError(
                            f"Rate limit exceeded: {error.message}",
                            code=response.status,
                            retry_after=retry_after
                        )
                    
                    elif response.status == 422:
                        # Unprocessable Entity - usually means bad parameters
                        logger.error(f"EODHD 422 error. URL: {url}, Params: {request_params}")
                        error = self._create_api_error(response.status, response_data)
                        return APIResponse(
                            status=APIStatus.ERROR,
                            error=error
                        )
                    
                    else:
                        # Other API error
                        error = self._create_api_error(response.status, response_data)
                        return APIResponse(
                            status=APIStatus.ERROR,
                            error=error,
                            raw_response=response_data
                        )
            
            
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                # Network errors
                last_exception = e
                if attempt < self.max_retries:
                    delay = self.retry_backoff * (2 ** attempt)
                    logger.warning(f"Request failed (attempt {attempt + 1}), retrying in {delay:.1f}s: {e}")
                    self._stats['retries_attempted'] += 1
                    await asyncio.sleep(delay)
                    continue
                else:
                    self._stats['requests_failed'] += 1
                    raise EODHDError(f"Request failed after {self.max_retries} retries: {e}")
            
            except Exception as e:
                # Unexpected errors
                last_exception = e
                logger.error(f"Unexpected error in API request: {e}")
                if attempt < self.max_retries:
                    delay = self.retry_backoff * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue
                else:
                    self._stats['requests_failed'] += 1
                    raise EODHDError(f"Unexpected error: {e}")
        
        # Should not reach here, but handle gracefully
        if last_exception:
            raise EODHDError(f"Request failed: {last_exception}")
        else:
            raise EODHDError("Request failed for unknown reason")
    
    async def screen_stocks(self, 
                           filters: Optional[List[List[Any]]] = None,
                           sort: Optional[str] = None,
                           limit: int = 50,
                           offset: int = 0) -> APIResponse:
        """
        Screen stocks using EODHD Screener API.
        
        Args:
            filters: List of filters in format [["field", "operation", value], ...]
            sort: Sort field and direction (e.g., "market_capitalization.desc")
            limit: Number of results to return (1-100)
            offset: Result offset for pagination
            
        Returns:
            APIResponse containing EODHDScreenerResponse or error
        """
        logger.debug(f"Screening stocks with {len(filters) if filters else 0} filters")
        
        # Build parameters
        params = {
            'limit': min(max(limit, 1), 100),  # Ensure limit is between 1-100
            'offset': max(offset, 0)  # Ensure offset is non-negative
        }
        
        if filters:
            params['filters'] = self._build_filters(filters)
            logger.info(f"EODHD screen_stocks filters: {params['filters']}")
        
        if sort:
            params['sort'] = sort
        
        # Make the request
        response = await self._make_request('screener', params=params)
        
        if response.is_success and response.data:
            try:
                screener_response = EODHDScreenerResponse.from_api_response(response.data)
                return APIResponse(
                    status=response.status,
                    data=screener_response,
                    raw_response=response.raw_response
                )
            except Exception as e:
                logger.error(f"Error parsing screener response: {e}")
                return APIResponse(
                    status=APIStatus.ERROR,
                    error=APIError(500, f"Error parsing response: {e}"),
                    raw_response=response.raw_response
                )
        
        return response
    
    async def screen_by_market_cap(self, 
                                 min_market_cap: int = 50_000_000,  # $50M
                                 max_market_cap: int = 5_000_000_000,  # $5B
                                 exchange: str = "us",
                                 min_volume: int = 100_000,  # Minimum daily volume
                                 limit: int = 100) -> APIResponse:
        """
        Screen US stocks by market capitalization range.
        
        This method implements the specific requirements for PMCC scanning:
        - Market cap between $50M and $5B
        - US exchange only
        - Sorted by market cap descending
        
        Args:
            min_market_cap: Minimum market cap in USD (default: $50M)
            max_market_cap: Maximum market cap in USD (default: $5B)
            exchange: Exchange filter (default: "us")
            limit: Number of results to return
            
        Returns:
            APIResponse containing list of stock symbols and data
        """
        logger.info(f"Screening stocks with market cap ${min_market_cap:,} - ${max_market_cap:,}")
        
        # Build base filters for market cap and volume
        base_filters = [
            ["market_capitalization", ">=", min_market_cap],
            ["market_capitalization", "<=", max_market_cap],
            ["avgvol_200d", ">=", min_volume]  # Average volume over 200 days
        ]
        
        # Sort by market cap descending to get larger companies first
        sort = "market_capitalization.desc"
        
        # Get NYSE stocks
        nyse_filters = base_filters + [["exchange", "=", "NYSE"]]
        nyse_response = await self.screen_stocks(
            filters=nyse_filters,
            sort=sort,
            limit=limit // 2,  # Half the limit for NYSE
            offset=0
        )
        
        # Get NASDAQ stocks
        nasdaq_filters = base_filters + [["exchange", "=", "NASDAQ"]]
        nasdaq_response = await self.screen_stocks(
            filters=nasdaq_filters,
            sort=sort,
            limit=limit // 2,  # Half the limit for NASDAQ
            offset=0
        )
        
        # Combine results
        if nyse_response.is_success and nasdaq_response.is_success:
            nyse_data = nyse_response.data
            nasdaq_data = nasdaq_response.data
            
            # Combine the results
            combined_results = []
            if hasattr(nyse_data, 'results'):
                combined_results.extend(nyse_data.results)
            if hasattr(nasdaq_data, 'results'):
                combined_results.extend(nasdaq_data.results)
            
            # Sort combined results by market cap
            combined_results.sort(key=lambda x: x.market_capitalization if hasattr(x, 'market_capitalization') else 0, reverse=True)
            
            # Create response with combined data
            from src.models.api_models import EODHDScreenerResponse
            combined_response = EODHDScreenerResponse(
                results=combined_results[:limit],  # Limit to requested amount
                total_count=len(combined_results),
                limit=limit
            )
            
            return APIResponse(
                status=APIStatus.OK,
                data=combined_response,
                raw_response={"combined": True, "nyse_count": len(nyse_data.results if hasattr(nyse_data, 'results') else []), 
                              "nasdaq_count": len(nasdaq_data.results if hasattr(nasdaq_data, 'results') else [])}
            )
        else:
            # Return whichever succeeded or first error
            return nyse_response if nyse_response.is_success else nasdaq_response
    
    async def get_pmcc_universe(self, limit: int = 100) -> List[str]:
        """
        Get list of stock symbols suitable for PMCC strategy.
        
        This is a convenience method that returns just the symbols
        for use with the MarketData API for options analysis.
        
        Args:
            limit: Maximum number of symbols to return
            
        Returns:
            List of stock ticker symbols
        """
        try:
            response = await self.screen_by_market_cap(limit=limit)
            
            if response.is_success and isinstance(response.data, EODHDScreenerResponse):
                symbols = response.data.get_symbols()
                logger.info(f"Retrieved {len(symbols)} symbols for PMCC universe")
                return symbols
            else:
                logger.error(f"Failed to get PMCC universe: {response.error}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting PMCC universe: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        stats = self._stats.copy()
        stats['cache_size'] = len(self._options_cache)
        # Rate limiting is handled server-side by EODHD
        return stats
    
    def _generate_cache_key(self, symbol: str, current_price: Optional[float] = None) -> str:
        """Generate cache key for PMCC options data."""
        # Include current price and date to ensure cache validity
        price_str = f"{current_price:.2f}" if current_price else "none"
        date_str = datetime.now().strftime('%Y-%m-%d')
        key_data = f"{symbol}_{price_str}_{date_str}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _is_cache_valid(self, cache_entry: Dict[str, Any], ttl_minutes: int) -> bool:
        """Check if cache entry is still valid."""
        if 'timestamp' not in cache_entry:
            return False
        
        cache_time = datetime.fromisoformat(cache_entry['timestamp'])
        age_minutes = (datetime.now() - cache_time).total_seconds() / 60
        return age_minutes < ttl_minutes
    
    def _get_cached_options(self, symbol: str, current_price: Optional[float], ttl_minutes: int) -> Optional[Dict[str, Any]]:
        """Get cached PMCC options data if valid."""
        cache_key = self._generate_cache_key(symbol, current_price)
        
        if cache_key in self._options_cache:
            cache_entry = self._options_cache[cache_key]
            if self._is_cache_valid(cache_entry, ttl_minutes):
                self._stats['cache_hits'] += 1
                logger.debug(f"Cache hit for {symbol} PMCC options")
                return cache_entry['data']
            else:
                # Remove expired entry
                del self._options_cache[cache_key]
        
        self._stats['cache_misses'] += 1
        return None
    
    def _cache_options(self, symbol: str, current_price: Optional[float], data: Dict[str, Any]):
        """Cache PMCC options data."""
        cache_key = self._generate_cache_key(symbol, current_price)
        self._options_cache[cache_key] = {
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        logger.debug(f"Cached PMCC options for {symbol}")
    
    def clear_cache(self):
        """Clear the options cache."""
        self._options_cache.clear()
        logger.info("Options cache cleared")
    
    async def get_options_eod(self,
                             symbol: str,
                             option_type: Optional[str] = None,
                             exp_date_from: Optional[str] = None,
                             exp_date_to: Optional[str] = None,
                             strike_from: Optional[float] = None,
                             strike_to: Optional[float] = None,
                             tradetime_from: Optional[str] = None,
                             limit: int = 1000) -> APIResponse:
        """
        Get end-of-day options data from EODHD Options API.
        
        Args:
            symbol: Underlying stock symbol
            option_type: Option type ("call" or "put"), None for both
            exp_date_from: Minimum expiration date (YYYY-MM-DD)
            exp_date_to: Maximum expiration date (YYYY-MM-DD)
            strike_from: Minimum strike price
            strike_to: Maximum strike price
            tradetime_from: Filter to only get options data from this trading date or later (YYYY-MM-DD).
                          If None, uses most recent trading date for better performance
            limit: Maximum number of contracts to return
            
        Returns:
            APIResponse containing options data or error
        """
        logger.debug(f"Getting options EOD data for {symbol}")
        
        # Handle tradetime filtering for better performance
        if tradetime_from is None:
            tradetime_from = self._get_tradetime_filter()
        else:
            logger.debug(f"Using provided tradetime filter: {tradetime_from}")
        
        # Build filter parameters
        params = {
            'filter[underlying_symbol]': symbol,
            'page[limit]': min(limit, 1000),  # API max is 1000
            'sort': 'exp_date'  # Sort by expiration date
        }
        
        # Add tradetime filter if available
        if tradetime_from:
            params['filter[tradetime_from]'] = tradetime_from
        
        if option_type:
            params['filter[type]'] = option_type.lower()
        
        if exp_date_from:
            params['filter[exp_date_from]'] = exp_date_from
            
        if exp_date_to:
            params['filter[exp_date_to]'] = exp_date_to
            
        if strike_from is not None:
            params['filter[strike_from]'] = strike_from
            
        if strike_to is not None:
            params['filter[strike_to]'] = strike_to
        
        # Make request to options endpoint
        return await self._make_request('mp/unicornbay/options/eod', params=params)
    
    async def get_pmcc_options_optimized(self,
                                       symbol: str,
                                       current_price: Optional[float] = None) -> APIResponse:
        """
        Get PMCC-relevant options using optimized filtering strategy.
        
        This method uses targeted date ranges to efficiently fetch only the 
        options needed for PMCC analysis, ensuring we get current market data.
        
        Args:
            symbol: Stock symbol to analyze
            current_price: Current stock price for strike filtering
            
        Returns:
            APIResponse containing combined LEAPS and short call options
        """
        logger.info(f"Fetching PMCC options for {symbol} with optimized filtering")
        
        # Calculate date ranges for PMCC strategy using next available expiration cycles
        from datetime import datetime, timedelta
        import calendar
        
        today = datetime.now()
        
        # For short calls: Target next 2-3 monthly expiration cycles (30-80 DTE)
        # This ensures we get current options with good liquidity
        short_min = today + timedelta(days=25)  # Start slightly earlier to catch monthly cycles
        short_max = today + timedelta(days=80)  # Extended to 80 DTE for more options
        
        # For LEAPS: Target 6-18 months out for better selection
        # Most LEAPS are January cycles, so target January dates
        current_year = today.year
        next_january = datetime(current_year + 1, 1, 1)
        if next_january < today + timedelta(days=180):  # If next Jan is too close
            next_january = datetime(current_year + 2, 1, 1)
        
        leaps_min = today + timedelta(days=180)  # Minimum 6 months for LEAPS
        leaps_max = next_january + timedelta(days=365)  # Up to year after next January
        
        all_options = []
        
        try:
            # Get tradetime filter for better performance
            tradetime_from = self._get_tradetime_filter()
            
            # Single optimized call: Get all relevant options with smart date range
            # Use a broader date range but with strike filtering to get current data efficiently
            params = {
                'filter[underlying_symbol]': symbol,
                'filter[type]': 'call',
                'filter[exp_date_from]': short_min.strftime('%Y-%m-%d'),
                'filter[exp_date_to]': leaps_max.strftime('%Y-%m-%d'),
                'sort': 'exp_date',
                'page[limit]': 1000
            }
            
            # Add tradetime filter if available
            if tradetime_from:
                params['filter[tradetime_from]'] = tradetime_from
            
            # Add strike filters if price is known to reduce API response size
            if current_price:
                # Get strikes from deep ITM (for LEAPS) to moderate OTM (for short calls)
                min_strike = current_price * 0.60  # Deep ITM for LEAPS
                max_strike = current_price * 1.30  # Moderate OTM for short calls
                params['filter[strike_from]'] = min_strike
                params['filter[strike_to]'] = max_strike
            
            logger.debug(f"Fetching options for {symbol} from {short_min.strftime('%Y-%m-%d')} to {leaps_max.strftime('%Y-%m-%d')}")
            if current_price:
                logger.debug(f"Strike range: {params.get('filter[strike_from]', 'N/A'):.2f} to {params.get('filter[strike_to]', 'N/A'):.2f}")
            
            response = await self._make_request('mp/unicornbay/options/eod', params=params)
            
            if response.is_success and response.data:
                options_data = response.data.get('data', [])
                logger.debug(f"Retrieved {len(options_data)} option contracts with tradetime filter: {tradetime_from}")
                
                # Separate and filter options by DTE and delta criteria
                leaps_count = 0
                short_count = 0
                
                for item in options_data:
                    if 'attributes' in item:
                        opt = item['attributes']
                        dte = opt.get('dte', 0)
                        delta = opt.get('delta', 0)
                        
                        # LEAPS criteria: 180+ DTE, delta >= 0.70
                        if dte >= 180 and delta >= 0.70:
                            all_options.append(opt)
                            leaps_count += 1
                        # Short call criteria: 25-80 DTE, delta 0.15-0.40
                        elif 25 <= dte <= 80 and 0.15 <= delta <= 0.40:
                            all_options.append(opt)
                            short_count += 1
                
                logger.debug(f"Filtered results: {leaps_count} LEAPS, {short_count} short calls")
            else:
                logger.warning(f"No options data returned for {symbol}")
            
            # Return combined results with metadata
            leaps_final = len([o for o in all_options if o.get('dte', 0) >= 180])
            short_final = len([o for o in all_options if 25 <= o.get('dte', 0) <= 80])
            
            return APIResponse(
                status=APIStatus.OK,
                data={
                    'symbol': symbol,
                    'options': all_options,
                    'leaps_count': leaps_final,
                    'short_count': short_final,
                    'total_options': len(all_options),
                    'date_range': {
                        'short_min': short_min.strftime('%Y-%m-%d'),
                        'short_max': short_max.strftime('%Y-%m-%d'),
                        'leaps_min': leaps_min.strftime('%Y-%m-%d'),
                        'leaps_max': leaps_max.strftime('%Y-%m-%d')
                    },
                    'strike_range': {
                        'min_strike': params.get('filter[strike_from]'),
                        'max_strike': params.get('filter[strike_to]'),
                        'current_price': current_price
                    },
                    'tradetime_filter': {
                        'tradetime_from': tradetime_from,
                        'filter_applied': tradetime_from is not None
                    },
                    'fetched_at': datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error fetching PMCC options for {symbol}: {e}")
            return APIResponse(
                status=APIStatus.ERROR,
                error=APIError(500, f"Error fetching PMCC options: {e}")
            )
    
    async def get_option_chain_eodhd(self, symbol: str) -> APIResponse:
        """
        Get option chain from EODHD in OptionChain format for compatibility.
        
        This method fetches options data efficiently using targeted date ranges
        to ensure we get the latest option data for PMCC analysis.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            APIResponse containing OptionChain object or error
        """
        try:
            # Get current stock price first for strike filtering
            quote_response = await self.get_stock_quote_eod(symbol)
            current_price = None
            if quote_response.is_success and quote_response.data:
                current_price = float(quote_response.data.last or quote_response.data.mid or 0)
            
            logger.debug(f"Current price for {symbol}: {current_price}")
            
            # Use the optimized PMCC method which is more efficient
            pmcc_response = await self.get_pmcc_options_optimized(symbol, current_price)
            
            if not pmcc_response.is_success:
                return pmcc_response
            
            # Convert PMCC optimized response to OptionChain format
            pmcc_data = pmcc_response.data
            options_list = pmcc_data.get('options', [])
            
            if not options_list:
                return APIResponse(
                    status=APIStatus.ERROR,
                    error=APIError(404, f"No options found for {symbol}")
                )
            
            # Create a fake response object with PMCC data in EODHD format
            # Convert back to EODHD API format for consistency
            eodhd_format_data = []
            for opt in options_list:
                eodhd_format_data.append({'attributes': opt})
            
            response = pmcc_response
            response.data = {'data': eodhd_format_data}
            logger.debug(f"Using optimized PMCC data: {len(eodhd_format_data)} contracts")
            
            if not response.is_success:
                return response
            
            # Convert EODHD response to OptionChain format
            eodhd_data = response.data.get('data', [])
            
            # Extract contracts
            contracts = []
            underlying_price = None
            
            # First pass: determine underlying price
            for item in eodhd_data:
                if 'attributes' in item:
                    opt_data = item['attributes']
                    
                    # Get underlying price from first contract (should be same for all)
                    if underlying_price is None and 'underlying_price' in opt_data:
                        underlying_price = Decimal(str(opt_data['underlying_price']))
                        break
            
            # If no underlying_price in options data, get it from quote
            if underlying_price is None:
                try:
                    quote_response = await self.get_stock_quote_eod(symbol)
                    if quote_response.is_success and quote_response.data:
                        underlying_price = quote_response.data.last or quote_response.data.mid
                except Exception:
                    pass
            
            # Second pass: create contracts with underlying price set
            for item in eodhd_data:
                if 'attributes' in item:
                    opt_data = item['attributes']
                    
                    # Convert EODHD option to OptionContract, passing underlying price
                    contract = OptionContract.from_eodhd_response(opt_data, underlying_price)
                    
                    contracts.append(contract)
            
            # Create OptionChain object
            option_chain = OptionChain(
                underlying=symbol,
                underlying_price=underlying_price,
                contracts=contracts,
                updated=datetime.now()
            )
            
            return APIResponse(
                status=APIStatus.OK,
                data=option_chain,
                raw_response=response.raw_response
            )
            
        except Exception as e:
            logger.error(f"Error converting EODHD options to OptionChain for {symbol}: {e}")
            return APIResponse(
                status=APIStatus.ERROR,
                error=APIError(500, f"Error converting options data: {e}")
            )

    async def get_eod_latest(self, symbol: str) -> APIResponse:
        """
        Get latest end-of-day quote for a symbol using EODHD historical data API.
        
        Args:
            symbol: Stock symbol (will be formatted as {symbol}.US for US stocks)
            
        Returns:
            APIResponse containing EOD quote data or error
        """
        logger.debug(f"Getting latest EOD quote for {symbol}")
        
        # Format symbol for US stocks
        eodhd_symbol = f"{symbol}.US" if not symbol.endswith('.US') else symbol
        
        # Get just the last few days to ensure we get the latest trading day
        from datetime import datetime, timedelta
        today = datetime.now()
        from_date = (today - timedelta(days=7)).strftime('%Y-%m-%d')  # Last 7 days
        
        # Build parameters
        params = {
            'fmt': 'json',  # Request JSON format
            'from': from_date  # Start from a week ago to ensure we get latest data
        }
        
        # Make request to EOD endpoint
        return await self._make_request(f'eod/{eodhd_symbol}', params=params)
    
    async def get_eod_historical(self, 
                                symbol: str,
                                from_date: Optional[str] = None,
                                to_date: Optional[str] = None,
                                period: str = 'd') -> APIResponse:
        """
        Get historical end-of-day data for a symbol.
        
        Args:
            symbol: Stock symbol (will be formatted as {symbol}.US for US stocks)
            from_date: Start date (YYYY-MM-DD format)
            to_date: End date (YYYY-MM-DD format)
            period: Data period ('d' for daily, 'w' for weekly, 'm' for monthly)
            
        Returns:
            APIResponse containing historical EOD data or error
        """
        logger.debug(f"Getting historical EOD data for {symbol}")
        
        # Format symbol for US stocks
        eodhd_symbol = f"{symbol}.US" if not symbol.endswith('.US') else symbol
        
        # Build parameters
        params = {
            'fmt': 'json',  # Request JSON format
            'period': period
        }
        
        if from_date:
            params['from'] = from_date
        if to_date:
            params['to'] = to_date
        
        # Make request to EOD historical endpoint
        return await self._make_request(f'eod/{eodhd_symbol}', params=params)
    
    async def get_stock_quote_eod(self, symbol: str) -> APIResponse:
        """
        Get stock quote from EODHD EOD data in StockQuote-compatible format.
        
        This method fetches the latest EOD data and converts it to a format
        compatible with the existing StockQuote model.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            APIResponse containing StockQuote-compatible data or error
        """
        try:
            # Get latest EOD data
            response = await self.get_eod_latest(symbol)
            
            if not response.is_success:
                return response
            
            eod_data = response.data
            
            # Convert EODHD EOD response to StockQuote format
            if isinstance(eod_data, list) and len(eod_data) > 0:
                # Historical endpoint returns array sorted by date, take the most recent (last)
                latest_data = eod_data[-1]  # Last item is most recent
            elif isinstance(eod_data, dict):
                # Latest endpoint returns single object
                latest_data = eod_data
            else:
                return APIResponse(
                    status=APIStatus.ERROR,
                    error=APIError(500, "Invalid EOD data format")
                )
            
            # Import StockQuote here to avoid circular imports
            from src.models.api_models import StockQuote
            
            # Extract data fields (EODHD EOD format)
            # Create arrays like MarketData API expects for compatibility with StockQuote.from_api_response
            quote_data = {
                'symbol': [symbol],  # Array format
                'last': [latest_data.get('adjusted_close', latest_data.get('close'))],
                'close': [latest_data.get('close')],
                'high': [latest_data.get('high')],
                'low': [latest_data.get('low')],
                'open': [latest_data.get('open')],
                'volume': [latest_data.get('volume')],
                'mid': [latest_data.get('adjusted_close', latest_data.get('close'))],  # Use close as mid
                'date': [latest_data.get('date')],  # Date field for parsing
                'bid': [None],  # EOD data doesn't include bid/ask
                'ask': [None],  # EOD data doesn't include bid/ask
                'change': [None],  # Would need to calculate from previous day
                'change_percent': [None],  # Would need to calculate from previous day
                'source': 'eodhd_eod'
            }
            
            # Convert to StockQuote object
            stock_quote = StockQuote.from_api_response(quote_data, index=0)
            
            return APIResponse(
                status=APIStatus.OK,
                data=stock_quote,
                raw_response=response.raw_response
            )
            
        except Exception as e:
            logger.error(f"Error getting EOD stock quote for {symbol}: {e}")
            return APIResponse(
                status=APIStatus.ERROR,
                error=APIError(500, f"Error getting EOD quote: {e}")
            )

    async def get_pmcc_options_fresh(self, symbol: str, current_price: Optional[float] = None) -> APIResponse:
        """
        Get PMCC-relevant options using granular date ranges to ensure fresh data.
        
        This method makes multiple targeted API calls with narrow date ranges
        to avoid the stale data issue that occurs with large date ranges.
        
        Args:
            symbol: Stock symbol to analyze
            current_price: Current stock price for strike filtering
            
        Returns:
            APIResponse containing PMCC-suitable options with fresh data
        """
        logger.info(f"Fetching fresh PMCC options for {symbol}")
        
        # Get current price if not provided
        if not current_price:
            try:
                quote_response = await self.get_stock_quote_eod(symbol)
                if quote_response.is_success and quote_response.data:
                    current_price = float(quote_response.data.last or quote_response.data.mid or 0)
            except Exception:
                logger.warning(f"Could not get current price for {symbol}")
        
        # Calculate date ranges using helper functions
        from datetime import datetime, timedelta
        
        def get_monthly_expiration(year: int, month: int) -> datetime:
            """Get the monthly option expiration date (3rd Friday)."""
            first_day = datetime(year, month, 1)
            first_friday = first_day
            while first_friday.weekday() != 4:  # 4 = Friday
                first_friday += timedelta(days=1)
            return first_friday + timedelta(weeks=2)
        
        today = datetime.now()
        short_ranges = []
        leaps_ranges = []
        
        # Calculate short call ranges (30-45 DTE)
        for i in range(3):  # Check next 3 months
            month = today.month + i + 1
            year = today.year
            if month > 12:
                month -= 12
                year += 1
            
            exp_date = get_monthly_expiration(year, month)
            dte = (exp_date - today).days
            
            if 25 <= dte <= 50:
                start = exp_date - timedelta(days=3)
                end = exp_date + timedelta(days=3)
                short_ranges.append((start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')))
        
        # Calculate LEAPS ranges (180-365 DTE)
        # Target January and quarterly expirations
        for target_month in [1, 3, 6, 9, 12]:
            for year_offset in range(2):
                year = today.year + year_offset
                if year == today.year and target_month <= today.month:
                    continue
                
                try:
                    exp_date = get_monthly_expiration(year, target_month)
                    dte = (exp_date - today).days
                    
                    if 180 <= dte <= 365:
                        start = exp_date - timedelta(days=5)
                        end = exp_date + timedelta(days=5)
                        leaps_ranges.append((start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')))
                except:
                    continue
        
        all_options = []
        api_calls = 0
        
        # Fetch short call candidates
        logger.debug(f"Fetching short calls across {len(short_ranges)} date ranges")
        
        for start_date, end_date in short_ranges:
            params = {
                'filter[underlying_symbol]': symbol,
                'filter[type]': 'call',
                'filter[exp_date_from]': start_date,
                'filter[exp_date_to]': end_date,
                'page[limit]': 500,
                'sort': 'strike'
            }
            
            if current_price:
                # Short calls: ATM to 20% OTM
                params['filter[strike_from]'] = current_price * 0.95
                params['filter[strike_to]'] = current_price * 1.20
            
            response = await self._make_request('mp/unicornbay/options/eod', params=params)
            api_calls += 1
            
            if response.is_success and response.data:
                options_data = response.data.get('data', [])
                logger.debug(f"Date range {start_date} to {end_date}: {len(options_data)} options")
                
                for item in options_data:
                    if 'attributes' in item:
                        opt = item['attributes']
                        delta = opt.get('delta', 0)
                        dte = opt.get('dte', 0)
                        
                        if 30 <= dte <= 45 and 0.15 <= delta <= 0.40:
                            opt['option_type'] = 'short'
                            all_options.append(opt)
        
        # Fetch LEAPS candidates
        logger.debug(f"Fetching LEAPS across {len(leaps_ranges)} date ranges")
        
        for start_date, end_date in leaps_ranges:
            params = {
                'filter[underlying_symbol]': symbol,
                'filter[type]': 'call',
                'filter[exp_date_from]': start_date,
                'filter[exp_date_to]': end_date,
                'page[limit]': 500,
                'sort': 'strike'
            }
            
            if current_price:
                # LEAPS: Deep ITM
                params['filter[strike_from]'] = current_price * 0.60
                params['filter[strike_to]'] = current_price * 0.85
            
            response = await self._make_request('mp/unicornbay/options/eod', params=params)
            api_calls += 1
            
            if response.is_success and response.data:
                options_data = response.data.get('data', [])
                logger.debug(f"Date range {start_date} to {end_date}: {len(options_data)} options")
                
                for item in options_data:
                    if 'attributes' in item:
                        opt = item['attributes']
                        delta = opt.get('delta', 0)
                        dte = opt.get('dte', 0)
                        
                        if dte >= 180 and delta >= 0.70:
                            opt['option_type'] = 'leaps'
                            all_options.append(opt)
        
        logger.info(f"Completed {api_calls} API calls, found {len(all_options)} PMCC candidates")
        
        return APIResponse(
            status=APIStatus.OK,
            data={
                'symbol': symbol,
                'current_price': current_price,
                'options': all_options,
                'short_calls': len([o for o in all_options if o.get('option_type') == 'short']),
                'leaps': len([o for o in all_options if o.get('option_type') == 'leaps']),
                'api_calls': api_calls,
                'fetched_at': datetime.now().isoformat()
            }
        )

    def get_weekly_expirations(self, start_date: datetime, weeks: int = 24) -> List[datetime]:
        """
        Generate weekly Friday expirations starting from the next Friday.
        
        Args:
            start_date: Starting date to calculate from
            weeks: Number of weekly expirations to generate
            
        Returns:
            List of Friday expiration dates
        """
        expirations = []
        
        # Find next Friday from start_date
        current = start_date
        days_until_friday = (4 - current.weekday()) % 7  # 4 = Friday
        if days_until_friday == 0 and current.hour >= 16:  # If it's Friday after market close
            days_until_friday = 7
        
        next_friday = current + timedelta(days=days_until_friday)
        
        # Generate weekly Fridays
        for i in range(weeks):
            expirations.append(next_friday + timedelta(weeks=i))
        
        return expirations
    
    def calculate_strike_targets(self, current_price: float, option_type: str) -> List[float]:
        """
        Calculate specific strike prices based on current price and option type.
        
        Args:
            current_price: Current stock price
            option_type: 'leaps' or 'short'
            
        Returns:
            List of target strike prices
        """
        def round_strike(price: float) -> float:
            """Round strike price based on price level."""
            if price < 10:
                return round(price * 2) / 2  # Round to nearest $0.50
            elif price < 25:
                return round(price)  # Round to nearest $1.00
            elif price < 100:
                return round(price / 2.5) * 2.5  # Round to nearest $2.50
            else:
                return round(price / 5) * 5  # Round to nearest $5.00
        
        strikes = []
        
        if option_type == 'leaps':
            # LEAPS: Deep ITM strikes with delta 0.70-0.95
            # Target strikes from 60% to 85% of current price
            for percentage in [0.60, 0.70, 0.80, 0.85]:
                strike = round_strike(current_price * percentage)
                if strike not in strikes:
                    strikes.append(strike)
        elif option_type == 'short':
            # Short calls: OTM strikes with delta 0.15-0.40
            # Target strikes from 105% to 125% of current price
            for percentage in [1.05, 1.10, 1.15, 1.20]:
                strike = round_strike(current_price * percentage)
                if strike not in strikes:
                    strikes.append(strike)
        
        return sorted(strikes)
    
    def generate_pmcc_targets(self, current_price: float) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generate all option targets for PMCC strategy.
        
        Args:
            current_price: Current stock price
            
        Returns:
            Dictionary with 'leaps' and 'short' target lists
        """
        today = datetime.now()
        
        # Generate expiration dates
        leaps_expirations = self.get_weekly_expirations(today + timedelta(days=180), 24)  # 6+ months out
        short_expirations = self.get_weekly_expirations(today + timedelta(days=25), 4)   # ~1 month out
        
        # Generate strike prices
        leaps_strikes = self.calculate_strike_targets(current_price, 'leaps')
        short_strikes = self.calculate_strike_targets(current_price, 'short')
        
        targets = {'leaps': [], 'short': []}
        
        # Generate LEAPS targets (24 expirations × 4 strikes = 96 targets)
        for exp_date in leaps_expirations:
            for strike in leaps_strikes:
                targets['leaps'].append({
                    'expiration': exp_date.strftime('%Y-%m-%d'),
                    'strike': strike,
                    'type': 'call'
                })
        
        # Generate short call targets (4 expirations × 4 strikes = 16 targets)
        for exp_date in short_expirations:
            for strike in short_strikes:
                targets['short'].append({
                    'expiration': exp_date.strftime('%Y-%m-%d'),
                    'strike': strike,
                    'type': 'call'
                })
        
        logger.debug(f"Generated {len(targets['leaps'])} LEAPS targets and {len(targets['short'])} short call targets")
        return targets
    
    async def get_pmcc_options_comprehensive(self, 
                                         symbol: str, 
                                         current_price: Optional[float] = None,
                                         batch_size: int = 10,
                                         batch_delay: float = 1.0,
                                         min_success_rate: float = 50.0,
                                         retry_failed: bool = True,
                                         enable_caching: bool = True,
                                         cache_ttl_minutes: int = 60) -> APIResponse:
        """
        Get comprehensive PMCC options using targeted retrieval strategy.
        
        This method implements a comprehensive approach to fetch PMCC-suitable options:
        - Generates 96 LEAPS targets (24 weekly expirations × 4 strikes)
        - Generates 16 short call targets (4 weekly expirations × 4 strikes)
        - Fetches each option with a 3-day date window
        - Processes requests in batches to avoid overwhelming the API
        - Returns comprehensive results with all PMCC opportunities
        
        Args:
            symbol: Stock symbol to analyze
            current_price: Current stock price for strike targeting
            batch_size: Number of options to process per batch
            batch_delay: Delay in seconds between batches
            min_success_rate: Minimum success rate (%) to consider operation successful
            retry_failed: Whether to retry failed option requests
            
        Returns:
            APIResponse containing comprehensive PMCC options data
        """
        logger.info(f"Starting comprehensive PMCC option retrieval for {symbol}")
        
        # Get tradetime filter for consistent filtering across all batch calls
        tradetime_from = self._get_tradetime_filter()
        if tradetime_from:
            logger.info(f"Using tradetime filter for comprehensive {symbol} retrieval: {tradetime_from}")
        
        # Check cache first if enabled
        if enable_caching:
            cached_data = self._get_cached_options(symbol, current_price, cache_ttl_minutes)
            if cached_data:
                logger.info(f"Returning cached PMCC options for {symbol}")
                return APIResponse(
                    status=APIStatus.OK,
                    data=cached_data
                )
        
        # Get current price if not provided
        if not current_price:
            try:
                quote_response = await self.get_stock_quote_eod(symbol)
                if quote_response.is_success and quote_response.data:
                    current_price = float(quote_response.data.last or quote_response.data.mid or 0)
                    logger.debug(f"Retrieved current price for {symbol}: ${current_price:.2f}")
                else:
                    return APIResponse(
                        status=APIStatus.ERROR,
                        error=APIError(400, f"Could not get current price for {symbol}")
                    )
            except Exception as e:
                logger.error(f"Error getting current price for {symbol}: {e}")
                return APIResponse(
                    status=APIStatus.ERROR,
                    error=APIError(500, f"Error getting current price: {e}")
                )
        
        # Generate all target options
        targets = self.generate_pmcc_targets(current_price)
        total_targets = len(targets['leaps']) + len(targets['short'])
        logger.info(f"Generated {total_targets} option targets ({len(targets['leaps'])} LEAPS, {len(targets['short'])} short calls)")
        
        # Use provided batch configuration
        
        all_options = []
        successful_requests = 0
        failed_requests = 0
        
        async def fetch_option_batch(option_targets: List[Dict[str, Any]], option_type: str) -> List[Dict[str, Any]]:
            """Fetch a batch of options concurrently."""
            nonlocal successful_requests, failed_requests
            batch_options = []
            
            # Create tasks for concurrent execution
            tasks = []
            for target in option_targets:
                exp_date = datetime.strptime(target['expiration'], '%Y-%m-%d')
                
                # 3-day window around target expiration
                start_date = (exp_date - timedelta(days=3)).strftime('%Y-%m-%d')
                end_date = (exp_date + timedelta(days=3)).strftime('%Y-%m-%d')
                
                params = {
                    'filter[underlying_symbol]': symbol,
                    'filter[type]': target['type'],
                    'filter[exp_date_from]': start_date,
                    'filter[exp_date_to]': end_date,
                    'filter[strike_from]': target['strike'] - 0.5,
                    'filter[strike_to]': target['strike'] + 0.5,
                    'page[limit]': 50,
                    'sort': 'exp_date'
                }
                
                # Add tradetime filter if available for consistent filtering
                if tradetime_from:
                    params['filter[tradetime_from]'] = tradetime_from
                
                task = self._make_request('mp/unicornbay/options/eod', params=params)
                tasks.append((task, target, option_type))
            
            # Execute batch concurrently
            results = await asyncio.gather(*[task for task, _, _ in tasks], return_exceptions=True)
            
            # Process results
            for i, result in enumerate(results):
                _, target, opt_type = tasks[i]
                
                if isinstance(result, Exception):
                    logger.warning(f"Failed to fetch {opt_type} option {target['strike']} exp {target['expiration']}: {result}")
                    failed_requests += 1
                    continue
                
                if result.is_success and result.data:
                    options_data = result.data.get('data', [])
                    
                    for item in options_data:
                        if 'attributes' in item:
                            opt = item['attributes']
                            
                            # Validate option meets PMCC criteria
                            delta = opt.get('delta', 0)
                            dte = opt.get('dte', 0)
                            strike = opt.get('strike', 0)
                            
                            if opt_type == 'leaps':
                                if dte >= 180 and delta >= 0.70 and abs(strike - target['strike']) <= 2.5:
                                    opt['pmcc_type'] = 'leaps'
                                    opt['target_strike'] = target['strike']
                                    opt['target_expiration'] = target['expiration']
                                    batch_options.append(opt)
                                    successful_requests += 1
                            elif opt_type == 'short':
                                if 25 <= dte <= 50 and 0.15 <= delta <= 0.40 and abs(strike - target['strike']) <= 2.5:
                                    opt['pmcc_type'] = 'short'
                                    opt['target_strike'] = target['strike']
                                    opt['target_expiration'] = target['expiration']
                                    batch_options.append(opt)
                                    successful_requests += 1
                else:
                    logger.debug(f"No data for {opt_type} option {target['strike']} exp {target['expiration']}")
                    failed_requests += 1
            
            return batch_options
        
        # Process LEAPS in batches
        logger.info(f"Processing {len(targets['leaps'])} LEAPS targets in batches of {batch_size}")
        leaps_batches = [targets['leaps'][i:i + batch_size] for i in range(0, len(targets['leaps']), batch_size)]
        
        for i, batch in enumerate(leaps_batches):
            logger.debug(f"Processing LEAPS batch {i + 1}/{len(leaps_batches)} ({len(batch)} options)")
            batch_options = await fetch_option_batch(batch, 'leaps')
            all_options.extend(batch_options)
            
            # Delay between batches to avoid overwhelming API
            if i < len(leaps_batches) - 1:
                await asyncio.sleep(batch_delay)
        
        # Process short calls in batches
        logger.info(f"Processing {len(targets['short'])} short call targets in batches of {batch_size}")
        short_batches = [targets['short'][i:i + batch_size] for i in range(0, len(targets['short']), batch_size)]
        
        for i, batch in enumerate(short_batches):
            logger.debug(f"Processing short call batch {i + 1}/{len(short_batches)} ({len(batch)} options)")
            batch_options = await fetch_option_batch(batch, 'short')
            all_options.extend(batch_options)
            
            # Delay between batches to avoid overwhelming API
            if i < len(short_batches) - 1:
                await asyncio.sleep(batch_delay)
        
        # Separate options by type for reporting
        leaps_options = [opt for opt in all_options if opt.get('pmcc_type') == 'leaps']
        short_options = [opt for opt in all_options if opt.get('pmcc_type') == 'short']
        
        logger.info(f"Comprehensive PMCC retrieval completed for {symbol}:")
        logger.info(f"  - Found {len(leaps_options)} LEAPS options")
        logger.info(f"  - Found {len(short_options)} short call options")
        logger.info(f"  - Success rate: {successful_requests}/{successful_requests + failed_requests} ({100 * successful_requests / (successful_requests + failed_requests) if successful_requests + failed_requests > 0 else 0:.1f}%)")
        
        # Build response data
        response_data = {
            'symbol': symbol,
            'current_price': current_price,
            'options': all_options,
            'leaps_options': leaps_options,
            'short_options': short_options,
            'summary': {
                'total_options': len(all_options),
                'leaps_count': len(leaps_options),
                'short_count': len(short_options),
                'targets_generated': total_targets,
                'successful_requests': successful_requests,
                'failed_requests': failed_requests,
                'success_rate': round(100 * successful_requests / (successful_requests + failed_requests) if successful_requests + failed_requests > 0 else 0, 1)
            },
            'targets': targets,
            'tradetime_filter': {
                'tradetime_from': tradetime_from,
                'filter_applied': tradetime_from is not None,
                'note': 'All batch requests used this tradetime filter for consistency'
            },
            'fetched_at': datetime.now().isoformat()
        }
        
        # Cache the results if caching is enabled and we have good data
        if enable_caching and len(all_options) > 0:
            self._cache_options(symbol, current_price, response_data)
        
        return APIResponse(
            status=APIStatus.OK,
            data=response_data
        )

    async def health_check(self) -> bool:
        """
        Perform a health check of the API connection.
        
        Returns:
            True if API is accessible, False otherwise
        """
        try:
            # Try a minimal screener request
            response = await self.screen_stocks(
                filters=[["exchange", "=", "us"]],
                limit=1
            )
            return response.is_success
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False