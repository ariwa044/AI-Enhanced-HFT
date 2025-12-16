//+------------------------------------------------------------------+
//| Backtest Heiken Ashi + Ensemble EA for Strategy Tester (MQL5)    |
//| Minimal backtest EA that mirrors the Python backtest rules:      |
//| - Heiken Ashi 3+ consecutive bars pattern                        |
//| - Volume confirmation (current > previous)                       |
//| - Ensemble CSV lookup by bar-time (previous completed bar)       |
//| - Requires ensemble vote when UseEnsembleVoting=true             |
//+------------------------------------------------------------------+
#property copyright "AI-Enhanced Trading"
#property version   "1.00"
#property strict
#include <Trade\Trade.mqh>
CTrade trade;

// Inputs
input int    ConsecutiveBarsUp    = 3;         // HA Consecutive Up Bars for Long
input int    ConsecutiveBarsDown  = 3;         // HA Consecutive Down Bars for Short
input ENUM_TIMEFRAMES HA_Timeframe = PERIOD_M15; // Heiken Ashi timeframe
input double StopLoss_Pips        = 100.0;     // SL in pips
input double TakeProfit_Pips      = 300.0;     // TP in pips
input double BaseLotSize          = 0.01;      // Base lot size
input bool   UseEnsembleVoting    = true;      // Require ensemble vote (ENABLED - critical for system)
input string EnsembleFileName     = "ensemble_ha15m_forecast.csv"; // CSV in MQL5\Files
input int    Magic                = 123456;
input string TradeComment         = "HA_Ensemble_Backtest";

// K-Means / Market regime (approximated) inputs
input bool   UseKMeansGate        = false;     // Use K-means density gate (DISABLED for testing)
input int    KMeans_K             = 3;         // clusters (unused exactly, kept for parity)
input int    KMeans_TrainBars     = 252;       // lookback for regime calculation
input double MinClusterDensityPercent = 10.0;  // minimum density percent to allow trades (lowered for limited backtest data)

// Risk / lot sizing inputs (mirror Python backtest)
input double MinLotSize           = 0.01;      // minimum lot size (match Python backtest)
input double MaxLotSize           = 1.2;       // maximum lot size
input double AccountBalance       = 10000.0;   // starting account balance used for lot calc
input double RiskPercent          = 2.0;       // percent risk per trade

// If ensemble CSV is missing, allow trades anyway (useful for Strategy Tester runs)
input bool   AllowTradesWhenEnsembleMissing = true;
// Use Python backtest sizing & pip scaling for parity
input bool   UsePythonSizing       = true;     // when true, use Python lot calc and pip multiplier
input double PipMultiplier         = 0.0001;   // pip multiplier used in Python backtest

// Globals
int ha_handle = INVALID_HANDLE;
double ha_close[];
int ups_counter = 0;
int dns_counter = 0;
datetime last_bar_time = 0;
bool market_good_condition = true;

struct EnsemblePrediction {
  int lstm_signal;
  int rf_signal;
  int xgb_signal;
  int ensemble_signal;
  double confidence;
  datetime time;
};
EnsemblePrediction current_ensemble;

// Trade logging
int trade_log_file = INVALID_HANDLE;
int total_trades_logged = 0;
string trade_log_filename = "backtest_trades_ea.csv";

// K-Means cluster struct
struct KMeansCluster
{
  double center;
  double std_dev;
  double density;
  int count;
};

KMeansCluster clusters[];
double price_history[];

