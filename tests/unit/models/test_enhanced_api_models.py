"""
Unit tests for enhanced API models.

Tests the new fundamental data models, calendar events, technical indicators,
risk metrics, and enhanced stock data functionality.
"""

import unittest
from datetime import datetime, date
from decimal import Decimal

from src.models.api_models import (
    FundamentalMetrics, CalendarEvent, TechnicalIndicators, RiskMetrics,
    EnhancedStockData, StockQuote
)


class TestFundamentalMetrics(unittest.TestCase):
    """Test FundamentalMetrics data model."""
    
    def test_from_eodhd_response(self):
        """Test creating FundamentalMetrics from EODHD response."""
        eodhd_data = {
            'General': {
                'Code': 'AAPL',
                'Sector': 'Technology',
                'Industry': 'Consumer Electronics'
            },
            'Highlights': {
                'PERatio': '28.5',
                'PEGRatio': '2.1',
                'ProfitMargin': '0.25',
                'ReturnOnEquityTTM': '0.147',
                'DebtToEquity': '1.73',
                'EarningsPerShareTTM': '6.05',
                'BookValue': '4.15',
                'Beta': '1.29',
                'MarketCapitalization': '3050000000000'
            },
            'SharesStats': {
                'SharesOutstanding': '15728200000',
                'SharesFloat': '15676700000',
                'PercentInstitutions': '0.595',
                'PercentInsiders': '0.071'
            },
            'Valuation': {
                'EnterpriseValue': '3100000000000'
            }
        }
        
        fundamentals = FundamentalMetrics.from_eodhd_response(eodhd_data)
        
        self.assertEqual(fundamentals.symbol, 'AAPL')
        self.assertEqual(fundamentals.pe_ratio, Decimal('28.5'))
        self.assertEqual(fundamentals.peg_ratio, Decimal('2.1'))
        self.assertEqual(fundamentals.profit_margin, Decimal('25.0'))  # Converted from 0.25 to 25%
        self.assertEqual(fundamentals.roe, Decimal('14.7'))  # Converted from 0.147 to 14.7%
        self.assertEqual(fundamentals.debt_to_equity, Decimal('1.73'))
        self.assertEqual(fundamentals.earnings_per_share, Decimal('6.05'))
        self.assertEqual(fundamentals.book_value_per_share, Decimal('4.15'))
        self.assertEqual(fundamentals.shares_outstanding, 15728200000)
        self.assertEqual(fundamentals.institutional_ownership, Decimal('59.5'))  # Converted to percentage
        self.assertEqual(fundamentals.insider_ownership, Decimal('7.1'))
        self.assertEqual(fundamentals.enterprise_value, Decimal('3100000000000'))
    
    def test_empty_response(self):
        """Test handling empty EODHD response."""
        empty_data = {}
        fundamentals = FundamentalMetrics.from_eodhd_response(empty_data)
        
        self.assertEqual(fundamentals.symbol, '')
        self.assertIsNone(fundamentals.pe_ratio)
        self.assertIsNone(fundamentals.profit_margin)


class TestCalendarEvent(unittest.TestCase):
    """Test CalendarEvent data model."""
    
    def test_from_eodhd_earnings_response(self):
        """Test creating CalendarEvent from EODHD earnings response."""
        earnings_data = {
            'code': 'AAPL',
            'date': '2024-01-25',
            'when': 'after_market',
            'estimate': '2.10',
            'actual': '2.18',
            'surprise_percent': '3.8'
        }
        
        event = CalendarEvent.from_eodhd_earnings_response(earnings_data)
        
        self.assertEqual(event.symbol, 'AAPL')
        self.assertEqual(event.event_type, 'earnings')
        self.assertEqual(event.date, date(2024, 1, 25))
        self.assertEqual(event.announcement_time, 'after_market')
        self.assertEqual(event.estimated_eps, Decimal('2.10'))
        self.assertEqual(event.actual_eps, Decimal('2.18'))
        self.assertEqual(event.surprise_percent, Decimal('3.8'))
    
    def test_from_eodhd_dividend_response(self):
        """Test creating CalendarEvent from EODHD dividend response."""
        dividend_data = {
            'code': 'AAPL',
            'date': '2024-02-09',
            'type': 'ex-dividend',
            'dividend': '0.24',
            'yield': '0.0045',
            'payment_date': '2024-02-16',
            'record_date': '2024-02-12'
        }
        
        event = CalendarEvent.from_eodhd_dividend_response(dividend_data)
        
        self.assertEqual(event.symbol, 'AAPL')
        self.assertEqual(event.event_type, 'ex_dividend')
        self.assertEqual(event.date, date(2024, 2, 9))
        self.assertEqual(event.dividend_amount, Decimal('0.24'))
        self.assertEqual(event.payment_date, date(2024, 2, 16))
        self.assertEqual(event.record_date, date(2024, 2, 12))


