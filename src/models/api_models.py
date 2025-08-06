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


@dataclass
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
            updated=updated
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