//+------------------------------------------------------------------+
int OnInit()
{
  // create Heiken Ashi indicator (standard example name)
  ha_handle = iCustom(_Symbol, HA_Timeframe, "Examples\\Heiken_Ashi");
  if(ha_handle == INVALID_HANDLE)
  {
    Print("Failed to create Heiken Ashi indicator handle");
    return INIT_FAILED;
  }

  ArraySetAsSeries(ha_close, true);

  // initialize price history for K-means
  ArrayResize(price_history, KMeans_TrainBars);
  ArrayInitialize(price_history, 0.0);
  ArrayResize(clusters, KMeans_K);

  // initialize ensemble
  current_ensemble.lstm_signal = 0;
  current_ensemble.rf_signal = 0;
  current_ensemble.xgb_signal = 0;
  current_ensemble.ensemble_signal = 0;
  current_ensemble.confidence = 0.0;
  current_ensemble.time = 0;

  // Initialize trade log CSV file
  trade_log_file = FileOpen(trade_log_filename, FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_COMMON);
  if(trade_log_file != INVALID_HANDLE)
  {
    // Write header
    string header = "entry_idx,entry_price,entry_time,entry_bar_time,direction,signal,lot_size,stop_loss,take_profit,confidence,exit_idx,exit_price,exit_type,exit_time,pnl,days_open,bars_open";
    FileWriteString(trade_log_file, header + "\n");
    Print("Trade log CSV initialized: ", trade_log_filename);
  }
  else
  {
    Print("Failed to create trade log CSV: ", GetLastError());
  }

  Print("Backtest EA initialized. Ensemble file: ", EnsembleFileName);
  PrintFormat("Key Settings: UseEnsembleVoting=%d UseKMeansGate=%d UsePythonSizing=%d ConsecutiveBarsUp=%d", 
              UseEnsembleVoting, UseKMeansGate, UsePythonSizing, ConsecutiveBarsUp);
  return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
  if(ha_handle != INVALID_HANDLE)
    IndicatorRelease(ha_handle);
  if(trade_log_file != INVALID_HANDLE)
  {
    FileClose(trade_log_file);
    Print("Trade log CSV closed. Total trades logged: ", total_trades_logged);
  }
}

//+------------------------------------------------------------------+
void OnTick()
{
  // detect new bar on HA_Timeframe
  datetime current_bar_time = iTime(_Symbol, HA_Timeframe, 0);
  if(current_bar_time == last_bar_time) return;
  last_bar_time = current_bar_time;

  // get HA buffer
  if(!GetHeikenAshiData()) return;

  // update pattern counts and price history
  CountConsecutiveBars();
  UpdatePriceHistory();

  // recalc K-means clusters and market condition
  RecalculateKMeans();

  // load ensemble prediction for previous completed bar (bar 1)
  bool ensemble_loaded = false;
  if(UseEnsembleVoting)
    ensemble_loaded = GetEnsemblePredictionFromCSV();

  // check signals
  CheckTradingSignals(ensemble_loaded);
}

//+------------------------------------------------------------------+
bool GetHeikenAshiData()
{
  if(ha_handle == INVALID_HANDLE) return false;
  // use buffer 1 (Heiken Ashi close) instead of 3 — ensures we read HA close values correctly
  if(CopyBuffer(ha_handle, 1, 0, 10, ha_close) <= 0)
  {
    Print("Failed to copy HA buffer");
    return false;
  }
  return true;
}

//+------------------------------------------------------------------+
// Approximate K-means density: count values within mean +/- stddev
// Recalculate K-means clusters over the rolling price_history (mirrors Python backtest)
void RecalculateKMeans()
{
  // Always allow trades initially; after 252 bars, gate on density if UseKMeansGate=true
  if(!UseKMeansGate) { market_good_condition = true; return; }
  
  int bars = KMeans_TrainBars;
  if(ArraySize(price_history) < bars) { market_good_condition = true; return; }

  // initialize cluster centers evenly from the history
  for(int k = 0; k < KMeans_K; k++)
  {
    int idx = (k * bars) / KMeans_K;
    clusters[k].center = price_history[idx];
    clusters[k].count = 0;
    clusters[k].std_dev = 0.0;
    clusters[k].density = 0.0;
  }

  // K-means iterations (5 iterations)
  for(int iter = 0; iter < 5; iter++)
  {
    // reset sums
    double sums[];
    int counts[];
    ArrayResize(sums, KMeans_K);
    ArrayResize(counts, KMeans_K);
    ArrayInitialize(sums, 0.0);
    ArrayInitialize(counts, 0);

    // assign each point to nearest center
    for(int i = 0; i < bars; i++)
    {
      double p = price_history[i];
      double min_dist = DBL_MAX;
      int nearest = 0;
      for(int k = 0; k < KMeans_K; k++)
      {
        double d = MathAbs(p - clusters[k].center);
        if(d < min_dist) { min_dist = d; nearest = k; }
      }
      sums[nearest] += p;
      counts[nearest]++;
    }

    // update centers
    for(int k = 0; k < KMeans_K; k++)
    {
      if(counts[k] > 0)
      {
        clusters[k].center = sums[k] / counts[k];
        clusters[k].count = counts[k];
      }
    }
  }

  // compute std_dev and density for each cluster
  for(int k = 0; k < KMeans_K; k++)
  {
    double sumsq = 0.0;
    int close_count = 0;
    for(int i = 0; i < bars; i++)
    {
      double d = MathAbs(price_history[i] - clusters[k].center);
      if(d < 200 * _Point)
      {
        sumsq += d * d;
        close_count++;
      }
    }
    clusters[k].std_dev = (close_count > 0) ? MathSqrt(sumsq / close_count) : 0.0;
    clusters[k].density = (double)clusters[k].count / bars * 100.0;
  }

  // sort clusters by density desc
  for(int i = 0; i < KMeans_K - 1; i++)
  {
    for(int j = i + 1; j < KMeans_K; j++)
    {
      if(clusters[j].density > clusters[i].density)
      {
        KMeansCluster tmp = clusters[i];
        clusters[i] = clusters[j];
        clusters[j] = tmp;
      }
    }
  }

  // market condition based on top cluster density
  market_good_condition = (clusters[0].density >= MinClusterDensityPercent);
  PrintFormat("KMeans: top_density=%.2f%% count=%d center=%.5f", clusters[0].density, clusters[0].count, clusters[0].center);
}

