#!/usr/bin/env python3
"""
Simple PMCC Scanner runner - bypasses complex configuration for quick testing
"""

import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime

# Add src to path
script_dir = Path(__file__).parent
project_root = script_dir.parent
src_dir = project_root / "src"
sys.path.insert(0, str(src_dir))

# Load environment
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

# Import required modules
from api.marketdata_client import MarketDataClient
from analysis.scanner import PMCCScanner
from analysis.stock_screener import StockScreener
from analysis.options_analyzer import OptionsAnalyzer
from analysis.risk_calculator import RiskCalculator

async def run_simple_scan():
    """Run a simplified PMCC scan"""
    print("=" * 80)
    print("PMCC Scanner - Simple Run Mode")
    print("=" * 80)
    print(f"Scan Time: {datetime.now()}")
    print("=" * 80)
    
    # Get API token
    api_token = os.getenv('MARKETDATA_API_TOKEN')
    if not api_token:
        print("ERROR: MARKETDATA_API_TOKEN not found in environment")
        return
    
    print("\n📊 Step 1: Initializing components...")
    
    # Initialize components with minimal config
    api_client = MarketDataClient(
        api_token=api_token,
        plan_type='free',  # Assuming free plan for now
        base_url='https://api.marketdata.app/v1'
    )
    
    stock_screener = StockScreener()
    options_analyzer = OptionsAnalyzer()
    risk_calculator = RiskCalculator()
    
    # Create scanner
    scanner = PMCCScanner(
        api_client=api_client,
        stock_screener=stock_screener,
        options_analyzer=options_analyzer,
        risk_calculator=risk_calculator
    )
    
    print("✅ Components initialized")
    
    print("\n📈 Step 2: Running PMCC scan...")
    
    # Define a small universe of stocks to scan
    test_symbols = ['AAPL', 'MSFT', 'AMD', 'NVDA', 'META']
    
    try:
        # Run the scan
        results = await scanner.scan_stocks(
            symbols=test_symbols,
            min_score=70.0
        )
        
        print(f"\n✅ Scan complete! Found {len(results.opportunities)} opportunities")
        
        # Display results
        if results.opportunities:
            print("\n🎯 Top PMCC Opportunities:")
            print("-" * 80)
            
            for i, opp in enumerate(results.opportunities[:5], 1):
                print(f"\n{i}. {opp.symbol} - Score: {opp.score:.1f}/100")
                print(f"   Stock Price: ${opp.stock_price:.2f}")
                print(f"   LEAPS: {opp.long_expiration} ${opp.long_strike}C @ ${opp.long_premium:.2f}")
                print(f"   Short: {opp.short_expiration} ${opp.short_strike}C @ ${opp.short_premium:.2f}")
                print(f"   Net Cost: ${opp.net_debit:.2f}")
                print(f"   Max Profit: ${opp.max_profit:.2f}")
                print(f"   Annual Return: {opp.annualized_return_pct:.1f}%")
        else:
            print("\nNo opportunities found meeting criteria")
        
        # Save results
        output_dir = project_root / "data"
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"scan_results_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            import json
            json.dump(results.to_dict(), f, indent=2, default=str)
        
        print(f"\n💾 Results saved to: {output_file}")
        
        # Show notification preview (without actually sending)
        if results.opportunities:
            print("\n📱 Notification Preview:")
            print("-" * 40)
            top_pick = results.opportunities[0]
            print(f"🎯 PMCC Alert: {top_pick.symbol}")
            print(f"Score: {top_pick.score:.1f}/100")
            print(f"Return: {top_pick.annualized_return_pct:.0f}% annualized")
            print(f"Action: Buy {top_pick.long_expiration} ${top_pick.long_strike}C")
            print(f"        Sell {top_pick.short_expiration} ${top_pick.short_strike}C")
            print("-" * 40)
            
    except Exception as e:
        print(f"\n❌ Error during scan: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main entry point"""
    await run_simple_scan()

if __name__ == "__main__":
    asyncio.run(main())