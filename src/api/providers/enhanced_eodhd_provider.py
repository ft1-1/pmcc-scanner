"""
Enhanced EODHD provider implementation using the official EODHD Python library.

This provider implements the DataProvider interface using the official EODHD library
while maintaining compatibility with the existing provider factory pattern. It adds
support for fundamental data, calendar events, technical indicators, and risk metrics
for AI-enhanced PMCC analysis.

Key features:
- Uses official EODHD Python library for improved reliability
- Comprehensive fundamental data collection
- Calendar events (earnings, dividends) integration
- Technical indicators and risk metrics
- Maintains backward compatibility with existing EODHD provider
- Full integration with provider factory and circuit breaker patterns
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, date, timedelta
from decimal import Decimal
import time

# Official EODHD library
from eodhd import APIClient as EODHDAPIClient

from src.api.data_provider import DataProvider, ProviderType, ProviderStatus, ProviderHealth, ScreeningCriteria
from src.models.api_models import (
    StockQuote, OptionChain, OptionContract, APIResponse, APIError, APIStatus, 
    RateLimitHeaders, ProviderMetadata, EODHDScreenerResponse,
    FundamentalMetrics, CalendarEvent, TechnicalIndicators, RiskMetrics, EnhancedStockData
)

logger = logging.getLogger(__name__)


class EnhancedEODHDProvider(DataProvider):
    """
    Enhanced EODHD implementation using the official EODHD Python library.
    
    This provider extends the basic EODHD functionality with comprehensive
    fundamental data, calendar events, technical indicators, and risk metrics
    for AI-enhanced PMCC analysis.
    """
    
    def __init__(self, provider_type: ProviderType, config: Dict[str, Any]):
        """
        Initialize enhanced EODHD provider.
        
        Args:
            provider_type: Should be ProviderType.EODHD
            config: Configuration dictionary with API credentials and settings
        """
        super().__init__(provider_type, config)
        
        # Initialize official EODHD client
        api_token = config.get('api_token')
        if not api_token:
            raise ValueError("EODHD API token is required")
        
        self.client = EODHDAPIClient(api_token)
        
        # Provider capabilities - FUNDAMENTALS AND ENHANCED DATA ONLY, NO OPTIONS
        self._supported_operations = {
            'get_stock_quote', 'get_stock_quotes', 'screen_stocks',
            # Enhanced operations for AI analysis
            'get_fundamental_data', 'get_calendar_events', 
            'get_technical_indicators', 'get_risk_metrics',
            'get_enhanced_stock_data'
        }
        
        # Rate limiting tracking
        self._last_rate_limit: Optional[RateLimitHeaders] = None
        self._request_count = 0
        self._error_count = 0
        
        # Cache settings
        self._caching_enabled = config.get('enable_caching', True)
        self._cache_ttl = config.get('cache_ttl_hours', 24)
        self._fundamental_cache: Dict[str, Dict[str, Any]] = {}
        self._calendar_cache: Dict[str, List[CalendarEvent]] = {}
        self._technical_cache: Dict[str, TechnicalIndicators] = {}
        
        logger.info("Enhanced EODHD provider initialized with official library")
    
    def get_last_trading_day(self, today: Optional[datetime] = None) -> str:
        """Get the most recent trading day, accounting for market holidays"""
        if today is None:
            today = datetime.now()
        
        # Look back 10 days to catch any holidays
        ten_days_ago = (today - timedelta(days=10)).strftime('%Y-%m-%d')
        today_str = today.strftime('%Y-%m-%d')
        
        try:
            # Get market holidays in the recent period
            holidays_data = self.client.get_details_trading_hours_stock_market_holidays(
                code="US", 
                from_date=ten_days_ago, 
                to_date=today_str
            )
            
            # Extract holiday dates
            holiday_dates = set()
            if holidays_data and isinstance(holidays_data, list):
                for holiday in holidays_data:
                    if isinstance(holiday, dict) and 'date' in holiday:
                        holiday_dates.add(holiday['date'])
            elif holidays_data and isinstance(holidays_data, dict) and 'date' in holidays_data:
                holiday_dates.add(holidays_data['date'])
        except Exception as e:
            logger.warning(f"Could not fetch holiday data: {e}")
            holiday_dates = set()
        
        # Find last trading day
        current_date = today
        while True:
            current_date_str = current_date.strftime('%Y-%m-%d')
            
            # Skip weekends (Saturday=5, Sunday=6) and holidays
            if current_date.weekday() < 5 and current_date_str not in holiday_dates:
                return current_date_str
                
            current_date = current_date - timedelta(days=1)
            
            # Safety check - don't go back more than 10 days
            if (today - current_date).days > 10:
                break
        
        # Fallback to simple business day logic
        # Use timedelta instead of pandas BDay for fallback
        fallback_date = today
        while fallback_date.weekday() >= 5:  # Skip weekends
            fallback_date = fallback_date - timedelta(days=1)
        return fallback_date.strftime('%Y-%m-%d')
    
    def get_trading_dates(self) -> Dict[str, str]:
        """Get all the dynamic dates needed for API calls"""
        today = datetime.now()
        last_trading_day = self.get_last_trading_day(today)
        last_trading_date = datetime.strptime(last_trading_day, '%Y-%m-%d')
        
        return {
            'today': last_trading_day,
            'thirty_days_ago': (last_trading_date - timedelta(days=30)).strftime('%Y-%m-%d'),
            'sixty_days_ago': (last_trading_date - timedelta(days=60)).strftime('%Y-%m-%d'),
            'six_months_ago': (last_trading_date - timedelta(days=180)).strftime('%Y-%m-%d'),
            'one_year_ago': (last_trading_date - timedelta(days=365)).strftime('%Y-%m-%d'),
            'hundred_days_ago': (last_trading_date - timedelta(days=100)).strftime('%Y-%m-%d')
        }
    
    async def health_check(self) -> ProviderHealth:
        """
        Perform health check using a lightweight API call.
        
        Returns:
            ProviderHealth with current status
        """
        start_time = time.time()
        
        try:
            # Use a simple call to check API connectivity
            # Get fundamental data for a well-known stock (AAPL) as health check
            response = await asyncio.get_event_loop().run_in_executor(
                None, self.client.get_fundamentals_data, 'AAPL.US'
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            if response and isinstance(response, dict):
                self._health.status = ProviderStatus.HEALTHY
                self._health.latency_ms = latency_ms
                self._health.error_message = None
            else:
                self._health.status = ProviderStatus.DEGRADED
                self._health.latency_ms = latency_ms
                self._health.error_message = "API returned empty response"
                
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self._health.status = ProviderStatus.UNHEALTHY
            self._health.latency_ms = latency_ms
            self._health.error_message = f"Health check failed: {str(e)}"
            logger.error(f"Enhanced EODHD health check failed: {e}")
        
        self._health.last_check = datetime.now()
        return self._health
    
    async def _create_enhanced_stock_quote(self, symbol: str, quote_data: Dict[str, Any], historical_data: Optional[Any] = None) -> StockQuote:
        """
        Create an enhanced StockQuote with calculated attributes.
        
        Args:
            symbol: Stock symbol
            quote_data: Basic quote data
            historical_data: Historical data for calculating change values
            
        Returns:
            StockQuote with all available attributes populated
        """
        try:
            # Calculate change and change_percent if we have historical data
            change = None
            change_percent = None
            previous_close = None
            
            if historical_data and hasattr(historical_data, '__len__') and len(historical_data) > 1:
                # Get previous day data for change calculation
                if hasattr(historical_data, 'iloc'):
                    # DataFrame response
                    prev_data = historical_data.iloc[-2]  # Second to last entry
                    previous_close = float(prev_data.get('adjusted_close', prev_data.get('close', 0)))
                elif isinstance(historical_data, list) and len(historical_data) > 1:
                    # List response
                    prev_data = historical_data[-2]
                    previous_close = float(prev_data.get('adjusted_close', prev_data.get('close', 0)))
                
                # Calculate change values
                if previous_close and previous_close > 0:
                    current_price = quote_data.get('last', 0)
                    if current_price > 0:
                        change = current_price - previous_close
                        change_percent = (change / previous_close) * 100
            
            # Get market cap from fundamentals if available (requires separate call)
            market_cap = None
            try:
                # This could be enhanced to fetch market cap from fundamentals
                # For now, we'll leave it as None and populate it elsewhere
                pass
            except Exception:
                pass
            
            # Create enhanced StockQuote
            quote = StockQuote(
                symbol=quote_data['symbol'],
                last=Decimal(str(quote_data['last'])),
                volume=quote_data.get('volume'),
                updated=quote_data.get('updated'),
                
                # Enhanced attributes
                change=Decimal(str(change)) if change is not None else None,
                change_percent=Decimal(str(change_percent)) if change_percent is not None else None,
                market_cap=Decimal(str(market_cap)) if market_cap is not None else None,
                previous_close=Decimal(str(previous_close)) if previous_close is not None else None
            )
            
            return quote
            
        except Exception as e:
            logger.warning(f"Error creating enhanced stock quote for {symbol}: {e}")
            # Fallback to basic quote
            return StockQuote(
                symbol=quote_data['symbol'],
                last=Decimal(str(quote_data['last'])),
                volume=quote_data.get('volume'),
                updated=quote_data.get('updated')
            )
    
    async def get_stock_quote(self, symbol: str) -> APIResponse:
        """
        Get real-time or delayed stock quote using EODHD live prices API with EOD fallback.
        
        Args:
            symbol: Stock symbol (e.g., "AAPL")
            
        Returns:
            APIResponse containing StockQuote data or error
        """
        start_time = time.time()
        
        try:
            symbol_with_exchange = f"{symbol}.US"
            
            # First try live stock prices for current quotes
            try:
                live_response = await asyncio.get_event_loop().run_in_executor(
                    None, self.client.get_live_stock_prices, symbol_with_exchange
                )
                
                if live_response and isinstance(live_response, dict) and symbol_with_exchange in live_response:
                    live_data = live_response[symbol_with_exchange]
                    quote_data = {
                        'symbol': symbol,
                        'last': float(live_data.get('close', live_data.get('price', 0))),
                        'volume': int(live_data.get('volume', 0)),
                        'updated': live_data.get('timestamp', live_data.get('date', None))
                    }
                    
                    # Create enhanced StockQuote with live data
                    quote = await self._create_enhanced_stock_quote(symbol, quote_data)
                    
                    latency_ms = (time.time() - start_time) * 1000
                    metadata = ProviderMetadata.for_eodhd(latency_ms)
                    self._request_count += 1
                    
                    return APIResponse(
                        status=APIStatus.OK,
                        data=quote,
                        provider_metadata=metadata
                    )
            except Exception as live_error:
                logger.warning(f"Live prices failed for {symbol}, falling back to EOD data: {live_error}")
            
            # Fallback to EOD historical data (most recent day)
            response = await asyncio.get_event_loop().run_in_executor(
                None, self.client.get_eod_historical_stock_market_data, 
                symbol_with_exchange, 'd', None, None, 'd'
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            if response is not None and hasattr(response, '__len__') and len(response) > 0:
                # Get the most recent trading day data - response is a DataFrame
                if hasattr(response, 'iloc'):
                    # DataFrame response
                    latest_data = response.iloc[-1]
                    quote_data = {
                        'symbol': symbol,
                        'last': float(latest_data.get('adjusted_close', latest_data.get('close', 0))),
                        'volume': int(latest_data.get('volume', 0)),
                        'updated': str(latest_data.get('date', ''))
                    }
                else:
                    # List/dict response (fallback)
                    latest_data = response[-1] if isinstance(response, list) else response
                    quote_data = {
                        'symbol': symbol,
                        'last': float(latest_data.get('adjusted_close', latest_data.get('close', 0))),
                        'volume': int(latest_data.get('volume', 0)),
                        'updated': str(latest_data.get('date', ''))
                    }
                
                # Validate data before creating quote
                if quote_data['last'] <= 0:
                    logger.warning(f"Invalid price data for {symbol}: {quote_data}")
                    return self._create_error_response(f"Invalid price data for symbol {symbol}")
                
                # Create enhanced StockQuote with historical data for change calculation
                quote = await self._create_enhanced_stock_quote(symbol, quote_data, response)
                
                metadata = ProviderMetadata.for_eodhd(latency_ms)
                self._request_count += 1
                
                return APIResponse(
                    status=APIStatus.OK,
                    data=quote,
                    provider_metadata=metadata
                )
            else:
                return self._create_error_response(f"No data found for symbol {symbol}")
                
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self._error_count += 1
            logger.error(f"Error getting stock quote for {symbol}: {e}")
            
            return self._create_error_response(
                f"Failed to get stock quote for {symbol}: {str(e)}"
            )
    
    async def get_stock_quotes(self, symbols: List[str]) -> APIResponse:
        """
        Get multiple stock quotes using concurrent EODHD EOD requests.
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            APIResponse containing list of StockQuote data or error
        """
        start_time = time.time()
        
        try:
            logger.info(f"Fetching EOD quotes for {len(symbols)} symbols using official EODHD library")
            
            async def get_quote_safe(symbol: str) -> tuple[str, Optional[StockQuote]]:
                try:
                    response = await self.get_stock_quote(symbol)
                    if response.is_success:
                        return symbol, response.data
                    else:
                        logger.warning(f"Failed to get quote for {symbol}: {response.error}")
                        return symbol, None
                except Exception as e:
                    logger.warning(f"Exception getting quote for {symbol}: {e}")
                    return symbol, None
            
            # Process symbols in batches to avoid overwhelming the API
            batch_size = 20
            all_quotes = []
            failed_symbols = []
            
            for i in range(0, len(symbols), batch_size):
                batch_symbols = symbols[i:i + batch_size]
                tasks = [get_quote_safe(symbol) for symbol in batch_symbols]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in results:
                    if isinstance(result, Exception):
                        logger.warning(f"Quote request failed with exception: {result}")
                        continue
                    
                    symbol, quote = result
                    if quote:
                        all_quotes.append(quote)
                    else:
                        failed_symbols.append(symbol)
                
                # Small delay between batches
                if i + batch_size < len(symbols):
                    await asyncio.sleep(0.3)  # 300ms delay for EODHD
            
            latency_ms = (time.time() - start_time) * 1000
            self._request_count += len(symbols)
            self._error_count += len(failed_symbols)
            
            if all_quotes:
                metadata = ProviderMetadata.for_eodhd(latency_ms)
                return APIResponse(
                    status=APIStatus.OK,
                    data=all_quotes,
                    provider_metadata=metadata
                )
            else:
                return self._create_error_response(
                    f"Failed to get quotes for all {len(symbols)} symbols"
                )
                
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self._error_count += len(symbols)
            logger.error(f"Error getting stock quotes: {e}")
            
            return self._create_error_response(
                f"Failed to get stock quotes: {str(e)}"
            )
    
    # OPTIONS OPERATIONS REMOVED - ENHANCED EODHD PROVIDER IS FUNDAMENTALS-ONLY
    # Options data should come from MarketData.app only
    
    async def screen_stocks(self, criteria: ScreeningCriteria) -> APIResponse:
        """
        Screen stocks using EODHD's native screener API with market cap range splitting.
        
        Args:
            criteria: Screening criteria
            
        Returns:
            APIResponse containing screening results or error
        """
        start_time = time.time()
        
        try:
            logger.info(f"[EnhancedEODHDProvider.screen_stocks] Called with criteria limit: {criteria.limit}")
            logger.info("Performing stock screening using official EODHD library")
            
            # Default to US exchanges if not specified
            exchanges = criteria.exchanges or ['NYSE', 'NASDAQ']
            
            all_results = []
            
            # Determine market cap ranges to query
            min_cap = int(criteria.min_market_cap) if criteria.min_market_cap else 50000000
            max_cap = int(criteria.max_market_cap) if criteria.max_market_cap else 5000000000
            
            # Split into market cap ranges to bypass the 1000 result limit
            market_cap_ranges = []
            if max_cap >= 4000000000:
                market_cap_ranges.append((4000000000, min(max_cap, 5000000000)))
            if max_cap >= 3000000000 and min_cap < 4000000000:
                market_cap_ranges.append((max(min_cap, 3000000000), min(max_cap, 4000000000)))
            if max_cap >= 2000000000 and min_cap < 3000000000:
                market_cap_ranges.append((max(min_cap, 2000000000), min(max_cap, 3000000000)))
            if max_cap >= 1000000000 and min_cap < 2000000000:
                market_cap_ranges.append((max(min_cap, 1000000000), min(max_cap, 2000000000)))
            if max_cap >= 500000000 and min_cap < 1000000000:
                market_cap_ranges.append((max(min_cap, 500000000), min(max_cap, 1000000000)))
            if max_cap >= 250000000 and min_cap < 500000000:
                market_cap_ranges.append((max(min_cap, 250000000), min(max_cap, 500000000)))
            if max_cap >= 100000000 and min_cap < 250000000:
                market_cap_ranges.append((max(min_cap, 100000000), min(max_cap, 250000000)))
            if min_cap < 100000000:
                market_cap_ranges.append((min_cap, min(max_cap, 100000000)))
            
            logger.info(f"Screening stocks in {len(market_cap_ranges)} market cap ranges to bypass API limits")
            
            for range_min, range_max in market_cap_ranges:
                range_label = f"${range_min/1000000:.0f}M-${range_max/1000000:.0f}M"
                
                for exchange in exchanges:
                    try:
                        # Build filters for this specific market cap range and exchange
                        range_filters = [
                            ['market_capitalization', '>=', range_min],
                            ['market_capitalization', '<=', range_max]
                        ]
                        if criteria.min_volume:
                            range_filters.append(['avgvol_200d', '>=', criteria.min_volume])
                        range_filters.append(['exchange', '=', exchange])
                        
                        logger.info(f"Screening {exchange} stocks in {range_label} range...")
                        
                        offset = 0
                        max_per_request = 100  # Use smaller batches
                        range_results = []
                        
                        while offset <= 999:  # EODHD API has a maximum offset of 999
                            # Call the method with keyword arguments via lambda
                            response = await asyncio.get_event_loop().run_in_executor(
                                None, 
                                lambda: self.client.stock_market_screener(
                                    sort='market_capitalization.desc',
                                    filters=range_filters,
                                    limit=max_per_request,
                                    offset=offset
                                )
                            )
                            
                            if response and isinstance(response, dict) and 'data' in response:
                                batch_results = response['data']
                                if not batch_results:
                                    break  # No more results
                                
                                for stock_data in batch_results:
                                    try:
                                        from src.models.api_models import EODHDScreenerResult
                                        result = EODHDScreenerResult.from_api_response(stock_data)
                                        range_results.append(result)
                                    except Exception as e:
                                        logger.warning(f"Error parsing screener result: {e}")
                                        continue
                                
                                # Check if we should continue
                                if len(batch_results) < max_per_request:
                                    break  # No more results available
                                    
                                offset += len(batch_results)
                                
                                # Small delay between requests to avoid rate limiting
                                await asyncio.sleep(0.1)
                            else:
                                break
                        
                        if range_results:
                            logger.info(f"  Found {len(range_results)} stocks in {exchange} {range_label}")
                            all_results.extend(range_results)
                        
                    except Exception as e:
                        logger.warning(f"Error screening {exchange} in range {range_label}: {e}")
                        continue
            
            latency_ms = (time.time() - start_time) * 1000
            self._request_count += len(exchanges) * len(market_cap_ranges)
            
            if all_results:
                logger.info(f"Total stocks retrieved across all ranges: {len(all_results)}")
                
                # Sort by market cap descending
                all_results.sort(
                    key=lambda x: x.market_capitalization or Decimal('0'), 
                    reverse=True
                )
                
                # Apply final limit if specified
                if criteria.limit and len(all_results) > criteria.limit:
                    logger.info(f"Trimming results from {len(all_results)} to {criteria.limit}")
                    all_results = all_results[:criteria.limit]
                
                screener_response = EODHDScreenerResponse(
                    results=all_results,
                    total_count=len(all_results)
                )
                
                return APIResponse(
                    status=APIStatus.OK,
                    data=screener_response
                )
            else:
                logger.warning("No stocks found matching criteria")
                return APIResponse(
                    status=APIStatus.NO_DATA,
                    error=APIError(404, "No stocks found matching screening criteria")
                )
                
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"Error in screen_stocks: {e}")
            
            return APIResponse(
                status=APIStatus.ERROR,
                error=APIError(500, f"Screening error: {str(e)}")
            )
    
    # GREEKS OPERATIONS REMOVED - ENHANCED EODHD PROVIDER IS FUNDAMENTALS-ONLY
    # Greeks data should come from MarketData.app only
    
    def filter_fundamental_data(self, fundamentals: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Filter fundamental data to essential PMCC-relevant metrics"""
        if not fundamentals:
            return None
        
        try:
            # Extract key fundamental metrics for PMCC analysis
            filtered = {}
            
            if 'General' in fundamentals:
                general = fundamentals['General']
                filtered['company_info'] = {
                    'name': general.get('Name'),
                    'sector': general.get('Sector'),
                    'industry': general.get('Industry'),
                    'market_cap_mln': general.get('MarketCapitalization', 0) / 1000000 if general.get('MarketCapitalization') else None,
                    'employees': general.get('FullTimeEmployees'),
                    'description': general.get('Description', '')[:300]  # Brief description for context
                }
            
            if 'Highlights' in fundamentals:
                highlights = fundamentals['Highlights']
                filtered['financial_health'] = {
                    # Profitability metrics
                    'eps_ttm': highlights.get('EarningsShare'),
                    'profit_margin': highlights.get('ProfitMargin'),
                    'operating_margin': highlights.get('OperatingMarginTTM'),
                    'roe': highlights.get('ReturnOnEquityTTM'),
                    'roa': highlights.get('ReturnOnAssetsTTM'),
                    
                    # Growth metrics
                    'revenue_growth_yoy': highlights.get('QuarterlyRevenueGrowthYOY'),
                    'earnings_growth_yoy': highlights.get('QuarterlyEarningsGrowthYOY'),
                    'eps_estimate_current_year': highlights.get('EPSEstimateCurrentYear'),
                    'eps_estimate_next_year': highlights.get('EPSEstimateNextYear'),
                    
                    # Dividend information (critical for PMCC)
                    'dividend_yield': highlights.get('DividendYield'),
                    'dividend_per_share': highlights.get('DividendShare'),
                    
                    # Revenue and earnings
                    'revenue_ttm': highlights.get('RevenueTTM'),
                    'revenue_per_share': highlights.get('RevenuePerShareTTM'),
                    'most_recent_quarter': highlights.get('MostRecentQuarter')
                }
            
            if 'Valuation' in fundamentals:
                valuation = fundamentals['Valuation']
                filtered['valuation_metrics'] = {
                    'pe_ratio': valuation.get('TrailingPE'),
                    'forward_pe': valuation.get('ForwardPE'),
                    'price_to_sales': valuation.get('PriceSalesTTM'),
                    'price_to_book': valuation.get('PriceBookMRQ'),
                    'enterprise_value': valuation.get('EnterpriseValue'),
                    'ev_to_revenue': valuation.get('EnterpriseValueRevenue'),
                    'ev_to_ebitda': valuation.get('EnterpriseValueEbitda')
                }
            
            if 'Technicals' in fundamentals:
                technicals = fundamentals['Technicals']
                filtered['stock_technicals'] = {
                    'beta': technicals.get('Beta'),
                    '52_week_high': technicals.get('52WeekHigh'),
                    '52_week_low': technicals.get('52WeekLow'),
                    '50_day_ma': technicals.get('50DayMA'),
                    '200_day_ma': technicals.get('200DayMA'),
                    'short_interest': technicals.get('ShortPercent'),
                    'short_ratio': technicals.get('ShortRatio')
                }
            
            if 'SplitsDividends' in fundamentals:
                dividends = fundamentals['SplitsDividends']
                filtered['dividend_info'] = {
                    'forward_dividend_rate': dividends.get('ForwardAnnualDividendRate'),
                    'forward_dividend_yield': dividends.get('ForwardAnnualDividendYield'),
                    'payout_ratio': dividends.get('PayoutRatio'),
                    'dividend_date': dividends.get('DividendDate'),
                    'ex_dividend_date': dividends.get('ExDividendDate'),
                    'last_split_date': dividends.get('LastSplitDate'),
                    'last_split_factor': dividends.get('LastSplitFactor')
                }
            
            if 'AnalystRatings' in fundamentals:
                ratings = fundamentals['AnalystRatings']
                filtered['analyst_sentiment'] = {
                    'avg_rating': ratings.get('Rating'),  # 1=Strong Buy, 5=Strong Sell
                    'target_price': ratings.get('TargetPrice'),
                    'strong_buy': ratings.get('StrongBuy'),
                    'buy': ratings.get('Buy'),
                    'hold': ratings.get('Hold'),
                    'sell': ratings.get('Sell'),
                    'strong_sell': ratings.get('StrongSell')
                }
            
            # Add institutional ownership summary (indicates confidence)
            if 'SharesStats' in fundamentals:
                shares = fundamentals['SharesStats']
                filtered['ownership_structure'] = {
                    'shares_outstanding': shares.get('SharesOutstanding'),
                    'percent_institutions': shares.get('PercentInstitutions'),
                    'percent_insiders': shares.get('PercentInsiders'),
                    'shares_float': shares.get('SharesFloat')
                }
            
            # Extract key financial statement data (most recent quarter)
            if 'Financials' in fundamentals:
                financials = fundamentals['Financials']
                
                # Balance Sheet - Financial Strength Indicators
                if 'Balance_Sheet' in financials and 'quarterly' in financials['Balance_Sheet']:
                    bs_data = financials['Balance_Sheet']['quarterly']
                    # Get most recent quarter
                    latest_quarter = max(bs_data.keys()) if bs_data else None
                    if latest_quarter:
                        bs = bs_data[latest_quarter]
                        filtered['balance_sheet'] = {
                            'total_assets': float(bs.get('totalAssets', 0)) / 1000000 if bs.get('totalAssets') else None,  # Convert to millions
                            'total_debt': float(bs.get('shortLongTermDebtTotal', 0)) / 1000000 if bs.get('shortLongTermDebtTotal') else None,
                            'cash_and_equivalents': float(bs.get('cashAndEquivalents', 0)) / 1000000 if bs.get('cashAndEquivalents') else None,
                            'net_debt': float(bs.get('netDebt', 0)) / 1000000 if bs.get('netDebt') else None,
                            'working_capital': float(bs.get('netWorkingCapital', 0)) / 1000000 if bs.get('netWorkingCapital') else None,
                            'shareholders_equity': float(bs.get('totalStockholderEquity', 0)) / 1000000 if bs.get('totalStockholderEquity') else None,
                            'debt_to_equity': None,  # Will calculate if both values exist
                            'quarter_date': latest_quarter
                        }
                        # Calculate debt-to-equity ratio
                        if filtered['balance_sheet']['total_debt'] and filtered['balance_sheet']['shareholders_equity']:
                            filtered['balance_sheet']['debt_to_equity'] = round(
                                filtered['balance_sheet']['total_debt'] / filtered['balance_sheet']['shareholders_equity'], 2
                            )
                
                # Income Statement - Profitability and Revenue Trends
                if 'Income_Statement' in financials and 'quarterly' in financials['Income_Statement']:
                    is_data = financials['Income_Statement']['quarterly']
                    # Get most recent quarter
                    latest_quarter = max(is_data.keys()) if is_data else None
                    if latest_quarter:
                        is_ = is_data[latest_quarter]
                        filtered['income_statement'] = {
                            'total_revenue': float(is_.get('totalRevenue', 0)) / 1000000 if is_.get('totalRevenue') else None,
                            'gross_profit': float(is_.get('grossProfit', 0)) / 1000000 if is_.get('grossProfit') else None,
                            'operating_income': float(is_.get('operatingIncome', 0)) / 1000000 if is_.get('operatingIncome') else None,
                            'net_income': float(is_.get('netIncome', 0)) / 1000000 if is_.get('netIncome') else None,
                            'ebitda': float(is_.get('ebitda', 0)) / 1000000 if is_.get('ebitda') else None,
                            'gross_margin': None,  # Will calculate
                            'operating_margin': None,  # Will calculate
                            'net_margin': None,  # Will calculate
                            'quarter_date': latest_quarter
                        }
                        # Calculate margins
                        if filtered['income_statement']['total_revenue'] and filtered['income_statement']['total_revenue'] > 0:
                            revenue = filtered['income_statement']['total_revenue']
                            if filtered['income_statement']['gross_profit']:
                                filtered['income_statement']['gross_margin'] = round(
                                    (filtered['income_statement']['gross_profit'] / revenue) * 100, 2
                                )
                            if filtered['income_statement']['operating_income']:
                                filtered['income_statement']['operating_margin'] = round(
                                    (filtered['income_statement']['operating_income'] / revenue) * 100, 2
                                )
                            if filtered['income_statement']['net_income']:
                                filtered['income_statement']['net_margin'] = round(
                                    (filtered['income_statement']['net_income'] / revenue) * 100, 2
                                )
                
                # Cash Flow - Critical for PMCC (company sustainability)
                if 'Cash_Flow' in financials and 'quarterly' in financials['Cash_Flow']:
                    cf_data = financials['Cash_Flow']['quarterly']
                    # Get most recent quarter
                    latest_quarter = max(cf_data.keys()) if cf_data else None
                    if latest_quarter:
                        cf = cf_data[latest_quarter]
                        filtered['cash_flow'] = {
                            'operating_cash_flow': float(cf.get('totalCashFromOperatingActivities', 0)) / 1000000 if cf.get('totalCashFromOperatingActivities') else None,
                            'free_cash_flow': float(cf.get('freeCashFlow', 0)) / 1000000 if cf.get('freeCashFlow') else None,  # Key metric for email report
                            'capex': float(cf.get('capitalExpenditures', 0)) / 1000000 if cf.get('capitalExpenditures') else None,
                            'net_income': float(cf.get('netIncome', 0)) / 1000000 if cf.get('netIncome') else None,
                            'cash_change': float(cf.get('changeInCash', 0)) / 1000000 if cf.get('changeInCash') else None,
                            'dividends_paid': float(cf.get('dividendsPaid', 0)) / 1000000 if cf.get('dividendsPaid') else None,
                            'quarter_date': latest_quarter
                        }
            
            return filtered
            
        except Exception as e:
            logger.error(f"Error filtering fundamental data: {e}")
            return fundamentals  # Return original if filtering fails
    
    async def get_economic_events(self, date_from: Optional[str] = None, date_to: Optional[str] = None) -> APIResponse:
        """Get economic events data (US macro context)"""
        start_time = time.time()
        
        try:
            dates = self.get_trading_dates()
            if not date_from:
                date_from = dates['six_months_ago']
            if not date_to:
                date_to = dates['today']
            
            logger.debug(f"Fetching economic events from {date_from} to {date_to}")
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                self.client.get_economic_events_data,
                date_from,
                date_to,
                'US',
                'mom',
                0,
                30
            )
            
            latency_ms = (time.time() - start_time) * 1000
            self._request_count += 1
            
            metadata = ProviderMetadata.for_eodhd(latency_ms)
            return APIResponse(
                status=APIStatus.OK,
                data=response,
                provider_metadata=metadata
            )
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self._error_count += 1
            logger.error(f"Error getting economic events: {e}")
            
            return self._create_error_response(
                f"Failed to get economic events: {str(e)}"
            )
    
    async def get_company_news(self, symbol: str, date_from: Optional[str] = None, date_to: Optional[str] = None, limit: int = 5) -> APIResponse:
        """Get recent company news (last 30 days)"""
        start_time = time.time()
        
        try:
            dates = self.get_trading_dates()
            if not date_from:
                date_from = dates['thirty_days_ago']
            if not date_to:
                date_to = dates['today']
            
            logger.debug(f"Fetching news for {symbol} from {date_from} to {date_to}")
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                self.client.financial_news,
                f'{symbol}.US',
                None,
                date_from,
                date_to,
                limit,
                0
            )
            
            latency_ms = (time.time() - start_time) * 1000
            self._request_count += 1
            
            metadata = ProviderMetadata.for_eodhd(latency_ms)
            return APIResponse(
                status=APIStatus.OK,
                data=response,
                provider_metadata=metadata
            )
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self._error_count += 1
            logger.error(f"Error getting news for {symbol}: {e}")
            
            return self._create_error_response(
                f"Failed to get news for {symbol}: {str(e)}"
            )
    
    async def get_live_price(self, symbol: str) -> APIResponse:
        """Get live price data for a stock"""
        start_time = time.time()
        
        try:
            dates = self.get_trading_dates()
            
            logger.debug(f"Fetching live price for {symbol}")
            
            # Call with positional arguments in correct order
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.get_live_stock_prices(
                    ticker=symbol,
                    date_from=dates['today'],
                    date_to=dates['today']
                )
            )
            
            latency_ms = (time.time() - start_time) * 1000
            self._request_count += 1
            
            metadata = ProviderMetadata.for_eodhd(latency_ms)
            return APIResponse(
                status=APIStatus.OK,
                data=response,
                provider_metadata=metadata
            )
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self._error_count += 1
            logger.error(f"Error getting live price for {symbol}: {e}")
            
            return self._create_error_response(
                f"Failed to get live price for {symbol}: {str(e)}"
            )
    
    async def get_earnings_data(self, symbol: str, date_from: Optional[str] = None, date_to: Optional[str] = None) -> APIResponse:
        """Get earnings data for a stock including future earnings"""
        start_time = time.time()
        
        try:
            dates = self.get_trading_dates()
            if not date_from:
                # Go back 15 months to get full year of historical earnings + buffer
                date_from = (datetime.now() - timedelta(days=450)).strftime('%Y-%m-%d')
            if not date_to:
                # Extend to 120 days in the future to capture more upcoming earnings
                date_to = (datetime.now() + timedelta(days=120)).strftime('%Y-%m-%d')
            
            logger.debug(f"Fetching earnings data for {symbol} from {date_from} to {date_to}")
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                self.client.get_upcoming_earnings_data,
                date_from,
                date_to,
                symbol
            )
            
            latency_ms = (time.time() - start_time) * 1000
            self._request_count += 1
            
            metadata = ProviderMetadata.for_eodhd(latency_ms)
            return APIResponse(
                status=APIStatus.OK,
                data=response,
                provider_metadata=metadata
            )
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self._error_count += 1
            logger.error(f"Error getting earnings data for {symbol}: {e}")
            
            return self._create_error_response(
                f"Failed to get earnings data for {symbol}: {str(e)}"
            )
    
    async def get_historical_prices(self, symbol: str, period: str = 'd', date_from: Optional[str] = None, date_to: Optional[str] = None) -> APIResponse:
        """Get historical price data (30 days default)"""
        start_time = time.time()
        
        try:
            dates = self.get_trading_dates()
            if not date_from:
                date_from = dates['thirty_days_ago']
            if not date_to:
                date_to = dates['today']
            
            logger.debug(f"Fetching historical prices for {symbol} from {date_from} to {date_to}")
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                self.client.get_eod_historical_stock_market_data,
                symbol,
                period,
                date_from,
                date_to,
                'd'
            )
            
            latency_ms = (time.time() - start_time) * 1000
            self._request_count += 1
            
            metadata = ProviderMetadata.for_eodhd(latency_ms)
            return APIResponse(
                status=APIStatus.OK,
                data=response,
                provider_metadata=metadata
            )
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self._error_count += 1
            logger.error(f"Error getting historical prices for {symbol}: {e}")
            
            return self._create_error_response(
                f"Failed to get historical prices for {symbol}: {str(e)}"
            )
    
    async def get_sentiment_data(self, symbol: str, date_from: Optional[str] = None, date_to: Optional[str] = None) -> APIResponse:
        """Get sentiment analysis data"""
        start_time = time.time()
        
        try:
            dates = self.get_trading_dates()
            if not date_from:
                date_from = dates['thirty_days_ago']
            if not date_to:
                date_to = dates['today']
            
            logger.debug(f"Fetching sentiment data for {symbol} from {date_from} to {date_to}")
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                self.client.get_sentiment,
                symbol,
                date_from,
                date_to
            )
            
            latency_ms = (time.time() - start_time) * 1000
            self._request_count += 1
            
            metadata = ProviderMetadata.for_eodhd(latency_ms)
            return APIResponse(
                status=APIStatus.OK,
                data=response,
                provider_metadata=metadata
            )
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self._error_count += 1
            logger.error(f"Error getting sentiment data for {symbol}: {e}")
            
            return self._create_error_response(
                f"Failed to get sentiment data for {symbol}: {str(e)}"
            )
    
    async def get_technical_indicators_comprehensive(self, symbol: str) -> APIResponse:
        """Get comprehensive technical indicators (RSI, volatility, ATR, beta)"""
        start_time = time.time()
        
        try:
            dates = self.get_trading_dates()
            
            logger.debug(f"Fetching technical indicators for {symbol}")
            
            technical_data = {}
            
            # List of indicators to try (beta excluded due to API issues)
            indicators = [
                {'name': 'rsi', 'function': 'rsi', 'period': 14, 'days_back': 60},
                {'name': 'volatility', 'function': 'volatility', 'period': 30, 'days_back': 60},
                {'name': 'atr', 'function': 'atr', 'period': 14, 'days_back': 60}
                # Beta indicator excluded - API returns "Incorrect value for fanction parameter" error
            ]
            
            for indicator in indicators:
                try:
                    logger.debug(f"  Fetching {indicator['name']}...")
                    days_back = (datetime.now() - timedelta(days=indicator['days_back'])).strftime('%Y-%m-%d')
                    
                    # Safe API call with parameter validation
                    try:
                        result = await asyncio.get_event_loop().run_in_executor(
                            None,
                            self.client.get_technical_indicator_data,
                            f'{symbol}.US',
                            indicator['function'],  # Ensure this is 'function' not 'fanction'
                            indicator['period'],
                            days_back,
                            dates['today'],
                            'd',
                            '0'
                        )
                    except Exception as api_error:
                        error_msg = str(api_error)
                        if 'fanction' in error_msg:
                            logger.error(f"  ✗ API parameter error for {indicator['name']}: {error_msg}")
                            logger.error(f"    Check EODHD library version and parameter names")
                        else:
                            logger.error(f"  ✗ API call failed for {indicator['name']}: {error_msg}")
                        result = None
                    
                    # Validate and normalize the result to ensure proper data structure
                    if result is not None:
                        if isinstance(result, str):
                            logger.warning(f"  ⚠ {indicator['name']} returned string instead of list: {result[:100]}...")
                            technical_data[indicator['name']] = None  # Set to None for string responses
                        elif isinstance(result, list) and len(result) > 0:
                            # Ensure all items in list are dictionaries
                            valid_items = []
                            for item in result:
                                if isinstance(item, dict):
                                    valid_items.append(item)
                                else:
                                    logger.warning(f"  ⚠ {indicator['name']} contains non-dict item: {type(item)}")
                            
                            if valid_items:
                                technical_data[indicator['name']] = valid_items
                                logger.debug(f"  ✓ {indicator['name']} collected successfully ({len(valid_items)} data points)")
                            else:
                                logger.warning(f"  ⚠ {indicator['name']} has no valid dictionary data")
                                technical_data[indicator['name']] = None
                        elif isinstance(result, dict):
                            # Single dictionary result - wrap in list for consistency
                            technical_data[indicator['name']] = [result]
                            logger.debug(f"  ✓ {indicator['name']} collected as single dict, wrapped in list")
                        else:
                            logger.warning(f"  ⚠ {indicator['name']} returned unexpected format: {type(result)}")
                            technical_data[indicator['name']] = None
                    else:
                        technical_data[indicator['name']] = None
                        logger.debug(f"  ⚠ {indicator['name']} returned None")
                    
                except Exception as e:
                    logger.warning(f"  ✗ Failed to fetch {indicator['name']}: {e}")
                    technical_data[indicator['name']] = None
            
            latency_ms = (time.time() - start_time) * 1000
            self._request_count += len(indicators)
            
            metadata = ProviderMetadata.for_eodhd(latency_ms)
            return APIResponse(
                status=APIStatus.OK,
                data=technical_data,
                provider_metadata=metadata
            )
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self._error_count += 1
            logger.error(f"Error getting technical indicators for {symbol}: {e}")
            
            return self._create_error_response(
                f"Failed to get technical indicators for {symbol}: {str(e)}"
            )
    
    async def get_comprehensive_enhanced_data(self, symbol: str) -> APIResponse:
        """Collect all 8 types of enhanced data for comprehensive analysis"""
        start_time = time.time()
        
        try:
            logger.info(f"Collecting comprehensive enhanced data for {symbol}")
            
            enhanced_data = {}
            
            # 1. Economic Events Data (US macro context)
            logger.debug("Fetching economic events...")
            econ_response = await self.get_economic_events()
            enhanced_data['economic_events'] = econ_response.data if econ_response.is_success else None
            
            # 2. Recent News
            logger.debug("Fetching recent news...")
            news_response = await self.get_company_news(symbol)
            enhanced_data['news'] = news_response.data if news_response.is_success else None
            
            # 3. Fundamental Data (filtered)
            logger.debug("Fetching fundamental data...")
            fund_response = await self.get_fundamental_data(symbol)
            enhanced_data['fundamentals'] = fund_response.data if fund_response.is_success else None
            
            # 4. Live Price
            logger.debug("Fetching live price...")
            price_response = await self.get_live_price(symbol)
            enhanced_data['live_price'] = price_response.data if price_response.is_success else None
            
            # 5. Earnings Data
            logger.debug("Fetching earnings data...")
            earnings_response = await self.get_earnings_data(symbol)
            enhanced_data['earnings'] = earnings_response.data if earnings_response.is_success else None
            
            # 6. Historical Price Data (30 days)
            logger.debug("Fetching historical prices...")
            hist_response = await self.get_historical_prices(symbol)
            enhanced_data['historical_prices'] = hist_response.data if hist_response.is_success else None
            
            # 7. Sentiment Analysis
            logger.debug("Fetching sentiment data...")
            sentiment_response = await self.get_sentiment_data(symbol)
            enhanced_data['sentiment'] = sentiment_response.data if sentiment_response.is_success else None
            
            # 8. Technical Indicators
            logger.debug("Fetching technical indicators...")
            tech_response = await self.get_technical_indicators_comprehensive(symbol)
            enhanced_data['technical_indicators'] = tech_response.data if tech_response.is_success else None
            
            # 9. Calendar Events (earnings dates, dividends, etc.)
            logger.debug("Fetching calendar events...")
            calendar_response = await self.get_calendar_events(symbol)
            enhanced_data['calendar_events'] = calendar_response.data if calendar_response.is_success else None
            
            latency_ms = (time.time() - start_time) * 1000
            self._request_count += 9  # 9 main data collection operations
            
            logger.info(f"✓ Successfully collected comprehensive enhanced data for {symbol}")
            
            metadata = ProviderMetadata.for_eodhd(latency_ms)
            return APIResponse(
                status=APIStatus.OK,
                data=enhanced_data,
                provider_metadata=metadata
            )
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self._error_count += 1
            logger.error(f"Error collecting comprehensive enhanced data for {symbol}: {e}")
            
            return self._create_error_response(
                f"Failed to collect comprehensive enhanced data for {symbol}: {str(e)}"
            )
    
    async def get_fundamental_data(self, symbol: str) -> APIResponse:
        """
        Get comprehensive fundamental data for a stock.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            APIResponse containing FundamentalMetrics data or error
        """
        start_time = time.time()
        
        try:
            # Check cache first
            if self._caching_enabled and symbol in self._fundamental_cache:
                cache_entry = self._fundamental_cache[symbol]
                cache_time = datetime.fromisoformat(cache_entry['timestamp'])
                if (datetime.now() - cache_time).total_seconds() < (self._cache_ttl * 3600):
                    logger.debug(f"Using cached fundamental data for {symbol}")
                    return cache_entry['response']
            
            logger.debug(f"Fetching fundamental data for {symbol}")
            
            # Use official EODHD library for fundamental data
            symbol_with_exchange = f"{symbol}.US"
            raw_response = await asyncio.get_event_loop().run_in_executor(
                None, self.client.get_fundamentals_data, symbol_with_exchange
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            if raw_response and isinstance(raw_response, dict):
                # Always use filtered dictionary approach for comprehensive data
                # This ensures we get all financial statement data (balance sheet, cash flow, etc.)
                fundamentals = self.filter_fundamental_data(raw_response)
                
                metadata = ProviderMetadata.for_eodhd(latency_ms)
                api_response = APIResponse(
                    status=APIStatus.OK,
                    data=fundamentals,
                    provider_metadata=metadata
                )
                
                # Cache the response
                if self._caching_enabled:
                    self._fundamental_cache[symbol] = {
                        'response': api_response,
                        'timestamp': datetime.now().isoformat()
                    }
                
                self._request_count += 1
                return api_response
            else:
                return self._create_error_response(f"No fundamental data found for symbol {symbol}")
                
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self._error_count += 1
            logger.error(f"Error getting fundamental data for {symbol}: {e}")
            
            return self._create_error_response(
                f"Failed to get fundamental data for {symbol}: {str(e)}"
            )
    
    async def get_calendar_events(
        self, 
        symbol: str, 
        event_types: Optional[List[str]] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> APIResponse:
        """
        Get calendar events (earnings, dividends) for a stock.
        
        Args:
            symbol: Stock symbol
            event_types: Types of events to fetch ('earnings', 'dividends')
            date_from: Start date for events
            date_to: End date for events
            
        Returns:
            APIResponse containing list of CalendarEvent data or error
        """
        start_time = time.time()
        
        try:
            logger.debug(f"Fetching calendar events for {symbol}")
            
            events = []
            event_types = event_types or ['earnings', 'dividends']
            
            # Set default date range if not provided
            if not date_from:
                date_from = date.today() - timedelta(days=30)
            if not date_to:
                date_to = date.today() + timedelta(days=90)
            
            # Fetch earnings events using upcoming earnings API
            if 'earnings' in event_types:
                try:
                    symbol_with_exchange = f"{symbol}.US"
                    earnings_response = await asyncio.get_event_loop().run_in_executor(
                        None, 
                        self.client.get_upcoming_earnings_data,
                        date_from.strftime('%Y-%m-%d'),
                        date_to.strftime('%Y-%m-%d'),
                        symbol_with_exchange
                    )
                    
                    if earnings_response and isinstance(earnings_response, dict):
                        # EODHD upcoming earnings returns a dict, not a list
                        earnings_list = earnings_response.get('earnings', [])
                        if isinstance(earnings_list, list):
                            for earnings_data in earnings_list:
                                if earnings_data.get('code') == symbol:
                                    try:
                                        event = CalendarEvent.from_eodhd_earnings_response(earnings_data)
                                        events.append(event)
                                    except Exception as parse_error:
                                        logger.warning(f"Error parsing earnings event for {symbol}: {parse_error}")
                                        continue
                        else:
                            # Handle single earnings data
                            if earnings_response.get('code') == symbol:
                                try:
                                    event = CalendarEvent.from_eodhd_earnings_response(earnings_response)
                                    events.append(event)
                                except Exception as parse_error:
                                    logger.warning(f"Error parsing single earnings event for {symbol}: {parse_error}")
                except Exception as e:
                    logger.warning(f"Error fetching earnings events for {symbol}: {e}")
            
            # Fetch dividend events using historical dividends API
            if 'dividends' in event_types:
                try:
                    symbol_with_exchange = f"{symbol}.US"
                    dividend_response = await asyncio.get_event_loop().run_in_executor(
                        None,
                        self.client.get_historical_dividends_data,
                        symbol_with_exchange,
                        date_from.strftime('%Y-%m-%d'),
                        date_to.strftime('%Y-%m-%d')
                    )
                    
                    if dividend_response:
                        # Handle both list and dict responses
                        dividend_list = dividend_response if isinstance(dividend_response, list) else [dividend_response]
                        
                        for dividend_data in dividend_list:
                            try:
                                # Historical dividends data structure may be different
                                event = CalendarEvent.from_eodhd_dividend_response(dividend_data)
                                events.append(event)
                            except Exception as parse_error:
                                logger.warning(f"Error parsing dividend event for {symbol}: {parse_error}")
                                continue
                except Exception as e:
                    logger.warning(f"Error fetching dividend events for {symbol}: {e}")
            
            latency_ms = (time.time() - start_time) * 1000
            self._request_count += len(event_types)
            
            # Sort events by date
            events.sort(key=lambda e: e.date)
            
            metadata = ProviderMetadata.for_eodhd(latency_ms)
            return APIResponse(
                status=APIStatus.OK,
                data=events,
                provider_metadata=metadata
            )
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self._error_count += 1
            logger.error(f"Error getting calendar events for {symbol}: {e}")
            
            return self._create_error_response(
                f"Failed to get calendar events for {symbol}: {str(e)}"
            )
    
    async def get_technical_indicators(self, symbol: str) -> APIResponse:
        """
        Get technical indicators for a stock.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            APIResponse containing TechnicalIndicators data or error
        """
        start_time = time.time()
        
        try:
            logger.debug(f"Fetching technical indicators for {symbol}")
            
            # Get raw fundamental data directly from EODHD API
            symbol_with_exchange = f"{symbol}.US"
            raw_response = await asyncio.get_event_loop().run_in_executor(
                None, self.client.get_fundamentals_data, symbol_with_exchange
            )
            
            if not raw_response or not isinstance(raw_response, dict):
                return self._create_error_response(
                    f"Failed to get fundamental data needed for technical indicators: {symbol}"
                )
            
            # Create technical indicators from raw EODHD data with error handling
            # In the future, this could be enhanced with actual technical API calls
            try:
                technical_indicators = TechnicalIndicators.from_eodhd_response(
                    raw_response, 
                    technicals_data=None  # Could be populated with technical API data
                )
            except Exception as conversion_error:
                logger.warning(f"Error creating technical indicators for {symbol}: {conversion_error}")
                # Return minimal technical indicators on conversion error
                technical_indicators = TechnicalIndicators(
                    symbol=symbol,
                    rsi=None,
                    moving_average_50=None,
                    moving_average_200=None,
                    bollinger_upper=None,
                    bollinger_lower=None,
                    macd=None,
                    volume_avg_10d=None,
                    support_level=None,
                    resistance_level=None
                )
            
            latency_ms = (time.time() - start_time) * 1000
            self._request_count += 1
            
            metadata = ProviderMetadata.for_eodhd(latency_ms)
            return APIResponse(
                status=APIStatus.OK,
                data=technical_indicators,
                provider_metadata=metadata
            )
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self._error_count += 1
            logger.error(f"Error getting technical indicators for {symbol}: {e}")
            
            return self._create_error_response(
                f"Failed to get technical indicators for {symbol}: {str(e)}"
            )
    
    async def get_risk_metrics(self, symbol: str) -> APIResponse:
        """
        Get risk assessment metrics for a stock.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            APIResponse containing RiskMetrics data or error
        """
        start_time = time.time()
        
        try:
            logger.debug(f"Fetching risk metrics for {symbol}")
            
            # Get raw fundamental data directly from EODHD API
            symbol_with_exchange = f"{symbol}.US"
            raw_response = await asyncio.get_event_loop().run_in_executor(
                None, self.client.get_fundamentals_data, symbol_with_exchange
            )
            
            if not raw_response or not isinstance(raw_response, dict):
                return self._create_error_response(
                    f"Failed to get fundamental data needed for risk metrics: {symbol}"
                )
            
            # Create risk metrics from raw EODHD data with error handling
            try:
                risk_metrics = RiskMetrics.from_eodhd_response(
                    raw_response,
                    analyst_data=None  # Could be enhanced with analyst recommendations API
                )
            except Exception as conversion_error:
                logger.warning(f"Error creating risk metrics for {symbol}: {conversion_error}")
                # Return minimal risk metrics on conversion error
                risk_metrics = RiskMetrics(
                    symbol=symbol,
                    beta=None,
                    volatility_30d=None,
                    volatility_90d=None,
                    sharpe_ratio=None,
                    max_drawdown=None,
                    var_95=None,
                    correlation_spy=None,
                    liquidity_score=None,
                    analyst_rating=None,
                    analyst_target_price=None
                )
            
            latency_ms = (time.time() - start_time) * 1000
            self._request_count += 1
            
            metadata = ProviderMetadata.for_eodhd(latency_ms)
            return APIResponse(
                status=APIStatus.OK,
                data=risk_metrics,
                provider_metadata=metadata
            )
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self._error_count += 1
            logger.error(f"Error getting risk metrics for {symbol}: {e}")
            
            return self._create_error_response(
                f"Failed to get risk metrics for {symbol}: {str(e)}"
            )
    
    async def get_enhanced_stock_data(self, symbol: str) -> APIResponse:
        """
        Get comprehensive enhanced stock data combining all available data sources.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            APIResponse containing EnhancedStockData with all available data
        """
        start_time = time.time()
        
        try:
            logger.debug(f"Fetching enhanced stock data for {symbol}")
            
            # Gather fundamental data only (NO OPTIONS)
            tasks = [
                self.get_stock_quote(symbol),
                self.get_fundamental_data(symbol),
                self.get_calendar_events(symbol),
                self.get_technical_indicators(symbol),
                self.get_risk_metrics(symbol)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            quote_response, fundamental_response, calendar_response, \
            technical_response, risk_response = results
            
            # Extract successful data (NO OPTIONS CHAIN)
            quote = quote_response.data if quote_response and quote_response.is_success else None
            fundamentals = fundamental_response.data if fundamental_response and fundamental_response.is_success else None
            calendar_events = calendar_response.data if calendar_response and calendar_response.is_success else []
            technical_indicators = technical_response.data if technical_response and technical_response.is_success else None
            risk_metrics = risk_response.data if risk_response and risk_response.is_success else None
            # Options chain must come from MarketData.app provider
            options_chain = None
            
            if not quote:
                return self._create_error_response(f"Failed to get basic quote data for {symbol}")
            
            # Enhance quote with market cap from fundamentals if available
            # Handle both FundamentalMetrics object and dictionary fallback
            if fundamentals:
                market_cap_mln = None
                if isinstance(fundamentals, dict):
                    # Dictionary fallback case
                    company_info = fundamentals.get('company_info', {})
                    market_cap_mln = company_info.get('market_cap_mln')
                elif hasattr(fundamentals, 'enterprise_value') and fundamentals.enterprise_value:
                    # FundamentalMetrics object case - estimate market cap from enterprise value
                    market_cap_mln = float(fundamentals.enterprise_value) / 1000000
                
                if market_cap_mln and not quote.market_cap:
                    quote.market_cap = Decimal(str(market_cap_mln * 1000000))  # Convert to actual market cap
            
            # Ensure fundamentals is a FundamentalMetrics object or None for EnhancedStockData
            if fundamentals and isinstance(fundamentals, dict):
                # This shouldn't happen with the new code, but handle as safety fallback
                logger.warning(f"Converting dictionary fundamentals to None for {symbol} - consider investigating")
                fundamentals = None
            
            # Create enhanced stock data (WITHOUT OPTIONS)
            enhanced_data = EnhancedStockData(
                quote=quote,
                fundamentals=fundamentals,  # Now guaranteed to be FundamentalMetrics object or None
                calendar_events=calendar_events or [],
                technical_indicators=technical_indicators,
                risk_metrics=risk_metrics,
                options_chain=None  # Options must come from MarketData.app provider
            )
            
            # Calculate completeness score
            enhanced_data.calculate_completeness_score()
            
            latency_ms = (time.time() - start_time) * 1000
            self._request_count += len(tasks)  # 5 requests: quote, fundamentals, calendar, technical, risk
            
            metadata = ProviderMetadata.for_eodhd(latency_ms)
            return APIResponse(
                status=APIStatus.OK,
                data=enhanced_data,
                provider_metadata=metadata
            )
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self._error_count += 1
            logger.error(f"Error getting enhanced stock data for {symbol}: {e}")
            
            return self._create_error_response(
                f"Failed to get enhanced stock data for {symbol}: {str(e)}"
            )
    
    def get_rate_limit_info(self) -> Optional[RateLimitHeaders]:
        """Get current rate limit status."""
        # EODHD handles rate limiting server-side
        return self._last_rate_limit
    
    def estimate_credits_required(self, operation: str, **kwargs) -> int:
        """
        Estimate API credits required for an operation.
        
        Args:
            operation: Type of operation
            **kwargs: Operation-specific parameters
            
        Returns:
            Estimated number of API credits required
        """
        if operation == 'screen_stocks':
            exchanges = kwargs.get('criteria', ScreeningCriteria()).exchanges or ['NYSE', 'NASDAQ']
            return len(exchanges) * 5  # 5 credits per exchange
        elif operation == 'get_fundamental_data':
            return 1
        elif operation == 'get_calendar_events':
            event_types = kwargs.get('event_types', ['earnings', 'dividends'])
            return len(event_types)
        elif operation == 'get_enhanced_stock_data':
            return 5  # Quote + fundamental + calendar + technical + risk (NO OPTIONS)
        elif operation == 'get_comprehensive_enhanced_data':
            return 11  # 9 main data types + overhead
        elif operation in ['get_economic_events', 'get_company_news', 'get_live_price', 'get_earnings_data', 'get_historical_prices', 'get_sentiment_data', 'get_technical_indicators_comprehensive']:
            return 1
        else:
            return 1
    
    def supports_operation(self, operation: str) -> bool:
        """Check if provider supports a specific operation."""
        return operation in self._supported_operations
    
    # OPTIONS-RELATED HELPER METHODS REMOVED - NOT NEEDED FOR FUNDAMENTALS-ONLY PROVIDER
    
    async def close(self):
        """Close the provider and cleanup resources."""
        # Clear caches
        if hasattr(self, '_fundamental_cache'):
            self._fundamental_cache.clear()
        if hasattr(self, '_calendar_cache'):
            self._calendar_cache.clear()
        if hasattr(self, '_technical_cache'):
            self._technical_cache.clear()
        
        logger.info("Enhanced EODHD provider closed")