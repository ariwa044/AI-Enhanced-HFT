import asyncio
import websockets
import json

WS_URL = "wss://ws-feed.exchange.coinbase.com"
SYMBOL = "BTC-USD"

async def test_coinbase_websocket():
    print(f"Connecting to {WS_URL}...")
    try:
        async with websockets.connect(WS_URL) as websocket:
            print("Connected!")
            
            # Subscribe message
            subscribe_msg = {
                "type": "subscribe",
                "product_ids": [SYMBOL],
                "channels": ["ticker"]
            }
            
            print(f"Subscribing to {SYMBOL} ticker...")
            await websocket.send(json.dumps(subscribe_msg))
            
            print("Waiting for messages (Ctrl+C to stop)...")
            count = 0
            while count < 5:
                response = await websocket.recv()
                data = json.loads(response)
                
                if data.get("type") == "ticker":
                    print(f"[{count+1}] Price: {data.get('price')} | Time: {data.get('time')}")
                    count += 1
                elif data.get("type") == "subscriptions":
                    print(f"Subscription confirmed: {data}")
            
            print("\n✓ Test Passed: Successfully received ticker updates")
                
    except Exception as e:
        print(f"Test Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_coinbase_websocket())
