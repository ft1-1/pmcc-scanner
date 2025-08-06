"""
MarketData.app API client implementation.

This client handles authentication, error handling, and retry logic
for the MarketData.app API as documented in marketdata_api_docs.md.

Key features:
- Bearer token authentication
- Comprehensive error handling
- Support for stock quotes and options chains
- Batch request processing for daily scans
- Rate limiting handled by the API itself
"""

import asyncio
import logging
import os
from typing import Optional, List, Dict, Any, Union
from urllib.parse import urljoin, urlencode
import aiohttp
import json
from datetime import datetime

from src.models.api_models import (
    StockQuote, OptionChain, APIResponse, APIError, APIStatus, RateLimitHeaders
)

logger = logging.getLogger(__name__)


class MarketDataError(Exception):
    """Base exception for MarketData API errors."""
    
    def __init__(self, message: str, code: Optional[int] = None, 
                 retry_after: Optional[float] = None):
        super().__init__(message)
        self.code = code
        self.retry_after = retry_after


class AuthenticationError(MarketDataError):
    """Authentication-related errors."""
    pass


class RateLimitError(MarketDataError):
    """Rate limit exceeded errors."""
    pass


class APIQuotaError(MarketDataError):
    """API quota/plan limit errors."""
    pass


class MarketDataClient:
    """
    Async client for MarketData.app API.
    
    Handles authentication, error handling, and provides methods for 
    fetching stock quotes and options chains. Rate limiting is handled
    by the API itself.
    """
    
    def __init__(self, 
                 api_token: Optional[str] = None,
                 base_url: Optional[str] = None,
                 timeout: float = 30.0,
                 max_retries: int = 3,
                 retry_backoff: float = 1.0):
        """
        Initialize MarketData API client.
        
        Args:
            api_token: API authentication token. If None, will try to load from environment
            base_url: API base URL. Defaults to official MarketData.app API
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_backoff: Initial backoff delay for retries (exponential backoff)
        """
        # API configuration
        self.api_token = api_token or os.getenv('MARKETDATA_API_TOKEN')
        if not self.api_token:
            logger.warning("No API token provided. Some endpoints may not be accessible.")
        
        self.base_url = base_url or os.getenv('MARKETDATA_API_BASE_URL', 
                                            'https://api.marketdata.app/v1')
        if not self.base_url.endswith('/'):
            self.base_url += '/'
        
        # Request configuration
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        
        # HTTP session (created lazily)
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Request statistics
        self._stats = {
            'requests_made': 0,
            'requests_failed': 0,
            'rate_limit_hits': 0,
            'retries_attempted': 0
        }
        
        logger.info("MarketData client initialized")
    
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
                limit=50,
                limit_per_host=50,
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
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers."""
        headers = {}
        if self.api_token:
            headers['Authorization'] = f'Bearer {self.api_token}'
        return headers
    
    def _parse_rate_limit_headers(self, headers: Dict[str, str]) -> RateLimitHeaders:
        """Parse rate limit headers from response."""
        def safe_int(value: str) -> Optional[int]:
            try:
                return int(value) if value else None
            except (ValueError, TypeError):
                return None
        
        return RateLimitHeaders(
            limit=safe_int(headers.get('X-Api-Ratelimit-Limit')),
            remaining=safe_int(headers.get('X-Api-Ratelimit-Remaining')),
            reset=safe_int(headers.get('X-Api-Ratelimit-Reset')),
            consumed=safe_int(headers.get('X-Api-Ratelimit-Consumed'))
        )
    
    def _create_api_error(self, status: int, data: Dict[str, Any]) -> APIError:
        """Create APIError from response data."""
        # Try to extract error message from various response formats
        message = "Unknown API error"
        details = None
        
        if isinstance(data, dict):
            # Standard error format
            message = data.get('error', data.get('message', message))
            details = data.get('details')
            
            # Sometimes error is in 's' field
            if data.get('s') == 'error':
                message = data.get('errmsg', message)
        
        return APIError(
            code=status,
            message=str(message),
            details=str(details) if details else None
        )
    
    async def _make_request(self, 
                          endpoint: str, 
                          params: Optional[Dict[str, Any]] = None) -> APIResponse:
        """
        Make authenticated API request with error handling and retries.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            APIResponse object with parsed data or error
        """
        await self._ensure_session()
        
        url = urljoin(self.base_url, endpoint)
        if not url.endswith('/'):
            url += '/'
        
        # Prepare request parameters
        request_params = params or {}
        headers = self._get_auth_headers()
        
        # Attempt request with retries
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                # Make the request
                async with self._session.get(url, params=request_params, 
                                           headers=headers) as response:
                    
                    # Update statistics
                    self._stats['requests_made'] += 1
                    
                    # Parse response
                    try:
                        response_data = await response.json()
                    except Exception:
                        # Handle non-JSON responses
                        response_text = await response.text()
                        response_data = {'error': f'Invalid JSON response: {response_text[:200]}'}
                    
                    # Parse rate limit headers
                    rate_limit = self._parse_rate_limit_headers(dict(response.headers))
                    
                    # Handle response based on status code
                    if response.status == 200:
                        # Success
                        return APIResponse(
                            status=APIStatus.OK,
                            data=response_data,
                            rate_limit=rate_limit,
                            raw_response=response_data
                        )
                    
                    elif response.status == 203:
                        # Success with cached data
                        return APIResponse(
                            status=APIStatus.OK,
                            data=response_data,
                            rate_limit=rate_limit,
                            raw_response=response_data
                        )
                    
                    elif response.status == 204:
                        # No cached data available for this symbol
                        # Per docs: Make a live request to fetch real-time data
                        logger.info(f"No cached data for endpoint, would need live request")
                        return APIResponse(
                            status=APIStatus.NO_DATA,
                            error=APIError(204, "No cached data available, use live feed"),
                            rate_limit=rate_limit,
                            raw_response=None
                        )
                    
                    elif response.status == 401:
                        # Authentication error
                        error = self._create_api_error(response.status, response_data)
                        raise AuthenticationError(
                            f"Authentication failed: {error.message}",
                            code=response.status
                        )
                    
                    elif response.status == 402:
                        # Payment required / plan limit
                        error = self._create_api_error(response.status, response_data)
                        raise APIQuotaError(
                            f"Plan limit exceeded: {error.message}",
                            code=response.status
                        )
                    
                    elif response.status == 429:
                        # Rate limit exceeded
                        self._stats['rate_limit_hits'] += 1
                        error = self._create_api_error(response.status, response_data)
                        
                        # Extract retry-after from headers or rate limit info
                        retry_after = None
                        if 'Retry-After' in response.headers:
                            try:
                                retry_after = float(response.headers['Retry-After'])
                            except ValueError:
                                pass
                        elif rate_limit.reset:
                            retry_after = max(0, rate_limit.reset - datetime.now().timestamp())
                        
                        raise RateLimitError(
                            f"Rate limit exceeded: {error.message}",
                            code=response.status,
                            retry_after=retry_after
                        )
                    
                    else:
                        # Other API error
                        error = self._create_api_error(response.status, response_data)
                        return APIResponse(
                            status=APIStatus.ERROR,
                            error=error,
                            rate_limit=rate_limit,
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
                    raise MarketDataError(f"Request failed after {self.max_retries} retries: {e}")
            
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
                    raise MarketDataError(f"Unexpected error: {e}")
        
        # Should not reach here, but handle gracefully
        if last_exception:
            raise MarketDataError(f"Request failed: {last_exception}")
        else:
            raise MarketDataError("Request failed for unknown reason")
    
    async def get_stock_quote(self, symbol: str) -> APIResponse:
        """
        Get stock quote for a single symbol.
        
        Args:
            symbol: Stock ticker symbol (e.g., 'AAPL')
            
        Returns:
            APIResponse containing StockQuote data or error
        """
        logger.debug(f"Fetching stock quote for {symbol}")
        
        response = await self._make_request(f'stocks/quotes/{symbol}')
        
        if response.is_success and response.data:
            try:
                quote = StockQuote.from_api_response(response.data)
                return APIResponse(
                    status=response.status,
                    data=quote,
                    rate_limit=response.rate_limit,
                    raw_response=response.raw_response
                )
            except Exception as e:
                logger.error(f"Error parsing stock quote for {symbol}: {e}")
                return APIResponse(
                    status=APIStatus.ERROR,
                    error=APIError(500, f"Error parsing response: {e}"),
                    rate_limit=response.rate_limit,
                    raw_response=response.raw_response
                )
        
        return response
    
    async def get_stock_quotes(self, symbols: List[str]) -> Dict[str, APIResponse]:
        """
        Get stock quotes for multiple symbols.
        
        Args:
            symbols: List of stock ticker symbols
            
        Returns:
            Dictionary mapping symbols to their APIResponse objects
        """
        logger.info(f"Fetching stock quotes for {len(symbols)} symbols")
        
        # Create tasks for concurrent requests (respecting rate limits)
        tasks = []
        for symbol in symbols:
            task = asyncio.create_task(self.get_stock_quote(symbol))
            tasks.append((symbol, task))
        
        # Wait for all requests to complete
        results = {}
        for symbol, task in tasks:
            try:
                results[symbol] = await task
            except Exception as e:
                logger.error(f"Error fetching quote for {symbol}: {e}")
                results[symbol] = APIResponse(
                    status=APIStatus.ERROR,
                    error=APIError(500, f"Request failed: {e}")
                )
        
        return results
    
    async def get_option_chain(self, 
                              symbol: str,
                              expiration: Optional[str] = None,
                              side: Optional[str] = None,
                              strike_limit: Optional[int] = None,
                              min_dte: Optional[int] = None,
                              max_dte: Optional[int] = None,
                              from_date: Optional[str] = None,
                              to_date: Optional[str] = None,
                              delta_range: Optional[str] = None,
                              min_open_interest: Optional[int] = None,
                              min_volume: Optional[int] = None,
                              use_cached_feed: bool = True) -> APIResponse:
        """
        Get option chain for a symbol with optimized filtering.
        
        Args:
            symbol: Underlying stock symbol
            expiration: Specific expiration date (YYYY-MM-DD format)
            side: Option side ('call' or 'put')
            strike_limit: Limit number of strikes returned
            min_dte: Minimum days to expiration (legacy, use from_date/to_date)
            max_dte: Maximum days to expiration (legacy, use from_date/to_date)
            from_date: Start date for expiration range (YYYY-MM-DD)
            to_date: End date for expiration range (YYYY-MM-DD)
            delta_range: Delta range filter (e.g., '.70-.95' for LEAPS)
            min_open_interest: Minimum open interest filter
            min_volume: Minimum volume filter
            use_cached_feed: Use cached feed (1 credit) vs live (1 credit per contract)
            
        Returns:
            APIResponse containing OptionChain data or error
        """
        logger.debug(f"Fetching option chain for {symbol}")
        
        # Build parameters
        params = {}
        if expiration:
            params['expiration'] = expiration
        elif from_date and to_date:
            # Use date range for better API efficiency
            params['from'] = from_date
            params['to'] = to_date
        elif min_dte and max_dte:
            # Convert legacy DTE to date range
            from datetime import datetime, timedelta
            today = datetime.now().date()
            params['from'] = (today + timedelta(days=min_dte)).isoformat()
            params['to'] = (today + timedelta(days=max_dte)).isoformat()
        
        if side:
            params['side'] = side
        if strike_limit:
            params['strikeLimit'] = strike_limit
        if delta_range:
            params['delta'] = delta_range
        if min_open_interest:
            params['minOpenInterest'] = min_open_interest
        if min_volume:
            params['minVolume'] = min_volume
        
        # Use cached feed by default to minimize API credit usage
        # Cached feed: 1 credit per API call regardless of number of contracts
        # Live feed: 1 credit per option symbol (can be thousands for SPX)
        if use_cached_feed:
            params['feed'] = 'cached'
        
        response = await self._make_request(f'options/chain/{symbol}', params=params)
        
        if response.is_success and response.data:
            try:
                chain = OptionChain.from_api_response(response.data)
                return APIResponse(
                    status=response.status,
                    data=chain,
                    rate_limit=response.rate_limit,
                    raw_response=response.raw_response
                )
            except Exception as e:
                logger.error(f"Error parsing option chain for {symbol}: {e}")
                return APIResponse(
                    status=APIStatus.ERROR,
                    error=APIError(500, f"Error parsing response: {e}"),
                    rate_limit=response.rate_limit,
                    raw_response=response.raw_response
                )
        
        return response
    
    async def get_pmcc_option_chains(self, symbol: str) -> Dict[str, APIResponse]:
        """
        Get optimized option chains for PMCC analysis.
        
        Makes two efficient API calls:
        1. LEAPS calls (6-12 months, delta 0.70-0.95)
        2. Short calls (21-45 days, delta 0.15-0.40)
        
        Args:
            symbol: Underlying stock symbol
            
        Returns:
            Dict with 'leaps' and 'short' APIResponse objects
        """
        from datetime import datetime, timedelta
        today = datetime.now().date()
        
        # LEAPS parameters (6-12 months out, deep ITM)
        leaps_params = {
            'from': (today + timedelta(days=180)).isoformat(),  # 6 months
            'to': (today + timedelta(days=365)).isoformat(),    # 12 months
            'side': 'call',
            'delta': '.70-.95',  # Deep ITM
            'minOpenInterest': 10,
            'minVolume': 1,
            'feed': 'cached'
        }
        
        # Short call parameters (21-45 days out, OTM)
        short_params = {
            'from': (today + timedelta(days=21)).isoformat(),   # 3 weeks
            'to': (today + timedelta(days=45)).isoformat(),     # 6 weeks
            'side': 'call',
            'delta': '.15-.40',  # OTM
            'minOpenInterest': 5,
            'feed': 'cached'
        }
        
        # Make both requests concurrently
        leaps_task = self._make_request(f'options/chain/{symbol}', params=leaps_params)
        short_task = self._make_request(f'options/chain/{symbol}', params=short_params)
        
        leaps_response, short_response = await asyncio.gather(leaps_task, short_task)
        
        # Parse responses
        results = {}
        
        if leaps_response.is_success and leaps_response.data:
            try:
                chain = OptionChain.from_api_response(leaps_response.data)
                results['leaps'] = APIResponse(
                    status=leaps_response.status,
                    data=chain,
                    rate_limit=leaps_response.rate_limit,
                    raw_response=leaps_response.raw_response
                )
            except Exception as e:
                logger.error(f"Error parsing LEAPS chain for {symbol}: {e}")
                results['leaps'] = leaps_response
        else:
            results['leaps'] = leaps_response
            
        if short_response.is_success and short_response.data:
            try:
                chain = OptionChain.from_api_response(short_response.data)
                results['short'] = APIResponse(
                    status=short_response.status,
                    data=chain,
                    rate_limit=short_response.rate_limit,
                    raw_response=short_response.raw_response
                )
            except Exception as e:
                logger.error(f"Error parsing short chain for {symbol}: {e}")
                results['short'] = short_response
        else:
            results['short'] = short_response
            
        return results
    
    async def get_option_expirations(self, symbol: str) -> APIResponse:
        """
        Get available option expiration dates for a symbol.
        
        Args:
            symbol: Underlying stock symbol
            
        Returns:
            APIResponse containing list of expiration dates
        """
        logger.debug(f"Fetching option expirations for {symbol}")
        
        response = await self._make_request(f'options/expirations/{symbol}')
        
        if response.is_success and response.data:
            # Parse expiration timestamps to dates
            try:
                expirations = []
                if 'expirations' in response.data:
                    for timestamp in response.data['expirations']:
                        try:
                            date = datetime.fromtimestamp(timestamp).date()
                            expirations.append(date.isoformat())
                        except (ValueError, TypeError):
                            continue
                
                return APIResponse(
                    status=response.status,
                    data=expirations,
                    rate_limit=response.rate_limit,
                    raw_response=response.raw_response
                )
            except Exception as e:
                logger.error(f"Error parsing expirations for {symbol}: {e}")
                return APIResponse(
                    status=APIStatus.ERROR,
                    error=APIError(500, f"Error parsing response: {e}"),
                    rate_limit=response.rate_limit,
                    raw_response=response.raw_response
                )
        
        return response
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        return self._stats.copy()
    
    async def health_check(self) -> bool:
        """
        Perform a health check of the API connection.
        
        Returns:
            True if API is accessible, False otherwise
        """
        try:
            # Try to get AAPL quote (free symbol)
            response = await self.get_stock_quote('AAPL')
            return response.is_success
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False