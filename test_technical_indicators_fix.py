#!/usr/bin/env python3
"""
Test script to validate technical indicators data structure fixes.
"""

import asyncio
import sys
import logging
from pathlib import Path
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config import get_settings
from src.api.provider_factory import SyncDataProviderFactory
from src.analysis.scanner import PMCCScanner

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_technical_indicators_fix():
    """Test the technical indicators data structure fixes."""
    try:
        logger.info("🔧 Testing technical indicators data structure fixes...")
        
        # Initialize components
        settings = get_settings()
        factory = SyncDataProviderFactory(settings)
        
        # Get enhanced EODHD provider
        eodhd_provider = factory.get_provider('get_comprehensive_enhanced_data')
        if not eodhd_provider:
            logger.error("❌ Enhanced EODHD provider not available")
            return False
        
        logger.info(f"📊 Using provider: {type(eodhd_provider).__name__}")
        
        # Test comprehensive enhanced data collection for a specific symbol
        test_symbol = "KSS"
        logger.info(f"🧪 Testing comprehensive data collection for {test_symbol}...")
        
        response = eodhd_provider.get_comprehensive_enhanced_data(test_symbol)
        
        if not response.is_success:
            logger.error(f"❌ Failed to get comprehensive data: {response.error}")
            return False
        
        enhanced_data = response.data
        logger.info(f"✅ Comprehensive data retrieved successfully")
        
        # Examine technical indicators structure
        if 'technical_indicators' in enhanced_data:
            tech_indicators = enhanced_data['technical_indicators']
            logger.info(f"🔍 Technical indicators analysis:")
            logger.info(f"  Type: {type(tech_indicators)}")
            
            if isinstance(tech_indicators, dict):
                for indicator_name, indicator_data in tech_indicators.items():
                    data_type = type(indicator_data)
                    if indicator_data is None:
                        status = "❌ None"
                    elif isinstance(indicator_data, str):
                        status = f"⚠️ String: {indicator_data[:30]}..."
                    elif isinstance(indicator_data, list):
                        if len(indicator_data) > 0 and isinstance(indicator_data[0], dict):
                            status = f"✅ List of dicts ({len(indicator_data)} items)"
                        else:
                            status = f"⚠️ List but not dicts ({len(indicator_data)} items)"
                    elif isinstance(indicator_data, dict):
                        status = "✅ Dictionary"
                    else:
                        status = f"❓ Other: {data_type}"
                    
                    logger.info(f"    {indicator_name}: {status}")
            
            # Test scanner conversion
            logger.info(f"🔄 Testing scanner data conversion...")
            scanner = PMCCScanner(provider_factory=factory)
            
            try:
                converted_data = scanner._enhanced_stock_data_to_dict(enhanced_data)
                logger.info(f"✅ Scanner conversion successful!")
                
                # Check converted technical indicators
                if 'technical_indicators' in converted_data:
                    conv_tech = converted_data['technical_indicators']
                    logger.info(f"📈 Converted technical indicators:")
                    for key, value in conv_tech.items():
                        logger.info(f"    {key}: {value} ({type(value).__name__})")
                else:
                    logger.warning(f"⚠️ No technical indicators in converted data")
                
                # Save converted data for inspection
                output_file = "data/technical_indicators_test_output.json"
                Path("data").mkdir(exist_ok=True)
                with open(output_file, 'w') as f:
                    json.dump(converted_data, f, indent=2, default=str)
                logger.info(f"💾 Converted data saved to {output_file}")
                
                return True
                
            except Exception as convert_error:
                logger.error(f"❌ Scanner conversion failed: {convert_error}")
                logger.exception("Full conversion error:")
                return False
        else:
            logger.warning(f"⚠️ No technical indicators in enhanced data")
            logger.info(f"Available keys: {list(enhanced_data.keys())}")
            return False
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        logger.exception("Full error details:")
        return False
    
    finally:
        pass  # SyncDataProviderFactory doesn't need explicit close

def test_individual_technical_indicators():
    """Test individual technical indicator fetching."""
    try:
        logger.info("🧪 Testing individual technical indicator fetching...")
        
        settings = get_settings()
        factory = SyncDataProviderFactory(settings)
        
        eodhd_provider = factory.get_provider('get_technical_indicators_comprehensive')
        if not eodhd_provider:
            logger.error("❌ Enhanced EODHD provider not available")
            return False
        
        # Test individual indicator call
        test_symbol = "AAPL"
        logger.info(f"📊 Testing individual technical indicators for {test_symbol}...")
        
        response = eodhd_provider.get_technical_indicators_comprehensive(test_symbol)
        
        if response.is_success:
            tech_data = response.data
            logger.info(f"✅ Individual technical indicators retrieved")
            logger.info(f"📈 Data structure analysis:")
            
            for indicator_name, indicator_data in tech_data.items():
                if indicator_data is None:
                    logger.info(f"    {indicator_name}: None")
                elif isinstance(indicator_data, str):
                    logger.info(f"    {indicator_name}: String - {indicator_data[:50]}...")
                elif isinstance(indicator_data, list):
                    logger.info(f"    {indicator_name}: List with {len(indicator_data)} items")
                    if len(indicator_data) > 0:
                        logger.info(f"        First item type: {type(indicator_data[0])}")
                        if isinstance(indicator_data[0], dict):
                            logger.info(f"        First item keys: {list(indicator_data[0].keys())}")
                elif isinstance(indicator_data, dict):
                    logger.info(f"    {indicator_name}: Dictionary with keys: {list(indicator_data.keys())}")
                else:
                    logger.info(f"    {indicator_name}: {type(indicator_data)}")
            
            return True
        else:
            logger.error(f"❌ Failed to get technical indicators: {response.error}")
            return False
    
    except Exception as e:
        logger.error(f"❌ Individual indicator test failed: {e}")
        logger.exception("Full error details:")
        return False
    
    finally:
        pass  # SyncDataProviderFactory doesn't need explicit close

if __name__ == "__main__":
    def main():
        logger.info("🚀 Starting technical indicators fix validation...")
        
        # Test 1: Individual technical indicators
        success1 = test_individual_technical_indicators()
        
        # Test 2: Comprehensive data conversion
        success2 = test_technical_indicators_fix()
        
        if success1 and success2:
            logger.info("🎉 All technical indicators tests passed!")
            return True
        else:
            logger.error("❌ Some tests failed")
            return False
    
    result = main()
    sys.exit(0 if result else 1)