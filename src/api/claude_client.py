"""
Claude AI API client implementation.

This client handles authentication, error handling, and retry logic
for the Anthropic Claude API for AI-enhanced PMCC analysis.

Key features:
- Bearer token authentication
- Comprehensive error handling with retry logic
- Support for enhanced PMCC opportunity analysis
- Rate limiting and cost tracking
- JSON response parsing with validation
"""

import asyncio
import logging
import os
import json
import time
from typing import Optional, List, Dict, Any, Union
from decimal import Decimal
from datetime import datetime, date, timedelta

import anthropic
from anthropic import AsyncAnthropic
from anthropic.types import Message

from src.models.api_models import (
    APIResponse, APIError, APIStatus, RateLimitHeaders, EnhancedStockData,
    ClaudeAnalysisResponse, PMCCOpportunityAnalysis
)

logger = logging.getLogger(__name__)


class ClaudeError(Exception):
    """Base exception for Claude API errors."""
    
    def __init__(self, message: str, code: Optional[int] = None, 
                 retry_after: Optional[float] = None):
        super().__init__(message)
        self.code = code
        self.retry_after = retry_after


class AuthenticationError(ClaudeError):
    """Authentication-related errors."""
    pass


class RateLimitError(ClaudeError):
    """Rate limit exceeded errors."""
    pass


class TokenLimitError(ClaudeError):
    """Token limit exceeded errors."""
    pass


