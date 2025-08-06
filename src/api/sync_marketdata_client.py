"""
Synchronous MarketData.app API client implementation.

This client provides synchronous access to the MarketData.app API following 
the official documentation exactly. It includes authentication, error handling, 
and retry logic without async/await complexity.

Key features:
- Bearer token authentication as documented
- Comprehensive error handling for all documented status codes
- Support for stock quotes and options chains
- Thread-safe operation for daily scan usage
- Rate limiting handled by the API itself

Based on marketdata_api_docs.md specifications.
"""

import logging
import os
import time
from typing import Optional, List, Dict, Any, Union
from urllib.parse import urljoin, urlencode
import requests
import json
from datetime import datetime
from dataclasses import dataclass

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


class SyncMarketDataClient:
    """
    Synchronous client for MarketData.app API.
    
    Provides synchronous access to stock quotes and options chains with proper
    authentication and error handling as documented. Rate limiting is handled
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
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        
        # HTTP session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PMCC-Scanner/1.0',
            'Accept': 'application/json'
        })
        
        # Request statistics
        self._stats = {
            'requests_made': 0,
            'requests_failed': 0,
            'rate_limit_hits': 0,
            'retries_attempted': 0
        }
        
        logger.info("MarketData client initialized")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def close(self):
        """Close HTTP session and cleanup resources."""
        if self.session:
            self.session.close()
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers per documentation."""
        headers = {}
        if self.api_token:
            headers['Authorization'] = f'Bearer {self.api_token}'
        return headers
    
    def _parse_rate_limit_headers(self, headers: Dict[str, str]) -> RateLimitHeaders:
        """Parse rate limit headers from response per documentation."""
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
    
    def _create_api_error(self, status: int, data: Any) -> APIError:
        """Create APIError from response data."""
        message = "Unknown API error"
        details = None
        
        if isinstance(data, dict):
            # Standard error format per documentation
            message = data.get('error', data.get('message', message))
            details = data.get('details')
            
            # Sometimes error is in 's' field per documentation
            if data.get('s') == 'error':
                message = data.get('errmsg', message)
        elif isinstance(data, str):
            message = data
        
        return APIError(
            code=status,
            message=str(message),
            details=str(details) if details else None
        )
    
    def _make_request(self, 
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
                response = self.session.get(
                    url, 
                    params=request_params, 
                    headers=headers,
                    timeout=self.timeout
                )
                
                # Update statistics
                self._stats['requests_made'] += 1
                
                # Parse response
                try:
                    response_data = response.json()
                except Exception:
                    # Handle non-JSON responses
                    response_text = response.text
                    response_data = {'error': f'Invalid JSON response: {response_text[:200]}'}
                
                # Parse rate limit headers
                rate_limit = self._parse_rate_limit_headers(dict(response.headers))
                
                # Handle response based on status code per documentation
                if response.status_code == 200:
                    # Success
                    return APIResponse(
                        status=APIStatus.OK,
                        data=response_data,
                        rate_limit=rate_limit,
                        raw_response=response_data
                    )
                
                elif response.status_code == 203:
                    # Success with cached data per documentation
                    return APIResponse(
                        status=APIStatus.OK,
                        data=response_data,
                        rate_limit=rate_limit,
                        raw_response=response_data
                    )
                
                elif response.status_code == 204:
                    # No cached data available for this symbol
                    # Per docs: Make a live request to fetch real-time data
                    logger.info(f"No cached data for endpoint, would need live request")
                    return APIResponse(
                        status=APIStatus.NO_DATA,
                        error=APIError(204, "No cached data available, use live feed"),
                        rate_limit=rate_limit,
                        raw_response=None
                    )
                
                elif response.status_code == 401:
                    # Authentication error per documentation
                    error = self._create_api_error(response.status_code, response_data)
                    raise AuthenticationError(
                        f"Authentication failed: {error.message}",
                        code=response.status_code
                    )
                
                elif response.status_code == 402:
                    # Payment required / plan limit per documentation
                    error = self._create_api_error(response.status_code, response_data)
                    raise APIQuotaError(
                        f"Plan limit exceeded: {error.message}",
                        code=response.status_code
                    )
                
                elif response.status_code == 429:
                    # Rate limit exceeded per documentation
                    self._stats['rate_limit_hits'] += 1
                    error = self._create_api_error(response.status_code, response_data)
                    
                    # Extract retry-after from headers per documentation
                    retry_after = None
                    if 'Retry-After' in response.headers:
                        try:
                            retry_after = float(response.headers['Retry-After'])
                        except ValueError:
                            pass
                    elif rate_limit.reset:
                        retry_after = max(0, rate_limit.reset - time.time())
                    
                    if retry_after and attempt < self.max_retries:
                        logger.warning(f"Rate limit hit, waiting {retry_after:.1f}s")
                        time.sleep(retry_after)
                        continue
                    
                    raise RateLimitError(
                        f"Rate limit exceeded: {error.message}",
                        code=response.status_code,
                        retry_after=retry_after
                    )
                
                else:
                    # Other API error
                    error = self._create_api_error(response.status_code, response_data)
                    return APIResponse(
                        status=APIStatus.ERROR,
                        error=error,
                        rate_limit=rate_limit,
                        raw_response=response_data
                    )
            
            except (requests.RequestException, requests.Timeout) as e:
                # Network errors
                last_exception = e
                if attempt < self.max_retries:
                    delay = self.retry_backoff * (2 ** attempt)
                    logger.warning(f"Request failed (attempt {attempt + 1}), retrying in {delay:.1f}s: {e}")
                    self._stats['retries_attempted'] += 1
                    time.sleep(delay)
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
                    time.sleep(delay)
                    continue
                else:
                    self._stats['requests_failed'] += 1
                    raise MarketDataError(f"Unexpected error: {e}")
        
        # Should not reach here, but handle gracefully
        if last_exception:
            raise MarketDataError(f"Request failed: {last_exception}")
        else:
            raise MarketDataError("Request failed for unknown reason")
    
    def get_stock_quote(self, symbol: str) -> APIResponse:
        """
        Get stock quote for a single symbol per API documentation.
        
        Args:
            symbol: Stock ticker symbol (e.g., 'AAPL')
            
        Returns:
            APIResponse containing StockQuote data or error
        """
        logger.debug(f"Fetching stock quote for {symbol}")
        
        response = self._make_request(f'stocks/quotes/{symbol}')
        
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
    
    def get_stock_quotes(self, symbols: List[str]) -> Dict[str, APIResponse]:
        """
        Get stock quotes for multiple symbols.
        
        Args:
            symbols: List of stock ticker symbols
            
        Returns:
            Dictionary mapping symbols to their APIResponse objects
        """
        logger.info(f"Fetching stock quotes for {len(symbols)} symbols")
        
        results = {}
        for symbol in symbols:
            try:
                results[symbol] = self.get_stock_quote(symbol)
            except Exception as e:
                logger.error(f"Error fetching quote for {symbol}: {e}")
                results[symbol] = APIResponse(
                    status=APIStatus.ERROR,
                    error=APIError(500, f"Request failed: {e}")
                )
        
        return results
    
    def get_option_chain(self, 
                        symbol: str,
                        expiration: Optional[str] = None,
                        side: Optional[str] = None,
                        strike_limit: Optional[int] = None,
                        min_dte: Optional[int] = None,
                        max_dte: Optional[int] = None,
                        use_cached_feed: bool = True,
                        pmcc_optimized: bool = False) -> APIResponse:
        """
        Get option chain for a symbol per API documentation.
        
        Args:
            symbol: Underlying stock symbol
            expiration: Specific expiration date (YYYY-MM-DD format)
            side: Option side ('call' or 'put')
            strike_limit: Limit number of strikes returned
            min_dte: Minimum days to expiration
            max_dte: Maximum days to expiration
            use_cached_feed: Use cached feed (1 credit per call) instead of live feed (1 credit per symbol)
            pmcc_optimized: Use PMCC-optimized parameters to get all needed data in one call
            
        Returns:
            APIResponse containing OptionChain data or error
        """
        logger.debug(f"Fetching option chain for {symbol}")
        
        # Build parameters per API documentation
        params = {}
        
        if pmcc_optimized:
            # PMCC-optimized parameters to get all data in one call
            params = {
                'from': 30,      # Min 30 days for short calls
                'to': 730,       # Max 730 days for LEAPS
                'side': 'call',  # Only calls for PMCC
                'minVolume': 10, # Minimum volume for liquidity
                'maxBidAskSpreadPct': 0.10,  # Max 10% spread
                'strikeLimit': 20,  # 20 strikes around ATM
                'nonstandard': False,  # Exclude non-standard
                'weekly': True,   # Include weekly expirations
                'monthly': True,  # Include monthly expirations
            }
        else:
            # Standard parameters
            if expiration:
                params['expiration'] = expiration
            if side:
                params['side'] = side
            if strike_limit:
                params['strikeLimit'] = strike_limit
            if min_dte:
                params['minDTE'] = min_dte
            if max_dte:
                params['maxDTE'] = max_dte
        
        # Use cached feed by default to minimize API credit usage
        # Cached feed: 1 credit per API call regardless of number of contracts
        # Live feed: 1 credit per option symbol (can be thousands for SPX)
        if use_cached_feed:
            params['feed'] = 'cached'
        
        response = self._make_request(f'options/chain/{symbol}', params=params)
        
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
    
    def get_option_expirations(self, symbol: str) -> APIResponse:
        """
        Get available option expiration dates for a symbol per API documentation.
        
        Args:
            symbol: Underlying stock symbol
            
        Returns:
            APIResponse containing list of expiration dates
        """
        logger.debug(f"Fetching option expirations for {symbol}")
        
        response = self._make_request(f'options/expirations/{symbol}')
        
        if response.is_success and response.data:
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
    
    # Compatibility methods for existing code
    def get_quote(self, symbol: str) -> APIResponse:
        """Alias for get_stock_quote for compatibility."""
        return self.get_stock_quote(symbol)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        return self._stats.copy()
    
    def health_check(self) -> bool:
        """
        Perform a health check of the API connection using free symbol per documentation.
        
        Returns:
            True if API is accessible, False otherwise
        """
        try:
            # Try to get AAPL quote (free symbol per documentation)
            response = self.get_stock_quote('AAPL')
            return response.is_success
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False