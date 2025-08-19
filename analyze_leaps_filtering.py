#!/usr/bin/env python3
"""Analyze why only 1 LEAPS is passing filters."""

import json
from datetime import datetime, date
from decimal import Decimal

# Load the most recent option chain data
with open('data/option_chains_complete_20250811_223152.json', 'r') as f:
    data = json.load(f)

chains = data.get('option_chains', {})
anf = chains.get('ANF', {})
stock_price = Decimal(str(anf.get('underlying_price', 0)))
contracts = anf.get('contracts', [])

print(f"Stock price: ${stock_price}")
print(f"Total contracts: {len(contracts)}")

# Filter criteria from .env
MIN_DTE = 180
MAX_DTE = 730
MIN_DELTA = 0.65
MAX_DELTA = 0.95
MAX_PREMIUM_PCT = 0.99  # 99% of stock price
MIN_OI = 1
MAX_SPREAD_PCT = 0  # Disabled
MAX_EXTRINSIC_PCT = 0  # Disabled

# Analyze LEAPS
calls = [c for c in contracts if c.get('side') == 'call']
print(f"\nTotal CALL contracts: {len(calls)}")

# Count rejections
dte_rejected = 0
delta_rejected = 0
oi_rejected = 0
not_itm_rejected = 0
pricing_rejected = 0
premium_rejected = 0
passed = []

print("\n" + "="*80)
print("ANALYZING EACH POTENTIAL LEAPS:")
print("="*80)

for c in calls:
    strike = Decimal(str(c.get('strike', 0)))
    dte = c.get('days_to_expiration', 0)
    delta = c.get('delta', 0)
    oi = c.get('open_interest', 0)
    bid = c.get('bid')
    ask = c.get('ask')
    
    # Track reasons for rejection
    reasons = []
    
    # DTE check
    if not (MIN_DTE <= dte <= MAX_DTE):
        dte_rejected += 1
        reasons.append(f"DTE={dte} not in {MIN_DTE}-{MAX_DTE}")
        continue
    
    # Delta check
    if not (MIN_DELTA <= delta <= MAX_DELTA):
        delta_rejected += 1
        reasons.append(f"Delta={delta} not in {MIN_DELTA}-{MAX_DELTA}")
        continue
        
    # OI check
    if oi < MIN_OI:
        oi_rejected += 1
        reasons.append(f"OI={oi} < {MIN_OI}")
        continue
        
    # ITM check
    is_itm = stock_price > strike
    if not is_itm:
        not_itm_rejected += 1
        reasons.append(f"Not ITM (stock=${stock_price}, strike=${strike})")
        continue
        
    # Pricing check
    if not bid or not ask or bid <= 0:
        pricing_rejected += 1
        reasons.append(f"Invalid pricing (bid={bid}, ask={ask})")
        continue
        
    # Premium check
    if ask and stock_price:
        premium_pct = Decimal(str(ask)) / stock_price
        if premium_pct > MAX_PREMIUM_PCT:
            premium_rejected += 1
            reasons.append(f"Premium {premium_pct*100:.1f}% > {MAX_PREMIUM_PCT*100}%")
            continue
    
    # This one passed!
    passed.append(c)
    print(f"\n✅ PASSED: Strike=${strike}, DTE={dte}, Delta={delta}, OI={oi}, Bid/Ask=${bid}/${ask}")

print("\n" + "="*80)
print("SUMMARY:")
print("="*80)
print(f"DTE out of range: {dte_rejected}")
print(f"Delta out of range: {delta_rejected}")
print(f"OI too low: {oi_rejected}")
print(f"Not ITM: {not_itm_rejected}")
print(f"Invalid pricing: {pricing_rejected}")
print(f"Premium too high: {premium_rejected}")
print(f"TOTAL PASSED: {len(passed)}")

# Show all LEAPS in the right DTE range to understand better
print("\n" + "="*80)
print("ALL CONTRACTS IN LEAPS DTE RANGE (180-730):")
print("="*80)
leaps_range = [c for c in calls if 180 <= c.get('days_to_expiration', 0) <= 730]
print(f"Found {len(leaps_range)} contracts in LEAPS date range")

for c in sorted(leaps_range, key=lambda x: x.get('delta', 0), reverse=True)[:10]:
    strike = c.get('strike')
    dte = c.get('days_to_expiration')
    delta = c.get('delta')
    oi = c.get('open_interest')
    bid = c.get('bid')
    ask = c.get('ask')
    is_itm = stock_price > strike
    
    print(f"\nStrike ${strike}:")
    print(f"  DTE: {dte}")
    print(f"  Delta: {delta}")
    print(f"  OI: {oi}")
    print(f"  Bid/Ask: ${bid}/${ask}")
    print(f"  ITM: {is_itm}")
    print(f"  Passes delta? {MIN_DELTA <= delta <= MAX_DELTA}")
    print(f"  Passes OI? {oi >= MIN_OI}")