import requests
import pandas as pd
import json

SYMBOL = "BTC-USD"
# 900 = 15 minutes
GRANULARITY = 900
URL = f"https://api.exchange.coinbase.com/products/{SYMBOL}/candles"

def verify_data_structure():
    print(f"Fetching 1 candle from {URL}...")
    params = {'granularity': GRANULARITY}
    response = requests.get(URL, params=params)
    
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        return

    data = response.json()
    if not data:
        print("No data received.")
        return

    # Get the most recent completed candle
    # Coinbase returns [time, low, high, open, close, volume] ? 
    # Let's verify by looking at values. 
    # High should be >= Low, Open, Close.
    # Low should be <= High, Open, Close.
    
    sample = data[0]
    print(f"\nRaw Sample (First Item): {sample}")
    
    # Official Docs say: [ time, low, high, open, close, volume ]
    # Let's map it
    mapped = {
        'time': sample[0],
        'low': sample[1],
        'high': sample[2],
        'open': sample[3],
        'close': sample[4],
        'volume': sample[5]
    }
    
    print("\nProposed Mapping:")
    print(json.dumps(mapped, indent=2))
    
    # Validation Logic
    is_valid = True
    if not (mapped['high'] >= mapped['low']): 
        print("❌ High < Low (Impossible)")
        is_valid = False
    
    if not (mapped['high'] >= mapped['open'] and mapped['high'] >= mapped['close']):
        print("❌ High is not the maximum")
        is_valid = False

    if not (mapped['low'] <= mapped['open'] and mapped['low'] <= mapped['close']):
        print("❌ Low is not the minimum")
        is_valid = False
        
    if is_valid:
        print("\n✅ Data logic holds (High is highest, Low is lowest).")
        print("The mapping [time, low, high, open, close, volume] appears CORRECT.")
    else:
        print("\n❌ Data logic FAILED. Mapping is wrong.")

if __name__ == "__main__":
    verify_data_structure()
