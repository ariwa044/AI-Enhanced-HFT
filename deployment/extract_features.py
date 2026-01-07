import joblib
import pandas as pd
import numpy as np
import os
import sys

MODEL_PATH = os.path.join(os.path.dirname(__file__), "app", "models", "scaler_randomforest_ha15m.save")

print(f"Loading scaler from: {MODEL_PATH}")

try:
    scaler = joblib.load(MODEL_PATH)
    
    # Create a dummy dataframe with a random column to trigger the error
    dummy_df = pd.DataFrame(np.zeros((1, 1)), columns=["Dummy_Column"])
    
    print("Attempting transform to trigger error...")
    scaler.transform(dummy_df)

except Exception as e:
    print("\n--- CAUGHT EXCEPTION ---")
    print(e)
    print("------------------------")
