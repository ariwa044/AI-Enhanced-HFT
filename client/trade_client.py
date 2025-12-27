import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import sys

# === Configuration ===
API_URL = "http://localhost:8000/predict"  # Change to Render URL in production
SYMBOL = "BTCUSD"
TIMEFRAME = mt5.TIMEFRAME_M15
LOOKBACK_BARS = 1000  # Increased to 1000 for better stability of MA/Volatility calculations

# === Risk Management ===
RISK_PARAMS = {
    "STOP_LOSS_PIPS": 100,
    "TAKE_PROFIT_PIPS": 300,
    "RISK_PERCENT": 2.0,   # Risk 2% of equity per trade
    "MAX_LOT_SIZE": 1.0,
    "MIN_LOT_SIZE": 0.01,
    "MAGIC_NUMBER": 123456,
    "MIN_HOLDING_BARS": 10,   # Minimum bars to hold (approx 2.5h on M15)
    "MAX_DAILY_TRADES": 6     # Max trades per day
}

# State Tracking
daily_trade_state = {
    "count": 0,
    "date": datetime.now().date()
}

def check_daily_limit_reset():
    """Reset daily counter if day changed"""
    today = datetime.now().date()
    if daily_trade_state["date"] != today:
        daily_trade_state["count"] = 0
        daily_trade_state["date"] = today
        print("New day: Reset daily trade count.")

def calculate_lot_size(sl_pips):
    account_info = mt5.account_info()
    if account_info is None:
        return RISK_PARAMS["MIN_LOT_SIZE"]
    
    balance = account_info.equity
    risk_amount = balance * (RISK_PARAMS["RISK_PERCENT"] / 100.0)
    
    symbol_info = mt5.symbol_info(SYMBOL)
    if not symbol_info:
        return RISK_PARAMS["MIN_LOT_SIZE"]
        
    contract_size = symbol_info.trade_contract_size
    price_change_for_sl = sl_pips * 0.01 # Assuming 1 pip = 0.01 (Check your broker!)
    
    loss_per_lot = price_change_for_sl * contract_size
    
    if loss_per_lot == 0:
        lot_size = RISK_PARAMS["MIN_LOT_SIZE"]
    else:
        lot_size = risk_amount / loss_per_lot
        
    lot_size = max(RISK_PARAMS["MIN_LOT_SIZE"], min(lot_size, RISK_PARAMS["MAX_LOT_SIZE"]))
    
    step = symbol_info.volume_step
    lot_size = round(lot_size / step) * step
    
    return float(lot_size)

def execute_trade(signal, confidence):
    check_daily_limit_reset()
    
    # Check existing positions
    all_positions = mt5.positions_get(symbol=SYMBOL)
    
    # Filter by Magic Number to ensure we only manage OUR trades
    positions = [p for p in all_positions if p.magic == RISK_PARAMS["MAGIC_NUMBER"]] if all_positions else []
    
    current_direction = 0 # 0 flat, 1 buy, -1 sell
    current_pos = None
    
    if positions and len(positions) > 0:
        current_pos = positions[0]
        if current_pos.type == mt5.ORDER_TYPE_BUY:
            current_direction = 1
        elif current_pos.type == mt5.ORDER_TYPE_SELL:
            current_direction = -1
            
    if signal == 0:
        return # Neutral
        
    if signal == current_direction:
        print(f"Creating/Holding position matching signal {signal}")
        return
        
    # --- Close Logic (with Min Holding check) ---
    if current_direction != 0:
        # Check Min Holding Bars
        # Time difference in seconds
        duration_sec = time.time() - current_pos.time
        bars_held = duration_sec / (15 * 60) # M15 = 900 seconds
        
        if bars_held < RISK_PARAMS["MIN_HOLDING_BARS"]:
            print(f"Signal flip, but holding: {bars_held:.1f}/{RISK_PARAMS['MIN_HOLDING_BARS']} bars.")
            return

        print("Closing opposite position...")
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": current_pos.ticket,
            "symbol": SYMBOL,
            "volume": current_pos.volume,
            "type": mt5.ORDER_TYPE_SELL if current_direction == 1 else mt5.ORDER_TYPE_BUY,
            "price": mt5.symbol_info_tick(SYMBOL).bid if current_direction == 1 else mt5.symbol_info_tick(SYMBOL).ask,
            "magic": RISK_PARAMS["MAGIC_NUMBER"],
            "comment": "AI Close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"Close failed: {result.comment}")
            return
        else:
            print("Position closed. Ready to reverse.")
            # Wait a tick?
            time.sleep(1)

    # --- Open Logic (with Max Daily Trades check) ---
    if daily_trade_state["count"] >= RISK_PARAMS["MAX_DAILY_TRADES"]:
        print(f"Daily trade limit reached ({daily_trade_state['count']}/{RISK_PARAMS['MAX_DAILY_TRADES']}). Skipping.")
        return

    lot_size = calculate_lot_size(RISK_PARAMS["STOP_LOSS_PIPS"])
    point = mt5.symbol_info(SYMBOL).point
    price = mt5.symbol_info_tick(SYMBOL).ask if signal == 1 else mt5.symbol_info_tick(SYMBOL).bid
    
    sl_points = RISK_PARAMS["STOP_LOSS_PIPS"] * 0.01 
    tp_points = RISK_PARAMS["TAKE_PROFIT_PIPS"] * 0.01
    
    sl = price - sl_points if signal == 1 else price + sl_points
    tp = price + tp_points if signal == 1 else price - tp_points
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": lot_size,
        "type": mt5.ORDER_TYPE_BUY if signal == 1 else mt5.ORDER_TYPE_SELL,
        "price": price,
        "sl": sl,
        "tp": tp,
        "magic": RISK_PARAMS["MAGIC_NUMBER"],
        "comment": f"AI Trade Conf:{confidence:.2f}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    result = mt5.order_send(request)
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"Open Trade Result: {result.comment}")
        daily_trade_state["count"] += 1
    else:
        print(f"Open Trade Failed: {result.comment}")


def run_bot():
    initialize_mt5()
    print("Bot Started. Waiting for next candle...")
    
    while True:
        try:
            # Sleep loop to wait for candle close? 
            # For HFT/M15, we check every minute? 
            # Or just run once per loop with a sleep
            
            df = get_data()
            if df is not None:
                features = calculate_heiken_ashi_and_features(df)
                if features:
                    print(f"Features: {features[:3]}...")
                    result = get_prediction(features)
                    
                    if result:
                        print(f"Signal: {result['signal']} ({result['confidence']:.2f})")
                        execute_trade(result['signal'], result['confidence'])
            
            time.sleep(60) # check every minute
            
        except KeyboardInterrupt:
            mt5.shutdown()
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    run_bot()
