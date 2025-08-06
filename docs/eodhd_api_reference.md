# EODHD API Reference

## Overview

EODHD (End of Day Historical Data) provides financial market data APIs including stock screening, historical data, and options data. This reference covers the APIs used by the PMCC Scanner application.

## Base URL
```
https://eodhd.com/api
```

## Authentication

EODHD uses API token authentication. The token must be included as a query parameter in all requests.

```
?api_token=YOUR_API_TOKEN
```

## Rate Limiting

- Each Screener API request consumes **5 API credits**
- Rate limits depend on your subscription plan
- The API returns 429 status code when rate limited
- Retry-After header indicates when to retry

## Endpoints

### 1. Stock Screener API

Screen stocks based on various financial criteria.

**Endpoint:** `/screener`

**Method:** `GET`

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| api_token | string | Yes | Your API authentication token |
| filters | string | No | JSON array of filter conditions |
| signals | string | No | Comma-separated list of signals |
| sort | string | No | Field and direction for sorting (e.g., `market_capitalization.desc`) |
| limit | number | No | Number of results (1-100, default: 50) |
| offset | number | No | Result offset for pagination (0-999, default: 0) |

**Filter Format:**
```json
[["field", "operation", value], ["field2", "operation2", value2]]
```

**Available Filter Fields:**

| Field | Type | Description |
|-------|------|-------------|
| code | String | Ticker symbol |
| name | String | Company name |
| exchange | String | Exchange code (e.g., "us", "NYSE", "NASDAQ") |
| sector | String | Company sector |
| industry | String | Company industry |
| market_capitalization | Number | Market cap in USD |
| earnings_share | Number | Earnings per share (EPS) |
| dividend_yield | Number | Dividend yield percentage |
| refund_1d_p | Number | 1-day gain/loss percentage |
| refund_5d_p | Number | 5-day gain/loss percentage |
| avgvol_1d | Number | 1-day volume |
| avgvol_200d | Number | 200-day average volume |
| adjusted_close | Number | Latest adjusted close price |

**Operations:**

- **String Operations:** `=`, `match` (supports wildcards with *)
- **Numeric Operations:** `=`, `>`, `<`, `>=`, `<=`

**Available Signals:**

| Signal | Description |
|--------|-------------|
| 200d_new_lo | New 200-day lows |
| 200d_new_hi | New 200-day highs |
| bookvalue_neg | Negative book value |
| bookvalue_pos | Positive book value |
| wallstreet_lo | Price below analyst expectations |
| wallstreet_hi | Price above analyst expectations |

**Example Request:**
```
GET https://eodhd.com/api/screener?api_token=YOUR_TOKEN&filters=[["market_capitalization",">",1000000000],["exchange","=","us"]]&sort=market_capitalization.desc&limit=50
```

**Response Format:**
```json
{
  "data": [
    {
      "code": "AAPL",
      "name": "Apple Inc.",
      "exchange": "US",
      "sector": "Technology",
      "industry": "Consumer Electronics",
      "market_capitalization": 2800000000000,
      "earnings_share": 5.89,
      "dividend_yield": 0.5,
      "adjusted_close": 175.43,
      "avgvol_200d": 65000000
    }
  ],
  "count": 50,
  "total": 523
}
```

### 2. Options Data API (Referenced but not documented)

Based on the codebase references, EODHD also provides options data through their marketplace:

**Endpoint:** `/marketplace/unicornbay/options`

**Features:**
- 6000+ US Stock Options End-of-Day Data
- 40+ data fields per option contract
- Requires commercial plan subscription

**Note:** Full options API documentation requires EODHD account access or contacting support@eodhistoricaldata.com

## Error Handling

| Status Code | Description |
|-------------|-------------|
| 200 | Success |
| 401 | Authentication failed - invalid or missing API token |
| 402 | Payment required - plan limit exceeded |
| 429 | Rate limit exceeded |
| 500 | Server error |

**Error Response Format:**
```json
{
  "error": "Error message",
  "message": "Detailed error description",
  "details": "Additional error context"
}
```

## Usage Examples

### 1. Screen Large-Cap US Stocks
```bash
curl "https://eodhd.com/api/screener?api_token=YOUR_TOKEN&filters=[[\"market_capitalization\",\">\",10000000000],[\"exchange\",\"=\",\"us\"]]&sort=market_capitalization.desc&limit=20"
```

### 2. Find Technology Stocks with Positive EPS
```bash
curl "https://eodhd.com/api/screener?api_token=YOUR_TOKEN&filters=[[\"sector\",\"=\",\"Technology\"],[\"earnings_share\",\">\",0]]&limit=50"
```

### 3. Get Top Daily Gainers
```bash
curl "https://eodhd.com/api/screener?api_token=YOUR_TOKEN&filters=[[\"exchange\",\"=\",\"us\"],[\"refund_1d_p\",\">\",5]]&sort=refund_1d_p.desc&limit=10"
```

### 4. PMCC Scanner Universe (Market Cap $50M - $5B)
```bash
curl "https://eodhd.com/api/screener?api_token=YOUR_TOKEN&filters=[[\"market_capitalization\",\">=\",50000000],[\"market_capitalization\",\"<=\",5000000000],[\"exchange\",\"=\",\"us\"]]&sort=market_capitalization.desc&limit=100"
```

## Client Implementation Notes

The PMCC Scanner uses the EODHD Screener API to:

1. **Filter stocks by market cap** for PMCC suitability ($50M - $5B range)
2. **Screen by exchange** (US stocks only)
3. **Sort by market cap** (descending) to prioritize larger, more liquid stocks
4. **Paginate results** using limit/offset for large result sets

The screener is used as a pre-filter before analyzing options data through the MarketData.app API, reducing API calls to only viable PMCC candidates.

## Best Practices

1. **Cache screener results** - Results change daily, not intraday
2. **Use appropriate filters** - Reduce result sets to minimize API credit usage
3. **Handle rate limits gracefully** - Implement exponential backoff
4. **Validate filter syntax** - Malformed filters return errors
5. **Monitor API credits** - Each request uses 5 credits

## Support

- **Documentation:** https://eodhd.com/financial-apis/
- **Support Email:** support@eodhistoricaldata.com
- **Forum:** Available through EODHD website