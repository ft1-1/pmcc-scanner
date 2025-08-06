"""
Unit tests for stock screener functionality.
"""

import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import Mock, patch

from src.analysis.stock_screener import (
    StockScreener, ScreeningCriteria, StockScreenResult
)
from src.models.api_models import StockQuote, APIResponse, APIStatus
from src.api.marketdata_client import MarketDataClient


class TestScreeningCriteria:
    """Test ScreeningCriteria dataclass."""
    
    def test_default_criteria(self):
        """Test default screening criteria values."""
        criteria = ScreeningCriteria()
        
        assert criteria.min_market_cap == Decimal('50')
        assert criteria.max_market_cap == Decimal('5000')
        assert criteria.min_price == Decimal('10')
        assert criteria.max_price == Decimal('500')
        assert criteria.min_daily_volume == 500_000
        assert criteria.require_weekly_options is True
        assert criteria.require_leaps is True
    
    def test_custom_criteria(self):
        """Test custom screening criteria."""
        criteria = ScreeningCriteria(
            min_market_cap=Decimal('100'),
            max_market_cap=Decimal('1000'),
            min_price=Decimal('20'),
            require_weekly_options=False
        )
        
        assert criteria.min_market_cap == Decimal('100')
        assert criteria.max_market_cap == Decimal('1000')
        assert criteria.min_price == Decimal('20')
        assert criteria.require_weekly_options is False


class TestStockScreenResult:
    """Test StockScreenResult dataclass."""
    
    def test_stock_screen_result_creation(self):
        """Test creating StockScreenResult."""
        quote = StockQuote(
            symbol="AAPL",
            last=Decimal('150.00'),
            volume=1_000_000
        )
        
        result = StockScreenResult(
            symbol="AAPL",
            quote=quote,
            market_cap=Decimal('2500000000'),  # $2.5B
            has_weekly_options=True,
            has_leaps=True,
            screening_score=Decimal('85')
        )
        
        assert result.symbol == "AAPL"
        assert result.quote.symbol == "AAPL"
        assert result.market_cap == Decimal('2500000000')
        assert result.has_weekly_options is True
        assert result.has_leaps is True
        assert result.screening_score == Decimal('85')


