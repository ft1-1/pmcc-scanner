# MarketData.app API Integration

This document describes the MarketData.app API integration for the PMCC Scanner project.

## Overview

The API integration provides reliable access to real-time and historical market data for:
- Stock quotes and market data
- Options chains with Greeks and analytics
- Option expiration dates and strikes
- Rate-limited access respecting API quotas

## Architecture

### Core Components

1. **MarketDataClient** (`src/api/marketdata_client.py`)
   - Async HTTP client with authentication
   - Comprehensive error handling and retry logic
   - Integration with rate limiter
   - Support for batch requests

2. **RateLimiter** (`src/api/rate_limiter.py`)
   - Token bucket algorithm implementation
   - Respects API concurrent limits (50 requests)
   - Handles daily rate limits by plan type
   - Thread-safe operation

3. **Data Models** (`src/models/api_models.py`)
   - Type-safe data structures for API responses
   - Automatic parsing from API JSON responses
   - Decimal precision for financial calculations
   - Built-in data validation

### Rate Limiting

The rate limiter implements MarketData.app's documented limits:

| Plan Type | Daily Limit | Per-Minute Limit | Concurrent Limit |
|-----------|-------------|------------------|------------------|
| Free      | 100         | None             | 50               |
| Starter   | 10,000      | None             | 50               |
| Trader    | 100,000     | None             | 50               |
| Prime     | Unlimited   | 60,000           | 50               |

Rate limits reset at 9:30 AM Eastern Time (NYSE opening).

## Configuration

### Environment Variables

Required environment variables (set in `.env` file):

```bash
# MarketData.app API Configuration
MARKETDATA_API_TOKEN=your_api_token_here
MARKETDATA_API_BASE_URL=https://api.marketdata.app/v1

# Plan type for rate limiting
MARKETDATA_PLAN_TYPE=free  # or starter, trader, prime
```

### Authentication

The client uses Bearer token authentication as documented:

```python
# Header-based authentication (recommended)
headers = {'Authorization': f'Bearer {token}'}

# URL parameter authentication (alternative)
url = f'https://api.marketdata.app/v1/stocks/quotes/AAPL/?token={token}'
```

## Usage Examples

### Basic Client Setup

```python
import asyncio
from src.api import MarketDataClient

async def main():
    async with MarketDataClient(plan_type='free') as client:
        # Client is ready to use
        response = await client.get_stock_quote('AAPL')
        
        if response.is_success:
            quote = response.data
            print(f"AAPL: ${quote.last}")
        else:
            print(f"Error: {response.error}")

asyncio.run(main())
```

### Stock Quotes

```python
# Single stock quote
response = await client.get_stock_quote('AAPL')
if response.is_success:
    quote = response.data
    print(f"Ask: ${quote.ask}, Bid: ${quote.bid}")
    print(f"Volume: {quote.volume:,}")
    print(f"Spread: {quote.spread_percentage:.2f}%")

# Multiple stock quotes (concurrent)
symbols = ['AAPL', 'MSFT', 'GOOGL']
responses = await client.get_stock_quotes(symbols)

for symbol, response in responses.items():
    if response.is_success:
        print(f"{symbol}: ${response.data.last}")
```

### Option Chains

```python
# Get option expirations
response = await client.get_option_expirations('AAPL')
if response.is_success:
    expirations = response.data
    print(f"Available expirations: {expirations}")

# Get option chain with filters
response = await client.get_option_chain(
    'AAPL',
    expiration='2024-01-19',  # Specific expiration
    side='call',              # Calls only
    strike_limit=20,          # Limit strikes
    min_dte=21,              # Minimum days to expiration
    max_dte=45               # Maximum days to expiration
)

if response.is_success:
    chain = response.data
    print(f"Underlying: {chain.underlying} @ ${chain.underlying_price}")
    
    # Filter for PMCC candidates
    leaps_calls = chain.get_leaps_calls(min_delta=Decimal('0.70'))
    short_calls = chain.get_short_calls(
        min_dte=21, max_dte=45,
        min_delta=Decimal('0.20'), max_delta=Decimal('0.35')
    )
```

