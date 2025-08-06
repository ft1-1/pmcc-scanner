"""
Unit tests for MarketData API client.
"""

import asyncio
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from decimal import Decimal

import aiohttp
from aioresponses import aioresponses

from src.api.marketdata_client import (
    MarketDataClient, MarketDataError, AuthenticationError, 
    RateLimitError, APIQuotaError
)
from src.models.api_models import (
    StockQuote, OptionChain, APIResponse, APIStatus, APIError
)


class TestMarketDataClient:
    """Test MarketData API client."""
    
    def test_client_initialization(self):
        """Test client initialization."""
        client = MarketDataClient(
            api_token="test_token",
            base_url="https://test.api.com/v1",
            plan_type="free"
        )
        
        assert client.api_token == "test_token"
        assert client.base_url == "https://test.api.com/v1/"
        assert client.max_retries == 3
        assert client._session is None
    
    def test_client_initialization_from_env(self):
        """Test client initialization from environment variables."""
        with patch.dict('os.environ', {
            'MARKETDATA_API_TOKEN': 'env_token',
            'MARKETDATA_API_BASE_URL': 'https://env.api.com/v1'
        }):
            client = MarketDataClient()
            
            assert client.api_token == "env_token"
            assert client.base_url == "https://env.api.com/v1/"
    
    def test_auth_headers(self):
        """Test authentication header generation."""
        client = MarketDataClient(api_token="test_token")
        headers = client._get_auth_headers()
        
        assert headers['Authorization'] == 'Bearer test_token'
    
    def test_auth_headers_no_token(self):
        """Test auth headers when no token provided."""
        client = MarketDataClient()
        headers = client._get_auth_headers()
        
        assert 'Authorization' not in headers
    
    def test_rate_limit_headers_parsing(self):
        """Test parsing of rate limit headers."""
        client = MarketDataClient()
        
        headers = {
            'X-Api-Ratelimit-Limit': '100',
            'X-Api-Ratelimit-Remaining': '75', 
            'X-Api-Ratelimit-Reset': '1609459200',
            'X-Api-Ratelimit-Consumed': '2'
        }
        
        rate_limit = client._parse_rate_limit_headers(headers)
        
        assert rate_limit.limit == 100
        assert rate_limit.remaining == 75
        assert rate_limit.reset == 1609459200
        assert rate_limit.consumed == 2
        
        # Test calculated properties
        assert rate_limit.usage_percentage == 25.0
        assert rate_limit.reset_datetime == datetime.fromtimestamp(1609459200)
    
    def test_api_error_creation(self):
        """Test API error creation from response data."""
        client = MarketDataClient()
        
        # Test standard error format
        data = {'error': 'Invalid symbol', 'details': 'Symbol not found'}
        error = client._create_api_error(404, data)
        
        assert error.code == 404
        assert error.message == 'Invalid symbol'
        assert error.details == 'Symbol not found'
        
        # Test alternative error format
        data = {'s': 'error', 'errmsg': 'Rate limit exceeded'}
        error = client._create_api_error(429, data)
        
        assert error.code == 429
        assert error.message == 'Rate limit exceeded'
    
    @pytest.mark.asyncio
    async def test_session_management(self):
        """Test HTTP session management."""
        client = MarketDataClient()
        
        # Session should be None initially
        assert client._session is None
        
        # Should create session when needed
        await client._ensure_session()
        assert client._session is not None
        assert not client._session.closed
        
        # Should close session properly
        await client.close()
        assert client._session.closed
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test client as async context manager."""
        async with MarketDataClient() as client:
            assert client._session is not None
            assert not client._session.closed
        
        # Session should be closed after exiting context
        assert client._session.closed


class TestAPIRequests:
    """Test API request handling."""
    
    @pytest.mark.asyncio
    async def test_successful_request(self):
        """Test successful API request."""
        with aioresponses() as mock_resp:
            # Mock successful response
            mock_data = {
                's': 'ok',
                'symbol': ['AAPL'],
                'ask': [150.50],
                'bid': [150.25],
                'last': [150.40]
            }
            
            mock_resp.get(
                'https://api.marketdata.app/v1/stocks/quotes/AAPL/',
                payload=mock_data,
                status=200,
                headers={
                    'X-Api-Ratelimit-Limit': '100',
                    'X-Api-Ratelimit-Remaining': '99',
                    'X-Api-Ratelimit-Consumed': '1'
                }
            )
            
            async with MarketDataClient(api_token="test") as client:
                response = await client._make_request('stocks/quotes/AAPL')
                
                assert response.is_success
                assert response.status == APIStatus.OK
                assert response.data == mock_data
                assert response.rate_limit.limit == 100
                assert response.rate_limit.remaining == 99
    
    @pytest.mark.asyncio
    async def test_authentication_error(self):
        """Test authentication error handling."""
        with aioresponses() as mock_resp:
            mock_resp.get(
                'https://api.marketdata.app/v1/stocks/quotes/AAPL/',
                payload={'error': 'Invalid token'},
                status=401
            )
            
            async with MarketDataClient() as client:
                with pytest.raises(AuthenticationError) as exc_info:
                    await client._make_request('stocks/quotes/AAPL')
                
                assert exc_info.value.code == 401
                assert "Authentication failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_rate_limit_error(self):
        """Test rate limit error handling."""
        with aioresponses() as mock_resp:
            mock_resp.get(
                'https://api.marketdata.app/v1/stocks/quotes/AAPL/',
                payload={'error': 'Rate limit exceeded'},
                status=429,
                headers={'Retry-After': '60'}
            )
            
            async with MarketDataClient() as client:
                with pytest.raises(RateLimitError) as exc_info:
                    await client._make_request('stocks/quotes/AAPL')
                
                assert exc_info.value.code == 429
                assert exc_info.value.retry_after == 60.0
    
    @pytest.mark.asyncio
    async def test_quota_error(self):
        """Test API quota error handling."""
        with aioresponses() as mock_resp:
            mock_resp.get(
                'https://api.marketdata.app/v1/stocks/quotes/AAPL/',
                payload={'error': 'Plan limit exceeded'},
                status=402
            )
            
            async with MarketDataClient() as client:
                with pytest.raises(APIQuotaError) as exc_info:
                    await client._make_request('stocks/quotes/AAPL')
                
                assert exc_info.value.code == 402
    
    @pytest.mark.asyncio
    async def test_network_error_retry(self):
        """Test network error retry logic."""
        with aioresponses() as mock_resp:
            # First two requests fail, third succeeds
            mock_resp.get(
                'https://api.marketdata.app/v1/stocks/quotes/AAPL/',
                exception=aiohttp.ClientError("Network error")
            )
            mock_resp.get(
                'https://api.marketdata.app/v1/stocks/quotes/AAPL/',
                exception=aiohttp.ClientError("Network error")
            )
            mock_resp.get(
                'https://api.marketdata.app/v1/stocks/quotes/AAPL/',
                payload={'s': 'ok', 'symbol': ['AAPL']},
                status=200
            )
            
            async with MarketDataClient(retry_backoff=0.01) as client:
                response = await client._make_request('stocks/quotes/AAPL')
                
                assert response.is_success
                assert client._stats['retries_attempted'] == 2
    
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test behavior when max retries exceeded."""
        with aioresponses() as mock_resp:
            # All requests fail
            for _ in range(5):
                mock_resp.get(
                    'https://api.marketdata.app/v1/stocks/quotes/AAPL/',
                    exception=aiohttp.ClientError("Network error")
                )
            
            async with MarketDataClient(max_retries=2, retry_backoff=0.01) as client:
                with pytest.raises(MarketDataError) as exc_info:
                    await client._make_request('stocks/quotes/AAPL')
                
                assert "Request failed after 2 retries" in str(exc_info.value)
                assert client._stats['requests_failed'] == 1


