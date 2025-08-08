#!/usr/bin/env python3
"""
Enhanced Notification System Demo

This script demonstrates how the Phase 4 AI-enhanced notification system works
with Claude AI insights integrated into PMCC opportunities.

Usage:
    python examples/enhanced_notification_demo.py
"""

import sys
import os
from datetime import datetime
from decimal import Decimal

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.notifications.formatters import WhatsAppFormatter, EmailFormatter
from src.notifications.models import NotificationTemplate, NotificationConfig
from src.notifications.notification_manager import NotificationManager


def create_sample_enhanced_data():
    """Create sample enhanced data with AI insights for demonstration."""
    return [
        {
            'symbol': 'AAPL',
            'underlying_price': 175.50,
            'net_debit': 25.50,
            'max_profit': 45.75,
            'claude_analyzed': True,
            'claude_score': 87,
            'combined_score': 89,
            'claude_confidence': 82,
            'ai_recommendation': 'strong_buy',
            'claude_reasoning': 'Strong fundamentals with upcoming iPhone cycle, excellent options liquidity, and favorable risk/reward profile for PMCC strategy.',
            'ai_insights': {
                'risk_score': 25,
                'fundamental_health_score': 88,
                'technical_setup_score': 92,
                'calendar_risk_score': 15,
                'pmcc_quality_score': 90,
                'key_strengths': [
                    'Excellent options liquidity across strikes',
                    'Strong fundamentals with growing services revenue',
                    'Favorable technical setup near support levels'
                ],
                'key_risks': [
                    'High IV could compress after earnings',
                    'Tech sector rotation risk'
                ]
            },
            'analysis': {
                'net_debit': 25.50,
                'risk_metrics': {
                    'max_profit': 45.75
                }
            }
        },
        {
            'symbol': 'MSFT',
            'underlying_price': 342.20,
            'net_debit': 38.25,
            'max_profit': 61.50,
            'claude_analyzed': True,
            'claude_score': 84,
            'combined_score': 86,
            'claude_confidence': 78,
            'ai_recommendation': 'buy',
            'claude_reasoning': 'Cloud growth momentum continues with Azure expansion. PMCC setup benefits from stable IV and good theta decay patterns.',
            'ai_insights': {
                'risk_score': 30,
                'fundamental_health_score': 91,
                'technical_setup_score': 79,
                'calendar_risk_score': 20,
                'pmcc_quality_score': 85,
                'key_strengths': [
                    'Dominant cloud market position',
                    'Consistent revenue growth',
                    'Strong balance sheet'
                ],
                'key_risks': [
                    'Competition in cloud space',
                    'Regulatory scrutiny potential'
                ]
            }
        },
        {
            'symbol': 'GOOGL',
            'underlying_price': 138.75,
            'net_debit': 18.50,
            'max_profit': 31.25,
            'claude_analyzed': True,
            'claude_score': 79,
            'combined_score': 81,
            'claude_confidence': 75,
            'ai_recommendation': 'buy',
            'claude_reasoning': 'Search dominance remains strong. AI developments position company well. Options chain shows good PMCC opportunities.',
            'ai_insights': {
                'risk_score': 35,
                'fundamental_health_score': 85,
                'technical_setup_score': 82,
                'calendar_risk_score': 25,
                'pmcc_quality_score': 83,
                'key_strengths': [
                    'Search monopoly with growing AI integration',
                    'YouTube revenue growth acceleration',
                    'Strong cash generation'
                ],
                'key_risks': [
                    'Antitrust regulatory pressure',
                    'Competition from AI chatbots'
                ]
            }
        }
    ]


def demo_whatsapp_formatting():
    """Demonstrate WhatsApp formatting with AI insights."""
    print("=" * 60)
    print("WhatsApp Formatting Demo - AI Enhanced")
    print("=" * 60)
    
    enhanced_data = create_sample_enhanced_data()
    
    # Test enhanced WhatsApp formatting
    template = WhatsAppFormatter.format_multiple_opportunities(
        candidates=[],  # Empty legacy format
        limit=10,
        enhanced_data=enhanced_data
    )
    
    print("Enhanced WhatsApp Message:")
    print("-" * 40)
    print(template.text_content)
    print()


def demo_email_formatting():
    """Demonstrate email formatting with AI insights."""
    print("=" * 60)
    print("Email Formatting Demo - AI Enhanced")
    print("=" * 60)
    
    enhanced_data = create_sample_enhanced_data()
    
    # Test enhanced email formatting
    template = EmailFormatter.format_multiple_opportunities(
        candidates=[],  # Empty legacy format
        enhanced_data=enhanced_data
    )
    
    print("Enhanced Email Subject:")
    print("-" * 40)
    print(template.subject)
    print()
    
    print("Enhanced Email Text Content (first 500 chars):")
    print("-" * 40)
    print(template.text_content[:500] + "...")
    print()
    
    print("Enhanced Email HTML Content (first 800 chars):")
    print("-" * 40)
    print(template.html_content[:800] + "...")
    print()


def demo_notification_config():
    """Demonstrate notification configuration with AI enhancements."""
    print("=" * 60)
    print("Notification Configuration Demo")
    print("=" * 60)
    
    # Create configuration with AI enhancements
    config = NotificationConfig(
        ai_enhanced_notifications=True,
        force_traditional_format=False,
        ai_confidence_threshold=70.0,
        top_n_limit=5
    )
    
    # Create notification manager
    manager = NotificationManager(config)
    
    # Show configuration summary
    config_summary = manager.get_notification_config_summary()
    
    print("Notification Configuration:")
    print("-" * 40)
    for section, settings in config_summary.items():
        print(f"{section.upper()}:")
        for key, value in settings.items():
            print(f"  {key}: {value}")
        print()


def demo_confidence_filtering():
    """Demonstrate confidence-based filtering."""
    print("=" * 60)
    print("AI Confidence Filtering Demo")
    print("=" * 60)
    
    enhanced_data = create_sample_enhanced_data()
    
    # Add some low-confidence data
    enhanced_data.append({
        'symbol': 'LOWCONF',
        'claude_confidence': 45,  # Below threshold
        'ai_recommendation': 'hold'
    })
    
    config = NotificationConfig(ai_confidence_threshold=70.0)
    manager = NotificationManager(config)
    
    print(f"Original data: {len(enhanced_data)} opportunities")
    
    # Filter by confidence
    filtered_data = manager.filter_enhanced_data_by_confidence(enhanced_data)
    
    print(f"After confidence filtering (≥70%): {len(filtered_data)} opportunities")
    print()
    
    for opp in filtered_data:
        print(f"  {opp['symbol']}: {opp.get('claude_confidence', 0)}% confidence")


def main():
    """Run all demonstrations."""
    print("PMCC Scanner - Enhanced Notification System Demo")
    print("Phase 4: AI Integration with Claude Insights")
    print(f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")
    print()
    
    try:
        demo_notification_config()
        demo_confidence_filtering()
        demo_whatsapp_formatting()
        demo_email_formatting()
        
        print("=" * 60)
        print("Demo completed successfully!")
        print("=" * 60)
        print()
        print("Key Features Demonstrated:")
        print("- AI-enhanced WhatsApp notifications with recommendations")
        print("- Rich HTML email templates with Claude insights")
        print("- Confidence-based filtering")
        print("- Feature toggles for AI vs traditional format")
        print("- Backward compatibility with existing PMCC data")
        
    except Exception as e:
        print(f"Error during demo: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())