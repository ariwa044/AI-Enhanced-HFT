//+------------------------------------------------------------------+
//| Ensemble Backtesting Expert Advisor with K-Means Market Regime   |
//| Production-Grade Backtest Engine for Python Ensemble Signals     |
//| Features: 3-bar pattern + ensemble voting + K-means adaptive TP  |
//+------------------------------------------------------------------+

#property copyright "AI-Enhanced HFT Systems"
#property link      "https://ai-hft.local"
#property version   "3.00"
#property strict
#property description "Professional Backtesting EA with realistic trade simulation"

//--- Input parameters (BACKTEST FOCUSED)
input double      RiskPercent           = 2.0;          // Risk per trade (%)
input int         StopLossPips          = 300;          // Fixed stop loss (pips)
input int         TakeProfitPips        = 800;          // Base TP (modified by K-means)
input int         MinHoldingBars        = 16;           // Min bars to hold (4 hours on M15)
input int         MaxDailyTrades        = 3;            // Max trades per calendar day
input double      MinLotSize            = 0.5;          // Minimum lot size (0.01 lots)
input double      MaxLotSize            = 2.0;          // Maximum lot size (2.0 lots)
input string      EnsembleCSVFile       = "ensemble_ha15m_forecast.csv";  // CSV filename
input bool        EnableTrading         = true;         // Master on/off switch
input double      InitialBalance        = 10000;        // Starting account balance
input bool        UseCSVSignals         = true;         // Read signals from CSV vs pattern fallback
input int         MaxConsecutiveWins    = 0;            // Track max consecutive wins
input int         MaxConsecutiveLosses  = 0;            // Track max consecutive losses

//--- Global variables
double            Points;
int               Digits;
int               BarCount = 0;
datetime          LastBarTime = 0;
datetime          LastTradeDate = 0;
int               DailyTradeCount = 0;

//--- Backtest metrics tracking
double            BacktestEquity;
double            BacktestInitialBalance;
int               BacktestTrades = 0;
int               BacktestWins = 0;
int               BacktestLosses = 0;
int               BacktestBreakeven = 0;
double            BacktestGrossProfit = 0;
double            BacktestGrossLoss = 0;
double            BacktestNetProfit = 0;
double            BacktestMaxDrawdown = 0;
double            BacktestMaxEquity = 0;
double            BacktestConsecutiveWins = 0;
double            BacktestConsecutiveLosses = 0;

//--- Trade data structure
struct Trade {
    datetime      entry_time;
    double        entry_price;
    int           entry_bar;
    int           direction;            // 1=BUY, -1=SELL
    double        cluster_density;      // For K-means TP
    double        tp_pips;              // Dynamic TP (200-600 range)
    double        sl_pips;              // Stop loss
    datetime      exit_time;
    double        exit_price;
    int           exit_bar;
    string        exit_type;            // "TP", "SL", "END"
    double        pnl_gross;            // Before commissions/spread
    double        pnl_net;              // After costs
    int           bars_held;
    int           confidence;
};

Trade             ActiveTrade;          // Current open position
Trade             CompletedTrades[1000]; // History of trades
int               CompletedTradeCount = 0;

//--- Bar pattern tracking
struct BarPattern {
    int           consecutive_up;
    int           consecutive_down;
    bool          pattern_valid;
};

