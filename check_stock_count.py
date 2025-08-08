#!/usr/bin/env python3
from eodhd import APIClient
from src.config.settings import get_settings

settings = get_settings()
client = APIClient(api_key=settings.eodhd.api_token)

# Check if there are more stocks beyond offset 999
for exchange in ['NYSE', 'NASDAQ']:
    resp = client.stock_market_screener(
        filters=[['market_capitalization', '>=', 50000000], 
                 ['market_capitalization', '<=', 5000000000],
                 ['avgvol_200d', '>=', 100000],
                 ['exchange', '=', exchange]],
        limit=10,
        offset=995
    )
    if resp and 'data' in resp:
        count = len(resp['data'])
        print(f'{exchange} at offset 995: {count} stocks returned')
        if count == 10:
            print(f'  → More stocks likely exist beyond offset 999 limit!')
        if count > 0:
            last_stock = resp['data'][-1]
            print(f'  Last stock: {last_stock.get("code")} - Market Cap: ${last_stock.get("market_capitalization", 0):,.0f}')