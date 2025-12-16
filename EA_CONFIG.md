# Backtest EA Configuration - ENSEMBLE VOTING ENABLED

## Critical Settings
- **UseEnsembleVoting**: TRUE ✓ (ENABLED - System requires ensemble voting for trades)
- **EnsembleFileName**: ensemble_ha15m_forecast.csv (95,765 rows of LSTM/RF/XGBoost predictions)
- **UseKMeansGate**: FALSE (K-means gate disabled for initial testing)
- **UsePythonSizing**: TRUE (Lot sizing matches Python backtest exactly)

## Pattern Detection
- **ConsecutiveBarsUp**: 3 bars (closes must be consecutively higher on HA M15)
- **ConsecutiveBarsDown**: 3 bars (closes must be consecutively lower on HA M15)
- Timeframe: M15 (15-minute candles on Heiken Ashi)

## Ensemble Voting Logic
For a LONG trade to execute:
1. HA M15 must show 3+ consecutive up closes ✓
2. Ensemble CSV must have matching row for the previous completed bar time ✓
3. Ensemble signal must be +1 (BUY) ✓
4. K-means gate (if enabled): market_good_condition must be TRUE

For a SHORT trade to execute:
1. HA M15 must show 3+ consecutive down closes ✓
2. Ensemble CSV must have matching row for the previous completed bar time ✓
3. Ensemble signal must be -1 (SELL) ✓
4. K-means gate (if enabled): market_good_condition must be TRUE

## Ensemble CSV Format
```
Time,LSTM,RandomForest,XGBoost,Ensemble,Confidence
2023-01-01 00:00:00,0.0,-1,-1.0,-1,66.66666666666666
2023-01-01 00:15:00,0.0,-1,-1.0,-1,66.66666666666666
...
```
- Signals: 1 (BUY), 0 (NEUTRAL), -1 (SELL)
- Confidence: percentage (0-100, shown as decimal)

## Risk & Lot Sizing
- **BaseLotSize**: 0.01
- **MinLotSize**: 0.01
- **MaxLotSize**: 1.2
- **AccountBalance**: 10,000 (for Python backtest parity)
- **RiskPercent**: 2% per trade
- **StopLoss**: 100 pips
- **TakeProfit**: 300 pips
- **PipMultiplier**: 0.0001 (Python backtest scaling)

## Debug Logging
All of the following are logged to Experts/Journal:
- HA bar closes and consecutive counter (CountConsecutiveBars)
- Pattern detection status (CheckTradingSignals)
- Ensemble CSV matching success/failure with signal details
- Lot size calculation breakdown
- Trade order submission attempts with error codes
- Position blocking checks

## Required Files
- **EA**: backtest_HA_Ensemble_EA.mq5 (compiled .ex5 in MQL5\Experts)
- **Ensemble CSV**: MQL5\Files\ensemble_ha15m_forecast.csv (95,765 rows)
- **HA Indicator**: Examples\Heiken_Ashi (standard MT5)

## Troubleshooting Checklist
- [ ] CSV file is in MQL5\Files directory (not Experts folder)
- [ ] CSV header matches: Time,LSTM,RandomForest,XGBoost,Ensemble,Confidence
- [ ] Backtest symbol is set correctly in EA parameters
- [ ] Timeframe is M15 in Strategy Tester
- [ ] Backtest date range has matching CSV data (2023-01-01 onwards)
- [ ] Check Experts/Journal for "SUCCESS:" messages indicating trades attempted

---
Last updated: EA enabled with ENSEMBLE VOTING = TRUE