//+------------------------------------------------------------------+
void CountConsecutiveBars()
{
  // Count consecutive up/down bars from the HA closes
  // bar[1] = previous completed bar, bar[2] = 2 bars ago, etc.
  ups_counter = 0;
  dns_counter = 0;
  
  // Count consecutive bars
  for(int i = 1; i < 10; i++)
  {
    if(i + 1 >= 10) break;
    double cur = ha_close[i];
    double prev = ha_close[i + 1];
    
    if(cur > prev) ups_counter++;
    else if(cur < prev) dns_counter++;
    else break; // no movement, stop counting
  }
  
  // Reset the one that didn't win
  if(ups_counter > 0 && dns_counter > 0) { ups_counter = 0; dns_counter = 0; }
  
  PrintFormat("HA: bar[1]=%.5f bar[2]=%.5f bar[3]=%.5f | ups=%d dns=%d", ha_close[1], ha_close[2], ha_close[3], ups_counter, dns_counter);
}

//+------------------------------------------------------------------+
// Update price_history with latest completed HA close
void UpdatePriceHistory()
{
  // shift back
  for(int i = KMeans_TrainBars - 1; i > 0; i--)
    price_history[i] = price_history[i-1];

  // insert latest completed bar HA close
  price_history[0] = ha_close[1];
}

//+------------------------------------------------------------------+
int StringToIntSafe(string s)
{
  double d = StringToDouble(s);
  return (int)MathRound(d);
}

//+------------------------------------------------------------------+
// Log closed trade to CSV file
void LogTrade(int entry_idx, double entry_price, datetime entry_time, string entry_bar_time,
              string direction, int signal, double lot_size, double sl, double tp, double confidence,
              int exit_idx, double exit_price, string exit_type, datetime exit_time, double pnl,
              int days_open, int bars_open)
{
  if(trade_log_file == INVALID_HANDLE) return;

  // Format: entry_idx,entry_price,entry_time,entry_bar_time,direction,signal,lot_size,sl,tp,confidence,exit_idx,exit_price,exit_type,exit_time,pnl,days_open,bars_open
  string line = StringFormat("%d,%.5f,%s,%s,%s,%d,%.3f,%.5f,%.5f,%.2f,%d,%.5f,%s,%s,%.2f,%d,%d",
                             entry_idx,
                             entry_price,
                             TimeToString(entry_time, TIME_DATE | TIME_MINUTES),
                             entry_bar_time,
                             direction,
                             signal,
                             lot_size,
                             sl,
                             tp,
                             confidence,
                             exit_idx,
                             exit_price,
                             exit_type,
                             TimeToString(exit_time, TIME_DATE | TIME_MINUTES),
                             pnl,
                             days_open,
                             bars_open);

  FileWriteString(trade_log_file, line + "\n");
  total_trades_logged++;
  PrintFormat("Trade logged: %s entry=%.5f exit=%.5f pnl=%.2f", direction, entry_price, exit_price, pnl);
}

