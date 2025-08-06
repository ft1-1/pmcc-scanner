"""
Trading Date Utilities for PMCC Scanner.

This module provides utilities for determining valid US stock market trading dates,
handling weekends and holidays. Critical for filtering EODHD API calls to only
get recent options data.

Key Features:
- US stock market holiday calendar
- Weekend exclusion (Saturday/Sunday)
- Configurable lookback periods
- Robust error handling
- Test-friendly date override capability
"""

import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Union
import pytz

import pandas as pd
from pandas.tseries.holiday import Holiday, USFederalHolidayCalendar, Easter
from pandas.tseries.offsets import Day, BDay

from .logger import get_logger


# Initialize logger
logger = get_logger("trading_dates")


class USStockMarketCalendar(USFederalHolidayCalendar):
    """
    US Stock Market Holiday Calendar.
    
    Extends pandas USFederalHolidayCalendar to include stock market specific holidays
    and exclude federal holidays that don't close the stock market.
    """
    
    def __init__(self):
        # Get base federal holidays
        super().__init__()
        
        # Stock market specific holidays (remove Columbus Day and Veterans Day)
        # These are the holidays when US stock markets are closed
        self.rules = [
            Holiday('New Year\'s Day', month=1, day=1, observance=self._nearest_workday),
            Holiday('Martin Luther King Jr. Day', month=1, day=1, offset=[pd.DateOffset(weekday=0), Day(14)]),
            Holiday('Presidents Day', month=2, day=1, offset=[pd.DateOffset(weekday=0), Day(14)]),
            Holiday('Good Friday', month=1, day=1, offset=[Easter(), Day(-2)]),
            Holiday('Memorial Day', month=5, day=31, offset=pd.DateOffset(weekday=0)),
            Holiday('Juneteenth', month=6, day=19, observance=self._nearest_workday, start_date='2021-06-19'),
            Holiday('Independence Day', month=7, day=4, observance=self._nearest_workday),
            Holiday('Labor Day', month=9, day=1, offset=pd.DateOffset(weekday=0)),
            Holiday('Thanksgiving', month=11, day=1, offset=[pd.DateOffset(weekday=3), Day(21)]),
            Holiday('Christmas Day', month=12, day=25, observance=self._nearest_workday),
        ]
    
    @staticmethod
    def _nearest_workday(dt):
        """
        Move holiday to nearest workday if it falls on weekend.
        Saturday -> Friday, Sunday -> Monday
        """
        if dt.weekday() == 5:  # Saturday
            return dt - pd.Timedelta(days=1)
        elif dt.weekday() == 6:  # Sunday
            return dt + pd.Timedelta(days=1)
        return dt


class TradingDateError(Exception):
    """Custom exception for trading date operations."""
    pass


