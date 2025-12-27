import os
import joblib
import numpy as np
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from .schemas import PredictionRequest, PredictionResponse

# Global variables for models and scalers
models = {}
scalers = {}

# Paths to models (relative to /code/app/models inside Docker)
# When running locally from deployment root: app/models/
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load models on startup
    print("Loading models...")
    try:
        models['rf'] = joblib.load(os.path.join(MODEL_DIR, "randomforest_ha15m_trend_model.pkl"))
        scalers['rf'] = joblib.load(os.path.join(MODEL_DIR, "scaler_randomforest_ha15m.save"))
        print("✓ Random Forest loaded")
        
        models['xgb'] = joblib.load(os.path.join(MODEL_DIR, "xgboost_ha15m_trend_model.pkl"))
        scalers['xgb'] = joblib.load(os.path.join(MODEL_DIR, "scaler_xgboost_ha15m.save"))
        print("✓ XGBoost loaded")
    except Exception as e:
        print(f"Error loading models: {e}")
        # In production, you might want to exit if models fail to load
    
    yield
    # Clean up (if needed)

app = FastAPI(title="HFT Ensemble Trading API", lifespan=lifespan)

def predict_rf(X_scaled):
    try:
        pred = models['rf'].predict(X_scaled)[0]
        return 1 if pred == 1 else -1
    except:
        return 0

def predict_xgb(X_scaled):
    try:
        pred = models['xgb'].predict(X_scaled)[0]
        return 1 if pred == 1 else -1
    except:
        return 0

@app.get("/")
def read_root():
    return {"status": "occupado", "models_loaded": list(models.keys())}

@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest):
    if not models.get('rf') or not models.get('xgb'):
        raise HTTPException(status_code=503, detail="Models not loaded")

    try:
        # Preprocess input
        features = np.array(request.features).reshape(1, -1)
        
        # Scale separately for each model (they might have different scalers even if trained on same data)
        X_rf = scalers['rf'].transform(features)
        X_xgb = scalers['xgb'].transform(features)
        
        # Get predictions
        vote_rf = predict_rf(X_rf)
        vote_xgb = predict_xgb(X_xgb)
        
        # Voting Logic: Consensus required for 2 models
        signal = 0
        confidence = 0.0
        
        if vote_rf == 1 and vote_xgb == 1:
            signal = 1
            confidence = 1.0
        elif vote_rf == -1 and vote_xgb == -1:
            signal = -1
            confidence = 1.0
        else:
            signal = 0
            confidence = 0.5 # Split vote
            
        return PredictionResponse(
            signal=signal,
            confidence=confidence,
            votes={"rf": int(vote_rf), "xgb": int(vote_xgb)}
        )

    except Exception as e:
        # Log the full error in production
        print(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
