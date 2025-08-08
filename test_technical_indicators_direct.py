#!/usr/bin/env python3
"""
Direct test of technical indicators fix without provider factory.
"""

import sys
import logging
from pathlib import Path
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config import get_settings
from src.api.providers.sync_enhanced_eodhd_provider import SyncEnhancedEODHDProvider
from src.analysis.scanner import PMCCScanner
from src.api.data_provider import ProviderType

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_technical_indicators_direct():
    """Test technical indicators directly with enhanced EODHD provider."""
    try:
        logger.info("🧪 Testing technical indicators directly...")
        
        # Get settings
        settings = get_settings()
        
        # Check if we have EODHD token
        eodhd_token = settings.eodhd_api_token or "demo"
        logger.info(f"Using EODHD token: {eodhd_token[:10]}...")
        
        # Create enhanced EODHD provider directly
        provider_config = {
            'api_token': eodhd_token,
            'enable_caching': True,
            'cache_ttl_hours': 1
        }
        
        enhanced_provider = SyncEnhancedEODHDProvider(
            provider_type=ProviderType.EODHD,
            config=provider_config
        )
        
        logger.info(f"✅ Enhanced EODHD provider created")
        
        # Test comprehensive enhanced data
        test_symbol = "AAPL"  # Use a well-known stock
        logger.info(f"🔍 Testing comprehensive enhanced data for {test_symbol}...")
        
        response = enhanced_provider.get_comprehensive_enhanced_data(test_symbol)
        
        if not response.is_success:
            logger.error(f"❌ Failed to get comprehensive data: {response.error}")
            return False
        
        enhanced_data = response.data
        logger.info(f"✅ Comprehensive data retrieved successfully")
        
        # Check technical indicators structure
        if 'technical_indicators' in enhanced_data:
            tech_indicators = enhanced_data['technical_indicators']
            logger.info(f"🔍 Technical indicators analysis:")
            logger.info(f"  Type: {type(tech_indicators)}")
            
            if isinstance(tech_indicators, dict):
                for indicator_name, indicator_data in tech_indicators.items():
                    if indicator_data is None:
                        status = "❌ None"
                    elif isinstance(indicator_data, str):
                        status = f"⚠️ String: {indicator_data[:50]}..."
                    elif isinstance(indicator_data, list):
                        if len(indicator_data) > 0:
                            first_item = indicator_data[0]
                            if isinstance(first_item, dict):
                                status = f"✅ List of dicts ({len(indicator_data)} items)"
                                sample_keys = list(first_item.keys())[:3]
                                logger.info(f"      Sample keys: {sample_keys}")
                            else:
                                status = f"⚠️ List but not dicts ({len(indicator_data)} items) - first: {type(first_item)}"
                        else:
                            status = "❌ Empty list"
                    elif isinstance(indicator_data, dict):
                        status = "✅ Dictionary"
                        sample_keys = list(indicator_data.keys())[:3]
                        logger.info(f"      Keys: {sample_keys}")
                    else:
                        status = f"❓ Other: {type(indicator_data)}"
                    
                    logger.info(f"    {indicator_name}: {status}")
            
            # Save raw data first before testing conversion
            logger.info(f"💾 Saving raw technical indicators data...")
            raw_output_file = "data/raw_technical_indicators_debug.json"
            Path("data").mkdir(exist_ok=True)
            with open(raw_output_file, 'w') as f:
                json.dump({
                    'technical_indicators': tech_indicators,
                    'full_enhanced_data': enhanced_data
                }, f, indent=2, default=str)
            logger.info(f"Raw data saved to {raw_output_file}")
            
            # Test scanner conversion method directly
            logger.info(f"🔄 Testing scanner data conversion method...")
            
            try:
                # Import the method directly to test it
                from src.analysis.scanner import PMCCScanner
                # Create a dummy scanner instance for accessing the method
                # We'll use a temporary workaround to avoid full initialization
                class TempScanner:
                    def __init__(self):
                        self.logger = logger
                
                temp_scanner = TempScanner()
                # Get the method from PMCCScanner class
                conversion_method = PMCCScanner._enhanced_stock_data_to_dict
                # Call it with temp_scanner as self
                converted_data = conversion_method(temp_scanner, enhanced_data)
                logger.info(f"✅ Scanner conversion successful!")
                
                # Check converted technical indicators
                if 'technical_indicators' in converted_data:
                    conv_tech = converted_data['technical_indicators']
                    logger.info(f"📈 Converted technical indicators:")
                    for key, value in conv_tech.items():
                        logger.info(f"    {key}: {value} ({type(value).__name__})")
                else:
                    logger.warning(f"⚠️ No technical indicators in converted data")
                
                # Save data for inspection
                output_file = "data/technical_indicators_direct_test.json"
                Path("data").mkdir(exist_ok=True)
                with open(output_file, 'w') as f:
                    json.dump({
                        'raw_technical_indicators': tech_indicators,
                        'converted_data': converted_data
                    }, f, indent=2, default=str)
                logger.info(f"💾 Test data saved to {output_file}")
                
                return True
                
            except Exception as convert_error:
                logger.error(f"❌ Scanner conversion failed: {convert_error}")
                logger.exception("Full conversion error:")
                return False
        else:
            logger.warning(f"⚠️ No technical indicators in enhanced data")
            logger.info(f"Available keys: {list(enhanced_data.keys())}")
            
            # Still save the data to see what we got
            output_file = "data/technical_indicators_no_data.json"
            Path("data").mkdir(exist_ok=True)
            with open(output_file, 'w') as f:
                json.dump(enhanced_data, f, indent=2, default=str)
            logger.info(f"💾 Data without technical indicators saved to {output_file}")
            return False
        
    except Exception as e:
        logger.error(f"❌ Direct test failed with error: {e}")
        logger.exception("Full error details:")
        return False

