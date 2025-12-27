import requests
import json
import random

# URL of the local server (or deployed URL)
URL = "http://localhost:8000/predict"

def test_prediction():
    print(f"Testing API at {URL}...")
    
    # Generate random dummy features (15 floats)
    dummy_features = [random.uniform(10, 100) for _ in range(15)]
    
    payload = {
        "features": dummy_features
    }
    
    try:
        response = requests.post(URL, json=payload)
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("Response:")
            print(json.dumps(data, indent=2))
            
            # Basic validation
            if "signal" in data and "confidence" in data:
                print("✅ Response structure valid")
            else:
                print("❌ Invalid response structure")
        else:
            print(f"❌ Error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Is it running?")
        print("Run: uvicorn deployment.app.main:app --host 0.0.0.0 --port 80")

if __name__ == "__main__":
    test_prediction()
