#!/usr/bin/env python3
"""
PMCC Scanner Provider Configuration Utility

This script helps users configure data providers for the PMCC Scanner,
migrate from legacy configurations, and validate their setup.

Usage:
    python scripts/configure_providers.py --validate
    python scripts/configure_providers.py --migrate
    python scripts/configure_providers.py --recommend
    python scripts/configure_providers.py --interactive
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add src to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

try:
    from src.config.settings import Settings, load_settings, ProviderMode, DataProviderType, FallbackStrategy
except ImportError as e:
    print(f"❌ Error importing settings: {e}")
    print("Please ensure you're running this script from the project root directory.")
    sys.exit(1)


class ProviderConfigurationWizard:
    """Interactive wizard for configuring data providers."""
    
    def __init__(self):
        self.env_file = Path(".env")
        self.env_example = Path(".env.example")
        
    def run_interactive_setup(self) -> None:
        """Run interactive provider configuration setup."""
        print("🔧 PMCC Scanner Provider Configuration Wizard")
        print("=" * 50)
        
        # Check if .env exists
        if not self.env_file.exists():
            if self.env_example.exists():
                print(f"📄 Creating .env from {self.env_example}")
                with open(self.env_example, 'r') as src, open(self.env_file, 'w') as dst:
                    dst.write(src.read())
            else:
                print("❌ No .env.example found. Please ensure you're in the project root.")
                return
        
        # Load current settings
        try:
            settings = load_settings()
            print("✅ Current configuration loaded successfully")
        except Exception as e:
            print(f"⚠️  Configuration has issues: {e}")
            print("Let's fix this configuration...")
            settings = None
        
        # Get available API tokens
        tokens = self._check_api_tokens()
        if not any(tokens.values()):
            print("\n❌ No API tokens configured!")
            self._configure_api_tokens()
            tokens = self._check_api_tokens()
        
        # Show current status
        self._show_provider_status(tokens, settings)
        
        # Ask user for configuration preferences
        config = self._get_user_preferences(tokens)
        
        # Apply configuration
        self._apply_configuration(config)
        
        # Validate final configuration
        self._validate_final_configuration()
        
        print("\n✅ Provider configuration complete!")
        print("Run 'python src/config/settings.py --validate' to verify your setup.")
    
    def _check_api_tokens(self) -> Dict[str, bool]:
        """Check which API tokens are configured."""
        return {
            'eodhd': bool(os.getenv('EODHD_API_TOKEN', '').strip() and 
                         os.getenv('EODHD_API_TOKEN') != 'your_eodhd_api_token_here'),
            'marketdata': bool(os.getenv('MARKETDATA_API_TOKEN', '').strip() and 
                              os.getenv('MARKETDATA_API_TOKEN') != 'your_marketdata_api_token_here')
        }
    
    def _configure_api_tokens(self) -> None:
        """Interactive API token configuration."""
        print("\n🔑 API Token Configuration")
        print("You need at least one API token to use the PMCC Scanner.")
        print("\nRecommended setup:")
        print("- EODHD: Required for stock screening, cost-effective")
        print("- MarketData: Excellent for options data, faster quotes")
        
        # EODHD Token
        eodhd_token = input("\nEnter your EODHD API token (or press Enter to skip): ").strip()
        if eodhd_token:
            self._update_env_var('EODHD_API_TOKEN', eodhd_token)
        
        # MarketData Token
        marketdata_token = input("Enter your MarketData.app API token (or press Enter to skip): ").strip()
        if marketdata_token:
            self._update_env_var('MARKETDATA_API_TOKEN', marketdata_token)
        
        if not eodhd_token and not marketdata_token:
            print("❌ At least one API token is required!")
            sys.exit(1)
    
    def _show_provider_status(self, tokens: Dict[str, bool], settings: Optional[Settings]) -> None:
        """Show current provider status."""
        print("\n📊 Current Provider Status:")
        print(f"EODHD: {'✅ Configured' if tokens['eodhd'] else '❌ Not configured'}")
        print(f"MarketData: {'✅ Configured' if tokens['marketdata'] else '❌ Not configured'}")
        
        if settings:
            print(f"\nCurrent mode: {settings.providers.provider_mode.value}")
            print(f"Primary provider: {settings.providers.primary_provider.value}")
            
            issues = settings.validate_provider_configuration()
            if issues:
                print("\n⚠️  Configuration Issues:")
                for issue in issues[:3]:  # Show first 3 issues
                    print(f"  • {issue}")
                if len(issues) > 3:
                    print(f"  ... and {len(issues) - 3} more issues")
    
    def _get_user_preferences(self, tokens: Dict[str, bool]) -> Dict[str, str]:
        """Get user configuration preferences."""
        config = {}
        
        print("\n⚙️  Configuration Preferences")
        
        # Provider mode
        if sum(tokens.values()) > 1:
            print("\nProvider Mode:")
            print("1. Factory (recommended) - Use multiple providers for optimal performance")
            print("2. Legacy - Use single provider approach")
            
            while True:
                choice = input("Choose provider mode (1-2): ").strip()
                if choice == "1":
                    config['PROVIDER_MODE'] = 'factory'
                    break
                elif choice == "2":
                    config['PROVIDER_MODE'] = 'legacy'
                    break
                else:
                    print("Please enter 1 or 2")
        else:
            config['PROVIDER_MODE'] = 'legacy'
            print("Single provider detected - using legacy mode")
        
        # Primary provider
        if sum(tokens.values()) > 1:
            print("\nPrimary Provider:")
            if tokens['eodhd']:
                print("1. EODHD - Best for stock screening, cost-effective")
            if tokens['marketdata']:
                print("2. MarketData - Best for real-time data, faster performance")
            
            while True:
                choice = input("Choose primary provider (1-2): ").strip()
                if choice == "1" and tokens['eodhd']:
                    config['PROVIDER_PRIMARY_PROVIDER'] = 'eodhd'
                    break
                elif choice == "2" and tokens['marketdata']:
                    config['PROVIDER_PRIMARY_PROVIDER'] = 'marketdata'
                    break
                else:
                    print("Invalid choice or provider not configured")
        else:
            # Single provider
            if tokens['eodhd']:
                config['PROVIDER_PRIMARY_PROVIDER'] = 'eodhd'
            else:
                config['PROVIDER_PRIMARY_PROVIDER'] = 'marketdata'
        
        # Operation preferences (only if both providers available)
        if tokens['eodhd'] and tokens['marketdata']:
            print("\n🎯 Operation Preferences (recommended settings will be used)")
            config['PROVIDER_PREFERRED_STOCK_SCREENER'] = 'eodhd'  # Only EODHD supports screening
            config['PROVIDER_PREFERRED_OPTIONS_PROVIDER'] = 'marketdata'  # MarketData is faster
            config['PROVIDER_PREFERRED_QUOTES_PROVIDER'] = 'marketdata'  # MarketData is faster
            config['PROVIDER_PREFERRED_GREEKS_PROVIDER'] = 'marketdata'  # MarketData is more accurate
            config['PROVIDER_FALLBACK_STRATEGY'] = 'operation_specific'
        
        return config
    
    def _apply_configuration(self, config: Dict[str, str]) -> None:
        """Apply configuration to .env file."""
        print("\n💾 Applying configuration...")
        
        for key, value in config.items():
            self._update_env_var(key, value)
        
        # Also set some sensible defaults
        defaults = {
            'PROVIDER_AUTO_DETECT_PROVIDERS': 'true',
            'PROVIDER_ENABLE_HEALTH_CHECKS': 'true',
            'PROVIDER_PRIORITIZE_COST_EFFICIENCY': 'true',
        }
        
        for key, value in defaults.items():
            if not os.getenv(key):
                self._update_env_var(key, value)
    
    def _update_env_var(self, key: str, value: str) -> None:
        """Update environment variable in .env file."""
        if not self.env_file.exists():
            self.env_file.touch()
        
        # Read current content
        lines = []
        if self.env_file.exists():
            with open(self.env_file, 'r') as f:
                lines = f.readlines()
        
        # Update or add the variable
        updated = False
        for i, line in enumerate(lines):
            if line.startswith(f"{key}="):
                lines[i] = f"{key}={value}\n"
                updated = True
                break
        
        if not updated:
            lines.append(f"{key}={value}\n")
        
        # Write back
        with open(self.env_file, 'w') as f:
            f.writelines(lines)
        
        # Also set in current environment
        os.environ[key] = value
    
    def _validate_final_configuration(self) -> None:
        """Validate the final configuration."""
        print("\n🔍 Validating configuration...")
        
        try:
            settings = load_settings()
            issues = settings.validate_provider_configuration()
            
            if not issues:
                print("✅ Configuration is valid!")
            else:
                print("⚠️  Configuration issues found:")
                for issue in issues:
                    level = issue.split(":")[0]
                    if level in ["CRITICAL", "ERROR"]:
                        print(f"❌ {issue}")
                    else:
                        print(f"ℹ️  {issue}")
        except Exception as e:
            print(f"❌ Configuration validation failed: {e}")


def migrate_legacy_configuration() -> None:
    """Migrate legacy configuration to new provider system."""
    print("🔄 Migrating Legacy Configuration")
    print("=" * 40)
    
    # Check current configuration
    try:
        settings = load_settings()
    except Exception as e:
        print(f"❌ Cannot load current configuration: {e}")
        return
    
    # Check if migration is needed
    if settings.providers.provider_mode == ProviderMode.FACTORY:
        print("✅ Already using factory mode - no migration needed")
        return
    
    # Detect available providers
    available = settings.get_available_providers()
    if len(available) < 2:
        print(f"ℹ️  Single provider ({available[0] if available else 'none'}) - factory mode not beneficial")
        return
    
    print(f"📊 Detected providers: {', '.join(available)}")
    
    # Recommend migration to factory mode
    wizard = ProviderConfigurationWizard()
    wizard._update_env_var('PROVIDER_MODE', 'factory')
    wizard._update_env_var('PROVIDER_FALLBACK_STRATEGY', 'operation_specific')
    
    # Set optimal operation preferences
    if 'EODHD' in available:
        wizard._update_env_var('PROVIDER_PREFERRED_STOCK_SCREENER', 'eodhd')
    if 'MarketData' in available:
        wizard._update_env_var('PROVIDER_PREFERRED_OPTIONS_PROVIDER', 'marketdata')
        wizard._update_env_var('PROVIDER_PREFERRED_QUOTES_PROVIDER', 'marketdata')
        wizard._update_env_var('PROVIDER_PREFERRED_GREEKS_PROVIDER', 'marketdata')
    
    print("✅ Migration complete! Restart the application to use the new configuration.")


def recommend_configuration() -> None:
    """Provide configuration recommendations."""
    print("💡 Configuration Recommendations")
    print("=" * 35)
    
    try:
        settings = load_settings()
        available = settings.get_available_providers()
        mode_rec, reason = settings.get_provider_mode_recommendation()
        
        print(f"Available providers: {', '.join(available) if available else 'None'}")
        print(f"Recommended mode: {mode_rec.value}")
        print(f"Reason: {reason}")
        
        # Specific recommendations
        print("\n📋 Specific Recommendations:")
        
        if not available:
            print("🔑 Get at least one API token (EODHD or MarketData)")
            print("   - EODHD: Required for stock screening")
            print("   - MarketData: Best for options and quotes")
        elif len(available) == 1:
            provider = available[0].lower()
            if provider == "eodhd":
                print("💰 Consider adding MarketData token for:")
                print("   - Faster options chain retrieval")
                print("   - Better real-time quotes")
                print("   - Improved Greeks accuracy")
            else:
                print("📊 Consider adding EODHD token for:")
                print("   - Stock screening capabilities")
                print("   - Lower cost for batch operations")
        else:
            print("✅ Optimal setup detected!")
            print("💡 Make sure you're using factory mode for best performance")
        
        # Show validation issues
        issues = settings.validate_provider_configuration()
        if issues:
            print("\n⚠️  Current Issues:")
            for issue in issues:
                print(f"   • {issue}")
    
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")


def validate_configuration() -> None:
    """Validate current provider configuration."""
    print("🔍 Validating Provider Configuration")
    print("=" * 38)
    
    try:
        settings = load_settings()
        
        # Basic validation
        available = settings.get_available_providers()
        print(f"Available providers: {', '.join(available) if available else 'None'}")
        print(f"Provider mode: {settings.providers.provider_mode.value}")
        print(f"Primary provider: {settings.providers.primary_provider.value}")
        
        # Detailed validation
        issues = settings.validate_provider_configuration()
        
        if not issues:
            print("\n✅ All provider configurations are valid!")
        else:
            print(f"\n📋 Found {len(issues)} configuration issues:")
            for issue in issues:
                level = issue.split(":")[0]
                if level == "CRITICAL":
                    print(f"❌ {issue}")
                elif level == "ERROR":
                    print(f"⚠️  {issue}")
                elif level == "WARNING":
                    print(f"⚠️  {issue}")
                else:
                    print(f"ℹ️  {issue}")
        
        # Show recommendations
        mode_rec, reason = settings.get_provider_mode_recommendation()
        if mode_rec != settings.providers.provider_mode:
            print(f"\n💡 Recommendation: Switch to {mode_rec.value} mode")
            print(f"   Reason: {reason}")
    
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="PMCC Scanner Provider Configuration Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/configure_providers.py --interactive
  python scripts/configure_providers.py --validate
  python scripts/configure_providers.py --migrate
  python scripts/configure_providers.py --recommend
        """
    )
    
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Run interactive configuration wizard'
    )
    
    parser.add_argument(
        '--validate', '-v',
        action='store_true',
        help='Validate current provider configuration'
    )
    
    parser.add_argument(
        '--migrate', '-m',
        action='store_true',
        help='Migrate legacy configuration to new provider system'
    )
    
    parser.add_argument(
        '--recommend', '-r',
        action='store_true',
        help='Show configuration recommendations'
    )
    
    args = parser.parse_args()
    
    # If no arguments provided, run interactive mode
    if not any([args.interactive, args.validate, args.migrate, args.recommend]):
        args.interactive = True
    
    try:
        if args.interactive:
            wizard = ProviderConfigurationWizard()
            wizard.run_interactive_setup()
        
        if args.validate:
            validate_configuration()
        
        if args.migrate:
            migrate_legacy_configuration()
        
        if args.recommend:
            recommend_configuration()
    
    except KeyboardInterrupt:
        print("\n\n👋 Configuration cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()