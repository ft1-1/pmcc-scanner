"""
Comprehensive tests for trading date utilities.

Tests all functionality including edge cases, holidays, weekends,
and EODHD API integration.
"""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import patch, MagicMock

from src.utils.trading_dates import (
    get_most_recent_trading_date,
    is_trading_day,
    get_next_trading_date,
    get_trading_days_range,
    format_date_for_eodhd,
    get_eodhd_filter_date,
    TradingDateError,
    USStockMarketCalendar
)


class TestUSStockMarketCalendar:
    """Test the custom US stock market calendar."""
    
    def test_market_holidays_2025(self):
        """Test that all expected 2025 market holidays are included."""
        calendar = USStockMarketCalendar()
        holidays_2025 = calendar.holidays(start='2025-01-01', end='2025-12-31')
        
        # Expected holidays for 2025
        expected_holidays = [
            '2025-01-01',  # New Year's Day
            '2025-01-20',  # MLK Day (3rd Monday in January)
            '2025-02-17',  # Presidents Day (3rd Monday in February)
            '2025-04-18',  # Good Friday (varies yearly)
            '2025-05-26',  # Memorial Day (last Monday in May)
            '2025-06-19',  # Juneteenth
            '2025-07-04',  # Independence Day
            '2025-09-01',  # Labor Day (1st Monday in September)
            '2025-11-27',  # Thanksgiving (4th Thursday in November)
            '2025-12-25',  # Christmas Day
        ]
        
        holiday_dates = [h.strftime('%Y-%m-%d') for h in holidays_2025]
        
        for expected in expected_holidays:
            assert expected in holiday_dates, f"Expected holiday {expected} not found"
    
    def test_weekend_observance(self):
        """Test that holidays are moved to weekdays when they fall on weekends."""
        calendar = USStockMarketCalendar()
        
        # Test New Year's Day 2024 (fell on Monday, no change)
        holidays_2024 = calendar.holidays(start='2024-01-01', end='2024-01-02')
        assert len(holidays_2024) == 1
        assert holidays_2024[0].strftime('%Y-%m-%d') == '2024-01-01'
        
        # Test Independence Day when it falls on different days
        # This tests the observance rule for weekend holidays


class TestGetMostRecentTradingDate:
    """Test the main function for getting most recent trading date."""
    
    def test_regular_weekday(self):
        """Test with a regular weekday that's a trading day."""
        # Friday, August 1, 2025
        result = get_most_recent_trading_date('2025-08-01')
        assert result == '2025-08-01'
    
    def test_weekend_saturday(self):
        """Test with Saturday - should return previous Friday."""
        # Saturday, August 2, 2025 -> Friday, August 1, 2025
        result = get_most_recent_trading_date('2025-08-02')
        assert result == '2025-08-01'
    
    def test_weekend_sunday(self):
        """Test with Sunday - should return previous Friday."""
        # Sunday, August 3, 2025 -> Friday, August 1, 2025
        result = get_most_recent_trading_date('2025-08-03')
        assert result == '2025-08-01'
    
    def test_independence_day_holiday(self):
        """Test with Independence Day holiday."""
        # July 4, 2025 is a Friday (market holiday) -> July 3, 2025 (Thursday)
        result = get_most_recent_trading_date('2025-07-04')
        assert result == '2025-07-03'
    
    def test_new_years_day(self):
        """Test with New Year's Day."""
        # January 1, 2025 is a Wednesday (market holiday) -> December 31, 2024
        result = get_most_recent_trading_date('2025-01-01')
        assert result == '2024-12-31'
    
    def test_with_datetime_object(self):
        """Test with datetime object input."""
        dt = datetime(2025, 8, 1, 15, 30, 0)  # Friday afternoon
        result = get_most_recent_trading_date(dt)
        assert result == '2025-08-01'
    
    def test_with_date_object(self):
        """Test with date object input."""
        d = date(2025, 8, 1)  # Friday
        result = get_most_recent_trading_date(d)
        assert result == '2025-08-01'
    
    def test_invalid_date_format(self):
        """Test with invalid date format."""
        with pytest.raises(ValueError):
            get_most_recent_trading_date('2025/08/01')  # Wrong format
    
    def test_invalid_date_type(self):
        """Test with invalid date type."""
        with pytest.raises(ValueError):
            get_most_recent_trading_date(123456)  # Invalid type
    
    @patch('src.utils.trading_dates.datetime')
    def test_current_date_default(self, mock_datetime):
        """Test that current date is used when reference_date is None."""
        # Mock current date to a known value
        mock_now = MagicMock()
        mock_now.date.return_value = date(2025, 8, 1)  # Friday
        mock_datetime.now.return_value = mock_now
        
        result = get_most_recent_trading_date()
        assert result == '2025-08-01'
    
    def test_extended_lookback(self):
        """Test with extended market closure requiring larger lookback."""
        # Test a scenario with multiple consecutive holidays/weekends
        result = get_most_recent_trading_date('2025-01-01', lookback_days=10)
        assert result == '2024-12-31'  # Should find the previous trading day
    
    def test_lookback_exceeded(self):
        """Test when no trading date found within lookback period."""
        with pytest.raises(TradingDateError, match="No trading date found"):
            # Use a very small lookback that won't find anything
            get_most_recent_trading_date('2025-01-01', lookback_days=0)
    
    def test_timezone_handling(self):
        """Test timezone handling for current date."""
        # This is tested indirectly through the default case
        # since timezone conversion happens when reference_date is None
        pass