class TestStockScreener:
    """Test StockScreener class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_api_client = Mock(spec=MarketDataClient)
        self.screener = StockScreener(self.mock_api_client)
    
    def test_init(self):
        """Test StockScreener initialization."""
        assert self.screener.api_client == self.mock_api_client
        assert hasattr(self.screener, 'logger')
    
    def test_check_price_filters_valid(self):
        """Test price filters with valid quote."""
        quote = StockQuote(
            symbol="AAPL",
            last=Decimal('150.00'),
            volume=1_000_000
        )
        criteria = ScreeningCriteria()
        
        result = self.screener._check_price_filters(quote, criteria)
        assert result is True
    
    def test_check_price_filters_price_too_low(self):
        """Test price filters with price too low."""
        quote = StockQuote(
            symbol="PENNY",
            last=Decimal('5.00'),  # Below min_price of $10
            volume=1_000_000
        )
        criteria = ScreeningCriteria()
        
        result = self.screener._check_price_filters(quote, criteria)
        assert result is False
    
    def test_check_price_filters_price_too_high(self):
        """Test price filters with price too high."""
        quote = StockQuote(
            symbol="EXPENSIVE",
            last=Decimal('600.00'),  # Above max_price of $500
            volume=1_000_000
        )
        criteria = ScreeningCriteria()
        
        result = self.screener._check_price_filters(quote, criteria)
        assert result is False
    
    def test_check_price_filters_volume_too_low(self):
        """Test price filters with volume too low."""
        quote = StockQuote(
            symbol="ILLIQUID",
            last=Decimal('50.00'),
            volume=100_000  # Below min_daily_volume of 500k
        )
        criteria = ScreeningCriteria()
        
        result = self.screener._check_price_filters(quote, criteria)
        assert result is False
    
    def test_check_price_filters_no_price(self):
        """Test price filters with no price data."""
        quote = StockQuote(
            symbol="NODATA",
            last=None,
            mid=None,
            volume=1_000_000
        )
        criteria = ScreeningCriteria()
        
        result = self.screener._check_price_filters(quote, criteria)
        assert result is False
    
    def test_check_has_leaps_true(self):
        """Test LEAPS detection with valid data."""
        options_data = {
            'dte': [30, 45, 90, 180, 365, 450, 730]  # Has 365+ day options
        }
        
        result = self.screener._check_has_leaps(options_data)
        assert result is True
    
    def test_check_has_leaps_false(self):
        """Test LEAPS detection with no LEAPS."""
        options_data = {
            'dte': [30, 45, 90, 180, 270]  # No 365+ day options
        }
        
        result = self.screener._check_has_leaps(options_data)
        assert result is False
    
    def test_check_has_leaps_empty(self):
        """Test LEAPS detection with empty data."""
        options_data = {'dte': []}
        
        result = self.screener._check_has_leaps(options_data)
        assert result is False
    
    def test_check_has_weekly_options_true(self):
        """Test weekly options detection."""
        options_data = {
            'dte': [3, 7, 14, 30, 45]  # Has <=7 day options
        }
        
        result = self.screener._check_has_weekly_options(options_data)
        assert result is True
    
    def test_check_has_weekly_options_false(self):
        """Test weekly options detection with no weeklies."""
        options_data = {
            'dte': [14, 30, 45, 90]  # No <=7 day options
        }
        
        result = self.screener._check_has_weekly_options(options_data)
        assert result is False
    
    def test_calculate_options_volume(self):
        """Test options volume calculation."""
        options_data = {
            'volume': [100, 200, None, 300, 0, 150]
        }
        
        result = self.screener._calculate_options_volume(options_data)
        assert result == 750  # 100 + 200 + 300 + 150
    
    def test_calculate_options_volume_empty(self):
        """Test options volume calculation with empty data."""
        options_data = {'volume': []}
        
        result = self.screener._calculate_options_volume(options_data)
        assert result is None
    
    def test_calculate_options_volume_no_valid(self):
        """Test options volume calculation with no valid volumes."""
        options_data = {'volume': [None, 0, None]}
        
        result = self.screener._calculate_options_volume(options_data)
        assert result is None
    
    def test_calculate_screening_score_comprehensive(self):
        """Test comprehensive screening score calculation."""
        quote = StockQuote(
            symbol="AAPL",
            last=Decimal('150.00'),
            volume=2_000_000
        )
        
        market_data = {
            'market_cap': Decimal('2500000000'),  # $2.5B - good mid-cap
            'avg_volume_20d': 1_500_000,  # Current volume > avg
            'options_volume': 10_000,  # Good options volume
            'iv_rank': Decimal('50'),  # Perfect IV rank
            'rsi': Decimal('55'),  # Good RSI
            'sma_20': Decimal('145')  # Price above SMA
        }
        
        criteria = ScreeningCriteria(above_sma_20=True)
        
        score = self.screener._calculate_screening_score(quote, market_data, criteria)
        
        # Should be a high score given all favorable factors
        assert score >= Decimal('80')
        assert score <= Decimal('100')
    
    def test_calculate_screening_score_poor_conditions(self):
        """Test screening score with poor market conditions."""
        quote = StockQuote(
            symbol="POOR",
            last=Decimal('50.00'),
            volume=100_000
        )
        
        market_data = {
            'market_cap': Decimal('10000000'),  # $10M - very small cap
            'avg_volume_20d': 200_000,  # Current volume < avg
            'options_volume': 10,  # Poor options volume
            'iv_rank': Decimal('90'),  # Very high IV rank
            'rsi': Decimal('80'),  # Overbought
            'sma_20': Decimal('55')  # Price below SMA
        }
        
        criteria = ScreeningCriteria(above_sma_20=True)
        
        score = self.screener._calculate_screening_score(quote, market_data, criteria)
        
        # Should be a low score given poor factors
        assert score <= Decimal('50')
    
    def test_get_universe_symbols_sp500(self):
        """Test getting S&P 500 universe symbols."""
        symbols = self.screener._get_universe_symbols("SP500")
        
        assert isinstance(symbols, list)
        assert len(symbols) > 0
        assert "AAPL" in symbols
        assert "MSFT" in symbols
    
    def test_get_universe_symbols_nasdaq100(self):
        """Test getting NASDAQ 100 universe symbols."""
        symbols = self.screener._get_universe_symbols("NASDAQ100")
        
        assert isinstance(symbols, list)
        assert len(symbols) > 0
        assert "AAPL" in symbols
        assert "GOOGL" in symbols
    
    def test_get_universe_symbols_demo(self):
        """Test getting demo universe symbols."""
        symbols = self.screener._get_universe_symbols("DEMO")
        
        assert isinstance(symbols, list)
        assert len(symbols) == 8  # Demo has 8 symbols
        assert "AAPL" in symbols
        assert "TSLA" in symbols
    
    def test_get_universe_symbols_unknown(self):
        """Test getting unknown universe defaults to demo."""
        symbols = self.screener._get_universe_symbols("UNKNOWN")
        
        assert isinstance(symbols, list)
        assert len(symbols) == 8  # Should default to demo
    
    @patch.object(StockScreener, '_screen_single_symbol')
    def test_screen_symbols_success(self, mock_screen_single):
        """Test screening multiple symbols successfully."""
        # Mock successful screening results
        mock_result1 = StockScreenResult(
            symbol="AAPL",
            quote=StockQuote(symbol="AAPL", last=Decimal('150')),
            screening_score=Decimal('90')
        )
        mock_result2 = StockScreenResult(
            symbol="MSFT", 
            quote=StockQuote(symbol="MSFT", last=Decimal('300')),
            screening_score=Decimal('85')
        )
        
        mock_screen_single.side_effect = [mock_result1, mock_result2]
        
        symbols = ["AAPL", "MSFT"]
        results = self.screener.screen_symbols(symbols)
        
        assert len(results) == 2
        # Should be sorted by score (highest first)
        assert results[0].symbol == "AAPL"  # Higher score
        assert results[1].symbol == "MSFT"
        
        # Verify all symbols were attempted
        assert mock_screen_single.call_count == 2
    
    @patch.object(StockScreener, '_screen_single_symbol')
    def test_screen_symbols_with_failures(self, mock_screen_single):
        """Test screening symbols with some failures."""
        # Mock mixed results (some succeed, some fail)
        mock_result = StockScreenResult(
            symbol="AAPL",
            quote=StockQuote(symbol="AAPL", last=Decimal('150')),
            screening_score=Decimal('90')
        )
        
        # First call succeeds, second returns None (filtered out), third raises exception
        mock_screen_single.side_effect = [mock_result, None, Exception("API Error")]
        
        symbols = ["AAPL", "FILTERED", "ERROR"]
        results = self.screener.screen_symbols(symbols)
        
        # Should only return the successful result
        assert len(results) == 1
        assert results[0].symbol == "AAPL"
        
        # All symbols should have been attempted
        assert mock_screen_single.call_count == 3
    
    def test_screen_symbols_empty_list(self):
        """Test screening empty symbol list."""
        results = self.screener.screen_symbols([])
        assert results == []
    
    @patch.object(StockScreener, 'screen_symbols')
    @patch.object(StockScreener, '_get_universe_symbols')
    def test_screen_universe(self, mock_get_universe, mock_screen_symbols):
        """Test screening a universe of stocks."""
        # Mock universe and screening results
        mock_get_universe.return_value = ["AAPL", "MSFT", "GOOGL"]
        mock_result = StockScreenResult(
            symbol="AAPL",
            quote=StockQuote(symbol="AAPL", last=Decimal('150')),
            screening_score=Decimal('90')
        )
        mock_screen_symbols.return_value = [mock_result]
        
        results = self.screener.screen_universe("SP500", max_results=50)
        
        mock_get_universe.assert_called_once_with("SP500")
        mock_screen_symbols.assert_called_once()
        assert len(results) == 1
        assert results[0].symbol == "AAPL"