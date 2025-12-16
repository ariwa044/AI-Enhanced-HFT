#!/usr/bin/env python3
"""
Heiken Ashi K-Means Ensemble AI Service
Real-time prediction server using LSTM, Random Forest, and XGBoost ensemble voting
for HA_KMeans_Hybrid_EA.mq5

Usage:
  python socket_ai_ha.py

Listens on port 9091 for incoming feature vectors from MT5 EA
Returns ±1 prediction via majority voting across 3 models
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
print("Heiken Ashi K-Means Ensemble AI Service v2.0 (3-Model Voting)")
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

# Load Random Forest
try:
    print("[2/3] Loading Random Forest model...")
    models['rf'] = joblib.load("randomforest_ha15m_trend_model.pkl")
    scalers['rf'] = joblib.load("scaler_randomforest_ha15m.save")
    print("  ✓ Random Forest model loaded")
    models_ready += 1
except Exception as e:
    print(f"  ✗ Random Forest load failed: {e}")

# Load XGBoost
try:
    print("[3/3] Loading XGBoost model...")
    models['xgb'] = joblib.load("xgboost_ha15m_trend_model.pkl")
    scalers['xgb'] = joblib.load("scaler_xgboost_ha15m.save")
    print("  ✓ XGBoost model loaded")
    models_ready += 1
except Exception as e:
    print(f"  ✗ XGBoost load failed: {e}")

if models_ready < 2:
    print(f"\n✗ CRITICAL: Only {models_ready} model(s) loaded")
    print("  Need at least 2 models for ensemble voting")
    print("  - xgboost_ha15m_trend_model.pkl")
    sys.exit(1)

# === Helper Functions ===
def preprocess_input(data_str):
    """Convert string input to scaled feature vector"""
    try:
        values = list(map(float, data_str.strip().split()))
        
        if len(values) != N_FEATURES:
            raise ValueError(f"Expected {N_FEATURES} features, got {len(values)}")
        
        # Reshape for scaler
        X = np.array(values).reshape(1, -1)
        X_scaled = scaler.transform(X)
        
        return X_scaled
    except Exception as e:
        raise ValueError(f"Input preprocessing error: {e}")

def make_prediction(X_scaled):
    """Make prediction with model"""
    try:
        # Predict probability
        y_pred_proba = model.predict_proba(X_scaled)[0]
        
        # Get class prediction
        y_pred = model.predict(X_scaled)[0]
        
        # Convert to ±1 format for EA
        # Class 0 = down (-1), Class 1 = up (1)
        prediction = 1 if y_pred == 1 else -1
        confidence = max(y_pred_proba)
        
        return prediction, confidence
    except Exception as e:
        raise RuntimeError(f"Prediction error: {e}")

# === Server ===
def start_server():
    """Start TCP socket server"""
    print("\n" + "=" * 60)
    print("Starting AI Prediction Server...")
    print("=" * 60)
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((HOST, PORT))
            s.listen(1)
            s.settimeout(TIMEOUT)
            
            print(f"\n✓ Server listening on {HOST}:{PORT}")
            print(f"✓ Ready to accept connections from HA_KMeans_Hybrid_EA.mq5")
            print(f"\nWaiting for predictions... (Press Ctrl+C to stop)\n")
            
            request_count = 0
            
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
                            X_scaled = preprocess_input(data)
                            
                            # Predict
                            prediction, confidence = make_prediction(X_scaled)
                            
                            # Send response
                            response = str(prediction).encode('utf-8')
                            conn.sendall(response)
                            
                            print(f"[{request_count}] Prediction: {prediction:+d} (confidence: {confidence:.2%})")
                            
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
        
        print("\n" + "=" * 60)
        print("Server stopped")
        print(f"Total predictions made: {request_count}")
        print("=" * 60)
    
    except OSError as e:
        print(f"\n✗ SERVER ERROR:")
        print(f"  {e}")
        print(f"\nPossible issues:")
        print(f"  - Port {PORT} already in use")
        print(f"  - Permission denied (try running as admin)")
        print(f"  - Network configuration issue")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        traceback.print_exc()
        sys.exit(1)

# === Entry Point ===
if __name__ == "__main__":
    try:
        start_server()
    except KeyboardInterrupt:
        print("\n\n✓ Server shutdown by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ FATAL ERROR: {e}")
        traceback.print_exc()
        sys.exit(1)
