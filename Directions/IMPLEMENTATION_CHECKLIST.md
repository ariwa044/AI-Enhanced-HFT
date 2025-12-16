# Heiken Ashi K-Means Hybrid System - Implementation Checklist

## 📋 Pre-Implementation Checklist

### Requirements Verification
- [ ] MetaTrader 5 installed on system
- [ ] Python 3.8+ installed
- [ ] Git/version control available (optional)
- [ ] Text editor or IDE available
- [ ] 5+ GB disk space free
- [ ] Network connection available
- [ ] Administrator access (for socket port binding)

### Python Libraries
```bash
pip install pandas numpy scikit-learn xgboost joblib matplotlib seaborn
```
- [ ] pandas installed
- [ ] numpy installed  
- [ ] scikit-learn installed
- [ ] xgboost installed
- [ ] joblib installed
- [ ] matplotlib installed (optional)

### MT5 Verification
- [ ] MT5 terminal running
- [ ] At least one BTCUSD quote available
- [ ] Examples folder exists in MQL5 directory
- [ ] Heiken Ashi indicator available (or can be downloaded)
- [ ] MetaQuotes Community accessible

---

## 🚀 Phase 1: Data Export & Preparation (Day 1)

### Step 1.1: Verify HA Indicator
- [ ] MT5 → Tools → Indicators → Search "Heiken Ashi"
- [ ] If not found: Download from MetaQuotes Community
- [ ] If found: Note the path (usually Examples\Heiken_Ashi)
- [ ] Test on any chart (should show colored candles)

### Step 1.2: Export Historical Data
- [ ] Open MT5 terminal
- [ ] Open BTCUSD chart (15-minute timeframe)
- [ ] Create new Expert Advisor → Paste `Export_15m_HA_Data.mq5` code
- [ ] Compile (F7 key)
- [ ] Right-click chart → Expert Advisors → Run
- [ ] Wait for completion message
- [ ] Check `MetaTrader\Files\BTCUSD_15m_HA_data.csv` exists
- [ ] Verify file size > 500 KB (should have ~10,000 rows)
- [ ] Open CSV in spreadsheet to verify data:
  - [ ] Time column: Timestamps present
  - [ ] HA_Open, HA_High, HA_Low, HA_Close: All numbers
  - [ ] Volume: All positive numbers

