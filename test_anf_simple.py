#!/usr/bin/env python3
"""Simple test to debug ANF issue."""

import json
from datetime import datetime, date

# Load the JSON data
with open('data/option_chains_complete_20250811_221025.json', 'r') as f:
    data = json.load(f)

chains = data.get('option_chains', {})
anf = chains.get('ANF', {})

print(f"Stock price: {anf.get('underlying_price')}")
print(f"Total contracts: {len(anf.get('contracts', []))}")

# Check LEAPS
contracts = anf.get('contracts', [])
leaps_count = 0
itm_leaps = 0
stock_price = float(anf.get('underlying_price', 0))

for c in contracts:
    if c.get('side') == 'call':
        dte = c.get('days_to_expiration', 0)
        if 180 <= dte <= 730:  # LEAPS range
            leaps_count += 1
            strike = float(c.get('strike', 0))
            if stock_price > strike:  # ITM
                itm_leaps += 1
                if itm_leaps <= 5:  # Show first 5
                    delta = c.get('delta', 'N/A')
                    oi = c.get('open_interest', 'N/A')
                    print(f"\nITM LEAPS #{itm_leaps}:")
                    print(f"  Strike: ${strike} (stock: ${stock_price})")
                    print(f"  DTE: {dte}")
                    print(f"  Delta: {delta}")
                    print(f"  OI: {oi}")
                    print(f"  Bid/Ask: ${c.get('bid')}/{c.get('ask')}")

print(f"\nTotal LEAPS: {leaps_count}")
print(f"ITM LEAPS: {itm_leaps}")

# Check why they might be rejected
print("\n🔍 Checking first ITM LEAPS against filters:")
for c in contracts:
    if c.get('side') == 'call':
        dte = c.get('days_to_expiration', 0)
        if 180 <= dte <= 730:
            strike = float(c.get('strike', 0))
            if stock_price > strike:
                delta = c.get('delta', 0)
                oi = c.get('open_interest', 0)
                bid = c.get('bid', 0)
                ask = c.get('ask', 0)
                
                print(f"\nStrike ${strike}:")
                print(f"  ✓ DTE: {dte} (180-730)")
                print(f"  {'✓' if 0.65 <= delta <= 0.95 else '✗'} Delta: {delta} (0.65-0.95)")
                print(f"  {'✓' if oi >= 1 else '✗'} OI: {oi} (≥1)")
                
                # Premium check
                if ask and stock_price:
                    premium_pct = ask / stock_price
                    print(f"  {'✓' if premium_pct <= 0.60 else '✗'} Premium: {premium_pct*100:.1f}% (≤60%)")
                
                # All passed?
                if (180 <= dte <= 730 and 
                    0.65 <= delta <= 0.95 and 
                    oi >= 1 and 
                    ask and stock_price and ask/stock_price <= 0.60):
                    print("  ✅ SHOULD PASS ALL FILTERS!")
                
                break  # Just check first one