def get_most_recent_trading_date(
    reference_date: Optional[Union[str, date, datetime]] = None,
    lookback_days: int = 5,
    market_timezone: str = "US/Eastern"
) -> str:
    """
    Get the most recent trading date in YYYY-MM-DD format.
    
    This function is critical for filtering EODHD options API calls to only get
    recent data using the filter[tradetime_from] parameter.
    
    Args:
        reference_date: Reference date to work backwards from. If None, uses current date.
                       Can be string (YYYY-MM-DD), date, or datetime object.
        lookback_days: Maximum number of business days to look back (default: 5).
                      This handles extended market closures like long weekends.
        market_timezone: Market timezone (default: US/Eastern)
    
    Returns:
        Most recent trading date as YYYY-MM-DD string
    
    Raises:
        TradingDateError: If no trading date found within lookback period
        ValueError: If reference_date format is invalid
    
    Examples:
        >>> get_most_recent_trading_date()  # Current trading date
        '2025-08-01'
        
        >>> get_most_recent_trading_date('2025-07-04')  # July 4th is holiday
        '2025-07-03'
        
        >>> get_most_recent_trading_date('2025-07-07')  # Sunday
        '2025-07-05'  # Previous Friday
    """
    
    try:
        # Parse reference date
        if reference_date is None:
            # Use current date in market timezone
            market_tz = pytz.timezone(market_timezone)
            ref_date = datetime.now(market_tz).date()
        elif isinstance(reference_date, str):
            ref_date = datetime.strptime(reference_date, "%Y-%m-%d").date()
        elif isinstance(reference_date, datetime):
            ref_date = reference_date.date()
        elif isinstance(reference_date, date):
            ref_date = reference_date
        else:
            raise ValueError(f"Invalid reference_date type: {type(reference_date)}")
        
        logger.debug(
            "Finding most recent trading date",
            extra={
                "reference_date": ref_date.isoformat(),
                "lookback_days": lookback_days,
                "market_timezone": market_timezone
            }
        )
        
        # Create market calendar
        market_calendar = USStockMarketCalendar()
        
        # Check each day working backwards
        current_date = ref_date
        days_checked = 0
        
        while days_checked <= lookback_days:
            # Skip weekends
            if current_date.weekday() < 5:  # Monday=0, Friday=4
                # Check if it's a market holiday
                holidays = market_calendar.holidays(
                    start=current_date,
                    end=current_date,
                    return_name=True
                )
                
                if len(holidays) == 0:  # Not a holiday
                    trading_date = current_date.isoformat()
                    
                    logger.info(
                        "Found most recent trading date",
                        extra={
                            "trading_date": trading_date,
                            "days_back": days_checked,
                            "reference_date": ref_date.isoformat()
                        }
                    )
                    
                    return trading_date
                else:
                    # It's a holiday
                    holiday_name = holidays.iloc[0]
                    logger.debug(
                        "Skipping market holiday",
                        extra={
                            "date": current_date.isoformat(),
                            "holiday": holiday_name
                        }
                    )
            else:
                # It's a weekend
                logger.debug(
                    "Skipping weekend",
                    extra={
                        "date": current_date.isoformat(),
                        "weekday": current_date.strftime("%A")
                    }
                )
            
            # Move to previous day
            current_date -= timedelta(days=1)
            days_checked += 1
        
        # If we get here, no trading date found within lookback period
        error_msg = (
            f"No trading date found within {lookback_days} days of {ref_date.isoformat()}. "
            "This may indicate an extended market closure or configuration issue."
        )
        
        logger.error(
            "No recent trading date found",
            extra={
                "reference_date": ref_date.isoformat(),
                "lookback_days": lookback_days,
                "days_checked": days_checked
            }
        )
        
        raise TradingDateError(error_msg)
        
    except Exception as e:
        if isinstance(e, (TradingDateError, ValueError)):
            raise
        
        logger.exception(
            "Unexpected error in get_most_recent_trading_date",
            extra={
                "reference_date": str(reference_date),
                "lookback_days": lookback_days,
                "error_type": type(e).__name__
            }
        )
        
        raise TradingDateError(f"Failed to determine trading date: {str(e)}") from e


def is_trading_day(check_date: Union[str, date, datetime]) -> bool:
    """
    Check if a given date is a valid trading day.
    
    Args:
        check_date: Date to check. Can be string (YYYY-MM-DD), date, or datetime object.
    
    Returns:
        True if the date is a trading day, False otherwise
    
    Examples:
        >>> is_trading_day('2025-08-01')  # Friday
        True
        
        >>> is_trading_day('2025-08-02')  # Saturday
        False
        
        >>> is_trading_day('2025-07-04')  # Independence Day
        False
    """
    
    try:
        # Parse date
        if isinstance(check_date, str):
            date_obj = datetime.strptime(check_date, "%Y-%m-%d").date()
        elif isinstance(check_date, datetime):
            date_obj = check_date.date()
        elif isinstance(check_date, date):
            date_obj = check_date
        else:
            raise ValueError(f"Invalid check_date type: {type(check_date)}")
        
        # Check if weekend
        if date_obj.weekday() >= 5:  # Saturday=5, Sunday=6
            return False
        
        # Check if holiday
        market_calendar = USStockMarketCalendar()
        holidays = market_calendar.holidays(
            start=date_obj,
            end=date_obj
        )
        
        is_trading = len(holidays) == 0
        
        logger.debug(
            "Trading day check",
            extra={
                "date": date_obj.isoformat(),
                "is_trading_day": is_trading,
                "weekday": date_obj.strftime("%A")
            }
        )
        
        return is_trading
        
    except Exception as e:
        logger.exception(
            "Error checking if trading day",
            extra={
                "check_date": str(check_date),
                "error_type": type(e).__name__
            }
        )
        raise TradingDateError(f"Failed to check trading day: {str(e)}") from e


