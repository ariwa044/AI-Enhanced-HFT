# Heiken Ashi K-Means Hybrid Trading System - Integration Guide
## BTCUSD 15-Minute Strategy

---

## 📋 System Overview

This hybrid system combines three powerful components:
1. **Heiken Ashi 15m consecutive bar strategy** - Entry signal generation
2. **K-means clustering** - Market condition validation and support/resistance identification  
3. **AI/ML predictions** - Dynamic lot sizing and trade confirmation

### Why This Works
- **HA Consecutive Bars**: Detects sustained price movements (3+ bars in one direction)
- **K-Means Clustering**: Identifies price level clusters (support/resistance zones) and validates market structure quality
- **Volume Filter**: Ensures trades occur with sufficient liquidity
- **AI Agreement**: Sizes positions based on alignment between technical and ML signals

---

## 🗂️ Files Overview

### Core Trading Files

| File | Purpose | Notes |
|------|---------|-------|
| `HA_KMeans_Hybrid_EA.mq5` | Main MetaTrader EA | Live/backtest trading |
| `Export_15m_HA_Data.mq5` | Data export utility | Generate training data |
| `train_ha_kmeans_xgboost.ipynb` | Model training notebook | Creates ML models |
| `HA_KMeans_Integration_Guide.md` | This file | Setup & troubleshooting |

### Generated During Training

| File | Purpose |
|------|---------|
| `BTCUSD_15m_HA_data.csv` | Raw 15m HA data from MT5 |
| `xgboost_ha15m_trend_model.pkl` | Trained XGBoost model |
| `scaler_ha15m_xgboost.save` | Feature scaler for preprocessing |
| `trend_forecast_HA15m.csv` | AI predictions (for backtesting) |

---

## ⚙️ Setup Procedure

### **Step 1: Export Historical Data**

**Goal**: Get 10,000 bars of BTCUSD 15m Heiken Ashi data

