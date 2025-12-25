# AI-Enhanced Hybrid Trading System

**AI-Enhanced HFT** is a production-ready hybrid trading system combining technical analysis with machine learning. It supports two main strategies:

1. **EMA + ADX Strategy** - Exponential moving average crossovers with trend validation
2. **Heiken Ashi K-Means + Ensemble Strategy** - 3-consecutive-bar pattern recognition with clustering and 3-model AI voting

Both strategies use dynamic lot sizing based on AI signal agreement and are fully compatible with MetaTrader 5 backtesting and live trading.

---

## 🎯 Quick Start

### For Heiken Ashi K-Means Ensemble (Recommended)

```bash
# 1. Export data (5 min)
# → Run Export_15m_HA_Data.mq5 on BTCUSD M15 in MT5

# 2. Train models (30 min)
# → Open Jupyter and run these notebooks in order:
#    - train_ha_kmeans_lstm.ipynb
#    - train_ha_kmeans_randomforest.ipynb
#    - train_ha_kmeans_xgboost.ipynb
#    - ensemble_ha15m_voting.ipynb

# 3. Backtest (varies)
# → Copy ensemble_ha15m_forecast.csv to MetaTrader\Files\
# → Run HA_KMeans_Hybrid_EA.mq5 in Strategy Tester

# 4. Live trade
# → python socket_ai_ha_ensemble.py
# → Attach HA_KMeans_Hybrid_EA.mq5 to live chart
```

---

## 📁 Core Files

### Trading EAs (MetaTrader 5)

| File | Purpose | Timeframe | Symbol |
|------|---------|-----------|--------|
| **HA_KMeans_Hybrid_EA.mq5** | Main ensemble trading EA | M15 | BTCUSD |
| **Export_15m_HA_Data.mq5** | Export HA data for training | M15 | BTCUSD |
| **Ensemble_DayTrader_EA.mq5** | EMA+ADX strategy EA | Flexible | Any |

### Python Components

| File | Purpose | Port | Input |
|------|---------|------|-------|
| **socket_ai_ha_ensemble.py** | 3-model ensemble server (LSTM+RF+XGBoost voting) | 9091 | 15 features |
| **socket_ai_ha.py** | Single XGBoost server | 9091 | 15 features |
| **socket_ai.py** | Legacy EMA+ADX server | 9091 | 15 features |

### Training Notebooks

| Notebook | Output | Runtime |
|----------|--------|---------|
| **train_ha_kmeans_lstm.ipynb** | lstm_ha15m_trend_model.h5 | 30 min |
| **train_ha_kmeans_randomforest.ipynb** | randomforest_ha15m_trend_model.pkl | 10 min |
| **train_ha_kmeans_xgboost.ipynb** | xgboost_ha15m_trend_model.pkl | 5 min |
| **ensemble_ha15m_voting.ipynb** | ensemble_ha15m_forecast.csv | 5 min |

---

## 🏗️ System Architecture

### Heiken Ashi K-Means Ensemble Strategy

```
BTCUSD M15 Chart
    ↓
Entry Signal Detection:
  ✓ 3 consecutive HA bars (up or down)
  ✓ K-means cluster density ≥ 20% (market structure validation)
  ✓ Volume confirmation (current > previous)
    ↓
Feature Calculation:
  • HA body, range, momentum
  • K-means cluster data (3 clusters, 252-bar window)
  • Volume and volatility metrics
    ↓
┌─────────────────────────────────────┐
│  socket_ai_ha_ensemble.py Server    │
├─────────────────────────────────────┤
│ LSTM Model     → Prediction: ±1     │
│ Random Forest  → Prediction: ±1     │
│ XGBoost        → Prediction: ±1     │
│                                     │
│ Majority Voting (2/3 models)       │
│ Result: ±1 (consensus) + confidence │
└─────────────────────────────────────┘
    ↓
Dynamic Lot Sizing:
  • AI agrees: BaseLot × 1.2
  • AI disagrees: BaseLot × 0.5
    ↓
Execute Trade:
  • SL: -100 pips
  • TP: +300 pips
```

### K-Means Clustering

Identifies 3 price clusters from 252-bar history:
- **Cluster Density**: Percentage of bars in primary cluster (Cluster 0)
- **Filter Threshold**: ≥20% minimum density for valid signals
- **Purpose**: Validate market structure quality before trading

