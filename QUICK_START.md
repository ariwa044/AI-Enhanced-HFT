# Heiken Ashi K-Means Hybrid System - Quick Reference
## BTCUSD 15-Minute Trading

---

## 🎯 Strategy at a Glance

**Entry Signal**:
- 3+ consecutive Heiken Ashi candles in same direction
- Highest cluster density ≥ 20% (market structure validation)
- Current volume > previous volume
- AI agreement adjusts lot size (1.2× if agree, 0.5× if disagree)

**Exit**:
- Stop Loss: 100 pips
- Take Profit: 300 pips

**Timeframe**: 15 minutes  
**Symbol**: BTCUSD  
**Clusters**: K-means identifies 3-5 price level clusters

---

## 📋 Setup in 4 Steps

### 1️⃣ Export Data (5 min)
```
→ Run: Export_15m_HA_Data.mq5 on BTCUSD M15 chart
→ Creates: BTCUSD_15m_HA_data.csv
```

### 2️⃣ Train Model (10 min)
```
→ Run: train_ha_kmeans_xgboost.ipynb (all cells)
→ Creates: xgboost_ha15m_trend_model.pkl, scaler_ha15m_xgboost.save, trend_forecast_HA15m.csv
```

### 3️⃣ Backtest (varies)
```
→ Copy trend_forecast_HA15m.csv to MetaTrader\Files\
→ Run: HA_KMeans_Hybrid_EA.mq5 in Strategy Tester
→ Review results, optimize parameters
```

### 4️⃣ Live Trade
```
→ Start: python socket_ai.py (for real-time AI)
→ Attach: HA_KMeans_Hybrid_EA.mq5 to live BTCUSD M15 chart
→ Set: UseAIPrediction = true, BaseLotSize per your risk
→ Monitor logs
```

---

## 🔧 Key Parameters

```
ENTRY SIGNALS:
  ConsecutiveBarsUp = 3
  ConsecutiveBarsDown = 3
  
CLUSTERING:
  KMeans_K = 3
  KMeans_TrainBars = 252
  MinClusterDensityPercent = 20.0
  
POSITION SIZING:
  BaseLotSize = 0.01 BTC
  LotMultiplierAgreement = 1.2
  LotMultiplierDisagreement = 0.5
  UseAIPrediction = true
  
RISK:
  StopLoss_Pips = 100
  TakeProfit_Pips = 300
```

---

## 📊 What K-Means Clustering Does

```
Price History (252 bars)
    ↓
K-Means Algorithm (3 clusters)
    ↓
Cluster 0: Center=47250, Density=28%  ← Primary level (TRADE)
Cluster 1: Center=48100, Density=35%  ← Secondary level
Cluster 2: Center=46400, Density=37%  ← Tertiary level
    ↓
IF Cluster[0].Density >= 20%
  → Market well-structured, signal valid
ELSE
  → Market chaotic, skip signal
```

---

## 🤖 AI Agreement Logic

```
LONG ENTRY EXAMPLE:

Signal: 3 HA up bars detected
AI: XGBoost predicts +1 (bullish)

IF Signal & AI AGREE:
  Lot = 0.01 × 1.2 = 0.012 BTC (~$420 at $35k)
  
ELSE IF Signal & AI DISAGREE:
  Lot = 0.01 × 0.5 = 0.005 BTC (~$175 at $35k)
  
ELSE NO AI DATA:
  Lot = 0.01 BTC (base)
```

---

## 🚨 Important Files

| File | Status | Purpose |
|------|--------|---------|
| `HA_KMeans_Hybrid_EA.mq5` | ✓ Ready | Main trading EA |
| `Export_15m_HA_Data.mq5` | ✓ Ready | Data exporter |
| `train_ha_kmeans_xgboost.ipynb` | ✓ Ready | Training notebook |
| `HA_KMeans_Integration_Guide.md` | ✓ Ready | Full documentation |
| `BTCUSD_15m_HA_data.csv` | → Create | Raw data |
| `xgboost_ha15m_trend_model.pkl` | → Create | Trained model |
| `scaler_ha15m_xgboost.save` | → Create | Feature scaler |
| `trend_forecast_HA15m.csv` | → Create | AI predictions |

---

