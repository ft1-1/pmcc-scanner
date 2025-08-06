#!/usr/bin/env python3
"""
Trading Dates Utility Demo

This demonstrates how to use the trading date utilities in the PMCC scanner,
particularly for filtering EODHD options API calls to get only recent data.
"""

import sys
import os
from datetime import datetime, date

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.utils.trading_dates import (
    get_most_recent_trading_date,
    is_trading_day,
    get_next_trading_date,
    get_trading_days_range,
    get_eodhd_filter_date,
    format_date_for_eodhd
)
from src.utils.logger import setup_logging

def demonstrate_basic_functionality():
    """Demonstrate basic trading date functionality."""
    print("=== Basic Trading Date Functionality ===")
    
    # Current most recent trading date
    current_trading_date = get_most_recent_trading_date()
    print(f"Current most recent trading date: {current_trading_date}")
    
    # Check if specific dates are trading days
    test_dates = [
        "2025-08-01",  # Friday
        "2025-08-02",  # Saturday
        "2025-08-03",  # Sunday
        "2025-07-04",  # Independence Day 2025 (Friday)
        "2025-12-25",  # Christmas 2025 (Thursday)
    ]
    
    print("\nTrading day checks:")
    for test_date in test_dates:
        is_trading = is_trading_day(test_date)
        weekday = datetime.strptime(test_date, "%Y-%m-%d").strftime("%A")
        print(f"  {test_date} ({weekday}): {'✅ Trading day' if is_trading else '❌ Not trading day'}")
    
    print()


def demonstrate_weekend_holiday_handling():
    """Demonstrate weekend and holiday handling."""
    print("=== Weekend and Holiday Handling ===")
    
    # Weekend scenarios
    weekend_scenarios = [
        ("2025-08-02", "Saturday"),
        ("2025-08-03", "Sunday"),
    ]
    
    print("Weekend handling:")
    for test_date, day_name in weekend_scenarios:
        recent_trading = get_most_recent_trading_date(test_date)
        print(f"  {test_date} ({day_name}) -> Most recent trading: {recent_trading}")
    
    # Holiday scenarios
    holiday_scenarios = [
        ("2025-07-04", "Independence Day (Friday)"),
        ("2025-01-01", "New Year's Day"),
        ("2025-12-25", "Christmas Day"),
    ]
    
    print("\nHoliday handling:")
    for test_date, holiday_name in holiday_scenarios:
        recent_trading = get_most_recent_trading_date(test_date)
        print(f"  {test_date} ({holiday_name}) -> Most recent trading: {recent_trading}")
    
    print()


def demonstrate_eodhd_integration():
    """Demonstrate EODHD API integration."""
    print("=== EODHD API Integration ===")
    
    # Current EODHD filter date
    filter_date = get_eodhd_filter_date()
    print(f"Current EODHD filter date: {filter_date}")
    
    # Example API URLs
    example_symbols = ["AAPL", "TSLA", "MSFT"]
    
    print("\nExample EODHD Options API URLs with filter:")
    for symbol in example_symbols:
        url = f"https://eodhd.com/api/options/{symbol}.US?filter[tradetime_from]={filter_date}&api_token=YOUR_TOKEN"
        print(f"  {symbol}: {url}")
    
    # Test different scenarios
    scenarios = [
        ("2025-08-01", "Regular Friday"),
        ("2025-08-02", "Saturday -> Previous Friday"),
        ("2025-08-03", "Sunday -> Previous Friday"),
        ("2025-07-04", "Independence Day -> Previous trading day"),
    ]
    
    print("\nFilter dates for different scenarios:")
    for test_date, description in scenarios:
        filter_date = get_eodhd_filter_date(test_date)
        print(f"  {test_date} ({description}): filter[tradetime_from]={filter_date}")
    
    print()