class TestStockQuotes:
    """Test stock quote functionality."""
    
    @pytest.mark.asyncio
    async def test_get_stock_quote_success(self):
        """Test successful stock quote retrieval."""
        with aioresponses() as mock_resp:
            mock_data = {
                's': 'ok',
                'symbol': ['AAPL'],
                'ask': [150.50],
                'askSize': [100],
                'bid': [150.25],
                'bidSize': [200],
                'mid': [150.375],
                'last': [150.40],
                'volume': [1000000],
                'updated': [1609459200]
            }
            
            mock_resp.get(
                'https://api.marketdata.app/v1/stocks/quotes/AAPL/',
                payload=mock_data,
                status=200
            )
            
            async with MarketDataClient() as client:
                response = await client.get_stock_quote('AAPL')
                
                assert response.is_success
                assert isinstance(response.data, StockQuote)
                assert response.data.symbol == 'AAPL'
                assert response.data.ask == Decimal('150.50')
                assert response.data.bid == Decimal('150.25')
                assert response.data.volume == 1000000
    
    @pytest.mark.asyncio
    async def test_get_stock_quote_parsing_error(self):
        """Test handling of quote parsing errors."""
        with aioresponses() as mock_resp:
            # Invalid data structure
            mock_data = {'s': 'ok', 'invalid': 'data'}
            
            mock_resp.get(
                'https://api.marketdata.app/v1/stocks/quotes/AAPL/',
                payload=mock_data,
                status=200
            )
            
            async with MarketDataClient() as client:
                response = await client.get_stock_quote('AAPL')
                
                assert not response.is_success
                assert response.status == APIStatus.ERROR
                assert "Error parsing response" in response.error.message
    
    @pytest.mark.asyncio
    async def test_get_multiple_stock_quotes(self):
        """Test retrieving multiple stock quotes."""
        with aioresponses() as mock_resp:
            symbols = ['AAPL', 'MSFT', 'GOOGL']
            
            for symbol in symbols:
                mock_data = {
                    's': 'ok',
                    'symbol': [symbol],
                    'last': [100.0 + len(symbol)]  # Different prices
                }
                
                mock_resp.get(
                    f'https://api.marketdata.app/v1/stocks/quotes/{symbol}/',
                    payload=mock_data,
                    status=200
                )
            
            async with MarketDataClient() as client:
                results = await client.get_stock_quotes(symbols)
                
                assert len(results) == 3
                for symbol in symbols:
                    assert symbol in results
                    assert results[symbol].is_success
                    assert results[symbol].data.symbol == symbol


