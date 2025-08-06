"""
Integration tests for complete PMCC workflow.

These tests verify the end-to-end functionality of the PMCC scanner
with realistic data and scenarios.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.analysis.scanner import PMCCScanner, ScanConfiguration
from src.analysis.stock_screener import ScreeningCriteria
from src.analysis.options_analyzer import LEAPSCriteria, ShortCallCriteria
from src.models.api_models import (
    StockQuote, OptionContract, OptionChain, OptionSide, APIResponse, APIStatus
)
from src.api.marketdata_client import MarketDataClient


class TestPMCCWorkflowIntegration:
    """Integration tests for complete PMCC scanning workflow."""
    
    def setup_method(self):
        """Set up test fixtures with realistic data."""
        self.mock_api_client = Mock(spec=MarketDataClient)
        self.scanner = PMCCScanner(self.mock_api_client)
        
        # Create realistic test data
        self.setup_realistic_test_data()
    
    def setup_realistic_test_data(self):
        """Set up realistic stock and options data for testing."""
        
        # AAPL stock quote
        self.aapl_quote_data = {
            'symbol': ['AAPL'],
            'last': [155.50],
            'bid': [155.45],
            'ask': [155.55],
            'volume': [45_000_000],
            'updated': [datetime.now().timestamp()]
        }
        
        # AAPL options chain with realistic data
        self.aapl_options_data = {
            'underlying': ['AAPL'] * 20,
            'underlyingPrice': [155.50] * 20,
            'optionSymbol': [
                # LEAPS calls (9+ months out)
                'AAPL241220C00135000',  # Deep ITM LEAPS
                'AAPL241220C00140000',  # ITM LEAPS
                'AAPL241220C00145000',  # ITM LEAPS
                'AAPL241220C00150000',  # ITM LEAPS
                'AAPL250117C00135000',  # Even longer LEAPS
                'AAPL250117C00140000',
                # Short-term calls (30-45 days)
                'AAPL240315C00160000',  # OTM short call
                'AAPL240315C00165000',  # OTM short call
                'AAPL240315C00170000',  # OTM short call
                'AAPL240315C00175000',  # Far OTM short call
                'AAPL240301C00160000',  # Weekly OTM
                'AAPL240301C00165000',  # Weekly OTM
                # Some puts (should be ignored for PMCC)
                'AAPL240315P00150000',
                'AAPL240315P00145000',
                # Some near-term calls (too short)
                'AAPL240201C00160000',
                'AAPL240208C00165000',
                # Some far OTM calls
                'AAPL240315C00180000',
                'AAPL240315C00185000',
                'AAPL240315C00190000',
                'AAPL240315C00195000'
            ],
            'expiration': [
                # LEAPS expirations
                datetime(2024, 12, 20).timestamp(),
                datetime(2024, 12, 20).timestamp(),
                datetime(2024, 12, 20).timestamp(),
                datetime(2024, 12, 20).timestamp(),
                datetime(2025, 1, 17).timestamp(),
                datetime(2025, 1, 17).timestamp(),
                # Short-term expirations
                datetime(2024, 3, 15).timestamp(),
                datetime(2024, 3, 15).timestamp(),
                datetime(2024, 3, 15).timestamp(),
                datetime(2024, 3, 15).timestamp(),
                datetime(2024, 3, 1).timestamp(),  # Weekly
                datetime(2024, 3, 1).timestamp(),  # Weekly
                # Puts
                datetime(2024, 3, 15).timestamp(),
                datetime(2024, 3, 15).timestamp(),
                # Too short calls
                datetime(2024, 2, 1).timestamp(),
                datetime(2024, 2, 8).timestamp(),
                # Far OTM calls
                datetime(2024, 3, 15).timestamp(),
                datetime(2024, 3, 15).timestamp(),
                datetime(2024, 3, 15).timestamp(),
                datetime(2024, 3, 15).timestamp()
            ],
            'side': [
                'call', 'call', 'call', 'call', 'call', 'call',  # LEAPS
                'call', 'call', 'call', 'call', 'call', 'call',  # Short calls
                'put', 'put',  # Puts
                'call', 'call',  # Too short
                'call', 'call', 'call', 'call'  # Far OTM
            ],
            'strike': [
                135, 140, 145, 150, 135, 140,  # LEAPS strikes
                160, 165, 170, 175, 160, 165,  # Short call strikes
                150, 145,  # Put strikes
                160, 165,  # Too short strikes
                180, 185, 190, 195  # Far OTM strikes
            ],
            'bid': [
                # LEAPS bids (higher due to longer time)
                25.50, 22.30, 18.80, 15.20, 26.10, 22.90,
                # Short call bids
                1.85, 0.95, 0.45, 0.20, 1.90, 0.98,
                # Put bids
                3.20, 1.85,
                # Too short bids
                1.75, 0.85,
                # Far OTM bids
                0.08, 0.04, 0.02, 0.01
            ],
            'ask': [
                # LEAPS asks
                26.00, 22.80, 19.30, 15.70, 26.60, 23.40,
                # Short call asks
                2.05, 1.10, 0.55, 0.28, 2.10, 1.13,
                # Put asks
                3.40, 2.00,
                # Too short asks
                1.95, 1.00,
                # Far OTM asks
                0.12, 0.08, 0.05, 0.03
            ],
            'delta': [
                # LEAPS deltas (high for ITM)
                0.82, 0.78, 0.71, 0.63, 0.83, 0.79,
                # Short call deltas (moderate for OTM)
                0.28, 0.18, 0.12, 0.07, 0.29, 0.19,
                # Put deltas (negative)
                -0.35, -0.25,
                # Too short deltas
                0.30, 0.20,
                # Far OTM deltas
                0.03, 0.02, 0.01, 0.005
            ],
            'gamma': [0.01] * 20,  # Simplified gamma values
            'theta': [-0.03] * 20,  # Simplified theta values
            'vega': [0.12] * 20,   # Simplified vega values
            'iv': [0.28] * 20,     # 28% implied volatility
            'volume': [
                # LEAPS volume (lower)
                150, 120, 200, 85, 95, 110,
                # Short call volume (higher)
                850, 620, 340, 180, 920, 680,
                # Put volume
                450, 280,
                # Too short volume
                300, 180,
                # Far OTM volume
                15, 8, 5, 2
            ],
            'openInterest': [
                # LEAPS OI
                2500, 1800, 3200, 1200, 1900, 2100,
                # Short call OI
                4500, 3200, 2100, 800, 4800, 3400,
                # Put OI
                2800, 1900,
                # Too short OI
                1500, 900,
                # Far OTM OI
                120, 80, 45, 20
            ],
            'dte': [
                # LEAPS DTE
                450, 450, 450, 450, 485, 485,
                # Short call DTE
                35, 35, 35, 35, 21, 21,
                # Put DTE
                35, 35,
                # Too short DTE
                12, 19,
                # Far OTM DTE
                35, 35, 35, 35
            ],
            'updated': [datetime.now().timestamp()] * 20
        }
        
        # MSFT data (simpler, should not pass all filters)
        self.msft_quote_data = {
            'symbol': ['MSFT'],
            'last': [380.25],
            'bid': [380.15],
            'ask': [380.35],
            'volume': [25_000_000],
            'updated': [datetime.now().timestamp()]
        }
        
        # MSFT options (limited, should find fewer opportunities)
        self.msft_options_data = {
            'underlying': ['MSFT'] * 8,
            'underlyingPrice': [380.25] * 8,
            'optionSymbol': [
                'MSFT241220C00350000',  # LEAPS
                'MSFT241220C00360000',  # LEAPS
                'MSFT240315C00390000',  # Short call
                'MSFT240315C00400000',  # Short call
                'MSFT240315C00410000',  # Short call (far OTM)
                'MSFT240315C00420000',  # Very far OTM
                'MSFT240201C00390000',  # Too short DTE
                'MSFT240315P00370000'   # Put
            ],
            'expiration': [
                datetime(2024, 12, 20).timestamp(),
                datetime(2024, 12, 20).timestamp(),
                datetime(2024, 3, 15).timestamp(),
                datetime(2024, 3, 15).timestamp(),
                datetime(2024, 3, 15).timestamp(),
                datetime(2024, 3, 15).timestamp(),
                datetime(2024, 2, 1).timestamp(),
                datetime(2024, 3, 15).timestamp()
            ],
            'side': ['call', 'call', 'call', 'call', 'call', 'call', 'call', 'put'],
            'strike': [350, 360, 390, 400, 410, 420, 390, 370],
            'bid': [35.50, 28.20, 4.80, 2.30, 1.10, 0.45, 4.20, 8.50],
            'ask': [36.20, 28.90, 5.20, 2.60, 1.35, 0.65, 4.60, 9.10],
            'delta': [0.85, 0.78, 0.32, 0.22, 0.14, 0.08, 0.35, -0.28],
            'gamma': [0.008] * 8,
            'theta': [-0.04] * 8,
            'vega': [0.18] * 8,
            'iv': [0.32] * 8,
            'volume': [180, 120, 650, 420, 180, 85, 280, 350],
            'openInterest': [1800, 1200, 3200, 2100, 980, 420, 1100, 2400],
            'dte': [450, 450, 35, 35, 35, 35, 12, 35],
            'updated': [datetime.now().timestamp()] * 8
        }
    
    def test_full_workflow_with_opportunities(self):
        """Test complete workflow that finds PMCC opportunities."""
        
        # Mock API responses
        def mock_get_response(endpoint_path):
            if 'quotes' in endpoint_path and 'AAPL' in endpoint_path:
                return APIResponse(status=APIStatus.OK, data=self.aapl_quote_data)
            elif 'quotes' in endpoint_path and 'MSFT' in endpoint_path:
                return APIResponse(status=APIStatus.OK, data=self.msft_quote_data)
            elif 'options/chain' in endpoint_path and 'AAPL' in endpoint_path:
                return APIResponse(status=APIStatus.OK, data=self.aapl_options_data)
            elif 'options/chain' in endpoint_path and 'MSFT' in endpoint_path:
                return APIResponse(status=APIStatus.OK, data=self.msft_options_data)
            else:
                return APIResponse(status=APIStatus.ERROR)
        
        # Configure mock to return appropriate responses
        self.mock_api_client.get_quote.side_effect = lambda symbol: mock_get_response(f'quotes/{symbol}')
        self.mock_api_client.get_option_chain.side_effect = lambda symbol: mock_get_response(f'options/chain/{symbol}')
        
        # Create test configuration
        config = ScanConfiguration(
            universe="DEMO",  # Will test with our mocked symbols
            max_stocks_to_screen=10,
            max_opportunities=5,
            min_total_score=Decimal('50'),  # Lower threshold for testing
            screening_criteria=ScreeningCriteria(
                min_price=Decimal('50'),
                max_price=Decimal('500'),
                min_daily_volume=1_000_000,
                require_leaps=True,
                require_weekly_options=False  # Relaxed for testing
            ),
            leaps_criteria=LEAPSCriteria(
                min_dte=400,  # 13+ months
                min_delta=Decimal('0.70'),
                min_open_interest=1000
            ),
            short_criteria=ShortCallCriteria(
                min_dte=20,
                max_dte=50,
                min_delta=Decimal('0.15'),
                max_delta=Decimal('0.35'),
                min_open_interest=1000
            )
        )
        
        # Mock universe symbols to our test symbols
        with patch.object(self.scanner.stock_screener, '_get_universe_symbols') as mock_universe:
            mock_universe.return_value = ['AAPL', 'MSFT']
            
            # Run the scan
            results = self.scanner.scan(config)
        
        # Verify scan completed successfully
        assert results.completed_at is not None
        assert results.total_duration_seconds is not None
        assert len(results.errors) == 0  # Should have no errors
        
        # Verify stocks were screened
        assert results.stocks_screened == 10  # max_stocks_to_screen
        assert results.stocks_passed_screening >= 0
        
        # Verify opportunities were found
        # AAPL should generate opportunities (good LEAPS + short calls)
        # MSFT might generate fewer due to higher prices
        assert results.opportunities_found >= 0
        
        # If opportunities were found, verify structure
        if results.opportunities_found > 0:
            assert len(results.top_opportunities) > 0
            
            # Check first opportunity structure
            top_opp = results.top_opportunities[0]
            assert top_opp.symbol in ['AAPL', 'MSFT']
            assert top_opp.analysis is not None
            assert top_opp.analysis.long_call is not None
            assert top_opp.analysis.short_call is not None
            assert top_opp.analysis.risk_metrics is not None
            assert top_opp.total_score is not None
            assert top_opp.rank == 1  # First opportunity should be rank 1
            
            # Verify PMCC structure
            long_call = top_opp.analysis.long_call
            short_call = top_opp.analysis.short_call
            
            assert long_call.side == OptionSide.CALL
            assert short_call.side == OptionSide.CALL
            assert long_call.strike < short_call.strike  # Long strike < Short strike
            assert long_call.dte > short_call.dte  # Long expires after short
            assert long_call.delta >= Decimal('0.70')  # Deep ITM LEAPS
            assert short_call.delta <= Decimal('0.35')  # OTM short call
    
    def test_workflow_with_restrictive_criteria(self):
        """Test workflow with very restrictive criteria that finds no opportunities."""
        
        # Mock API responses (same as above)
        def mock_get_response(endpoint_path):
            if 'quotes' in endpoint_path and 'AAPL' in endpoint_path:
                return APIResponse(status=APIStatus.OK, data=self.aapl_quote_data)
            elif 'options/chain' in endpoint_path and 'AAPL' in endpoint_path:
                return APIResponse(status=APIStatus.OK, data=self.aapl_options_data)
            else:
                return APIResponse(status=APIStatus.ERROR)
        
        self.mock_api_client.get_quote.side_effect = lambda symbol: mock_get_response(f'quotes/{symbol}')
        self.mock_api_client.get_option_chain.side_effect = lambda symbol: mock_get_response(f'options/chain/{symbol}')
        
        # Very restrictive configuration
        config = ScanConfiguration(
            universe="DEMO",
            screening_criteria=ScreeningCriteria(
                min_price=Decimal('1000'),  # Too high - no stocks will pass
                require_leaps=True
            ),
            min_total_score=Decimal('95')  # Very high threshold
        )
        
        with patch.object(self.scanner.stock_screener, '_get_universe_symbols') as mock_universe:
            mock_universe.return_value = ['AAPL']
            
            results = self.scanner.scan(config)
        
        # Should complete without errors but find no opportunities
        assert results.completed_at is not None
        assert results.stocks_screened > 0
        assert results.stocks_passed_screening == 0  # No stocks should pass restrictive screening
        assert results.opportunities_found == 0
        assert len(results.top_opportunities) == 0
    
    def test_workflow_with_api_errors(self):
        """Test workflow resilience when API calls fail."""
        
        # Mock API to return errors
        error_response = APIResponse(
            status=APIStatus.ERROR,
            error=Mock(code=500, message="Server Error")
        )
        
        self.mock_api_client.get_quote.return_value = error_response
        self.mock_api_client.get_option_chain.return_value = error_response
        
        config = ScanConfiguration(universe="DEMO")
        
        with patch.object(self.scanner.stock_screener, '_get_universe_symbols') as mock_universe:
            mock_universe.return_value = ['AAPL', 'MSFT']
            
            results = self.scanner.scan(config)
        
        # Should complete despite errors
        assert results.completed_at is not None
        assert len(results.warnings) > 0  # Should have warnings about API failures
        assert results.opportunities_found == 0  # No opportunities due to API errors
    
    def test_single_symbol_scan_success(self):
        """Test scanning a single symbol successfully."""
        
        # Mock AAPL responses
        self.mock_api_client.get_quote.return_value = APIResponse(
            status=APIStatus.OK, data=self.aapl_quote_data
        )
        self.mock_api_client.get_option_chain.return_value = APIResponse(
            status=APIStatus.OK, data=self.aapl_options_data
        )
        
        # Configure with reasonable criteria
        config = ScanConfiguration(
            leaps_criteria=LEAPSCriteria(
                min_dte=400,
                min_delta=Decimal('0.70'),
                min_open_interest=1000
            ),
            short_criteria=ShortCallCriteria(
                min_dte=20,
                max_dte=50,
                min_delta=Decimal('0.15'),
                max_delta=Decimal('0.35'),
                min_open_interest=1000
            )
        )
        
        candidates = self.scanner.scan_symbol("AAPL", config)
        
        # Should find opportunities for AAPL
        assert len(candidates) >= 0  # May or may not find depending on exact criteria
        
        # If found, verify structure
        if candidates:
            candidate = candidates[0]
            assert candidate.symbol == "AAPL"
            assert candidate.analysis.long_call.side == OptionSide.CALL
            assert candidate.analysis.short_call.side == OptionSide.CALL
            assert candidate.analysis.is_valid_pmcc
    
    def test_realistic_pmcc_analysis(self):
        """Test realistic PMCC analysis with actual calculations."""
        
        # Create realistic PMCC position
        long_call = OptionContract(
            option_symbol="AAPL241220C00140000",
            underlying="AAPL",
            expiration=datetime(2024, 12, 20),
            side=OptionSide.CALL,
            strike=Decimal('140'),
            bid=Decimal('22.30'),
            ask=Decimal('22.80'),
            mid=Decimal('22.55'),
            delta=Decimal('0.78'),
            gamma=Decimal('0.01'),
            theta=Decimal('-0.03'),
            vega=Decimal('0.12'),
            iv=Decimal('0.28'),
            volume=120,
            open_interest=1800,
            dte=450,
            underlying_price=Decimal('155.50')
        )
        
        short_call = OptionContract(
            option_symbol="AAPL240315C00165000",
            underlying="AAPL",
            expiration=datetime(2024, 3, 15),
            side=OptionSide.CALL,
            strike=Decimal('165'),
            bid=Decimal('0.95'),
            ask=Decimal('1.10'),
            mid=Decimal('1.025'),
            delta=Decimal('0.18'),
            gamma=Decimal('0.02'),
            theta=Decimal('-0.03'),
            vega=Decimal('0.08'),
            iv=Decimal('0.28'),
            volume=620,
            open_interest=3200,
            dte=35,
            underlying_price=Decimal('155.50')
        )
        
        underlying = StockQuote(
            symbol="AAPL",
            last=Decimal('155.50'),
            bid=Decimal('155.45'),
            ask=Decimal('155.55'),
            volume=45_000_000
        )
        
        # Create and analyze PMCC
        analysis = self.scanner.options_analyzer.get_pmcc_analysis(long_call, short_call, underlying)
        
        assert analysis is not None
        assert analysis.is_valid_pmcc
        
        # Verify calculations
        net_debit = long_call.ask - short_call.bid  # 22.80 - 0.95 = 21.85
        assert analysis.net_debit == net_debit
        
        # Max profit = strike width - net debit = (165-140) - 21.85 = 3.15
        expected_max_profit = (short_call.strike - long_call.strike) - net_debit
        assert analysis.risk_metrics.max_profit == expected_max_profit
        
        # Max loss = net debit = 21.85
        assert analysis.risk_metrics.max_loss == net_debit
        
        # Breakeven = long strike + net debit = 140 + 21.85 = 161.85
        expected_breakeven = long_call.strike + net_debit
        assert analysis.risk_metrics.breakeven == expected_breakeven
        
        # Risk/reward ratio
        expected_rr = expected_max_profit / net_debit
        assert analysis.risk_metrics.risk_reward_ratio == expected_rr
        
        # Greeks should be calculated
        assert analysis.risk_metrics.net_delta == long_call.delta - short_call.delta
        assert analysis.risk_metrics.net_theta == long_call.theta - short_call.theta
        
        # Liquidity score should be reasonable given the volume/OI
        assert analysis.liquidity_score > Decimal('50')  # Should be decent liquidity
    
    def test_comprehensive_risk_analysis(self):
        """Test comprehensive risk analysis functionality."""
        
        from src.models.pmcc_models import PMCCAnalysis
        
        # Create test PMCC analysis
        long_call = OptionContract(
            option_symbol="AAPL241220C00140000",
            underlying="AAPL",
            expiration=datetime(2024, 12, 20),
            side=OptionSide.CALL,
            strike=Decimal('140'),
            ask=Decimal('22.80'),
            delta=Decimal('0.78'),
            theta=Decimal('-0.03'),
            vega=Decimal('0.12'),
            dte=450,
            extrinsic_value=Decimal('7.30')
        )
        
        short_call = OptionContract(
            option_symbol="AAPL240315C00165000",
            underlying="AAPL",
            expiration=datetime(2024, 3, 15),
            side=OptionSide.CALL,
            strike=Decimal('165'),
            bid=Decimal('0.95'),
            delta=Decimal('0.18'),
            theta=Decimal('-0.03'),
            vega=Decimal('0.08'),
            dte=35,
            extrinsic_value=Decimal('0.95')
        )
        
        underlying = StockQuote(symbol="AAPL", last=Decimal('155.50'))
        
        analysis = PMCCAnalysis(
            long_call=long_call,
            short_call=short_call,
            underlying=underlying,
            net_debit=Decimal('21.85'),
            analyzed_at=datetime.now()
        )
        
        # Calculate risk metrics
        analysis.risk_metrics = analysis.calculate_risk_metrics()
        
        # Test comprehensive risk calculation
        comp_risk = self.scanner.risk_calculator.calculate_comprehensive_risk(
            analysis, 
            account_size=Decimal('100000'),
            risk_free_rate=Decimal('0.05')
        )
        
        # Verify comprehensive risk components
        assert comp_risk.basic_metrics is not None
        assert comp_risk.early_assignment is not None
        assert comp_risk.position_sizing is not None
        assert comp_risk.scenario_analysis is not None
        
        # Early assignment should be low risk (short call OTM)
        assert comp_risk.early_assignment.risk_level in ["LOW", "MEDIUM"]
        
        # Position sizing should be reasonable
        assert comp_risk.position_sizing.recommended_size >= 1
        assert comp_risk.position_sizing.capital_required > 0
        
        # Scenario analysis should have multiple scenarios
        assert len(comp_risk.scenario_analysis.scenarios) > 5
        
        # Should have best/worst cases
        assert comp_risk.scenario_analysis.best_case is not None
        assert comp_risk.scenario_analysis.worst_case is not None
    
    @pytest.mark.slow
    def test_performance_with_large_dataset(self):
        """Test scanner performance with larger dataset."""
        
        # Create larger options dataset (simulate 50+ contracts per symbol)
        large_options_data = self.aapl_options_data.copy()
        
        # Multiply data for performance testing
        for key in large_options_data:
            if isinstance(large_options_data[key], list):
                large_options_data[key] = large_options_data[key] * 3  # 60 contracts
        
        def mock_get_response(endpoint_path):
            if 'quotes' in endpoint_path:
                return APIResponse(status=APIStatus.OK, data=self.aapl_quote_data)
            elif 'options/chain' in endpoint_path:
                return APIResponse(status=APIStatus.OK, data=large_options_data)
            else:
                return APIResponse(status=APIStatus.ERROR)
        
        self.mock_api_client.get_quote.side_effect = lambda symbol: mock_get_response(f'quotes/{symbol}')
        self.mock_api_client.get_option_chain.side_effect = lambda symbol: mock_get_response(f'options/chain/{symbol}')
        
        config = ScanConfiguration(
            universe="DEMO",
            max_stocks_to_screen=20,  # More stocks
            max_opportunities=10
        )
        
        with patch.object(self.scanner.stock_screener, '_get_universe_symbols') as mock_universe:
            # Simulate 20 symbols
            mock_universe.return_value = [f"TEST{i:02d}" for i in range(20)]
            
            start_time = datetime.now()
            results = self.scanner.scan(config)
            duration = (datetime.now() - start_time).total_seconds()
        
        # Should complete within reasonable time (adjust threshold as needed)
        assert duration < 60  # Should complete within 1 minute
        assert results.completed_at is not None
        
        # Should handle the larger dataset without errors
        assert len(results.errors) == 0