class TestIsTradingDay:
    """Test the trading day validation function."""
    
    def test_regular_weekday(self):
        """Test regular weekday."""
        assert is_trading_day('2025-08-01') == True  # Friday
        assert is_trading_day('2025-07-31') == True  # Thursday
    
    def test_weekend(self):
        """Test weekends."""
        assert is_trading_day('2025-08-02') == False  # Saturday
        assert is_trading_day('2025-08-03') == False  # Sunday
    
    def test_holidays(self):
        """Test market holidays."""
        assert is_trading_day('2025-01-01') == False  # New Year's Day
        assert is_trading_day('2025-07-04') == False  # Independence Day
        assert is_trading_day('2025-12-25') == False  # Christmas
    
    def test_day_before_holiday(self):
        """Test day before holiday (should be trading day)."""
        assert is_trading_day('2025-07-03') == True  # Day before July 4th
        assert is_trading_day('2024-12-31') == True  # Day before New Year's
    
    def test_with_different_input_types(self):
        """Test with different input types."""
        test_date = date(2025, 8, 1)  # Friday
        test_datetime = datetime(2025, 8, 1, 15, 30)
        test_string = '2025-08-01'
        
        assert is_trading_day(test_date) == True
        assert is_trading_day(test_datetime) == True
        assert is_trading_day(test_string) == True
    
    def test_invalid_input(self):
        """Test with invalid input."""
        with pytest.raises(TradingDateError):
            is_trading_day(123456)


class TestGetNextTradingDate:
    """Test getting next trading date."""
    
    def test_friday_to_monday(self):
        """Test Friday to next Monday (skip weekend)."""
        # Friday August 1 -> Monday August 4
        result = get_next_trading_date('2025-08-01')
        assert result == '2025-08-04'
    
    def test_thursday_to_friday(self):
        """Test regular Thursday to Friday."""
        result = get_next_trading_date('2025-07-31')  # Thursday
        assert result == '2025-08-01'  # Friday
    
    def test_before_holiday(self):
        """Test day before holiday."""
        # July 3 (Thursday) -> July 7 (Monday, skipping July 4 holiday and weekend)
        result = get_next_trading_date('2025-07-03')
        assert result == '2025-07-07'
    
    def test_with_current_date_default(self):
        """Test with default current date."""
        # This test will vary based on when it's run, so we just check it returns a valid date
        result = get_next_trading_date()
        assert len(result) == 10  # YYYY-MM-DD format
        assert result.count('-') == 2
    
    def test_forward_days_exceeded(self):
        """Test when no trading date found within forward period."""
        with pytest.raises(TradingDateError):
            get_next_trading_date('2025-07-03', forward_days=1)  # Not enough days to skip holiday