### Error Handling

```python
from src.api import MarketDataError, RateLimitError, AuthenticationError

try:
    response = await client.get_stock_quote('AAPL')
    
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
    print("Check your API token")
    
except RateLimitError as e:
    print(f"Rate limit exceeded: {e}")
    if e.retry_after:
        print(f"Retry after {e.retry_after} seconds")
    
except MarketDataError as e:
    print(f"API error: {e}")
    
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Rate Limit Monitoring

```python
# Check usage statistics
stats = client.get_stats()
print(f"Daily usage: {stats['daily_usage']}/{stats.get('daily_limit', 'unlimited')}")
print(f"Usage percentage: {stats.get('usage_percentage', 0):.1f}%")
print(f"Active requests: {stats['active_requests']}/{stats['concurrent_limit']}")

# Health check
is_healthy = await client.health_check()
if not is_healthy:
    print("API connection issues detected")
```

## Data Models

### StockQuote

```python
@dataclass
class StockQuote:
    symbol: str
    ask: Optional[Decimal] = None
    bid: Optional[Decimal] = None
    last: Optional[Decimal] = None
    volume: Optional[int] = None
    updated: Optional[datetime] = None
    
    @property
    def spread(self) -> Optional[Decimal]:
        """Calculate bid-ask spread"""
    
    @property 
    def spread_percentage(self) -> Optional[Decimal]:
        """Spread as percentage of mid price"""
```

### OptionContract

```python
@dataclass
class OptionContract:
    option_symbol: str
    underlying: str
    expiration: datetime
    side: OptionSide  # CALL or PUT
    strike: Decimal
    
    # Pricing and Greeks
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    delta: Optional[Decimal] = None
    gamma: Optional[Decimal] = None
    theta: Optional[Decimal] = None
    vega: Optional[Decimal] = None
    iv: Optional[Decimal] = None
    
    # Analytics
    dte: Optional[int] = None  # Days to expiration
    volume: Optional[int] = None
    open_interest: Optional[int] = None
    
    @property
    def is_leaps(self) -> bool:
        """Check if LEAPS (>1 year to expiration)"""
    
    @property
    def moneyness(self) -> Optional[str]:
        """Return 'ITM', 'ATM', or 'OTM'"""
```

### OptionChain

```python
@dataclass
class OptionChain:
    underlying: str
    underlying_price: Optional[Decimal] = None
    contracts: List[OptionContract] = field(default_factory=list)
    
    def get_calls(self) -> List[OptionContract]:
        """Get all call contracts"""
    
    def get_puts(self) -> List[OptionContract]:
        """Get all put contracts"""
    
    def get_leaps_calls(self, min_delta: Decimal) -> List[OptionContract]:
        """Get LEAPS calls for PMCC strategy"""
    
    def get_short_calls(self, min_dte: int, max_dte: int, 
                       min_delta: Decimal, max_delta: Decimal) -> List[OptionContract]:
        """Get short-term calls for PMCC strategy"""
```

## Error Handling

### HTTP Status Codes

The client handles all documented MarketData.app status codes:

- **200 OK**: Successful request
- **203 Non-Authoritative**: Cached data returned
- **401 Unauthorized**: Invalid or missing token
- **402 Payment Required**: Plan limit exceeded
- **403 Forbidden**: Access denied
- **429 Too Many Requests**: Rate limit exceeded
- **500+ Server Errors**: Temporary server issues

### Retry Logic

- **Network errors**: Exponential backoff retry (max 3 attempts)
- **Rate limits**: Automatic retry with calculated delay
- **Server errors**: Retry with backoff
- **Authentication errors**: No retry (immediate failure)

### Rate Limit Recovery

When rate limits are hit:

1. **Daily limits**: Wait until 9:30 AM ET reset
2. **Per-minute limits**: Wait calculated time based on refill rate
3. **Concurrent limits**: Wait for active requests to complete

## Performance Optimization

### Batch Processing

For daily scans, use concurrent requests within rate limits:

```python
# Process multiple symbols concurrently
symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA']
responses = await client.get_stock_quotes(symbols)