### Step 1.3: Prepare Working Directory
- [ ] Create folder: `C:\AI_Trading\` (or your preferred location)
- [ ] Copy `BTCUSD_15m_HA_data.csv` to this folder
- [ ] Copy `train_ha_kmeans_xgboost.ipynb` to this folder
- [ ] Verify both files in same directory

---

## 🧠 Phase 2: Model Training (Day 2)

### Step 2.1: Launch Jupyter Notebook
```bash
cd C:\AI_Trading\
jupyter notebook
```
- [ ] Jupyter launches in browser
- [ ] Open `train_ha_kmeans_xgboost.ipynb`
- [ ] Verify notebook loads without errors

### Step 2.2: Run Each Section
- [ ] **Section 1**: Import libraries → ✓ All imported
- [ ] **Section 2**: Load data → ✓ Shows data shape & first 5 rows
- [ ] **Section 3**: HA properties → ✓ New columns created
- [ ] **Section 4**: K-means → ✓ Shows cluster analysis
- [ ] **Section 5**: Consecutive bars → ✓ Shows signal counts
- [ ] **Section 6**: Target labels → ✓ Shows trend distribution
- [ ] **Section 7**: Feature engineering → ✓ Shows 15+ features
- [ ] **Section 8**: Train-test split → ✓ Shows sample counts
- [ ] **Section 9**: Train model → ✓ XGBoost trains
- [ ] **Section 10**: Evaluate → ✓ Shows metrics (>50% accuracy is good)
- [ ] **Section 11**: Feature importance → ✓ Shows top features
- [ ] **Section 12**: Generate predictions → ✓ Creates forecast
- [ ] **Section 13**: Save files → ✓ Confirms saved

### Step 2.3: Verify Output Files
Check working directory for:
- [ ] `xgboost_ha15m_trend_model.pkl` (> 100 KB)
- [ ] `scaler_ha15m_xgboost.save` (> 1 KB)
- [ ] `trend_forecast_HA15m.csv` (> 100 KB)
- [ ] `training_info.txt` (contains metrics)

### Step 2.4: Review Metrics
Open `training_info.txt`:
- [ ] Accuracy > 50% (acceptable)
- [ ] Precision > 45% (good)
- [ ] F1-Score > 0.45 (good)
- [ ] If below these: adjust parameters and retrain

---

## 📊 Phase 3: Backtesting Setup (Day 3)

### Step 3.1: Prepare EA Files
- [ ] Copy `HA_KMeans_Hybrid_EA.mq5` to `MetaTrader\MQL5\Experts\`
- [ ] Copy `trend_forecast_HA15m.csv` to `MetaTrader\Files\`
- [ ] In MT5: File → Open Data Folder → Files → Verify CSV is there

### Step 3.2: Compile EA
- [ ] MT5 → Tools → New Expert Advisor (or Edit)
- [ ] Copy `HA_KMeans_Hybrid_EA.mq5` code
- [ ] Click Compile (F7)
- [ ] Verify no errors (warnings are okay)
- [ ] Check bottom of editor: "Compiled successfully"

### Step 3.3: Setup Backtest
- [ ] MT5 → View → Strategy Tester (or Ctrl+R)
- [ ] Settings:
  - [ ] Expert Advisor: HA_KMeans_Hybrid_EA
  - [ ] Symbol: BTCUSD
  - [ ] Timeframe: M15
  - [ ] Model: Every tick
  - [ ] FromDate: 1 year ago (2023-12-11)
  - [ ] ToDate: Today (2024-12-11)
  - [ ] Initial Deposit: 10000 USD
  - [ ] Leverage: 100:1

### Step 3.4: Run Backtest
- [ ] Click "Start" button
- [ ] Wait for completion (5-30 minutes)
- [ ] Status bar shows: "0 errors, X trades"
- [ ] Check "Report" tab for results

### Step 3.5: Analyze Results
- [ ] Profit/Loss: Positive (hopefully!)
- [ ] Total Trades: 50-200 (normal range)
- [ ] Win Rate: 40-60%
- [ ] Profit Factor: > 1.2 (acceptable)
- [ ] Max Drawdown: < 25% (good)
- [ ] Sharpe Ratio: > 0.5 (okay)

If results are poor:
- [ ] Check "Journal" tab for errors
- [ ] Verify CSV file format
- [ ] Adjust `MinClusterDensityPercent` (try 15 or 25)
- [ ] Adjust `ConsecutiveBarsUp/Down` (try 2 or 4)
- [ ] Retrain model with different parameters

### Step 3.6: Save Backtest Report
- [ ] Right-click report → Export as HTML
- [ ] Save: `backtest_report_BTCUSD_15m_vX.html`
- [ ] Keep for records/comparison

---

## 🎯 Phase 4: Parameter Optimization (Day 4-5)

### Step 4.1: Test Parameter Combinations
Create test matrix:

| ConsecutiveBars | Density | Result |
|-----------------|---------|--------|
| 2 | 15 | ? |
| 2 | 20 | ? |
| 3 | 15 | ? |
| 3 | 20 | ? |
| 3 | 25 | ? |
| 4 | 20 | ? |
| 4 | 25 | ? |

- [ ] Run each combination
- [ ] Record profit factor for each
- [ ] Note best performing parameters

### Step 4.2: Fine-tune Winner
- [ ] Select best configuration from matrix
- [ ] Test variations around it
- [ ] Example: If (3, 20) wins, test (3, 18), (3, 22)
- [ ] Record final optimized parameters

### Step 4.3: Walk-Forward Test
- [ ] Split backtest data in half
- [ ] Optimize on first half
- [ ] Test on second half
- [ ] Verify profit factor > 1.2 on out-of-sample data
- [ ] If poor: may be overfitted

- [ ] Optimized parameters documented
- [ ] Out-of-sample test passed

---

## 🚀 Phase 5: Live Trading Preparation (Day 6)

### Step 5.1: Risk Management Setup
Account Size: $10,000  
- [ ] Max Risk Per Trade: 1-2% ($100-200)
- [ ] At current BTC price ($35k): 
  - [ ] BaseLotSize = 0.01 BTC = $350
  - [ ] Max loss per trade = 100 pips = $100 ✓
- [ ] Adjust BaseLotSize if needed

### Step 5.2: Prepare EA for Live
- [ ] Open `HA_KMeans_Hybrid_EA.mq5` in editor
- [ ] Change parameters to optimized values:
  - [ ] ConsecutiveBarsUp = (your value)
  - [ ] ConsecutiveBarsDown = (your value)
  - [ ] MinClusterDensityPercent = (your value)
- [ ] Set `BaseLotSize` = (your calculated value)
- [ ] Set `UseAIPrediction = true`
- [ ] Verify `AISocketPort = 9091`
- [ ] Compile (F7)

### Step 5.3: Start AI Server
- [ ] Open command prompt
- [ ] Navigate to folder with model files:
  ```bash
  cd C:\AI_Trading\
  ```
- [ ] Start server:
  ```bash
  python socket_ai_ha.py
  ```
- [ ] Verify output:
  ```
  ✓ Scaler loaded
  ✓ Model loaded
  ✓ Server listening on 127.0.0.1:9091
  Waiting for predictions...
  ```
- [ ] Keep this window open during trading

### Step 5.4: Attach EA to Live Chart
- [ ] Open BTCUSD 15-minute chart (LIVE, not backtest)
- [ ] Right-click → Expert Advisors → Attach Expert Advisor
- [ ] Select HA_KMeans_Hybrid_EA
- [ ] Click OK
- [ ] Verify in chart title: "HA_KMeans_Hybrid_EA (BTCUSD,M15)"

### Step 5.5: Verify EA Running
- [ ] Check Expert Advisors panel (View → Expert Advisors)
- [ ] Status should show "HA_KMeans_Hybrid_EA is working"
- [ ] Check logs (View → Logs)
- [ ] Should see:
  - [ ] "HA K-Means Hybrid EA Initialized"
  - [ ] "HA Analysis..." every 15 minutes
  - [ ] Cluster updates with density values

### Step 5.6: Monitor First Bar
- [ ] Wait for next 15m bar close
- [ ] Check logs for:
  - [ ] HA consecutive bar count
  - [ ] Cluster analysis output
  - [ ] Volume confirmation
  - [ ] AI prediction (if any)
- [ ] Do NOT expect trade on first bar
- [ ] Just verify system is operational

---

## ✅ Phase 6: First 10 Trades (Week 1)

### Trade Execution Checklist
For each trade, verify:
- [ ] Entry logged in Journal
- [ ] Position visible in Positions tab
- [ ] Entry price matches prediction logic
- [ ] Lot size correct (base, agreement, or disagreement)
- [ ] Stop loss set 100 pips away
- [ ] Take profit set 300 pips away
- [ ] AI prediction in logs (socket connected)

### Trade Monitoring
- [ ] After each trade, record:
  - [ ] Entry time & price
  - [ ] AI prediction (if used)
  - [ ] Exit type (SL, TP, manual)
  - [ ] Exit time & price
  - [ ] P&L
  - [ ] Notes on market conditions

### Trade Journal Template
```
Date        Time    Signal  AI    Lot     Entry   Exit    P&L     Notes
12/11/24    10:30   LONG    +1    0.012   35450   35750   $300    Good consolidation
12/11/24    14:45   SHORT   -1    0.012   35200   34900   $300    Strong volume
...
```

- [ ] First 10 trades executed successfully
- [ ] P&L positive or minor negative (normal for crypto)
- [ ] No system errors or crashes
- [ ] AI predictions working correctly

---

## 📈 Phase 7: Ongoing Monitoring (Week 2+)

### Daily Checks
- [ ] [ ] Server running: `python socket_ai_ha.py` active
- [ ] [ ] EA active: Status shows "working"
- [ ] [ ] Logs clear: No errors in Expert Advisors tab
- [ ] [ ] Cluster density reasonable (15-40%)

### Weekly Reviews
- [ ] Review all trades from week
- [ ] Calculate win rate, profit factor
- [ ] Check if results match backtest expectations
- [ ] Note any market regime changes
- [ ] Adjust parameters if needed

### Monthly Optimization
- [ ] Retrain model with latest data
- [ ] Test new parameter combinations
- [ ] Compare live performance vs backtest
- [ ] Adjust risk per trade if needed
- [ ] Document any changes

---

## 🔧 Troubleshooting Checklist

### If No Signals Generated
- [ ] Check Expert Advisors logs for "HA Analysis" every 15 min
- [ ] Verify chart is LIVE (not historical/backtest)
- [ ] Increase `MinClusterDensityPercent` to 15 (was 20)
- [ ] Check if 3+ consecutive bars are forming
- [ ] Verify volume > previous volume
- [ ] Check cluster density (should show in logs)

### If AI Connection Fails
- [ ] Verify server running: `python socket_ai_ha.py`
- [ ] Check firewall allows port 9091
- [ ] Verify scaler file exists: `scaler_ha15m_xgboost.save`
- [ ] Verify model file exists: `xgboost_ha15m_trend_model.pkl`
- [ ] Check server logs for errors
- [ ] Restart server if needed

### If Backtest Shows Losses
- [ ] Check CSV file dates match backtest period
- [ ] Verify cluster density not too high (> 40% might be overfitted)
- [ ] Try longer training period (more data)
- [ ] Adjust consecutive bars threshold
- [ ] Reduce lot size
- [ ] Test different market periods

---

## ✨ Success Criteria

### Backtesting Phase Success
- [ ] Positive profit factor (> 1.2)
- [ ] Win rate > 45%
- [ ] Max drawdown < 25%
- [ ] Sharpe ratio > 0.5

### Live Trading Phase Success  
- [ ] First 10 trades without errors
- [ ] P&L positive or near break-even
- [ ] AI predictions working (logs show ±1 values)
- [ ] No crashes or system errors
- [ ] Cluster updates every 15 minutes

### Long-term Success
- [ ] Month 1: Verified system stability
- [ ] Month 2: Profit factor > 1.3
- [ ] Month 3: Confident in parameter settings
- [ ] Month 6: Consistent profitability

---

## 📊 Final Checklist

### All Files Created ✅
- [ ] HA_KMeans_Hybrid_EA.mq5
- [ ] Export_15m_HA_Data.mq5
- [ ] train_ha_kmeans_xgboost.ipynb
- [ ] socket_ai_ha.py
- [ ] HA_KMeans_Integration_Guide.md
- [ ] QUICK_START.md
- [ ] IMPLEMENTATION_SUMMARY.md

### All Phases Completed
- [ ] Phase 1: Data Export (Day 1)
- [ ] Phase 2: Model Training (Day 2)
- [ ] Phase 3: Backtesting (Day 3)
- [ ] Phase 4: Optimization (Days 4-5)
- [ ] Phase 5: Live Prep (Day 6)
- [ ] Phase 6: First Trades (Week 1)
- [ ] Phase 7: Monitoring (Week 2+)

### Ready for Production ✅
- [ ] All tests passed
- [ ] Parameters optimized
- [ ] Risk management in place
- [ ] Monitoring procedure established
- [ ] Backup of all model files
- [ ] Trading journal started

---

## 🎉 Completion Status

When all checkboxes are complete, your Heiken Ashi K-Means hybrid system is:
- ✅ Fully implemented
- ✅ Thoroughly tested
- ✅ Production ready
- ✅ Continuously monitored

**Expected timeline**: 6-7 days from start to live trading

**Good luck trading!** 📈
