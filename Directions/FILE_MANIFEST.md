# Complete File Manifest - Heiken Ashi K-Means Ensemble System

## Quick Navigation

**New to this system?** Start with: [START_HERE.md](START_HERE.md)

**Want to train models?** Go to: [ENSEMBLE_TRAINING_GUIDE.md](ENSEMBLE_TRAINING_GUIDE.md)

**Need full reference?** See: [HA_KMeans_Integration_Guide.md](HA_KMeans_Integration_Guide.md)

---

## 📁 Complete File Listing

### 🤖 TRADING EAs (MetaTrader 5)

#### `HA_KMeans_Hybrid_EA.mq5` (485 lines)
- **Purpose**: Main trading Expert Advisor
- **Symbol**: BTCUSD
- **Timeframe**: M15 (15 minutes)
- **Key Features**:
  - Heiken Ashi 3-consecutive-bar pattern detection
  - K-means clustering (3 clusters, 252-bar window)
  - Cluster density validation (≥20% minimum)
  - Volume confirmation
  - Dynamic lot sizing based on AI confidence
  - Socket connection to ensemble server
  - CSV fallback for backtesting
- **Entry/Exit**:
  - Entry: Market order when all conditions met
  - SL: 100 pips
  - TP: 300 pips
- **Runs On**: MetaTrader 5
- **Requires**: Heiken_Ashi indicator (MT5 Examples)

#### `Export_15m_HA_Data.mq5` (73 lines)
- **Purpose**: Exports BTCUSD M15 Heiken Ashi data
- **Output**: BTCUSD_15m_HA_data.csv
- **Columns**: Time, HA_Open, HA_High, HA_Low, HA_Close, Volume
- **Default Export**: 10,000 bars (~104 days)
- **Usage**: Attach to BTCUSD M15, run once to export
- **Output Path**: MetaTrader\Files\
- **Runs On**: MetaTrader 5

---

### 🐍 PYTHON SERVER

#### `socket_ai_ha_ensemble.py` (280 lines)
- **Purpose**: Real-time ensemble prediction server
- **Architecture**: 3-model voting (LSTM + RF + XGBoost)
- **Port**: 9091 (localhost)
- **Protocol**: TCP socket
- **Input**: 15 numerical features (price, K-means, momentum)
- **Output**: ±1 prediction (bullish/bearish) + confidence
- **Voting Logic**: Majority voting (2/3 models)
- **Models Loaded**: All 3 at startup
- **Fallback**: Works with 2 models minimum
- **Logging**: socket_ai_ha.log
- **Startup Command**: `python socket_ai_ha_ensemble.py`
- **Requirements**: TensorFlow, scikit-learn, joblib

---

### 📓 TRAINING NOTEBOOKS

#### `train_ha_kmeans_lstm.ipynb` (18 cells)
- **Purpose**: Train LSTM neural network model
- **Input**: BTCUSD_15m_HA_data.csv
- **Architecture**: 2-layer LSTM with dropout
- **Sequence Length**: 5 bars lookback
- **Training**: 80/20 split, 100 epochs max
- **Outputs**:
  - `lstm_ha15m_trend_model.h5` (200 KB, TensorFlow)
  - `scaler_lstm_ha15m.save` (2 KB, StandardScaler)
  - `lstm_ha15m_forecast.csv` (500 KB, predictions)
- **Expected Runtime**: 30 minutes (GPU: 5 min)
- **Expected Accuracy**: 48-54%
- **Key Sections**:
  1. Load libraries & data
  2. Calculate HA metrics
  3. K-means clustering
  4. Pattern detection
  5. Feature engineering
  6. Sequences creation
  7. Train/test split
  8. LSTM model build & training
  9. Evaluation & predictions

#### `train_ha_kmeans_randomforest.ipynb` (17 cells)
- **Purpose**: Train Random Forest classifier
- **Input**: BTCUSD_15m_HA_data.csv
- **Model**: 200 trees, max_depth=20, balanced classes
- **Training**: 80/20 split
- **Outputs**:
  - `randomforest_ha15m_trend_model.pkl` (300 KB, Scikit-learn)
  - `scaler_randomforest_ha15m.save` (2 KB)
  - `randomforest_ha15m_forecast.csv` (500 KB)
- **Expected Runtime**: 10 minutes
- **Expected Accuracy**: 50-56%
- **Key Features**: Feature importance analysis included

#### `train_ha_kmeans_xgboost.ipynb` (18 cells)
- **Purpose**: Train XGBoost classifier
- **Input**: BTCUSD_15m_HA_data.csv
- **Model**: XGBoost with default hyperparameters
- **Training**: 80/20 split, early stopping
- **Outputs**:
  - `xgboost_ha15m_trend_model.pkl` (200 KB, Scikit-learn)
  - `scaler_xgboost_ha15m.save` (2 KB)
  - `xgboost_ha15m_forecast.csv` (500 KB)
- **Expected Runtime**: 5 minutes
- **Expected Accuracy**: 50-55%
- **Key Features**: ROC-AUC evaluation, feature importance

