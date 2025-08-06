#!/usr/bin/env python3
"""
Demo script showing how to use the PMCC Scanner notification system.

This script demonstrates:
1. Setting up the notification manager
2. Sending PMCC opportunity alerts
3. Handling multiple opportunities
4. System alerts and monitoring
5. Testing connectivity

Usage:
    python examples/notification_system_demo.py
"""

import os
import sys
from datetime import datetime
from decimal import Decimal

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from src.notifications import NotificationManager, NotificationConfig
    from src.models.pmcc_models import PMCCCandidate, PMCCAnalysis, RiskMetrics
    from src.models.api_models import OptionContract, StockQuote, OptionSide
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure to install dependencies: pip install -r requirements.txt")
    sys.exit(1)


def create_sample_pmcc_opportunity():
    """Create a sample PMCC opportunity for demonstration."""
    # Create LEAPS (long call)
    long_call = OptionContract(
        option_symbol="AAPL250117C00150000",
        underlying_symbol="AAPL",
        strike=Decimal("150.00"),
        expiration=datetime(2025, 1, 17),
        side=OptionSide.CALL,
        bid=Decimal("25.50"),
        ask=Decimal("26.00"),
        delta=Decimal("0.80"),
        dte=365  # Days to expiration
    )
    
    # Create short call
    short_call = OptionContract(
        option_symbol="AAPL241220C00160000",
        underlying_symbol="AAPL",
        strike=Decimal("160.00"),
        expiration=datetime(2024, 12, 20),
        side=OptionSide.CALL,
        bid=Decimal("3.50"),
        ask=Decimal("3.75"),
        delta=Decimal("0.30"),
        dte=30  # Days to expiration
    )
    
    # Create underlying stock quote
    underlying = StockQuote(
        symbol="AAPL",
        price=Decimal("155.00"),
        timestamp=datetime.now()
    )
    
    # Create risk metrics
    risk_metrics = RiskMetrics(
        max_loss=Decimal("22.25"),      # Net debit paid
        max_profit=Decimal("7.75"),     # Strike width - net debit
        breakeven=Decimal("172.25"),    # Long strike + net debit
        risk_reward_ratio=Decimal("0.35")  # max_profit / max_loss
    )
    
    # Create PMCC analysis
    analysis = PMCCAnalysis(
        long_call=long_call,
        short_call=short_call,
        underlying=underlying,
        net_debit=Decimal("22.25"),
        risk_metrics=risk_metrics
    )
    
    # Create PMCC candidate
    candidate = PMCCCandidate(
        symbol="AAPL",
        underlying_price=Decimal("155.00"),
        analysis=analysis,
        liquidity_score=Decimal("85"),
        total_score=Decimal("82")
    )
    
    return candidate


def demo_notification_setup():
    """Demonstrate notification system setup."""
    print("=== PMCC Scanner Notification System Demo ===\n")
    
    # Method 1: Create with custom config
    print("1. Setting up notification system with custom configuration:")
    config = NotificationConfig(
        max_retries=3,
        retry_delay_seconds=60,
        enable_fallback=True,
        fallback_delay_seconds=300,
        whatsapp_enabled=True,
        email_enabled=True
    )
    
    try:
        manager = NotificationManager(config)
        print("   ✓ Notification manager created successfully")
    except Exception as e:
        print(f"   ✗ Failed to create notification manager: {e}")
        print("   Make sure environment variables are set:")
        print("   - TWILIO_ACCOUNT_SID")
        print("   - TWILIO_AUTH_TOKEN")
        print("   - MAILGUN_API_KEY (or SENDGRID_API_KEY for legacy)")
        print("   - MAILGUN_DOMAIN (if using Mailgun)")
        return None
    
    # Method 2: Create from environment
    print("\n2. Creating notification manager from environment:")
    try:
        env_manager = NotificationManager.create_from_env()
        print("   ✓ Environment-based manager created successfully")
    except Exception as e:
        print(f"   ✗ Failed to create from environment: {e}")
        env_manager = manager
    
    return env_manager


def demo_single_opportunity_notification(manager):
    """Demonstrate sending notification for a single PMCC opportunity."""
    print("\n3. Sending notification for single PMCC opportunity:")
    
    # Create sample opportunity
    opportunity = create_sample_pmcc_opportunity()
    
    try:
        results = manager.send_pmcc_opportunity(opportunity)
        
        print(f"   Sent {len(results)} notifications:")
        for result in results:
            status_icon = "✓" if result.is_success else "✗"
            print(f"   {status_icon} {result.channel.value}: {result.recipient} - {result.status.value}")
            if result.error_message:
                print(f"      Error: {result.error_message}")
                
    except Exception as e:
        print(f"   ✗ Failed to send notifications: {e}")