class ClaudeClient:
    """
    Async client for Claude AI API.
    
    Handles authentication, error handling, and provides methods for 
    analyzing PMCC opportunities using AI-enhanced analysis.
    """
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 model: str = "claude-3-5-sonnet-20241022",
                 max_tokens: int = 4000,
                 temperature: float = 0.1,
                 timeout: float = 60.0,
                 max_retries: int = 3,
                 retry_backoff: float = 1.0):
        """
        Initialize Claude API client.
        
        Args:
            api_key: Anthropic API key. If None, will try to load from environment
            model: Claude model to use
            max_tokens: Maximum tokens in response
            temperature: Response randomness (0.0 to 1.0)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_backoff: Initial backoff delay for retries (exponential backoff)
        """
        # API configuration
        self.api_key = api_key or os.getenv('CLAUDE_API_KEY')
        if not self.api_key:
            raise AuthenticationError("No Claude API key provided. Set CLAUDE_API_KEY environment variable.")
        
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        
        # Initialize client
        self.client = AsyncAnthropic(api_key=self.api_key)
        
        # Request statistics
        self._stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_input_tokens': 0,
            'total_output_tokens': 0,
            'total_cost_estimate': 0.0
        }
        
        logger.info(f"Claude client initialized with model: {self.model}")
    
    async def analyze_pmcc_opportunities(
        self, 
        enhanced_stock_data: List[EnhancedStockData],
        market_context: Optional[Dict[str, Any]] = None
    ) -> APIResponse:
        """
        Analyze PMCC opportunities using Claude AI.
        
        Args:
            enhanced_stock_data: List of enhanced stock data for analysis
            market_context: Optional market context information
            
        Returns:
            APIResponse containing ClaudeAnalysisResponse or error
        """
        if not enhanced_stock_data:
            return APIResponse(
                status=APIStatus.ERROR,
                error=APIError(code=400, message="No stock data provided for analysis")
            )
        
        try:
            # Build the analysis prompt
            prompt = self._build_pmcc_analysis_prompt(enhanced_stock_data, market_context)
            
            # Execute the analysis with retry logic
            start_time = time.time()
            response = await self._execute_with_retry(prompt)
            processing_time_ms = (time.time() - start_time) * 1000
            
            # Parse the response
            analysis_response = self._parse_analysis_response(response, processing_time_ms)
            
            # Update statistics
            self._update_stats(response, success=True)
            
            return APIResponse(
                status=APIStatus.OK,
                data=analysis_response
            )
            
        except Exception as e:
            logger.error(f"Error analyzing PMCC opportunities: {e}")
            self._update_stats(None, success=False)
            
            return APIResponse(
                status=APIStatus.ERROR,
                error=APIError(
                    code=500,
                    message=f"Claude analysis failed: {str(e)}"
                )
            )
    
    async def analyze_single_opportunity(
        self,
        opportunity_data: Dict[str, Any],
        enhanced_stock_data: Dict[str, Any],
        market_context: Optional[Dict[str, Any]] = None
    ) -> APIResponse:
        """
        Analyze a single PMCC opportunity using Claude AI.
        
        This method provides focused analysis on one opportunity with complete data package
        including PMCC details, option chain data, and all 8 types of EODHD enhanced data.
        
        Args:
            opportunity_data: PMCC opportunity data with strikes, Greeks, risk metrics
            enhanced_stock_data: Complete enhanced stock data package
            market_context: Optional market context information
            
        Returns:
            APIResponse containing single opportunity analysis with 0-100 score
        """
        if not opportunity_data or not enhanced_stock_data:
            return APIResponse(
                status=APIStatus.ERROR,
                error=APIError(code=400, message="Missing opportunity or stock data for analysis")
            )
        
        try:
            # Build the single opportunity analysis prompt
            prompt = self._build_single_opportunity_prompt(
                opportunity_data, enhanced_stock_data, market_context
            )
            
            # Execute the analysis with retry logic
            start_time = time.time()
            response = await self._execute_with_retry(prompt)
            processing_time_ms = (time.time() - start_time) * 1000
            
            # Parse the response for single opportunity
            analysis_response = self._parse_single_opportunity_response(response, processing_time_ms)
            
            # Add the full prompt to the response for debugging
            analysis_response['_debug_prompt'] = prompt
            
            # Update statistics
            self._update_stats(response, success=True)
            
            return APIResponse(
                status=APIStatus.OK,
                data=analysis_response
            )
            
        except Exception as e:
            logger.error(f"Error analyzing single PMCC opportunity: {e}")
            self._update_stats(None, success=False)
            
            return APIResponse(
                status=APIStatus.ERROR,
                error=APIError(
                    code=500,
                    message=f"Single opportunity analysis failed: {str(e)}"
                )
            )
    
    def _build_pmcc_analysis_prompt(
        self, 
        enhanced_stock_data: List[EnhancedStockData],
        market_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build the analysis prompt for Claude."""
        
        # Create market context summary
        market_summary = ""
        if market_context:
            market_summary = f"""
CURRENT MARKET CONTEXT:
- Market Volatility: {market_context.get('volatility_regime', 'Unknown')}
- Interest Rate Environment: {market_context.get('interest_rate_trend', 'Unknown')}
- Overall Market Sentiment: {market_context.get('market_sentiment', 'Neutral')}
- VIX Level: {market_context.get('vix_level', 'Unknown')}
"""
        
        # Create stock data summary
        stock_summaries = []
        for i, stock in enumerate(enhanced_stock_data[:20], 1):  # Limit to 20 stocks to manage token usage
            summary = self._create_stock_summary(stock)
            stock_summaries.append(f"{i}. {summary}")
        
        stocks_data = "\n".join(stock_summaries)
        
        prompt = f"""You are an expert quantitative analyst specializing in Poor Man's Covered Call (PMCC) options strategies. Your task is to analyze the provided stock data and identify the top 10 PMCC opportunities for a moderate risk investor profile.

{market_summary}

PMCC STRATEGY REQUIREMENTS:
- LEAPS: Deep ITM call options (delta 0.70-0.95) with 6-12 months to expiration
- Short Calls: OTM call options (delta 0.15-0.40) with 30-45 days to expiration
- Target moderate risk profile with balanced risk/reward

ANALYSIS CRITERIA:
1. Risk Assessment (25%): Beta, debt levels, earnings volatility, credit quality
2. Fundamental Health (25%): PE ratio, profit margins, ROE, growth metrics
3. Technical Setup (20%): Trend analysis, volatility regime, support/resistance
4. Calendar Awareness (15%): Upcoming earnings, dividends, ex-dividend dates
5. PMCC Quality (15%): Option liquidity, delta profiles, profit potential

STOCK DATA:
{stocks_data}

Please analyze each stock and provide a JSON response with exactly this structure:

{{
    "market_assessment": "Your assessment of current market conditions for PMCC strategies",
    "opportunities": [
        {{
            "symbol": "STOCK_SYMBOL",
            "score": 85.5,
            "reasoning": "Concise explanation of why this stock scores well for PMCC",
            "risk_score": 35.0,
            "fundamental_health_score": 82.0,
            "technical_setup_score": 78.0,
            "calendar_risk_score": 25.0,
            "pmcc_quality_score": 88.0,
            "key_strengths": ["Strong fundamentals", "Good option liquidity"],
            "key_risks": ["Earnings in 2 weeks", "High beta"],
            "recommendation": "buy",
            "confidence": 85.0
        }}
    ]
}}

Return exactly 10 opportunities ranked by score (highest first). Focus on quality analysis over quantity.

Important: Respond ONLY with valid JSON. Do not include any text before or after the JSON response."""

        return prompt
    
    def _build_single_opportunity_prompt(
        self,
        opportunity_data: Dict[str, Any],
        enhanced_stock_data: Dict[str, Any],
        market_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build the analysis prompt for a single PMCC opportunity using new template."""
        
        # LOG: Enhanced stock data structure
        logger.info("=== CLAUDE PROMPT DEBUG: ENHANCED STOCK DATA ===")
        logger.info(f"Enhanced stock data keys: {list(enhanced_stock_data.keys())}")
        
        for key, value in enhanced_stock_data.items():
            if isinstance(value, dict):
                logger.info(f"{key}: dict with {len(value)} keys: {list(value.keys())}")
            elif isinstance(value, list):
                logger.info(f"{key}: list with {len(value)} items")
            else:
                logger.info(f"{key}: {type(value).__name__} - {str(value)[:100]}...")
        
        # Extract all necessary data with safe gets
        symbol = opportunity_data.get('symbol', 'Unknown')
        underlying_price = opportunity_data.get('underlying_price', 0)
        
        logger.info(f"Processing opportunity for {symbol} at ${underlying_price}")
        
        # Strategy details
        strategy = opportunity_data.get('strategy_details', {})
        net_debit = strategy.get('net_debit', 0)
        
        # LEAPS option data
        leaps = opportunity_data.get('leaps_option', {})
        leaps_strike = leaps.get('strike', 0)
        leaps_expiration = leaps.get('expiration', 'N/A')
        leaps_dte = leaps.get('dte', 0)
        leaps_delta = leaps.get('delta', 0)
        leaps_volume = leaps.get('volume', 0)
        leaps_oi = leaps.get('open_interest', 0)
        leaps_bid = leaps.get('bid', 0)
        leaps_ask = leaps.get('ask', 0)
        
        # Short call option data
        short = opportunity_data.get('short_option', {})
        short_strike = short.get('strike', 0)
        short_expiration = short.get('expiration', 'N/A')
        short_dte = short.get('dte', 0)
        short_delta = short.get('delta', 0)
        short_volume = short.get('volume', 0)
        short_oi = short.get('open_interest', 0)
        short_bid = short.get('bid', 0)
        short_ask = short.get('ask', 0)
        
        # Extract enhanced data with comprehensive coverage
        fundamentals = enhanced_stock_data.get('fundamentals', {})
        tech_indicators = enhanced_stock_data.get('technical_indicators', {})
        news = enhanced_stock_data.get('recent_news', [])
        earnings = enhanced_stock_data.get('earnings_calendar', [])
        economic = enhanced_stock_data.get('economic_context', [])
        balance_sheet = enhanced_stock_data.get('balance_sheet', {})
        cash_flow = enhanced_stock_data.get('cash_flow', {})
        historical_prices = enhanced_stock_data.get('historical_prices', [])
        analyst_sentiment = enhanced_stock_data.get('analyst_sentiment', {})
        calendar_events = enhanced_stock_data.get('calendar_events', [])
        risk_metrics = enhanced_stock_data.get('risk_metrics', {})
        options_chain = enhanced_stock_data.get('options_chain', {})
        
        # LOG: Data extraction summary
        logger.info("=== DATA EXTRACTION SUMMARY ===")
        logger.info(f"Fundamentals: {len(fundamentals)} fields: {list(fundamentals.keys())[:10]}")
        logger.info(f"Tech indicators: {len(tech_indicators)} fields: {list(tech_indicators.keys())}")
        logger.info(f"News: {len(news)} articles")
        logger.info(f"Earnings: {len(earnings)} events")
        logger.info(f"Economic: {len(economic)} events")
        logger.info(f"Balance sheet: {len(balance_sheet)} fields: {list(balance_sheet.keys())}")
        logger.info(f"Cash flow: {len(cash_flow)} fields: {list(cash_flow.keys())}")
        logger.info(f"Historical prices: {len(historical_prices)} data points")
        logger.info(f"Analyst sentiment: {len(analyst_sentiment)} fields: {list(analyst_sentiment.keys())}")
        logger.info(f"Calendar events: {len(calendar_events)} events")
        logger.info(f"Risk metrics: {len(risk_metrics)} fields: {list(risk_metrics.keys())}")
        logger.info(f"Options chain: {len(options_chain)} fields: {list(options_chain.keys())}")
        
        # Helper function to get meaningful value or return None
        def get_meaningful_value(value, default_zeros=[0, 0.0]):
            """Return value if meaningful, None if it would show as 0 or N/A"""
            if value is None or value == 'N/A' or value in default_zeros:
                return None
            return value
        
        # Helper function to format field conditionally
        def format_field(label, value, unit='', format_type='default'):
            """Format field only if value is meaningful"""
            meaningful_val = get_meaningful_value(value)
            if meaningful_val is None:
                return None
            
            if format_type == 'currency':
                return f"{label}: ${meaningful_val:.2f}{unit}"
            elif format_type == 'percentage':
                # Convert decimal to percentage (0.0075 -> 0.75%)
                percentage_val = meaningful_val * 100
                return f"{label}: {percentage_val:.2f}%{unit}"
            elif format_type == 'percentage_raw':
                # Use value as-is for percentages already in percentage form
                return f"{label}: {meaningful_val:.2f}%{unit}"
            elif format_type == 'number':
                return f"{label}: {meaningful_val:.0f}{unit}"
            else:
                return f"{label}: {meaningful_val}{unit}"
        
        # Extract enhanced data with meaningful value filtering
        company_info = fundamentals.get('company_info', {})
        financial_health = fundamentals.get('financial_health', {})
        valuation_metrics = fundamentals.get('valuation_metrics', {})
        stock_technicals = fundamentals.get('stock_technicals', {})
        dividend_info = fundamentals.get('dividend_info', {})
        
        # Direct fundamentals access for additional fields not in sub-objects
        if not company_info and 'market_capitalization' in fundamentals:
            # Handle flat fundamentals structure
            company_info = fundamentals
        if not financial_health and 'pe_ratio' in fundamentals:
            financial_health = fundamentals
        if not valuation_metrics and ('pe_ratio' in fundamentals or 'enterprise_value' in fundamentals):
            valuation_metrics = fundamentals
        if not stock_technicals and 'beta' in fundamentals:
            stock_technicals = fundamentals
        
        # Build company info section
        company_fields = []
        # Try both 'name' and 'company_name' for company name
        company_name = company_info.get('name') or company_info.get('company_name') or fundamentals.get('company_name')
        if company_name:
            company_fields.append(f"Company: {company_name}")
        if company_info.get('sector') or fundamentals.get('sector'):
            sector = company_info.get('sector') or fundamentals.get('sector')
            company_fields.append(f"Sector: {sector}")
        if company_info.get('industry') or fundamentals.get('industry'):
            industry = company_info.get('industry') or fundamentals.get('industry')
            company_fields.append(f"Industry: {industry}")
        
        # Add employee count
        employees = company_info.get('employees') or fundamentals.get('employees')
        employees_field = format_field("Employees", employees, "", 'number')
        if employees_field:
            company_fields.append(employees_field)
        
        # Add company description if available
        description_raw = company_info.get('description') or fundamentals.get('description')
        if description_raw:
            # Truncate description to reasonable length
            description = description_raw[:200] + "..." if len(description_raw) > 200 else description_raw
            company_fields.append(f"Description: {description}")
        
        # Try multiple fields for market cap or calculate it from shares outstanding
        market_cap = company_info.get('market_cap_mln') or company_info.get('market_capitalization') or fundamentals.get('market_capitalization')
        
        # If no market cap available, calculate it from shares outstanding and current price
        if not market_cap:
            shares_outstanding = fundamentals.get('shares_outstanding') or balance_sheet.get('shares_outstanding')
            current_price = enhanced_stock_data.get('quote', {}).get('last') or enhanced_stock_data.get('quote', {}).get('price')
            if shares_outstanding and current_price:
                market_cap = (shares_outstanding * current_price) / 1000000  # Convert to millions
                logger.info(f"Calculated market cap: {shares_outstanding} shares × ${current_price} = ${market_cap:.0f}M")
        
        if market_cap:
            if market_cap > 1000:  # In millions, convert to billions
                market_cap_field = format_field("Market Cap", market_cap / 1000, "B", 'number')
            else:  # Already in millions
                market_cap_field = format_field("Market Cap", market_cap, "M", 'number')
            if market_cap_field:
                company_fields.append(market_cap_field)
        
        # Build financial health section
        financial_fields = []
        
        # Profitability metrics - try multiple field names
        eps_candidates = ['eps_ttm', 'earnings_per_share', 'eps']
        for candidate in eps_candidates:
            eps_value = financial_health.get(candidate) or fundamentals.get(candidate)
            if eps_value:
                eps_field = format_field("EPS (TTM)", eps_value, "", 'currency')
                if eps_field:
                    financial_fields.append(eps_field)
                break
            
        profit_margin_field = format_field("Profit Margin", financial_health.get('profit_margin') or fundamentals.get('profit_margin'), "", 'percentage')
        if profit_margin_field:
            financial_fields.append(profit_margin_field)
            
        operating_margin_field = format_field("Operating Margin", financial_health.get('operating_margin') or fundamentals.get('operating_margin'), "", 'percentage')
        if operating_margin_field:
            financial_fields.append(operating_margin_field)
            
        # Add gross margin (already in percentage form, don't convert)
        gross_margin_field = format_field("Gross Margin", financial_health.get('gross_margin') or fundamentals.get('gross_margin'), "", 'percentage_raw')
        if gross_margin_field:
            financial_fields.append(gross_margin_field)
            
        roe_field = format_field("ROE", financial_health.get('roe') or fundamentals.get('roe'), "", 'percentage')
        if roe_field:
            financial_fields.append(roe_field)
            
        # Add ROA and ROIC
        roa_field = format_field("ROA", financial_health.get('roa') or fundamentals.get('roa'), "", 'percentage')
        if roa_field:
            financial_fields.append(roa_field)
            
        roic_field = format_field("ROIC", financial_health.get('roic') or fundamentals.get('roic'), "", 'percentage')
        if roic_field:
            financial_fields.append(roic_field)
            
        # Growth metrics - try multiple field names
        revenue_growth_candidates = ['revenue_growth_yoy', 'revenue_growth_rate', 'revenue_growth']
        for candidate in revenue_growth_candidates:
            revenue_growth = financial_health.get(candidate) or fundamentals.get(candidate)
            if revenue_growth:
                revenue_growth_field = format_field("Revenue Growth YoY", revenue_growth, "", 'percentage')
                if revenue_growth_field:
                    financial_fields.append(revenue_growth_field)
                break
                
        # Earnings growth
        earnings_growth_candidates = ['earnings_growth_yoy', 'earnings_growth_rate', 'earnings_growth']
        for candidate in earnings_growth_candidates:
            earnings_growth = financial_health.get(candidate) or fundamentals.get(candidate)
            if earnings_growth:
                earnings_growth_field = format_field("Earnings Growth YoY", earnings_growth, "", 'percentage')
                if earnings_growth_field:
                    financial_fields.append(earnings_growth_field)
                break
            
        # Remove dividend yield from financial section - it's now in dividend section
            
        # Revenue TTM - try multiple field names
        revenue_candidates = ['revenue_ttm', 'total_revenue', 'revenue']
        for candidate in revenue_candidates:
            revenue = financial_health.get(candidate) or fundamentals.get(candidate)
            if revenue:
                if revenue > 1000000000:  # Billions
                    revenue_field = format_field("Revenue (TTM)", revenue / 1000000000, "B", 'number')
                elif revenue > 1000000:  # Millions
                    revenue_field = format_field("Revenue (TTM)", revenue / 1000000, "M", 'number')
                else:
                    revenue_field = format_field("Revenue (TTM)", revenue, "M", 'number')
                if revenue_field:
                    financial_fields.append(revenue_field)
                break
        
        # Build valuation section
        valuation_fields = []
        
        # P/E Ratio - try multiple field names
        pe_candidates = ['pe_ratio', 'PERatio', 'p_e_ratio']
        for candidate in pe_candidates:
            pe_value = valuation_metrics.get(candidate) or fundamentals.get(candidate)
            if pe_value:
                pe_field = format_field("P/E Ratio", pe_value)
                if pe_field:
                    valuation_fields.append(pe_field)
                break
        
        # Forward P/E
        forward_pe_candidates = ['forward_pe', 'forward_pe_ratio', 'ForwardPE']
        for candidate in forward_pe_candidates:
            forward_pe = valuation_metrics.get(candidate) or fundamentals.get(candidate)
            if forward_pe:
                forward_pe_field = format_field("Forward P/E", forward_pe)
                if forward_pe_field:
                    valuation_fields.append(forward_pe_field)
                break
            
        # Price to Sales - try multiple field names
        ps_candidates = ['price_to_sales', 'ps_ratio', 'PriceSalesTTM']
        for candidate in ps_candidates:
            ps_value = valuation_metrics.get(candidate) or fundamentals.get(candidate)
            if ps_value:
                price_to_sales_field = format_field("Price/Sales", ps_value)
                if price_to_sales_field:
                    valuation_fields.append(price_to_sales_field)
                break
            
        # Price to Book - try multiple field names
        pb_candidates = ['price_to_book', 'pb_ratio', 'PriceBookMRQ']
        for candidate in pb_candidates:
            pb_value = valuation_metrics.get(candidate) or fundamentals.get(candidate)
            if pb_value:
                price_to_book_field = format_field("Price/Book", pb_value)
                if price_to_book_field:
                    valuation_fields.append(price_to_book_field)
                break
        
        # PEG Ratio
        peg_candidates = ['peg_ratio', 'PEGRatio']
        for candidate in peg_candidates:
            peg_value = valuation_metrics.get(candidate) or fundamentals.get(candidate)
            if peg_value:
                peg_field = format_field("PEG Ratio", peg_value)
                if peg_field:
                    valuation_fields.append(peg_field)
                break
            
        # Enterprise Value - try multiple field names
        ev_candidates = ['enterprise_value', 'EnterpriseValue']
        for candidate in ev_candidates:
            ev_value = valuation_metrics.get(candidate) or fundamentals.get(candidate)
            if ev_value:
                if ev_value > 1000000000:  # Billions
                    ev_field = format_field("Enterprise Value", ev_value / 1000000000, "B", 'number')
                elif ev_value > 1000000:  # Millions  
                    ev_field = format_field("Enterprise Value", ev_value / 1000000, "M", 'number')
                else:
                    ev_field = format_field("Enterprise Value", ev_value, "M", 'number')
                if ev_field:
                    valuation_fields.append(ev_field)
                break
                
        # EV/Revenue and EV/EBITDA
        ev_revenue_candidates = ['ev_to_revenue', 'EnterpriseValueRevenue']
        for candidate in ev_revenue_candidates:
            ev_revenue = valuation_metrics.get(candidate) or fundamentals.get(candidate)
            if ev_revenue:
                ev_revenue_field = format_field("EV/Revenue", ev_revenue)
                if ev_revenue_field:
                    valuation_fields.append(ev_revenue_field)
                break
                
        ev_ebitda_candidates = ['ev_to_ebitda', 'EnterpriseValueEbitda']
        for candidate in ev_ebitda_candidates:
            ev_ebitda = valuation_metrics.get(candidate) or fundamentals.get(candidate)
            if ev_ebitda:
                ev_ebitda_field = format_field("EV/EBITDA", ev_ebitda)
                if ev_ebitda_field:
                    valuation_fields.append(ev_ebitda_field)
                break
        
        # Build technical indicators section
        technical_fields = []
        
        # Beta - try multiple sources
        beta_candidates = ['beta']
        beta_field = None
        for source in [stock_technicals, fundamentals, tech_indicators]:
            for candidate in beta_candidates:
                beta_value = source.get(candidate)
                if beta_value:
                    beta_field = format_field("Beta", beta_value)
                    if beta_field:
                        technical_fields.append(beta_field)
                    break
            if beta_field:
                break
            
        # 52-week range - try multiple field names
        week_52_high = get_meaningful_value(stock_technicals.get('52_week_high')) or get_meaningful_value(fundamentals.get('52_week_high'))
        week_52_low = get_meaningful_value(stock_technicals.get('52_week_low')) or get_meaningful_value(fundamentals.get('52_week_low'))
        if week_52_high and week_52_low:
            technical_fields.append(f"52-Week Range: ${week_52_low:.2f} - ${week_52_high:.2f}")
            
        # Short interest and short ratio
        short_interest_candidates = ['short_interest', 'short_ratio', 'shares_short']
        for candidate in short_interest_candidates:
            short_interest = stock_technicals.get(candidate) or fundamentals.get(candidate)
            if short_interest:
                if candidate == 'short_ratio':  # Short ratio is a multiplier, not percentage
                    short_interest_field = format_field("Short Ratio", short_interest, "x")
                else:
                    # Short interest should be converted from decimal to percentage
                    short_interest_field = format_field("Short Interest", short_interest, "", 'percentage')
                if short_interest_field:
                    technical_fields.append(short_interest_field)
                break
        
        # Add separate short ratio if not already included
        short_ratio_candidates = ['short_ratio_days', 'days_to_cover']
        for candidate in short_ratio_candidates:
            short_ratio = stock_technicals.get(candidate) or fundamentals.get(candidate)
            if short_ratio:
                short_ratio_field = format_field("Days to Cover", short_ratio, " days")
                if short_ratio_field:
                    technical_fields.append(short_ratio_field)
                break
                
        # Average volume
        avg_volume_candidates = ['avg_volume_30d', 'average_volume', 'avg_volume']
        for candidate in avg_volume_candidates:
            avg_volume = stock_technicals.get(candidate) or fundamentals.get(candidate)
            if avg_volume:
                avg_volume_field = format_field("Avg Volume (30d)", avg_volume, "", 'number')
                if avg_volume_field:
                    technical_fields.append(avg_volume_field)
                break
        
        # Build dividend & calendar section with enhanced dividend details
        dividend_fields = []
        
        # CRITICAL: Dividend yield - this is the most important dividend metric
        dividend_yield_candidates = ['dividend_yield', 'dividendYield']
        for candidate in dividend_yield_candidates:
            dividend_yield = dividend_info.get(candidate) or fundamentals.get(candidate)
            if dividend_yield:
                dividend_yield_field = format_field("Dividend Yield", dividend_yield, "", 'percentage')
                if dividend_yield_field:
                    dividend_fields.append(dividend_yield_field)
                break
        
        # Dividend per share
        dividend_per_share_candidates = ['dividend_per_share', 'annual_dividend', 'dividends_per_share']
        for candidate in dividend_per_share_candidates:
            dividend_per_share = dividend_info.get(candidate) or fundamentals.get(candidate)
            if dividend_per_share:
                dividend_per_share_field = format_field("Dividend Per Share", dividend_per_share, "", 'currency')
                if dividend_per_share_field:
                    dividend_fields.append(dividend_per_share_field)
                break
        
        # CRITICAL: Payout ratio - very important for dividend sustainability
        payout_ratio_candidates = ['payout_ratio', 'payoutRatio']
        for candidate in payout_ratio_candidates:
            payout_ratio = dividend_info.get(candidate) or fundamentals.get(candidate)
            if payout_ratio:
                payout_ratio_field = format_field("Payout Ratio", payout_ratio, "", 'percentage')
                if payout_ratio_field:
                    dividend_fields.append(payout_ratio_field)
                break
            
        # CRITICAL: Ex-dividend date - impacts PMCC strategy timing
        ex_dividend_date_candidates = ['ex_dividend_date', 'exDividendDate']
        for candidate in ex_dividend_date_candidates:
            ex_dividend_date = dividend_info.get(candidate) or fundamentals.get(candidate)
            if ex_dividend_date:
                dividend_fields.append(f"Ex-Dividend: {ex_dividend_date}")
                break
                
        # Next dividend date
        dividend_date_candidates = ['dividend_date', 'dividendDate', 'next_dividend_date']
        for candidate in dividend_date_candidates:
            dividend_date = dividend_info.get(candidate) or fundamentals.get(candidate)
            if dividend_date:
                dividend_fields.append(f"Next Dividend: {dividend_date}")
                break
        
        # Record date
        if dividend_info.get('record_date'):
            dividend_fields.append(f"Record Date: {dividend_info['record_date']}")
        
        # Payment date
        if dividend_info.get('payment_date'):
            dividend_fields.append(f"Payment Date: {dividend_info['payment_date']}")
        
        # Build analyst sentiment section with extended analyst data
        analyst_fields = []
        
        avg_rating_field = format_field("Avg Rating", analyst_sentiment.get('avg_rating'), "/5")
        if avg_rating_field:
            analyst_fields.append(avg_rating_field)
            
        target_price_field = format_field("Target Price", analyst_sentiment.get('target_price'), "", 'currency')
        if target_price_field:
            analyst_fields.append(target_price_field)
        
        # High and low price targets
        high_target_field = format_field("High Target", analyst_sentiment.get('target_price_high'), "", 'currency')
        if high_target_field:
            analyst_fields.append(high_target_field)
            
        low_target_field = format_field("Low Target", analyst_sentiment.get('target_price_low'), "", 'currency')
        if low_target_field:
            analyst_fields.append(low_target_field)
        
        # Total analyst count and buy count
        total_analysts = get_meaningful_value(analyst_sentiment.get('total_analysts'))
        if total_analysts:
            analyst_fields.append(f"Total Analysts: {total_analysts}")
            
        buy_count = get_meaningful_value(analyst_sentiment.get('buy_count'))
        if buy_count:
            analyst_fields.append(f"Buy Recommendations: {buy_count}")
        
        # Rating distribution
        rating_counts = []
        strong_buy = get_meaningful_value(analyst_sentiment.get('strong_buy'))
        buy = get_meaningful_value(analyst_sentiment.get('buy'))
        hold = get_meaningful_value(analyst_sentiment.get('hold'))
        sell = get_meaningful_value(analyst_sentiment.get('sell'))
        strong_sell = get_meaningful_value(analyst_sentiment.get('strong_sell'))
        
        if any([strong_buy, buy, hold, sell, strong_sell]):
            ratings = []
            if strong_buy:
                ratings.append(f"{strong_buy} Strong Buy")
            if buy:
                ratings.append(f"{buy} Buy")
            if hold:
                ratings.append(f"{hold} Hold")
            if sell:
                ratings.append(f"{sell} Sell")
            if strong_sell:
                ratings.append(f"{strong_sell} Strong Sell")
            if ratings:
                analyst_fields.append(f"Ratings: {', '.join(ratings)}")
        
        # Build balance sheet section with share structure
        balance_sheet_fields = []
        
        # Share structure data
        shares_outstanding_candidates = ['shares_outstanding', 'SharesOutstanding', 'outstanding_shares']
        for candidate in shares_outstanding_candidates:
            shares_outstanding = balance_sheet.get(candidate) or fundamentals.get(candidate)
            if shares_outstanding:
                if shares_outstanding > 1000000000:  # Billions
                    shares_field = format_field("Shares Outstanding", shares_outstanding / 1000000000, "B", 'number')
                elif shares_outstanding > 1000000:  # Millions
                    shares_field = format_field("Shares Outstanding", shares_outstanding / 1000000, "M", 'number')
                else:
                    shares_field = format_field("Shares Outstanding", shares_outstanding, "M", 'number')
                if shares_field:
                    balance_sheet_fields.append(shares_field)
                break
                
        # Float
        float_candidates = ['float_shares', 'SharesFloat', 'floating_shares']
        for candidate in float_candidates:
            float_shares = balance_sheet.get(candidate) or fundamentals.get(candidate)
            if float_shares:
                if float_shares > 1000000000:  # Billions
                    float_field = format_field("Float", float_shares / 1000000000, "B", 'number')
                elif float_shares > 1000000:  # Millions
                    float_field = format_field("Float", float_shares / 1000000, "M", 'number')
                else:
                    float_field = format_field("Float", float_shares, "M", 'number')
                if float_field:
                    balance_sheet_fields.append(float_field)
                break
        
        # Institutional ownership
        institutional_ownership_candidates = ['institutional_ownership', 'InstitutionalOwnership', 'inst_ownership_pct']
        for candidate in institutional_ownership_candidates:
            inst_ownership = balance_sheet.get(candidate) or fundamentals.get(candidate)
            if inst_ownership:
                inst_field = format_field("Institutional Ownership", inst_ownership, "", 'percentage')
                if inst_field:
                    balance_sheet_fields.append(inst_field)
                break
                
        # Insider ownership
        insider_ownership_candidates = ['insider_ownership', 'InsiderOwnership', 'insider_ownership_pct']
        for candidate in insider_ownership_candidates:
            insider_ownership = balance_sheet.get(candidate) or fundamentals.get(candidate)
            if insider_ownership:
                insider_field = format_field("Insider Ownership", insider_ownership, "", 'percentage')
                if insider_field:
                    balance_sheet_fields.append(insider_field)
                break
        
        # Total debt - try multiple field names and sources
        debt_candidates = ['total_debt', 'TotalDebt', 'long_term_debt', 'debt']
        debt_field = None
        for source in [balance_sheet, fundamentals]:
            for candidate in debt_candidates:
                total_debt = source.get(candidate)
                if total_debt:
                    if total_debt > 1000000000:  # Billions
                        debt_field = format_field("Total Debt", total_debt / 1000000000, "B", 'number')
                    elif total_debt > 1000000:  # Millions
                        debt_field = format_field("Total Debt", total_debt / 1000000, "M", 'number')
                    else:
                        debt_field = format_field("Total Debt", total_debt, "M", 'number')
                    if debt_field:
                        balance_sheet_fields.append(debt_field)
                    break
            if debt_field:
                break
            
        # Total assets
        assets_candidates = ['total_assets', 'TotalAssets', 'assets']
        assets_field = None
        for source in [balance_sheet, fundamentals]:
            for candidate in assets_candidates:
                total_assets = source.get(candidate)
                if total_assets:
                    if total_assets > 1000000000:  # Billions
                        assets_field = format_field("Total Assets", total_assets / 1000000000, "B", 'number')
                    elif total_assets > 1000000:  # Millions
                        assets_field = format_field("Total Assets", total_assets / 1000000, "M", 'number')
                    else:
                        assets_field = format_field("Total Assets", total_assets, "M", 'number')
                    if assets_field:
                        balance_sheet_fields.append(assets_field)
                    break
            if assets_field:
                break
            
        # Working capital
        working_capital_candidates = ['working_capital', 'WorkingCapital', 'net_working_capital']
        wc_field = None
        for source in [balance_sheet, fundamentals]:
            for candidate in working_capital_candidates:
                working_capital = source.get(candidate)
                if working_capital:
                    if working_capital > 1000000000:  # Billions
                        wc_field = format_field("Working Capital", working_capital / 1000000000, "B", 'number')
                    elif working_capital > 1000000:  # Millions
                        wc_field = format_field("Working Capital", working_capital / 1000000, "M", 'number')
                    else:
                        wc_field = format_field("Working Capital", working_capital, "M", 'number')
                    if wc_field:
                        balance_sheet_fields.append(wc_field)
                    break
            if wc_field:
                break
                
        # Debt ratios
        debt_to_equity_candidates = ['debt_to_equity', 'DebtToEquity', 'debt_equity_ratio']
        de_field = None
        for source in [balance_sheet, fundamentals]:
            for candidate in debt_to_equity_candidates:
                debt_to_equity = source.get(candidate)
                if debt_to_equity:
                    de_field = format_field("Debt/Equity", debt_to_equity)
                    if de_field:
                        balance_sheet_fields.append(de_field)
                    break
            if de_field:
                break
                
        # Current ratio
        current_ratio_candidates = ['current_ratio', 'CurrentRatio']
        cr_field = None
        for source in [balance_sheet, fundamentals]:
            for candidate in current_ratio_candidates:
                current_ratio = source.get(candidate)
                if current_ratio:
                    cr_field = format_field("Current Ratio", current_ratio)
                    if cr_field:
                        balance_sheet_fields.append(cr_field)
                    break
            if cr_field:
                break
        
        # Build cash flow section
        cash_flow_fields = []
        
        # Free cash flow - try multiple field names and sources
        fcf_candidates = ['free_cash_flow', 'FreeCashFlow', 'fcf']
        fcf_field = None
        for source in [cash_flow, fundamentals]:
            for candidate in fcf_candidates:
                free_cash_flow = source.get(candidate)
                if free_cash_flow:
                    if free_cash_flow > 1000000000:  # Billions
                        fcf_field = format_field("Free Cash Flow", free_cash_flow / 1000000000, "B", 'number')
                    elif free_cash_flow > 1000000:  # Millions
                        fcf_field = format_field("Free Cash Flow", free_cash_flow / 1000000, "M", 'number')
                    else:
                        fcf_field = format_field("Free Cash Flow", free_cash_flow, "M", 'number')
                    if fcf_field:
                        cash_flow_fields.append(fcf_field)
                    break
            if fcf_field:
                break
            
        # Operating cash flow
        ocf_candidates = ['operating_cash_flow', 'OperatingCashFlow', 'cash_from_operations']
        ocf_field = None
        for source in [cash_flow, fundamentals]:
            for candidate in ocf_candidates:
                operating_cash_flow = source.get(candidate)
                if operating_cash_flow:
                    if operating_cash_flow > 1000000000:  # Billions
                        ocf_field = format_field("Operating Cash Flow", operating_cash_flow / 1000000000, "B", 'number')
                    elif operating_cash_flow > 1000000:  # Millions
                        ocf_field = format_field("Operating Cash Flow", operating_cash_flow / 1000000, "M", 'number')
                    else:
                        ocf_field = format_field("Operating Cash Flow", operating_cash_flow, "M", 'number')
                    if ocf_field:
                        cash_flow_fields.append(ocf_field)
                    break
            if ocf_field:
                break
                
        # Cash per share
        cash_per_share_candidates = ['cash_per_share', 'CashPerShare']
        cps_field = None
        for source in [cash_flow, fundamentals]:
            for candidate in cash_per_share_candidates:
                cash_per_share = source.get(candidate)
                if cash_per_share:
                    cps_field = format_field("Cash Per Share", cash_per_share, "", 'currency')
                    if cps_field:
                        cash_flow_fields.append(cps_field)
                    break
            if cps_field:
                break
        
        # Build share structure section
        share_structure_fields = []
        
        # Shares float - try multiple field names
        float_candidates = ['shares_float', 'float_shares', 'SharesFloat', 'floating_shares']
        for candidate in float_candidates:
            float_shares = balance_sheet.get(candidate) or fundamentals.get(candidate)
            if float_shares:
                if float_shares > 1000000000:  # Billions
                    float_field = format_field("Float", float_shares / 1000000000, "B", 'number')
                elif float_shares > 1000000:  # Millions
                    float_field = format_field("Float", float_shares / 1000000, "M", 'number')
                else:
                    float_field = format_field("Float", float_shares, "M", 'number')
                if float_field:
                    share_structure_fields.append(float_field)
                break
        
        # Institutional ownership percentage
        institutional_candidates = ['percent_institutions', 'institutional_ownership', 'InstitutionalOwnership']
        for candidate in institutional_candidates:
            inst_ownership = balance_sheet.get(candidate) or fundamentals.get(candidate)
            if inst_ownership:
                # percent_institutions is already in percentage form
                if candidate == 'percent_institutions':
                    inst_field = format_field("Institutional Ownership", inst_ownership, "", 'percentage_raw')
                else:
                    inst_field = format_field("Institutional Ownership", inst_ownership, "", 'percentage')
                if inst_field:
                    share_structure_fields.append(inst_field)
                break
                
        # Insider ownership percentage
        insider_candidates = ['percent_insiders', 'insider_ownership', 'InsiderOwnership'] 
        for candidate in insider_candidates:
            insider_ownership = balance_sheet.get(candidate) or fundamentals.get(candidate)
            if insider_ownership:
                # percent_insiders is already in percentage form
                if candidate == 'percent_insiders':
                    insider_field = format_field("Insider Ownership", insider_ownership, "", 'percentage_raw')
                else:
                    insider_field = format_field("Insider Ownership", insider_ownership, "", 'percentage')
                if insider_field:
                    share_structure_fields.append(insider_field)
                break
        
        # Build moving averages section
        moving_averages_fields = []
        
        # 50-day moving average
        ma_50_candidates = ['fifty_day_ma', '50_day_ma', 'SMA50']
        for candidate in ma_50_candidates:
            ma_50 = stock_technicals.get(candidate) or fundamentals.get(candidate)
            if ma_50:
                ma_50_field = format_field("50-Day MA", ma_50, "", 'currency')
                if ma_50_field:
                    moving_averages_fields.append(ma_50_field)
                break
        
        # 200-day moving average
        ma_200_candidates = ['two_hundred_day_ma', '200_day_ma', 'SMA200']
        for candidate in ma_200_candidates:
            ma_200 = stock_technicals.get(candidate) or fundamentals.get(candidate)
            if ma_200:
                ma_200_field = format_field("200-Day MA", ma_200, "", 'currency')
                if ma_200_field:
                    moving_averages_fields.append(ma_200_field)
                break
        
        # Build historical prices section
        historical_fields = []
        if historical_prices and len(historical_prices) > 0:
            # Sort by date to get most recent first
            sorted_prices = sorted(historical_prices, key=lambda x: x.get('date', ''), reverse=True)
            recent_prices = sorted_prices[:15]  # Last 15 days max
            
            if len(recent_prices) >= 5:
                # Calculate 5-day and 10-day trends
                current_price = recent_prices[0].get('adjusted_close', 0)
                price_5d = recent_prices[4].get('adjusted_close', 0) if len(recent_prices) > 4 else current_price
                price_10d = recent_prices[9].get('adjusted_close', 0) if len(recent_prices) > 9 else current_price
                
                if current_price and price_5d:
                    trend_5d = ((current_price - price_5d) / price_5d) * 100
                    historical_fields.append(f"5-Day Trend: {trend_5d:+.1f}%")
                
                if current_price and price_10d and len(recent_prices) > 9:
                    trend_10d = ((current_price - price_10d) / price_10d) * 100
                    historical_fields.append(f"10-Day Trend: {trend_10d:+.1f}%")
                
                # Add recent trading range
                recent_highs = [p.get('high', 0) for p in recent_prices[:10] if p.get('high')]
                recent_lows = [p.get('low', 0) for p in recent_prices[:10] if p.get('low')]
                if recent_highs and recent_lows:
                    recent_high = max(recent_highs)
                    recent_low = min(recent_lows)
                    historical_fields.append(f"10-Day Range: ${recent_low:.2f} - ${recent_high:.2f}")
                
                # Add average volume
                recent_volumes = [p.get('volume', 0) for p in recent_prices[:5] if p.get('volume')]
                if recent_volumes:
                    avg_volume = sum(recent_volumes) / len(recent_volumes)
                    historical_fields.append(f"5-Day Avg Volume: {avg_volume:,.0f}")
        
        # Build enhanced technical indicators section (from technical_indicators data)
        enhanced_technical_fields = []
        
        # Add moving averages - 50-day and 200-day specifically
        ma_50_field = format_field("50-Day MA", tech_indicators.get('sma_50') or tech_indicators.get('ma_50') or fundamentals.get('50_day_ma'), "", 'currency')
        if ma_50_field:
            enhanced_technical_fields.append(ma_50_field)
            
        ma_200_field = format_field("200-Day MA", tech_indicators.get('sma_200') or tech_indicators.get('ma_200') or fundamentals.get('200_day_ma'), "", 'currency')
        if ma_200_field:
            enhanced_technical_fields.append(ma_200_field)
        
        # RSI with date if available - try multiple field names
        rsi_candidates = ['rsi', 'rsi_14d', 'rsi_14']
        for candidate in rsi_candidates:
            rsi_value = tech_indicators.get(candidate)
            if rsi_value:
                # Try to find RSI date
                rsi_date = tech_indicators.get(f'{candidate}_date') or tech_indicators.get('rsi_date')
                if rsi_date:
                    rsi_field = format_field(f"RSI(14) as of {rsi_date}", rsi_value)
                else:
                    rsi_field = format_field("RSI(14)", rsi_value)
                if rsi_field:
                    enhanced_technical_fields.append(rsi_field)
                break
        
        # Volatility - try multiple field names
        volatility_candidates = ['volatility', 'volatility_30d', 'historical_volatility']
        for candidate in volatility_candidates:
            volatility = tech_indicators.get(candidate)
            if volatility:
                # Volatility is already in percentage form, don't convert
                volatility_field = format_field("Volatility (30d)", volatility, "", 'percentage_raw')
                if volatility_field:
                    enhanced_technical_fields.append(volatility_field)
                break
        
        # ATR with date if available - try multiple field names
        atr_candidates = ['atr', 'average_true_range']
        for candidate in atr_candidates:
            atr_value = tech_indicators.get(candidate)
            if atr_value:
                # Try to find ATR date
                atr_date = tech_indicators.get(f'{candidate}_date') or tech_indicators.get('atr_date')
                if atr_date:
                    atr_field = format_field(f"ATR as of {atr_date}", atr_value, "", 'currency')
                else:
                    atr_field = format_field("ATR", atr_value, "", 'currency')
                if atr_field:
                    enhanced_technical_fields.append(atr_field)
                break
        
        # Moving averages - try multiple field names
        ma_pairs = [
            (['sma_20', 'sma20'], 'SMA(20)'),
            (['sma_50', 'sma50', 'sma_50d'], 'SMA(50)'),
            (['sma_200', 'sma200', 'sma_200d'], 'SMA(200)'),
            (['ema_21', 'ema21', 'ema_21d'], 'EMA(21)')
        ]
        
        for candidates, label in ma_pairs:
            for candidate in candidates:
                ma_value = tech_indicators.get(candidate)
                if ma_value:
                    ma_field = format_field(label, ma_value, "", 'currency')
                    if ma_field:
                        enhanced_technical_fields.append(ma_field)
                    break
        
        # MACD - try multiple field names
        macd_candidates = ['macd', 'macd_line']
        for candidate in macd_candidates:
            macd_value = tech_indicators.get(candidate)
            if macd_value:
                macd_field = format_field("MACD", macd_value)
                if macd_field:
                    enhanced_technical_fields.append(macd_field)
                break
                
        # MACD Signal and Histogram
        macd_signal = tech_indicators.get('macd_signal')
        if macd_signal:
            signal_field = format_field("MACD Signal", macd_signal)
            if signal_field:
                enhanced_technical_fields.append(signal_field)
                
        macd_histogram = tech_indicators.get('macd_histogram')
        if macd_histogram:
            histogram_field = format_field("MACD Histogram", macd_histogram)
            if histogram_field:
                enhanced_technical_fields.append(histogram_field)
                
        # Bollinger Bands
        bb_upper = tech_indicators.get('bollinger_upper')
        bb_lower = tech_indicators.get('bollinger_lower')
        if bb_upper and bb_lower:
            enhanced_technical_fields.append(f"Bollinger Bands: ${bb_lower:.2f} - ${bb_upper:.2f}")
        
        # Build comprehensive earnings calendar section
        earnings_calendar_items = []
        
        # Process earnings from both sources
        earnings_sources = [earnings, calendar_events]
        all_earnings = []
        
        for source in earnings_sources:
            if source and len(source) > 0:
                for event in source:
                    if isinstance(event, dict):
                        event_type = event.get('event_type', event.get('type', ''))
                        if 'earnings' in event_type.lower() or event.get('eps_actual') or event.get('eps_estimate'):
                            all_earnings.append(event)
        
        # Sort earnings by date (prefer report_date for actual announcement date)
        sorted_earnings = []
        for event in all_earnings:
            # Use report_date (announcement date) if available, otherwise fall back to date (quarter end)
            event_date_str = event.get('report_date') or event.get('date') or event.get('event_date', '')
            if event_date_str:
                try:
                    from datetime import datetime
                    if isinstance(event_date_str, str):
                        event_date = datetime.fromisoformat(event_date_str.replace('Z', '+00:00')).date()
                    else:
                        event_date = event_date_str
                    event['parsed_date'] = event_date
                    # Also store the quarter end date for reference
                    quarter_date_str = event.get('date', '')
                    if quarter_date_str:
                        event['quarter_date'] = quarter_date_str
                    sorted_earnings.append(event)
                except:
                    continue
        
        sorted_earnings = sorted(sorted_earnings, key=lambda x: x['parsed_date'])
        
        # Format earnings calendar with actual vs estimate comparisons
        today = datetime.now().date()
        for event in sorted_earnings[:10]:  # Limit to 10 most relevant
            event_date = event['parsed_date']
            days_diff = (event_date - today).days
            
            eps_actual = get_meaningful_value(event.get('eps_actual') or event.get('actual_eps'))
            eps_estimate = get_meaningful_value(event.get('eps_estimate') or event.get('estimated_eps'))
            revenue_actual = get_meaningful_value(event.get('revenue_actual'))
            revenue_estimate = get_meaningful_value(event.get('revenue_estimate'))
            
            # Add clarity about whether this is report date or quarter end
            quarter_date = event.get('quarter_date', '')
            if quarter_date and str(event_date) != quarter_date:
                date_label = f"{event_date} ({days_diff:+d} days, Q-end: {quarter_date})"
            else:
                date_label = f"{event_date} ({days_diff:+d} days)"
            
            if eps_actual and eps_estimate:
                surprise = ((eps_actual - eps_estimate) / eps_estimate) * 100 if eps_estimate != 0 else 0
                earnings_calendar_items.append(f"• {date_label}: EPS ${eps_actual} vs ${eps_estimate} est ({surprise:+.1f}% surprise)")
            elif eps_actual:
                earnings_calendar_items.append(f"• {date_label}: EPS ${eps_actual} (actual)")
            elif eps_estimate:
                earnings_calendar_items.append(f"• {date_label}: EPS ${eps_estimate} (estimated)")
            else:
                earnings_calendar_items.append(f"• {date_label}: Earnings announcement")
            
            # Add revenue data if available with enhanced actual/estimate values
            if revenue_actual and revenue_estimate:
                rev_surprise = ((revenue_actual - revenue_estimate) / revenue_estimate) * 100 if revenue_estimate != 0 else 0
                if revenue_actual > 1000000000:  # Billions
                    rev_actual_display = f"${revenue_actual/1000000000:.1f}B"
                elif revenue_actual > 1000000:  # Millions
                    rev_actual_display = f"${revenue_actual/1000000:.0f}M"
                else:
                    rev_actual_display = f"${revenue_actual:.0f}M"
                    
                if revenue_estimate > 1000000000:  # Billions
                    rev_est_display = f"${revenue_estimate/1000000000:.1f}B"
                elif revenue_estimate > 1000000:  # Millions
                    rev_est_display = f"${revenue_estimate/1000000:.0f}M"
                else:
                    rev_est_display = f"${revenue_estimate:.0f}M"
                    
                earnings_calendar_items.append(f"  Revenue: {rev_actual_display} vs {rev_est_display} est ({rev_surprise:+.1f}% surprise)")
            elif revenue_actual:
                if revenue_actual > 1000000000:
                    rev_display = f"${revenue_actual/1000000000:.1f}B"
                elif revenue_actual > 1000000:
                    rev_display = f"${revenue_actual/1000000:.0f}M"
                else:
                    rev_display = f"${revenue_actual:.0f}M"
                earnings_calendar_items.append(f"  Revenue: {rev_display} (actual)")
            elif revenue_estimate:
                if revenue_estimate > 1000000000:
                    rev_display = f"${revenue_estimate/1000000000:.1f}B"
                elif revenue_estimate > 1000000:
                    rev_display = f"${revenue_estimate/1000000:.0f}M"
                else:
                    rev_display = f"${revenue_estimate:.0f}M"
                earnings_calendar_items.append(f"  Revenue: {rev_display} (estimated)")
        
        # Keep the simplified earnings info for dividend section
        earnings_info = []
        if sorted_earnings:
            # Most recent past earnings
            past_earnings = [e for e in sorted_earnings if e['parsed_date'] < today]
            if past_earnings:
                recent = past_earnings[-1]
                eps_actual = get_meaningful_value(recent.get('eps_actual') or recent.get('actual_eps'))
                if eps_actual:
                    earnings_info.append(f"Recent Earnings: {recent['parsed_date']} - EPS: ${eps_actual}")
            
            # Next upcoming earnings
            future_earnings = [e for e in sorted_earnings if e['parsed_date'] >= today]
            if future_earnings:
                next_earn = future_earnings[0]
                eps_estimate = get_meaningful_value(next_earn.get('eps_estimate') or next_earn.get('estimated_eps'))
                if eps_estimate:
                    earnings_info.append(f"Next Earnings: {next_earn['parsed_date']} - Est: ${eps_estimate}")
                else:
                    earnings_info.append(f"Next Earnings: {next_earn['parsed_date']}")
        
        # Format news articles (full content, no sentiment)
        full_news_articles = ""
        if news:
            for i, article in enumerate(news[:5], 1):  # Limit to 5 articles
                full_news_articles += f"\n\n**Article {i}:**\n"
                full_news_articles += f"Date: {article.get('date', 'N/A')}\n"
                full_news_articles += f"Title: {article.get('title', 'N/A')}\n"
                if article.get('content'):
                    full_news_articles += f"{article['content']}\n"
        else:
            full_news_articles = "\nNo recent news available."
        
        # Build detailed economic events section
        economic_events_summary = ""
        economic_events_detailed = []
        
        if economic:
            # Sort events by date and impact
            sorted_events = sorted(economic[:15], key=lambda x: (x.get('date', ''), x.get('impact', 'low')))
            
            for event in sorted_events:
                if event.get('event') and event.get('date'):
                    impact = event.get('impact', 'N/A')
                    country = event.get('country', 'N/A')
                    time = event.get('time', '')
                    forecast = event.get('forecast', '')
                    previous = event.get('previous', '')
                    
                    # Build detailed event description
                    event_desc = f"- {event['date']}"
                    if time:
                        event_desc += f" {time}"
                    event_desc += f": {event['event']} ({country}) - {impact.upper()} impact"
                    
                    # Add forecast, previous, and actual values if available
                    actual_value = event.get('actual', '')
                    if forecast or previous or actual_value:
                        details = []
                        if actual_value:
                            details.append(f"Actual: {actual_value}")
                        if forecast:
                            details.append(f"Forecast: {forecast}")
                        if previous:
                            details.append(f"Previous: {previous}")
                        if details:
                            event_desc += f" [{', '.join(details)}]"
                    
                    economic_events_detailed.append(event_desc)
            
            # Create summary for main section (limit to 5)
            summary_events = []
            for event in economic[:5]:
                if event.get('event') and event.get('date'):
                    impact_label = event.get('impact', 'medium').lower()
                    summary_events.append(f"- {event['date']}: {event['event']} ({event.get('country', 'N/A')}) - {impact_label}")
            
            economic_events_summary = "\n".join(summary_events) if summary_events else "No upcoming economic events"
            
        else:
            economic_events_summary = "No upcoming economic events"
        
        # Extract market sentiment and context data
        market_sentiment_data = enhanced_stock_data.get('market_sentiment', {})
        volatility_regime = market_context.get('volatility_regime', 'normal') if market_context else 'normal'
        sector_context = market_context.get('sector_context', 'N/A') if market_context else 'N/A'
        
        # Build market sentiment section with market context details
        market_sentiment_fields = []
        
        # Market context from market_context parameter
        if market_context:
            market_trend = market_context.get('market_trend')
            if market_trend:
                market_sentiment_fields.append(f"Market Trend: {market_trend}")
                
            interest_rate_environment = market_context.get('interest_rate_environment')
            if interest_rate_environment:
                market_sentiment_fields.append(f"Interest Rate Environment: {interest_rate_environment}")
                
            sector_performance = market_context.get('sector_performance')
            if sector_performance:
                market_sentiment_fields.append(f"Sector Performance: {sector_performance}")
                
            market_phase = market_context.get('market_phase')
            if market_phase:
                market_sentiment_fields.append(f"Market Phase: {market_phase}")
        
        # Overall market sentiment indicators
        sentiment_score = get_meaningful_value(market_sentiment_data.get('sentiment_score'))
        if sentiment_score:
            sentiment_label = "Bullish" if sentiment_score > 60 else "Bearish" if sentiment_score < 40 else "Neutral"
            market_sentiment_fields.append(f"Overall Sentiment: {sentiment_score}/100 ({sentiment_label})")
        
        # Fear & Greed index
        fear_greed = get_meaningful_value(market_sentiment_data.get('fear_greed_index'))
        if fear_greed:
            fg_label = "Extreme Greed" if fear_greed > 75 else "Greed" if fear_greed > 60 else "Fear" if fear_greed < 40 else "Extreme Fear" if fear_greed < 25 else "Neutral"
            market_sentiment_fields.append(f"Fear & Greed Index: {fear_greed}/100 ({fg_label})")
        
        # VIX level and interpretation
        vix_level = get_meaningful_value(market_sentiment_data.get('vix_current')) or get_meaningful_value(market_context.get('vix_level') if market_context else None)
        if vix_level:
            vix_regime = "Low" if vix_level < 15 else "Normal" if vix_level < 25 else "Elevated" if vix_level < 35 else "High"
            market_sentiment_fields.append(f"VIX Level: {vix_level:.1f} ({vix_regime} volatility)")
        
        # Put/Call ratio
        put_call_ratio = get_meaningful_value(market_sentiment_data.get('put_call_ratio'))
        if put_call_ratio:
            pc_sentiment = "Bearish" if put_call_ratio > 1.2 else "Bullish" if put_call_ratio < 0.8 else "Neutral"
            market_sentiment_fields.append(f"Put/Call Ratio: {put_call_ratio:.2f} ({pc_sentiment})")
        
        # Insider trading activity
        insider_sentiment = market_sentiment_data.get('insider_sentiment')
        if insider_sentiment:
            market_sentiment_fields.append(f"Insider Activity: {insider_sentiment}")
        
        # Analyst sentiment changes
        analyst_changes = market_sentiment_data.get('recent_rating_changes')
        if analyst_changes:
            upgrades = analyst_changes.get('upgrades', 0)
            downgrades = analyst_changes.get('downgrades', 0)
            if upgrades or downgrades:
                market_sentiment_fields.append(f"Recent Analyst Changes: {upgrades} upgrades, {downgrades} downgrades")
        
        # Sector rotation trends
        sector_momentum = market_sentiment_data.get('sector_momentum')
        if sector_momentum:
            market_sentiment_fields.append(f"Sector Momentum: {sector_momentum}")
        
        # Options flow sentiment
        options_flow = market_sentiment_data.get('options_flow_sentiment')
        if options_flow:
            market_sentiment_fields.append(f"Options Flow: {options_flow}")
        
        # Social media sentiment
        social_sentiment = market_sentiment_data.get('social_media_sentiment')
        if social_sentiment:
            market_sentiment_fields.append(f"Social Media Sentiment: {social_sentiment}")
        
        # Build conditional sections for the prompt
        prompt_sections = []
        
        # Strategy setup (always included) - Enhanced with extended quote data
        quote_data = enhanced_stock_data.get('quote', {})
        stock_change = quote_data.get('change', 0)
        stock_change_pct = quote_data.get('change_percent', 0)
        stock_volume = quote_data.get('volume', 0)
        stock_high = quote_data.get('high', 0)
        stock_low = quote_data.get('low', 0)
        stock_open = quote_data.get('open', 0)
        
        prompt_sections.append(f"""## PMCC OPPORTUNITY: {symbol}

**STRATEGY SETUP:**
- Current Stock Price: ${underlying_price}
- Daily Change: ${stock_change:.2f} ({stock_change_pct:+.2f}%)
- Daily Range: ${stock_low:.2f} - ${stock_high:.2f} | Open: ${stock_open:.2f}
- Volume: {stock_volume:,}
- Net Debit: ${net_debit:.2f}
- LEAPS Strike: ${leaps_strike} | Expiration: {leaps_expiration} | DTE: {leaps_dte} | Delta: {leaps_delta:.3f}
- Short Call Strike: ${short_strike} | Expiration: {short_expiration} | DTE: {short_dte} | Delta: {short_delta:.3f}

**LIQUIDITY ASSESSMENT:**
- LEAPS: Volume {leaps_volume} | OI {leaps_oi} | Bid/Ask: ${leaps_bid:.2f}/${leaps_ask:.2f}
- Short Call: Volume {short_volume} | OI {short_oi} | Bid/Ask: ${short_bid:.2f}/${short_ask:.2f}

## COMPREHENSIVE ANALYSIS DATA""")
        
        # LOG: Section building tracking
        logger.info("=== SECTION BUILDING TRACKING ===")
        sections_included = ["Strategy Setup (always included)"]
        
        # Company info section (if any meaningful data)
        if company_fields:
            sections_included.append(f"Company Overview ({len(company_fields)} fields)")
            logger.info(f"Including Company Overview: {company_fields}")
            prompt_sections.append(f"""
**COMPANY OVERVIEW:**
- {' | '.join(company_fields)}""")
        
        # Financial health section (if any meaningful data)
        if financial_fields:
            sections_included.append(f"Financial Health ({len(financial_fields)} fields)")
            logger.info(f"Including Financial Health: {financial_fields}")
            prompt_sections.append(f"""
**FINANCIAL HEALTH:**
- {' | '.join(financial_fields)}""")
        
        # Valuation section (if any meaningful data)
        if valuation_fields:
            prompt_sections.append(f"""
**VALUATION METRICS:**
- {' | '.join(valuation_fields)}""")
        
        # Historical prices section (if any meaningful data)
        if historical_fields:
            prompt_sections.append(f"""
**HISTORICAL PRICE TRENDS:**
- {' | '.join(historical_fields)}""")
        
        # Technical indicators section (if any meaningful data)
        if technical_fields:
            prompt_sections.append(f"""
**TECHNICAL INDICATORS (BASIC):**
- {' | '.join(technical_fields)}""")
        
        # Enhanced technical indicators section (if any meaningful data)
        if enhanced_technical_fields:
            prompt_sections.append(f"""
**TECHNICAL INDICATORS (ADVANCED):**
- {' | '.join(enhanced_technical_fields)}""")
        
        # Build comprehensive options analysis section with extended options data
        options_analysis_fields = []
        
        # Option symbols for both legs
        leaps_option_symbol = leaps.get('option_symbol') or leaps.get('symbol')
        short_option_symbol = short.get('option_symbol') or short.get('symbol')
        
        if leaps_option_symbol:
            options_analysis_fields.append(f"LEAPS Symbol: {leaps_option_symbol}")
        if short_option_symbol:
            options_analysis_fields.append(f"Short Call Symbol: {short_option_symbol}")
        
        # Mid and last prices for both legs
        leaps_mid = (leaps_bid + leaps_ask) / 2 if (leaps_bid and leaps_ask) else None
        leaps_last = leaps.get('last') or leaps.get('last_price')
        
        if leaps_mid:
            options_analysis_fields.append(f"LEAPS Mid Price: ${leaps_mid:.2f}")
        if leaps_last:
            options_analysis_fields.append(f"LEAPS Last Price: ${leaps_last:.2f}")
        
        short_mid = (short_bid + short_ask) / 2 if (short_bid and short_ask) else None
        short_last = short.get('last') or short.get('last_price')
        
        if short_mid:
            options_analysis_fields.append(f"Short Call Mid Price: ${short_mid:.2f}")
        if short_last:
            options_analysis_fields.append(f"Short Call Last Price: ${short_last:.2f}")
        
        # LEAPS Greeks and pricing details with comprehensive analysis
        leaps_gamma = leaps.get('gamma', 0)
        leaps_theta = leaps.get('theta', 0)
        leaps_vega = leaps.get('vega', 0)
        leaps_iv = leaps.get('iv', 0)
        
        if leaps_volume or leaps_oi:
            liquidity_score = "Excellent" if (leaps_volume > 50 and leaps_oi > 500) else "Good" if (leaps_volume > 10 and leaps_oi > 100) else "Moderate" if (leaps_volume > 5 or leaps_oi > 50) else "Poor"
            options_analysis_fields.append(f"LEAPS Liquidity: {liquidity_score} (Vol: {leaps_volume}, OI: {leaps_oi})")
            
        leaps_spread = leaps_ask - leaps_bid if (leaps_ask and leaps_bid) else 0
        if leaps_spread > 0:
            spread_pct = (leaps_spread / ((leaps_ask + leaps_bid) / 2)) * 100 if (leaps_ask and leaps_bid) else 0
            spread_quality = "Tight" if spread_pct < 2 else "Moderate" if spread_pct < 5 else "Wide"
            options_analysis_fields.append(f"LEAPS Spread: ${leaps_spread:.2f} ({spread_pct:.1f}% - {spread_quality})")
            
        # LEAPS Greeks analysis
        greeks_analysis = []
        if leaps_delta:
            delta_quality = "Deep ITM" if leaps_delta > 0.85 else "Moderate ITM" if leaps_delta > 0.7 else "Shallow ITM"
            greeks_analysis.append(f"Delta: {leaps_delta:.3f} ({delta_quality})")
        if leaps_gamma:
            greeks_analysis.append(f"Gamma: {leaps_gamma:.4f}")
        if leaps_theta:
            theta_per_day = abs(leaps_theta)
            greeks_analysis.append(f"Theta: {leaps_theta:.3f} (${theta_per_day:.2f}/day decay)")
        if leaps_vega:
            greeks_analysis.append(f"Vega: {leaps_vega:.3f} (IV risk: {leaps_iv*100:.1f}%)")
        
        if greeks_analysis:
            options_analysis_fields.append(f"LEAPS Greeks: {' | '.join(greeks_analysis)}")
            
        # Short call Greeks and pricing details with comprehensive analysis
        short_gamma = short.get('gamma', 0)
        short_theta = short.get('theta', 0)
        short_vega = short.get('vega', 0)
        short_iv = short.get('iv', 0)
        
        if short_volume or short_oi:
            liquidity_score = "Excellent" if (short_volume > 100 and short_oi > 1000) else "Good" if (short_volume > 20 and short_oi > 200) else "Moderate" if (short_volume > 10 or short_oi > 100) else "Poor"
            options_analysis_fields.append(f"Short Call Liquidity: {liquidity_score} (Vol: {short_volume}, OI: {short_oi})")
            
        short_spread = short_ask - short_bid if (short_ask and short_bid) else 0
        if short_spread > 0:
            spread_pct = (short_spread / ((short_ask + short_bid) / 2)) * 100 if (short_ask and short_bid) else 0
            spread_quality = "Tight" if spread_pct < 3 else "Moderate" if spread_pct < 8 else "Wide"
            options_analysis_fields.append(f"Short Call Spread: ${short_spread:.2f} ({spread_pct:.1f}% - {spread_quality})")
            
        # Short call Greeks analysis
        short_greeks_analysis = []
        if short_delta:
            delta_quality = "Far OTM" if short_delta < 0.15 else "Moderate OTM" if short_delta < 0.35 else "Close to ATM"
            short_greeks_analysis.append(f"Delta: {short_delta:.3f} ({delta_quality})")
        if short_gamma:
            short_greeks_analysis.append(f"Gamma: {short_gamma:.4f}")
        if short_theta:
            theta_credit = abs(short_theta)
            short_greeks_analysis.append(f"Theta: {short_theta:.3f} (+${theta_credit:.2f}/day credit)")
        if short_vega:
            short_greeks_analysis.append(f"Vega: {short_vega:.3f} (IV risk: {short_iv*100:.1f}%)")
        
        if short_greeks_analysis:
            options_analysis_fields.append(f"Short Call Greeks: {' | '.join(short_greeks_analysis)}")
            
        # Combined Greeks analysis and complete strategy details
        if leaps_delta and short_delta:
            delta_diff = leaps_delta - short_delta
            delta_ratio = leaps_delta / short_delta if short_delta != 0 else 0
            options_analysis_fields.append(f"Delta Analysis: Spread {delta_diff:.3f} | Ratio {delta_ratio:.2f}x")
        
        # Complete strategy details with max profit/loss and breakeven
        max_profit = strategy.get('max_profit')
        max_loss = strategy.get('max_loss') 
        breakeven_price = strategy.get('breakeven_price')
        risk_reward_ratio = strategy.get('risk_reward_ratio')
        
        strategy_details = []
        if max_profit:
            if max_profit == float('inf') or max_profit > 999999:
                strategy_details.append("Max Profit: Unlimited")
            else:
                strategy_details.append(f"Max Profit: ${max_profit:.2f}")
        
        if max_loss:
            strategy_details.append(f"Max Loss: ${max_loss:.2f}")
        
        if breakeven_price:
            strategy_details.append(f"Breakeven: ${breakeven_price:.2f}")
        
        if risk_reward_ratio:
            strategy_details.append(f"Risk/Reward: 1:{risk_reward_ratio:.2f}")
        
        if strategy_details:
            options_analysis_fields.extend(strategy_details)
        
        # Net Greeks exposure
        if leaps_theta and short_theta:
            net_theta = leaps_theta + short_theta  # Short theta is positive for seller
            net_theta_direction = "Positive" if net_theta > 0 else "Negative"
            options_analysis_fields.append(f"Net Theta: {net_theta:.3f} ({net_theta_direction} time decay)")
        
        if leaps_vega and short_vega:
            net_vega = leaps_vega - short_vega  # Net long vega exposure
            vega_direction = "Long" if net_vega > 0 else "Short"
            options_analysis_fields.append(f"Net Vega: {net_vega:.3f} ({vega_direction} volatility exposure)")
        
        # Options chain summary with detailed analysis
        if options_chain:
            chain_underlying = options_chain.get('underlying', '')
            chain_price = options_chain.get('underlying_price', 0)
            contract_count = options_chain.get('contract_count', 0)
            iv_rank = options_chain.get('iv_rank')
            iv_percentile = options_chain.get('iv_percentile')
            
            if chain_underlying and contract_count:
                options_analysis_fields.append(f"Options Chain: {contract_count} contracts available for {chain_underlying}")
            
            if iv_rank:
                options_analysis_fields.append(f"IV Rank: {iv_rank:.0f}% (volatility environment)")
            if iv_percentile:
                options_analysis_fields.append(f"IV Percentile: {iv_percentile:.0f}% (historical context)")
                
        # Rename for consistency with existing code
        options_data_fields = options_analysis_fields
                
        # Risk metrics from enhanced data
        risk_metrics_fields = []
        if risk_metrics:
            credit_rating = risk_metrics.get('credit_rating')
            if credit_rating and credit_rating != 'N/A':
                risk_metrics_fields.append(f"Credit Rating: {credit_rating}")
                
            earnings_volatility = risk_metrics.get('earnings_volatility')
            if earnings_volatility:
                ev_field = format_field("Earnings Volatility", earnings_volatility, "", 'percentage')
                if ev_field:
                    risk_metrics_fields.append(ev_field)
                    
            debt_coverage = risk_metrics.get('debt_coverage_ratio')
            if debt_coverage:
                dc_field = format_field("Debt Coverage", debt_coverage)
                if dc_field:
                    risk_metrics_fields.append(dc_field)
        
        # Enhanced options market analysis section (if any meaningful data)
        if options_data_fields:
            prompt_sections.append(f"""
**COMPREHENSIVE OPTIONS ANALYSIS:**
- {' | '.join(options_data_fields)}""")
        
        # Risk assessment section (if any meaningful data)
        if risk_metrics_fields:
            prompt_sections.append(f"""
**RISK ASSESSMENT:**
- {' | '.join(risk_metrics_fields)}""")
        
        # Balance sheet section (if any meaningful data)
        if balance_sheet_fields:
            prompt_sections.append(f"""
**BALANCE SHEET STRENGTH:**
- {' | '.join(balance_sheet_fields)}""")
        
        # Cash flow section (if any meaningful data)
        if cash_flow_fields:
            prompt_sections.append(f"""
**CASH FLOW ANALYSIS:**
- {' | '.join(cash_flow_fields)}""")
        
        # Share structure section (if any meaningful data)
        if share_structure_fields:
            sections_included.append(f"Share Structure ({len(share_structure_fields)} fields)")
            logger.info(f"Including Share Structure: {share_structure_fields}")
            prompt_sections.append(f"""
**SHARE STRUCTURE:**
- {' | '.join(share_structure_fields)}""")
        
        # Moving averages section (if any meaningful data)
        if moving_averages_fields:
            sections_included.append(f"Moving Averages ({len(moving_averages_fields)} fields)")
            logger.info(f"Including Moving Averages: {moving_averages_fields}")
            prompt_sections.append(f"""
**MOVING AVERAGES:**
- {' | '.join(moving_averages_fields)}""")
        
        # Income statement section with quarter date and EPS estimates
        income_statement_fields = []
        income_statement = enhanced_stock_data.get('income_statement', {})
        
        # Quarter date
        quarter_date = income_statement.get('quarter_date') or income_statement.get('period_end_date')
        if quarter_date:
            income_statement_fields.append(f"Quarter End: {quarter_date}")
        
        # EPS estimates - current year and next year
        eps_estimate_current = fundamentals.get('eps_estimate_current_year') or analyst_sentiment.get('eps_estimate_current_year')
        if eps_estimate_current:
            eps_current_field = format_field("EPS Est (Current Year)", eps_estimate_current, "", 'currency')
            if eps_current_field:
                income_statement_fields.append(eps_current_field)
                
        eps_estimate_next = fundamentals.get('eps_estimate_next_year') or analyst_sentiment.get('eps_estimate_next_year')
        if eps_estimate_next:
            eps_next_field = format_field("EPS Est (Next Year)", eps_estimate_next, "", 'currency')
            if eps_next_field:
                income_statement_fields.append(eps_next_field)
        
        # Revenue
        revenue = income_statement.get('total_revenue')
        if revenue:
            if revenue > 1000:  # Billions
                income_statement_fields.append(f"Revenue: ${revenue/1000:.1f}B")
            else:
                income_statement_fields.append(f"Revenue: ${revenue:.0f}M")
        
        # Gross profit and margin
        gross_profit = income_statement.get('gross_profit')
        if gross_profit:
            if gross_profit > 1000:
                income_statement_fields.append(f"Gross Profit: ${gross_profit/1000:.1f}B")
            else:
                income_statement_fields.append(f"Gross Profit: ${gross_profit:.0f}M")
        
        gross_margin = income_statement.get('gross_margin')
        if gross_margin:
            income_statement_fields.append(f"Gross Margin: {gross_margin:.1f}%")
            
        # Operating income
        operating_income = income_statement.get('operating_income')
        if operating_income:
            if abs(operating_income) > 1000:
                income_statement_fields.append(f"Operating Income: ${operating_income/1000:.1f}B")
            else:
                income_statement_fields.append(f"Operating Income: ${operating_income:.0f}M")
                
        # Net income
        net_income = income_statement.get('net_income')
        if net_income:
            if abs(net_income) > 1000:
                income_statement_fields.append(f"Net Income: ${net_income/1000:.1f}B")
            else:
                income_statement_fields.append(f"Net Income: ${net_income:.0f}M")
                
        # EBITDA
        ebitda = income_statement.get('ebitda')
        if ebitda:
            if abs(ebitda) > 1000:
                income_statement_fields.append(f"EBITDA: ${ebitda/1000:.1f}B")
            else:
                income_statement_fields.append(f"EBITDA: ${ebitda:.0f}M")
        
        if income_statement_fields:
            prompt_sections.append(f"""
**INCOME STATEMENT:**
- {' | '.join(income_statement_fields)}""")
        
        # Dividend & calendar section (if any meaningful data)
        dividend_calendar_info = []
        dividend_calendar_info.extend(dividend_fields)
        dividend_calendar_info.extend(earnings_info)
        
        # Separate dividend analysis section for critical dividend metrics
        if dividend_fields:
            sections_included.append(f"Dividend Analysis ({len(dividend_fields)} fields)")
            logger.info(f"Including Dividend Analysis: {dividend_fields}")
            prompt_sections.append(f"""
**DIVIDEND ANALYSIS (CRITICAL):**
- {' | '.join(dividend_fields)}""")
        
        # Calendar risk section for earnings timing
        if earnings_info:
            prompt_sections.append(f"""
**CALENDAR RISK:**
- {' | '.join(earnings_info)}""")
        elif dividend_calendar_info:
            # Fallback: if no earnings but have dividend calendar info
            prompt_sections.append(f"""
**DIVIDEND & CALENDAR RISK:**
- {' | '.join(dividend_calendar_info)}""")
        
        # Market sentiment section (if any meaningful data)
        if market_sentiment_fields:
            prompt_sections.append(f"""
**MARKET SENTIMENT:**
- {' | '.join(market_sentiment_fields)}""")
        
        # Analyst sentiment section (if any meaningful data)
        if analyst_fields:
            prompt_sections.append(f"""
**ANALYST SENTIMENT:**
- {' | '.join(analyst_fields)}""")
        
        # Earnings calendar section (if any meaningful data)
        if earnings_calendar_items:
            prompt_sections.append(f"""
**EARNINGS CALENDAR:**
{chr(10).join(earnings_calendar_items)}""")
        
        # News section (always included)
        prompt_sections.append(f"""
**RECENT NEWS & DEVELOPMENTS:**
{full_news_articles}""")
        
        # Economic context section with detailed events
        economic_context_content = f"""**ECONOMIC CONTEXT:**
- Market Volatility Regime: {volatility_regime}
- Sector Performance: {sector_context}

**DETAILED ECONOMIC CALENDAR:**
{chr(10).join(economic_events_detailed) if economic_events_detailed else 'No detailed economic events available'}

**SUMMARY - KEY ECONOMIC EVENTS:**
{economic_events_summary}"""
        
        prompt_sections.append(economic_context_content)
        
        # Data completeness section
        completeness_score = enhanced_stock_data.get('completeness_score', 0)
        data_sources = []
        if fundamentals: data_sources.append('Fundamentals')
        if tech_indicators: data_sources.append('Technical')
        if calendar_events or earnings: data_sources.append('Calendar')
        if balance_sheet: data_sources.append('Balance Sheet')
        if cash_flow: data_sources.append('Cash Flow')
        if analyst_sentiment: data_sources.append('Analyst Data')
        if news: data_sources.append('News')
        
        if data_sources:
            prompt_sections.append(f"""
**DATA COMPLETENESS:**
- Completeness Score: {completeness_score:.1f}%
- Available Data: {', '.join(data_sources)}""")
        
        # Combine all sections
        data_sections = ''.join(prompt_sections)
        
        # LOG: Final prompt summary
        logger.info("=== FINAL PROMPT SUMMARY ===")
        logger.info(f"Sections included: {sections_included}")
        logger.info(f"Data sources available: {data_sources}")
        logger.info(f"Completeness score: {completeness_score:.1f}%")
        logger.info(f"Total prompt sections: {len(prompt_sections)}")
        
        # Build the complete prompt
        prompt = f"""You are an expert options strategist specializing in Poor Man's Covered Call (PMCC) analysis. Analyze this specific PMCC opportunity using the comprehensive dataset provided and score it from 0-100.

{data_sections}

## ENHANCED PMCC SCORING FRAMEWORK (0-100 Total)

**COMPREHENSIVE DATA ANALYSIS:**
This analysis incorporates {len(data_sources)} data sources with {completeness_score:.1f}% completeness.

## SCORING FRAMEWORK (0-100 Total)

**1. EXECUTION RISK (30 points)**
- Liquidity Quality: Bid/ask spreads, volume, open interest for both legs
- Greeks Alignment: Delta positioning, theta decay optimization, vega risk
- Strike Selection: LEAPS depth ITM, short call distance OTM
- Spread Management: Ability to adjust, roll, or close positions

**2. FINANCIAL STABILITY (25 points)**
- Cash Flow Health: Free cash flow generation, operating cash trends
- Balance Sheet Strength: Debt levels, working capital, financial flexibility
- Earnings Quality: Profit margins, revenue growth sustainability
- Survival Probability: Ability to weather 6-12 month holding period

**3. CALENDAR & EVENT RISK (25 points)**
- Dividend Timing: Ex-dividend dates relative to short expiration cycles
- Earnings Proximity: Volatility impact, early assignment risk
- Economic Sensitivity: Sector exposure to macro events, tariffs, policy changes
- Volatility Events: Known catalysts that could disrupt strategy

**4. TECHNICAL SETUP (20 points)**
- Entry Timing: Current price relative to support/resistance, trend
- Volatility Environment: IV vs HV, volatility term structure
- Momentum Indicators: RSI, trend strength, reversal signals
- Risk/Reward Profile: Probability-weighted return expectations

## CRITICAL PMCC CONSIDERATIONS

**RED FLAGS (Avoid if present):**
- LEAPS volume < 10 or extremely wide spreads
- Company burning cash with high debt loads
- Ex-dividend date within 45 days of short expiration
- Earnings within 7 days of short expiration
- Sector in severe distress or regulatory pressure

**GREEN FLAGS (Favorable conditions):**
- Stable/growing free cash flow with manageable debt
- Technical oversold condition with solid fundamentals
- High implied volatility environment with mean reversion potential
- Strong options liquidity with tight spreads
- Clear catalyst for recovery during LEAPS holding period

## RESPONSE FORMAT

Provide your analysis as a JSON object with this exact structure:

{{
"symbol": "{symbol}",
"pmcc_score": 0,
"execution_risk_score": 0,
"financial_stability_score": 0,
"calendar_event_score": 0,
"technical_setup_score": 0,
"recommendation": "buy/hold/avoid",
"confidence_level": 0,
"key_risks": ["risk1", "risk2", "risk3"],
"key_opportunities": ["opp1", "opp2", "opp3"],
"management_strategy": "Specific guidance for position management",
"entry_timing": "Immediate/Wait for X condition/Avoid",
"exit_conditions": ["condition1", "condition2"],
"position_sizing": "X% of portfolio based on risk profile"
}}

## ANALYSIS INSTRUCTIONS

1. **Prioritize PMCC-specific factors** over general stock analysis
2. **Quantify risks with specific dates and probabilities** when possible
3. **Focus on 3-6 month time horizon** matching typical PMCC holding periods
4. **Consider position sizing implications** based on liquidity and volatility
5. **Provide actionable management guidance** for different market scenarios
6. **Weight recent news and events** more heavily than historical data
7. **Account for current market regime** in volatility and sentiment analysis

**Critical**: Base your analysis strictly on the provided comprehensive dataset. Respond only with the JSON structure above - no additional commentary."""
        
        # LOG: Final prompt (truncated for logging)
        logger.info("=== FINAL PROMPT (first 1000 chars) ===")
        logger.info(prompt[:1000])
        logger.info("=== FINAL PROMPT (last 1000 chars) ===")
        logger.info(prompt[-1000:])
        logger.info(f"Total prompt length: {len(prompt)} characters")
        
        return prompt
    
    def _parse_single_opportunity_response(self, response: Message, processing_time_ms: float) -> Dict[str, Any]:
        """Parse Claude's response for single opportunity analysis."""
        try:
            # Extract the content from the response
            content = response.content[0].text if response.content else ""
            
            # Try to parse as JSON
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                # Try to extract JSON from response if it's wrapped in other text
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    raise ClaudeError(f"Invalid JSON response: {str(e)}")
            
            # Add usage metadata if available
            if hasattr(response, 'usage') and response.usage:
                data['usage'] = {
                    'input_tokens': response.usage.input_tokens,
                    'output_tokens': response.usage.output_tokens
                }
            
            # Add processing time and model information
            data['processing_time_ms'] = processing_time_ms
            data['model_used'] = response.model if hasattr(response, 'model') else self.model
            data['analysis_timestamp'] = datetime.now().isoformat()
            
            # Validate required fields for new format
            required_fields = ['symbol', 'pmcc_score', 'recommendation']
            for field in required_fields:
                if field not in data:
                    raise ClaudeError(f"Missing required field in response: {field}")
            
            # Map new format fields to expected format for compatibility
            if 'execution_risk_score' in data:
                data['comprehensive_risk_score'] = data['execution_risk_score']
            if 'financial_stability_score' in data:
                data['fundamental_health_score'] = data['financial_stability_score']
            if 'calendar_event_score' in data:
                data['calendar_event_score'] = data['calendar_event_score']
            if 'technical_setup_score' in data:
                data['technical_momentum_score'] = data['technical_setup_score']
            
            # Create analysis summary from key components
            if 'analysis_summary' not in data:
                risks = data.get('key_risks', [])
                opps = data.get('key_opportunities', [])
                data['analysis_summary'] = f"PMCC opportunity with score {data['pmcc_score']}/100. Key risks: {', '.join(risks[:2])}. Key opportunities: {', '.join(opps[:2])}."
            
            # Add detailed reasoning if not present
            if 'detailed_reasoning' not in data:
                data['detailed_reasoning'] = data.get('management_strategy', 'See individual score components for detailed analysis.')
            
            # Validate score range
            score = data.get('pmcc_score', 0)
            if not isinstance(score, (int, float)) or score < 0 or score > 100:
                raise ClaudeError(f"Invalid PMCC score: {score}. Must be 0-100.")
            
            return data
            
        except Exception as e:
            logger.error(f"Error parsing single opportunity response: {e}")
            logger.debug(f"Raw response content: {response.content if response else 'No response'}")
            raise ClaudeError(f"Failed to parse single opportunity response: {str(e)}") from e
    
    def _create_stock_summary(self, stock: EnhancedStockData) -> str:
        """Create a concise summary of stock data for the prompt."""
        symbol = stock.symbol
        quote = stock.quote
        fundamentals = stock.fundamentals
        technical = stock.technical_indicators
        risk = stock.risk_metrics
        
        # Basic info
        price = f"${quote.last}" if quote.last else "N/A"
        volume = f"{quote.volume:,}" if quote.volume else "N/A"
        
        # Fundamental metrics
        pe = f"PE: {fundamentals.pe_ratio}" if fundamentals and fundamentals.pe_ratio else "PE: N/A"
        roe = f"ROE: {fundamentals.roe}%" if fundamentals and fundamentals.roe else "ROE: N/A"
        margin = f"Margin: {fundamentals.profit_margin}%" if fundamentals and fundamentals.profit_margin else "Margin: N/A"
        debt_equity = f"D/E: {fundamentals.debt_to_equity}" if fundamentals and fundamentals.debt_to_equity else "D/E: N/A"
        
        # Technical metrics
        beta = f"Beta: {technical.beta}" if technical and technical.beta else "Beta: N/A"
        sector = f"Sector: {technical.sector}" if technical and technical.sector else "Sector: N/A"
        
        # Calendar events
        earnings_date = "N/A"
        div_date = "N/A"
        if stock.upcoming_earnings_date:
            days_to_earnings = (stock.upcoming_earnings_date - date.today()).days
            earnings_date = f"Earnings in {days_to_earnings} days"
        if stock.next_ex_dividend_date:
            days_to_div = (stock.next_ex_dividend_date - date.today()).days
            div_date = f"Ex-div in {days_to_div} days"
        
        # Options availability
        options_info = "No options data" if not stock.has_options_data else f"{len(stock.options_chain.contracts)} option contracts"
        
        # Risk metrics
        inst_ownership = f"Inst Own: {risk.institutional_ownership}%" if risk and risk.institutional_ownership else "Inst Own: N/A"
        analyst_rating = f"Analyst: {risk.analyst_rating_avg}" if risk and risk.analyst_rating_avg else "Analyst: N/A"
        
        return f"""**{symbol}** - {price} (Vol: {volume})
   Fundamentals: {pe}, {roe}, {margin}, {debt_equity}
   Technical: {beta}, {sector}
   Calendar: {earnings_date}, {div_date}
   Options: {options_info}
   Risk: {inst_ownership}, {analyst_rating}"""
    
    async def _execute_with_retry(self, prompt: str) -> Message:
        """Execute Claude API request with retry logic."""
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )
                
                return response
                
            except anthropic.RateLimitError as e:
                last_error = e
                if attempt < self.max_retries:
                    wait_time = self.retry_backoff * (2 ** attempt)
                    logger.warning(f"Rate limit hit, retrying in {wait_time}s (attempt {attempt + 1})")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise RateLimitError(f"Rate limit exceeded after {self.max_retries} retries") from e
            
            except anthropic.AuthenticationError as e:
                raise AuthenticationError(f"Authentication failed: {str(e)}") from e
            
            except anthropic.BadRequestError as e:
                # Don't retry bad requests
                raise ClaudeError(f"Bad request: {str(e)}") from e
            
            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    wait_time = self.retry_backoff * (2 ** attempt)
                    logger.warning(f"Request failed, retrying in {wait_time}s (attempt {attempt + 1}): {e}")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise ClaudeError(f"Request failed after {self.max_retries} retries: {str(e)}") from e
        
        # Should not reach here, but just in case
        raise ClaudeError(f"Request failed: {str(last_error)}") from last_error
    
    def _parse_analysis_response(self, response: Message, processing_time_ms: float) -> ClaudeAnalysisResponse:
        """Parse Claude's response into structured data."""
        try:
            # Extract the content from the response
            content = response.content[0].text if response.content else ""
            
            # Try to parse as JSON
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                # Try to extract JSON from response if it's wrapped in other text
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    raise ClaudeError(f"Invalid JSON response: {str(e)}")
            
            # Add usage metadata if available
            usage_data = {}
            if hasattr(response, 'usage') and response.usage:
                usage_data = {
                    'input_tokens': response.usage.input_tokens,
                    'output_tokens': response.usage.output_tokens
                }
                data['usage'] = usage_data
            
            # Add model information
            data['model'] = response.model if hasattr(response, 'model') else self.model
            
            # Create the analysis response
            analysis = ClaudeAnalysisResponse.from_claude_response(data, processing_time_ms)
            
            # Validate that we have exactly 10 opportunities (or close to it)
            if len(analysis.opportunities) == 0:
                raise ClaudeError("No opportunities found in Claude response")
            elif len(analysis.opportunities) > 15:
                # Trim to top 10 if Claude provided more than expected
                analysis.opportunities = analysis.get_top_opportunities(10)
                logger.warning("Claude returned more than 10 opportunities, trimmed to top 10")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error parsing Claude response: {e}")
            logger.debug(f"Raw response content: {response.content if response else 'No response'}")
            raise ClaudeError(f"Failed to parse Claude response: {str(e)}") from e
    
    def _update_stats(self, response: Optional[Message], success: bool):
        """Update client statistics."""
        self._stats['total_requests'] += 1
        
        if success:
            self._stats['successful_requests'] += 1
            
            if response and hasattr(response, 'usage') and response.usage:
                self._stats['total_input_tokens'] += response.usage.input_tokens
                self._stats['total_output_tokens'] += response.usage.output_tokens
                
                # Rough cost estimation (Claude 3.5 Sonnet pricing as of 2024)
                input_cost = response.usage.input_tokens * 0.000003  # $3/1M input tokens
                output_cost = response.usage.output_tokens * 0.000015  # $15/1M output tokens
                self._stats['total_cost_estimate'] += input_cost + output_cost
        else:
            self._stats['failed_requests'] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client usage statistics."""
        return {
            **self._stats,
            'success_rate': (
                self._stats['successful_requests'] / self._stats['total_requests'] 
                if self._stats['total_requests'] > 0 else 0
            ),
            'avg_input_tokens': (
                self._stats['total_input_tokens'] / self._stats['successful_requests']
                if self._stats['successful_requests'] > 0 else 0
            ),
            'avg_output_tokens': (
                self._stats['total_output_tokens'] / self._stats['successful_requests']
                if self._stats['successful_requests'] > 0 else 0
            )
        }
    
    async def health_check(self) -> bool:
        """Perform a simple health check."""
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=50,
                temperature=0,
                messages=[
                    {
                        "role": "user",
                        "content": "Reply with just 'OK' to confirm you're working."
                    }
                ]
            )
            
            return bool(response and response.content)
            
        except Exception as e:
            logger.error(f"Claude health check failed: {e}")
            return False