#### `ensemble_ha15m_voting.ipynb` (10 cells)
- **Purpose**: Combine 3 models via majority voting
- **Input Files**:
  - `lstm_ha15m_forecast.csv`
  - `randomforest_ha15m_forecast.csv`
  - `xgboost_ha15m_forecast.csv`
- **Voting Logic**: 2/3 models majority
- **Output**: `ensemble_ha15m_forecast.csv`
- **Output Columns**:
  - Time, LSTM, RandomForest, XGBoost, Ensemble, Confidence
- **Expected Runtime**: 2 minutes
- **Key Metrics**:
  - Individual model agreement percentages
  - Consensus strength analysis
  - Pairwise correlation

---

### 📖 DOCUMENTATION - START HERE

#### `START_HERE.md` (400+ lines)
- **Read This First!**
- **Contents**:
  - What you asked for vs what you got
  - Complete file inventory
  - 3-model ensemble advantage
  - Step-by-step walkthroughs
  - Performance expectations
  - Implementation timeline
  - FAQ section
- **Best For**: New users getting oriented

#### `ENSEMBLE_SYSTEM_OVERVIEW.md` (400+ lines)
- **System architecture explanation**
- **Contents**:
  - Why 3 models matter
  - System architecture diagram
  - How ensemble voting works
  - Voting examples (4 scenarios)
  - File inventory with outputs
  - Complete training sequence
  - Model contribution explanation
  - Quick start commands
  - Next action items
- **Best For**: Understanding the system design

#### `ENSEMBLE_TRAINING_GUIDE.md` (450+ lines)
- **Step-by-step training manual**
- **Contents**:
  - Why ensemble voting works
  - Phase-by-phase training steps
  - File verification checklist
  - Server testing
  - Backtesting workflow
  - Result interpretation
  - Retraining schedule
  - Hyperparameter tuning
  - Advanced weighting strategies
  - Performance expectations
  - Troubleshooting section
- **Best For**: Running the training notebooks

#### `HA_KMeans_Integration_Guide.md` (600+ lines)
- **Complete technical reference**
- **Contents**:
  - System architecture overview
  - Component descriptions (EA, server, models)
  - Parameter reference guide
  - Feature engineering details
  - K-means algorithm explanation
  - Setup procedures (4 phases)
  - Optimization guidelines
  - Risk management specs
  - Troubleshooting (10+ issues)
  - Performance metrics
  - Maintenance schedule
- **Best For**: Deep technical understanding

#### `IMPLEMENTATION_CHECKLIST.md` (300+ lines)
- **Day-by-day setup plan**
- **Contents**:
  - 7-phase implementation plan
  - Pre-requirements checklist
  - Daily task lists
  - Success criteria for each phase
  - Testing procedures
  - Deployment checklist
  - 6+ month monitoring plan
  - Common issues & fixes
  - Performance tracking
- **Best For**: Following structured setup

#### `IMPLEMENTATION_SUMMARY.md` (400+ lines)
- **System overview and architecture**
- **Contents**:
  - Technical overview
  - Component descriptions
  - System flow diagrams
  - K-means clustering details
  - Feature engineering process
  - Expected performance
  - Risk management
  - Maintenance procedures
- **Best For**: Architecture understanding

#### `HA_KMEANS_README.md` (250+ lines)
- **Quick overview and reference**
- **Contents**:
  - 30-second elevator pitch
  - Quick links to all docs
  - What the system does
  - Performance expectations
  - File overview
  - 3-step quick start
  - Key parameters
  - System architecture
  - Troubleshooting table
  - Next steps
- **Best For**: Quick reference

---

### 📊 ORIGINAL SYSTEM FILES (Preserved)

#### `Hybrid_EA.mq5`
- Original EMA/ADX hybrid EA
- Symbol: XAGUSD, Timeframe: H1
- Still available for reference

#### `Export_H1_Data.mq5`
- Original H1 data exporter
- Symbol: XAGUSD

#### `socket_ai.py`
- Original single-model socket server
- For Hybrid_EA.mq5

#### `README.md`
- Original system documentation

#### Backtest Results
- `backtest_adx22/` - ADX parameter backtest results
- `backtest_default_params/` - Default parameter tests
- `backtest_ema6-24/` - EMA tuning tests
- `backtest_iAD_filter/` - Accumulation/Distribution filter tests

#### Model Directories
- `model_lstm/` - Original LSTM training artifacts
- `model_rf/` - Original Random Forest artifacts
- `model_xgboost/` - Original XGBoost artifacts

---

## 🎯 Which Files Do You Need?

### For Backtesting
1. `HA_KMeans_Hybrid_EA.mq5` ← Main EA
2. `Export_15m_HA_Data.mq5` ← Export data
3. `train_ha_kmeans_lstm.ipynb` ← Train LSTM
4. `train_ha_kmeans_randomforest.ipynb` ← Train RF
5. `train_ha_kmeans_xgboost.ipynb` ← Train XGBoost
6. `ensemble_ha15m_voting.ipynb` ← Create ensemble
7. `ENSEMBLE_TRAINING_GUIDE.md` ← Instructions

