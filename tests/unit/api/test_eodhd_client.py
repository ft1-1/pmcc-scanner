"""
Unit tests for EODHD API client.
"""

import asyncio
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

import aiohttp
from aioresponses import aioresponses

from src.api.eodhd_client import (
    EODHDClient, EODHDError, EODHDAuthenticationError, 
    EODHDRateLimitError, EODHDQuotaError
)
from src.models.api_models import (
    EODHDScreenerResponse, EODHDScreenerResult, APIResponse, APIStatus, APIError
)


class TestEODHDClient:
    """Test EODHD API client."""
    
    def test_client_initialization(self):
        """Test client initialization."""
        client = EODHDClient(
            api_token="test_token",
            base_url="https://test.eodhd.com/api",
            timeout=15.0
        )
        
        assert client.api_token == "test_token"
        assert client.base_url == "https://test.eodhd.com/api/"
        assert client.max_retries == 3
        assert client._session is None
    
    def test_client_initialization_from_env(self):
        """Test client initialization from environment variables."""
        with patch.dict('os.environ', {
            'EODHD_API_TOKEN': 'env_token',
            'EODHD_API_BASE_URL': 'https://env.eodhd.com/api'
        }):
            client = EODHDClient()
            
            assert client.api_token == "env_token"
            assert client.base_url == "https://env.eodhd.com/api/"
    
    def test_build_filters(self):
        """Test filter building."""
        client = EODHDClient(api_token="test")
        
        filters = [
            ["market_capitalization", ">", 1000000000],
            ["exchange", "=", "us"]
        ]
        
        result = client._build_filters(filters)
        expected = json.dumps(filters)
        
        assert result == expected
    
    def test_create_api_error(self):
        """Test API error creation."""
        client = EODHDClient(api_token="test")
        
        # Test with dict response
        error_data = {
            "error": "Invalid request",
            "details": "Market cap filter is invalid"
        }
        
        error = client._create_api_error(400, error_data)
        
        assert error.code == 400
        assert error.message == "Invalid request"
        assert error.details == "Market cap filter is invalid"
        
        # Test with string response
        error = client._create_api_error(500, "Server error")
        assert error.code == 500
        assert error.message == "Server error"
    
    @pytest.mark.asyncio
    async def test_session_management(self):
        """Test HTTP session management."""
        client = EODHDClient(api_token="test")
        
        # Session should be None initially
        assert client._session is None
        
        # Ensure session creates one
        await client._ensure_session()
        assert client._session is not None
        assert not client._session.closed
        
        # Close should cleanup
        await client.close()
        assert client._session is None
    
    @pytest.mark.asyncio
    async def test_successful_screener_request(self):
        """Test successful screener API request."""
        client = EODHDClient(api_token="test_token")
        
        # Mock response data
        mock_data = [
            {
                "code": "AAPL",
                "name": "Apple Inc.",
                "exchange": "NASDAQ",
                "market_capitalization": 3000000000000,
                "sector": "Technology",
                "adjusted_close": 150.0
            },
            {
                "code": "MSFT", 
                "name": "Microsoft Corporation",
                "exchange": "NASDAQ",
                "market_capitalization": 2500000000000,
                "sector": "Technology",
                "adjusted_close": 300.0
            }
        ]
        
        with aioresponses() as m:
            m.get(
                'https://eodhd.com/api/screener?api_token=test_token&limit=50&offset=0',
                payload=mock_data,
                status=200
            )
            
            response = await client.screen_stocks()
            
            assert response.is_success
            assert isinstance(response.data, EODHDScreenerResponse)
            assert len(response.data.results) == 2
            assert response.data.results[0].code == "AAPL"
            assert response.data.results[1].code == "MSFT"
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_screener_with_filters(self):
        """Test screener request with filters."""
        client = EODHDClient(api_token="test_token")
        
        filters = [
            ["market_capitalization", ">=", 1000000000],
            ["exchange", "=", "us"]
        ]
        
        mock_data = [
            {
                "code": "AAPL",
                "name": "Apple Inc.",
                "exchange": "NASDAQ",
                "market_capitalization": 3000000000000
            }
        ]
        
        with aioresponses() as m:
            # Build expected URL with filters
            expected_params = {
                'api_token': 'test_token',
                'limit': '50',
                'offset': '0',
                'filters': json.dumps(filters),
                'sort': 'market_capitalization.desc'
            }
            
            m.get(
                'https://eodhd.com/api/screener',
                payload=mock_data,
                status=200
            )
            
            response = await client.screen_stocks(
                filters=filters,
                sort="market_capitalization.desc"
            )
            
            assert response.is_success
            assert isinstance(response.data, EODHDScreenerResponse)
            assert len(response.data.results) == 1
            assert response.data.results[0].code == "AAPL"
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_screen_by_market_cap(self):
        """Test market cap screening convenience method."""
        client = EODHDClient(api_token="test_token")
        
        mock_data = [
            {
                "code": "AAPL",
                "name": "Apple Inc.",
                "exchange": "NASDAQ",
                "market_capitalization": 3000000000000
            }
        ]
        
        with aioresponses() as m:
            m.get(
                'https://eodhd.com/api/screener',
                payload=mock_data,
                status=200
            )
            
            response = await client.screen_by_market_cap(
                min_market_cap=50_000_000,
                max_market_cap=5_000_000_000,
                limit=100
            )
            
            assert response.is_success
            assert isinstance(response.data, EODHDScreenerResponse)
            assert len(response.data.results) == 1
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_get_pmcc_universe(self):
        """Test PMCC universe retrieval."""
        client = EODHDClient(api_token="test_token")
        
        mock_data = [
            {
                "code": "AAPL",
                "name": "Apple Inc.",
                "exchange": "NASDAQ",
                "market_capitalization": 3000000000000
            },
            {
                "code": "MSFT",
                "name": "Microsoft Corporation", 
                "exchange": "NASDAQ",
                "market_capitalization": 2500000000000
            }
        ]
        
        with aioresponses() as m:
            m.get(
                'https://eodhd.com/api/screener',
                payload=mock_data,
                status=200
            )
            
            symbols = await client.get_pmcc_universe(limit=100)
            
            assert symbols == ["AAPL", "MSFT"]
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_authentication_error(self):
        """Test authentication error handling."""
        client = EODHDClient(api_token="invalid_token")
        
        with aioresponses() as m:
            m.get(
                'https://eodhd.com/api/screener',
                payload={"error": "Invalid API token"},
                status=401
            )
            
            with pytest.raises(EODHDAuthenticationError):
                await client.screen_stocks()
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_rate_limit_error(self):
        """Test rate limit error handling."""
        client = EODHDClient(api_token="test_token")
        
        with aioresponses() as m:
            m.get(
                'https://eodhd.com/api/screener',
                payload={"error": "Rate limit exceeded"},
                status=429,
                headers={"Retry-After": "60"}
            )
            
            with pytest.raises(EODHDRateLimitError) as exc_info:
                await client.screen_stocks()
            
            assert exc_info.value.retry_after == 60.0
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_quota_error(self):
        """Test quota exceeded error handling."""
        client = EODHDClient(api_token="test_token")
        
        with aioresponses() as m:
            m.get(
                'https://eodhd.com/api/screener',
                payload={"error": "API quota exceeded"},
                status=402
            )
            
            with pytest.raises(EODHDQuotaError):
                await client.screen_stocks()
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_server_error(self):
        """Test server error handling."""
        client = EODHDClient(api_token="test_token")
        
        with aioresponses() as m:
            m.get(
                'https://eodhd.com/api/screener',
                payload={"error": "Internal server error"},
                status=500
            )
            
            response = await client.screen_stocks()
            
            assert not response.is_success
            assert response.status == APIStatus.ERROR
            assert response.error.code == 500
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_invalid_json_response(self):
        """Test handling of invalid JSON responses."""
        client = EODHDClient(api_token="test_token")
        
        with aioresponses() as m:
            m.get(
                'https://eodhd.com/api/screener',
                body="Not valid JSON",
                status=200
            )
            
            response = await client.screen_stocks()
            
            assert not response.is_success
            assert response.status == APIStatus.ERROR
            assert "Error parsing response" in response.error.message
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_network_error_retry(self):
        """Test network error retry logic."""
        client = EODHDClient(api_token="test_token", max_retries=2)
        
        with aioresponses() as m:
            # First call fails
            m.get(
                'https://eodhd.com/api/screener',
                exception=aiohttp.ClientConnectorError(
                    connection_key=None, 
                    os_error=None
                )
            )
            # Second call succeeds
            m.get(
                'https://eodhd.com/api/screener',
                payload=[{"code": "AAPL", "name": "Apple", "exchange": "NASDAQ"}],
                status=200
            )
            
            response = await client.screen_stocks()
            
            assert response.is_success
            assert client._stats['retries_attempted'] > 0
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check."""
        client = EODHDClient(api_token="test_token")
        
        with aioresponses() as m:
            m.get(
                'https://eodhd.com/api/screener',
                payload=[{"code": "AAPL", "name": "Apple", "exchange": "NASDAQ"}],
                status=200
            )
            
            health = await client.health_check()
            assert health is True
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test failed health check."""
        client = EODHDClient(api_token="test_token")
        
        with aioresponses() as m:
            m.get(
                'https://eodhd.com/api/screener',
                payload={"error": "Server error"},
                status=500
            )
            
            health = await client.health_check()
            assert health is False
        
        await client.close()
    
    def test_get_stats(self):
        """Test statistics retrieval."""
        client = EODHDClient(api_token="test_token")
        
        stats = client.get_stats()
        
        assert 'requests_made' in stats
        assert 'requests_failed' in stats
        assert 'rate_limit_hits' in stats
        assert 'retries_attempted' in stats
        
        # Should include rate limiter stats
        assert 'requests_remaining_minute' in stats
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager usage."""
        async with EODHDClient(api_token="test_token") as client:
            assert client._session is not None
            
        # Session should be closed after context exit
        assert client._session is None


class TestEODHDScreenerResult:
    """Test EODHD screener result model."""
    
    def test_from_api_response(self):
        """Test creating result from API response."""
        data = {
            "code": "AAPL",
            "name": "Apple Inc.",
            "exchange": "NASDAQ",
            "market_capitalization": 3000000000000,
            "sector": "Technology",
            "earnings_share": 6.15,
            "adjusted_close": 150.0,
            "volume": 50000000
        }
        
        result = EODHDScreenerResult.from_api_response(data)
        
        assert result.code == "AAPL"
        assert result.name == "Apple Inc."
        assert result.exchange == "NASDAQ"
        assert result.market_capitalization == Decimal('3000000000000')
        assert result.sector == "Technology"
        assert result.earnings_share == Decimal('6.15')
        assert result.adjusted_close == Decimal('150.0')
        assert result.volume == 50000000
    
    def test_market_cap_properties(self):
        """Test market cap conversion properties."""
        result = EODHDScreenerResult(
            code="AAPL",
            name="Apple Inc.",
            exchange="NASDAQ",
            market_capitalization=Decimal('3000000000000')
        )
        
        assert result.market_cap_millions == Decimal('3000000')
        assert result.market_cap_billions == Decimal('3000')
    
    def test_market_cap_properties_none(self):
        """Test market cap properties when market cap is None."""
        result = EODHDScreenerResult(
            code="AAPL",
            name="Apple Inc.",
            exchange="NASDAQ"
        )
        
        assert result.market_cap_millions is None
        assert result.market_cap_billions is None


class TestEODHDScreenerResponse:
    """Test EODHD screener response model."""
    
    def test_from_api_response_list(self):
        """Test creating response from list data."""
        data = [
            {"code": "AAPL", "name": "Apple", "exchange": "NASDAQ"},
            {"code": "MSFT", "name": "Microsoft", "exchange": "NASDAQ"}
        ]
        
        response = EODHDScreenerResponse.from_api_response(data)
        
        assert len(response.results) == 2
        assert response.total_count == 2
        assert response.results[0].code == "AAPL"
        assert response.results[1].code == "MSFT"
    
    def test_from_api_response_dict(self):
        """Test creating response from dict data."""
        data = {
            "data": [
                {"code": "AAPL", "name": "Apple", "exchange": "NASDAQ"}
            ],
            "total_count": 100,
            "offset": 0,
            "limit": 50
        }
        
        response = EODHDScreenerResponse.from_api_response(data)
        
        assert len(response.results) == 1
        assert response.total_count == 100
        assert response.offset == 0
        assert response.limit == 50
    
    def test_get_symbols(self):
        """Test symbol extraction."""
        response = EODHDScreenerResponse(
            results=[
                EODHDScreenerResult("AAPL", "Apple", "NASDAQ"),
                EODHDScreenerResult("MSFT", "Microsoft", "NASDAQ")
            ]
        )
        
        symbols = response.get_symbols()
        assert symbols == ["AAPL", "MSFT"]
    
    def test_filter_by_market_cap(self):
        """Test market cap filtering."""
        response = EODHDScreenerResponse(
            results=[
                EODHDScreenerResult("AAPL", "Apple", "NASDAQ", 
                                  market_capitalization=Decimal('3000000000000')),
                EODHDScreenerResult("SMALL", "Small Corp", "NASDAQ",
                                  market_capitalization=Decimal('100000000'))
            ]
        )
        
        filtered = response.filter_by_market_cap(
            min_cap=Decimal('1000000000000')
        )
        
        assert len(filtered) == 1
        assert filtered[0].code == "AAPL"
    
    def test_filter_by_exchange(self):
        """Test exchange filtering.""" 
        response = EODHDScreenerResponse(
            results=[
                EODHDScreenerResult("AAPL", "Apple", "NASDAQ"),
                EODHDScreenerResult("TSM", "Taiwan Semi", "NYSE")
            ]
        )
        
        filtered = response.filter_by_exchange(["NASDAQ"])
        
        assert len(filtered) == 1
        assert filtered[0].code == "AAPL"