"""
Unit tests for API data models.
"""

import pytest
from datetime import datetime
from decimal import Decimal

from src.models.api_models import (
    StockQuote, OptionContract, OptionChain, OptionSide,
    APIResponse, APIError, APIStatus, RateLimitHeaders
)


class TestRateLimitHeaders:
    """Test RateLimitHeaders model."""
    
    def test_rate_limit_headers_creation(self):
        """Test creating RateLimitHeaders."""
        headers = RateLimitHeaders(
            limit=100,
            remaining=75,
            reset=1609459200,
            consumed=2
        )
        
        assert headers.limit == 100
        assert headers.remaining == 75
        assert headers.reset == 1609459200  
        assert headers.consumed == 2
    
    def test_reset_datetime_property(self):
        """Test reset_datetime property."""
        headers = RateLimitHeaders(reset=1609459200)
        reset_dt = headers.reset_datetime
        
        assert isinstance(reset_dt, datetime)
        assert reset_dt == datetime.fromtimestamp(1609459200)
        
        # Test with None
        headers = RateLimitHeaders()
        assert headers.reset_datetime is None
    
    def test_usage_percentage_property(self):
        """Test usage_percentage property."""
        headers = RateLimitHeaders(limit=100, remaining=25)
        assert headers.usage_percentage == 75.0
        
        headers = RateLimitHeaders(limit=100, remaining=100)
        assert headers.usage_percentage == 0.0
        
        # Test with None values
        headers = RateLimitHeaders()
        assert headers.usage_percentage is None


class TestAPIError:
    """Test APIError model."""
    
    def test_api_error_creation(self):
        """Test creating APIError."""
        error = APIError(
            code=404,
            message="Symbol not found",
            details="The symbol INVALID was not found in our database"
        )
        
        assert error.code == 404
        assert error.message == "Symbol not found"
        assert error.details == "The symbol INVALID was not found in our database"
    
    def test_api_error_string_representation(self):
        """Test string representation of APIError."""
        error = APIError(code=429, message="Rate limit exceeded")
        assert str(error) == "API Error 429: Rate limit exceeded"


class TestAPIResponse:
    """Test APIResponse model."""
    
    def test_api_response_success(self):
        """Test successful API response."""
        response = APIResponse(
            status=APIStatus.OK,
            data={"test": "data"}
        )
        
        assert response.is_success is True
        assert response.is_rate_limited is False
        assert response.data == {"test": "data"}
    
    def test_api_response_error(self):
        """Test error API response."""
        error = APIError(code=404, message="Not found")
        response = APIResponse(
            status=APIStatus.ERROR,
            error=error
        )
        
        assert response.is_success is False
        assert response.is_rate_limited is False
    
    def test_api_response_rate_limited(self):
        """Test rate limited API response."""
        error = APIError(code=429, message="Rate limit exceeded")
        response = APIResponse(
            status=APIStatus.ERROR,
            error=error
        )
        
        assert response.is_success is False
        assert response.is_rate_limited is True


