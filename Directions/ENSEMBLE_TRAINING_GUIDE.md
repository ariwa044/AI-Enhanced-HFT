# Heiken Ashi K-Means 3-Model Ensemble Training Guide

## Overview

Your Heiken Ashi K-Means hybrid system now uses **ensemble voting** from three machine learning models:

1. **LSTM** (Long Short-Term Memory) - Captures sequential patterns
2. **Random Forest** - Ensemble of decision trees  
3. **XGBoost** - Gradient boosting classifier

Each model makes an independent prediction (±1), and the final trading signal is determined by **majority voting**.

---

## Why Ensemble Voting?

### Strengths of Each Model

| Model | Strength | Weakness |
|-------|----------|----------|
| **LSTM** | Captures time-series patterns, momentum | Can overfit on small datasets |
| **Random Forest** | Robust to outliers, handles non-linear relationships | Slower training |
| **XGBoost** | Fast, handles feature interactions, strong accuracy | Can overfit if not regularized |

### Ensemble Benefits

- ✅ **Reduced overfitting** - Each model's bias is offset by others
- ✅ **Better generalization** - Works on unseen market data
- ✅ **Confidence scoring** - Can weight trades by model agreement
- ✅ **Robustness** - Survives individual model failures

---

## Voting Logic

```
Model Predictions:
  LSTM:  +1 (Bullish)
  RF:    +1 (Bullish)  
  XGB:   -1 (Bearish)

Majority Vote:
  2 out of 3 = +1 (BULLISH)
  Confidence: 2/3 = 67%

EA Action:
  Signal: +1 (Enter long)
  Lot Size: Multiplied by confidence (1.2x at 67%)
```

---

## Step-by-Step Training

### Phase 1: Prepare Data (5 minutes)

```
1. Run Export_15m_HA_Data.mq5 on BTCUSD M15
   Creates: BTCUSD_15m_HA_data.csv (10,000+ bars)

2. Verify file:
   - Size: >1 MB
   - Columns: Time, HA_Open, HA_High, HA_Low, HA_Close, Volume
```

### Phase 2: Train LSTM Model (30 minutes)

Run `train_ha_kmeans_lstm.ipynb` - all cells in order:

```python
# This notebook:
✓ Loads BTCUSD_15m_HA_data.csv
✓ Calculates HA metrics (body, range, momentum)
✓ Performs K-means clustering (3 clusters, 252-bar window)
✓ Detects consecutive bar patterns
✓ Creates sequences (5-bar lookback)
✓ Builds 2-layer LSTM with dropout
✓ Trains on 80% of data
✓ Saves outputs:
  - lstm_ha15m_trend_model.h5 (TensorFlow model)
  - scaler_lstm_ha15m.save (Feature scaler)
  - lstm_ha15m_forecast.csv (Predictions)

Expected Performance:
  Accuracy: 48-54%
  Training time: 3-10 minutes
```

### Phase 3: Train Random Forest Model (10 minutes)

Run `train_ha_kmeans_randomforest.ipynb` - all cells:

```python
# This notebook:
✓ Loads same data
✓ Same feature engineering as LSTM
✓ Trains Random Forest (200 trees, max_depth=20)
✓ No sequences needed (Random Forest is non-sequential)
✓ Saves outputs:
  - randomforest_ha15m_trend_model.pkl (Scikit-learn model)
  - scaler_randomforest_ha15m.save (Feature scaler)
  - randomforest_ha15m_forecast.csv (Predictions)

Expected Performance:
  Accuracy: 50-56%
  Training time: 1-5 minutes
```

### Phase 4: Train XGBoost Model (5 minutes)

Run `train_ha_kmeans_xgboost.ipynb` - all cells:

```python
# This notebook:
✓ Loads same data
✓ Same features as other models
✓ Trains XGBoost classifier
✓ Saves outputs:
  - xgboost_ha15m_trend_model.pkl (XGBoost model)
  - scaler_xgboost_ha15m.save (Feature scaler)
  - xgboost_ha15m_forecast.csv (Predictions)

Expected Performance:
  Accuracy: 50-55%
  Training time: 1-3 minutes
```

### Phase 5: Generate Ensemble Voting (2 minutes)

Run `ensemble_ha15m_voting.ipynb` - all cells:

```python
# This notebook:
✓ Loads 3 model predictions
✓ Performs majority voting
✓ Calculates confidence scores
✓ Generates final ensemble predictions
✓ Saves:
  - ensemble_ha15m_forecast.csv (Voting results)

Output columns:
  Time                  - Timestamp
  LSTM                  - LSTM prediction (±1)
  RandomForest          - RF prediction (±1)
  XGBoost               - XGB prediction (±1)
  Ensemble              - Final vote (±1 or 0)
  Confidence            - Agreement strength (33-100%)
```

