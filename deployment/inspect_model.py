import joblib
import os
import sys

MODEL_DIR = os.path.join(os.path.dirname(__file__), "app", "models")
MODEL_PATH = os.path.join(MODEL_DIR, "randomforest_ha15m_trend_model.pkl")

print(f"Inspecting: {MODEL_PATH}")

try:
    model = joblib.load(MODEL_PATH)
    if hasattr(model, "feature_names_in_"):
        print("\n✅ REQUIRED FEATURES (Correct Order):")
        for i, name in enumerate(model.feature_names_in_):
            print(f"{i}: {name}")
    else:
        print("\n⚠️ Model does not have 'feature_names_in_' attribute.")
        print(f"n_features_in_: {model.n_features_in_}")

except Exception as e:
    print(f"\n❌ Error loading model: {e}")