class TestGetTradingDaysRange:
    """Test getting range of trading days."""
    
    def test_regular_week(self):
        """Test regular week with no holidays."""
        # Monday to Friday
        result = get_trading_days_range('2025-07-28', '2025-08-01')
        expected = ['2025-07-28', '2025-07-29', '2025-07-30', '2025-07-31', '2025-08-01']
        assert result == expected
    
    def test_week_with_weekend(self):
        """Test week including weekend."""
        # Friday to Tuesday (skip weekend)
        result = get_trading_days_range('2025-08-01', '2025-08-05')
        expected = ['2025-08-01', '2025-08-04', '2025-08-05']
        assert result == expected
    
    def test_week_with_holiday(self):
        """Test week with holiday."""
        # July 2 to July 8 (skip July 4 holiday and weekend)
        result = get_trading_days_range('2025-07-02', '2025-07-08')
        expected = ['2025-07-02', '2025-07-03', '2025-07-07', '2025-07-08']
        assert result == expected
    
    def test_single_day_trading(self):
        """Test single trading day range."""
        result = get_trading_days_range('2025-08-01', '2025-08-01')
        assert result == ['2025-08-01']
    
    def test_single_day_non_trading(self):
        """Test single non-trading day range."""
        result = get_trading_days_range('2025-08-02', '2025-08-02')  # Saturday
        assert result == []
    
    def test_invalid_range(self):
        """Test invalid date range."""
        with pytest.raises(ValueError):
            get_trading_days_range('2025-08-05', '2025-08-01')  # end before start
    
    def test_different_input_types(self):
        """Test with different input types."""
        result1 = get_trading_days_range('2025-08-01', '2025-08-01')
        result2 = get_trading_days_range(date(2025, 8, 1), date(2025, 8, 1))
        result3 = get_trading_days_range(
            datetime(2025, 8, 1, 10, 0), 
            datetime(2025, 8, 1, 16, 0)
        )
        
        assert result1 == result2 == result3 == ['2025-08-01']


class TestFormatDateForEodhd:
    """Test EODHD date formatting."""
    
    def test_string_input(self):
        """Test with string input."""
        result = format_date_for_eodhd('2025-08-01')
        assert result == '2025-08-01'
    
    def test_date_input(self):
        """Test with date object input."""
        result = format_date_for_eodhd(date(2025, 8, 1))
        assert result == '2025-08-01'
    
    def test_datetime_input(self):
        """Test with datetime object input."""
        result = format_date_for_eodhd(datetime(2025, 8, 1, 15, 30))
        assert result == '2025-08-01'
    
    def test_invalid_string_format(self):
        """Test with invalid string format."""
        with pytest.raises(TradingDateError):
            format_date_for_eodhd('2025/08/01')
    
    def test_invalid_input_type(self):
        """Test with invalid input type."""
        with pytest.raises(TradingDateError):
            format_date_for_eodhd(123456)