BarPattern        Pattern;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    Digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
    Points = _Point;
    
    // Initialize backtest metrics
    BacktestEquity = InitialBalance;
    BacktestInitialBalance = InitialBalance;
    BacktestMaxEquity = InitialBalance;
    BacktestTrades = 0;
    BacktestWins = 0;
    BacktestLosses = 0;
    BacktestBreakeven = 0;
    BacktestGrossProfit = 0;
    BacktestGrossLoss = 0;
    BacktestNetProfit = 0;
    BacktestMaxDrawdown = 0;
    
    // Initialize position tracking
    ActiveTrade.entry_bar = 0;
    ActiveTrade.direction = 0;
    
    // Initialize pattern
    Pattern.consecutive_up = 0;
    Pattern.consecutive_down = 0;
    Pattern.pattern_valid = false;
    
    // Print startup info
    Print("\n========================================");
    Print("ENSEMBLE BACKTESTING EA v3.00");
    Print("========================================");
    Print("Symbol: ", _Symbol);
    Print("Timeframe: M15 (Expert will use M15 data)");
    Print("Initial Balance: $", DoubleToString(InitialBalance, 2));
    Print("Risk per Trade: ", RiskPercent, "%");
    Print("Stop Loss: ", StopLossPips, " pips");
    Print("Base Take Profit: ", TakeProfitPips, " pips");
    Print("Min Holding Period: ", MinHoldingBars, " bars");
    Print("Max Daily Trades: ", MaxDailyTrades);
    Print("CSV Signal File: ", EnsembleCSVFile);
    Print("========================================\n");
    
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    // Calculate final metrics
    double roi = (BacktestEquity - BacktestInitialBalance) / BacktestInitialBalance * 100;
    double win_rate = (BacktestTrades > 0 ? (double)BacktestWins / BacktestTrades * 100 : 0);
    double profit_factor = (BacktestGrossLoss > 0 ? BacktestGrossProfit / BacktestGrossLoss : 0);
    double avg_win = (BacktestWins > 0 ? BacktestGrossProfit / BacktestWins : 0);
    double avg_loss = (BacktestLosses > 0 ? BacktestGrossLoss / BacktestLosses : 0);
    
    // Print final results
    Print("\n========================================");
    Print("BACKTEST RESULTS SUMMARY");
    Print("========================================");
    Print("\n--- ACCOUNT SUMMARY ---");
    Print("Initial Balance:    $", DoubleToString(BacktestInitialBalance, 2));
    Print("Final Equity:       $", DoubleToString(BacktestEquity, 2));
    Print("Net Profit/Loss:    $", DoubleToString(BacktestNetProfit, 2));
    Print("Return on Investment: ", DoubleToString(roi, 2), "%");
    
    Print("\n--- TRADE STATISTICS ---");
    Print("Total Trades:       ", BacktestTrades);
    Print("Winning Trades:     ", BacktestWins);
    Print("Losing Trades:      ", BacktestLosses);
    Print("Breakeven Trades:   ", BacktestBreakeven);
    Print("Win Rate:           ", DoubleToString(win_rate, 2), "%");
    
    Print("\n--- PROFITABILITY ---");
    Print("Gross Profit:       $", DoubleToString(BacktestGrossProfit, 2));
    Print("Gross Loss:         $", DoubleToString(BacktestGrossLoss, 2));
    Print("Profit Factor:      ", DoubleToString(profit_factor, 2));
    Print("Avg Win:            $", DoubleToString(avg_win, 2));
    Print("Avg Loss:           $", DoubleToString(avg_loss, 2));
    
    Print("\n--- RISK METRICS ---");
    Print("Max Drawdown:       ", DoubleToString(BacktestMaxDrawdown, 2), "%");
    Print("Max Consecutive Wins:   ", (int)BacktestConsecutiveWins);
    Print("Max Consecutive Losses: ", (int)BacktestConsecutiveLosses);
    
    Print("\n========================================\n");
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    if(!EnableTrading)
        return;
    
    // Check for new bar on M15
    datetime current_time = iTime(_Symbol, PERIOD_M15, 0);
    if(LastBarTime == current_time)
        return;
    
    LastBarTime = current_time;
    BarCount++;
    
    // Reset daily trade counter if new day
    if(TimeDay(current_time) != TimeDay(LastTradeDate))
    {
        DailyTradeCount = 0;
        LastTradeDate = current_time;
    }
    
    // Update bar pattern on each new bar
    UpdateBarPattern();
    
    // Process exit conditions first (open position)
    if(ActiveTrade.entry_bar > 0)
    {
        ProcessExitConditions();
    }
    
    // Process entry conditions (only if no open position)
    if(ActiveTrade.entry_bar == 0 && DailyTradeCount < MaxDailyTrades && EnableTrading)
    {
        ProcessEntryConditions();
    }
}

