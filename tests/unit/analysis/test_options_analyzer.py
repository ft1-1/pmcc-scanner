"""
Unit tests for options analyzer functionality.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.analysis.options_analyzer import (
    OptionsAnalyzer, LEAPSCriteria, ShortCallCriteria, PMCCOpportunity
)
from src.models.api_models import (
    OptionContract, OptionChain, StockQuote, OptionSide, APIResponse, APIStatus
)
from src.models.pmcc_models import PMCCAnalysis
from src.api.marketdata_client import MarketDataClient


class TestLEAPSCriteria:
    """Test LEAPSCriteria dataclass."""
    
    def test_default_criteria(self):
        """Test default LEAPS criteria values."""
        criteria = LEAPSCriteria()
        
        assert criteria.min_dte == 270  # 9 months
        assert criteria.max_dte == 730  # 24 months
        assert criteria.min_delta == Decimal('0.75')
        assert criteria.max_delta == Decimal('0.90')
        assert criteria.max_bid_ask_spread_pct == Decimal('5.0')
        assert criteria.min_open_interest == 10
        assert criteria.moneyness == "ITM"
    
    def test_custom_criteria(self):
        """Test custom LEAPS criteria."""
        criteria = LEAPSCriteria(
            min_dte=365,
            max_dte=600,
            min_delta=Decimal('0.80'),
            min_open_interest=25
        )
        
        assert criteria.min_dte == 365
        assert criteria.max_dte == 600
        assert criteria.min_delta == Decimal('0.80')
        assert criteria.min_open_interest == 25


class TestShortCallCriteria:
    """Test ShortCallCriteria dataclass."""
    
    def test_default_criteria(self):
        """Test default short call criteria values."""
        criteria = ShortCallCriteria()
        
        assert criteria.min_dte == 21  # 3 weeks
        assert criteria.max_dte == 45  # ~6 weeks
        assert criteria.min_delta == Decimal('0.20')
        assert criteria.max_delta == Decimal('0.35')
        assert criteria.max_bid_ask_spread_pct == Decimal('10.0')
        assert criteria.min_open_interest == 5
        assert criteria.prefer_weekly is True
        assert criteria.moneyness == "OTM"


class TestPMCCOpportunity:
    """Test PMCCOpportunity dataclass."""
    
    def test_pmcc_opportunity_creation(self):
        """Test creating PMCCOpportunity."""
        leaps = OptionContract(
            option_symbol="AAPL241220C00130000",
            underlying="AAPL",
            expiration=datetime(2024, 12, 20),
            side=OptionSide.CALL,
            strike=Decimal('130'),
            bid=Decimal('25.00'),
            ask=Decimal('25.50'),
            delta=Decimal('0.80'),
            dte=450
        )
        
        short = OptionContract(
            option_symbol="AAPL240215C00155000",
            underlying="AAPL",
            expiration=datetime(2024, 2, 15),
            side=OptionSide.CALL,
            strike=Decimal('155'),
            bid=Decimal('2.50'),
            ask=Decimal('2.70'),
            delta=Decimal('0.30'),
            dte=30
        )
        
        quote = StockQuote(symbol="AAPL", last=Decimal('150.00'))
        
        opportunity = PMCCOpportunity(
            leaps_contract=leaps,
            short_contract=short,
            underlying_quote=quote,
            net_debit=Decimal('22.50'),  # 25.50 - 2.50
            max_profit=Decimal('2.50'),  # 155-130-22.50
            max_loss=Decimal('22.50'),
            breakeven=Decimal('152.50'),  # 130+22.50
            roi_potential=Decimal('11.11'),  # 2.50/22.50*100
            risk_reward_ratio=Decimal('0.111'),  # 2.50/22.50
            probability_score=Decimal('65'),
            liquidity_score=Decimal('75'),
            total_score=Decimal('70'),
            analyzed_at=datetime.now()
        )
        
        assert opportunity.leaps_contract.strike == Decimal('130')
        assert opportunity.short_contract.strike == Decimal('155')
        assert opportunity.net_debit == Decimal('22.50')
        assert opportunity.max_profit == Decimal('2.50')
        assert opportunity.total_score == Decimal('70')


class TestOptionsAnalyzer:
    """Test OptionsAnalyzer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_api_client = Mock(spec=MarketDataClient)
        self.analyzer = OptionsAnalyzer(self.mock_api_client)
    
    def test_init(self):
        """Test OptionsAnalyzer initialization."""
        assert self.analyzer.api_client == self.mock_api_client
        assert hasattr(self.analyzer, 'logger')
    
    def create_test_option_contract(self, symbol: str, strike: Decimal, 
                                  dte: int, delta: Decimal, side: OptionSide = OptionSide.CALL,
                                  bid: Decimal = Decimal('10.00'), ask: Decimal = Decimal('10.20'),
                                  oi: int = 100, volume: int = 50, 
                                  underlying_price: Decimal = Decimal('150.00')) -> OptionContract:
        """Helper to create test option contracts."""
        return OptionContract(
            option_symbol=symbol,
            underlying="AAPL",
            expiration=datetime.now() + timedelta(days=dte),
            side=side,
            strike=strike,
            bid=bid,
            ask=ask,
            mid=(bid + ask) / 2,
            delta=delta,
            open_interest=oi,
            volume=volume,
            dte=dte,
            underlying_price=underlying_price
        )
    
    def test_check_contract_liquidity_valid(self):
        """Test liquidity check with valid contract."""
        contract = self.create_test_option_contract(
            "AAPL240315C00150000", Decimal('150'), 30, Decimal('0.30'),
            bid=Decimal('2.00'), ask=Decimal('2.10'), oi=100, volume=50
        )
        
        result = self.analyzer._check_contract_liquidity(
            contract, min_oi=10, min_volume=10, max_spread_pct=Decimal('10')
        )
        assert result is True
    
    def test_check_contract_liquidity_low_oi(self):
        """Test liquidity check with low open interest."""
        contract = self.create_test_option_contract(
            "AAPL240315C00150000", Decimal('150'), 30, Decimal('0.30'),
            oi=5  # Below minimum of 10
        )
        
        result = self.analyzer._check_contract_liquidity(
            contract, min_oi=10, min_volume=0, max_spread_pct=Decimal('20')
        )
        assert result is False
    
    def test_check_contract_liquidity_low_volume(self):
        """Test liquidity check with low volume."""
        contract = self.create_test_option_contract(
            "AAPL240315C00150000", Decimal('150'), 30, Decimal('0.30'),
            volume=5  # Below minimum of 10
        )
        
        result = self.analyzer._check_contract_liquidity(
            contract, min_oi=10, min_volume=10, max_spread_pct=Decimal('20')
        )
        assert result is False
    
    def test_check_contract_liquidity_wide_spread(self):
        """Test liquidity check with wide bid-ask spread."""
        contract = self.create_test_option_contract(
            "AAPL240315C00150000", Decimal('150'), 30, Decimal('0.30'),
            bid=Decimal('2.00'), ask=Decimal('2.50')  # 22.2% spread
        )
        
        result = self.analyzer._check_contract_liquidity(
            contract, min_oi=10, min_volume=10, max_spread_pct=Decimal('20')
        )
        assert result is False
    
    def test_is_valid_pmcc_combination_valid(self):
        """Test valid PMCC combination check."""
        leaps = self.create_test_option_contract(
            "AAPL241220C00130000", Decimal('130'), 450, Decimal('0.80'),
            bid=Decimal('18.50'), ask=Decimal('19.00')  # Lower cost for LEAPS
        )
        
        short = self.create_test_option_contract(
            "AAPL240215C00155000", Decimal('155'), 30, Decimal('0.30'),
            bid=Decimal('4.50'), ask=Decimal('4.70')  # Higher premium for short
        )
        
        quote = StockQuote(symbol="AAPL", last=Decimal('150.00'))
        
        result = self.analyzer._is_valid_pmcc_combination(leaps, short, quote)
        assert result is True
    
    def test_is_valid_pmcc_combination_short_strike_too_low(self):
        """Test PMCC validation with short strike below long strike."""
        leaps = self.create_test_option_contract(
            "AAPL241220C00150000", Decimal('150'), 450, Decimal('0.75')
        )
        
        short = self.create_test_option_contract(
            "AAPL240215C00145000", Decimal('145'), 30, Decimal('0.35')  # Strike < LEAPS
        )
        
        quote = StockQuote(symbol="AAPL", last=Decimal('148.00'))
        
        result = self.analyzer._is_valid_pmcc_combination(leaps, short, quote)
        assert result is False
    
    def test_is_valid_pmcc_combination_short_expires_after_long(self):
        """Test PMCC validation with short expiring after long."""
        leaps = self.create_test_option_contract(
            "AAPL240315C00130000", Decimal('130'), 90, Decimal('0.80')  # Shorter DTE
        )
        
        short = self.create_test_option_contract(
            "AAPL241220C00155000", Decimal('155'), 450, Decimal('0.30')  # Longer DTE
        )
        
        quote = StockQuote(symbol="AAPL", last=Decimal('150.00'))
        
        result = self.analyzer._is_valid_pmcc_combination(leaps, short, quote)
        assert result is False
    
    def test_is_valid_pmcc_combination_short_itm(self):
        """Test PMCC validation with short call ITM."""
        leaps = self.create_test_option_contract(
            "AAPL241220C00130000", Decimal('130'), 450, Decimal('0.80')
        )
        
        short = self.create_test_option_contract(
            "AAPL240215C00145000", Decimal('145'), 30, Decimal('0.70')  # ITM
        )
        
        quote = StockQuote(symbol="AAPL", last=Decimal('150.00'))  # Price > short strike
        
        result = self.analyzer._is_valid_pmcc_combination(leaps, short, quote)
        assert result is False
    
    def test_is_valid_pmcc_combination_negative_profit(self):
        """Test PMCC validation with negative max profit."""
        leaps = self.create_test_option_contract(
            "AAPL241220C00130000", Decimal('130'), 450, Decimal('0.80'),
            ask=Decimal('30.00')  # Very expensive
        )
        
        short = self.create_test_option_contract(
            "AAPL240215C00155000", Decimal('155'), 30, Decimal('0.30'),
            bid=Decimal('2.00')  # Low premium
        )
        
        quote = StockQuote(symbol="AAPL", last=Decimal('150.00'))
        
        # Net debit = 30.00 - 2.00 = 28.00
        # Max profit = (155-130) - 28.00 = 25 - 28 = -3 (negative)
        
        result = self.analyzer._is_valid_pmcc_combination(leaps, short, quote)
        assert result is False
    
    def test_is_valid_pmcc_combination_poor_risk_reward(self):
        """Test PMCC validation with poor risk-reward ratio."""
        leaps = self.create_test_option_contract(
            "AAPL241220C00130000", Decimal('130'), 450, Decimal('0.80'),
            ask=Decimal('28.00')
        )
        
        short = self.create_test_option_contract(
            "AAPL240215C00135000", Decimal('135'), 30, Decimal('0.30'),
            bid=Decimal('1.00')
        )
        
        quote = StockQuote(symbol="AAPL", last=Decimal('132.00'))
        
        # Net debit = 28.00 - 1.00 = 27.00
        # Max profit = (135-130) - 27.00 = 5 - 27 = -22 (way negative)
        
        result = self.analyzer._is_valid_pmcc_combination(leaps, short, quote)
        assert result is False
    
    def test_filter_leaps_contracts(self):
        """Test LEAPS contract filtering."""
        # Create test option chain with various contracts
        contracts = [
            # Valid LEAPS
            self.create_test_option_contract(
                "AAPL241220C00130000", Decimal('130'), 450, Decimal('0.80'), oi=50
            ),
            self.create_test_option_contract(
                "AAPL250117C00135000", Decimal('135'), 500, Decimal('0.75'), oi=30
            ),
            # Too short DTE
            self.create_test_option_contract(
                "AAPL240315C00140000", Decimal('140'), 200, Decimal('0.70'), oi=40
            ),
            # Delta too low
            self.create_test_option_contract(
                "AAPL241220C00160000", Decimal('160'), 450, Decimal('0.60'), oi=25
            ),
            # Low open interest
            self.create_test_option_contract(
                "AAPL241220C00125000", Decimal('125'), 450, Decimal('0.85'), oi=5
            )
        ]
        
        option_chain = OptionChain(
            underlying="AAPL",
            contracts=contracts
        )
        
        criteria = LEAPSCriteria()
        quote = StockQuote(symbol="AAPL", last=Decimal('150.00'))
        
        result = self.analyzer._filter_leaps_contracts(option_chain, criteria, quote)
        
        # Should return only the 2 valid LEAPS contracts
        assert len(result) == 2
        assert result[0].strike == Decimal('130')  # Higher delta first
        assert result[1].strike == Decimal('135')
    
    def test_filter_short_contracts(self):
        """Test short call contract filtering."""
        contracts = [
            # Valid short calls
            self.create_test_option_contract(
                "AAPL240215C00155000", Decimal('155'), 30, Decimal('0.30'), oi=20
            ),
            self.create_test_option_contract(
                "AAPL240315C00160000", Decimal('160'), 40, Decimal('0.25'), oi=15
            ),
            # DTE too short
            self.create_test_option_contract(
                "AAPL240201C00155000", Decimal('155'), 10, Decimal('0.30'), oi=25
            ),
            # DTE too long
            self.create_test_option_contract(
                "AAPL240601C00155000", Decimal('155'), 120, Decimal('0.30'), oi=30
            ),
            # Delta too high
            self.create_test_option_contract(
                "AAPL240215C00145000", Decimal('145'), 30, Decimal('0.50'), oi=40
            ),
            # Low open interest
            self.create_test_option_contract(
                "AAPL240215C00165000", Decimal('165'), 30, Decimal('0.20'), oi=2
            )
        ]
        
        option_chain = OptionChain(
            underlying="AAPL",
            contracts=contracts
        )
        
        criteria = ShortCallCriteria()
        quote = StockQuote(symbol="AAPL", last=Decimal('150.00'))
        
        result = self.analyzer._filter_short_contracts(option_chain, criteria, quote)
        
        # Should return only the 2 valid short call contracts
        assert len(result) == 2
        # Should be sorted by bid price (higher premium first)
        assert result[0].strike == Decimal('155')  # Likely higher premium
        assert result[1].strike == Decimal('160')
    
    def test_calculate_probability_score(self):
        """Test probability score calculation."""
        leaps = self.create_test_option_contract(
            "AAPL241220C00130000", Decimal('130'), 450, Decimal('0.80')
        )
        
        short = self.create_test_option_contract(
            "AAPL240315C00155000", Decimal('155'), 35, Decimal('0.30')  # Good DTE
        )
        
        quote = StockQuote(symbol="AAPL", last=Decimal('150.00'))
        breakeven = Decimal('152.50')  # Close to current price
        
        score = self.analyzer._calculate_probability_score(leaps, short, quote, breakeven)
        
        # Should be a reasonable score given good conditions
        assert Decimal('50') <= score <= Decimal('100')
    
    def test_calculate_liquidity_score(self):
        """Test liquidity score calculation."""
        leaps = self.create_test_option_contract(
            "AAPL241220C00130000", Decimal('130'), 450, Decimal('0.80'),
            bid=Decimal('24.50'), ask=Decimal('25.00'), volume=100, oi=200
        )
        
        short = self.create_test_option_contract(
            "AAPL240315C00155000", Decimal('155'), 35, Decimal('0.30'),
            bid=Decimal('2.50'), ask=Decimal('2.60'), volume=150, oi=300
        )
        
        score = self.analyzer._calculate_liquidity_score(leaps, short)
        
        # Should be a high score given tight spreads and good volume/OI
        assert score >= Decimal('70')
    
    def test_calculate_total_score(self):
        """Test total score calculation."""
        roi_potential = Decimal('15')  # 15% ROI
        risk_reward_ratio = Decimal('0.5')  # 1:2 risk:reward
        probability_score = Decimal('70')
        liquidity_score = Decimal('80')
        
        total = self.analyzer._calculate_total_score(
            roi_potential, risk_reward_ratio, probability_score, liquidity_score
        )
        
        # Should be a weighted average around these values
        assert Decimal('40') <= total <= Decimal('80')
    
    @patch.object(OptionsAnalyzer, '_get_option_chain')
    @patch.object(OptionsAnalyzer, '_get_current_quote')
    def test_find_pmcc_opportunities_no_data(self, mock_get_quote, mock_get_chain):
        """Test finding PMCC opportunities with no data."""
        mock_get_chain.return_value = None
        mock_get_quote.return_value = None
        
        result = self.analyzer.find_pmcc_opportunities("AAPL")
        
        assert result == []
    
    @patch.object(OptionsAnalyzer, '_get_option_chain')
    @patch.object(OptionsAnalyzer, '_get_current_quote')
    def test_find_pmcc_opportunities_no_leaps(self, mock_get_quote, mock_get_chain):
        """Test finding PMCC opportunities with no suitable LEAPS."""
        # Mock option chain with no suitable LEAPS
        option_chain = OptionChain(
            underlying="AAPL",
            contracts=[
                # Only short-term contracts
                self.create_test_option_contract(
                    "AAPL240215C00150000", Decimal('150'), 30, Decimal('0.50')
                )
            ]
        )
        
        quote = StockQuote(symbol="AAPL", last=Decimal('150.00'))
        
        mock_get_chain.return_value = option_chain
        mock_get_quote.return_value = quote
        
        result = self.analyzer.find_pmcc_opportunities("AAPL")
        
        assert result == []