def test_individual_technical_indicators():
    """Test individual technical indicator fetching directly."""
    try:
        logger.info("🧪 Testing individual technical indicators directly...")
        
        settings = get_settings()
        eodhd_token = settings.eodhd_api_token or "demo"
        
        # Create enhanced EODHD provider directly
        provider_config = {
            'api_token': eodhd_token,
            'enable_caching': True,
            'cache_ttl_hours': 1
        }
        
        enhanced_provider = SyncEnhancedEODHDProvider(
            provider_type=ProviderType.EODHD,
            config=provider_config
        )
        
        # Test individual technical indicators
        test_symbol = "MSFT"
        logger.info(f"📊 Testing individual technical indicators for {test_symbol}...")
        
        response = enhanced_provider.get_technical_indicators_comprehensive(test_symbol)
        
        if response.is_success:
            tech_data = response.data
            logger.info(f"✅ Individual technical indicators retrieved")
            logger.info(f"📈 Data structure analysis:")
            
            for indicator_name, indicator_data in tech_data.items():
                if indicator_data is None:
                    logger.info(f"    {indicator_name}: None")
                elif isinstance(indicator_data, str):
                    logger.info(f"    {indicator_name}: String - '{indicator_data[:100]}{'...' if len(indicator_data) > 100 else ''}'")
                elif isinstance(indicator_data, list):
                    logger.info(f"    {indicator_name}: List with {len(indicator_data)} items")
                    if len(indicator_data) > 0:
                        first_item = indicator_data[0]
                        logger.info(f"        First item type: {type(first_item)}")
                        if isinstance(first_item, dict):
                            logger.info(f"        First item keys: {list(first_item.keys())}")
                        else:
                            logger.info(f"        First item value: {first_item}")
                elif isinstance(indicator_data, dict):
                    logger.info(f"    {indicator_name}: Dictionary with keys: {list(indicator_data.keys())}")
                else:
                    logger.info(f"    {indicator_name}: {type(indicator_data)} - {indicator_data}")
            
            # Save individual data
            output_file = "data/individual_technical_indicators.json"
            Path("data").mkdir(exist_ok=True)
            with open(output_file, 'w') as f:
                json.dump(tech_data, f, indent=2, default=str)
            logger.info(f"💾 Individual indicators data saved to {output_file}")
            
            return True
        else:
            logger.error(f"❌ Failed to get individual technical indicators: {response.error}")
            return False
    
    except Exception as e:
        logger.error(f"❌ Individual indicator test failed: {e}")
        logger.exception("Full error details:")
        return False

if __name__ == "__main__":
    def main():
        logger.info("🚀 Starting direct technical indicators fix validation...")
        
        # Test 1: Individual technical indicators
        success1 = test_individual_technical_indicators()
        
        # Test 2: Comprehensive data conversion
        success2 = test_technical_indicators_direct()
        
        if success1 and success2:
            logger.info("🎉 All direct technical indicators tests passed!")
            return True
        else:
            logger.error("❌ Some direct tests failed")
            return False
    
    result = main()
    sys.exit(0 if result else 1)