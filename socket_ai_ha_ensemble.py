#!/usr/bin/env python3
"""
Heiken Ashi K-Means Ensemble AI Service v2.0
Real-time prediction server using LSTM, Random Forest, and XGBoost ensemble voting
for HA_KMeans_Hybrid_EA.mq5

Usage:
  python socket_ai_ha_ensemble.py

Listens on port 9091 for incoming feature vectors from MT5 EA
Returns ±1 prediction via majority voting across 3 models

Voting Logic:
  2+ models predict +1 → signal = +1 (BULLISH)
  2+ models predict -1 → signal = -1 (BEARISH)
  Mixed decision → signal = 0 (NEUTRAL - skip trade)
"""

import socket
import numpy as np
import joblib
import traceback
import warnings
import sys
import tensorflow as tf
from tensorflow.keras.models import load_model

warnings.filterwarnings("ignore", category=UserWarning)

print("=" * 70)
print("Heiken Ashi K-Means Ensemble AI Service v2.0")
print("3-Model Voting: LSTM + Random Forest + XGBoost")
print("=" * 70)

# === Configuration ===
HOST = '127.0.0.1'
PORT = 9091
N_FEATURES = 15  # Match EA feature count
TIMEOUT = 5.0

# === Load All Three Models ===
models = {}
scalers = {}
models_ready = 0

print("\n[LOADING MODELS]")

# Load LSTM
try:
    print("[1/3] Loading LSTM model...")
    models['lstm'] = load_model("lstm_ha15m_trend_model.h5")
    scalers['lstm'] = joblib.load("scaler_lstm_ha15m.save")
    print("  ✓ LSTM model loaded")
    models_ready += 1
except Exception as e:
    print(f"  ✗ LSTM load failed: {e}")
    models['lstm'] = None

# Load Random Forest
try:
    print("[2/3] Loading Random Forest model...")
    models['rf'] = joblib.load("randomforest_ha15m_trend_model.pkl")
    scalers['rf'] = joblib.load("scaler_randomforest_ha15m.save")
    print("  ✓ Random Forest model loaded")
    models_ready += 1
except Exception as e:
    print(f"  ✗ Random Forest load failed: {e}")
    models['rf'] = None

# Load XGBoost
try:
    print("[3/3] Loading XGBoost model...")
    models['xgb'] = joblib.load("xgboost_ha15m_trend_model.pkl")
    scalers['xgb'] = joblib.load("scaler_xgboost_ha15m.save")
    print("  ✓ XGBoost model loaded")
    models_ready += 1
except Exception as e:
    print(f"  ✗ XGBoost load failed: {e}")
    models['xgb'] = None

if models_ready < 2:
    print(f"\n✗ CRITICAL: Only {models_ready} model(s) loaded")
    print("  Need at least 2 models for ensemble voting")
    print("\nRequired files:")
    print("  LSTM:         lstm_ha15m_trend_model.h5 + scaler_lstm_ha15m.save")
    print("  Random Forest: randomforest_ha15m_trend_model.pkl + scaler_randomforest_ha15m.save")
    print("  XGBoost:      xgboost_ha15m_trend_model.pkl + scaler_xgboost_ha15m.save")
    sys.exit(1)

print(f"\n✓ Ensemble ready with {models_ready} models")

# === Helper Functions ===

def preprocess_input(data_str):
    """Convert string input to scaled feature vectors for all models"""
    try:
        values = list(map(float, data_str.strip().split()))
        
        if len(values) != N_FEATURES:
            raise ValueError(f"Expected {N_FEATURES} features, got {len(values)}")
        
        # Create single array
        X = np.array(values).reshape(1, -1)
        
        # Scale for each model
        X_scaled = {}
        if models['lstm'] is not None:
            X_scaled['lstm'] = scalers['lstm'].transform(X)
        if models['rf'] is not None:
            X_scaled['rf'] = scalers['rf'].transform(X)
        if models['xgb'] is not None:
            X_scaled['xgb'] = scalers['xgb'].transform(X)
        
        return X_scaled
    except Exception as e:
        raise ValueError(f"Input preprocessing error: {e}")

def predict_lstm(X_scaled):
    """LSTM prediction"""
    try:
        # LSTM expects sequence input, use last bar
        # Reshape: (1, 5, 15) for sequence length 5
        X_seq = X_scaled.reshape(1, 1, -1)  # (1, 1, 15)
        pred = models['lstm'].predict(X_seq, verbose=0)[0][0]
        return 1 if pred > 0 else -1
    except:
        return 0  # Error return

def predict_rf(X_scaled):
    """Random Forest prediction"""
    try:
        pred = models['rf'].predict(X_scaled)[0]
        return 1 if pred == 1 else -1
    except:
        return 0

