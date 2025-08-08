import sys
sys.path.append("src")
import asyncio
from api.provider_factory import DataProviderFactory
from config.settings import get_settings

async def test_basic_functionality():
    print("=== PMCC AI Enhancement System Validation ===")
    print()
    
    # Test 1: Configuration
    print("1. Configuration Test:")
    settings = get_settings()
    print(f"   Available providers: {settings.get_available_providers()}")
    print()
    
    # Test 2: Provider Factory
    print("2. Provider Factory Test:")
    try:
        factory = DataProviderFactory()
        print(f"   ✓ Factory initialized successfully")
        print()
    except Exception as e:
        print(f"   ❌ Factory initialization failed: {e}")
        return
    
    print("=== Basic Functionality Test Complete ===")

if __name__ == "__main__":
    asyncio.run(test_basic_functionality())
