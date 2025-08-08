#!/usr/bin/env python3
"""
Simple debug script to capture the exact Claude prompt being generated for KSS.

This script uses the existing test framework to capture KSS data.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Dict, Any
from datetime import datetime

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.api.claude_client import ClaudeClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PromptCapturingClaudeClient(ClaudeClient):
    """Claude client that captures the prompt without sending it to the API."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_prompt = None
        self.last_enhanced_stock_data = None
        self.last_opportunity_data = None
    
    async def analyze_single_opportunity(
        self,
        opportunity_data: Dict[str, Any],
        enhanced_stock_data: Dict[str, Any],
        market_context: Dict[str, Any] = None
    ):
        """Capture the prompt but don't send to API."""
        
        # Store the data for analysis
        self.last_opportunity_data = opportunity_data.copy()
        self.last_enhanced_stock_data = enhanced_stock_data.copy()
        
        # Build the prompt (this will trigger our logging)
        self.last_prompt = self._build_single_opportunity_prompt(
            opportunity_data, enhanced_stock_data, market_context
        )
        
        logger.info(f"Captured prompt for {opportunity_data.get('symbol', 'Unknown')}")
        logger.info(f"Prompt length: {len(self.last_prompt)} characters")
        
        # Return a mock response without calling the API
        from src.models.api_models import APIResponse, APIStatus
        return APIResponse(
            status=APIStatus.OK,
            data={
                'symbol': opportunity_data.get('symbol'),
                'pmcc_score': 999,  # Mock score to indicate this was captured
                'prompt_captured': True,
                'recommendation': 'mock',
                'confidence_level': 100
            }
        )


def create_kss_opportunity_data() -> Dict[str, Any]:
    """Create KSS PMCC opportunity data for testing."""
    return {
        'symbol': 'KSS',
        'underlying_price': 18.45,
        'pmcc_score': 72.3,
        'total_score': 72.3,
        'liquidity_score': 65.0,
        
        'strategy_details': {
            'net_debit': 845.00,
            'credit_received': 125.00,
            'max_profit': 970.00,
            'max_loss': 720.00,
            'breakeven_price': 25.45,
            'risk_reward_ratio': 1.35,
            'strategy_type': 'Poor_Mans_Covered_Call'
        },
        
        'leaps_option': {
            'option_symbol': 'KSS250117C00015000',
            'strike': 15.00,
            'expiration': '2025-01-17',
            'dte': 365,
            'delta': 0.78,
            'gamma': 0.025,
            'theta': -0.15,
            'vega': 0.35,
            'iv': 45.2,
            'bid': 4.20,
            'ask': 4.50,
            'mid': 4.35,
            'last': 4.40,
            'volume': 25,
            'open_interest': 150,
            'bid_size': 5,
            'ask_size': 3
        },
        
        'short_option': {
            'option_symbol': 'KSS241215C00020000',
            'strike': 20.00,
            'expiration': '2024-12-15',
            'dte': 45,
            'delta': 0.32,
            'gamma': 0.045,
            'theta': -0.06,
            'vega': 0.12,
            'iv': 52.8,
            'bid': 1.20,
            'ask': 1.35,
            'mid': 1.28,
            'last': 1.25,
            'volume': 15,
            'open_interest': 85,
            'bid_size': 2,
            'ask_size': 4
        }
    }


