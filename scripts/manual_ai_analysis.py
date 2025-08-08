#!/usr/bin/env python3
"""
Manual AI Analysis Script for PMCC Scanner

This script allows testing AI-enhanced analysis on existing scan results
without re-running the full scan. It loads existing JSON scan results,
extracts opportunities, runs enhanced data collection, and performs Claude AI analysis.

Usage:
    python scripts/manual_ai_analysis.py --input data/pmcc_scan_20250806_220918.json
    python scripts/manual_ai_analysis.py --input data/pmcc_scan_20250806_220918.json --top 5
    python scripts/manual_ai_analysis.py --input data/pmcc_scan_20250806_220918.json --symbols KSS,QS,SOUN
    python scripts/manual_ai_analysis.py --input data/pmcc_scan_20250806_220918.json --interactive
    python scripts/manual_ai_analysis.py --list-files  # Show available scan files
"""

import argparse
import json
import logging
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from decimal import Decimal

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.config.settings import get_settings
    from src.api.provider_factory import SyncDataProviderFactory
    from src.api.providers.enhanced_eodhd_provider import EnhancedEODHDProvider
    from src.api.claude_client import ClaudeClient
    import asyncio
    from src.analysis.claude_integration import ClaudeIntegrationManager
    from src.models.api_models import EnhancedStockData, ClaudeAnalysisResponse
    from src.utils.logger import setup_logging
    from src.utils.error_handler import get_error_handler
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the project root or have proper Python path setup")
    sys.exit(1)