**Instructions**:
1. Open MetaTrader 5
2. Open BTCUSD chart (15-minute timeframe)
3. Right-click → Expert Advisors → Edit (or paste `Export_15m_HA_Data.mq5`)
4. Compile & run on the chart
5. File created: `BTCUSD_15m_HA_data.csv` (in `MetaTrader\Files\` folder)

**Expected**: ~10,000 rows with columns: Time, HA_Open, HA_High, HA_Low, HA_Close, Volume

---

### **Step 2: Train Machine Learning Model**

**Goal**: Create prediction model with K-means features

**Instructions**:
1. Ensure `BTCUSD_15m_HA_data.csv` is in your working directory
2. Open Jupyter Notebook: `train_ha_kmeans_xgboost.ipynb`
3. Run all cells sequentially
4. Monitor outputs for training progress

**What Happens**:
- Loads 15m HA data
- Calculates K-means clusters (default: 3 clusters)
- Detects consecutive HA bars patterns
- Engineers 15+ features
- Trains XGBoost classifier
- Generates predictions CSV

**Files Created**:
- `xgboost_ha15m_trend_model.pkl` ← Model (keep safe!)
- `scaler_ha15m_xgboost.save` ← Scaler
- `trend_forecast_HA15m.csv` ← Predictions
- `training_info.txt` ← Performance metrics

**Expected Results**:
- Accuracy: 50-65% (crypto is challenging!)
- Precision: 45-60%
- ROC-AUC: 0.55-0.70

---

### **Step 3: Backtest Strategy**

**Goal**: Validate strategy performance on historical data

**Instructions**:
1. Copy `trend_forecast_HA15m.csv` to MetaTrader's `\Files\` folder
2. Attach `HA_KMeans_Hybrid_EA.mq5` to BTCUSD M15 chart
3. Open Strategy Tester (Ctrl+R in MT5)
4. **Settings**:
   - Expert Advisor: HA_KMeans_Hybrid_EA
   - Symbol: BTCUSD
   - Period: M15
   - FromDate: 1 year back
   - ToDate: Today
5. Click "Start"

**Key Parameters to Test**:
```
ConsecutiveBarsUp = 3         (3-5 bars)
ConsecutiveBarsDown = 3       (3-5 bars)
KMeans_K = 3                  (3-5 clusters)
MinClusterDensityPercent = 20  (15-30%)
UseAIPrediction = true        (enable/disable)
```

---

### **Step 4: Live Trading**

**Goal**: Deploy on live BTCUSD chart

**Prerequisites**:
- Model files ready: `xgboost_ha15m_trend_model.pkl`, `scaler_ha15m_xgboost.save`
- `socket_ai.py` running (for real-time predictions)
- Account with proper risk management

**Instructions**:
1. Start AI service:
   ```bash
   python socket_ai.py
   # Output: Model Server listening on 127.0.0.1:9091
   ```

2. In MetaTrader:
   - Attach `HA_KMeans_Hybrid_EA.mq5` to BTCUSD M15 live chart
   - Set `UseAIPrediction = true`
   - Adjust `BaseLotSize` (default 0.01 = 100 USD per BTC)
   - Enable AutoTrading

3. Monitor Expert Advisor logs for:
   - K-means cluster updates
   - Signal detection
   - AI prediction confirmation
   - Trade execution logs

---

## 🎯 Trading Logic

### Entry Conditions

**LONG Trade Triggered When**:
1. ✓ 3+ consecutive HA bars with closes rising (up_counter ≥ 3)
2. ✓ Highest cluster density ≥ 20% (good market structure)
3. ✓ Current bar volume > previous bar volume
4. ✓ No existing long position
5. → Lot size: BaseLotSize × (AI agreement ? 1.2 : 0.5)

**SHORT Trade Triggered When**:
1. ✓ 3+ consecutive HA bars with closes falling (dns_counter ≥ 3)
2. ✓ Highest cluster density ≥ 20% (good market structure)
3. ✓ Current bar volume > previous bar volume
4. ✓ No existing short position
5. → Lot size: BaseLotSize × (AI agreement ? 1.2 : 0.5)

### Exit Strategy

**Automatic Exits**:
- Stop Loss: 100 pips
- Take Profit: 300 pips
- Manual position reversal when opposite signal triggers

---

## 📊 K-Means Clustering Explained

### What It Does
- Identifies 3 price clusters from last 252 bars
- Cluster 0 (highest density) = primary support/resistance level
- Calculates density % to assess market consolidation

### Cluster Density Quality Levels

| Density | Market Condition | Action |
|---------|-----------------|--------|
| < 15% | Choppy/scattered | No trade signal validity |
| 15-25% | Mixed | Low confidence |
| 25-35% | Good | Normal trading |
| > 35% | Strong consolidation | High confidence |

**Filter Logic**: Only execute trades when Cluster[0].density ≥ 20%

---

## 🤖 AI Agreement Logic

### When AI Agrees With Technical Signal

```
Technical Says: BUY (3 HA up bars)
AI Predicts: +1 (bullish)
→ Lot Size = 0.01 × 1.2 = 0.012 BTC (~$400 at $35k)
```

### When AI Disagrees

```
Technical Says: BUY (3 HA up bars)
AI Predicts: -1 (bearish)
→ Lot Size = 0.01 × 0.5 = 0.005 BTC (~$175 at $35k)
```

### No AI Data Available

```
→ Lot Size = 0.01 BTC (base lot)
```

---

## ⚙️ Key Parameters

### Entry/Exit
```
ConsecutiveBarsUp = 3           # HA bars for long signal
ConsecutiveBarsDown = 3         # HA bars for short signal
StopLoss_Pips = 100             # Stop loss in pips
TakeProfit_Pips = 300           # Take profit in pips
```

### Clustering
```
KMeans_K = 3                    # Number of clusters (3-5)
KMeans_TrainBars = 252          # Bars for cluster calculation
MinClusterDensityPercent = 20.0  # Min density threshold
```

### Position Sizing
```
BaseLotSize = 0.01              # Base BTC lot (adjust per risk)
LotMultiplierAgreement = 1.2     # Multiplier when AI agrees
LotMultiplierDisagreement = 0.5  # Multiplier when AI disagrees
UseAIPrediction = true          # Enable/disable AI
```

---

## 📈 Optimization Guidelines

### For Backtesting
- Increase `KMeans_TrainBars` to 500+ for more stable clusters
- Lower `MinClusterDensityPercent` to 15 for more signal frequency
- Test `ConsecutiveBars` range: 2-4

### For Live Trading
- Use smaller `ConsecutiveBars` (2-3) for faster entries
- Keep `KMeans_K = 3` for simpler interpretation
- Monitor cluster shifts during market regime changes

### Parameter Sensitivity
```
↑ ConsecutiveBars → Fewer trades, higher quality entries
↓ MinDensity → More trades, may include false signals
↑ TakeProfit → Larger wins but harder to achieve
↓ StopLoss → Risk less per trade but tighter exits
```

---

## 🐛 Troubleshooting

### Error: "Failed to create Heiken Ashi indicator handle"
**Cause**: HA indicator not found in MT5  
**Solution**:
1. Ensure `Examples\Heiken_Ashi` exists in MT5 indicators folder
2. If missing, download from MT5 Community or create custom HA indicator
3. Place in: `MetaTrader\MQL5\Indicators\Examples\`

### Error: "CSV file not found"
**Cause**: Backtesting CSV not in MT5 Files folder  
**Solution**:
1. Check: `MetaTrader\Files\trend_forecast_HA15m.csv` exists
2. File must have columns: `time,trend,confidence`
3. Format: time must be ISO format (2024-01-15 10:30:00)

### No Trades Executing
**Possible Causes**:
1. Cluster density too low (increase data range or lower threshold)
2. Volume filter too strict (check actual volumes)
3. AI predictions all zeros (check CSV formatting)
4. No new bars generated (check chart timeframe is M15)

**Debugging Steps**:
1. Enable Expert Advisor logging (View → Logs)
2. Check print statements for signal reasons
3. Verify cluster density output each bar
4. Confirm volume > previous volume condition

---

## 💡 Strategy Variations

### Conservative (Lower Risk)
```
ConsecutiveBarsUp = 4
MinClusterDensityPercent = 30
LotMultiplierAgreement = 1.0
LotMultiplierDisagreement = 0.3
```

### Aggressive (Higher Reward)
```
ConsecutiveBarsUp = 2
MinClusterDensityPercent = 15
LotMultiplierAgreement = 1.5
LotMultiplierDisagreement = 0.8
```

### AI-Dominant (Trust Predictions)
```
UseAIPrediction = true
LotMultiplierAgreement = 2.0      # Double size when AI agrees
LotMultiplierDisagreement = 0.1   # Minimal size when disagreed
```

---

## 📊 Expected Performance (BTCUSD)

Based on typical backtests:

| Metric | Range |
|--------|-------|
| Win Rate | 42-58% |
| Profit Factor | 1.2-1.8 |
| Sharpe Ratio | 0.5-1.5 |
| Max Drawdown | 8-25% |
| Avg Win | 200-400 pips |
| Avg Loss | 100 pips |

**Note**: Crypto markets are highly variable. Always backtest on your symbol/period combination.

---

## 🚀 Quick Start Checklist

- [ ] Export BTCUSD 15m data using `Export_15m_HA_Data.mq5`
- [ ] Train model using `train_ha_kmeans_xgboost.ipynb`
- [ ] Backtest with Strategy Tester
- [ ] Optimize key parameters
- [ ] Start live trading with small lot sizes
- [ ] Monitor and adjust parameters monthly
- [ ] Keep trading journal

---

## 📞 Support

For issues:
1. Check Expert Advisor logs (View → Logs in MT5)
2. Verify all CSV files in correct folder
3. Ensure Python socket service running (port 9091)
4. Confirm Heiken Ashi indicator available
5. Test on data first before live trading

---

**Last Updated**: December 2024  
**Version**: 1.0  
**Strategy**: Heiken Ashi K-Means Hybrid with AI  
**Symbol**: BTCUSD  
**Timeframe**: 15 Minutes
