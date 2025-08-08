#!/usr/bin/env python3
"""Check the final earnings calendar format in scan results."""

import json
from datetime import datetime

# Load the latest scan results
with open('data/pmcc_scan_20250808_181204.json', 'r') as f:
    data = json.load(f)

print("EARNINGS CALENDAR FORMAT CHECK")
print("="*80)

# Navigate to the earnings_calendar - it might be in different places
earnings_calendar = None

# Check in AI insights
if data['top_opportunities']:
    opp = data['top_opportunities'][0]
    ai_insights = opp.get('ai_insights', {})
    
    # Look for earnings_calendar in AI insights
    if 'earnings_calendar' in ai_insights:
        earnings_calendar = ai_insights['earnings_calendar']
        print("✅ Found earnings_calendar in AI insights")
    else:
        print("❌ No earnings_calendar in AI insights")
        
        # Check if it's elsewhere in the opportunity data
        if 'earnings_calendar' in opp:
            earnings_calendar = opp['earnings_calendar']
            print("✅ Found earnings_calendar at opportunity level")

if earnings_calendar:
    print(f"\nTotal earnings events: {len(earnings_calendar)}")
    
    # Check what we have
    today = datetime.now()
    future_events = []
    past_events = []
    
    for event in earnings_calendar:
        print(f"\n{'='*60}")
        print(f"Event:")
        
        # Check which date to use
        report_date = event.get('report_date', '')
        quarter_date = event.get('date', '')
        
        # Determine if future based on report_date
        is_future = False
        display_date = quarter_date
        if report_date:
            display_date = report_date
            try:
                report_dt = datetime.strptime(report_date, '%Y-%m-%d')
                is_future = report_dt.date() > today.date()
            except:
                pass
        elif quarter_date:
            try:
                quarter_dt = datetime.strptime(quarter_date, '%Y-%m-%d')
                is_future = quarter_dt.date() > today.date()
            except:
                pass
        
        status = "FUTURE" if is_future else "HISTORICAL"
        
        print(f"  Status: {status}")
        print(f"  Quarter End: {quarter_date}")
        print(f"  Report Date: {report_date}")
        print(f"  Time: {event.get('time', 'N/A')}")
        print(f"  EPS Estimate: {event.get('eps_estimate', 'N/A')}")
        print(f"  EPS Actual: {event.get('eps_actual', 'N/A')}")
        print(f"  Difference: {event.get('difference', 'N/A')}")
        print(f"  Surprise %: {event.get('percent', 'N/A')}")
        
        if is_future:
            future_events.append(event)
        else:
            past_events.append(event)
    
    print(f"\n{'='*60}")
    print(f"SUMMARY:")
    print(f"  Future earnings: {len(future_events)}")
    print(f"  Historical earnings: {len(past_events)}")
    
    if len(past_events) > 0:
        print(f"\n✅ Historical earnings included for pattern analysis")
    else:
        print(f"\n❌ No historical earnings data")
        
    if any(e.get('report_date') for e in earnings_calendar):
        print(f"✅ Report dates included")
    else:
        print(f"❌ Report dates missing")
else:
    print("\n❌ No earnings_calendar found in scan results")
    
    # Debug: show structure
    if data['top_opportunities']:
        opp = data['top_opportunities'][0]
        print(f"\nDebug - Top-level keys in opportunity: {list(opp.keys())}")
        if 'ai_insights' in opp:
            print(f"Debug - Keys in ai_insights: {list(opp['ai_insights'].keys())}")