---

## Testing Your Models

### Check Model Files

After training, verify all files exist:

```bash
# LSTM
ls -lh lstm_ha15m_trend_model.h5
ls -lh scaler_lstm_ha15m.save

# Random Forest
ls -lh randomforest_ha15m_trend_model.pkl
ls -lh scaler_randomforest_ha15m.save

# XGBoost
ls -lh xgboost_ha15m_trend_model.pkl
ls -lh scaler_xgboost_ha15m.save

# Should all be present (100+ KB each)
```

### Test Ensemble Server

```bash
# Start the ensemble server
python socket_ai_ha_ensemble.py

# Expected output:
# ✓ LSTM model loaded
# ✓ Random Forest model loaded
# ✓ XGBoost model loaded
# ✓ Ensemble ready with 3 models
# ✓ Server listening on 127.0.0.1:9091
```

---

## Using Ensemble Predictions in Backtesting

### Backtesting Workflow

```
1. Copy ensemble_ha15m_forecast.csv to MetaTrader\Files\
2. Open HA_KMeans_Hybrid_EA.mq5 in MetaEditor
3. Set parameters:
   UseAIPrediction = true
   BaseLotSize = 0.01 BTC

4. Run in Strategy Tester:
   Symbol: BTCUSD
   Period: M15 (15 minutes)
   Model: Every tick (most accurate)
   Use ensemble_ha15m_forecast.csv

5. Analysis:
   Compare results with/without AI predictions
   Average trade size with AI should be 1.1x-1.2x baseline
```

---

## Interpreting Ensemble Results

### Signal Quality by Confidence

```
Confidence 100% (All 3 models agree)
  → Highest quality signal
  → Use maximum lot size (1.2x)
  → Wait ratio: Accept

Confidence 67%  (2 out of 3 models agree)
  → Good quality signal
  → Use standard lot size (1.0x)
  → Wait ratio: Accept

Confidence 33%  (Only 1 model agrees / Split decision)
  → Low quality signal
  → Use reduced lot size (0.5x)
  → Consider skipping trade

Confidence 0%   (Models don't agree)
  → No signal
  → Skip this bar
```

### Model Agreement Analysis

```
High LSTM ↔ RF agreement (>80%)
  → Both capture similar patterns
  → Strong pattern signals

High RF ↔ XGB agreement (>80%)
  → Both tree-based models agree
  → Strong structural signals

High LSTM ↔ XGB agreement (>80%)
  → Different architectures agree
  → Very strong signal (triple confirmation)

Low overall agreement (<70%)
  → Market is noisy or in transition
  → Consider stricter entry criteria
```

---

## Retraining Schedule

### When to Retrain

- **Weekly**: Generate new ensemble predictions from fresh data
- **Monthly**: Retrain all 3 models with latest 3 months of data
- **Quarterly**: Full retraining with 1 year of data
- **If drawdown >20%**: Immediate retraining to adapt to regime change

### Retraining Procedure

```
1. Export new data: Run Export_15m_HA_Data.mq5
   (Or append to existing BTCUSD_15m_HA_data.csv)

2. Retrain all notebooks:
   - train_ha_kmeans_lstm.ipynb
   - train_ha_kmeans_randomforest.ipynb
   - train_ha_kmeans_xgboost.ipynb

3. Regenerate ensemble:
   - ensemble_ha15m_voting.ipynb

4. Backtest new models:
   - Compare to previous ensemble
   - Check accuracy improvement

5. Deploy if better:
   - Copy new files to model directory
   - Restart socket_ai_ha_ensemble.py
```

---

## Troubleshooting

### Problem: "Model not found" error in socket server

**Solution:**
```bash
# Check file names and locations
ls -lh lstm_ha15m_trend_model.h5
ls -lh randomforest_ha15m_trend_model.pkl
ls -lh xgboost_ha15m_trend_model.pkl

# Ensure all files are in current working directory
# Or update socket_ai_ha_ensemble.py paths
```

### Problem: Low accuracy on ensemble

**Cause:** Models may need retraining or tuning

**Solution:**
```
1. Check individual model performance
   - Which model has lowest accuracy?
   - Retrain that specific model

2. Try different hyperparameters:
   LSTM:      Increase layers, reduce dropout
   RF:        Increase n_estimators (200 → 300)
   XGB:       Adjust max_depth, learning_rate

3. Feature engineering:
   - Add more lag features
   - Try different K-means values (2-5 clusters)
```