def predict_xgb(X_scaled):
    """XGBoost prediction"""
    try:
        pred = models['xgb'].predict(X_scaled)[0]
        return 1 if pred == 1 else -1
    except:
        return 0

def ensemble_voting(lstm_pred, rf_pred, xgb_pred):
    """Majority voting across 3 models"""
    votes = []
    
    if lstm_pred != 0:
        votes.append(lstm_pred)
    if rf_pred != 0:
        votes.append(rf_pred)
    if xgb_pred != 0:
        votes.append(xgb_pred)
    
    if not votes:
        return 0, 0  # No valid predictions
    
    bullish = sum(1 for v in votes if v == 1)
    bearish = sum(1 for v in votes if v == -1)
    
    # Majority voting
    if bullish >= len(votes) / 2:
        confidence = bullish / len(votes)
        return 1, confidence
    elif bearish >= len(votes) / 2:
        confidence = bearish / len(votes)
        return -1, confidence
    else:
        return 0, 0.33  # No consensus

def make_prediction(X_scaled):
    """Get predictions from all models and vote"""
    try:
        # Get individual predictions
        lstm_pred = predict_lstm(X_scaled['lstm']) if 'lstm' in X_scaled else 0
        rf_pred = predict_rf(X_scaled['rf']) if 'rf' in X_scaled else 0
        xgb_pred = predict_xgb(X_scaled['xgb']) if 'xgb' in X_scaled else 0
        
        # Ensemble voting
        ensemble_pred, confidence = ensemble_voting(lstm_pred, rf_pred, xgb_pred)
        
        return ensemble_pred, confidence, (lstm_pred, rf_pred, xgb_pred)
    except Exception as e:
        raise RuntimeError(f"Prediction error: {e}")

# === Server ===
def start_server():
    """Start TCP socket server"""
    print("\n" + "=" * 70)
    print("Starting Ensemble AI Prediction Server...")
    print("=" * 70)
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((HOST, PORT))
            s.listen(1)
            s.settimeout(TIMEOUT)
            
            print(f"\n✓ Server listening on {HOST}:{PORT}")
            print(f"✓ Ensemble voting active ({models_ready} models)")
            print(f"✓ Ready for HA_KMeans_Hybrid_EA.mq5 connections")
            print(f"\nWaiting for predictions... (Press Ctrl+C to stop)\n")
            
            request_count = 0
            bullish_count = 0
            bearish_count = 0
            neutral_count = 0
            
            while True:
                try:
                    # Accept connection
                    conn, addr = s.accept()
                    request_count += 1
                    
                    with conn:
                        # Set connection timeout
                        conn.settimeout(TIMEOUT)
                        
                        # Receive data
                        data = conn.recv(4096).decode('utf-8')
                        
                        if not data:
                            print(f"[{request_count}] Empty data received")
                            conn.sendall(b"0")
                            continue
                        
                        try:
                            # Preprocess
                            X_scaled_dict = preprocess_input(data)
                            
                            # Predict with ensemble
                            prediction, confidence, votes = make_prediction(X_scaled_dict)
                            
                            # Count signals
                            if prediction == 1:
                                bullish_count += 1
                                signal = "BULLISH"
                            elif prediction == -1:
                                bearish_count += 1
                                signal = "BEARISH"
                            else:
                                neutral_count += 1
                                signal = "NEUTRAL"
                            
                            # Send response
                            response = str(prediction).encode('utf-8')
                            conn.sendall(response)
                            
                            # Log
                            lstm_pred, rf_pred, xgb_pred = votes
                            vote_str = f"[LSTM:{lstm_pred:+d} RF:{rf_pred:+d} XGB:{xgb_pred:+d}]"
                            print(f"[{request_count}] {signal:7s} {vote_str} (conf: {confidence:.0%})")
                            
                        except ValueError as ve:
                            print(f"[{request_count}] ✗ Preprocessing error: {ve}")
                            conn.sendall(b"0")
                        except RuntimeError as re:
                            print(f"[{request_count}] ✗ Prediction error: {re}")
                            conn.sendall(b"0")
                
                except socket.timeout:
                    # No connection, keep listening
                    continue
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"[{request_count}] Connection error: {e}")
                    continue
        
        print("\n" + "=" * 70)
        print("Server stopped")
        print(f"Total requests: {request_count}")
        print(f"  Bullish:  {bullish_count}")
        print(f"  Bearish:  {bearish_count}")
        print(f"  Neutral:  {neutral_count}")
        print("=" * 70)
    
    except OSError as e:
        print(f"\n✗ Server error: {e}")
        if "Address already in use" in str(e):
            print(f"  Port {PORT} is already in use")
            print(f"  Try stopping other instances or using a different port")
        sys.exit(1)

if __name__ == "__main__":
    try:
        start_server()
    except Exception as e:
        print(f"\n✗ CRITICAL ERROR: {e}")
        traceback.print_exc()
        sys.exit(1)
