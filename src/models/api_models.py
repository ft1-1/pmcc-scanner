"""
Data models for multiple data provider API responses.

These models represent the structure of data returned by various market data APIs
including MarketData.app and EODHD, providing a unified interface for the PMCC Scanner.

The models support data from:
- MarketData.app API (documented in marketdata_api_docs.md)
- EODHD API (documented in eodhd-screener.md and related documentation)
- Future providers through standardized factory methods
"""

from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
from enum import Enum


class APIStatus(Enum):
    """API response status codes."""
    OK = "ok"
    ERROR = "error"
    NO_DATA = "no_data"


class OptionSide(Enum):
    """Option contract side (call or put)."""
    CALL = "call"
    PUT = "put"


class DataProviderType(Enum):
    """Supported data provider types."""
    EODHD = "eodhd"
    MARKETDATA = "marketdata"
    CLAUDE = "claude"
    UNKNOWN = "unknown"


@dataclass
class RateLimitHeaders:
    """Rate limit information from API response headers."""
    limit: Optional[int] = None  # X-Api-Ratelimit-Limit
    remaining: Optional[int] = None  # X-Api-Ratelimit-Remaining
    reset: Optional[int] = None  # X-Api-Ratelimit-Reset (UTC epoch seconds)
    consumed: Optional[int] = None  # X-Api-Ratelimit-Consumed
    
    @property
    def reset_datetime(self) -> Optional[datetime]:
        """Convert reset timestamp to datetime."""
        if self.reset:
            return datetime.fromtimestamp(self.reset)
        return None
    
    @property
    def usage_percentage(self) -> Optional[float]:
        """Calculate usage as percentage of limit."""
        if self.limit and self.remaining is not None:
            used = self.limit - self.remaining
            return (used / self.limit) * 100
        return None


@dataclass
class ProviderMetadata:
    """Metadata about the data provider that generated the response."""
    provider_type: DataProviderType
    provider_name: str
    request_timestamp: datetime
    response_latency_ms: Optional[float] = None
    data_freshness: Optional[datetime] = None  # When the underlying data was last updated
    api_version: Optional[str] = None
    request_id: Optional[str] = None
    
    @classmethod
    def for_eodhd(cls, latency_ms: Optional[float] = None) -> 'ProviderMetadata':
        """Create metadata for EODHD provider."""
        return cls(
            provider_type=DataProviderType.EODHD,
            provider_name="EODHD",
            request_timestamp=datetime.now(),
            response_latency_ms=latency_ms,
            api_version="v1"
        )
    
    @classmethod
    def for_marketdata(cls, latency_ms: Optional[float] = None) -> 'ProviderMetadata':
        """Create metadata for MarketData.app provider."""
        return cls(
            provider_type=DataProviderType.MARKETDATA,
            provider_name="MarketData.app",
            request_timestamp=datetime.now(),
            response_latency_ms=latency_ms,
            api_version="v1"
        )


@dataclass
class APIError:
    """API error response."""
    code: int
    message: str
    details: Optional[str] = None
    request_id: Optional[str] = None
    
    def __str__(self) -> str:
        return f"API Error {self.code}: {self.message}"


@dataclass
class APIResponse:
    """Base API response wrapper."""
    status: APIStatus
    data: Optional[Any] = None
    error: Optional[APIError] = None
    rate_limit: Optional[RateLimitHeaders] = None
    raw_response: Optional[Dict[str, Any]] = None
    provider_metadata: Optional[ProviderMetadata] = None
    
    @property
    def is_success(self) -> bool:
        """Check if response indicates success."""
        return self.status == APIStatus.OK and self.error is None
    
    @property
    def is_rate_limited(self) -> bool:
        """Check if response indicates rate limiting."""
        return self.error and self.error.code == 429
    
    @property
    def provider_name(self) -> Optional[str]:
        """Get the name of the provider that generated this response."""
        return self.provider_metadata.provider_name if self.provider_metadata else None
    
    @property
    def response_latency_ms(self) -> Optional[float]:
        """Get the response latency in milliseconds."""
        return self.provider_metadata.response_latency_ms if self.provider_metadata else None
    
    def with_provider_metadata(self, metadata: ProviderMetadata) -> 'APIResponse':
        """Create a copy of this response with provider metadata."""
        return APIResponse(
            status=self.status,
            data=self.data,
            error=self.error,
            rate_limit=self.rate_limit,
            raw_response=self.raw_response,
            provider_metadata=metadata
        )


class StockQuote:
    """Stock quote data from MarketData.app API."""
    symbol: str
    ask: Optional[Decimal] = None
    ask_size: Optional[int] = None
    bid: Optional[Decimal] = None
    bid_size: Optional[int] = None
    mid: Optional[Decimal] = None
    last: Optional[Decimal] = None
    volume: Optional[int] = None
    updated: Optional[datetime] = None
    
    # Additional attributes for enhanced data integration
    change: Optional[Decimal] = None  # Price change from previous close
    change_percent: Optional[Decimal] = None  # Percentage change from previous close
    market_cap: Optional[Decimal] = None  # Market capitalization
    previous_close: Optional[Decimal] = None  # Previous day closing price
    
    def __init__(self, symbol: str, price: Optional[Union[Decimal, str, float]] = None, **kwargs):
        """Initialize StockQuote with backward compatibility for 'price' parameter."""
        # Handle legacy 'price' parameter by mapping it to 'last'
        if price is not None and 'last' not in kwargs:
            if isinstance(price, (str, float, int)):
                try:
                    kwargs['last'] = Decimal(str(price))
                except (ValueError, TypeError):
                    pass
            elif isinstance(price, Decimal):
                kwargs['last'] = price
        
        # Set all fields from kwargs or defaults
        self.symbol = symbol
        self.ask = kwargs.get('ask')
        self.ask_size = kwargs.get('ask_size')
        self.bid = kwargs.get('bid')
        self.bid_size = kwargs.get('bid_size')
        self.mid = kwargs.get('mid')
        self.last = kwargs.get('last')
        self.volume = kwargs.get('volume')
        self.updated = kwargs.get('updated')
        
        # Additional enhanced data attributes
        self.change = kwargs.get('change')
        self.change_percent = kwargs.get('change_percent')
        self.market_cap = kwargs.get('market_cap')
        self.previous_close = kwargs.get('previous_close')
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any], index: int = 0) -> 'StockQuote':
        """
        Create StockQuote from API response data.
        
        Args:
            data: Raw API response data
            index: Index in the response arrays (default 0 for single quotes)
        """
        def get_array_value(key: str, default=None):
            """Safely get value from API response array."""
            arr = data.get(key, [])
            if isinstance(arr, list) and len(arr) > index:
                value = arr[index]
                return value if value is not None else default
            return default
        
        # Extract symbol - can be from array or single value
        symbol_data = data.get('symbol', data.get('Symbol', []))
        if isinstance(symbol_data, list):
            symbol = symbol_data[index] if len(symbol_data) > index else "UNKNOWN"
        else:
            symbol = symbol_data or "UNKNOWN"
        
        # Convert timestamp to datetime if present
        updated = None
        timestamp = get_array_value('updated') or get_array_value('Date') or get_array_value('date')
        if timestamp:
            try:
                if isinstance(timestamp, (int, float)):
                    # Unix timestamp
                    updated = datetime.fromtimestamp(timestamp)
                elif isinstance(timestamp, str):
                    # String date format (EODHD uses YYYY-MM-DD)
                    if '-' in timestamp:
                        updated = datetime.strptime(timestamp, '%Y-%m-%d')
                    else:
                        updated = datetime.fromtimestamp(float(timestamp))
            except (ValueError, TypeError):
                pass
        
        # Convert price fields to Decimal for precision
        def to_decimal(value):
            if value is not None:
                try:
                    return Decimal(str(value))
                except (ValueError, TypeError):
                    pass
            return None
        
        return cls(
            symbol=symbol,
            ask=to_decimal(get_array_value('ask') or get_array_value('Ask')),
            ask_size=get_array_value('askSize') or get_array_value('Ask Size'),
            bid=to_decimal(get_array_value('bid') or get_array_value('Bid')),
            bid_size=get_array_value('bidSize') or get_array_value('Bid Size'),
            mid=to_decimal(get_array_value('mid') or get_array_value('Mid')),
            last=to_decimal(get_array_value('last') or get_array_value('Last') or 
                          get_array_value('close') or get_array_value('adjusted_close')),  # Support EODHD EOD format
            volume=get_array_value('volume') or get_array_value('Volume'),
            updated=updated,
            
            # Additional enhanced data fields
            change=to_decimal(get_array_value('change') or get_array_value('Change')),
            change_percent=to_decimal(get_array_value('change_percent') or get_array_value('ChangePercent') or get_array_value('change_p')),
            market_cap=to_decimal(get_array_value('market_cap') or get_array_value('MarketCap') or get_array_value('market_capitalization')),
            previous_close=to_decimal(get_array_value('previous_close') or get_array_value('PreviousClose') or get_array_value('prev_close'))
        )
    
    @property
    def spread(self) -> Optional[Decimal]:
        """Calculate bid-ask spread."""
        if self.ask and self.bid:
            return self.ask - self.bid
        return None
    
    @property
    def spread_percentage(self) -> Optional[Decimal]:
        """Calculate bid-ask spread as percentage of mid price."""
        if self.spread and self.mid and self.mid > 0:
            return (self.spread / self.mid) * 100
        return None