# Process results
for symbol, response in responses.items():
    if response.is_success:
        # Process quote data
        pass
```

### Caching Strategy

For production use, implement caching:

```python
# Use MarketData.app's cached feed for cost savings
response = await client.get_option_chain('AAPL', feed='cached')

# Implement local caching for repeated requests
import time
cache = {}

def get_cached_quote(symbol, ttl=60):
    now = time.time()
    if symbol in cache:
        data, timestamp = cache[symbol]
        if now - timestamp < ttl:
            return data
    
    # Fetch fresh data
    response = await client.get_stock_quote(symbol)
    if response.is_success:
        cache[symbol] = (response.data, now)
        return response.data
```

### Memory Management

For large option chains:

```python
# Use filters to reduce data size
chain_response = await client.get_option_chain(
    'AAPL',
    strike_limit=20,    # Limit strikes near current price
    min_dte=14,         # Skip very short-term options
    side='call'         # Calls only for PMCC scanning
)

# Process contracts in batches
contracts = chain_response.data.contracts
batch_size = 100

for i in range(0, len(contracts), batch_size):
    batch = contracts[i:i + batch_size]
    # Process batch
    process_contracts(batch)
```

## Testing

### Unit Tests

Run unit tests:

```bash
# Test rate limiter
pytest tests/unit/api/test_rate_limiter.py -v

# Test API client
pytest tests/unit/api/test_marketdata_client.py -v

# Test data models
pytest tests/unit/models/test_api_models.py -v

# All API tests
pytest tests/unit/api/ -v
```

### Integration Tests

For integration testing with live API:

```bash
# Set test token
export MARKETDATA_API_TOKEN=your_test_token

# Run integration tests
pytest tests/integration/api/ -v
```

### Demo Script

Run the demo script to test functionality:

```bash
# Set API token in .env file
echo "MARKETDATA_API_TOKEN=your_token" >> .env

# Run demo
python examples/api_client_demo.py
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Check API token is valid and active
   - Verify token has correct permissions
   - Ensure token is not expired

2. **Rate Limit Issues**
   - Monitor daily usage with `client.get_stats()`
   - Implement proper delays between requests
   - Consider upgrading plan for higher limits

3. **Network Connectivity**
   - Check internet connection
   - Verify API endpoint is accessible
   - Check for firewall issues

4. **Data Parsing Errors**
   - Verify API response format matches expectations
   - Check for missing or null data fields
   - Validate data types and ranges

### Debug Logging

Enable debug logging:

```python
import logging

# Enable debug logging for API client
logging.getLogger('src.api').setLevel(logging.DEBUG)

# Enable debug logging for rate limiter
logging.getLogger('src.api.rate_limiter').setLevel(logging.DEBUG)

# Enable HTTP request logging
logging.getLogger('aiohttp.client').setLevel(logging.DEBUG)
```

### Support Resources

- [MarketData.app Documentation](https://marketdata.app/docs/api)
- [MarketData.app Support](https://marketdata.app/support)
- [Rate Limiting Guide](https://marketdata.app/docs/api/rate-limiting)
- [Authentication Guide](https://marketdata.app/docs/api/authentication)

## Production Considerations

### Monitoring

Implement monitoring for:
- API request success/failure rates
- Rate limit usage and violations
- Response times and latency
- Error frequencies by type

### Alerting

Set up alerts for:
- Authentication failures
- Sustained rate limit violations
- API quota approaching limits
- Extended periods of failed requests

### Logging

Log important events:
- Authentication token refresh
- Rate limit hits and recoveries
- API errors and retries
- Performance metrics

### Security

Security best practices:
- Store API tokens securely (environment variables)
- Rotate tokens periodically
- Use HTTPS for all requests
- Implement request/response logging for audit trails
- Monitor for unusual API usage patterns