//+------------------------------------------------------------------+
// (ATR removed) SL/TP will be calculated using fixed StopLoss_Pips and TakeProfit_Pips

//+------------------------------------------------------------------+
// Read ensemble CSV by bar time (previous completed bar) — returns true if matching row found
bool GetEnsemblePredictionFromCSV()
{
  datetime barTime = iTime(_Symbol, HA_Timeframe, 1);
  current_ensemble.ensemble_signal = 0;
  current_ensemble.confidence = 0.0;
  current_ensemble.time = 0;

  int fh = FileOpen(EnsembleFileName, FILE_READ | FILE_CSV | FILE_ANSI | FILE_COMMON);
  if(fh == INVALID_HANDLE)
  {
    int err = GetLastError();
    PrintFormat("ERROR: Ensemble CSV not found: %s (error=%d)", EnsembleFileName, err);
    PrintFormat("  Expected location: MQL5\\Files\\%s", EnsembleFileName);
    return false;
  }

  bool found = false;
  int row = 0;
  int total_rows = 0;
  
  while(!FileIsEnding(fh))
  {
    string line = FileReadString(fh);
    
    // Skip empty lines
    if(StringLen(line) == 0) continue;
    
    // Skip header (row 0)
    if(row == 0) { row++; continue; }
    
    // Parse CSV line
    string parts[];
    int cnt = StringSplit(line, ',', parts);
    if(cnt < 6) 
    { 
      PrintFormat("WARNING: Row %d has fewer than 6 columns (%d), skipping", row, cnt);
      row++; 
      continue; 
    }

    total_rows++;
    
    // Parse time from first column
    string timestr = parts[0];
    if(StringLen(timestr) == 0) { row++; continue; }

    // Try to convert time string to datetime
    datetime t = StringToTime(timestr);
    
    // Check if this is our bar's time
    if(t == barTime)
    {
      current_ensemble.lstm_signal = StringToIntSafe(parts[1]);
      current_ensemble.rf_signal = StringToIntSafe(parts[2]);
      current_ensemble.xgb_signal = StringToIntSafe(parts[3]);
      current_ensemble.ensemble_signal = StringToIntSafe(parts[4]);
      current_ensemble.confidence = StringToDouble(parts[5]);
      current_ensemble.time = t;
      found = true;
      
      PrintFormat("SUCCESS: Ensemble matched for bar %s → LSTM=%d RF=%d XGB=%d Ensemble=%d Confidence=%.2f%%", 
                  TimeToString(barTime, TIME_DATE|TIME_MINUTES), 
                  current_ensemble.lstm_signal, 
                  current_ensemble.rf_signal,
                  current_ensemble.xgb_signal,
                  current_ensemble.ensemble_signal,
                  current_ensemble.confidence);
      break;
    }
    else if(t > barTime)
    {
      // CSV has future data, no match for this bar
      PrintFormat("INFO: CSV row %s > target bar %s, stopping search (found %d data rows)", 
                  TimeToString(t, TIME_DATE|TIME_MINUTES), 
                  TimeToString(barTime, TIME_DATE|TIME_MINUTES),
                  total_rows);
      break;
    }

    row++;
  }

  FileClose(fh);
  
  if(!found)
  {
    PrintFormat("WARNING: No ensemble row found for bar time %s (searched %d data rows)", 
                TimeToString(barTime, TIME_DATE|TIME_MINUTES), total_rows);
    return false;
  }
  
  return true;
}