@dataclass
class OptionContract:
    """Option contract data from MarketData.app API."""
    option_symbol: str
    underlying: str
    expiration: datetime
    side: OptionSide
    strike: Decimal
    
    # Pricing data
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    mid: Optional[Decimal] = None
    last: Optional[Decimal] = None
    
    # Size data
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None
    
    # Market data
    volume: Optional[int] = None
    open_interest: Optional[int] = None
    
    # Greeks and analytics
    delta: Optional[Decimal] = None
    gamma: Optional[Decimal] = None
    theta: Optional[Decimal] = None
    vega: Optional[Decimal] = None
    iv: Optional[Decimal] = None  # Implied volatility
    
    # Calculated values
    intrinsic_value: Optional[Decimal] = None
    extrinsic_value: Optional[Decimal] = None
    underlying_price: Optional[Decimal] = None
    in_the_money: Optional[bool] = None
    
    # Time data
    dte: Optional[int] = None  # Days to expiration
    first_traded: Optional[datetime] = None
    updated: Optional[datetime] = None
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any], index: int) -> 'OptionContract':
        """
        Create OptionContract from API response data.
        
        The MarketData.app API returns option data as parallel arrays where each index
        corresponds to a single option contract. This method extracts data at the specified
        index from all relevant arrays.
        
        Args:
            data: Raw API response data containing parallel arrays
            index: Index in the response arrays for this specific contract
        """
        def get_array_value(key: str, default=None):
            """Safely get value from API response array at the specified index."""
            arr = data.get(key, [])
            if isinstance(arr, list) and len(arr) > index:
                value = arr[index]
                return value if value is not None else default
            return default
        
        def to_decimal(value):
            """Convert value to Decimal for precision."""
            if value is not None and value != '':
                try:
                    return Decimal(str(value))
                except (ValueError, TypeError):
                    pass
            return None
        
        def to_datetime(timestamp):
            """Convert timestamp to datetime."""
            if timestamp:
                try:
                    return datetime.fromtimestamp(timestamp)
                except (ValueError, TypeError):
                    pass
            return None
        
        # Extract required fields - these must be present for a valid contract
        option_symbol = get_array_value('optionSymbol', '')
        underlying = get_array_value('underlying', '')
        
        # Parse expiration timestamp
        expiration_ts = get_array_value('expiration')
        expiration = to_datetime(expiration_ts)
        if not expiration:
            # Fallback if timestamp parsing fails
            expiration = datetime.now()
        
        # Parse option side (call or put)
        side_str = get_array_value('side', 'call')
        side = OptionSide.CALL if side_str.lower() == 'call' else OptionSide.PUT
        
        # Parse strike price
        strike = to_decimal(get_array_value('strike', 0)) or Decimal('0')
        
        return cls(
            option_symbol=option_symbol,
            underlying=underlying,
            expiration=expiration,
            side=side,
            strike=strike,
            
            # Pricing data
            bid=to_decimal(get_array_value('bid')),
            ask=to_decimal(get_array_value('ask')),
            mid=to_decimal(get_array_value('mid')),
            last=to_decimal(get_array_value('last')),
            
            # Size data
            bid_size=get_array_value('bidSize'),
            ask_size=get_array_value('askSize'),
            
            # Market data
            volume=get_array_value('volume'),
            open_interest=get_array_value('openInterest'),
            
            # Greeks
            delta=to_decimal(get_array_value('delta')),
            gamma=to_decimal(get_array_value('gamma')),
            theta=to_decimal(get_array_value('theta')),
            vega=to_decimal(get_array_value('vega')),
            iv=to_decimal(get_array_value('iv')),
            
            # Analytics
            intrinsic_value=to_decimal(get_array_value('intrinsicValue')),
            extrinsic_value=to_decimal(get_array_value('extrinsicValue')),
            underlying_price=to_decimal(get_array_value('underlyingPrice')),
            in_the_money=get_array_value('inTheMoney'),
            
            # Time data
            dte=get_array_value('dte'),
            first_traded=to_datetime(get_array_value('firstTraded')),
            updated=to_datetime(get_array_value('updated'))
        )
    
    @classmethod
    def from_eodhd_response(cls, data: Dict[str, Any], underlying_price: Optional[Decimal] = None) -> 'OptionContract':
        """
        Create OptionContract from EODHD Options API response data.
        
        EODHD returns option data as individual objects with named fields,
        unlike MarketData.app's parallel array structure.
        
        Args:
            data: Raw EODHD option data object
            underlying_price: Underlying stock price (if not in data)
        """
        def to_decimal(value):
            """Convert value to Decimal for precision."""
            if value is not None and value != '':
                try:
                    return Decimal(str(value))
                except (ValueError, TypeError):
                    pass
            return None
        
        def to_datetime_from_string(date_str):
            """Convert date string to datetime."""
            if date_str:
                try:
                    # EODHD uses YYYY-MM-DD format for dates
                    return datetime.strptime(date_str, '%Y-%m-%d')
                except (ValueError, TypeError):
                    pass
            return None
        
        # Extract required fields
        option_symbol = data.get('contract', '')
        underlying = data.get('underlying_symbol', '')
        
        # Parse expiration date
        exp_date_str = data.get('exp_date')
        expiration = to_datetime_from_string(exp_date_str)
        if not expiration:
            expiration = datetime.now()
        
        # Parse option side (call or put)
        side_str = data.get('type', 'call')
        side = OptionSide.CALL if side_str.lower() == 'call' else OptionSide.PUT
        
        # Parse strike price
        strike = to_decimal(data.get('strike', 0)) or Decimal('0')
        
        # Calculate DTE if not provided
        dte = data.get('dte')
        if dte is None and expiration:
            dte = (expiration - datetime.now()).days
        
        # Get underlying price - use passed parameter if available, otherwise from data
        contract_underlying_price = underlying_price or to_decimal(data.get('underlying_price'))
        
        # Calculate ITM status from moneyness if available, otherwise from underlying price
        in_the_money = data.get('in_the_money')
        if in_the_money is None and 'moneyness' in data:
            moneyness = data.get('moneyness', 0)
            if side == OptionSide.CALL:
                in_the_money = moneyness > 1.0  # Call is ITM if underlying > strike
            else:  # PUT
                in_the_money = moneyness < 1.0  # Put is ITM if underlying < strike
        
        # If still no underlying price but we have moneyness, derive it
        if contract_underlying_price is None and 'moneyness' in data and strike > 0:
            moneyness = to_decimal(data.get('moneyness'))
            if moneyness:
                contract_underlying_price = strike * moneyness
        
        # Calculate intrinsic and extrinsic values if not provided
        intrinsic_value = to_decimal(data.get('intrinsic_value'))
        extrinsic_value = to_decimal(data.get('time_value'))
        
        # Calculate intrinsic value if not provided and we have underlying price
        if intrinsic_value is None and contract_underlying_price and strike:
            if side == OptionSide.CALL:
                intrinsic_value = max(Decimal('0'), contract_underlying_price - strike)
            else:  # PUT
                intrinsic_value = max(Decimal('0'), strike - contract_underlying_price)
        
        # Calculate extrinsic value if not provided
        option_price = to_decimal(data.get('midpoint')) or to_decimal(data.get('last'))
        if extrinsic_value is None and option_price and intrinsic_value is not None:
            extrinsic_value = max(Decimal('0'), option_price - intrinsic_value)
        
        return cls(
            option_symbol=option_symbol,
            underlying=underlying,
            expiration=expiration,
            side=side,
            strike=strike,
            
            # Pricing data - use 'midpoint' instead of 'mid'
            bid=to_decimal(data.get('bid')),
            ask=to_decimal(data.get('ask')),
            mid=to_decimal(data.get('midpoint')),
            last=to_decimal(data.get('last')),
            
            # Size data  
            bid_size=data.get('bid_size'),
            ask_size=data.get('ask_size'),
            
            # Market data
            volume=data.get('volume'),
            open_interest=data.get('open_interest'),
            
            # Greeks (EODHD includes these in the response) - use 'volatility' instead of 'implied_volatility'
            delta=to_decimal(data.get('delta')),
            gamma=to_decimal(data.get('gamma')),
            theta=to_decimal(data.get('theta')),
            vega=to_decimal(data.get('vega')),
            iv=to_decimal(data.get('volatility')),
            
            # Analytics
            intrinsic_value=intrinsic_value,
            extrinsic_value=extrinsic_value,
            underlying_price=contract_underlying_price,
            in_the_money=in_the_money,
            
            # Time data
            dte=dte,
            first_traded=None,  # Not provided by EODHD
            updated=datetime.now()
        )
    
    @property
    def spread(self) -> Optional[Decimal]:
        """Calculate bid-ask spread."""
        if self.ask and self.bid:
            return self.ask - self.bid
        return None
    
    @property
    def spread_percentage(self) -> Optional[Decimal]:
        """Calculate bid-ask spread as percentage of mid price."""
        if self.spread and self.mid and self.mid > 0:
            return (self.spread / self.mid) * 100
        return None
    
    @property
    def is_leaps(self) -> bool:
        """Check if this is a LEAPS contract (>1 year to expiration)."""
        if self.dte:
            return self.dte >= 365
        return False
    
    @property
    def moneyness(self) -> Optional[str]:
        """Get moneyness description (ITM, ATM, OTM)."""
        if self.underlying_price and self.strike:
            if self.side == OptionSide.CALL:
                if self.underlying_price > self.strike:
                    return "ITM"
                elif abs(self.underlying_price - self.strike) < Decimal('0.50'):
                    return "ATM"
                else:
                    return "OTM"
            else:  # PUT
                if self.underlying_price < self.strike:
                    return "ITM"
                elif abs(self.underlying_price - self.strike) < Decimal('0.50'):
                    return "ATM"
                else:
                    return "OTM"
        return None
    
    @classmethod
    def from_provider_response(
        cls, 
        data: Dict[str, Any], 
        provider_type: DataProviderType,
        index: Optional[int] = None,
        underlying_price: Optional[Decimal] = None
    ) -> 'OptionContract':
        """
        Create OptionContract from any supported provider response.
        
        Args:
            data: Raw API response data
            provider_type: Type of data provider
            index: Index for array-based responses (MarketData.app)
            underlying_price: Underlying stock price if not in data
            
        Returns:
            OptionContract instance
        """
        if provider_type == DataProviderType.MARKETDATA:
            if index is not None:
                return cls.from_api_response(data, index)
            else:
                raise ValueError("MarketData.app responses require an index parameter")
        elif provider_type == DataProviderType.EODHD:
            return cls.from_eodhd_response(data, underlying_price)
        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")
    
    @property
    def provider_specific_symbol(self) -> str:
        """
        Get provider-specific option symbol format.
        
        Different providers may use different option symbol formats.
        This property ensures we use the correct format for each provider.
        """
        # For now, return the standard option_symbol
        # This can be enhanced to support provider-specific formatting
        return self.option_symbol