//+------------------------------------------------------------------+
//| Update consecutive bar pattern (3-bar confirmation)              |
//+------------------------------------------------------------------+
void UpdateBarPattern()
{
    double close_prev = iClose(_Symbol, PERIOD_M15, 1);
    double close_prev2 = iClose(_Symbol, PERIOD_M15, 2);
    
    // Count consecutive up/down bars (close > previous close)
    if(close_prev > close_prev2)
    {
        Pattern.consecutive_up++;
        Pattern.consecutive_down = 0;
    }
    else if(close_prev < close_prev2)
    {
        Pattern.consecutive_down++;
        Pattern.consecutive_up = 0;
    }
    else
    {
        Pattern.consecutive_up = 0;
        Pattern.consecutive_down = 0;
    }
    
    // Pattern valid when we have 3+ consecutive bars
    Pattern.pattern_valid = (Pattern.consecutive_up >= 3 || Pattern.consecutive_down >= 3);
}

//+------------------------------------------------------------------+
//| Process entry conditions: pattern + signal                       |
//+------------------------------------------------------------------+
void ProcessEntryConditions()
{
    // Pattern validation: need 3+ consecutive bars
    if(!Pattern.pattern_valid)
        return;
    
    // Get ensemble signal (from CSV or pattern fallback)
    int signal = GetEnsembleSignal(iTime(_Symbol, PERIOD_M15, 0));
    if(signal == 0)
        return;
    
    // Signal direction determines trade direction
    int direction = signal;  // 1=BUY, -1=SELL
    
    // Verify signal matches pattern direction
    if(direction == 1 && Pattern.consecutive_up < 3)
        return;  // BUY signal but not enough up bars
    if(direction == -1 && Pattern.consecutive_down < 3)
        return;  // SELL signal but not enough down bars
    
    // Both conditions met: execute trade entry
    OpenTrade(direction);
}

//+------------------------------------------------------------------+
//| Open a new trade position                                        |
//+------------------------------------------------------------------+
void OpenTrade(int direction)
{
    double entry_price = iClose(_Symbol, PERIOD_M15, 0);
    double cluster_density = GetClusterDensity();
    
    // K-means adaptive TP: 200-600 pips based on cluster density
    // Higher density (>0.7) = stronger trend = wider TP
    // Lower density (<0.3) = weaker trend = tighter TP
    double dynamic_tp = 200 + (cluster_density * 400);
    
    // Calculate position sizing based on risk
    double risk_amount = BacktestEquity * (RiskPercent / 100);
    double pip_value = Points * (Digits == 3 || Digits == 5 ? 10 : 1);
    double sl_dollars = StopLossPips * pip_value;
    double lot_size = risk_amount / sl_dollars;
    lot_size = MathMax(MinLotSize, MathMin(MaxLotSize, lot_size));
    
    // Store trade entry data
    ActiveTrade.entry_time = iTime(_Symbol, PERIOD_M15, 0);
    ActiveTrade.entry_price = entry_price;
    ActiveTrade.entry_bar = BarCount;
    ActiveTrade.direction = direction;
    ActiveTrade.cluster_density = cluster_density;
    ActiveTrade.tp_pips = dynamic_tp;
    ActiveTrade.sl_pips = StopLossPips;
    ActiveTrade.confidence = GetSignalConfidence(direction);
    
    DailyTradeCount++;
    BacktestTrades++;
    
    // Log entry
    Print("\n>>> TRADE ENTRY #", BacktestTrades, " [Bar ", BarCount, "]");
    Print("Type: ", (direction == 1 ? "BUY" : "SELL"));
    Print("Entry Price: ", DoubleToString(entry_price, Digits));
    Print("SL Pips: ", (int)ActiveTrade.sl_pips, " | TP Pips: ", DoubleToString(ActiveTrade.tp_pips, 1));
    Print("Cluster Density: ", DoubleToString(cluster_density, 3), " | Lot Size: ", DoubleToString(lot_size, 2));
    Print("Pattern: ", (Pattern.consecutive_up >= 3 ? "Up" : "Down"), " bars=", 
          (Pattern.consecutive_up >= 3 ? Pattern.consecutive_up : Pattern.consecutive_down));
}