class ManualAIAnalyzer:
    """
    Manual AI analysis tool for testing AI enhancement on existing scan results.
    
    This class provides functionality to:
    1. Load existing JSON scan results
    2. Extract and filter opportunities
    3. Run enhanced data collection
    4. Perform Claude AI analysis
    5. Display results with AI insights
    """
    
    def __init__(self):
        """Initialize the manual analyzer."""
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)
        
        # Initialize providers
        self.provider_factory = SyncDataProviderFactory(self.settings)
        self.enhanced_eodhd = None
        self.claude_client = None
        self.claude_integration = ClaudeIntegrationManager()
        
        # Initialize components if available
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize enhanced providers if API keys are available."""
        try:
            # Initialize Enhanced EODHD Provider (like in the scanner)
            if self.settings.eodhd_api_token:
                from src.api.data_provider import ProviderType
                # Try to get the provider config from the provider factory
                try:
                    eodhd_provider = self.provider_factory.get_provider("get_stock_quote", preferred_provider=ProviderType.EODHD)
                    if eodhd_provider and hasattr(eodhd_provider, 'config'):
                        self.enhanced_eodhd = EnhancedEODHDProvider(
                            provider_type=ProviderType.EODHD,
                            config=eodhd_provider.config
                        )
                        self.logger.info("Enhanced EODHD provider initialized")
                    else:
                        # Fallback to manual config
                        config = {'api_token': self.settings.eodhd_api_token}
                        self.enhanced_eodhd = EnhancedEODHDProvider(ProviderType.EODHD, config)
                        self.logger.info("Enhanced EODHD provider initialized (fallback)")
                except Exception as e:
                    # Final fallback
                    config = {'api_token': self.settings.eodhd_api_token}
                    self.enhanced_eodhd = EnhancedEODHDProvider(ProviderType.EODHD, config)
                    self.logger.info("Enhanced EODHD provider initialized (direct)")
            else:
                self.logger.warning("EODHD API token not available - enhanced data collection disabled")
            
            # Initialize Claude Client
            if self.settings.claude_api_key:
                self.claude_client = ClaudeClient(
                    api_key=self.settings.claude_api_key,
                    model=getattr(self.settings, 'claude_model', 'claude-3-5-sonnet-20241022'),
                    max_tokens=getattr(self.settings, 'claude_max_tokens', 4000),
                    temperature=getattr(self.settings, 'claude_temperature', 0.1)
                )
                self.logger.info("Claude client initialized")
            else:
                self.logger.warning("Claude API key not available - AI analysis disabled")
                
        except Exception as e:
            self.logger.error(f"Error initializing providers: {e}")
    
    def list_available_scan_files(self, data_dir: str = "data") -> List[str]:
        """
        List available scan result files.
        
        Args:
            data_dir: Directory to search for scan files
            
        Returns:
            List of available scan file paths
        """
        data_path = project_root / data_dir
        if not data_path.exists():
            self.logger.warning(f"Data directory not found: {data_path}")
            return []
        
        scan_files = []
        for file_path in data_path.glob("pmcc_scan_*.json"):
            scan_files.append(str(file_path))
        
        # Sort by modification time (newest first)
        scan_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        return scan_files
    
    def load_scan_results(self, file_path: str) -> Dict[str, Any]:
        """
        Load scan results from JSON file.
        
        Args:
            file_path: Path to the scan results JSON file
            
        Returns:
            Parsed scan results dictionary
            
        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If file is not valid JSON
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Scan results file not found: {file_path}")
        
        try:
            with open(file_path, 'r') as f:
                results = json.load(f)
            
            self.logger.info(f"Loaded scan results from {file_path}")
            self.logger.info(f"Scan ID: {results.get('scan_id', 'Unknown')}")
            self.logger.info(f"Opportunities found: {results.get('stats', {}).get('opportunities_found', 0)}")
            
            return results
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Invalid JSON in scan results file: {e}")
    
    def extract_opportunities(self, scan_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract opportunities from scan results.
        
        Args:
            scan_results: Loaded scan results dictionary
            
        Returns:
            List of opportunity dictionaries
        """
        opportunities = scan_results.get('top_opportunities', [])
        if not opportunities:
            self.logger.warning("No opportunities found in scan results")
        else:
            self.logger.info(f"Extracted {len(opportunities)} opportunities")
        
        return opportunities
    
    def filter_opportunities(
        self, 
        opportunities: List[Dict[str, Any]], 
        top_n: Optional[int] = None,
        symbols: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Filter opportunities by criteria.
        
        Args:
            opportunities: List of all opportunities
            top_n: Take only top N opportunities by rank
            symbols: Filter to specific symbols
            
        Returns:
            Filtered list of opportunities
        """
        filtered = opportunities.copy()
        
        # Filter by symbols if specified
        if symbols:
            symbols_upper = [s.upper() for s in symbols]
            filtered = [opp for opp in filtered if opp.get('symbol', '').upper() in symbols_upper]
            self.logger.info(f"Filtered to {len(filtered)} opportunities for symbols: {', '.join(symbols_upper)}")
        
        # Take top N if specified
        if top_n is not None:
            filtered = filtered[:top_n]
            self.logger.info(f"Taking top {top_n} opportunities")
        
        return filtered
    
    def interactive_symbol_selection(self, opportunities: List[Dict[str, Any]]) -> List[str]:
        """
        Interactive symbol selection from available opportunities.
        
        Args:
            opportunities: List of available opportunities
            
        Returns:
            List of selected symbols
        """
        if not opportunities:
            print("No opportunities available for selection")
            return []
        
        print("\nAvailable opportunities:")
        print("=" * 80)
        for i, opp in enumerate(opportunities[:20], 1):  # Show up to 20
            symbol = opp.get('symbol', 'Unknown')
            score = opp.get('total_score', 0)
            rank = opp.get('rank', i)
            price = opp.get('underlying_price', 0)
            print(f"{i:2d}. {symbol:<6} - Score: {score:6.2f} - Rank: {rank:2d} - Price: ${price:.2f}")
        
        if len(opportunities) > 20:
            print(f"... and {len(opportunities) - 20} more")
        
        print("\nSelection options:")
        print("1. Enter symbol names (comma-separated): AAPL,MSFT,GOOGL")
        print("2. Enter numbers from list above (comma-separated): 1,2,3")
        print("3. Enter 'top N' for top N opportunities: top 5")
        print("4. Enter 'all' for all opportunities")
        
        while True:
            selection = input("\nYour selection: ").strip()
            
            if not selection:
                continue
            
            # Handle 'all'
            if selection.lower() == 'all':
                return [opp.get('symbol', '') for opp in opportunities]
            
            # Handle 'top N'
            if selection.lower().startswith('top '):
                try:
                    n = int(selection.split()[1])
                    if n <= 0:
                        print("Please enter a positive number")
                        continue
                    return [opp.get('symbol', '') for opp in opportunities[:n]]
                except (IndexError, ValueError):
                    print("Invalid format. Use 'top 5' for example")
                    continue
            
            # Handle comma-separated values
            parts = [p.strip() for p in selection.split(',')]
            symbols = []
            
            # Check if all parts are numbers (indices)
            if all(p.isdigit() for p in parts):
                try:
                    indices = [int(p) - 1 for p in parts]  # Convert to 0-based
                    for idx in indices:
                        if 0 <= idx < len(opportunities):
                            symbols.append(opportunities[idx].get('symbol', ''))
                        else:
                            print(f"Index {idx + 1} is out of range")
                            symbols = []
                            break
                    if symbols:
                        return symbols
                except ValueError:
                    print("Invalid number format")
                    continue
            else:
                # Assume symbol names
                available_symbols = {opp.get('symbol', '').upper(): opp.get('symbol', '') for opp in opportunities}
                for part in parts:
                    symbol = part.upper()
                    if symbol in available_symbols:
                        symbols.append(available_symbols[symbol])
                    else:
                        print(f"Symbol {symbol} not found in opportunities")
                        symbols = []
                        break
                if symbols:
                    return symbols
            
            print("Invalid selection. Please try again.")
    
    async def collect_enhanced_data(self, symbols: List[str]) -> Dict[str, EnhancedStockData]:
        """
        Collect enhanced data for the given symbols.
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            Dictionary mapping symbols to enhanced stock data
        """
        if not self.enhanced_eodhd:
            self.logger.error("Enhanced EODHD provider not available")
            return {}
        
        enhanced_data = {}
        self.logger.info(f"Collecting enhanced data for {len(symbols)} symbols...")
        
        for symbol in symbols:
            try:
                self.logger.info(f"Collecting enhanced data for {symbol}...")
                response = await self.enhanced_eodhd.get_enhanced_stock_data(symbol)
                if response and response.status.value == "ok" and response.data:
                    enhanced_data[symbol] = response.data
                    self.logger.info(f"Successfully collected enhanced data for {symbol}")
                else:
                    error_msg = response.error.message if response and response.error else "No data returned"
                    self.logger.warning(f"No enhanced data for {symbol}: {error_msg}")
            except Exception as e:
                self.logger.error(f"Error collecting enhanced data for {symbol}: {e}")
        
        return enhanced_data
    
    async def run_claude_analysis(
        self, 
        opportunities: List[Dict[str, Any]], 
        enhanced_data: Dict[str, EnhancedStockData]
    ) -> List[Dict[str, Any]]:
        """
        Run individual Claude AI analysis on each opportunity with comprehensive data.
        
        Args:
            opportunities: List of PMCC opportunities
            enhanced_data: Dictionary of enhanced stock data
            
        Returns:
            List of opportunities enhanced with Claude analysis results
        """
        if not self.claude_client:
            self.logger.error("Claude client not available")
            return opportunities
        
        enhanced_opportunities = []
        
        try:
            self.logger.info(f"Running individual Claude AI analysis on {len(opportunities)} opportunities...")
            
            # Create market context
            market_context = {
                'analysis_date': datetime.now().date().isoformat(),
                'total_opportunities': len(opportunities),
                'market_sentiment': 'neutral',
                'volatility_regime': 'normal'
            }
            
            successful_analyses = 0
            failed_analyses = 0
            
            # Analyze each opportunity individually
            for i, opportunity in enumerate(opportunities, 1):
                symbol = opportunity.get('symbol', '')
                if not symbol:
                    self.logger.warning(f"Opportunity {i} missing symbol")
                    enhanced_opportunities.append(opportunity)
                    failed_analyses += 1
                    continue
                
                try:
                    self.logger.info(f"Analyzing opportunity {i}/{len(opportunities)}: {symbol}")
                    print(f"  Analyzing {symbol} ({i}/{len(opportunities)})...")
                    
                    # Prepare opportunity data for Claude with complete PMCC details
                    opportunity_data = {
                        'symbol': symbol,
                        'underlying_price': opportunity.get('underlying_price', 0),
                        'strategy_details': {
                            'net_debit': opportunity.get('net_debit', 0),
                            'credit_received': 0,  # PMCC is a net debit strategy
                            'max_profit': opportunity.get('max_profit', 0),
                            'max_loss': opportunity.get('max_loss', 0),
                            'breakeven_price': opportunity.get('breakeven', 0),
                            'risk_reward_ratio': opportunity.get('risk_reward_ratio', 0)
                        },
                        'leaps_option': opportunity.get('long_call', {}),
                        'short_option': opportunity.get('short_call', {}),
                        'pmcc_score': opportunity.get('total_score', opportunity.get('pmcc_score', 0)),
                        'liquidity_score': opportunity.get('liquidity_score', 0)
                    }
                    
                    # Get enhanced stock data for this symbol
                    stock_data = enhanced_data.get(symbol)
                    if stock_data:
                        # Convert enhanced stock data to dictionary format
                        enhanced_stock_dict = self._enhanced_stock_data_to_dict(stock_data, opportunity)
                    else:
                        # Create minimal enhanced data from opportunity
                        enhanced_stock_dict = self._create_minimal_enhanced_data(opportunity)
                    
                    # Run individual Claude analysis
                    claude_response = await self.claude_client.analyze_single_opportunity(
                        opportunity_data,
                        enhanced_stock_dict,
                        market_context
                    )
                    
                    if claude_response.is_success and claude_response.data:
                        claude_result = claude_response.data
                        
                        # Add Claude insights to the opportunity
                        enhanced_opportunity = opportunity.copy()
                        enhanced_opportunity['ai_insights'] = claude_result
                        enhanced_opportunity['claude_score'] = claude_result.get('pmcc_score', 0)
                        enhanced_opportunity['combined_score'] = (
                            float(opportunity.get('total_score', opportunity.get('pmcc_score', 0))) * 0.6 + 
                            claude_result.get('pmcc_score', 0) * 0.4
                        )
                        enhanced_opportunity['claude_reasoning'] = claude_result.get('analysis_summary', '')
                        enhanced_opportunity['ai_recommendation'] = claude_result.get('recommendation', 'neutral')
                        enhanced_opportunity['claude_confidence'] = claude_result.get('confidence_score', 0)
                        
                        enhanced_opportunities.append(enhanced_opportunity)
                        successful_analyses += 1
                        
                        self.logger.debug(f"{symbol}: PMCC={opportunity.get('total_score', 0):.1f}, "
                                       f"Claude={claude_result.get('pmcc_score', 0):.1f}, "
                                       f"Combined={enhanced_opportunity['combined_score']:.1f}")
                    else:
                        self.logger.warning(f"Claude analysis failed for {symbol}")
                        enhanced_opportunities.append(opportunity)
                        failed_analyses += 1
                    
                except Exception as e:
                    self.logger.error(f"Error analyzing {symbol} with Claude: {e}")
                    enhanced_opportunities.append(opportunity)
                    failed_analyses += 1
                    continue
            
            success_rate = (successful_analyses / len(opportunities)) * 100 if opportunities else 0
            
            self.logger.info(f"Individual Claude AI analysis completed. "
                           f"Success: {successful_analyses}, Failed: {failed_analyses} "
                           f"(Success rate: {success_rate:.1f}%)")
            
            print(f"✅ Individual Claude AI analysis completed: {successful_analyses} successful, "
                  f"{failed_analyses} failed ({success_rate:.1f}% success rate)")
            
            return enhanced_opportunities
                
        except Exception as e:
            self.logger.error(f"Error during Claude analysis: {e}")
            return opportunities
    
    def _enhanced_stock_data_to_dict(self, enhanced_data: EnhancedStockData, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """Convert EnhancedStockData to dictionary format for Claude analysis."""
        result = {}
        
        # Quote data
        if enhanced_data.quote:
            result['quote'] = {
                'symbol': enhanced_data.quote.symbol,
                'last': float(enhanced_data.quote.last),
                'change': float(enhanced_data.quote.change) if enhanced_data.quote.change else 0,
                'change_percent': float(enhanced_data.quote.change_percent) if enhanced_data.quote.change_percent else 0,
                'volume': enhanced_data.quote.volume if enhanced_data.quote.volume else 0,
                'market_cap': float(enhanced_data.quote.market_cap) if enhanced_data.quote.market_cap else 0
            }
        
        # Fundamental data
        if enhanced_data.fundamentals:
            fund = enhanced_data.fundamentals
            result['fundamentals'] = {
                'market_capitalization': float(fund.market_capitalization) if fund.market_capitalization else 0,
                'pe_ratio': float(fund.pe_ratio) if fund.pe_ratio else 0,
                'beta': float(fund.beta) if fund.beta else 0,
                'dividend_yield': float(fund.dividend_yield) if fund.dividend_yield else 0,
                'roe': float(fund.roe) if fund.roe else 0,
                'roa': float(fund.roa) if fund.roa else 0,
                'profit_margin': float(fund.profit_margin) if fund.profit_margin else 0,
                'debt_to_equity': float(fund.debt_to_equity) if fund.debt_to_equity else 0,
                'revenue_growth': float(fund.revenue_growth) if fund.revenue_growth else 0,
                'earnings_growth': float(fund.earnings_growth) if fund.earnings_growth else 0
            }
        
        # Technical indicators
        if enhanced_data.technical_indicators:
            tech = enhanced_data.technical_indicators
            result['technical_indicators'] = {
                'rsi': float(tech.rsi) if tech.rsi else 0,
                'sma_50': float(tech.sma_50) if tech.sma_50 else 0,
                'sma_200': float(tech.sma_200) if tech.sma_200 else 0,
                'volatility': float(tech.volatility) if tech.volatility else 0,
                'bollinger_upper': float(tech.bollinger_upper) if tech.bollinger_upper else 0,
                'bollinger_lower': float(tech.bollinger_lower) if tech.bollinger_lower else 0
            }
        
        # Calendar events
        if enhanced_data.calendar_events:
            result['calendar_events'] = []
            for event in enhanced_data.calendar_events[:5]:  # Limit to 5 most recent
                result['calendar_events'].append({
                    'event_type': event.event_type,
                    'event_date': event.event_date.isoformat() if hasattr(event.event_date, 'isoformat') else str(event.event_date),
                    'description': event.description
                })
        
        # Risk metrics
        if enhanced_data.risk_metrics:
            risk = enhanced_data.risk_metrics
            result['risk_metrics'] = {
                'credit_rating': risk.credit_rating if risk.credit_rating else 'N/A',
                'earnings_volatility': float(risk.earnings_volatility) if risk.earnings_volatility else 0,
                'debt_coverage_ratio': float(risk.debt_coverage_ratio) if risk.debt_coverage_ratio else 0
            }
        
        # Options chain (if available)
        if enhanced_data.options_chain and enhanced_data.options_chain.contracts:
            result['options_chain'] = {
                'underlying': enhanced_data.options_chain.underlying,
                'underlying_price': float(enhanced_data.options_chain.underlying_price),
                'contract_count': len(enhanced_data.options_chain.contracts)
            }
        
        # PMCC analysis (add from opportunity data)
        result['pmcc_analysis'] = {
            'pmcc_score': opportunity.get('total_score', opportunity.get('pmcc_score', 0)),
            'net_debit': opportunity.get('net_debit', 0),
            'max_profit': opportunity.get('max_profit', 0),
            'max_loss': opportunity.get('max_loss', 0),
            'risk_reward_ratio': opportunity.get('risk_reward_ratio', 0),
            'breakeven': opportunity.get('breakeven', 0),
            'liquidity_score': opportunity.get('liquidity_score', 0)
        }
        
        # Completeness score
        result['completeness_score'] = enhanced_data.completeness_score
        
        return result
    
    def _create_minimal_enhanced_data(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """Create minimal enhanced data structure from opportunity data."""
        symbol = opportunity.get('symbol', '')
        
        return {
            'quote': {
                'symbol': symbol,
                'last': opportunity.get('underlying_price', 0),
                'change': 0,
                'change_percent': 0,
                'volume': 0,
                'market_cap': 0
            },
            'pmcc_analysis': {
                'pmcc_score': opportunity.get('total_score', opportunity.get('pmcc_score', 0)),
                'net_debit': opportunity.get('net_debit', 0),
                'max_profit': opportunity.get('max_profit', 0),
                'max_loss': opportunity.get('max_loss', 0),
                'risk_reward_ratio': opportunity.get('risk_reward_ratio', 0),
                'breakeven': opportunity.get('breakeven', 0),
                'liquidity_score': opportunity.get('liquidity_score', 0)
            },
            'completeness_score': 25.0  # Minimal completeness
        }
    
    def _merge_pmcc_with_enhanced_data(
        self, 
        opportunities: List[Dict[str, Any]], 
        enhanced_data: Dict[str, EnhancedStockData]
    ) -> List[EnhancedStockData]:
        """
        Merge PMCC opportunity data with enhanced stock data for Claude analysis.
        
        This method ensures that Claude receives both the complete PMCC analysis 
        (options contracts, Greeks, strategy details) and the enhanced fundamental
        data (financials, technical indicators, calendar events).
        
        Args:
            opportunities: List of PMCC opportunities from JSON exports
            enhanced_data: Dictionary of enhanced stock data by symbol
            
        Returns:
            List of EnhancedStockData objects with merged PMCC and fundamental data
        """
        from src.models.api_models import OptionChain, OptionContract, OptionSide, StockQuote
        from datetime import datetime
        from decimal import Decimal
        
        merged_data = []
        
        for opp in opportunities:
            symbol = opp.get('symbol', '')
            if not symbol:
                continue
            
            try:
                # Get the enhanced data for this symbol (may be None)
                enhanced = enhanced_data.get(symbol)
                
                # Create option contracts from PMCC data
                contracts = []
                
                # Create LEAPS contract (long call)
                long_call_data = opp.get('long_call', {})
                if long_call_data.get('option_symbol'):
                    long_contract = OptionContract(
                        option_symbol=long_call_data.get('option_symbol', ''),
                        underlying=symbol,
                        strike=Decimal(str(long_call_data.get('strike', 0))),
                        expiration=datetime.fromisoformat(long_call_data.get('expiration', datetime.now().isoformat())).date(),
                        side=OptionSide.CALL,
                        dte=long_call_data.get('dte', 0),
                        # Complete Greeks and pricing
                        bid=Decimal(str(long_call_data.get('bid', 0))) if long_call_data.get('bid') else None,
                        ask=Decimal(str(long_call_data.get('ask', 0))) if long_call_data.get('ask') else None,
                        mid=Decimal(str(long_call_data.get('mid', 0))) if long_call_data.get('mid') else None,
                        last=Decimal(str(long_call_data.get('last', 0))) if long_call_data.get('last') else None,
                        volume=long_call_data.get('volume', 0),
                        open_interest=long_call_data.get('open_interest', 0),
                        delta=Decimal(str(long_call_data.get('delta', 0))) if long_call_data.get('delta') else None,
                        gamma=Decimal(str(long_call_data.get('gamma', 0))) if long_call_data.get('gamma') else None,
                        theta=Decimal(str(long_call_data.get('theta', 0))) if long_call_data.get('theta') else None,
                        vega=Decimal(str(long_call_data.get('vega', 0))) if long_call_data.get('vega') else None,
                        iv=Decimal(str(long_call_data.get('iv', 0))) if long_call_data.get('iv') else None,
                        underlying_price=Decimal(str(opp.get('underlying_price', 0)))
                    )
                    contracts.append(long_contract)
                
                # Create short call contract
                short_call_data = opp.get('short_call', {})
                if short_call_data.get('option_symbol'):
                    short_contract = OptionContract(
                        option_symbol=short_call_data.get('option_symbol', ''),
                        underlying=symbol,
                        strike=Decimal(str(short_call_data.get('strike', 0))),
                        expiration=datetime.fromisoformat(short_call_data.get('expiration', datetime.now().isoformat())).date(),
                        side=OptionSide.CALL,
                        dte=short_call_data.get('dte', 0),
                        # Complete Greeks and pricing
                        bid=Decimal(str(short_call_data.get('bid', 0))) if short_call_data.get('bid') else None,
                        ask=Decimal(str(short_call_data.get('ask', 0))) if short_call_data.get('ask') else None,
                        mid=Decimal(str(short_call_data.get('mid', 0))) if short_call_data.get('mid') else None,
                        last=Decimal(str(short_call_data.get('last', 0))) if short_call_data.get('last') else None,
                        volume=short_call_data.get('volume', 0),
                        open_interest=short_call_data.get('open_interest', 0),
                        delta=Decimal(str(short_call_data.get('delta', 0))) if short_call_data.get('delta') else None,
                        gamma=Decimal(str(short_call_data.get('gamma', 0))) if short_call_data.get('gamma') else None,
                        theta=Decimal(str(short_call_data.get('theta', 0))) if short_call_data.get('theta') else None,
                        vega=Decimal(str(short_call_data.get('vega', 0))) if short_call_data.get('vega') else None,
                        iv=Decimal(str(short_call_data.get('iv', 0))) if short_call_data.get('iv') else None,
                        underlying_price=Decimal(str(opp.get('underlying_price', 0)))
                    )
                    contracts.append(short_contract)
                
                # Create options chain with PMCC contracts
                options_chain = OptionChain(
                    underlying=symbol,
                    underlying_price=Decimal(str(opp.get('underlying_price', 0))),
                    contracts=contracts,
                    updated=datetime.now()
                ) if contracts else None
                
                # If we have enhanced data, use it and add the PMCC options chain
                if enhanced:
                    enhanced.options_chain = options_chain
                    enhanced.pmcc_analysis = {
                        'pmcc_score': opp.get('total_score', opp.get('pmcc_score', 0)),
                        'net_debit': opp.get('net_debit', 0),
                        'max_profit': opp.get('max_profit', 0),
                        'max_loss': opp.get('max_loss', 0),
                        'risk_reward_ratio': opp.get('risk_reward_ratio', 0),
                        'breakeven': opp.get('breakeven', 0),
                        'liquidity_score': opp.get('liquidity_score', 0)
                    }
                    merged_data.append(enhanced)
                else:
                    # Create minimal enhanced data from PMCC opportunity
                    quote = StockQuote(
                        symbol=symbol,
                        last=Decimal(str(opp.get('underlying_price', 0))),
                        updated=datetime.now()
                    )
                    
                    from src.models.api_models import EnhancedStockData
                    enhanced_stock = EnhancedStockData(
                        quote=quote,
                        fundamentals=None,
                        calendar_events=[],
                        technical_indicators=None,
                        risk_metrics=None,
                        options_chain=options_chain
                    )
                    enhanced_stock.pmcc_analysis = {
                        'pmcc_score': opp.get('total_score', opp.get('pmcc_score', 0)),
                        'net_debit': opp.get('net_debit', 0),
                        'max_profit': opp.get('max_profit', 0),
                        'max_loss': opp.get('max_loss', 0),
                        'risk_reward_ratio': opp.get('risk_reward_ratio', 0),
                        'breakeven': opp.get('breakeven', 0),
                        'liquidity_score': opp.get('liquidity_score', 0)
                    }
                    enhanced_stock.calculate_completeness_score()
                    merged_data.append(enhanced_stock)
                    
            except Exception as e:
                self.logger.warning(f"Error merging PMCC data for {symbol}: {e}")
                continue
        
        self.logger.info(f"Successfully merged PMCC data with enhanced data for {len(merged_data)} opportunities")
        return merged_data
    
    def format_analysis_results(
        self, 
        opportunities: List[Dict[str, Any]], 
        enhanced_data: Dict[str, EnhancedStockData],
        claude_enhanced_opportunities: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Format the analysis results for display.
        
        Args:
            opportunities: List of original PMCC opportunities
            enhanced_data: Enhanced stock data
            claude_enhanced_opportunities: Claude-enhanced opportunities with individual analysis results
            
        Returns:
            Formatted results string
        """
        # Use Claude-enhanced opportunities if available, otherwise use original
        display_opportunities = claude_enhanced_opportunities or opportunities
        
        lines = []
        lines.append("=" * 100)
        lines.append("MANUAL AI ANALYSIS RESULTS (Individual Analysis)")
        lines.append("=" * 100)
        lines.append(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Opportunities Analyzed: {len(opportunities)}")
        lines.append(f"Enhanced Data Collected: {len(enhanced_data)}")
        
        # Count AI-analyzed opportunities
        ai_analyzed_count = sum(1 for opp in display_opportunities if opp.get('claude_score') is not None)
        lines.append(f"Claude Individual Analysis: {'✓ Success' if ai_analyzed_count > 0 else '✗ Failed/Unavailable'}")
        lines.append(f"AI Analyzed Opportunities: {ai_analyzed_count}/{len(display_opportunities)}")
        lines.append("")
        
        # Individual Opportunity Analysis
        lines.append("OPPORTUNITY ANALYSIS")
        lines.append("-" * 50)
        
        for i, opp in enumerate(display_opportunities, 1):
            symbol = opp.get('symbol', 'Unknown')
            # Use total_score from JSON exports, which is the actual PMCC score
            pmcc_score = opp.get('total_score', opp.get('pmcc_score', 0))
            
            # Check if this opportunity has Claude analysis
            has_claude_analysis = opp.get('claude_score') is not None
            combined_score = opp.get('combined_score')
            
            if has_claude_analysis and combined_score:
                lines.append(f"{i}. {symbol} - PMCC: {pmcc_score:.2f} | Combined: {combined_score:.2f}")
            else:
                lines.append(f"{i}. {symbol} - PMCC Score: {pmcc_score:.2f}")
            
            # Basic opportunity info
            price = opp.get('underlying_price', 0)
            max_profit = opp.get('max_profit', 0)
            max_loss = opp.get('max_loss', 0)
            rrr = opp.get('risk_reward_ratio', 0)
            
            lines.append(f"   Stock Price: ${price:.2f}")
            lines.append(f"   Max Profit: ${max_profit:.2f} | Max Loss: ${max_loss:.2f} | R/R: {rrr:.3f}")
            
            # Enhanced data info
            if symbol in enhanced_data:
                enhanced = enhanced_data[symbol]
                
                # Safely check fundamentals
                if hasattr(enhanced, 'fundamentals') and enhanced.fundamentals:
                    fund = enhanced.fundamentals
                    
                    # Check attributes safely
                    if hasattr(fund, 'market_capitalization') and fund.market_capitalization:
                        lines.append(f"   Market Cap: ${fund.market_capitalization:,.0f}")
                    if hasattr(fund, 'pe_ratio') and fund.pe_ratio:
                        lines.append(f"   P/E: {fund.pe_ratio:.2f}")
                    if hasattr(fund, 'beta') and fund.beta:
                        lines.append(f"   Beta: {fund.beta:.2f}")
                
                # Safely check technical indicators
                if hasattr(enhanced, 'technical_indicators') and enhanced.technical_indicators:
                    tech = enhanced.technical_indicators
                    if hasattr(tech, 'rsi') and tech.rsi:
                        lines.append(f"   RSI: {tech.rsi:.2f}")
                    if hasattr(tech, 'sma_50') and tech.sma_50:
                        lines.append(f"   50-day MA: ${tech.sma_50:.2f}")
                
                # Safely check calendar events
                if hasattr(enhanced, 'calendar_events') and enhanced.calendar_events:
                    lines.append(f"   Calendar Events: {len(enhanced.calendar_events)} events")
            
            # Claude analysis for this specific opportunity
            if has_claude_analysis:
                claude_score = opp.get('claude_score', 0)
                confidence = opp.get('claude_confidence', 0)
                recommendation = opp.get('ai_recommendation', 'neutral')
                reasoning = opp.get('claude_reasoning', '')
                
                lines.append(f"   Claude Score: {claude_score:.2f}")
                if confidence:
                    lines.append(f"   Confidence: {confidence:.1f}%")
                if recommendation and recommendation != 'neutral':
                    lines.append(f"   Recommendation: {recommendation}")
                if reasoning:
                    # Truncate reasoning for display
                    short_reasoning = reasoning[:100] + "..." if len(reasoning) > 100 else reasoning
                    lines.append(f"   Analysis: {short_reasoning}")
            
            lines.append("")
        
        # Final rankings if Claude analysis is available
        if ai_analyzed_count > 0:
            lines.append("CLAUDE AI RANKINGS (Individual Analysis)")
            lines.append("-" * 50)
            
            # Sort by combined score if available, otherwise by Claude score
            claude_analyzed_opps = [opp for opp in display_opportunities if opp.get('claude_score') is not None]
            claude_rankings = sorted(
                claude_analyzed_opps,
                key=lambda x: x.get('combined_score', x.get('claude_score', 0)),
                reverse=True
            )
            
            for i, opp in enumerate(claude_rankings[:10], 1):
                symbol = opp.get('symbol', 'Unknown')
                claude_score = opp.get('claude_score', 0)
                combined_score = opp.get('combined_score')
                confidence = opp.get('claude_confidence', 0)
                recommendation = opp.get('ai_recommendation', 'N/A')
                
                if combined_score:
                    score_display = f"Combined: {combined_score:6.2f}"
                else:
                    score_display = f"Claude: {claude_score:6.2f}"
                
                conf_display = f"({confidence:4.1f}% conf)" if confidence else "(N/A conf)"
                lines.append(f"{i:2d}. {symbol:<6} - {score_display} {conf_display} - {recommendation}")
        
        return "\n".join(lines)
    
    def save_results(self, results_text: str, output_file: Optional[str] = None):
        """
        Save analysis results to file.
        
        Args:
            results_text: Formatted results text
            output_file: Output file path (if None, auto-generate)
        """
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"manual_ai_analysis_{timestamp}.txt"
        
        output_path = project_root / "data" / output_file
        output_path.parent.mkdir(exist_ok=True)
        
        try:
            with open(output_path, 'w') as f:
                f.write(results_text)
            self.logger.info(f"Results saved to {output_path}")
            print(f"\nResults saved to: {output_path}")
        except Exception as e:
            self.logger.error(f"Error saving results: {e}")


def main():
    """Main function with command-line interface."""
    parser = argparse.ArgumentParser(
        description="Manual AI Analysis for PMCC Scanner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze latest scan file interactively
  python scripts/manual_ai_analysis.py --interactive
  
  # Analyze top 5 opportunities from specific file
  python scripts/manual_ai_analysis.py --input data/pmcc_scan_20250806_220918.json --top 5
  
  # Analyze specific symbols
  python scripts/manual_ai_analysis.py --input data/pmcc_scan_20250806_220918.json --symbols KSS,QS,SOUN
  
  # List available scan files
  python scripts/manual_ai_analysis.py --list-files
        """
    )
    
    parser.add_argument(
        '--input', '-i',
        type=str,
        help='Path to scan results JSON file'
    )
    
    parser.add_argument(
        '--top', '-t',
        type=int,
        help='Analyze top N opportunities by score'
    )
    
    parser.add_argument(
        '--symbols', '-s',
        type=str,
        help='Comma-separated list of symbols to analyze (e.g., AAPL,MSFT,GOOGL)'
    )
    
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Interactive mode for file and symbol selection'
    )
    
    parser.add_argument(
        '--list-files',
        action='store_true',
        help='List available scan result files and exit'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output file for results (default: auto-generated)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose logging'
    )
    
    parser.add_argument(
        '--data-dir',
        type=str,
        default='data',
        help='Directory containing scan result files (default: data)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logger = setup_logging()
    logger.setLevel(log_level)
    # Set console handler level if verbose
    if args.verbose:
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setLevel(log_level)
    
    # Initialize analyzer
    try:
        analyzer = ManualAIAnalyzer()
    except Exception as e:
        logger.error(f"Failed to initialize analyzer: {e}")
        sys.exit(1)
    
    # List files and exit if requested
    if args.list_files:
        scan_files = analyzer.list_available_scan_files(args.data_dir)
        if scan_files:
            print("Available scan result files:")
            print("=" * 50)
            for i, file_path in enumerate(scan_files, 1):
                file_name = Path(file_path).name
                mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                file_size = os.path.getsize(file_path) / 1024 / 1024  # MB
                print(f"{i:2d}. {file_name}")
                print(f"     Modified: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"     Size: {file_size:.1f} MB")
                print()
        else:
            print("No scan result files found")
        sys.exit(0)
    
    # Determine input file
    input_file = args.input
    if args.interactive or not input_file:
        scan_files = analyzer.list_available_scan_files(args.data_dir)
        if not scan_files:
            print("No scan result files found")
            sys.exit(1)
        
        if len(scan_files) == 1:
            input_file = scan_files[0]
            print(f"Using only available scan file: {Path(input_file).name}")
        else:
            print("Available scan result files:")
            for i, file_path in enumerate(scan_files[:10], 1):  # Show up to 10
                file_name = Path(file_path).name
                mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                print(f"{i:2d}. {file_name} ({mod_time.strftime('%Y-%m-%d %H:%M')})")
            
            if len(scan_files) > 10:
                print(f"... and {len(scan_files) - 10} more")
            
            while True:
                selection = input("\nSelect file number (or 'latest' for most recent): ").strip()
                if selection.lower() == 'latest' or selection == '1':
                    input_file = scan_files[0]
                    break
                try:
                    idx = int(selection) - 1
                    if 0 <= idx < len(scan_files):
                        input_file = scan_files[idx]
                        break
                    else:
                        print("Invalid selection")
                except ValueError:
                    print("Please enter a number or 'latest'")
    
    if not input_file:
        print("No input file specified")
        sys.exit(1)
    
    # Load scan results
    try:
        scan_results = analyzer.load_scan_results(input_file)
    except Exception as e:
        logger.error(f"Failed to load scan results: {e}")
        sys.exit(1)
    
    # Extract opportunities
    opportunities = analyzer.extract_opportunities(scan_results)
    if not opportunities:
        print("No opportunities found in scan results")
        sys.exit(1)
    
    # Determine symbols to analyze
    symbols_to_analyze = None
    if args.symbols:
        symbols_to_analyze = [s.strip() for s in args.symbols.split(',')]
    elif args.interactive:
        symbols_to_analyze = analyzer.interactive_symbol_selection(opportunities)
        if not symbols_to_analyze:
            print("No symbols selected")
            sys.exit(1)
    
    # Filter opportunities
    filtered_opportunities = analyzer.filter_opportunities(
        opportunities, 
        top_n=args.top,
        symbols=symbols_to_analyze
    )
    
    if not filtered_opportunities:
        print("No opportunities match the filtering criteria")
        sys.exit(1)
    
    print(f"\nAnalyzing {len(filtered_opportunities)} opportunities...")
    
    # Run the async analysis
    async def run_analysis():
        # Collect enhanced data
        symbols = [opp.get('symbol') for opp in filtered_opportunities if opp.get('symbol')]
        enhanced_data = await analyzer.collect_enhanced_data(symbols)
        
        # Run Claude analysis (now returns enhanced opportunities)
        claude_enhanced_opportunities = await analyzer.run_claude_analysis(filtered_opportunities, enhanced_data)
        
        return enhanced_data, claude_enhanced_opportunities
    
    # Run the async operations
    enhanced_data, claude_enhanced_opportunities = asyncio.run(run_analysis())
    
    # Format and display results
    results_text = analyzer.format_analysis_results(
        filtered_opportunities, enhanced_data, claude_enhanced_opportunities
    )
    
    print("\n" + results_text)
    
    # Save results if output file specified
    if args.output or args.interactive:
        output_file = args.output
        if args.interactive and not output_file:
            save = input("\nSave results to file? (y/N): ").strip().lower()
            if save in ['y', 'yes']:
                output_file = input("Enter filename (or press Enter for auto-generated): ").strip()
                if not output_file:
                    output_file = None
        
        if output_file is not None:
            analyzer.save_results(results_text, output_file)


if __name__ == "__main__":
    main()