@dataclass
class OptionChain:
    """Option chain data from MarketData.app API."""
    underlying: str
    underlying_price: Optional[Decimal] = None
    contracts: List[OptionContract] = field(default_factory=list)
    updated: Optional[datetime] = None
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'OptionChain':
        """
        Create OptionChain from API response data.
        
        The MarketData.app API returns option chain data as parallel arrays where each index
        corresponds to a single option contract. For example:
        - optionSymbol[0] corresponds to strike[0], bid[0], ask[0], etc.
        - All contract data is at the same index across different arrays.
        
        Args:
            data: Raw API response data containing parallel arrays
        """
        # Extract underlying symbol - should be the same for all contracts
        underlying_arr = data.get('underlying', [])
        underlying = underlying_arr[0] if underlying_arr else "UNKNOWN"
        
        # Extract underlying price - should be the same for all contracts
        underlying_price = None
        price_arr = data.get('underlyingPrice', [])
        if price_arr:
            try:
                underlying_price = Decimal(str(price_arr[0]))
            except (ValueError, TypeError):
                pass
        
        # Extract contracts from parallel arrays
        contracts = []
        option_symbols = data.get('optionSymbol', [])
        
        # Process each contract by index
        for i in range(len(option_symbols)):
            try:
                contract = OptionContract.from_api_response(data, i)
                contracts.append(contract)
            except Exception as e:
                # Log error but continue processing other contracts
                import logging
                logging.warning(f"Error parsing option contract at index {i}: {e}")
                continue
        
        # Extract update timestamp - should be the same for all contracts
        updated = None
        updated_arr = data.get('updated', [])
        if updated_arr:
            try:
                updated = datetime.fromtimestamp(updated_arr[0])
            except (ValueError, TypeError):
                pass
        
        return cls(
            underlying=underlying,
            underlying_price=underlying_price,
            contracts=contracts,
            updated=updated
        )
    
    def filter_by_expiration(self, min_dte: Optional[int] = None, 
                           max_dte: Optional[int] = None) -> List[OptionContract]:
        """Filter contracts by days to expiration."""
        filtered = self.contracts
        
        if min_dte is not None:
            filtered = [c for c in filtered if c.dte and c.dte >= min_dte]
        
        if max_dte is not None:
            filtered = [c for c in filtered if c.dte and c.dte <= max_dte]
        
        return filtered
    
    def filter_by_delta(self, min_delta: Optional[Decimal] = None,
                       max_delta: Optional[Decimal] = None) -> List[OptionContract]:
        """Filter contracts by delta."""
        filtered = self.contracts
        
        if min_delta is not None:
            filtered = [c for c in filtered if c.delta and abs(c.delta) >= min_delta]
        
        if max_delta is not None:
            filtered = [c for c in filtered if c.delta and abs(c.delta) <= max_delta]
        
        return filtered
    
    def filter_by_side(self, side: OptionSide) -> List[OptionContract]:
        """Filter contracts by option side (call/put)."""
        return [c for c in self.contracts if c.side == side]
    
    def get_calls(self) -> List[OptionContract]:
        """Get all call contracts."""
        return self.filter_by_side(OptionSide.CALL)
    
    def get_puts(self) -> List[OptionContract]:
        """Get all put contracts."""
        return self.filter_by_side(OptionSide.PUT)
    
    def get_leaps_calls(self, min_delta: Decimal = Decimal('0.70')) -> List[OptionContract]:
        """Get LEAPS call contracts suitable for PMCC strategy."""
        calls = self.get_calls()
        leaps = [c for c in calls if c.is_leaps]
        return [c for c in leaps if c.delta and c.delta >= min_delta]
    
    def get_short_calls(self, min_dte: int = 21, max_dte: int = 45,
                       min_delta: Decimal = Decimal('0.20'),
                       max_delta: Decimal = Decimal('0.35')) -> List[OptionContract]:
        """Get short call contracts suitable for PMCC strategy."""
        calls = self.get_calls()
        
        # Filter by expiration
        calls = [c for c in calls if c.dte and min_dte <= c.dte <= max_dte]
        
        # Filter by delta
        calls = [c for c in calls if c.delta and min_delta <= c.delta <= max_delta]
        
        return calls
    
    @classmethod
    def from_provider_response(
        cls, 
        data: Dict[str, Any], 
        provider_type: DataProviderType
    ) -> 'OptionChain':
        """
        Create OptionChain from any supported provider response.
        
        Args:
            data: Raw API response data
            provider_type: Type of data provider
            
        Returns:
            OptionChain instance
        """
        if provider_type == DataProviderType.MARKETDATA:
            return cls.from_api_response(data)
        elif provider_type == DataProviderType.EODHD:
            # EODHD doesn't have a specific chain response format
            # This would need to be implemented based on EODHD's actual response structure
            return cls.from_api_response(data)
        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")


