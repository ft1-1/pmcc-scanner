# EODHD Options API Reference

This document provides a comprehensive reference for the EODHD Options API, specifically for US stock options data. This API will be used for fetching options chains, contract details, and Greeks for the PMCC Scanner application.

## Overview

The EODHD Options API provides end-of-day options data for 6,000+ actively traded US stock symbols with over 40 data fields per option contract. The API captures over 1.5 million bid/ask/trade events daily and provides 1+ year of historical options data.

## Base Information

- **Base URL**: `https://eodhd.com/api/mp/unicornbay/options`
- **Authentication**: API token required (passed as query parameter)
- **Data Format**: JSON
- **Update Frequency**: End-of-day (EOD) data only

## Authentication

All API requests require an API token to be passed as a query parameter:

```
?api_token=YOUR_API_TOKEN
```

A demo token is available for testing purposes: `demo`

## Main Endpoints

### 1. Options EOD Data

Retrieve end-of-day options data for specific contracts or filtered criteria.

**Endpoint**: `/eod`

**Full URL**: `https://eodhd.com/api/mp/unicornbay/options/eod`

**Method**: GET

**Query Parameters**:
- `api_token` (required): Your API authentication token
- `filter[underlying_symbol]`: Stock ticker symbol (e.g., "AAPL", "MSFT")
- `filter[type]`: Option type - "call" or "put"
- `filter[strike_from]`: Minimum strike price (numeric)
- `filter[strike_to]`: Maximum strike price (numeric)
- `filter[exp_date_from]`: Start expiration date (YYYY-MM-DD format)
- `filter[exp_date_to]`: End expiration date (YYYY-MM-DD format)
- `filter[date_from]`: Start date for historical data (YYYY-MM-DD format)
- `filter[date_to]`: End date for historical data (YYYY-MM-DD format)
- `sort`: Sort order (e.g., "strike_price", "-strike_price", "exp_date", "-exp_date")
- `limit`: Number of results to return
- `offset`: Pagination offset

**Example Request**:
```
GET https://eodhd.com/api/mp/unicornbay/options/eod?api_token=demo&filter[underlying_symbol]=AAPL&filter[type]=call&filter[strike_from]=150&filter[strike_to]=200&filter[exp_date_from]=2024-01-01&filter[exp_date_to]=2024-12-31
```

### 2. Options Contracts

Get available options contracts for a specific underlying symbol.

**Endpoint**: `/contracts`

**Full URL**: `https://eodhd.com/api/mp/unicornbay/options/contracts`

**Method**: GET

**Query Parameters**:
- `api_token` (required): Your API authentication token
- `filter[underlying_symbol]` (required): Stock ticker symbol
- `filter[exp_date_from]`: Filter by minimum expiration date
- `filter[exp_date_to]`: Filter by maximum expiration date
- `filter[type]`: Filter by option type ("call" or "put")

**Example Request**:
```
GET https://eodhd.com/api/mp/unicornbay/options/contracts?api_token=demo&filter[underlying_symbol]=AAPL
```

## Response Data Fields

The API returns comprehensive options data with 40+ fields per contract. Key fields include:

### Contract Information
- `symbol`: Option contract symbol
- `underlying_symbol`: Underlying stock ticker
- `type`: Option type (call/put)
- `strike_price`: Strike price of the option
- `exp_date`: Expiration date
- `contract_size`: Number of shares per contract (typically 100)

### Pricing Data
- `bid`: Current bid price
- `ask`: Current ask price
- `last`: Last traded price
- `close`: Closing price
- `open`: Opening price
- `high`: Day's high price
- `low`: Day's low price
- `volume`: Trading volume
- `open_interest`: Open interest

### Greeks and Risk Metrics
- `delta`: Option delta
- `gamma`: Option gamma
- `theta`: Option theta (time decay)
- `vega`: Option vega (volatility sensitivity)
- `rho`: Option rho (interest rate sensitivity)
- `implied_volatility`: Implied volatility

### Additional Fields
- `date`: Data date
- `time`: Data timestamp
- `bid_size`: Size of bid
- `ask_size`: Size of ask
- `in_the_money`: Boolean indicating if option is ITM
- `theoretical_value`: Theoretical option value
- `intrinsic_value`: Intrinsic value of the option
- `time_value`: Time value of the option

## Query Parameters (Complete List)

### Filtering Parameters

- `filter[contract]` (string): Filter by specific contract name (e.g., "AAPL270115P00450000")
- `filter[underlying_symbol]` (string): Filter by underlying symbol (e.g., "AAPL")
- `filter[exp_date_eq]` (date): Exact expiration date (YYYY-MM-DD)
- `filter[exp_date_from]` (date): Minimum expiration date (YYYY-MM-DD)
- `filter[exp_date_to]` (date): Maximum expiration date (YYYY-MM-DD)
- `filter[tradetime_eq]` (date): Exact trade date (YYYY-MM-DD)
- `filter[tradetime_from]` (date): Minimum trade date (YYYY-MM-DD)
- `filter[tradetime_to]` (date): Maximum trade date (YYYY-MM-DD)
- `filter[type]` (enum): Option type - "put" or "call"
- `filter[strike_eq]` (number): Exact strike price
- `filter[strike_from]` (number): Minimum strike price
- `filter[strike_to]` (number): Maximum strike price

