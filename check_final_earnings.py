#!/usr/bin/env python3
"""Check if future earnings are in the final scan results."""

import json
from datetime import datetime

# Load the latest scan results
with open('data/pmcc_scan_20250808_180520.json', 'r') as f:
    data = json.load(f)

if data['top_opportunities']:
    opp = data['top_opportunities'][0]
    ai_insights = opp.get('ai_insights', {})
    
    print(f"Checking {opp['symbol']} AI insights for earnings data...")
    print("="*60)
    
    # Check calendar event score
    calendar_score = ai_insights.get('calendar_event_score', 0)
    print(f"📊 Calendar Event Score: {calendar_score}/25")
    
    # Check if earnings are mentioned in risks or opportunities
    print("\n🔍 Checking for earnings mentions in AI analysis:")
    
    all_text = []
    all_text.extend(ai_insights.get('key_risks', []))
    all_text.extend(ai_insights.get('key_opportunities', []))
    all_text.append(ai_insights.get('management_strategy', ''))
    all_text.append(ai_insights.get('entry_timing', ''))
    
    earnings_mentions = []
    for text in all_text:
        if text and 'earning' in text.lower():
            earnings_mentions.append(text)
    
    if earnings_mentions:
        print("\n✅ Found earnings mentions:")
        for mention in earnings_mentions:
            print(f"   - {mention}")
    else:
        print("\n❌ No earnings mentions found in AI analysis")
    
    # Check exit conditions for earnings
    exit_conditions = ai_insights.get('exit_conditions', [])
    earnings_exits = [e for e in exit_conditions if 'earning' in e.lower()]
    if earnings_exits:
        print("\n⚠️  Earnings-related exit conditions:")
        for condition in earnings_exits:
            print(f"   - {condition}")
    
    # Display the full AI reasoning to see if earnings are considered
    print("\n📝 Full AI Reasoning:")
    print(ai_insights.get('claude_reasoning', 'No reasoning provided'))
    
    # Check if the raw enhanced data had earnings (for debugging)
    print("\n" + "="*60)
    print("DEBUG: Checking raw data structure...")
    
    # The AI insights might have processed earnings data even if not explicitly shown
    if 'analysis_summary' in ai_insights:
        print(f"\nAnalysis Summary: {ai_insights['analysis_summary']}")
    
    if 'detailed_reasoning' in ai_insights:
        print(f"\nDetailed Reasoning: {ai_insights['detailed_reasoning']}")