@dataclass
class EODHDScreenerResult:
    """Stock screener result from EODHD API."""
    code: str
    name: str
    exchange: str
    market_capitalization: Optional[Decimal] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    earnings_share: Optional[Decimal] = None
    dividend_yield: Optional[Decimal] = None
    adjusted_close: Optional[Decimal] = None
    volume: Optional[int] = None
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'EODHDScreenerResult':
        """
        Create EODHDScreenerResult from API response data.
        
        Args:
            data: Raw API response data for a single stock
        """
        def to_decimal(value):
            """Convert value to Decimal for precision."""
            if value is not None:
                try:
                    return Decimal(str(value))
                except (ValueError, TypeError):
                    pass
            return None
        
        return cls(
            code=data.get('code', ''),
            name=data.get('name', ''),
            exchange=data.get('exchange', ''),
            market_capitalization=to_decimal(data.get('market_capitalization')),
            sector=data.get('sector'),
            industry=data.get('industry'),
            earnings_share=to_decimal(data.get('earnings_share')),
            dividend_yield=to_decimal(data.get('dividend_yield')),
            adjusted_close=to_decimal(data.get('adjusted_close')),
            volume=data.get('volume')
        )
    
    @property
    def market_cap_millions(self) -> Optional[Decimal]:
        """Get market cap in millions."""
        if self.market_capitalization:
            return self.market_capitalization / Decimal('1000000')
        return None
    
    @property
    def market_cap_billions(self) -> Optional[Decimal]:
        """Get market cap in billions."""
        if self.market_capitalization:
            return self.market_capitalization / Decimal('1000000000')
        return None


@dataclass
class EODHDScreenerResponse:
    """Complete response from EODHD Screener API."""
    results: List[EODHDScreenerResult]
    total_count: Optional[int] = None
    offset: int = 0
    limit: int = 50
    
    @classmethod
    def from_api_response(cls, data: Union[List[Dict[str, Any]], Dict[str, Any]]) -> 'EODHDScreenerResponse':
        """
        Create EODHDScreenerResponse from API response data.
        
        Args:
            data: Raw API response data - can be a list of stocks or dict with metadata
        """
        if isinstance(data, list):
            # Direct list of results
            results = []
            for item in data:
                try:
                    result = EODHDScreenerResult.from_api_response(item)
                    results.append(result)
                except Exception as e:
                    import logging
                    logging.warning(f"Error parsing screener result: {e}")
                    continue
            
            return cls(
                results=results,
                total_count=len(results)
            )
        
        elif isinstance(data, dict):
            # Response with metadata
            results_data = data.get('data', data.get('results', []))
            results = []
            for item in results_data:
                try:
                    result = EODHDScreenerResult.from_api_response(item)
                    results.append(result)
                except Exception as e:
                    import logging
                    logging.warning(f"Error parsing screener result: {e}")
                    continue
            
            return cls(
                results=results,
                total_count=data.get('total_count', len(results)),
                offset=data.get('offset', 0),
                limit=data.get('limit', 50)
            )
        
        else:
            return cls(results=[])
    
    def get_symbols(self) -> List[str]:
        """Get list of stock symbols from results."""
        return [result.code for result in self.results if result.code]
    
    def filter_by_market_cap(self, min_cap: Optional[Decimal] = None, 
                           max_cap: Optional[Decimal] = None) -> List[EODHDScreenerResult]:
        """Filter results by market capitalization."""
        filtered = self.results
        
        if min_cap is not None:
            filtered = [r for r in filtered if r.market_capitalization and r.market_capitalization >= min_cap]
        
        if max_cap is not None:
            filtered = [r for r in filtered if r.market_capitalization and r.market_capitalization <= max_cap]
        
        return filtered
    
    def filter_by_exchange(self, exchanges: List[str]) -> List[EODHDScreenerResult]:
        """Filter results by exchange."""
        exchange_set = {ex.upper() for ex in exchanges}
        return [r for r in self.results if r.exchange.upper() in exchange_set]