//+------------------------------------------------------------------+
//| Get ensemble signal from CSV file                                |
//+------------------------------------------------------------------+
int GetEnsembleSignal(datetime bar_time)
{
    if(!UseCSVSignals)
    {
        // Fallback: use pattern direction as signal
        if(Pattern.consecutive_up >= 3)
            return 1;
        if(Pattern.consecutive_down >= 3)
            return -1;
        return 0;
    }
    
    // Try to read from CSV file
    int handle = FileOpen(EnsembleCSVFile, FILE_READ | FILE_TXT | FILE_CSV);
    if(handle == INVALID_HANDLE)
    {
        // Print("CSV file not found, using pattern fallback");
        // Fallback to pattern
        if(Pattern.consecutive_up >= 3)
            return 1;
        if(Pattern.consecutive_down >= 3)
            return -1;
        return 0;
    }
    
    string time_str = TimeToString(bar_time, TIME_DATE);
    string line = "";
    int signal = 0;
    
    // Skip header line
    if(!FileIsEnding(handle))
        FileReadString(handle);
    
    // Search for matching time
    int line_count = 0;
    while(!FileIsEnding(handle) && line_count < 10000)
    {
        line = FileReadString(handle);
        line_count++;
        
        // Match by date (Time column is first)
        if(StringFind(line, time_str) >= 0)
        {
            // Parse CSV: Time, LSTM, RF, XGBoost, Ensemble, Confidence
            // Ensemble signal is 5th column (index 4)
            string ensemble_str = GetCSVField(line, 4);
            signal = (int)StringToDouble(ensemble_str);
            break;
        }
    }
    
    FileClose(handle);
    return signal;
}

//+------------------------------------------------------------------+
//| Parse CSV field by index                                         |
//+------------------------------------------------------------------+
string GetCSVField(const string line, int field_index)
{
    string fields[];
    int field_count = StringSplit(line, ',', fields);
    
    if(field_index < field_count && field_index >= 0)
        return fields[field_index];
    
    return "0";
}

//+------------------------------------------------------------------+
//| Get signal confidence (simplified)                               |
//+------------------------------------------------------------------+
int GetSignalConfidence(int direction)
{
    // Higher confidence with stronger pattern
    int pattern_strength = (direction == 1 ? Pattern.consecutive_up : Pattern.consecutive_down);
    
    if(pattern_strength >= 5)
        return 90;
    else if(pattern_strength >= 4)
        return 75;
    else
        return 60;
}

//+------------------------------------------------------------------+
//| Calculate K-means cluster density (market regime indicator)       |
//+------------------------------------------------------------------+
double GetClusterDensity()
{
    // Simplified K-means approximation using volatility
    // High volatility = low cluster density (weaker trend, 0.2-0.3)
    // Low volatility = high cluster density (stronger trend, 0.7-0.8)
    
    int lookback = 20;
    double sum_range = 0;
    
    for(int i = 1; i <= lookback; i++)
    {
        double high = iHigh(_Symbol, PERIOD_M15, i);
        double low = iLow(_Symbol, PERIOD_M15, i);
        double range = high - low;
        sum_range += range;
    }
    
    double avg_range = sum_range / lookback;
    
    // Current bar volatility
    double curr_high = iHigh(_Symbol, PERIOD_M15, 0);
    double curr_low = iLow(_Symbol, PERIOD_M15, 0);
    double curr_range = curr_high - curr_low;
    
    // Density = 1 - (current_volatility / average_volatility)
    // Clamp between 0.1 and 0.9
    double density;
    if(avg_range > 0)
        density = 1.0 - (curr_range / avg_range);
    else
        density = 0.5;
    
    density = MathMax(0.1, MathMin(0.9, density));
    return density;
}

//+------------------------------------------------------------------+
//| Process exit conditions (check SL/TP/time)                       |
//+------------------------------------------------------------------+
void ProcessExitConditions()
{
    // Must have open position
    if(ActiveTrade.entry_bar == 0)
        return;
    
    double current_price = iClose(_Symbol, PERIOD_M15, 0);
    double entry_price = ActiveTrade.entry_price;
    int bars_held = BarCount - ActiveTrade.entry_bar;
    
    // Minimum holding period (day trader requirement - 16 bars = 4 hours on M15)
    if(bars_held < MinHoldingBars)
        return;
    
    double stop_loss, take_profit;
    double exit_price = current_price;
    string exit_type = "";
    
    // Calculate SL and TP levels
    if(ActiveTrade.direction == 1)  // BUY
    {
        stop_loss = entry_price - (ActiveTrade.sl_pips * Points);
        take_profit = entry_price + (ActiveTrade.tp_pips * Points);
        
        if(current_price <= stop_loss)
        {
            exit_price = stop_loss;
            exit_type = "SL";
        }
        else if(current_price >= take_profit)
        {
            exit_price = take_profit;
            exit_type = "TP";
        }
    }
    else  // SELL
    {
        stop_loss = entry_price + (ActiveTrade.sl_pips * Points);
        take_profit = entry_price - (ActiveTrade.tp_pips * Points);
        
        if(current_price >= stop_loss)
        {
            exit_price = stop_loss;
            exit_type = "SL";
        }
        else if(current_price <= take_profit)
        {
            exit_price = take_profit;
            exit_type = "TP";
        }
    }
    
    // Close trade if SL or TP hit
    if(exit_type != "")
    {
        CloseTrade(exit_price, exit_type, bars_held);
    }
}

