//+------------------------------------------------------------------+
//|                    Export_15m_HA_Data.mq5                         |
//|              Export Heiken Ashi 15m data for BTCUSD training     |
//+------------------------------------------------------------------+
#property copyright "AI-Enhanced Trading 2024"
#property version   "1.00"

//--- Input parameters
input string input_symbol = "BTCUSD";
input int bars_to_export = 10000;

void OnStart()
{
    string filename = "BTCUSD_15m_HA_data.csv";
    int file_handle = FileOpen(filename, FILE_WRITE | FILE_CSV | FILE_ANSI);
    if(file_handle == INVALID_HANDLE)
    {
        Print("Error opening file");
        return;
    }

    FileWrite(file_handle, "Time", "HA_Open", "HA_High", "HA_Low", "HA_Close", "Volume");

    int ha_handle = iCustom(input_symbol, PERIOD_M15, "Examples\\Heiken_Ashi");
    if(ha_handle == INVALID_HANDLE)
    {
        Print("Failed to create HA indicator");
        FileClose(file_handle);
        return;
    }

    double ha_open[], ha_high[], ha_low[], ha_close[];
    
    ArraySetAsSeries(ha_open, true);
    ArraySetAsSeries(ha_high, true);
    ArraySetAsSeries(ha_low, true);
    ArraySetAsSeries(ha_close, true);

    int available_bars = Bars(input_symbol, PERIOD_M15);
    int bars_to_use = MathMin(bars_to_export, available_bars);

    MqlRates rates[];
    if(CopyRates(input_symbol, PERIOD_M15, 0, bars_to_use, rates) <= 0)
    {
        Print("Error loading historical data");
        FileClose(file_handle);
        return;
    }
    ArraySetAsSeries(rates, true);

    if(CopyBuffer(ha_handle, 0, 0, bars_to_use, ha_open) <= 0 ||
       CopyBuffer(ha_handle, 1, 0, bars_to_use, ha_high) <= 0 ||
       CopyBuffer(ha_handle, 2, 0, bars_to_use, ha_low) <= 0 ||
       CopyBuffer(ha_handle, 3, 0, bars_to_use, ha_close) <= 0)
    {
        Print("Error copying indicator buffers");
        FileClose(file_handle);
        return;
    }

    ArraySetAsSeries(ha_open, true);
    ArraySetAsSeries(ha_high, true);
    ArraySetAsSeries(ha_low, true);
    ArraySetAsSeries(ha_close, true);

    for(int i = 0; i < bars_to_use; i++)
    {
        FileWrite(file_handle,
                  TimeToString(rates[i].time, TIME_DATE | TIME_MINUTES),
                  ha_open[i],
                  ha_high[i],
                  ha_low[i],
                  ha_close[i],
                  rates[i].tick_volume);
    }

    FileClose(file_handle);
    
    Print("Export completed: ", filename);
    Print("Bars exported: ", bars_to_use);
    Print("Timeframe: 15m (Heiken Ashi)");
}
