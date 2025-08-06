# Trading Dates Utility Integration

This document explains how to integrate the new trading dates utility with the PMCC scanner to filter EODHD options API calls for only recent data.

## Overview

The trading dates utility (`src/utils/trading_dates.py`) provides robust functionality to:

- Determine the most recent trading date (excluding weekends and US market holidays)
- Filter EODHD options API calls to get only fresh data
- Handle edge cases like extended market closures
- Provide production-ready logging and error handling

## Key Functions

### Primary Function for PMCC Scanner

```python
from src.utils.trading_dates import get_eodhd_filter_date

# Get the most recent trading date formatted for EODHD API
filter_date = get_eodhd_filter_date()
# Returns: "2025-08-01" (YYYY-MM-DD format)

# Use in EODHD options API call
url = f"https://eodhd.com/api/options/{symbol}.US?filter[tradetime_from]={filter_date}&api_token={api_token}"
```

### Supporting Functions

```python
from src.utils.trading_dates import (
    get_most_recent_trading_date,
    is_trading_day,
    get_next_trading_date,
    get_trading_days_range
)

# Check if a specific date is a trading day
is_trading_day('2025-08-01')  # True
is_trading_day('2025-08-02')  # False (Saturday)
is_trading_day('2025-07-04')  # False (Independence Day)

# Get most recent trading date from any reference date
get_most_recent_trading_date('2025-08-02')  # Returns '2025-08-01'
get_most_recent_trading_date()  # Uses current date as reference

# Get next trading date
get_next_trading_date('2025-08-01')  # Returns '2025-08-04' (Monday)

# Get all trading days in a range
get_trading_days_range('2025-08-01', '2025-08-08')
# Returns: ['2025-08-01', '2025-08-04', '2025-08-05', '2025-08-06', '2025-08-07', '2025-08-08']
```

## Integration Points

### 1. Options Data Fetching

**Current Issue**: EODHD options API returns historical data that may include stale weekend/holiday data.

**Solution**: Add trading date filter to all options API calls.

```python
# Before (gets all historical data)
url = f"https://eodhd.com/api/options/{symbol}.US?api_token={api_token}"

# After (gets only recent trading day data)
from src.utils.trading_dates import get_eodhd_filter_date
filter_date = get_eodhd_filter_date()
url = f"https://eodhd.com/api/options/{symbol}.US?filter[tradetime_from]={filter_date}&api_token={api_token}"
```

### 2. EODHD Client Integration

Modify `src/api/eodhd_client.py` to automatically include trading date filters:

```python
class EodhdClient:
    def __init__(self):
        self.trading_date_filter = get_eodhd_filter_date()
    
    def get_options_chain(self, symbol: str, **kwargs):
        # Automatically add trading date filter
        params = {
            'filter[tradetime_from]': self.trading_date_filter,
            'api_token': self.api_token,
            **kwargs
        }
        # ... rest of implementation
```

### 3. Daily Scanner Workflow

The daily scanner should refresh the trading date at the start of each run:

```python
def run_daily_scan():
    # Get current trading date filter
    trading_date = get_eodhd_filter_date()
    logger.info(f"Using trading date filter: {trading_date}")
    
    # Pass to all components that fetch options data
    scanner = PmccScanner(trading_date_filter=trading_date)
    results = scanner.scan()
```

### 4. Error Handling

The utility includes comprehensive error handling:

```python
from src.utils.trading_dates import TradingDateError

try:
    filter_date = get_eodhd_filter_date()
except TradingDateError as e:
    logger.error(f"Could not determine trading date: {e}")
    # Fallback logic or exit gracefully
```

## Holiday Calendar

The utility includes all US stock market holidays:

- New Year's Day (observed on weekday if falls on weekend)
- Martin Luther King Jr. Day (3rd Monday in January)
- Presidents Day (3rd Monday in February)
- Good Friday (varies yearly, calculated from Easter)
- Memorial Day (last Monday in May)
- Juneteenth (June 19, observed on weekday if weekend)
- Independence Day (July 4, observed on weekday if weekend)
- Labor Day (1st Monday in September)
- Thanksgiving (4th Thursday in November)
- Christmas Day (December 25, observed on weekday if weekend)

## Configuration

The utility supports several configuration options:

```python
# Custom lookback period (default: 5 business days)
get_most_recent_trading_date(lookback_days=10)

# Custom market timezone (default: US/Eastern)
get_most_recent_trading_date(market_timezone="US/Central")

# Test with specific reference date
get_most_recent_trading_date(reference_date="2025-07-04")
```

## Logging Integration

The utility integrates with the existing PMCC scanner logging system:

```python
# Automatic logging of trading date decisions
2025-08-03 20:01:41 - pmcc_scanner.trading_dates - INFO - Found most recent trading date
2025-08-03 20:01:41 - pmcc_scanner.trading_dates - DEBUG - Skipping weekend
2025-08-03 20:01:41 - pmcc_scanner.trading_dates - DEBUG - Skipping market holiday
```

## Testing

Comprehensive test suite included:

```bash
# Run trading date tests
python3 -m pytest tests/unit/utils/test_trading_dates.py -v

# Run demonstration
python3 examples/trading_dates_demo.py

# CLI testing
python3 -m src.utils.trading_dates --test
python3 -m src.utils.trading_dates --eodhd
```

## Migration Guide

### Step 1: Update EODHD Client

Add trading date filter to options API calls in `src/api/eodhd_client.py`.

### Step 2: Update Options Analyzer

Modify `src/analysis/options_analyzer.py` to use filtered data.

### Step 3: Update Scanner

Update `src/analysis/scanner.py` to initialize with trading date filter.

### Step 4: Test Integration

Run existing tests to ensure no regression:

```bash
python3 -m pytest tests/integration/test_pmcc_workflow.py
```

### Step 5: Update Documentation

Update API documentation to reflect the new filtering behavior.

## Benefits

1. **Data Freshness**: Only gets most recent trading day's options data
2. **Accuracy**: Eliminates stale weekend/holiday data that could skew analysis
3. **Reliability**: Robust holiday calendar handles all market closures
4. **Performance**: Reduces data volume by filtering out historical data
5. **Maintainability**: Centralized date logic with comprehensive logging

## Example Usage in PMCC Scanner

```python
# In src/analysis/scanner.py
from src.utils.trading_dates import get_eodhd_filter_date

class PmccScanner:
    def __init__(self):
        self.trading_date_filter = get_eodhd_filter_date()
        self.logger.info(f"Initialized with trading date filter: {self.trading_date_filter}")
    
    def analyze_symbol(self, symbol: str):
        # Get options data with trading date filter
        options_data = self.eodhd_client.get_options_chain(
            symbol, 
            filter_tradetime_from=self.trading_date_filter
        )
        
        # Analysis logic continues with fresh data only
        return self.analyze_pmcc_opportunities(options_data)
```

This integration ensures the PMCC scanner only analyzes the most recent, relevant options data while handling all edge cases robustly.