class TestStockQuote:
    """Test StockQuote model."""
    
    def test_stock_quote_creation(self):
        """Test creating StockQuote."""
        quote = StockQuote(
            symbol="AAPL",
            ask=Decimal("150.50"),
            bid=Decimal("150.25"),
            last=Decimal("150.40"),
            volume=1000000
        )
        
        assert quote.symbol == "AAPL"
        assert quote.ask == Decimal("150.50")
        assert quote.bid == Decimal("150.25")
        assert quote.last == Decimal("150.40")
        assert quote.volume == 1000000
    
    def test_stock_quote_from_api_response(self):
        """Test creating StockQuote from API response."""
        api_data = {
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
        
        quote = StockQuote.from_api_response(api_data)
        
        assert quote.symbol == "AAPL"
        assert quote.ask == Decimal("150.50")
        assert quote.ask_size == 100
        assert quote.bid == Decimal("150.25")
        assert quote.bid_size == 200
        assert quote.mid == Decimal("150.375")
        assert quote.last == Decimal("150.40")
        assert quote.volume == 1000000
        assert quote.updated == datetime.fromtimestamp(1609459200)
    
    def test_stock_quote_from_api_response_alternative_format(self):
        """Test parsing alternative API response format."""
        api_data = {
            'Symbol': ['MSFT'],
            'Ask': [300.75],
            'Bid': [300.50],
            'Last': [300.60],
            'Volume': [500000],
            'Date': [1609459300]
        }
        
        quote = StockQuote.from_api_response(api_data)
        
        assert quote.symbol == "MSFT"
        assert quote.ask == Decimal("300.75")
        assert quote.bid == Decimal("300.50")
        assert quote.last == Decimal("300.60")
        assert quote.volume == 500000
    
    def test_stock_quote_spread_calculation(self):
        """Test spread calculation."""
        quote = StockQuote(
            symbol="AAPL",
            ask=Decimal("150.50"),
            bid=Decimal("150.25"),
            mid=Decimal("150.375")
        )
        
        assert quote.spread == Decimal("0.25")
        assert quote.spread_percentage == Decimal("0.25") / Decimal("150.375") * 100
    
    def test_stock_quote_spread_with_missing_data(self):
        """Test spread calculation with missing data."""
        quote = StockQuote(symbol="AAPL", ask=Decimal("150.50"))
        
        assert quote.spread is None
        assert quote.spread_percentage is None


class TestOptionContract:
    """Test OptionContract model."""
    
    def test_option_contract_creation(self):
        """Test creating OptionContract."""
        expiration = datetime(2023, 6, 16)
        contract = OptionContract(
            option_symbol="AAPL230616C00150000",
            underlying="AAPL",
            expiration=expiration,
            side=OptionSide.CALL,
            strike=Decimal("150"),
            bid=Decimal("5.50"),
            ask=Decimal("5.75")
        )
        
        assert contract.option_symbol == "AAPL230616C00150000"
        assert contract.underlying == "AAPL"
        assert contract.expiration == expiration
        assert contract.side == OptionSide.CALL
        assert contract.strike == Decimal("150")
        assert contract.bid == Decimal("5.50")
        assert contract.ask == Decimal("5.75")
    
    def test_option_contract_from_api_response(self):
        """Test creating OptionContract from API response."""
        api_data = {
            'optionSymbol': ['AAPL230616C00150000', 'AAPL230616P00150000'],
            'underlying': ['AAPL', 'AAPL'],
            'expiration': [1686945600, 1686945600],
            'side': ['call', 'put'],
            'strike': [150, 150],
            'bid': [5.50, 4.25],
            'ask': [5.75, 4.50],
            'delta': [0.55, -0.45],
            'gamma': [0.02, 0.02],
            'theta': [-0.05, -0.04],
            'vega': [0.15, 0.12],
            'iv': [0.25, 0.28],
            'dte': [30, 30],
            'volume': [1000, 500],
            'openInterest': [5000, 3000],
            'inTheMoney': [True, False],
            'intrinsicValue': [5.0, 0.0],
            'extrinsicValue': [0.625, 4.375],
            'underlyingPrice': [155.0, 155.0]
        }
        
        # Test call contract (index 0)
        call_contract = OptionContract.from_api_response(api_data, 0)
        
        assert call_contract.option_symbol == "AAPL230616C00150000"
        assert call_contract.underlying == "AAPL"
        assert call_contract.side == OptionSide.CALL
        assert call_contract.strike == Decimal("150")
        assert call_contract.bid == Decimal("5.50")
        assert call_contract.ask == Decimal("5.75")
        assert call_contract.delta == Decimal("0.55")
        assert call_contract.dte == 30
        assert call_contract.in_the_money is True
        
        # Test put contract (index 1)
        put_contract = OptionContract.from_api_response(api_data, 1)
        
        assert put_contract.option_symbol == "AAPL230616P00150000"
        assert put_contract.side == OptionSide.PUT
        assert put_contract.delta == Decimal("-0.45")
        assert put_contract.in_the_money is False
    
    def test_option_contract_properties(self):
        """Test OptionContract calculated properties."""
        contract = OptionContract(
            option_symbol="AAPL230616C00150000",
            underlying="AAPL",
            expiration=datetime(2023, 6, 16),
            side=OptionSide.CALL,
            strike=Decimal("150"),
            bid=Decimal("5.50"),
            ask=Decimal("5.75"),
            mid=Decimal("5.625"),
            dte=400,  # LEAPS
            underlying_price=Decimal("155")
        )
        
        # Test spread calculation
        assert contract.spread == Decimal("0.25")
        assert contract.spread_percentage == Decimal("0.25") / Decimal("5.625") * 100
        
        # Test LEAPS identification  
        assert contract.is_leaps is True
        
        # Test moneyness
        assert contract.moneyness == "ITM"  # Call with underlying > strike
        
        # Test PUT moneyness
        put_contract = OptionContract(
            option_symbol="AAPL230616P00160000",
            underlying="AAPL",
            expiration=datetime(2023, 6, 16),
            side=OptionSide.PUT,
            strike=Decimal("160"),
            underlying_price=Decimal("155")
        )
        
        assert put_contract.moneyness == "ITM"  # Put with underlying < strike


class TestOptionChain:
    """Test OptionChain model."""
    
    def test_option_chain_creation(self):
        """Test creating OptionChain."""
        contracts = [
            OptionContract(
                option_symbol="AAPL230616C00150000",
                underlying="AAPL",
                expiration=datetime(2023, 6, 16),
                side=OptionSide.CALL,
                strike=Decimal("150")
            )
        ]
        
        chain = OptionChain(
            underlying="AAPL",
            underlying_price=Decimal("155"),
            contracts=contracts
        )
        
        assert chain.underlying == "AAPL"
        assert chain.underlying_price == Decimal("155")
        assert len(chain.contracts) == 1
    
    def test_option_chain_from_api_response(self):
        """Test creating OptionChain from API response."""
        api_data = {
            'underlying': ['AAPL', 'AAPL'],
            'underlyingPrice': [155.0, 155.0],
            'optionSymbol': ['AAPL230616C00150000', 'AAPL230616P00150000'],
            'expiration': [1686945600, 1686945600],
            'side': ['call', 'put'],
            'strike': [150, 150],
            'dte': [30, 30],
            'updated': [1609459200, 1609459200]
        }
        
        chain = OptionChain.from_api_response(api_data)
        
        assert chain.underlying == "AAPL"
        assert chain.underlying_price == Decimal("155.0")
        assert len(chain.contracts) == 2
        assert chain.updated == datetime.fromtimestamp(1609459200)
    
    def test_option_chain_filtering(self):
        """Test option chain filtering methods."""
        # Create test contracts
        contracts = [
            OptionContract(
                option_symbol="AAPL230616C00150000",
                underlying="AAPL",
                expiration=datetime(2023, 6, 16),
                side=OptionSide.CALL,
                strike=Decimal("150"),
                dte=30,
                delta=Decimal("0.55")
            ),
            OptionContract(
                option_symbol="AAPL230716C00150000",
                underlying="AAPL", 
                expiration=datetime(2023, 7, 16),
                side=OptionSide.CALL,
                strike=Decimal("150"),
                dte=60,
                delta=Decimal("0.60")
            ),
            OptionContract(
                option_symbol="AAPL230616P00150000",
                underlying="AAPL",
                expiration=datetime(2023, 6, 16),
                side=OptionSide.PUT,
                strike=Decimal("150"),
                dte=30,
                delta=Decimal("-0.45")
            ),
            OptionContract(
                option_symbol="AAPL250116C00150000",
                underlying="AAPL",
                expiration=datetime(2025, 1, 16),
                side=OptionSide.CALL,
                strike=Decimal("150"),
                dte=400,  # LEAPS
                delta=Decimal("0.75")
            )
        ]
        
        chain = OptionChain(underlying="AAPL", contracts=contracts)
        
        # Test expiration filtering
        short_term = chain.filter_by_expiration(min_dte=20, max_dte=40)
        assert len(short_term) == 2  # Both 30 DTE contracts
        
        # Test delta filtering
        high_delta = chain.filter_by_delta(min_delta=Decimal("0.50"))
        assert len(high_delta) == 3  # Two calls and one put (absolute value)
        
        # Test side filtering
        calls = chain.get_calls()
        puts = chain.get_puts()
        assert len(calls) == 3
        assert len(puts) == 1
        
        # Test LEAPS filtering
        leaps = chain.get_leaps_calls(min_delta=Decimal("0.70"))
        assert len(leaps) == 1
        assert leaps[0].dte == 400
        
        # Test short call filtering
        short_calls = chain.get_short_calls(
            min_dte=20, max_dte=40,
            min_delta=Decimal("0.50"), max_delta=Decimal("0.65")
        )
        assert len(short_calls) == 2  # Both short-term calls within delta range