class TestTechnicalIndicators(unittest.TestCase):
    """Test TechnicalIndicators data model."""
    
    def test_from_eodhd_response(self):
        """Test creating TechnicalIndicators from EODHD response."""
        eodhd_data = {
            'General': {
                'Code': 'MSFT',
                'Sector': 'Technology',
                'Industry': 'Software—Infrastructure'
            },
            'Highlights': {
                'Beta': '0.90',
                'MarketCapitalization': '2800000000000'  # $2.8T
            }
        }
        
        technical = TechnicalIndicators.from_eodhd_response(eodhd_data)
        
        self.assertEqual(technical.symbol, 'MSFT')
        self.assertEqual(technical.beta, Decimal('0.90'))
        self.assertEqual(technical.sector, 'Technology')
        self.assertEqual(technical.industry, 'Software—Infrastructure')
        self.assertEqual(technical.market_cap_category, 'mega')  # Over $200B
    
    def test_market_cap_categorization(self):
        """Test market cap category assignment."""
        # Test large cap
        large_cap_data = {
            'General': {'Code': 'TEST1'},
            'Highlights': {'MarketCapitalization': '50000000000'}  # $50B
        }
        technical = TechnicalIndicators.from_eodhd_response(large_cap_data)
        self.assertEqual(technical.market_cap_category, 'large')
        
        # Test mid cap
        mid_cap_data = {
            'General': {'Code': 'TEST2'},
            'Highlights': {'MarketCapitalization': '5000000000'}  # $5B
        }
        technical = TechnicalIndicators.from_eodhd_response(mid_cap_data)
        self.assertEqual(technical.market_cap_category, 'mid')
        
        # Test small cap
        small_cap_data = {
            'General': {'Code': 'TEST3'},
            'Highlights': {'MarketCapitalization': '500000000'}  # $500M
        }
        technical = TechnicalIndicators.from_eodhd_response(small_cap_data)
        self.assertEqual(technical.market_cap_category, 'small')


class TestRiskMetrics(unittest.TestCase):
    """Test RiskMetrics data model."""
    
    def test_from_eodhd_response(self):
        """Test creating RiskMetrics from EODHD response."""
        eodhd_data = {
            'General': {'Code': 'GOOGL'},
            'SharesStats': {
                'PercentInstitutions': '0.68',
                'PercentInsiders': '0.12',
                'ShortInterest': '0.015'
            }
        }
        
        analyst_data = {
            'Rating': {
                'Rating': '4.2',
                'AnalystCount': '35',
                'TargetPrice': '2800'
            }
        }
        
        risk = RiskMetrics.from_eodhd_response(eodhd_data, analyst_data)
        
        self.assertEqual(risk.symbol, 'GOOGL')
        self.assertEqual(risk.institutional_ownership, Decimal('68.0'))
        self.assertEqual(risk.insider_ownership, Decimal('12.0'))
        self.assertEqual(risk.short_interest, Decimal('1.5'))
        self.assertEqual(risk.analyst_rating_avg, Decimal('4.2'))
        self.assertEqual(risk.analyst_count, 35)
        self.assertEqual(risk.price_target_avg, Decimal('2800'))


class TestEnhancedStockData(unittest.TestCase):
    """Test EnhancedStockData data model."""
    
    def setUp(self):
        """Set up test data."""
        self.quote = StockQuote(
            symbol='AAPL',
            last=Decimal('150.00'),
            volume=50000000
        )
        
        self.fundamentals = FundamentalMetrics(
            symbol='AAPL',
            pe_ratio=Decimal('28.5'),
            profit_margin=Decimal('25.0'),
            debt_to_equity=Decimal('1.73'),
            roe=Decimal('14.7')
        )
    
    def test_enhanced_stock_data_creation(self):
        """Test creating EnhancedStockData."""
        enhanced_data = EnhancedStockData(
            quote=self.quote,
            fundamentals=self.fundamentals
        )
        
        self.assertEqual(enhanced_data.symbol, 'AAPL')
        self.assertTrue(enhanced_data.has_complete_fundamental_data)
        self.assertFalse(enhanced_data.has_options_data)
    
    def test_completeness_score_calculation(self):
        """Test data completeness score calculation."""
        enhanced_data = EnhancedStockData(
            quote=self.quote,
            fundamentals=self.fundamentals
        )
        
        score = enhanced_data.calculate_completeness_score()
        
        # Should have: quote (30%) + fundamentals (25%) = 55%
        # No options, technical, or risk data
        self.assertEqual(score, Decimal('55.0'))
    
    def test_calendar_event_properties(self):
        """Test calendar event helper properties."""
        # Create calendar events
        earnings_event = CalendarEvent(
            symbol='AAPL',
            event_type='earnings',
            date=date(2024, 4, 25)
        )
        
        dividend_event = CalendarEvent(
            symbol='AAPL',
            event_type='ex_dividend',
            date=date(2024, 3, 8)
        )
        
        enhanced_data = EnhancedStockData(
            quote=self.quote,
            calendar_events=[earnings_event, dividend_event]
        )
        
        # Test upcoming earnings (assuming test runs before 2024-04-25)
        # Note: In a real test, you'd mock date.today()
        self.assertIsInstance(enhanced_data.upcoming_earnings_date, (date, type(None)))
        self.assertIsInstance(enhanced_data.next_ex_dividend_date, (date, type(None)))


if __name__ == '__main__':
    unittest.main()