import asyncio
import websockets
import json
import numpy as np

WS_URL = "ws://localhost:8080/ws"

async def test_websocket():
    print(f"Connecting to {WS_URL}...")
    try:
        async with websockets.connect(WS_URL) as websocket:
            print("Connected!")
            
            # Create dummy features (15 floats)
            dummy_features = list(np.random.rand(15))
            
            print("Sending features...")
            await websocket.send(json.dumps({"features": dummy_features}))
            
            print("Waiting for response...")
            response = await websocket.recv()
            data = json.loads(response)
            
            print(f"Received: {json.dumps(data, indent=2)}")
            
            if "signal" in data and "confidence" in data:
                print("✓ Test Passed: Valid signal received")
            else:
                print("✗ Test Failed: Invalid response structure")
                
    except Exception as e:
        print(f"Test Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