//+------------------------------------------------------------------+
void CheckTradingSignals(bool ensemble_loaded)
{
  bool long_pattern = (ups_counter >= ConsecutiveBarsUp);
  bool short_pattern = (dns_counter >= ConsecutiveBarsDown);
  
  PrintFormat("CheckSignals: long_pattern=%d short_pattern=%d ensemble_loaded=%d market_good=%d", long_pattern, short_pattern, ensemble_loaded, market_good_condition);

  // require ensemble vote when UseEnsembleVoting==true
  if(long_pattern)
  {
    if(UseEnsembleVoting)
    {
      if(!ensemble_loaded)
      {
        if(!AllowTradesWhenEnsembleMissing)
        {
          Print("Long pattern but ensemble missing — skipping (AllowTradesWhenEnsembleMissing=false)");
          return;
        }
        else
        {
          Print("Long pattern and ensemble missing — allowing trade due to AllowTradesWhenEnsembleMissing=true");
        }
      }
      else if(current_ensemble.ensemble_signal != 1)
      {
        Print("Long pattern but ensemble not BUY");
        return;
      }
    }
    // require market regime valid (only if K-means gate enabled)
    if(UseKMeansGate && !market_good_condition) { PrintFormat("Long pattern BUT K-means gate failed: density=%.2f%% threshold=%.2f%%", clusters[0].density, MinClusterDensityPercent); return; }
    PrintFormat("OPENING LONG: ups_counter=%d ensemble_signal=%d", ups_counter, current_ensemble.ensemble_signal);
    double lot = CalculateLotSize(current_ensemble.confidence);
    OpenLongWithLots(lot);
  }

  if(short_pattern)
  {
    if(UseEnsembleVoting)
    {
      if(!ensemble_loaded)
      {
        if(!AllowTradesWhenEnsembleMissing)
        {
          Print("Short pattern but ensemble missing — skipping (AllowTradesWhenEnsembleMissing=false)");
          return;
        }
        else
        {
          Print("Short pattern and ensemble missing — allowing trade due to AllowTradesWhenEnsembleMissing=true");
        }
      }
      else if(current_ensemble.ensemble_signal != -1)
      {
        Print("Short pattern but ensemble not SELL");
        return;
      }
    }
    if(UseKMeansGate && !market_good_condition) { PrintFormat("Short pattern BUT K-means gate failed: density=%.2f%% threshold=%.2f%%", clusters[0].density, MinClusterDensityPercent); return; }
    PrintFormat("OPENING SHORT: dns_counter=%d ensemble_signal=%d", dns_counter, current_ensemble.ensemble_signal);
    double lot = CalculateLotSize(current_ensemble.confidence);
    OpenShortWithLots(lot);
  }
}

//+------------------------------------------------------------------+
void OpenLong()
{
  if(PositionSelect(_Symbol))
  {
    // if any position exists for symbol, skip (simpler)
    Print("Position already open, skipping long");
    return;
  }
  double price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
  double sl = price - StopLoss_Pips * _Point;
  double tp = price + TakeProfit_Pips * _Point;
  if(UsePythonSizing)
  {
    sl = price - StopLoss_Pips * PipMultiplier;
    tp = price + TakeProfit_Pips * PipMultiplier;
  }
  double lots = BaseLotSize;
  string comment = TradeComment + "_Long";

  if(!EnsureValidStopsAndLots(true, lots, sl, tp))
  {
    Print("OpenLong: Invalid stops after adjustment, skipping order");
    return;
  }

  if(trade.Buy(lots, _Symbol, price, sl, tp, comment))
    PrintFormat("Opened LONG @%.5f lots=%.3f sl=%.5f tp=%.5f", price, lots, sl, tp);
  else
    PrintFormat("Buy failed: %d (price=%.5f lots=%.3f sl=%.5f tp=%.5f)", GetLastError(), price, lots, sl, tp);
}