@dataclass
class FundamentalMetrics:
    """Fundamental financial metrics for a stock."""
    symbol: str = ""
    
    # Valuation metrics
    market_capitalization: Optional[Decimal] = None  # Market capitalization
    pe_ratio: Optional[Decimal] = None  # Price-to-Earnings ratio
    peg_ratio: Optional[Decimal] = None  # Price/Earnings to Growth ratio
    pb_ratio: Optional[Decimal] = None  # Price-to-Book ratio
    ps_ratio: Optional[Decimal] = None  # Price-to-Sales ratio
    price_to_cash_flow: Optional[Decimal] = None
    enterprise_value: Optional[Decimal] = None
    ev_to_revenue: Optional[Decimal] = None
    ev_to_ebitda: Optional[Decimal] = None
    
    # Profitability metrics
    profit_margin: Optional[Decimal] = None  # Net profit margin %
    operating_margin: Optional[Decimal] = None  # Operating margin %
    gross_margin: Optional[Decimal] = None  # Gross margin %
    roe: Optional[Decimal] = None  # Return on Equity %
    roa: Optional[Decimal] = None  # Return on Assets %
    roic: Optional[Decimal] = None  # Return on Invested Capital %
    
    # Financial strength metrics
    debt_to_equity: Optional[Decimal] = None  # Debt-to-Equity ratio
    debt_to_assets: Optional[Decimal] = None  # Debt-to-Assets ratio
    current_ratio: Optional[Decimal] = None  # Current assets / Current liabilities
    quick_ratio: Optional[Decimal] = None  # (Current assets - Inventory) / Current liabilities
    cash_ratio: Optional[Decimal] = None  # Cash / Current liabilities
    
    # Growth metrics
    revenue_growth_rate: Optional[Decimal] = None  # YoY revenue growth %
    earnings_growth_rate: Optional[Decimal] = None  # YoY earnings growth %
    book_value_growth_rate: Optional[Decimal] = None  # YoY book value growth %
    
    # Per-share metrics
    earnings_per_share: Optional[Decimal] = None  # EPS
    book_value_per_share: Optional[Decimal] = None  # Book value per share
    cash_per_share: Optional[Decimal] = None  # Cash per share
    revenue_per_share: Optional[Decimal] = None  # Revenue per share
    
    # Other metrics
    shares_outstanding: Optional[int] = None  # Number of shares outstanding
    float_shares: Optional[int] = None  # Number of freely traded shares
    insider_ownership: Optional[Decimal] = None  # Insider ownership %
    institutional_ownership: Optional[Decimal] = None  # Institutional ownership %
    
    # Data freshness
    last_updated: Optional[datetime] = None
    fiscal_year_end: Optional[date] = None
    
    @classmethod
    def from_eodhd_response(cls, data: Dict[str, Any]) -> 'FundamentalMetrics':
        """
        Create FundamentalMetrics from EODHD fundamental data response.
        
        Args:
            data: Raw EODHD fundamental data
        """
        def to_decimal(value):
            """Convert value to Decimal for precision."""
            if value is not None and value != '' and value != 'None':
                try:
                    return Decimal(str(value))
                except (ValueError, TypeError):
                    pass
            return None
        
        def to_percentage_decimal(value):
            """Convert percentage value to decimal (e.g., 15.5% -> 15.5)."""
            if value is not None and value != '' and value != 'None':
                try:
                    val = float(value)
                    # If value is between 0 and 1, assume it's already a decimal percentage
                    if 0 < val < 1:
                        val *= 100
                    return Decimal(str(val))
                except (ValueError, TypeError):
                    pass
            return None
        
        # Extract symbol
        symbol = data.get('General', {}).get('Code', '') or data.get('symbol', '')
        
        # Valuation data
        valuation = data.get('Valuation', {})
        
        # Highlights data (contains key metrics)
        highlights = data.get('Highlights', {})
        
        # Financials data
        financials = data.get('Financials', {})
        balance_sheet = financials.get('Balance_Sheet', {}).get('yearly', {})
        income_statement = financials.get('Income_Statement', {}).get('yearly', {})
        
        # Get most recent year's data (first item in yearly data)
        latest_balance = list(balance_sheet.values())[0] if balance_sheet else {}
        latest_income = list(income_statement.values())[0] if income_statement else {}
        
        # SharesStats data
        shares_stats = data.get('SharesStats', {})
        
        return cls(
            symbol=symbol,
            
            # Valuation metrics
            market_capitalization=to_decimal(highlights.get('MarketCapitalization') or valuation.get('MarketCapitalization')),
            pe_ratio=to_decimal(valuation.get('PERatio') or highlights.get('PERatio')),
            peg_ratio=to_decimal(valuation.get('PEGRatio') or highlights.get('PEGRatio')),
            pb_ratio=to_decimal(valuation.get('PriceBookMRQ') or highlights.get('PriceBookMRQ')),
            ps_ratio=to_decimal(valuation.get('PriceSalesTTM') or highlights.get('PriceSalesTTM')),
            price_to_cash_flow=to_decimal(valuation.get('PriceCashFlowMRQ')),
            enterprise_value=to_decimal(valuation.get('EnterpriseValue') or highlights.get('EnterpriseValue')),
            ev_to_revenue=to_decimal(valuation.get('EnterpriseValueRevenue')),
            ev_to_ebitda=to_decimal(valuation.get('EnterpriseValueEbitda')),
            
            # Profitability metrics (convert percentages)
            profit_margin=to_percentage_decimal(highlights.get('ProfitMargin')),
            operating_margin=to_percentage_decimal(highlights.get('OperatingMarginTTM')),
            gross_margin=to_percentage_decimal(highlights.get('GrossProfitTTM')),
            roe=to_percentage_decimal(highlights.get('ReturnOnEquityTTM')),
            roa=to_percentage_decimal(highlights.get('ReturnOnAssetsTTM')),
            roic=to_percentage_decimal(highlights.get('ReturnOnInvestmentTTM')),
            
            # Financial strength metrics
            debt_to_equity=to_decimal(highlights.get('DebtToEquity')),
            current_ratio=to_decimal(highlights.get('CurrentRatio')),
            quick_ratio=to_decimal(highlights.get('QuickRatio')),
            
            # Growth metrics (convert percentages)
            revenue_growth_rate=to_percentage_decimal(highlights.get('RevenuePerShareTTM')),
            earnings_growth_rate=to_percentage_decimal(highlights.get('QuarterlyEarningsGrowthYOY')),
            
            # Per-share metrics
            earnings_per_share=to_decimal(highlights.get('EarningsPerShareTTM')),
            book_value_per_share=to_decimal(highlights.get('BookValue')),
            revenue_per_share=to_decimal(highlights.get('RevenuePerShareTTM')),
            
            # Share information
            shares_outstanding=int(shares_stats.get('SharesOutstanding', 0)) if shares_stats.get('SharesOutstanding') else None,
            float_shares=int(shares_stats.get('SharesFloat', 0)) if shares_stats.get('SharesFloat') else None,
            insider_ownership=to_percentage_decimal(shares_stats.get('PercentInsiders')),
            institutional_ownership=to_percentage_decimal(shares_stats.get('PercentInstitutions')),
            
            # Data freshness
            last_updated=datetime.now(),
            fiscal_year_end=None  # Could be extracted from General.FiscalYearEnd if needed
        )