def get_next_trading_date(
    reference_date: Optional[Union[str, date, datetime]] = None,
    forward_days: int = 10
) -> str:
    """
    Get the next trading date after the reference date.
    
    Args:
        reference_date: Reference date to work forwards from. If None, uses current date.
        forward_days: Maximum number of days to look forward (default: 10)
    
    Returns:
        Next trading date as YYYY-MM-DD string
    
    Raises:
        TradingDateError: If no trading date found within forward period
    """
    
    try:
        # Parse reference date
        if reference_date is None:
            ref_date = datetime.now().date()
        elif isinstance(reference_date, str):
            ref_date = datetime.strptime(reference_date, "%Y-%m-%d").date()
        elif isinstance(reference_date, datetime):
            ref_date = reference_date.date()
        elif isinstance(reference_date, date):
            ref_date = reference_date
        else:
            raise ValueError(f"Invalid reference_date type: {type(reference_date)}")
        
        # Start from the day after reference date
        current_date = ref_date + timedelta(days=1)
        days_checked = 0
        
        while days_checked <= forward_days:
            if is_trading_day(current_date):
                trading_date = current_date.isoformat()
                
                logger.info(
                    "Found next trading date",
                    extra={
                        "next_trading_date": trading_date,
                        "days_forward": days_checked + 1,
                        "reference_date": ref_date.isoformat()
                    }
                )
                
                return trading_date
            
            current_date += timedelta(days=1)
            days_checked += 1
        
        error_msg = f"No trading date found within {forward_days} days of {ref_date.isoformat()}"
        logger.error(
            "No next trading date found",
            extra={
                "reference_date": ref_date.isoformat(),
                "forward_days": forward_days
            }
        )
        
        raise TradingDateError(error_msg)
        
    except Exception as e:
        if isinstance(e, (TradingDateError, ValueError)):
            raise
        
        logger.exception(
            "Error finding next trading date",
            extra={
                "reference_date": str(reference_date),
                "forward_days": forward_days,
                "error_type": type(e).__name__
            }
        )
        
        raise TradingDateError(f"Failed to find next trading date: {str(e)}") from e


def get_trading_days_range(
    start_date: Union[str, date, datetime],
    end_date: Union[str, date, datetime]
) -> List[str]:
    """
    Get all trading days between start_date and end_date (inclusive).
    
    Args:
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
    
    Returns:
        List of trading dates as YYYY-MM-DD strings
    
    Examples:
        >>> get_trading_days_range('2025-08-01', '2025-08-08')
        ['2025-08-01', '2025-08-04', '2025-08-05', '2025-08-06', '2025-08-07', '2025-08-08']
    """
    
    try:
        # Parse dates
        if isinstance(start_date, str):
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
        elif isinstance(start_date, datetime):
            start = start_date.date()
        elif isinstance(start_date, date):
            start = start_date
        else:
            raise ValueError(f"Invalid start_date type: {type(start_date)}")
        
        if isinstance(end_date, str):
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        elif isinstance(end_date, datetime):
            end = end_date.date()
        elif isinstance(end_date, date):
            end = end_date
        else:
            raise ValueError(f"Invalid end_date type: {type(end_date)}")
        
        if start > end:
            raise ValueError("start_date must be <= end_date")
        
        # Generate trading days
        trading_days = []
        current_date = start
        
        while current_date <= end:
            if is_trading_day(current_date):
                trading_days.append(current_date.isoformat())
            current_date += timedelta(days=1)
        
        logger.info(
            "Generated trading days range",
            extra={
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "trading_days_count": len(trading_days)
            }
        )
        
        return trading_days
        
    except Exception as e:
        if isinstance(e, ValueError):
            raise
        
        logger.exception(
            "Error generating trading days range",
            extra={
                "start_date": str(start_date),
                "end_date": str(end_date),
                "error_type": type(e).__name__
            }
        )
        
        raise TradingDateError(f"Failed to generate trading days range: {str(e)}") from e