def demo_multiple_opportunities_notification(manager):
    """Demonstrate sending notifications for multiple opportunities."""
    print("\n4. Sending notification for multiple opportunities:")
    
    # Create multiple opportunities
    opportunities = []
    symbols = ["AAPL", "MSFT", "GOOGL"]
    
    for i, symbol in enumerate(symbols):
        opportunity = create_sample_pmcc_opportunity()
        opportunity.symbol = symbol
        opportunity.underlying_price = Decimal(str(150 + i * 50))
        opportunity.total_score = Decimal(str(85 - i * 2))
        opportunities.append(opportunity)
    
    try:
        results = manager.send_multiple_opportunities(opportunities)
        
        print(f"   Sent summary notifications to {len(results)} channels:")
        for result in results:
            status_icon = "✓" if result.is_success else "✗"
            print(f"   {status_icon} {result.channel.value}: {result.recipient}")
            
    except Exception as e:
        print(f"   ✗ Failed to send multiple opportunity notifications: {e}")


def demo_system_alerts(manager):
    """Demonstrate system alert notifications."""
    print("\n5. Sending system alerts:")
    
    alerts = [
        ("Scanner started successfully", "info"),
        ("High volatility detected", "warning"),
        ("API rate limit exceeded", "error"),
        ("Database connection lost", "critical")
    ]
    
    for message, severity in alerts:
        try:
            results = manager.send_system_alert(message, severity)
            print(f"   {severity.upper()}: Sent to {len(results)} recipients")
        except Exception as e:
            print(f"   ✗ Failed to send {severity} alert: {e}")


def demo_monitoring_features(manager):
    """Demonstrate monitoring and status features."""
    print("\n6. Monitoring and status features:")
    
    # Test connectivity
    print("   Testing connectivity:")
    try:
        connectivity = manager.test_connectivity()
        for service, status in connectivity.items():
            status_icon = "✓" if status else "✗"
            print(f"     {status_icon} {service.title()}: {'Connected' if status else 'Failed'}")
    except Exception as e:
        print(f"     ✗ Connectivity test failed: {e}")
    
    # Get delivery status
    print("\n   Delivery statistics:")
    try:
        status = manager.get_delivery_status()
        print(f"     Total messages: {status['total']}")
        print(f"     Successful: {status['successful']}")
        print(f"     Failed: {status['failed']}")
        print(f"     Success rate: {status['success_rate']:.1%}")
        
        if status['by_channel']:
            print("     By channel:")
            for channel, stats in status['by_channel'].items():
                print(f"       {channel.title()}: {stats['successful']}/{stats['total']}")
                
    except Exception as e:
        print(f"     ✗ Failed to get delivery status: {e}")
    
    # Test health check
    try:
        is_healthy = manager.is_healthy()
        health_icon = "✓" if is_healthy else "✗"
        print(f"\n   {health_icon} System health: {'Healthy' if is_healthy else 'Degraded'}")
    except Exception as e:
        print(f"   ✗ Health check failed: {e}")


def demo_configuration_options():
    """Demonstrate configuration options."""
    print("\n7. Configuration options:")
    
    print("   Environment variables to set:")
    env_vars = [
        ("TWILIO_ACCOUNT_SID", "Your Twilio account SID"),
        ("TWILIO_AUTH_TOKEN", "Your Twilio auth token"),
        ("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886 (or your Twilio WhatsApp number)"),
        ("WHATSAPP_TO_NUMBERS", "whatsapp:+1234567890,whatsapp:+0987654321"),
        ("MAILGUN_API_KEY", "Your Mailgun API key"),
        ("MAILGUN_DOMAIN", "Your Mailgun domain"),
        # ("SENDGRID_API_KEY", "Your SendGrid API key - deprecated"),
        ("EMAIL_FROM", "pmcc-scanner@yourdomain.com"),
        ("EMAIL_TO", "user@example.com,another@example.com"),
        ("NOTIFICATION_ENABLED", "true"),
        ("WHATSAPP_ENABLED", "true"),
        ("EMAIL_ENABLED", "true")
    ]
    
    for var_name, description in env_vars:
        current_value = os.getenv(var_name, "Not set")
        print(f"     {var_name}: {description}")
        print(f"       Current: {current_value}")


def main():
    """Run the notification system demonstration."""
    # Setup
    manager = demo_notification_setup()
    
    if manager is None:
        print("\nDemo stopped due to setup issues.")
        print("Please configure your environment variables and try again.")
        demo_configuration_options()
        return
    
    # Demonstrate features
    demo_single_opportunity_notification(manager)
    demo_multiple_opportunities_notification(manager)
    demo_system_alerts(manager)
    demo_monitoring_features(manager)
    demo_configuration_options()
    
    print("\n=== Demo completed ===")
    print("\nTo use in production:")
    print("1. Set all required environment variables")
    print("2. Test connectivity with manager.test_connectivity()")
    print("3. Integrate with your PMCC scanner workflow")
    print("4. Monitor delivery status and system health")


if __name__ == "__main__":
    main()