#!/usr/bin/env python3
"""Check earnings data in the latest scan results."""

import json
from datetime import datetime

# Load the latest scan results
with open('data/pmcc_scan_20250808_175836.json', 'r') as f:
    data = json.load(f)

# Check if we have AI insights
if data['top_opportunities'] and len(data['top_opportunities']) > 0:
    opportunity = data['top_opportunities'][0]
    ai_insights = opportunity.get('ai_insights', {})
    
    print(f"Checking earnings data for {opportunity['symbol']}...")
    print("="*60)
    
    # Look for earnings-related fields in AI insights
    if 'earnings_calendar' in ai_insights:
        print("\n✅ Found earnings_calendar in AI insights:")
        earnings = ai_insights['earnings_calendar']
        print(f"   Total events: {len(earnings)}")
        
        # Categorize by date
        today = datetime.now().date()
        future_earnings = []
        past_earnings = []
        
        for event in earnings:
            event_date = datetime.strptime(event['date'], '%Y-%m-%d').date()
            if event_date > today:
                future_earnings.append(event)
            else:
                past_earnings.append(event)
        
        print(f"\n📅 FUTURE EARNINGS: {len(future_earnings)}")
        for event in future_earnings:
            print(f"   - Date: {event['date']}")
            print(f"     EPS Estimate: {event.get('eps_estimate', 'N/A')}")
            print(f"     Has Actual: {'eps_actual' in event}")
        
        print(f"\n📊 PAST EARNINGS: {len(past_earnings)} (showing last 3)")
        for event in past_earnings[-3:]:
            print(f"   - Date: {event['date']}")
            print(f"     EPS Actual: {event.get('eps_actual', 'N/A')}")
            print(f"     EPS Estimate: {event.get('eps_estimate', 'N/A')}")
    
    # Check raw enhanced data that was sent to Claude
    print("\n" + "="*60)
    print("Raw data structure available to Claude:")
    
    # The enhanced data would have been processed, but we can check what Claude saw
    if 'key_risks' in ai_insights:
        print("\n🔍 Claude identified these risks:")
        for risk in ai_insights['key_risks'][:3]:
            print(f"   - {risk}")
        
        # Check if any risks mention earnings
        earnings_risks = [r for r in ai_insights['key_risks'] if 'earning' in r.lower()]
        if earnings_risks:
            print("\n⚠️  Earnings-related risks identified:")
            for risk in earnings_risks:
                print(f"   - {risk}")
    
    # Check calendar event score
    if 'calendar_event_score' in ai_insights:
        print(f"\n📊 Calendar Event Score: {ai_insights['calendar_event_score']}/25")
        print("   (Higher score = better calendar positioning)")
else:
    print("No opportunities found in scan results")