### For Live Trading
1. `HA_KMeans_Hybrid_EA.mq5` ← Main EA
2. `socket_ai_ha_ensemble.py` ← Ensemble server
3. All 9 trained model files (3 models × 3 files)
4. `ENSEMBLE_SYSTEM_OVERVIEW.md` ← Understanding

### For Understanding the System
1. `START_HERE.md` ← Start here
2. `ENSEMBLE_SYSTEM_OVERVIEW.md` ← Architecture
3. `ENSEMBLE_TRAINING_GUIDE.md` ← Training details
4. `HA_KMeans_Integration_Guide.md` ← Full reference

---

## 📦 Data Files Generated (During Training)

### Input Data
- `BTCUSD_15m_HA_data.csv` ← Created by Export_15m_HA_Data.mq5

### Model Files (After Training)
```
LSTM:
  lstm_ha15m_trend_model.h5        (200 KB)
  scaler_lstm_ha15m.save           (2 KB)

Random Forest:
  randomforest_ha15m_trend_model.pkl (300 KB)
  scaler_randomforest_ha15m.save   (2 KB)

XGBoost:
  xgboost_ha15m_trend_model.pkl    (200 KB)
  scaler_xgboost_ha15m.save        (2 KB)

Forecast CSVs:
  lstm_ha15m_forecast.csv          (500 KB)
  randomforest_ha15m_forecast.csv  (500 KB)
  xgboost_ha15m_forecast.csv       (500 KB)
  ensemble_ha15m_forecast.csv      (500 KB)
```

### Log Files (At Runtime)
- `socket_ai_ha.log` ← Server logs

---

## 🚀 Quick Start File Path

```
1. Read:     START_HERE.md
2. Export:   Export_15m_HA_Data.mq5
3. Train:    train_ha_kmeans_lstm.ipynb
4. Train:    train_ha_kmeans_randomforest.ipynb
5. Train:    train_ha_kmeans_xgboost.ipynb
6. Vote:     ensemble_ha15m_voting.ipynb
7. Backtest: HA_KMeans_Hybrid_EA.mq5 (Strategy Tester)
8. Deploy:   socket_ai_ha_ensemble.py
```

---

## 💾 Disk Space Requirements

| Component | Size | Notes |
|-----------|------|-------|
| Data | 1 MB | BTCUSD_15m_HA_data.csv |
| Models | 1 MB | 3 models × 3 files |
| Forecasts | 2 MB | 4 CSV files |
| Notebooks | 500 KB | 4 .ipynb files |
| Documentation | 2 MB | 6 .md files |
| **Total** | **~7 MB** | Very compact |

---

## 📞 Getting Help

| Issue | File to Check |
|-------|---------------|
| Where do I start? | START_HERE.md |
| How does ensemble work? | ENSEMBLE_SYSTEM_OVERVIEW.md |
| How do I train models? | ENSEMBLE_TRAINING_GUIDE.md |
| What are all the parameters? | HA_KMeans_Integration_Guide.md |
| What's my setup checklist? | IMPLEMENTATION_CHECKLIST.md |
| Want a quick reference? | HA_KMEANS_README.md |
| Training notebook errors? | ENSEMBLE_TRAINING_GUIDE.md troubleshooting |
| System isn't working? | HA_KMeans_Integration_Guide.md troubleshooting |

---

## ✅ File Completeness Checklist

- ✅ Main EA: HA_KMeans_Hybrid_EA.mq5
- ✅ Data Exporter: Export_15m_HA_Data.mq5
- ✅ Ensemble Server: socket_ai_ha_ensemble.py
- ✅ LSTM Notebook: train_ha_kmeans_lstm.ipynb
- ✅ RF Notebook: train_ha_kmeans_randomforest.ipynb
- ✅ XGBoost Notebook: train_ha_kmeans_xgboost.ipynb
- ✅ Ensemble Notebook: ensemble_ha15m_voting.ipynb
- ✅ Overview: START_HERE.md
- ✅ System Overview: ENSEMBLE_SYSTEM_OVERVIEW.md
- ✅ Training Guide: ENSEMBLE_TRAINING_GUIDE.md
- ✅ Integration Guide: HA_KMeans_Integration_Guide.md
- ✅ Checklist: IMPLEMENTATION_CHECKLIST.md
- ✅ Summary: IMPLEMENTATION_SUMMARY.md
- ✅ Quick Ref: HA_KMEANS_README.md
- ✅ Manifest: FILE_MANIFEST.md (this file)

**All 15 files present! ✅**

---

## 🎉 You're Ready!

Everything you need is here:
- 3 executable trading files
- 4 training notebooks
- 7 comprehensive guides
- Complete documentation

**Next: Read START_HERE.md**

---

*Heiken Ashi K-Means 3-Model Ensemble System*
*Complete and Production Ready*
*December 2024*