def create_kss_enhanced_stock_data() -> Dict[str, Any]:
    """Create sample enhanced EODHD stock data for KSS."""
    return {
        'symbol': 'KSS',
        'completeness_score': 85.5,
        
        'fundamentals': {
            'company_info': {
                'name': "Kohl's Corporation",
                'sector': 'Consumer Discretionary',
                'industry': 'Department Stores',
                'market_cap_mln': 2150.0,
                'employees': 85000
            },
            'financial_health': {
                'eps_ttm': 1.23,
                'profit_margin': 2.8,
                'operating_margin': 4.2,
                'gross_margin': 38.5,
                'roe': 8.5,
                'roa': 3.2,
                'revenue_growth_yoy': -2.3,
                'earnings_growth_yoy': -15.2,
                'dividend_yield': 8.5,
                'revenue_ttm': 18900000000
            },
            'valuation_metrics': {
                'pe_ratio': 15.2,
                'price_to_sales': 0.12,
                'price_to_book': 1.8,
                'peg_ratio': 1.25,
                'enterprise_value': 2800000000,
                'ev_to_revenue': 0.15,
                'ev_to_ebitda': 8.2
            },
            'stock_technicals': {
                'beta': 1.85,
                '52_week_high': 26.35,
                '52_week_low': 12.15,
                'short_interest': 12.5,
                'avg_volume_30d': 3500000
            },
            'dividend_info': {
                'payout_ratio': 85.2,
                'dividend_date': '2024-03-15',
                'ex_dividend_date': '2024-02-28'
            }
        },
        
        'technical_indicators': {
            'rsi': 45.2,
            'volatility': 42.8,
            'atr': 0.85,
            'sma_20': 19.25,
            'sma_50': 20.15,
            'sma_200': 22.45,
            'ema_21': 18.95,
            'macd': -0.25,
            'macd_signal': -0.18,
            'macd_histogram': -0.07,
            'bollinger_upper': 21.50,
            'bollinger_lower': 16.80
        },
        
        'recent_news': [
            {
                'date': '2024-01-25',
                'title': "Kohl's reports mixed Q4 results as turnaround continues",
                'content': "Kohl's Corporation reported fourth-quarter earnings that beat expectations on the bottom line but missed on revenue. The department store chain continues its turnaround efforts amid challenging retail conditions. Same-store sales declined 3.4% year-over-year, better than the expected 5% decline. Management emphasized progress in digital transformation and inventory optimization initiatives."
            },
            {
                'date': '2024-01-20',
                'title': "Retail sector faces headwinds as consumer spending shifts",
                'content': "Department stores including Kohl's face continued pressure from changing consumer preferences and economic uncertainty. Analysts note that while some retailers are adapting well to omnichannel strategies, traditional department stores need to accelerate transformation efforts to remain competitive."
            }
        ],
        
        'earnings_calendar': [
            {
                'date': '2024-03-05',
                'event_type': 'earnings_release',
                'eps_estimate': 0.78,
                'eps_actual': None
            }
        ],
        
        'economic_context': [
            {
                'date': '2024-02-01',
                'event': 'FOMC Meeting',
                'country': 'US',
                'impact': 'High'
            },
            {
                'date': '2024-02-15',
                'event': 'Retail Sales Report',
                'country': 'US',
                'impact': 'Medium'
            }
        ],
        
        'balance_sheet': {
            'total_debt': 1950000000,
            'total_assets': 12500000000,
            'working_capital': 850000000,
            'debt_to_equity': 1.25,
            'current_ratio': 1.15
        },
        
        'cash_flow': {
            'free_cash_flow': 245000000,
            'operating_cash_flow': 680000000,
            'cash_per_share': 2.85
        },
        
        'historical_prices': [
            {'date': '2024-01-25', 'adjusted_close': 18.45, 'high': 19.20, 'low': 18.10, 'volume': 4200000},
            {'date': '2024-01-24', 'adjusted_close': 18.80, 'high': 19.15, 'low': 18.35, 'volume': 3800000},
            {'date': '2024-01-23', 'adjusted_close': 19.25, 'high': 19.55, 'low': 18.90, 'volume': 3500000},
            {'date': '2024-01-22', 'adjusted_close': 19.10, 'high': 19.45, 'low': 18.75, 'volume': 3200000},
            {'date': '2024-01-19', 'adjusted_close': 18.95, 'high': 19.35, 'low': 18.60, 'volume': 3100000},
            {'date': '2024-01-18', 'adjusted_close': 19.40, 'high': 19.85, 'low': 19.05, 'volume': 2900000},
            {'date': '2024-01-17', 'adjusted_close': 19.60, 'high': 19.95, 'low': 19.25, 'volume': 2800000},
            {'date': '2024-01-16', 'adjusted_close': 19.85, 'high': 20.15, 'low': 19.45, 'volume': 2700000},
            {'date': '2024-01-12', 'adjusted_close': 20.05, 'high': 20.40, 'low': 19.70, 'volume': 2600000},
            {'date': '2024-01-11', 'adjusted_close': 20.20, 'high': 20.55, 'low': 19.85, 'volume': 2500000}
        ],
        
        'analyst_sentiment': {
            'avg_rating': 2.8,
            'target_price': 22.50,
            'strong_buy': 0,
            'buy': 2,
            'hold': 8,
            'sell': 3,
            'strong_sell': 1
        },
        
        'calendar_events': [
            {
                'date': '2024-03-05',
                'event_type': 'earnings_release',
                'event_date': '2024-03-05'
            },
            {
                'date': '2024-02-28',
                'event_type': 'ex_dividend_date',
                'event_date': '2024-02-28'
            }
        ],
        
        'risk_metrics': {
            'credit_rating': 'BBB-',
            'earnings_volatility': 25.8,
            'debt_coverage_ratio': 2.1
        },
        
        'options_chain': {
            'underlying': 'KSS',
            'underlying_price': 18.45,
            'contract_count': 245
        }
    }


