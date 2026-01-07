import joblib
import os
import sys
import xgboost as xgb

MODEL_DIR = os.path.join(os.path.dirname(__file__), "app", "models")
MODEL_PATH = os.path.join(MODEL_DIR, "xgboost_ha15m_trend_model.pkl")

print(f"Inspecting: {MODEL_PATH}")

try:
    model = joblib.load(MODEL_PATH)
    print(f"Type: {type(model)}")
    
    if hasattr(model, "feature_names_in_"):
        print("\n✅ REQUIRED FEATURES (feature_names_in_):")
        for i, name in enumerate(model.feature_names_in_):
            print(f"{i}: {name}")
    elif hasattr(model, "get_booster"):
        print("\n✅ REQUIRED FEATURES (get_dump):")
        print(model.get_booster().feature_names)
    else:
        print("\n⚠️ Feature names not found directly.")

except Exception as e:
    print(f"\n❌ Error loading model: {e}")