Density Levels:
- **< 15%**: Chaotic market (skip signals)
- **15-25%**: Mixed conditions (caution)
- **25-35%**: Good structure (normal trading)
- **> 35%**: Strong consolidation (high confidence)

### AI Agreement Logic

```
Technical Signal: BUY (3 consecutive HA up bars)
    ↓
AI Ensemble: Majority voting (2+ models agree)
    ↓
AGREEMENT (2+ models bullish)   → Lot Size: 1.2×
DISAGREEMENT (split vote)       → Lot Size: 0.5×
```

---

## 🧠 Models & Training

### LSTM (Long Short-Term Memory)
- **Input**: 5-bar sequences of engineered features
- **Architecture**: 2 layers with dropout (0.3)
- **Training**: 80/20 split, up to 100 epochs
- **Strength**: Captures time-series patterns and momentum
- **Output**: 48-54% accuracy typically

### Random Forest
- **Estimators**: 200 trees
- **Max Depth**: 20
- **Training**: 80/20 split, no sequences needed
- **Strength**: Robust to outliers, handles non-linear relationships
- **Output**: 50-56% accuracy typically

### XGBoost
- **Boosting Rounds**: 200-300
- **Max Depth**: 6
- **Learning Rate**: 0.1
- **Strength**: Fast, handles feature interactions, strong accuracy
- **Output**: 52-58% accuracy typically

### Ensemble Benefits
- ✅ Reduced overfitting (voting reduces individual biases)
- ✅ Better generalization (works on unseen market data)
- ✅ Confidence scoring (weight trades by model agreement)
- ✅ Robustness (survives individual model failures)

---

## 🎛️ Configuration Parameters

### Entry Signals
```
ConsecutiveBarsUp = 3          (3-5 bars typically)
ConsecutiveBarsDown = 3        (3-5 bars typically)
```

### K-Means Clustering
```
KMeans_K = 3                   (3-5 clusters)
KMeans_TrainBars = 252         (252 = 1 trading week on M15)
MinClusterDensityPercent = 20   (15-30% typical range)
```

### Position Sizing
```
BaseLotSize = 0.01 BTC         (adjust per risk tolerance)
LotMultiplierAgreement = 1.2    (when AI agrees)
LotMultiplierDisagreement = 0.5 (when AI disagrees)
UseAIPrediction = true          (enable/disable ensemble voting)
```

### Risk Management
```
StopLoss_Pips = 100
TakeProfit_Pips = 300
RiskPercent = 2% per trade
```

---

## 📊 Setup Instructions

### Step 1: Export Historical Data (5 min)

1. Open MetaTrader 5
2. Open BTCUSD chart (15-minute timeframe)
3. Create new EA → Paste `Export_15m_HA_Data.mq5` code
4. Compile (F7) and run on chart
5. Verify: `MetaTrader\Files\BTCUSD_15m_HA_data.csv` created (>500 KB)

### Step 2: Train Models (30-45 min total)

1. Ensure `BTCUSD_15m_HA_data.csv` is in your working directory
2. Run Jupyter notebooks **in this order**:
   ```
   train_ha_kmeans_lstm.ipynb
   train_ha_kmeans_randomforest.ipynb
   train_ha_kmeans_xgboost.ipynb
   ensemble_ha15m_voting.ipynb
   ```
3. Verify output files created:
   - `lstm_ha15m_trend_model.h5`
   - `randomforest_ha15m_trend_model.pkl`
   - `xgboost_ha15m_trend_model.pkl`
   - `ensemble_ha15m_forecast.csv`
   - Scalers: `scaler_*.save`

### Step 3: Backtest (Varies)