def format_date_for_eodhd(trading_date: Union[str, date, datetime]) -> str:
    """
    Format a trading date for use with EODHD API filter parameters.
    
    EODHD API expects dates in YYYY-MM-DD format for filter[tradetime_from] parameter.
    
    Args:
        trading_date: Trading date to format
    
    Returns:
        Date formatted as YYYY-MM-DD string for EODHD API
    
    Examples:
        >>> format_date_for_eodhd(date(2025, 8, 1))
        '2025-08-01'
        
        >>> format_date_for_eodhd('2025-08-01')
        '2025-08-01'
    """
    
    try:
        if isinstance(trading_date, str):
            # Validate and reformat if needed
            parsed = datetime.strptime(trading_date, "%Y-%m-%d").date()
            return parsed.isoformat()
        elif isinstance(trading_date, datetime):
            return trading_date.date().isoformat()
        elif isinstance(trading_date, date):
            return trading_date.isoformat()
        else:
            raise ValueError(f"Invalid trading_date type: {type(trading_date)}")
            
    except Exception as e:
        logger.exception(
            "Error formatting date for EODHD",
            extra={
                "trading_date": str(trading_date),
                "error_type": type(e).__name__
            }
        )
        
        raise TradingDateError(f"Failed to format date for EODHD: {str(e)}") from e


# Convenience function for the most common use case
def get_eodhd_filter_date(
    reference_date: Optional[Union[str, date, datetime]] = None,
    lookback_days: int = 5
) -> str:
    """
    Get the most recent trading date formatted for EODHD API filter parameter.
    
    This is the primary function used by the PMCC scanner to filter options data
    to only the most recent trading day.
    
    Args:
        reference_date: Reference date (if None, uses current date)
        lookback_days: Maximum days to look back for trading date
    
    Returns:
        Most recent trading date formatted for EODHD filter[tradetime_from] parameter
    
    Examples:
        >>> get_eodhd_filter_date()  # Gets most recent trading date
        '2025-08-01'
        
        # Usage in EODHD API call:
        # url = f"https://eodhd.com/api/options/{symbol}?filter[tradetime_from]={get_eodhd_filter_date()}"
    """
    
    trading_date = get_most_recent_trading_date(
        reference_date=reference_date,
        lookback_days=lookback_days
    )
    
    return format_date_for_eodhd(trading_date)


if __name__ == "__main__":
    """CLI for testing trading date utilities."""
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description="Trading Date Utilities")
    parser.add_argument("--test", action="store_true", help="Run comprehensive tests")
    parser.add_argument("--date", help="Check specific date (YYYY-MM-DD)")
    parser.add_argument("--recent", action="store_true", help="Get most recent trading date")
    parser.add_argument("--next", help="Get next trading date after specified date")
    parser.add_argument("--range", nargs=2, help="Get trading days in range (start end)")
    parser.add_argument("--eodhd", action="store_true", help="Get EODHD filter date")
    
    args = parser.parse_args()
    
    # Setup simple logging for CLI
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    try:
        if args.test:
            print("Running trading date utility tests...")
            
            # Test current date
            current_trading = get_most_recent_trading_date()
            print(f"Most recent trading date: {current_trading}")
            
            # Test specific dates
            test_dates = [
                "2025-07-04",  # Independence Day
                "2025-07-05",  # Saturday
                "2025-07-06",  # Sunday
                "2025-08-01",  # Regular Friday
            ]
            
            for test_date in test_dates:
                is_trading = is_trading_day(test_date)
                recent = get_most_recent_trading_date(test_date)
                print(f"{test_date}: Trading day={is_trading}, Recent trading date={recent}")
            
            # Test EODHD format
            eodhd_date = get_eodhd_filter_date()
            print(f"EODHD filter date: {eodhd_date}")
            
            print("Tests completed successfully!")
        
        elif args.date:
            is_trading = is_trading_day(args.date)
            recent = get_most_recent_trading_date(args.date)
            print(f"Date: {args.date}")
            print(f"Is trading day: {is_trading}")
            print(f"Most recent trading date: {recent}")
        
        elif args.recent:
            trading_date = get_most_recent_trading_date()
            print(f"Most recent trading date: {trading_date}")
        
        elif args.next:
            next_trading = get_next_trading_date(args.next)
            print(f"Next trading date after {args.next}: {next_trading}")
        
        elif args.range:
            start, end = args.range
            trading_days = get_trading_days_range(start, end)
            print(f"Trading days from {start} to {end}:")
            for day in trading_days:
                print(f"  {day}")
        
        elif args.eodhd:
            eodhd_date = get_eodhd_filter_date()
            print(f"EODHD filter date: {eodhd_date}")
            print(f"Usage: filter[tradetime_from]={eodhd_date}")
        
        else:
            parser.print_help()
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)