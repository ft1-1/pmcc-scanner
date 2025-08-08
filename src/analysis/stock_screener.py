"""
Stock screener for identifying PMCC candidates.

Filters stocks based on market cap, liquidity, options availability,
volatility, and technical factors.
"""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime, timedelta

try:
    from src.models.api_models import StockQuote, OptionChain, EODHDScreenerResponse
    from src.api.sync_marketdata_client import SyncMarketDataClient as MarketDataClient
    from src.api.eodhd_client import EODHDClient
except ImportError:
    # Handle case when running as script
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from models.api_models import StockQuote, OptionChain, EODHDScreenerResponse
    from api.sync_marketdata_client import SyncMarketDataClient as MarketDataClient
    from api.eodhd_client import EODHDClient


logger = logging.getLogger(__name__)


@dataclass
class ScreeningCriteria:
    """Criteria for screening stocks for PMCC opportunities."""
    
    # Market cap filters (in millions)
    min_market_cap: Decimal = Decimal('50')  # $50M minimum
    max_market_cap: Decimal = Decimal('50000')  # $50B maximum (increased for large caps)
    
    # Price filters
    min_price: Decimal = Decimal('10')  # $10 minimum for reasonable option spreads
    max_price: Decimal = Decimal('500')  # $500 maximum for capital efficiency
    
    # Liquidity filters
    min_daily_volume: int = 500_000  # Minimum daily share volume
    min_avg_volume_20d: Optional[int] = 1_000_000  # 20-day average volume
    
    # Options requirements
    require_weekly_options: bool = False  # Optional: weekly expirations preferred but not required
    require_leaps: bool = False  # Optional: LEAPS preferred but not required for initial screening
    min_options_volume: int = 50  # Minimum daily options volume (lowered for broader screening)
    
    # Volatility filters
    min_iv_rank: Optional[Decimal] = None  # Optional: 30th percentile IV rank
    max_iv_rank: Optional[Decimal] = None  # Optional: 80th percentile IV rank
    min_hv_20d: Optional[Decimal] = None  # Optional: 20% minimum 20-day HV
    
    # Technical filters
    above_sma_20: bool = False  # Optional: price above 20-day SMA
    above_sma_50: bool = False  # Optional: above 50-day SMA
    min_rsi: Optional[Decimal] = None  # Optional: minimum RSI (oversold protection)
    max_rsi: Optional[Decimal] = None  # Optional: maximum RSI (overbought protection)
    
    # Fundamental filters
    exclude_earnings_week: bool = True  # Exclude stocks with earnings this week
    min_market_cap_ratio: Optional[Decimal] = None  # Market cap / revenue ratio


@dataclass 
class StockScreenResult:
    """Result of stock screening process."""
    symbol: str
    quote: StockQuote
    market_cap: Optional[Decimal] = None
    avg_volume_20d: Optional[int] = None
    iv_rank: Optional[Decimal] = None
    hv_20d: Optional[Decimal] = None
    sma_20: Optional[Decimal] = None
    sma_50: Optional[Decimal] = None
    rsi: Optional[Decimal] = None
    has_weekly_options: bool = False
    has_leaps: bool = False
    options_volume: Optional[int] = None
    earnings_date: Optional[datetime] = None
    screening_score: Optional[Decimal] = None
    screened_at: datetime = datetime.now()