1. Copy `ensemble_ha15m_forecast.csv` → `MetaTrader\Files\`
2. Compile `HA_KMeans_Hybrid_EA.mq5`
3. Open Strategy Tester (Ctrl+R)
4. **Settings**:
   - Expert Advisor: HA_KMeans_Hybrid_EA
   - Symbol: BTCUSD
   - Period: M15
   - Model: Every tick
   - FromDate: 1 year ago
   - ToDate: Today
5. Click "Start" and monitor results

### Step 4: Live Trading (Optional)

1. Start AI server:
   ```bash
   python socket_ai_ha_ensemble.py
   ```
2. In MetaTrader:
   - Attach `HA_KMeans_Hybrid_EA.mq5` to live BTCUSD M15 chart
   - Set `UseAIPrediction = true`
   - Set `BaseLotSize` per your risk tolerance
   - Enable AutoTrading
3. Monitor Expert Advisor journal for signal execution

---

## 🐛 Troubleshooting

### CSV File Not Found
- Verify file in `MetaTrader\Files\` directory (not Experts folder)
- Check header matches: `Time,LSTM,RandomForest,XGBoost,Ensemble,Confidence`

### No Trades Executing
- Check Experts journal for error messages
- Verify K-means density meets threshold (default 20%)
- Ensure CSV data covers backtest date range

### Socket Connection Failed
- Ensure `socket_ai_ha_ensemble.py` is running: `python socket_ai_ha_ensemble.py`
- Check port 9091 is available
- Verify firewall allows Python connections

### Poor Backtest Results
- Adjust `MinClusterDensityPercent` (try 15 or 25)
- Adjust `ConsecutiveBarsUp/Down` (try 2 or 4)
- Retrain models if data is stale (>30 days old)

---

## 📈 Expected Performance

Based on backtests with 1 year BTCUSD M15 data:

| Metric | Range | Status |
|--------|-------|--------|
| **Win Rate** | 40-60% | Expected |
| **Profit Factor** | > 1.2 | Acceptable |
| **Sharpe Ratio** | > 0.5 | Good |
| **Max Drawdown** | < 25% | Healthy |
| **Model Accuracy** | 50-58% | Competitive |

*Results vary based on market conditions, parameters, and timeframe*

---

## 🔄 Legacy Strategy: EMA + ADX

The system also includes the original EMA/ADX-based strategy (Ensemble_DayTrader_EA.mq5):
- **Entry**: EMA 6/24 crossover with ADX > 22 confirmation
- **Volume**: Current bar > previous bar requirement
- **Exit**: Stop loss (100 pips), Take profit (300 pips), or ADX < 25
- **AI Integration**: Optional socket connection for prediction confirmation

This strategy works on any timeframe/symbol but has been superseded by the Heiken Ashi ensemble approach for BTCUSD M15.

---

## 📝 Feature Engineering

The system calculates 15+ features from raw OHLCV data:

**Heiken Ashi Properties**:
- Body size, range, momentum
- Direction (up/down candle)

**K-Means Clustering**:
- Cluster assignments (0, 1, 2)
- Cluster distances
- Density percentage per cluster

**Volume & Volatility**:
- Volume confirmation
- Price range
- Momentum indicators

**Pattern Detection**:
- Consecutive bars counter
- Direction confirmation

---

## ⚙️ Installation & Dependencies

### Python Requirements
```bash
pip install pandas numpy scikit-learn xgboost joblib tensorflow matplotlib seaborn
```

### MetaTrader 5 Requirements
- MT5 terminal installed
- Heiken Ashi indicator available (standard Examples folder)
- Network connectivity for socket (live trading only)

---

## 📄 File Inventory

**Core Trading Files**: 3 MQL5 scripts
**Python Components**: 3 server scripts
**Training Notebooks**: 4 Jupyter notebooks
**Data Files**: CSVs and trained models (generated during training)
**Models**: H5 (LSTM), PKL (RF/XGBoost), JSON (config)

---

## ✅ Checklist

- [ ] Python 3.8+ with required packages installed
- [ ] MetaTrader 5 terminal running
- [ ] BTCUSD M15 chart available
- [ ] Data exported via Export_15m_HA_Data.mq5
- [ ] All 4 notebooks trained successfully
- [ ] Output models saved to working directory
- [ ] Forecast CSV copied to MetaTrader\Files\
- [ ] EA compiled without errors
- [ ] Backtest completed successfully
- [ ] Results reviewed and parameters optimized

---

## 📞 Support

For issues:
1. Check journal/logs for error messages
2. Verify all files in correct directories
3. Ensure CSV format matches expected structure
4. Retrain models if data is stale (>30 days old)
5. Review parameter settings against your market conditions
