#!/usr/bin/env python3
"""Test Claude prompt generation with financial data"""

import json
import os
import sys
from datetime import datetime
import asyncio

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from src.config import get_settings
from src.api.providers.enhanced_eodhd_provider import EnhancedEODHDProvider
from src.api.claude_client import ClaudeClient
from src.models.pmcc_models import PMCCCandidate, PMCCAnalysis
from src.api.data_provider import ProviderType

async def test_claude_prompt():
    """Test that Claude prompt includes all financial data"""
    print("\n=== Testing Claude Prompt with Financial Data ===\n")
    
    # Initialize components
    settings = get_settings()
    
    # Create EODHD provider
    if not settings.eodhd or not settings.eodhd.api_token:
        print("✗ EODHD API token not configured")
        return
        
    eodhd_config = {
        'api_token': settings.eodhd.api_token,
        'enable_caching': True,
        'cache_ttl_hours': 24
    }
    
    eodhd_provider = EnhancedEODHDProvider(ProviderType.EODHD, eodhd_config)
    
    # Create Claude client
    if not settings.claude or not settings.claude.api_key:
        print("✗ Claude API key not configured")
        return
        
    claude_config = {
        'api_key': settings.claude.api_key,
        'max_tokens': settings.claude.max_tokens,
        'temperature': settings.claude.temperature,
        'rate_limit': settings.claude.rate_limit_per_minute,
        'retry_max_attempts': settings.claude.retry_max_attempts,
        'retry_delay': settings.claude.retry_delay,
        'daily_request_limit': settings.claude.daily_request_limit,
        'daily_cost_limit': settings.claude.daily_cost_limit
    }
    
    claude_client = ClaudeClient(ProviderType.CLAUDE, claude_config)
    
    # Test with KSS stock
    symbol = 'KSS'
    print(f"Testing with symbol: {symbol}")
    
    try:
        # Get enhanced data
        print("\n1. Fetching enhanced data from EODHD...")
        response = await eodhd_provider.get_comprehensive_enhanced_data(symbol)
        
        if response.is_success:
            enhanced_data = response.data
            print("✓ Enhanced data fetched successfully")
            
            # Check fundamentals
            fundamentals = enhanced_data.get('fundamentals', {})
            print(f"\nFundamentals has {len([s for s in ['balance_sheet', 'cash_flow', 'income_statement', 'analyst_sentiment'] if s in fundamentals])} financial sections")
            
            # Create mock opportunity
            from src.models.api_models import OptionContract
            
            # Mock LEAPS contract
            mock_leaps = OptionContract(
                option_symbol="KSS250117C00040000",
                strike=40.0,
                expiration=datetime(2025, 1, 17).date(),
                dte=365,
                bid=14.5,
                ask=15.5,
                mid=15.0,
                last=15.0,
                volume=100,
                open_interest=500,
                delta=0.8,
                gamma=0.01,
                theta=-0.02,
                vega=0.15,
                iv=0.25
            )
            
            # Mock short call
            mock_short = OptionContract(
                option_symbol="KSS240315C00055000",
                strike=55.0,
                expiration=datetime(2024, 3, 15).date(),
                dte=30,
                bid=1.8,
                ask=2.2,
                mid=2.0,
                last=2.0,
                volume=200,
                open_interest=1000,
                delta=0.3,
                gamma=0.02,
                theta=-0.05,
                vega=0.10,
                iv=0.30
            )
            
            mock_opportunity = PMCCCandidate(
                symbol=symbol,
                underlying_price=50.0,
                leaps_option=mock_leaps,
                short_option=mock_short,
                analysis=PMCCAnalysis(
                    max_profit=200.0,
                    max_loss=1300.0,
                    break_even=53.0,
                    risk_reward_ratio=0.15,
                    probability_of_profit=0.65,
                    score=75.0,
                    recommendation="Good opportunity"
                ),
                risk_metrics=None,
                enhanced_stock_data=enhanced_data
            )
            
            # Convert enhanced data to dict (simulating scanner's conversion)
            from src.analysis.scanner import PMCCScanner
            scanner = PMCCScanner(None, settings)  # Provider not needed for this test
            enhanced_dict = scanner._enhanced_stock_data_to_dict(enhanced_data)
            
            # Build request data
            request_data = {
                'symbol': symbol,
                'opportunity': mock_opportunity,
                'enhanced_stock_data': enhanced_dict
            }
            
            # Build Claude prompt
            print("\n2. Building Claude prompt...")
            prompt = claude_client._build_single_opportunity_prompt(request_data)
            
            # Check if financial sections are in the prompt
            print("\n3. Checking Claude prompt for financial data:")
            
            sections_to_check = ['balance_sheet', 'cash_flow', 'income_statement', 'analyst_sentiment', 'historical_prices']
            sections_found = {}
            
            for section in sections_to_check:
                pattern = f'"{section}":'
                sections_found[section] = pattern in prompt
                status = "✓" if sections_found[section] else "✗"
                print(f"  {status} {section}: {'Found' if sections_found[section] else 'NOT FOUND'} in prompt")
            
            # Save prompt for inspection
            with open('test_claude_prompt_complete.json', 'w') as f:
                f.write(prompt)
            print("\n✓ Full prompt saved to test_claude_prompt_complete.json")
            
            # Parse and analyze the prompt content
            try:
                # Extract JSON from prompt
                json_start = prompt.find('```json') + 7
                json_end = prompt.find('```', json_start)
                prompt_json_str = prompt[json_start:json_end].strip()
                prompt_json = json.loads(prompt_json_str)
                
                enhanced_data_in_prompt = prompt_json.get('enhanced_stock_data', {})
                
                print("\n4. Analyzing data content in prompt:")
                for section in sections_to_check:
                    if section in enhanced_data_in_prompt:
                        section_data = enhanced_data_in_prompt[section]
                        if isinstance(section_data, dict):
                            non_zero = sum(1 for v in section_data.values() if v and v != 0)
                            print(f"  ✓ {section}: {len(section_data)} fields ({non_zero} non-zero)")
                            
                            # Show sample values
                            if section == 'balance_sheet':
                                print(f"     - total_assets: ${section_data.get('total_assets', 'N/A')}M")
                                print(f"     - total_debt: ${section_data.get('total_debt', 'N/A')}M")
                            elif section == 'cash_flow':
                                print(f"     - free_cash_flow: ${section_data.get('free_cash_flow', 'N/A')}M")
                        elif isinstance(section_data, list):
                            print(f"  ✓ {section}: {len(section_data)} items")
                        else:
                            print(f"  ⚠ {section}: Present but not dict/list")
                    else:
                        print(f"  ✗ {section}: Missing from enhanced_stock_data")
                        
                # Check if all sections made it through
                missing_sections = [s for s in sections_to_check if s not in enhanced_data_in_prompt]
                if missing_sections:
                    print(f"\n⚠ Missing sections: {', '.join(missing_sections)}")
                else:
                    print("\n✅ All financial sections successfully included in Claude prompt!")
                    
            except Exception as e:
                print(f"\n⚠ Error parsing prompt JSON: {e}")
                
        else:
            print(f"✗ Failed to fetch enhanced data: {response.error}")
            
    except Exception as e:
        print(f"\n✗ Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await eodhd_provider.close()
        if hasattr(claude_client, 'close'):
            await claude_client.close()

if __name__ == "__main__":
    asyncio.run(test_claude_prompt())