class StockScreener:
    """Screens stocks for PMCC suitability."""
    
    def __init__(self, api_client: Optional[MarketDataClient], eodhd_client: Optional[EODHDClient] = None):
        """
        Initialize with API clients.
        
        Args:
            api_client: Optional MarketData.app client for quotes and options data
            eodhd_client: Optional EODHD client for stock screening
        """
        self.api_client = api_client
        self.eodhd_client = eodhd_client
        self.sync_eodhd_client = None  # Will be initialized when needed
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Log warning if no clients available
        if not api_client and not eodhd_client:
            self.logger.warning("No API clients provided - functionality will be limited")
    
    def _get_sync_eodhd_client(self):
        """Get or create sync EODHD client for quote operations."""
        if self.sync_eodhd_client is None and self.eodhd_client:
            from src.api.sync_eodhd_client import SyncEODHDClient
            self.sync_eodhd_client = SyncEODHDClient(
                api_token=self.eodhd_client.api_token,
                base_url=self.eodhd_client.base_url,
                timeout=self.eodhd_client.timeout.total,
                max_retries=self.eodhd_client.max_retries,
                retry_backoff=self.eodhd_client.retry_backoff
            )
        return self.sync_eodhd_client
    
    def screen_symbols(self, symbols: List[str], 
                      criteria: Optional[ScreeningCriteria] = None,
                      quote_source: str = "marketdata") -> List[StockScreenResult]:
        """
        Screen a list of symbols against PMCC criteria.
        
        Args:
            symbols: List of stock symbols to screen
            criteria: Screening criteria (uses defaults if None)
            quote_source: Source for quotes/volume data ("marketdata" or "eodhd")
            
        Returns:
            List of StockScreenResult objects for passing stocks
        """
        if criteria is None:
            criteria = ScreeningCriteria()
        
        results = []
        
        for symbol in symbols:
            try:
                result = self._screen_single_symbol(symbol, criteria, quote_source)
                if result:
                    results.append(result)
            except Exception as e:
                self.logger.warning(f"Error screening {symbol}: {e}")
                continue
        
        # Sort by screening score (highest first)
        results.sort(key=lambda x: x.screening_score or Decimal('0'), reverse=True)
        
        return results
    
    def screen_universe(self, universe: str = "SP500", 
                       criteria: Optional[ScreeningCriteria] = None,
                       max_results: int = 100,
                       quote_source: str = "marketdata") -> List[StockScreenResult]:
        """
        Screen a predefined universe of stocks.
        
        Args:
            universe: Stock universe to screen ("SP500", "NASDAQ100", "EODHD_PMCC", etc.)
            criteria: Screening criteria
            max_results: Maximum number of results to return
            quote_source: Source for quotes/volume data ("marketdata" or "eodhd")
            
        Returns:
            List of top-ranked StockScreenResult objects
        """
        if criteria is None:
            criteria = ScreeningCriteria()
        
        # Get universe symbols
        symbols = self._get_universe_symbols(universe, criteria)
        
        results = self.screen_symbols(symbols, criteria, quote_source)
        
        return results[:max_results]
    
    def _screen_single_symbol(self, symbol: str, 
                             criteria: ScreeningCriteria,
                             quote_source: str = "marketdata") -> Optional[StockScreenResult]:
        """Screen a single symbol against criteria."""
        
        # Get basic quote data from appropriate source
        quote_response = None
        if quote_source.lower() == "eodhd":
            # Use EODHD for EOD quotes/volume
            eodhd_client = self._get_sync_eodhd_client()
            if not eodhd_client and self.api_client:
                self.logger.warning(f"EODHD client not available for {symbol}, falling back to MarketData")
                quote_response = self.api_client.get_quote(symbol)
            elif eodhd_client:
                quote_response = eodhd_client.get_stock_quote_eod(symbol)
            elif not self.api_client:
                self.logger.error(f"No API clients available for {symbol}")
                return None
        else:
            # Use MarketData for real-time quotes
            if self.api_client:
                quote_response = self.api_client.get_quote(symbol)
            elif self.eodhd_client:
                # Fall back to EODHD if MarketData not available
                eodhd_client = self._get_sync_eodhd_client()
                if eodhd_client:
                    quote_response = eodhd_client.get_stock_quote_eod(symbol)
                else:
                    self.logger.error(f"No API clients available for {symbol}")
                    return None
            else:
                self.logger.error(f"No API clients available for {symbol}")
                return None
        
        if not quote_response or not quote_response.is_success or not quote_response.data:
            self.logger.debug(f"Failed to get quote for {symbol} from {quote_source}")
            return None
        
        # Convert raw response to StockQuote if needed
        if isinstance(quote_response.data, dict):
            from src.models.api_models import StockQuote
            quote = StockQuote.from_api_response(quote_response.data)
        else:
            quote = quote_response.data
        
        # Apply basic price filters
        if not self._check_price_filters(quote, criteria):
            return None
        
        # Get additional market data
        market_data = self._get_market_data(symbol, quote_source)
        
        # Apply all screening filters
        if not self._check_all_filters(quote, market_data, criteria):
            return None
        
        # Calculate screening score
        score = self._calculate_screening_score(quote, market_data, criteria)
        
        return StockScreenResult(
            symbol=symbol,
            quote=quote,
            market_cap=market_data.get('market_cap'),
            avg_volume_20d=market_data.get('avg_volume_20d'),
            iv_rank=market_data.get('iv_rank'),
            hv_20d=market_data.get('hv_20d'),
            sma_20=market_data.get('sma_20'),
            sma_50=market_data.get('sma_50'),
            rsi=market_data.get('rsi'),
            has_weekly_options=market_data.get('has_weekly_options', False),
            has_leaps=market_data.get('has_leaps', False),
            options_volume=market_data.get('options_volume'),
            earnings_date=market_data.get('earnings_date'),
            screening_score=score
        )
    
    def _check_price_filters(self, quote: StockQuote, 
                           criteria: ScreeningCriteria) -> bool:
        """Check basic price and volume filters."""
        
        # Check price range
        price = quote.last or quote.mid
        if not price:
            return False
        
        if price < criteria.min_price or price > criteria.max_price:
            return False
        
        # Check volume
        if not quote.volume or quote.volume < criteria.min_daily_volume:
            return False
        
        return True
    
    def _get_market_data(self, symbol: str, quote_source: str = "marketdata") -> Dict[str, Any]:
        """Get additional market data for screening."""
        market_data = {}
        
        try:
            # In a real implementation, these would be actual API calls
            # For now, using placeholder logic
            
            # Market cap estimation (simplified) - reuse the same quote logic
            quote_response = None
            if quote_source.lower() == "eodhd":
                eodhd_client = self._get_sync_eodhd_client()
                if not eodhd_client and self.api_client:
                    # Fall back to MarketData if EODHD not available
                    quote_response = self.api_client.get_quote(symbol)
                elif eodhd_client:
                    quote_response = eodhd_client.get_stock_quote_eod(symbol)
            else:
                # Default to MarketData client
                if self.api_client:
                    quote_response = self.api_client.get_quote(symbol)
                elif self.eodhd_client:
                    # Fall back to EODHD if MarketData not available
                    eodhd_client = self._get_sync_eodhd_client()
                    if eodhd_client:
                        quote_response = eodhd_client.get_stock_quote_eod(symbol)
            
            if quote_response and quote_response.is_success and quote_response.data:
                # Convert raw response to StockQuote if needed
                if isinstance(quote_response.data, dict):
                    from src.models.api_models import StockQuote
                    quote = StockQuote.from_api_response(quote_response.data)
                else:
                    quote = quote_response.data
                
                if quote.last:
                    # Rough estimate - would need shares outstanding from fundamentals API
                    estimated_market_cap = quote.last * Decimal('100000000')  # Placeholder
                    market_data['market_cap'] = estimated_market_cap
            else:
                self.logger.warning(f"Could not get quote for {symbol} from {quote_source}")
            
            # Options availability check
            options_response = None
            if self.api_client:
                # Use MarketData client if available
                options_response = self.api_client.get_option_chain(symbol)
            elif self.eodhd_client:
                # Fall back to EODHD client
                eodhd_sync_client = self._get_sync_eodhd_client()
                if eodhd_sync_client:
                    options_response = eodhd_sync_client.get_option_chain(symbol)
                    
            if options_response and options_response.is_success and options_response.data:
                # Check for LEAPS (> 365 days) and weekly options
                market_data['has_leaps'] = self._check_has_leaps(options_response.data)
                market_data['has_weekly_options'] = self._check_has_weekly_options(options_response.data)
                market_data['options_volume'] = self._calculate_options_volume(options_response.data)
            
            # Technical indicators (would be calculated from historical data)
            market_data.update({
                'avg_volume_20d': None,  # Would calculate from historical data
                'iv_rank': None,  # Would calculate from IV history
                'hv_20d': None,  # Would calculate from price history
                'sma_20': None,  # Would calculate from price history
                'sma_50': None,  # Would calculate from price history
                'rsi': None,  # Would calculate from price history
                'earnings_date': None  # Would get from fundamentals API
            })
            
        except Exception as e:
            self.logger.warning(f"Error getting market data for {symbol}: {e}")
        
        return market_data
    
    def _check_has_leaps(self, options_data: OptionChain) -> bool:
        """Check if stock has LEAPS available."""
        if not options_data.contracts:
            return False
        return any(contract.dte and contract.dte >= 365 for contract in options_data.contracts)
    
    def _check_has_weekly_options(self, options_data: OptionChain) -> bool:
        """Check if stock has weekly options."""
        if not options_data.contracts:
            return False
        # Simplified check - would need to analyze expiration patterns
        return any(contract.dte and contract.dte <= 7 for contract in options_data.contracts)
    
    def _calculate_options_volume(self, options_data: OptionChain) -> Optional[int]:
        """Calculate total options volume."""
        if not options_data.contracts:
            return None
        valid_volumes = [contract.volume for contract in options_data.contracts 
                        if contract.volume is not None and contract.volume > 0]
        return sum(valid_volumes) if valid_volumes else None
    
    def _check_all_filters(self, quote: StockQuote, market_data: Dict[str, Any],
                          criteria: ScreeningCriteria) -> bool:
        """Apply all screening filters."""
        
        # Market cap filter
        market_cap = market_data.get('market_cap')
        if market_cap:
            market_cap_millions = market_cap / Decimal('1000000')
            if (market_cap_millions < criteria.min_market_cap or 
                market_cap_millions > criteria.max_market_cap):
                return False
        
        # Options requirements
        if criteria.require_leaps and not market_data.get('has_leaps', False):
            return False
        
        if criteria.require_weekly_options and not market_data.get('has_weekly_options', False):
            return False
        
        options_volume = market_data.get('options_volume')
        if options_volume and options_volume < criteria.min_options_volume:
            return False
        
        # Volatility filters
        iv_rank = market_data.get('iv_rank')
        if iv_rank and criteria.min_iv_rank and iv_rank < criteria.min_iv_rank:
            return False
        if iv_rank and criteria.max_iv_rank and iv_rank > criteria.max_iv_rank:
            return False
        
        # Technical filters
        if criteria.above_sma_20:
            sma_20 = market_data.get('sma_20')
            if sma_20 and quote.last and quote.last < sma_20:
                return False
        
        if criteria.above_sma_50:
            sma_50 = market_data.get('sma_50')
            if sma_50 and quote.last and quote.last < sma_50:
                return False
        
        # RSI filters
        rsi = market_data.get('rsi')
        if rsi and criteria.min_rsi and rsi < criteria.min_rsi:
            return False
        if rsi and criteria.max_rsi and rsi > criteria.max_rsi:
            return False
        
        # Earnings filter
        if criteria.exclude_earnings_week:
            earnings_date = market_data.get('earnings_date')
            if earnings_date:
                days_to_earnings = (earnings_date - datetime.now()).days
                if abs(days_to_earnings) <= 7:  # Within a week
                    return False
        
        return True
    
    def _calculate_screening_score(self, quote: StockQuote, market_data: Dict[str, Any],
                                 criteria: ScreeningCriteria) -> Decimal:
        """Calculate a composite screening score (0-100)."""
        
        score = Decimal('0')
        factors = 0
        
        # Liquidity score (30% weight)
        if quote.volume and market_data.get('avg_volume_20d'):
            volume_ratio = quote.volume / market_data['avg_volume_20d']
            liquidity_score = min(100, volume_ratio * 50)  # Higher current volume is better
            score += Decimal(str(liquidity_score)) * Decimal('0.3')
            factors += 1
        
        # Options liquidity score (25% weight)
        options_volume = market_data.get('options_volume')
        if options_volume:
            # Logarithmic scale for options volume
            import math
            options_score = min(100, math.log10(max(1, options_volume)) * 20)
            score += Decimal(str(options_score)) * Decimal('0.25')
            factors += 1
        
        # Volatility score (20% weight)
        iv_rank = market_data.get('iv_rank')
        if iv_rank:
            # Prefer moderate IV rank (40-60th percentile)
            if 40 <= iv_rank <= 60:
                vol_score = 100
            elif 30 <= iv_rank <= 70:
                vol_score = 80
            else:
                vol_score = max(0, 100 - abs(iv_rank - 50) * 2)
            score += Decimal(str(vol_score)) * Decimal('0.20')
            factors += 1
        
        # Technical score (15% weight)
        tech_score = Decimal('50')  # Neutral baseline
        
        if market_data.get('rsi'):
            rsi = market_data['rsi']
            # Prefer RSI between 40-60
            if 40 <= rsi <= 60:
                tech_score += Decimal('25')
            elif 30 <= rsi <= 70:
                tech_score += Decimal('10')
        
        if criteria.above_sma_20 and market_data.get('sma_20') and quote.last:
            if quote.last > market_data['sma_20']:
                tech_score += Decimal('25')
        
        score += tech_score * Decimal('0.15')
        factors += 1
        
        # Market cap score (10% weight)
        market_cap = market_data.get('market_cap')
        if market_cap:
            market_cap_millions = market_cap / Decimal('1000000')
            # Prefer mid-cap stocks (500M - 2B)
            if 500 <= market_cap_millions <= 2000:
                cap_score = 100
            elif 100 <= market_cap_millions <= 5000:
                cap_score = 80
            else:
                cap_score = 60
            score += Decimal(str(cap_score)) * Decimal('0.10')
            factors += 1
        
        if factors > 0:
            return min(100, max(0, score))
        
        return Decimal('50')  # Neutral score if no factors available
    
    def _get_universe_symbols(self, universe: str, criteria: Optional[ScreeningCriteria] = None, max_symbols: Optional[int] = None) -> List[str]:
        """Get symbols for a predefined universe."""
        
        # Check if EODHD screening is requested and available
        if universe == "EODHD_PMCC" and self.eodhd_client:
            return self._get_eodhd_pmcc_universe(criteria, max_symbols)
        
        # Simplified universe definitions - in practice would fetch from API
        universes = {
            "SP500": [
                "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "BRK.B",
                "UNH", "JNJ", "JPM", "V", "PG", "HD", "MA", "CVX", "LLY", "ABBV",
                "PFE", "KO", "AVGO", "PEP", "TMO", "COST", "WMT", "MRK", "DHR",
                "VZ", "ABT", "ADBE", "ACN", "LIN", "NKE", "TXN", "BMY", "QCOM",
                "ORCL", "WFC", "PM", "UPS", "RTX", "HON", "LOW", "SBUX", "NEE",
                "AMD", "IBM", "CRM", "MDT", "INTU", "C", "GS", "CAT", "BA"
            ],
            "NASDAQ100": [
                "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "AVGO",
                "ADBE", "PEP", "COST", "CMCSA", "NFLX", "PYPL", "INTC", "QCOM",
                "TXN", "AMAT", "INTU", "AMD", "MU", "ISRG", "ADP", "GILD", "BKNG",
                "MDLZ", "CSX", "REGN", "VRTX", "LRCX", "FISV", "ATVI", "ADI",
                "KLAC", "MELI", "CHTR", "MRNA", "BIIB", "KDP", "SNPS", "MAR",
                "ORLY", "FTNT", "MCHP", "IDXX", "CTAS", "NXPI", "PAYX", "WDAY"
            ],
            "DEMO": [
                "AAPL", "MSFT", "GOOGL", "TSLA", "AMD", "NVDA", "META", "NFLX"
            ]
        }
        
        return universes.get(universe, universes["DEMO"])
    
    def _get_eodhd_pmcc_universe(self, criteria: Optional[ScreeningCriteria] = None, max_symbols: Optional[int] = None) -> List[str]:
        """
        Get PMCC-suitable universe from EODHD screener API.
        
        Args:
            criteria: Screening criteria to determine market cap range
            max_symbols: Maximum number of symbols to retrieve
            
        Returns:
            List of stock symbols from EODHD screener
        """
        if not self.eodhd_client:
            self.logger.warning("EODHD client not available, falling back to demo universe")
            return self._get_universe_symbols("DEMO")
        
        try:
            if criteria is None:
                criteria = ScreeningCriteria()
            
            # Market cap values need to be converted from millions to dollars
            min_market_cap = int(criteria.min_market_cap * 1_000_000)  # Convert millions to dollars
            max_market_cap = int(criteria.max_market_cap * 1_000_000)  # Convert millions to dollars
            min_volume = criteria.min_daily_volume if criteria.min_daily_volume else 100_000
            
            # Determine the limit to use
            limit = max_symbols if max_symbols else 500
            
            self.logger.info(f"Fetching PMCC universe with market cap ${min_market_cap:,} - ${max_market_cap:,}, min volume {min_volume:,}")
            self.logger.info(f"EODHD API limit will be set to {limit} (will paginate if >500)")
            self.logger.info(f"Using sync_client.screen_by_market_cap with limit={limit}")
            
            # Use sync EODHD client instead of async
            sync_client = self._get_sync_eodhd_client()
            if not sync_client:
                self.logger.error("Failed to create sync EODHD client")
                return self._get_universe_symbols("DEMO")
            
            # Call screen_by_market_cap directly on sync client
            # EODHD API will handle pagination if limit > 500
            response = sync_client.screen_by_market_cap(
                min_market_cap=min_market_cap,
                max_market_cap=max_market_cap,
                min_volume=min_volume,
                limit=limit
            )
            
            if response.is_success and response.data:
                # Extract symbols from response
                symbols = []
                if hasattr(response.data, 'get_symbols'):
                    symbols = response.data.get_symbols()
                elif hasattr(response.data, 'results'):
                    # Handle list of results
                    for stock in response.data.results:
                        if hasattr(stock, 'code'):
                            symbols.append(stock.code)
                        elif isinstance(stock, dict) and 'code' in stock:
                            symbols.append(stock['code'])
                elif isinstance(response.data, list):
                    # Handle direct list response
                    for stock in response.data:
                        if hasattr(stock, 'code'):
                            symbols.append(stock.code)
                        elif isinstance(stock, dict) and 'code' in stock:
                            symbols.append(stock['code'])
                
                if symbols:
                    self.logger.info(f"Retrieved {len(symbols)} symbols from EODHD screener")
                    return symbols
                else:
                    self.logger.warning("No symbols extracted from EODHD response, using demo universe")
                    return self._get_universe_symbols("DEMO")
            else:
                self.logger.warning(f"EODHD screener failed: {response.error}, using demo universe")
                return self._get_universe_symbols("DEMO")
                
        except Exception as e:
            self.logger.error(f"Error fetching EODHD universe: {e}")
            # Fallback to predefined universe
            return self._get_universe_symbols("SP500")
    
    # Removed async method - now using sync client directly in _get_eodhd_pmcc_universe