// Open with explicit lot size
bool EnsureValidStopsAndLots(bool isBuy, double &lots, double &sl, double &tp)
{
  // enforce symbol volume limits
  double vol_min = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
  double vol_max = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
  double vol_step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
  if(vol_min <= 0) vol_min = 0.01;
  if(vol_step <= 0) vol_step = 0.01;

  // clip lots to allowed range
  if(lots < vol_min) lots = vol_min;
  if(vol_max > 0 && lots > vol_max) lots = vol_max;

  // normalize to step
  double steps = MathRound(lots / vol_step);
  lots = steps * vol_step;

  // minimal stop distance (in points)
  int minStops = (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
  double minStopDistance = (minStops > 0) ? (minStops * _Point) : (10 * _Point);
  double buffer = 2 * _Point; // small extra buffer

  // current price
  double price = isBuy ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID);

  // compute desired SL/TP using either broker points or Python pip multiplier
  if(isBuy)
  {
    double desired_sl = price - StopLoss_Pips * (UsePythonSizing ? PipMultiplier : _Point);
    double desired_tp = price + TakeProfit_Pips * (UsePythonSizing ? PipMultiplier : _Point);
    if(price - desired_sl < minStopDistance + buffer) desired_sl = price - (minStopDistance + buffer);
    if(desired_tp - price < minStopDistance + buffer) desired_tp = price + (minStopDistance + buffer);
    sl = desired_sl; tp = desired_tp;
  }
  else
  {
    double desired_sl = price + StopLoss_Pips * (UsePythonSizing ? PipMultiplier : _Point);
    double desired_tp = price - TakeProfit_Pips * (UsePythonSizing ? PipMultiplier : _Point);
    if(desired_sl - price < minStopDistance + buffer) desired_sl = price + (minStopDistance + buffer);
    if(price - desired_tp < minStopDistance + buffer) desired_tp = price - (minStopDistance + buffer);
    sl = desired_sl; tp = desired_tp;
  }

  // final sanity: sl and tp must be on correct sides
  if(isBuy)
  {
    if(!(sl < price && tp > price)) return false;
  }
  else
  {
    if(!(sl > price && tp < price)) return false;
  }

  PrintFormat("EnsureStops: isBuy=%s price=%.5f sl=%.5f tp=%.5f lots=%.3f minStopPts=%d", isBuy?"BUY":"SELL", price, sl, tp, lots, minStops);
  return true;
}

// Open with explicit lot size
void OpenLongWithLots(double lots)
{
  PrintFormat("OpenLongWithLots: called with lots=%.3f", lots);
  if(PositionSelect(_Symbol)) { PrintFormat("BLOCKED: Position already open for %s", _Symbol); return; }
  double price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
  double sl = price - StopLoss_Pips * (UsePythonSizing ? PipMultiplier : _Point);
  double tp = price + TakeProfit_Pips * (UsePythonSizing ? PipMultiplier : _Point);
  string comment = TradeComment + "_Long";

  PrintFormat("Before EnsureStops: price=%.5f sl=%.5f tp=%.5f lots=%.3f", price, sl, tp, lots);
  
  if(!EnsureValidStopsAndLots(true, lots, sl, tp))
  {
    PrintFormat("BLOCKED: EnsureValidStopsAndLots returned false");
    return;
  }

  PrintFormat("After EnsureStops: price=%.5f sl=%.5f tp=%.5f lots=%.3f", price, sl, tp, lots);
  
  if(trade.Buy(lots, _Symbol, price, sl, tp, comment))
    PrintFormat("SUCCESS: Opened LONG @%.5f lots=%.3f sl=%.5f tp=%.5f", price, lots, sl, tp);
  else
    PrintFormat("FAILED: Buy order rejected. Error=%d (price=%.5f lots=%.3f sl=%.5f tp=%.5f)", GetLastError(), price, lots, sl, tp);
}

// Open short
void OpenShort()
{
  if(PositionSelect(_Symbol))
  {
    Print("Position already open, skipping short");
    return;
  }
  double price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
  double lots = BaseLotSize;
  double sl = price + StopLoss_Pips * (UsePythonSizing ? PipMultiplier : _Point);
  double tp = price - TakeProfit_Pips * (UsePythonSizing ? PipMultiplier : _Point);
  string comment = TradeComment + "_Short";

  if(!EnsureValidStopsAndLots(false, lots, sl, tp))
  {
    Print("OpenShort: Invalid stops after adjustment, skipping order");
    return;
  }

  if(trade.Sell(lots, _Symbol, price, sl, tp, comment))
    PrintFormat("Opened SHORT @%.5f lots=%.3f sl=%.5f tp=%.5f", price, lots, sl, tp);
  else
    PrintFormat("Sell failed: %d (price=%.5f lots=%.3f sl=%.5f tp=%.5f)", GetLastError(), price, lots, sl, tp);
}