@dataclass 
class CalendarEvent:
    """Represents a calendar event (earnings, dividend, etc.) for a stock."""
    symbol: str
    event_type: str  # 'earnings', 'dividend', 'ex_dividend', 'split', etc.
    date: date
    
    # Event-specific data
    announcement_time: Optional[str] = None  # 'before_market', 'after_market', 'during_market'
    
    # Earnings specific
    estimated_eps: Optional[Decimal] = None
    actual_eps: Optional[Decimal] = None
    surprise_percent: Optional[Decimal] = None
    
    # Dividend specific
    dividend_amount: Optional[Decimal] = None
    dividend_yield: Optional[Decimal] = None
    payment_date: Optional[date] = None
    record_date: Optional[date] = None
    
    # Split specific
    split_ratio: Optional[str] = None  # e.g., "2:1", "3:2"
    
    # Additional info
    confirmed: bool = True
    last_updated: Optional[datetime] = None
    
    @classmethod
    def from_eodhd_earnings_response(cls, data: Dict[str, Any]) -> 'CalendarEvent':
        """Create CalendarEvent from EODHD earnings calendar data."""
        def to_decimal(value):
            if value is not None and value != '' and value != 'None':
                try:
                    return Decimal(str(value))
                except (ValueError, TypeError):
                    pass
            return None
        
        def to_date(date_str):
            if date_str:
                try:
                    return datetime.strptime(date_str, '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    pass
            return None
        
        return cls(
            symbol=data.get('code', ''),
            event_type='earnings',
            date=to_date(data.get('date')),
            announcement_time=data.get('when'),  # EODHD uses 'when' field
            estimated_eps=to_decimal(data.get('estimate')),
            actual_eps=to_decimal(data.get('actual')),
            surprise_percent=to_decimal(data.get('surprise_percent')),
            last_updated=datetime.now()
        )
    
    @classmethod
    def from_eodhd_dividend_response(cls, data: Dict[str, Any]) -> 'CalendarEvent':
        """Create CalendarEvent from EODHD dividend calendar data."""
        def to_decimal(value):
            if value is not None and value != '' and value != 'None':
                try:
                    return Decimal(str(value))
                except (ValueError, TypeError):
                    pass
            return None
        
        def to_date(date_str):
            if date_str:
                try:
                    return datetime.strptime(date_str, '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    pass
            return None
        
        return cls(
            symbol=data.get('code', ''),
            event_type='ex_dividend' if data.get('type') == 'ex-dividend' else 'dividend',
            date=to_date(data.get('date')),
            dividend_amount=to_decimal(data.get('dividend')),
            dividend_yield=to_decimal(data.get('yield')),
            payment_date=to_date(data.get('payment_date')),
            record_date=to_date(data.get('record_date')),
            last_updated=datetime.now()
        )


@dataclass
class TechnicalIndicators:
    """Technical indicators and market metrics for a stock."""
    symbol: str
    
    # Volatility metrics
    beta: Optional[Decimal] = None  # Beta vs market (usually S&P 500)
    volatility_30d: Optional[Decimal] = None  # 30-day historical volatility %
    volatility_90d: Optional[Decimal] = None  # 90-day historical volatility %
    volatility_1y: Optional[Decimal] = None  # 1-year historical volatility %
    implied_volatility: Optional[Decimal] = None  # Average implied volatility from options
    
    # Price momentum
    rsi_14d: Optional[Decimal] = None  # 14-day Relative Strength Index
    macd: Optional[Decimal] = None  # MACD value
    macd_signal: Optional[Decimal] = None  # MACD signal line
    macd_histogram: Optional[Decimal] = None  # MACD histogram
    
    # Moving averages (as percentage from current price)
    sma_50d: Optional[Decimal] = None  # 50-day simple moving average
    sma_200d: Optional[Decimal] = None  # 200-day simple moving average
    ema_21d: Optional[Decimal] = None  # 21-day exponential moving average
    
    # Support/Resistance levels
    support_level: Optional[Decimal] = None  # Identified support level
    resistance_level: Optional[Decimal] = None  # Identified resistance level
    
    # Volume indicators
    avg_volume_30d: Optional[int] = None  # 30-day average volume
    relative_volume: Optional[Decimal] = None  # Current volume vs average
    
    # Classification
    sector: Optional[str] = None  # Sector classification
    industry: Optional[str] = None  # Industry classification  
    market_cap_category: Optional[str] = None  # 'large', 'mid', 'small', 'micro'
    
    # Data freshness
    last_updated: Optional[datetime] = None
    
    @classmethod
    def from_eodhd_response(cls, data: Dict[str, Any], technicals_data: Optional[Dict[str, Any]] = None) -> 'TechnicalIndicators':
        """
        Create TechnicalIndicators from EODHD data.
        
        Args:
            data: EODHD fundamental data containing general info
            technicals_data: Optional technical indicators data if available
        """
        def to_decimal(value):
            if value is not None and value != '' and value != 'None':
                try:
                    return Decimal(str(value))
                except (ValueError, TypeError):
                    pass
            return None
        
        # Extract basic info
        general = data.get('General', {})
        highlights = data.get('Highlights', {})
        
        # Market cap categorization
        market_cap = to_decimal(highlights.get('MarketCapitalization'))
        market_cap_category = None
        if market_cap:
            if market_cap >= 200_000_000_000:  # $200B+
                market_cap_category = 'mega'
            elif market_cap >= 10_000_000_000:  # $10B+
                market_cap_category = 'large'
            elif market_cap >= 2_000_000_000:   # $2B+
                market_cap_category = 'mid'
            elif market_cap >= 300_000_000:     # $300M+
                market_cap_category = 'small'
            else:
                market_cap_category = 'micro'
        
        return cls(
            symbol=general.get('Code', '') or data.get('symbol', ''),
            
            # From highlights if available
            beta=to_decimal(highlights.get('Beta')),
            
            # Sector/Industry classification
            sector=general.get('Sector'),
            industry=general.get('Industry'),
            market_cap_category=market_cap_category,
            
            # Volume data if available
            avg_volume_30d=int(highlights.get('SharesFloat', 0)) if highlights.get('SharesFloat') else None,
            
            # Technical indicators from separate API call if provided
            rsi_14d=to_decimal(technicals_data.get('rsi')) if technicals_data else None,
            sma_50d=to_decimal(technicals_data.get('sma_50')) if technicals_data else None,
            sma_200d=to_decimal(technicals_data.get('sma_200')) if technicals_data else None,
            
            last_updated=datetime.now()
        )


@dataclass 
class RiskMetrics:
    """Risk assessment metrics for a stock."""
    symbol: str
    
    # Credit and financial risk
    credit_rating: Optional[str] = None  # S&P, Moody's, Fitch rating
    financial_strength_score: Optional[int] = None  # 1-10 scale
    bankruptcy_risk_score: Optional[Decimal] = None  # Probability of bankruptcy %
    
    # Ownership and liquidity risk
    institutional_ownership: Optional[Decimal] = None  # % owned by institutions
    insider_ownership: Optional[Decimal] = None  # % owned by insiders
    short_interest: Optional[Decimal] = None  # % of float sold short
    days_to_cover: Optional[Decimal] = None  # Days to cover short position
    
    # Analyst coverage
    analyst_rating_avg: Optional[Decimal] = None  # Average analyst rating (1-5 scale)
    analyst_count: Optional[int] = None  # Number of analysts covering
    price_target_avg: Optional[Decimal] = None  # Average analyst price target
    price_target_upside: Optional[Decimal] = None  # % upside to price target
    
    # ESG (Environmental, Social, Governance) scores
    esg_score_total: Optional[int] = None  # Total ESG score
    environmental_score: Optional[int] = None  # Environmental score
    social_score: Optional[int] = None  # Social score
    governance_score: Optional[int] = None  # Governance score
    
    # Options market risk indicators
    put_call_ratio: Optional[Decimal] = None  # Put/Call volume ratio
    options_volume_avg: Optional[int] = None  # Average daily options volume
    max_pain_price: Optional[Decimal] = None  # Options max pain price
    
    # Liquidity risk
    bid_ask_spread_pct: Optional[Decimal] = None  # Average bid-ask spread %
    trading_volume_rank: Optional[int] = None  # Volume percentile rank (1-100)
    
    # Data freshness
    last_updated: Optional[datetime] = None
    
    @classmethod
    def from_eodhd_response(cls, data: Dict[str, Any], analyst_data: Optional[Dict[str, Any]] = None) -> 'RiskMetrics':
        """
        Create RiskMetrics from EODHD data.
        
        Args:
            data: EODHD fundamental data
            analyst_data: Optional analyst recommendations data
        """
        def to_decimal(value):
            if value is not None and value != '' and value != 'None':
                try:
                    return Decimal(str(value))
                except (ValueError, TypeError):
                    pass
            return None
        
        def to_percentage_decimal(value):
            if value is not None and value != '' and value != 'None':
                try:
                    val = float(value)
                    if 0 < val < 1:
                        val *= 100
                    return Decimal(str(val))
                except (ValueError, TypeError):
                    pass
            return None
        
        # Extract data from different sections
        general = data.get('General', {})
        shares_stats = data.get('SharesStats', {})
        highlights = data.get('Highlights', {})
        
        # Analyst data processing
        analyst_rating_avg = None
        analyst_count = None
        price_target_avg = None
        
        if analyst_data:
            # Process analyst recommendations
            ratings = analyst_data.get('Rating', {})
            if ratings:
                analyst_rating_avg = to_decimal(ratings.get('Rating'))
                analyst_count = int(ratings.get('AnalystCount', 0)) if ratings.get('AnalystCount') else None
                price_target_avg = to_decimal(ratings.get('TargetPrice'))
        
        return cls(
            symbol=general.get('Code', '') or data.get('symbol', ''),
            
            # Ownership metrics from SharesStats
            institutional_ownership=to_percentage_decimal(shares_stats.get('PercentInstitutions')),
            insider_ownership=to_percentage_decimal(shares_stats.get('PercentInsiders')),
            short_interest=to_percentage_decimal(shares_stats.get('ShortInterest')),
            
            # Analyst data
            analyst_rating_avg=analyst_rating_avg,
            analyst_count=analyst_count,
            price_target_avg=price_target_avg,
            
            # Calculate upside if we have price target and current price
            price_target_upside=(
                ((price_target_avg - to_decimal(highlights.get('MarketCapitalization'))) / 
                 to_decimal(highlights.get('MarketCapitalization'))) * 100
                if price_target_avg and highlights.get('MarketCapitalization') else None
            ),
            
            last_updated=datetime.now()
        )


class EnhancedStockData:
    """
    Enhanced stock data combining quote, fundamental, calendar, technical, and risk data.
    This represents a complete view of a stock for AI-enhanced PMCC analysis.
    """
    
    def __init__(
        self,
        quote: Optional[StockQuote] = None,
        symbol: Optional[str] = None,
        fundamentals: Optional[FundamentalMetrics] = None,
        calendar_events: Optional[List[CalendarEvent]] = None,
        technical_indicators: Optional[TechnicalIndicators] = None,
        risk_metrics: Optional[RiskMetrics] = None,
        options_chain: Optional[OptionChain] = None,
        pmcc_suitability_score: Optional[Decimal] = None,
        ai_analysis_summary: Optional[str] = None,
        data_collection_timestamp: Optional[datetime] = None,
        data_completeness_score: Optional[Decimal] = None,
    ):
        """Initialize EnhancedStockData with backward compatibility for 'symbol' parameter."""
        # Handle symbol parameter by creating a basic StockQuote if not provided
        if quote is None and symbol is not None:
            quote = StockQuote(symbol=symbol)
        elif quote is None:
            raise ValueError("Either 'quote' or 'symbol' parameter must be provided")
        
        # Basic quote data
        self.quote = quote
        
        # Enhanced data components
        self.fundamentals = fundamentals
        self.calendar_events = calendar_events or []
        self.technical_indicators = technical_indicators
        self.risk_metrics = risk_metrics
        
        # Options market data
        self.options_chain = options_chain
        
        # AI analysis results (to be populated by AI analysis engine)
        self.pmcc_suitability_score = pmcc_suitability_score
        self.ai_analysis_summary = ai_analysis_summary
        
        # Data collection metadata
        self.data_collection_timestamp = data_collection_timestamp or datetime.now()
        self.data_completeness_score = data_completeness_score
    
    @property
    def symbol(self) -> str:
        """Get the stock symbol."""
        return self.quote.symbol
    
    @property
    def has_complete_fundamental_data(self) -> bool:
        """Check if fundamental data is available and reasonably complete."""
        if not self.fundamentals:
            return False
        
        # Check if key fundamental metrics are available
        key_metrics = [
            self.fundamentals.pe_ratio,
            self.fundamentals.profit_margin,
            self.fundamentals.debt_to_equity,
            self.fundamentals.roe,
            self.fundamentals.earnings_per_share
        ]
        
        available_count = sum(1 for metric in key_metrics if metric is not None)
        return available_count >= 3  # At least 3 out of 5 key metrics
    
    @property
    def has_options_data(self) -> bool:
        """Check if options chain data is available."""
        return self.options_chain is not None and len(self.options_chain.contracts) > 0
    
    @property  
    def upcoming_earnings_date(self) -> Optional[date]:
        """Get the next earnings date if available."""
        earnings_events = [
            event for event in self.calendar_events 
            if event.event_type == 'earnings' and event.date >= date.today()
        ]
        if earnings_events:
            return min(event.date for event in earnings_events)
        return None
    
    @property
    def next_ex_dividend_date(self) -> Optional[date]:
        """Get the next ex-dividend date if available."""
        dividend_events = [
            event for event in self.calendar_events 
            if event.event_type == 'ex_dividend' and event.date >= date.today()
        ]
        if dividend_events:
            return min(event.date for event in dividend_events)
        return None
    
    def calculate_completeness_score(self) -> Decimal:
        """
        Calculate a completeness score based on available data.
        
        Returns:
            Decimal score from 0-100 indicating data completeness
        """
        total_weight = 0
        available_weight = 0
        
        # Quote data (required) - 30% weight
        if self.quote:
            available_weight += 30
        total_weight += 30
        
        # Fundamental data - 25% weight  
        total_weight += 25
        if self.fundamentals and self.has_complete_fundamental_data:
            available_weight += 25
        elif self.fundamentals:
            available_weight += 15  # Partial credit
        
        # Options data - 20% weight
        total_weight += 20
        if self.has_options_data:
            available_weight += 20
        
        # Technical indicators - 15% weight
        total_weight += 15
        if self.technical_indicators:
            # Check how many technical fields are populated
            tech_fields = [
                self.technical_indicators.beta,
                self.technical_indicators.sector,
                self.technical_indicators.volatility_30d,
                self.technical_indicators.rsi_14d
            ]
            tech_completeness = sum(1 for f in tech_fields if f is not None) / len(tech_fields)
            available_weight += 15 * tech_completeness
        
        # Risk metrics - 10% weight
        total_weight += 10
        if self.risk_metrics:
            risk_fields = [
                self.risk_metrics.institutional_ownership,
                self.risk_metrics.analyst_rating_avg,
                self.risk_metrics.short_interest
            ]
            risk_completeness = sum(1 for f in risk_fields if f is not None) / len(risk_fields)
            available_weight += 10 * risk_completeness
        
        score = (available_weight / total_weight) * 100 if total_weight > 0 else 0
        self.data_completeness_score = Decimal(str(round(score, 1)))
        return self.data_completeness_score
    
    @property
    def completeness_score(self) -> Optional[Decimal]:
        """Backward compatibility property for completeness_score."""
        return self.data_completeness_score


@dataclass
class PMCCOpportunityAnalysis:
    """AI analysis result for a single PMCC opportunity."""
    symbol: str
    score: Decimal  # 0-100 score for this opportunity
    reasoning: str  # Brief reasoning for the score
    
    # Risk assessment components
    risk_score: Optional[Decimal] = None  # 0-100, higher = riskier
    fundamental_health_score: Optional[Decimal] = None  # 0-100
    technical_setup_score: Optional[Decimal] = None  # 0-100
    calendar_risk_score: Optional[Decimal] = None  # 0-100, upcoming events risk
    pmcc_quality_score: Optional[Decimal] = None  # 0-100, PMCC strategy fit
    
    # Key insights
    key_strengths: Optional[List[str]] = None
    key_risks: Optional[List[str]] = None
    
    # Recommendation
    recommendation: Optional[str] = None  # "strong_buy", "buy", "hold", "avoid"
    confidence: Optional[Decimal] = None  # 0-100, confidence in analysis
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PMCCOpportunityAnalysis':
        """Create PMCCOpportunityAnalysis from dictionary data."""
        def to_decimal(value):
            if value is not None:
                try:
                    return Decimal(str(value))
                except (ValueError, TypeError):
                    pass
            return None
        
        def to_string_list(value):
            if isinstance(value, list):
                return [str(item) for item in value if item is not None]
            return None
        
        return cls(
            symbol=str(data.get('symbol', '')),
            score=to_decimal(data.get('score')) or Decimal('0'),
            reasoning=str(data.get('reasoning', '')),
            risk_score=to_decimal(data.get('risk_score')),
            fundamental_health_score=to_decimal(data.get('fundamental_health_score')),
            technical_setup_score=to_decimal(data.get('technical_setup_score')),
            calendar_risk_score=to_decimal(data.get('calendar_risk_score')),
            pmcc_quality_score=to_decimal(data.get('pmcc_quality_score')),
            key_strengths=to_string_list(data.get('key_strengths')),
            key_risks=to_string_list(data.get('key_risks')),
            recommendation=data.get('recommendation'),
            confidence=to_decimal(data.get('confidence'))
        )


@dataclass
class ClaudeAnalysisResponse:
    """Complete AI analysis response from Claude."""
    opportunities: List[PMCCOpportunityAnalysis]
    market_assessment: Optional[str] = None  # Overall market conditions assessment
    analysis_timestamp: datetime = field(default_factory=datetime.now)
    
    # Metadata
    model_used: Optional[str] = None
    processing_time_ms: Optional[float] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    
    @classmethod
    def from_claude_response(cls, raw_response: Dict[str, Any], processing_time_ms: Optional[float] = None) -> 'ClaudeAnalysisResponse':
        """
        Create ClaudeAnalysisResponse from Claude API response.
        
        Args:
            raw_response: Raw response from Claude API
            processing_time_ms: Time taken to process the request
            
        Returns:
            ClaudeAnalysisResponse instance
        """
        # Extract opportunities from response
        opportunities = []
        opportunities_data = raw_response.get('opportunities', [])
        
        if not isinstance(opportunities_data, list):
            # Handle case where opportunities is not a list
            opportunities_data = []
        
        for opp_data in opportunities_data:
            if isinstance(opp_data, dict):
                try:
                    opportunity = PMCCOpportunityAnalysis.from_dict(opp_data)
                    opportunities.append(opportunity)
                except Exception as e:
                    import logging
                    logging.warning(f"Error parsing opportunity data: {e}")
                    continue
        
        # Extract metadata from usage if available
        usage = raw_response.get('usage', {})
        
        return cls(
            opportunities=opportunities,
            market_assessment=raw_response.get('market_assessment'),
            model_used=raw_response.get('model'),
            processing_time_ms=processing_time_ms,
            input_tokens=usage.get('input_tokens'),
            output_tokens=usage.get('output_tokens')
        )
    
    def get_top_opportunities(self, limit: int = 10) -> List[PMCCOpportunityAnalysis]:
        """Get top N opportunities sorted by score."""
        sorted_opportunities = sorted(self.opportunities, key=lambda x: x.score, reverse=True)
        return sorted_opportunities[:limit]
    
    def get_high_confidence_opportunities(self, min_confidence: Decimal = Decimal('75')) -> List[PMCCOpportunityAnalysis]:
        """Get opportunities with confidence above threshold."""
        return [
            opp for opp in self.opportunities 
            if opp.confidence and opp.confidence >= min_confidence
        ]