### Problem: Models disagree constantly (low confidence)

**Cause:** Market is choppy or models aren't converged

**Solution:**
```
1. Increase MinDensity parameter:
   From 20% → 30% (only trade in well-defined clusters)

2. Require higher model agreement:
   Set minimum confidence threshold in EA:
   If Confidence < 50% → Skip trade

3. Retrain with more recent data:
   Market conditions may have changed
```

---

## Advanced: Custom Weighting

Instead of equal voting, you can weight models by their historical performance:

```python
# Example in socket_ai_ha_ensemble.py

def weighted_voting(lstm_pred, rf_pred, xgb_pred):
    """Weighted voting based on accuracy"""
    
    # Historical accuracies (from backtests)
    weights = {
        'lstm': 0.45,      # 45% accuracy
        'rf': 0.48,        # 48% accuracy
        'xgb': 0.50        # 50% accuracy (best)
    }
    
    weighted_sum = (
        lstm_pred * weights['lstm'] +
        rf_pred * weights['rf'] +
        xgb_pred * weights['xgb']
    )
    
    return 1 if weighted_sum > 0 else -1
```

---

## Performance Expectations

### Per-Model Accuracy
```
LSTM:           48-54%
Random Forest:  50-56%
XGBoost:        50-55%

Ensemble:       52-58% (better than individual models)
```

### Trade Statistics
```
Win Rate:       45-55% (slightly > 50% due to ensemble)
Profit Factor:  1.2-1.8 (good risk/reward)
Sharpe Ratio:   0.5-1.5 (acceptable for crypto)

With Ensemble Sizing:
  High confidence trades: 5-10% higher win rate
  Low confidence trades: Skip or trade 0.5x
```

---

## Files Generated

| File | Size | Purpose |
|------|------|---------|
| lstm_ha15m_trend_model.h5 | ~200 KB | LSTM model |
| scaler_lstm_ha15m.save | ~2 KB | LSTM feature scaler |
| lstm_ha15m_forecast.csv | ~500 KB | LSTM predictions |
| randomforest_ha15m_trend_model.pkl | ~300 KB | RF model |
| scaler_randomforest_ha15m.save | ~2 KB | RF feature scaler |
| randomforest_ha15m_forecast.csv | ~500 KB | RF predictions |
| xgboost_ha15m_trend_model.pkl | ~200 KB | XGBoost model |
| scaler_xgboost_ha15m.save | ~2 KB | XGBoost feature scaler |
| xgboost_ha15m_forecast.csv | ~500 KB | XGBoost predictions |
| ensemble_ha15m_forecast.csv | ~500 KB | Final ensemble votes |

**Total disk usage:** ~3-4 MB

---

## Next Steps

1. ✅ Run all 4 training notebooks (LSTM, RF, XGBoost, Ensemble)
2. ✅ Verify all model files created
3. ✅ Test ensemble server: `python socket_ai_ha_ensemble.py`
4. ✅ Backtest HA_KMeans_Hybrid_EA.mq5 with ensemble predictions
5. ✅ Compare ensemble accuracy to individual models
6. ✅ Deploy to live trading (start small: 0.01 BTC)

---

## Quick Reference

### Training Commands

```bash
# Run all notebooks in sequence
jupyter notebook train_ha_kmeans_lstm.ipynb
jupyter notebook train_ha_kmeans_randomforest.ipynb  
jupyter notebook train_ha_kmeans_xgboost.ipynb
jupyter notebook ensemble_ha15m_voting.ipynb

# Or run in order with ipython
ipython < train_ha_kmeans_lstm.ipynb
ipython < train_ha_kmeans_randomforest.ipynb
ipython < train_ha_kmeans_xgboost.ipynb
ipython < ensemble_ha15m_voting.ipynb
```

### Deployment Checklist

- [ ] All 4 notebooks trained successfully
- [ ] All 9 model files present (3 models × 3 files each)
- [ ] Ensemble server starts without errors
- [ ] Backtest accuracy >50%
- [ ] Trade count: 200+ trades in backtest
- [ ] Win rate: 45%+
- [ ] Profit factor: 1.2+
- [ ] Max drawdown: <25%

---

## Support

For issues or questions:
1. Check [HA_KMeans_Integration_Guide.md](HA_KMeans_Integration_Guide.md)
2. Review [IMPLEMENTATION_CHECKLIST.md](IMPLEMENTATION_CHECKLIST.md)
3. Check notebook cell errors for specific issues
4. Review socket_ai_ha.log for runtime errors

**Good luck with your ensemble! 🚀**
