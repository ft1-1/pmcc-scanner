#!/usr/bin/env python3
"""Preview the AI-enhanced email format with PMCC contract details."""

from datetime import datetime
from decimal import Decimal

# Sample data similar to ANF
sample_data = {
    'symbol': 'ANF',
    'underlying_price': 103.03,
    'claude_score': 72,
    'combined_score': 71.6,
    'claude_confidence': 75,
    'ai_recommendation': 'hold',
    'claude_reasoning': 'PMCC opportunity with score 72/100. Key risks: Poor LEAPS liquidity with only 5 volume/15 OI, High short interest at 23.05% creating squeeze risk. Key opportunities: Strong FCF and balance sheet metrics, Low P/E of 10.17 provides valuation support.',
    'net_debit': 47.2,
    'max_profit': 27.7,
    'analysis': {
        'long_call': {
            'option_symbol': 'ANF260320C00055000',
            'strike': 55.0,
            'expiration': datetime(2026, 3, 20),
            'dte': 224,
            'ask': 49.0,
            'bid': 47.7,
            'delta': 0.920
        },
        'short_call': {
            'option_symbol': 'ANF250919C00130000', 
            'strike': 130.0,
            'expiration': datetime(2025, 9, 19),
            'dte': 42,
            'bid': 1.80,
            'ask': 1.95,
            'delta': 0.165
        }
    },
    'ai_insights': {
        'key_opportunities': [
            'Strong FCF and balance sheet metrics',
            'Low P/E of 10.17 provides valuation support',
            'Positive analyst sentiment with $121.47 price target'
        ],
        'key_risks': [
            'Poor LEAPS liquidity with only 5 volume/15 OI',
            'High short interest at 23.05% creating squeeze risk',
            'Upcoming earnings in Q3 could increase volatility'
        ]
    }
}

print("\n" + "="*80)
print("AI-ENHANCED EMAIL PREVIEW - PMCC CONTRACT DETAILS")
print("="*80 + "\n")

# Show what the email sections will look like
print("📊 CLAUDE AI ANALYSIS")
print(f"  AI Score:         {sample_data['claude_score']}/100")
print(f"  Combined Score:   {sample_data['combined_score']}/100")  
print(f"  Confidence:       {sample_data['claude_confidence']}%")
print(f"  Recommendation:   {sample_data['ai_recommendation'].title()}")
print(f"\n  AI Reasoning:\n  {sample_data['claude_reasoning']}")

print("\n📊 TRADITIONAL METRICS:")
print(f"  Net Cost:         ${sample_data['net_debit']:.2f}")
print(f"  Max Profit:       ${sample_data['max_profit']:.2f}")
print(f"  Return %:         {(sample_data['max_profit']/sample_data['net_debit']*100):.1f}%")

print("\n📊 PMCC CONTRACT DETAILS:")
print("\n  LONG LEAPS CALL:")
print(f"    Symbol:         {sample_data['analysis']['long_call']['option_symbol']}")
print(f"    Strike:         ${sample_data['analysis']['long_call']['strike']:.2f}")
print(f"    Expiration:     {sample_data['analysis']['long_call']['expiration'].strftime('%b %d, %Y')}")
print(f"    DTE:            {sample_data['analysis']['long_call']['dte']} days")
print(f"    Ask Price:      ${sample_data['analysis']['long_call']['ask']:.2f}")
print(f"    Delta:          {sample_data['analysis']['long_call']['delta']:.3f}")

print("\n  SHORT CALL:")
print(f"    Symbol:         {sample_data['analysis']['short_call']['option_symbol']}")
print(f"    Strike:         ${sample_data['analysis']['short_call']['strike']:.2f}")
print(f"    Expiration:     {sample_data['analysis']['short_call']['expiration'].strftime('%b %d, %Y')}")
print(f"    DTE:            {sample_data['analysis']['short_call']['dte']} days")
print(f"    Bid Price:      ${sample_data['analysis']['short_call']['bid']:.2f}")
print(f"    Delta:          {sample_data['analysis']['short_call']['delta']:.3f}")

print("\n✅ KEY OPPORTUNITIES:")
for opp in sample_data['ai_insights']['key_opportunities'][:3]:
    print(f"  • {opp}")

print("\n⚠️  KEY RISKS:")
for risk in sample_data['ai_insights']['key_risks'][:3]:
    print(f"  • {risk}")

print("\n" + "="*80)
print("Email will display these sections in a nicely formatted HTML layout")
print("with color coding and proper sections for easy reading")
print("="*80 + "\n")