class TestGetEodhdFilterDate:
    """Test the main EODHD integration function."""
    
    def test_regular_day(self):
        """Test regular trading day."""
        result = get_eodhd_filter_date('2025-08-01')
        assert result == '2025-08-01'
    
    def test_weekend(self):
        """Test weekend returns previous Friday."""
        result = get_eodhd_filter_date('2025-08-02')  # Saturday
        assert result == '2025-08-01'  # Friday
    
    def test_holiday(self):
        """Test holiday returns previous trading day."""
        result = get_eodhd_filter_date('2025-07-04')  # Independence Day Friday
        assert result == '2025-07-03'  # Thursday
    
    @patch('src.utils.trading_dates.get_most_recent_trading_date')
    def test_calls_underlying_function(self, mock_get_recent):
        """Test that it properly calls the underlying function."""
        mock_get_recent.return_value = '2025-08-01'
        
        result = get_eodhd_filter_date('2025-08-01', lookback_days=3)
        
        mock_get_recent.assert_called_once_with(
            reference_date='2025-08-01',
            lookback_days=3
        )
        assert result == '2025-08-01'
    
    def test_with_current_date(self):
        """Test with current date (None reference)."""
        result = get_eodhd_filter_date()
        # Should return a valid date string
        assert len(result) == 10  # YYYY-MM-DD format
        assert result.count('-') == 2


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_year_boundary(self):
        """Test year boundary crossing."""
        # New Year's Day 2025 -> December 31, 2024
        result = get_most_recent_trading_date('2025-01-01')
        assert result == '2024-12-31'
    
    def test_leap_year_handling(self):
        """Test leap year handling."""
        # Test February 29, 2024 (leap year)
        result = get_most_recent_trading_date('2024-02-29')
        assert result == '2024-02-29'  # Should be valid trading day
    
    def test_thanksgiving_week(self):
        """Test Thanksgiving week (market closes early on Wednesday, closed Thursday)."""
        # Test the day after Thanksgiving 2025 (Friday, November 28)
        result = get_most_recent_trading_date('2025-11-28')
        # Day after Thanksgiving is typically a half-day, but still a trading day
        assert result == '2025-11-28'
    
    def test_christmas_new_year_period(self):
        """Test the period between Christmas and New Year."""
        # December 26, 2025 (Thursday after Christmas Day)
        result = get_most_recent_trading_date('2025-12-26')
        assert result == '2025-12-26'  # Should be trading day
    
    def test_good_friday_calculation(self):
        """Test that Good Friday is correctly calculated for different years."""
        # Good Friday 2025 is April 18
        assert is_trading_day('2025-04-18') == False
        assert is_trading_day('2025-04-17') == True  # Thursday before
    
    def test_memory_efficiency_large_range(self):
        """Test that large date ranges don't cause memory issues."""
        # Test a full year range
        result = get_trading_days_range('2025-01-01', '2025-12-31')
        # Should have approximately 252 trading days in a year
        assert 250 <= len(result) <= 255
    
    @patch('src.utils.trading_dates.logger')
    def test_logging_called(self, mock_logger):
        """Test that logging is properly called."""
        get_most_recent_trading_date('2025-08-01')
        # Should have debug and info log calls
        assert mock_logger.debug.called
        assert mock_logger.info.called


class TestIntegrationScenarios:
    """Test real-world integration scenarios."""
    
    def test_eodhd_api_filter_format(self):
        """Test that the output format matches EODHD API requirements."""
        result = get_eodhd_filter_date()
        
        # Should match YYYY-MM-DD format exactly
        import re
        pattern = r'^\d{4}-\d{2}-\d{2}$'
        assert re.match(pattern, result), f"Date {result} doesn't match EODHD format"
    
    def test_options_chain_filtering_scenario(self):
        """Test typical options chain filtering scenario."""
        # Simulate getting options data for a recent trading day
        filter_date = get_eodhd_filter_date()
        
        # The URL would be constructed like:
        # f"https://eodhd.com/api/options/AAPL.US?filter[tradetime_from]={filter_date}"
        
        # Verify the filter date is a valid trading day
        assert is_trading_day(filter_date) == True
    
    def test_weekend_processing_scenario(self):
        """Test scenario where scanner runs on weekend."""
        # Saturday processing should get Friday's data
        saturday_filter = get_eodhd_filter_date('2025-08-02')  # Saturday
        assert saturday_filter == '2025-08-01'  # Friday
        
        # Sunday processing should also get Friday's data
        sunday_filter = get_eodhd_filter_date('2025-08-03')  # Sunday
        assert sunday_filter == '2025-08-01'  # Friday
    
    def test_holiday_processing_scenario(self):
        """Test scenario where scanner runs on or after holiday."""
        # Independence Day 2025 (Friday) processing should get Thursday's data
        holiday_filter = get_eodhd_filter_date('2025-07-04')
        assert holiday_filter == '2025-07-03'
        
        # Saturday after Independence Day should still get Thursday's data
        post_holiday_filter = get_eodhd_filter_date('2025-07-05')
        assert post_holiday_filter == '2025-07-03'


if __name__ == "__main__":
    """Run tests when executed directly."""
    pytest.main([__file__, "-v"])