class TestOptionChains:
    """Test option chain functionality."""
    
    @pytest.mark.asyncio
    async def test_get_option_chain_success(self):
        """Test successful option chain retrieval."""
        with aioresponses() as mock_resp:
            mock_data = {
                's': 'ok',
                'optionSymbol': ['AAPL230616C00150000', 'AAPL230616P00150000'],
                'underlying': ['AAPL', 'AAPL'],
                'expiration': [1686945600, 1686945600],
                'side': ['call', 'put'],
                'strike': [150, 150],
                'bid': [5.50, 4.25],
                'ask': [5.75, 4.50],
                'delta': [0.55, -0.45],
                'dte': [30, 30],
                'underlyingPrice': [155.0, 155.0]
            }
            
            mock_resp.get(
                'https://api.marketdata.app/v1/options/chain/AAPL/',
                payload=mock_data,
                status=200
            )
            
            async with MarketDataClient() as client:
                response = await client.get_option_chain('AAPL')
                
                assert response.is_success
                assert isinstance(response.data, OptionChain)
                assert response.data.underlying == 'AAPL'
                assert len(response.data.contracts) == 2
                assert response.data.underlying_price == Decimal('155.0')
    
    @pytest.mark.asyncio
    async def test_get_option_chain_with_filters(self):
        """Test option chain with filtering parameters."""
        with aioresponses() as mock_resp:
            mock_data = {
                's': 'ok',
                'optionSymbol': ['AAPL230616C00150000'],
                'underlying': ['AAPL'],
                'expiration': [1686945600],
                'side': ['call'],
                'strike': [150]
            }
            
            # Expect request with query parameters
            expected_url = 'https://api.marketdata.app/v1/options/chain/AAPL/'
            mock_resp.get(expected_url, payload=mock_data, status=200)
            
            async with MarketDataClient() as client:
                response = await client.get_option_chain(
                    'AAPL',
                    expiration='2023-06-16',
                    side='call',
                    strike_limit=10,
                    min_dte=20,
                    max_dte=40
                )
                
                assert response.is_success
                # Verify the request was made with parameters
                assert len(mock_resp.requests) == 1
                request = mock_resp.requests[0][0]
                assert 'expiration=2023-06-16' in str(request.url)
                assert 'side=call' in str(request.url)
    
    @pytest.mark.asyncio
    async def test_get_option_expirations(self):
        """Test option expirations retrieval."""
        with aioresponses() as mock_resp:
            mock_data = {
                's': 'ok',
                'expirations': [1686945600, 1689624000, 1692302400]
            }
            
            mock_resp.get(
                'https://api.marketdata.app/v1/options/expirations/AAPL/',
                payload=mock_data,
                status=200
            )
            
            async with MarketDataClient() as client:
                response = await client.get_option_expirations('AAPL')
                
                assert response.is_success
                assert len(response.data) == 3
                # Should convert timestamps to ISO date strings
                assert all('2023-' in date for date in response.data)