// Open short with explicit lots
void OpenShortWithLots(double lots)
{
  PrintFormat("OpenShortWithLots: called with lots=%.3f", lots);
  if(PositionSelect(_Symbol)) { PrintFormat("BLOCKED: Position already open for %s", _Symbol); return; }
  double price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
  double sl = price + StopLoss_Pips * (UsePythonSizing ? PipMultiplier : _Point);
  double tp = price - TakeProfit_Pips * (UsePythonSizing ? PipMultiplier : _Point);
  string comment = TradeComment + "_Short";

  PrintFormat("Before EnsureStops: price=%.5f sl=%.5f tp=%.5f lots=%.3f", price, sl, tp, lots);
  
  if(!EnsureValidStopsAndLots(false, lots, sl, tp))
  {
    PrintFormat("BLOCKED: EnsureValidStopsAndLots returned false");
    return;
  }

  PrintFormat("After EnsureStops: price=%.5f sl=%.5f tp=%.5f lots=%.3f", price, sl, tp, lots);
  
  if(trade.Sell(lots, _Symbol, price, sl, tp, comment))
    PrintFormat("SUCCESS: Opened SHORT @%.5f lots=%.3f sl=%.5f tp=%.5f", price, lots, sl, tp);
  else
    PrintFormat("FAILED: Sell order rejected. Error=%d (price=%.5f lots=%.3f sl=%.5f tp=%.5f)", GetLastError(), price, lots, sl, tp);
}

//+------------------------------------------------------------------+
// Utility: select position by magic and type
bool PositionExists(int type)
{
  for(int i=0;i<PositionsTotal();i++)
  {
    ulong ticket = PositionGetTicket(i);
    if(ticket > 0)
    {
      if(PositionSelectByTicket(ticket))
      {
        if(PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==Magic && PositionGetInteger(POSITION_TYPE)==type)
          return true;
      }
    }
  }
  return false;
}

//+------------------------------------------------------------------+
// Calculate lot size based on AccountBalance, RiskPercent and SL pips
double CalculateLotSize(double confidence)
{
  double risk_amount = AccountBalance * (RiskPercent / 100.0);
  double lots = BaseLotSize;

  if(UsePythonSizing)
  {
    // Mirror Python: pip value fixed (0.01 in python script) and pip multiplier
    double pip_value = 0.01; // same as python backtest
    double sl_pips = StopLoss_Pips;
    double sl_dollars_per_lot = sl_pips * pip_value;
    if(sl_dollars_per_lot > 0) lots = risk_amount / sl_dollars_per_lot;
    else lots = BaseLotSize;
    // confidence multipliers (same thresholds)
    if(confidence >= 67.0) lots *= 1.2;
    else if(confidence <= 50.0) lots *= 0.5;
  }
  else
  {
    // Broker-accurate sizing using tick values
    double sl_price = StopLoss_Pips * _Point;
    double tick_value = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
    double tick_size = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
    double value_per_price = 0.0;
    if(tick_value > 0 && tick_size > 0) value_per_price = tick_value / tick_size; // currency per 1 price move per lot
    double sl_dollars_per_lot = 0.0;
    if(value_per_price > 0) sl_dollars_per_lot = sl_price * value_per_price;
    else sl_dollars_per_lot = StopLoss_Pips * 0.01; // fallback estimate
    lots = (sl_dollars_per_lot > 0) ? (risk_amount / sl_dollars_per_lot) : BaseLotSize;

    if(confidence >= 67.0) lots *= 1.2;
    else if(confidence <= 50.0) lots *= 0.5;
  }

  // Clip to allowed range and normalize to symbol step
  double vol_min = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
  double vol_max = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
  double vol_step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
  if(vol_min <= 0) vol_min = MinLotSize;
  if(vol_step <= 0) vol_step = 0.01;

  if(lots < MinLotSize) lots = MinLotSize;
  if(vol_max > 0 && lots > vol_max) lots = vol_max;

  // normalize to step
  double steps = MathRound(lots / vol_step);
  lots = steps * vol_step;

  double lots_norm = NormalizeDouble(lots, 3);
  PrintFormat("LotCalc: python_mode=%s risk_amount=%.2f sl_pips=%.2f raw_lots=%.5f final_lots=%.3f confidence=%.2f vol_min=%.3f vol_max=%.3f vol_step=%.3f", 
              UsePythonSizing?"YES":"NO", risk_amount, StopLoss_Pips, lots, lots_norm, confidence, vol_min, vol_max, vol_step);
  return lots_norm;
}

//+------------------------------------------------------------------+
// End of file
//+------------------------------------------------------------------+