//+------------------------------------------------------------------+
//| Close trade and record results                                   |
//+------------------------------------------------------------------+
void CloseTrade(double exit_price, string exit_type, int bars_held)
{
    // Calculate P&L
    double price_diff = 0;
    if(ActiveTrade.direction == 1)  // BUY
        price_diff = exit_price - ActiveTrade.entry_price;
    else  // SELL
        price_diff = ActiveTrade.entry_price - exit_price;
    
    // Approximate lot size calculation
    double risk_amount = BacktestEquity * (RiskPercent / 100);
    double pip_value = Points * (Digits == 3 || Digits == 5 ? 10 : 1);
    double sl_dollars = ActiveTrade.sl_pips * pip_value;
    double lot_size = risk_amount / sl_dollars;
    lot_size = MathMax(MinLotSize, MathMin(MaxLotSize, lot_size));
    
    // Gross profit (before any costs)
    double pnl_gross = (price_diff / Points) * pip_value * lot_size;
    
    // Net profit (for now same as gross, add spread/commission later)
    double pnl_net = pnl_gross;
    
    // Update equity
    BacktestEquity += pnl_net;
    BacktestNetProfit += pnl_net;
    
    // Track metrics
    if(pnl_net > 0)
    {
        BacktestWins++;
        BacktestGrossProfit += pnl_net;
        BacktestConsecutiveWins++;
        BacktestConsecutiveLosses = 0;
    }
    else if(pnl_net < 0)
    {
        BacktestLosses++;
        BacktestGrossLoss += MathAbs(pnl_net);
        BacktestConsecutiveLosses++;
        BacktestConsecutiveWins = 0;
    }
    else
    {
        BacktestBreakeven++;
    }
    
    // Update max metrics
    if(BacktestEquity > BacktestMaxEquity)
        BacktestMaxEquity = BacktestEquity;
    
    double drawdown_pct = (BacktestMaxEquity - BacktestEquity) / BacktestMaxEquity * 100;
    if(drawdown_pct > BacktestMaxDrawdown)
        BacktestMaxDrawdown = drawdown_pct;
    
    // Update max consecutive
    if(BacktestConsecutiveWins > MaxConsecutiveWins)
        MaxConsecutiveWins = (int)BacktestConsecutiveWins;
    if(BacktestConsecutiveLosses > MaxConsecutiveLosses)
        MaxConsecutiveLosses = (int)BacktestConsecutiveLosses;
    
    // Log exit
    Print("<<< TRADE EXIT #", BacktestTrades, " [Bar ", BarCount, "]");
    Print("Exit Type: ", exit_type);
    Print("Entry Price: ", DoubleToString(ActiveTrade.entry_price, Digits));
    Print("Exit Price: ", DoubleToString(exit_price, Digits));
    Print("Bars Held: ", bars_held);
    Print("P&L: $", DoubleToString(pnl_net, 2), " (", (pnl_net > 0 ? "WIN" : (pnl_net < 0 ? "LOSS" : "BE")), ")");
    Print("Equity: $", DoubleToString(BacktestEquity, 2));
    Print("Win Rate: ", (BacktestTrades > 0 ? DoubleToString((double)BacktestWins / BacktestTrades * 100, 2) : 0), "%\n");
    
    // Reset position
    ActiveTrade.entry_bar = 0;
    ActiveTrade.direction = 0;
}

//+------------------------------------------------------------------+
//| On Trade Event (placeholder for future use)                      |
//+------------------------------------------------------------------+
void OnTrade()
{
    // Backtest: all trades handled in ProcessExitConditions
    // This is for live trading event logging in future versions
}