## ⚠️ Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| "HA indicator not found" | Download/create Examples\Heiken_Ashi |
| "CSV file not found" | Copy trend_forecast_HA15m.csv to MT5\Files\ |
| No trades executing | Check cluster density, volume, bar count |
| AI socket error | Start python socket_ai.py before live trading |
| Wrong predictions | Verify CSV format: time,trend,confidence |

---

## 📈 Strategy Strength

✅ **Advantages**:
- Detects strong trending moves (3+ bar confirmation)
- K-means filters weak/choppy markets
- Dynamic lot sizing with AI confidence
- Volume confirmation reduces false signals
- Works on any timeframe (15m optimal)

⚠️ **Limitations**:
- Requires 3 bars = delay in fast markets
- K-means takes time to recalculate
- Crypto volatility → 42-58% win rate typical
- AI predictions only 55-65% accurate

---

## 💰 Risk Management Recommendation

```
Account Size: $10,000
Risk per Trade: 1% ($100)
BTC Price: $35,000

BaseLotSize = 0.01 BTC
Max Loss per Trade = 100 pips × 0.01 = $100 ✓

If AI Agrees:
  Lot = 0.012 BTC → Max Loss = $120 (1.2% risk)

If AI Disagrees:
  Lot = 0.005 BTC → Max Loss = $50 (0.5% risk)
```

**Never Risk More Than 2% Per Trade!**

---

## 🧪 Backtesting Workflow

1. **Export Data**
   ```bash
   # Run Export_15m_HA_Data.mq5
   # Creates BTCUSD_15m_HA_data.csv
   ```

2. **Train Model**
   ```bash
   jupyter notebook train_ha_kmeans_xgboost.ipynb
   # Run all cells → creates trend_forecast_HA15m.csv
   ```

3. **Backtest**
   ```
   MT5 Strategy Tester
   Symbol: BTCUSD, Period: M15
   FromDate: 1 year ago, ToDate: Today
   Expert: HA_KMeans_Hybrid_EA
   ```

4. **Analyze Results**
   - Profit Factor > 1.3 → Good
   - Max Drawdown < 20% → Acceptable
   - Win Rate > 45% → Profitable

5. **Optimize** (optional)
   - Test ConsecutiveBars: 2, 3, 4, 5
   - Test Density Filter: 15%, 20%, 25%, 30%
   - Test Lot Multipliers: 1.0-1.5, 0.2-0.8

---

## 📱 Live Trading Checklist

- [ ] Model training completed with good metrics
- [ ] Backtesting shows positive profit factor
- [ ] Risk per trade ≤ 1-2% of account
- [ ] socket_ai.py running on port 9091
- [ ] EA attached to live BTCUSD M15 chart
- [ ] Logs visible (View → Expert Advisors → Logs)
- [ ] First few trades verified manually
- [ ] Position sizing realistic for account
- [ ] Stop loss and take profit active
- [ ] AutoTrading enabled

---

## 📞 Quick Debug

**Problem**: No signals generated  
**Check**:
1. `print("HA Analysis")` appears in logs every 15 min
2. Cluster density value shown
3. Volume values printing
4. 3+ consecutive HA bars forming

**Problem**: AI always returns 0  
**Check**:
1. CSV has correct header: `time,trend,confidence`
2. Times match (hourly, not minutely)
3. Data file in MT5\Files\ folder
4. Use socket_ai.py for live (not CSV)

**Problem**: Trades too small/large  
**Check**:
1. BaseLotSize appropriate for account
2. LotMultiplier values (0.5-1.2 typical)
3. AI agreement logic (check logs)

---

## 🎓 Learning Resources

- K-Means Clustering: [Scikit-learn docs](https://scikit-learn.org/stable/modules/clustering.html#k-means)
- Heiken Ashi: TradingView documentation
- XGBoost: [Official guide](https://xgboost.readthedocs.io/)
- MQL5: [MetaTrader 5 documentation](https://www.mql5.com/)

---

## 📅 Next Steps

1. **Today**: Set up data export & train model
2. **This Week**: Backtest with multiple parameters
3. **Next Week**: Paper trade (demo account)
4. **Month 2**: Validate on fresh data
5. **Month 3+**: Live trade with small size

---

**Ready to start? Run `Export_15m_HA_Data.mq5` now!** 🚀
