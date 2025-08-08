# EODHD Python Library API Reference

## Overview
This is the official Python library developed by EODHD for accessing various financial data via API. The library provides access to comprehensive financial data including stocks, ETFs, mutual funds, and more.

## Installation
```bash
python3 -m pip install eodhd -U
```

## Authentication
All API calls require an API key. You can obtain a free API key by registering at https://eodhd.com.

## Core Classes

### 1. APIClient
Main class for accessing EODHD financial data APIs.

```python
from eodhd import APIClient

# Initialize client
api = APIClient("your_api_key")
```

### 2. ScannerClient  
Specialized class for stock market screening functionality.

```python
from eodhd import ScannerClient

# Initialize scanner
scanner = ScannerClient("your_api_key")
```

### 3. WebSocketClient
For real-time data streaming (advanced usage).

```python
from eodhd import WebSocketClient

# Initialize websocket client
ws_client = WebSocketClient("your_api_key")
```

## APIClient Methods

Based on the official example_api.py, the APIClient class supports the following methods:

### Exchange Data
```python
# Get list of supported exchanges
resp = api.get_exchanges()

# Get symbols for specific exchange
resp = api.get_exchange_symbols("US")  # US exchange symbols

# Trading hours and market holidays
resp = api.get_details_trading_hours_stock_market_holidays(
    code='US', 
    from_date='2022-12-01', 
    to_date='2023-01-03'
)
```

### Historical Data
```python
# End-of-day historical data
resp = api.get_historical_data("AAPL.US", "d")  # Daily data
resp = api.get_historical_data("AAPL.US", "d", "2021-11-24")  # From specific date
resp = api.get_historical_data("AAPL.US", "d", "2021-11-24", "2021-11-27")  # Date range
resp = api.get_historical_data("AAPL.US", "d", results=400)  # Last N results

# Intraday historical data
resp = api.get_intraday_historical_data('AAPL.US', '1m')  # 1 minute intervals
resp = api.get_historical_data("AAPL.US", "5m")  # 5 minute intervals  
resp = api.get_historical_data("AAPL.US", "1h")  # 1 hour intervals
```

### Fundamental Data
```python
# Company fundamentals
resp = api.get_fundamentals_data(ticker='AAPL')

# Bonds fundamentals
resp = api.get_bonds_fundamentals_data(isin='DE000CB83CF0')
```

### Corporate Actions & Events
```python
# Splits and dividends
resp = api.get_eod_splits_dividends_data(
    country='US',
    type='splits',  # or 'dividends'
    date='2010-09-21',
    symbols='MSFT',
    filter='extended'
)

# Earnings trends
resp = api.get_earning_trends_data(symbols='AAPL.US')
# Multiple symbols: symbols='AAPL.US,MSFT.US'
```

### Economic Data
```python
# Economic events
resp = api.get_economic_events_data(
    date_from='2020-01-05',
    date_to='2020-02-10',
    country='AU',
    comparison='mom',  # or 'qoq', 'yoy'
    offset=50,
    limit=50
)
```

### News Data
```python
# Financial news
resp = api.financial_news(
    s='AAPL.US',  # Symbol
    t=None,  # Or specific topic like 'balance sheet'
    from_date='2020-01-05',
    to_date='2020-02-10',
    limit=100,
    offset=200
)
```

## Data Format
All API responses return Python dictionaries parsed from JSON. You can convert to pandas DataFrames:

```python
import pandas as pd

# Get historical data
data = api.get_historical_data("AAPL.US", "d")

# Convert to DataFrame
df = pd.DataFrame(data)
df.set_index('date', inplace=True)

# Plot closing prices
df['close'].plot(figsize=(10,5))
```

## ScannerClient Methods

The ScannerClient class provides stock screening functionality. Refer to `example_scanner.py` in the official repository for complete method list.

**Note:** The exact methods available in ScannerClient should be referenced from the official example_scanner.py file.

## Common Parameters

### Ticker Symbols
- US stocks: `AAPL.US`, `MSFT.US`
- Cryptocurrencies: `BTC-USD.CC`
- Forex: `EUR-USD`
- Other exchanges: Use appropriate exchange suffix

### Date Formats
- Date strings: `"2021-11-24"`
- Datetime strings: `"2021-11-27 23:56:00"`

### Intervals for Historical Data
- `"1m"` - 1 minute
- `"5m"` - 5 minutes  
- `"1h"` - 1 hour
- `"d"` - Daily
- `"w"` - Weekly
- `"m"` - Monthly



## Error Handling

```python
try:
    data = api.get_historical_data("INVALID.SYMBOL", "d")
except Exception as e:
    print(f"API Error: {e}")
```

## Best Practices

1. **Use appropriate ticker formats** with exchange suffixes
2. **Handle API rate limits** - implement retry logic for production use
3. **Cache responses** when possible to minimize API calls  
4. **Validate data completeness** before processing
5. **Use date ranges** to limit data volume when appropriate

## Stock Screening Considerations

**Important:** Based on the search results, stock screening functionality is available through the `ScannerClient` class. However, the exact method signatures should be verified by examining the official `example_scanner.py` file.

For PMCC scanner integration:
- Use `ScannerClient` for stock screening if available
- Implement market cap and volume filters
- Consider fallback to other screening methods if EODHD screening is limited

## Integration Notes for PMCC Scanner

When integrating with the PMCC Scanner:

1. **Provider Method Mapping:** Ensure method names match exactly what's available in APIClient/ScannerClient
2. **Data Structure Validation:** Verify returned data structures match expected formats  
3. **Error Handling:** Implement proper exception handling for API failures
4. **Rate Limiting:** Respect API rate limits to avoid service interruptions

## Reference Links

- **Official Documentation:** https://eodhd.com/financial-apis/python-financial-libraries-and-code-samples/
- **GitHub Repository:** https://github.com/EodHistoricalData/EODHD-APIs-Python-Financial-Library
- **PyPI Package:** https://pypi.org/project/eodhd/
- **Example Files:** 
  - example_api.py (APIClient methods)
  - example_scanner.py (ScannerClient methods)  
  - example_websockets.py (WebSocketClient methods)

## Version Information

- **Package Name:** `eodhd`
- **Latest Version:** 1.0.32+ (check PyPI for current version)
- **Python Requirements:** Python 3.8+

---

*Note: This reference is based on available documentation and example files. For the most current and complete method list, always refer to the official example files in the GitHub repository.*