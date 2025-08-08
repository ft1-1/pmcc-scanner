#!/usr/bin/env python3
"""Test the email formatting with actual scan data."""

import json
from datetime import datetime
from src.notifications.formatters import EmailFormatter
from src.notifications.notification_manager import NotificationManager

# Load the latest scan results
with open('data/pmcc_scan_20250808_172515.json', 'r') as f:
    scan_data = json.load(f)

# Extract the opportunity and enhanced data
opportunity = scan_data['top_opportunities'][0]

# Create enhanced data format (as it would be from main.py)
enhanced_data = [{
    'symbol': opportunity['symbol'],
    'underlying_price': opportunity['underlying_price'],
    'net_debit': opportunity['net_debit'],
    'max_profit': opportunity['risk_metrics']['max_profit'],
    'pmcc_score': opportunity['total_score'],
    'liquidity_score': opportunity['liquidity_score'],
    'claude_score': opportunity['claude_score'],
    'combined_score': opportunity['combined_score'],
    'claude_confidence': opportunity['claude_confidence'],
    'claude_reasoning': opportunity['claude_reasoning'],
    'ai_recommendation': opportunity['ai_recommendation'],
    'claude_analyzed': True,
    'ai_insights': opportunity['ai_insights'],
    'analysis': {
        'long_call': opportunity['long_call'],
        'short_call': opportunity['short_call']
    }
}]

# Create scan metadata
scan_metadata = {
    'duration_seconds': scan_data['total_duration_seconds'],
    'stocks_screened': scan_data['stats']['stocks_screened'],
    'stocks_passed_screening': scan_data['stats']['stocks_passed_screening'],
    'options_analyzed': scan_data['stats']['options_analyzed'],
    'opportunities_found': scan_data['stats']['opportunities_found']
}

# Use the notification manager method that handles enhanced data
from src.config import get_settings
settings = get_settings()

# Format the email using the actual method that's called
templates = EmailFormatter.format_multiple_opportunities(
    enhanced_data, 
    scan_metadata, 
    enhanced_data=enhanced_data
)

# Get the email template
email_template = templates.get('email')
if email_template:
    subject = email_template.subject
    html_content = email_template.html_content
    text_content = email_template.text_content
else:
    print("No email template generated!")
    exit(1)

print("\n" + "="*80)
print("EMAIL PREVIEW - AI ENHANCED WITH PMCC CONTRACT DETAILS")
print("="*80 + "\n")

print(f"SUBJECT: {subject}\n")
print("TEXT CONTENT:")
print("-"*80)
print(text_content)
print("-"*80)

# Extract key sections from HTML to verify formatting
print("\n\nKEY HTML SECTIONS:")
print("-"*80)

# Check if PMCC contract details are in the HTML
if "PMCC CONTRACT DETAILS" in html_content:
    print("✅ PMCC CONTRACT DETAILS section found in HTML")
else:
    print("❌ PMCC CONTRACT DETAILS section NOT found in HTML")

if opportunity['long_call']['option_symbol'] in html_content:
    print("✅ LEAPS contract symbol found in HTML")
else:
    print("❌ LEAPS contract symbol NOT found in HTML")

if opportunity['short_call']['option_symbol'] in html_content:
    print("✅ Short call contract symbol found in HTML")
else:
    print("❌ Short call contract symbol NOT found in HTML")

# Check for key opportunities
if "KEY OPPORTUNITIES" in html_content:
    print("✅ KEY OPPORTUNITIES section found in HTML")
else:
    print("❌ KEY OPPORTUNITIES section NOT found in HTML")

print("\n" + "="*80)
print("Email formatting test complete!")
print("="*80 + "\n")