class TestClientStats:
    """Test client statistics and health checks."""
    
    @pytest.mark.asyncio
    async def test_client_stats(self):
        """Test client statistics collection."""
        with aioresponses() as mock_resp:
            mock_resp.get(
                'https://api.marketdata.app/v1/stocks/quotes/AAPL/',
                payload={'s': 'ok', 'symbol': ['AAPL']},
                status=200
            )
            
            async with MarketDataClient() as client:
                await client.get_stock_quote('AAPL')
                
                stats = client.get_stats()
                
                assert stats['requests_made'] == 1
                assert stats['requests_failed'] == 0
                assert 'plan_type' in stats
                assert 'daily_usage' in stats
    
    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check."""
        with aioresponses() as mock_resp:
            mock_resp.get(
                'https://api.marketdata.app/v1/stocks/quotes/AAPL/',
                payload={'s': 'ok', 'symbol': ['AAPL']},
                status=200
            )
            
            async with MarketDataClient() as client:
                is_healthy = await client.health_check()
                
                assert is_healthy is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test health check failure."""
        with aioresponses() as mock_resp:
            mock_resp.get(
                'https://api.marketdata.app/v1/stocks/quotes/AAPL/',
                exception=aiohttp.ClientError("Connection failed")
            )
            
            async with MarketDataClient(max_retries=0) as client:
                is_healthy = await client.health_check()
                
                assert is_healthy is False


@pytest.mark.asyncio
async def test_rate_limiter_integration():
    """Test integration with rate limiter."""
    with patch('src.api.marketdata_client.create_rate_limiter') as mock_create:
        mock_limiter = AsyncMock()
        mock_create.return_value = mock_limiter
        
        # Mock successful acquisition
        mock_context = AsyncMock()
        mock_limiter.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_context)
        mock_limiter.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with aioresponses() as mock_resp:
            mock_resp.get(
                'https://api.marketdata.app/v1/stocks/quotes/AAPL/',
                payload={'s': 'ok', 'symbol': ['AAPL']},
                status=200,
                headers={'X-Api-Ratelimit-Consumed': '2'}
            )
            
            async with MarketDataClient() as client:
                await client.get_stock_quote('AAPL')
                
                # Verify rate limiter was used
                mock_limiter.acquire.assert_called_once_with(1)
                mock_context.set_credits_consumed.assert_called_once_with(2)