def demonstrate_trading_ranges():
    """Demonstrate trading day ranges."""
    print("=== Trading Day Ranges ===")
    
    # Get trading days for a week
    week_range = get_trading_days_range("2025-07-28", "2025-08-03")
    print("Trading days from 2025-07-28 to 2025-08-03 (Monday to Sunday):")
    for day in week_range:
        weekday = datetime.strptime(day, "%Y-%m-%d").strftime("%A")
        print(f"  {day} ({weekday})")
    
    # Get trading days around Independence Day
    holiday_range = get_trading_days_range("2025-07-01", "2025-07-07")
    print(f"\nTrading days around Independence Day (2025-07-01 to 2025-07-07):")
    for day in holiday_range:
        weekday = datetime.strptime(day, "%Y-%m-%d").strftime("%A")
        is_july_4 = day == "2025-07-04"
        note = " (Independence Day - Holiday)" if is_july_4 else ""
        print(f"  {day} ({weekday}){note}")
    
    print()


def demonstrate_next_trading_date():
    """Demonstrate getting next trading date."""
    print("=== Next Trading Date ===")
    
    scenarios = [
        ("2025-07-31", "Thursday -> Friday"),
        ("2025-08-01", "Friday -> Monday (skip weekend)"),
        ("2025-07-03", "Thursday before July 4th -> Monday after holiday"),
    ]
    
    for test_date, description in scenarios:
        next_trading = get_next_trading_date(test_date)
        print(f"  {test_date} ({description}): {next_trading}")
    
    print()


def demonstrate_pmcc_scanner_integration():
    """Demonstrate how this integrates with PMCC scanner workflow."""
    print("=== PMCC Scanner Integration Example ===")
    
    # Simulate the PMCC scanner workflow
    print("Simulated PMCC Scanner daily workflow:")
    
    # Step 1: Get the most recent trading date for options data
    trading_date = get_eodhd_filter_date()
    print(f"1. Most recent trading date for options data: {trading_date}")
    
    # Step 2: Construct EODHD API calls
    print("2. Constructing EODHD API calls:")
    
    # Example stocks from screening
    screened_stocks = ["AAPL", "TSLA", "NVDA", "AMD", "RIOT"]
    
    for stock in screened_stocks:
        # Options chain API with trading date filter
        options_url = f"https://eodhd.com/api/options/{stock}.US"
        options_params = {
            "filter[tradetime_from]": trading_date,
            "api_token": "YOUR_API_TOKEN"
        }
        
        print(f"   {stock} options: {options_url}?filter[tradetime_from]={trading_date}")
    
    # Step 3: Verify we're getting recent data
    print(f"3. Data freshness check:")
    print(f"   Filtering for options data from: {trading_date}")
    print(f"   This ensures we only get the most recent trading day's data")
    print(f"   Excludes stale weekend/holiday data that could skew analysis")
    
    # Step 4: Show what dates would be excluded
    if not is_trading_day(datetime.now().strftime("%Y-%m-%d")):
        current_date = datetime.now().strftime("%Y-%m-%d")
        print(f"4. Current date ({current_date}) is not a trading day")
        print(f"   Scanner will use {trading_date} data instead of stale current date data")
    else:
        print(f"4. Current date is a trading day - using fresh data")
    
    print()


def main():
    """Run all demonstrations."""
    print("Trading Date Utilities Demonstration")
    print("=" * 50)
    print()
    
    # Setup logging
    setup_logging()
    
    try:
        demonstrate_basic_functionality()
        demonstrate_weekend_holiday_handling()
        demonstrate_eodhd_integration()
        demonstrate_trading_ranges()
        demonstrate_next_trading_date()
        demonstrate_pmcc_scanner_integration()
        
        print("🎉 All demonstrations completed successfully!")
        print()
        print("Key Benefits for PMCC Scanner:")
        print("✅ Accurate market holiday handling")
        print("✅ Weekend date exclusion")
        print("✅ EODHD API filter integration")
        print("✅ Robust error handling")
        print("✅ Production-ready logging")
        print("✅ Comprehensive test coverage")
        
    except Exception as e:
        print(f"❌ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())