async def debug_kss_prompt():
    """Debug the KSS prompt generation."""
    
    logger.info("=== STARTING KSS CLAUDE PROMPT DEBUG ===")
    
    try:
        # Create mock Claude client
        mock_claude = PromptCapturingClaudeClient()
        
        logger.info("Mock Claude client initialized")
        
        # Create KSS test data
        opportunity_data = create_kss_opportunity_data()
        enhanced_stock_data = create_kss_enhanced_stock_data()
        market_context = {
            'volatility_regime': 'High',
            'interest_rate_trend': 'Stable',
            'market_sentiment': 'Neutral',
            'vix_level': 22.5,
            'sector_context': 'Retail sector under pressure'
        }
        
        logger.info(f"Created test data for {opportunity_data['symbol']}")
        logger.info(f"Enhanced data completeness: {enhanced_stock_data.get('completeness_score', 0):.1f}%")
        
        # Analyze the opportunity (this will capture the prompt)
        result = await mock_claude.analyze_single_opportunity(
            opportunity_data, enhanced_stock_data, market_context
        )
        
        # Capture the data
        if mock_claude.last_prompt and mock_claude.last_enhanced_stock_data:
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Save enhanced stock data
            enhanced_data_file = f'kss_enhanced_stock_data_{timestamp}.json'
            with open(enhanced_data_file, 'w') as f:
                json.dump(mock_claude.last_enhanced_stock_data, f, indent=2, default=str)
            logger.info(f"Enhanced stock data saved to {enhanced_data_file}")
            
            # Save opportunity data
            opportunity_data_file = f'kss_opportunity_data_{timestamp}.json'
            with open(opportunity_data_file, 'w') as f:
                json.dump(mock_claude.last_opportunity_data, f, indent=2, default=str)
            logger.info(f"Opportunity data saved to {opportunity_data_file}")
            
            # Save the prompt
            prompt_file = f'kss_claude_prompt_{timestamp}.txt'
            with open(prompt_file, 'w') as f:
                f.write("=== KSS CLAUDE PROMPT DEBUG ===\n")
                f.write(f"Generated at: {datetime.now().isoformat()}\n")
                f.write(f"Prompt length: {len(mock_claude.last_prompt)} characters\n")
                f.write("\n" + "="*80 + "\n")
                f.write("FULL PROMPT:\n")
                f.write("="*80 + "\n")
                f.write(mock_claude.last_prompt)
            logger.info(f"Claude prompt saved to {prompt_file}")
            
            # Create a comprehensive analysis file
            analysis_file = f'kss_prompt_analysis_{timestamp}.txt'
            with open(analysis_file, 'w') as f:
                f.write("=== KSS CLAUDE PROMPT ANALYSIS ===\n")
                f.write(f"Generated at: {datetime.now().isoformat()}\n\n")
                
                f.write("ENHANCED STOCK DATA STRUCTURE:\n")
                f.write("-" * 50 + "\n")
                for key, value in mock_claude.last_enhanced_stock_data.items():
                    if isinstance(value, dict):
                        f.write(f"{key}: dict with {len(value)} keys\n")
                        for subkey, subvalue in value.items():
                            if isinstance(subvalue, dict):
                                f.write(f"  {subkey}: dict with {len(subvalue)} keys - {list(subvalue.keys())}\n")
                            elif isinstance(subvalue, list):
                                f.write(f"  {subkey}: list with {len(subvalue)} items\n")
                            else:
                                f.write(f"  {subkey}: {type(subvalue).__name__} = {str(subvalue)[:50]}...\n")
                    elif isinstance(value, list):
                        f.write(f"{key}: list with {len(value)} items\n")
                        if value and isinstance(value[0], dict):
                            f.write(f"  Sample item keys: {list(value[0].keys())}\n")
                    else:
                        f.write(f"{key}: {type(value).__name__} = {str(value)[:100]}...\n")
                
                f.write(f"\nOPPORTUNITY DATA STRUCTURE:\n")
                f.write("-" * 50 + "\n")
                for key, value in mock_claude.last_opportunity_data.items():
                    if isinstance(value, dict):
                        f.write(f"{key}: dict with {len(value)} keys - {list(value.keys())}\n")
                    else:
                        f.write(f"{key}: {type(value).__name__} = {value}\n")
                
                f.write(f"\nPROMPT STATISTICS:\n")
                f.write("-" * 50 + "\n")
                f.write(f"Total length: {len(mock_claude.last_prompt)} characters\n")
                f.write(f"Line count: {mock_claude.last_prompt.count(chr(10)) + 1}\n")
                f.write(f"Word count: {len(mock_claude.last_prompt.split())}\n")
                
                # Find key sections in prompt
                sections = [
                    "COMPANY OVERVIEW",
                    "FINANCIAL HEALTH", 
                    "VALUATION METRICS",
                    "TECHNICAL INDICATORS",
                    "RECENT NEWS",
                    "BALANCE SHEET",
                    "CASH FLOW",
                    "ANALYST SENTIMENT"
                ]
                
                f.write("\nSECTIONS FOUND IN PROMPT:\n")
                f.write("-" * 50 + "\n")
                for section in sections:
                    if section in mock_claude.last_prompt:
                        f.write(f"✓ {section}\n")
                    else:
                        f.write(f"✗ {section}\n")
                
                f.write(f"\nPROMPT PREVIEW (first 1000 chars):\n")
                f.write("-" * 50 + "\n")
                f.write(mock_claude.last_prompt[:1000])
                f.write("\n...\n")
            
            logger.info(f"Prompt analysis saved to {analysis_file}")
            
            # Print key information
            print("\n" + "="*80)
            print("KSS CLAUDE PROMPT DEBUG COMPLETED")
            print("="*80)
            print(f"Enhanced data file: {enhanced_data_file}")
            print(f"Opportunity data file: {opportunity_data_file}")
            print(f"Prompt file: {prompt_file}")
            print(f"Analysis file: {analysis_file}")
            print("="*80)
            
            # Show key data structure info
            print("\nENHANCED STOCK DATA KEYS:")
            for key, value in mock_claude.last_enhanced_stock_data.items():
                if isinstance(value, dict):
                    print(f"  {key}: dict with {len(value)} keys")
                elif isinstance(value, list):
                    print(f"  {key}: list with {len(value)} items")
                else:
                    print(f"  {key}: {type(value).__name__}")
            
            print(f"\nPrompt length: {len(mock_claude.last_prompt):,} characters")
            print(f"Completeness score: {enhanced_stock_data.get('completeness_score', 0):.1f}%")
            
            return {
                'enhanced_data_file': enhanced_data_file,
                'opportunity_data_file': opportunity_data_file, 
                'prompt_file': prompt_file,
                'analysis_file': analysis_file,
                'enhanced_stock_data': mock_claude.last_enhanced_stock_data,
                'prompt': mock_claude.last_prompt
            }
        else:
            logger.error("No prompt or enhanced data captured!")
            return None
            
    except Exception as e:
        logger.error(f"Error during KSS debug: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


if __name__ == "__main__":
    # Run the debug
    result = asyncio.run(debug_kss_prompt())
    
    if result:
        print("\n✅ KSS Claude prompt debug completed successfully!")
        print("✅ Check the generated files for detailed analysis")
    else:
        print("\n❌ KSS Claude prompt debug failed!")
        sys.exit(1)