### Sorting Parameters

- `sort` (enum): Sort order
  - "exp_date": Sort by expiration date (ascending)
  - "-exp_date": Sort by expiration date (descending)
  - "strike": Sort by strike price (ascending)
  - "-strike": Sort by strike price (descending)

### Pagination Parameters

- `page[offset]` (integer): Starting point for results (default: 0, max: 10000)
- `page[limit]` (integer): Number of results to return (default and max: 1000)

### Field Selection

- `fields[options-contracts]` (string): Comma-separated list of fields to include (e.g., "contract,exp_date,strike,delta,bid,ask")

## Response Format

### Successful Response
```json
{
  "data": [
    {
      "symbol": "AAPL240119C00150000",
      "underlying_symbol": "AAPL",
      "type": "call",
      "strike_price": 150.00,
      "exp_date": "2024-01-19",
      "bid": 45.20,
      "ask": 45.50,
      "last": 45.35,
      "volume": 1234,
      "open_interest": 5678,
      "delta": 0.85,
      "gamma": 0.002,
      "theta": -0.05,
      "vega": 0.12,
      "implied_volatility": 0.25,
      "date": "2024-01-15",
      // ... additional fields
    }
  ],
  "meta": {
    "total": 100,
    "count": 25,
    "per_page": 25,
    "current_page": 1,
    "total_pages": 4
  }
}
```

### Error Response
```json
{
  "error": {
    "code": "401",
    "message": "Unauthorized. Invalid API token."
  }
}
```

## Rate Limits

- API rate limits are based on your subscription plan
- Demo token has limited requests per day
- Commercial plans offer higher rate limits
- Rate limit headers are included in responses:
  - `X-RateLimit-Limit`: Maximum requests allowed
  - `X-RateLimit-Remaining`: Requests remaining
  - `X-RateLimit-Reset`: Time when limit resets

## Important Notes

1. **Data Coverage**: 
   - Only end-of-day data is available (no intraday)
   - Historical data goes back 1+ years
   - Covers 6,000+ actively traded US stocks

2. **Best Practices**:
   - Use filters to reduce data transfer and processing time
   - Implement pagination for large result sets
   - Cache frequently accessed data to minimize API calls
   - Handle rate limits gracefully with exponential backoff

3. **Limitations**:
   - No real-time or intraday options data
   - Limited to US stock options only
   - Greeks calculations are end-of-day only

4. **Authentication**:
   - Never expose your API token in client-side code
   - Use environment variables for token storage
   - Rotate tokens periodically for security

## Example Usage for PMCC Scanner

### Finding LEAPS Candidates
```python
# Find deep ITM call options with 6-12 months to expiration
params = {
    'api_token': 'YOUR_TOKEN',
    'filter[underlying_symbol]': 'AAPL',
    'filter[type]': 'call',
    'filter[exp_date_from]': '2024-06-01',  # 6 months out
    'filter[exp_date_to]': '2024-12-31',    # 12 months out
    'filter[strike_to]': 150,  # Deep ITM (assuming AAPL at 180)
    'sort': 'delta'  # Sort by delta to find high-delta options
}
```

### Finding Short Call Candidates
```python
# Find OTM call options with 30-45 DTE
params = {
    'api_token': 'YOUR_TOKEN',
    'filter[underlying_symbol]': 'AAPL',
    'filter[type]': 'call',
    'filter[exp_date_from]': '2024-02-01',  # 30 days out
    'filter[exp_date_to]': '2024-02-15',    # 45 days out
    'filter[strike_from]': 185,  # OTM (assuming AAPL at 180)
    'sort': '-volume'  # Sort by volume for liquidity
}
```

## Migration Notes from MarketData.app

When migrating from MarketData.app to EODHD for options data:

1. **Endpoint Changes**: Update all options-related endpoints to use EODHD
2. **Parameter Mapping**: Convert MarketData parameters to EODHD filter syntax
3. **Response Parsing**: Update response parsing to handle EODHD's data structure
4. **Greeks Availability**: EODHD provides Greeks in the same response (no separate call needed)
5. **Historical Data**: EODHD provides up to 1 year of historical options data

## Support and Documentation

- API Specification: `https://eodhd.com/vendor/marketplace/unicornbay/options/spec.yaml`
- Product Page: https://eodhd.com/lp/us-stock-options-api
- Academy Examples: https://eodhd.com/financial-academy/stock-options/us-stock-options-api-usage-examples