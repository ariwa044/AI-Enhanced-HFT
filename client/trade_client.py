import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import requests
import asyncio
import websockets
import json
import time
from datetime import datetime
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import sys
import logging

# === Configuration ===
WS_URL = "wss://ai-main-ai-92945097390.europe-west2.run.app/ws" # Production
#WS_URL = "ws://localhost:8080/ws" # Local Testing
SYMBOL = "BTCUSDm"
TIMEFRAME = mt5.TIMEFRAME_M15
LOOKBACK_BARS = 1000  # Increased to 1000 for better stability of MA/Volatility calculations

# === Logging Setup ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trade_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# === Risk Management ===
RISK_PARAMS = {
    "STOP_LOSS_PIPS": 100,
    "TAKE_PROFIT_PIPS": 300,
    "RISK_PERCENT": 2.0,   # Risk 2% of equity per trade
    "MAX_LOT_SIZE": 1.0,
    "MIN_LOT_SIZE": 0.01,
    "MAGIC_NUMBER": 123456,
    "MIN_HOLDING_BARS": 10,   # Minimum bars to hold (approx 2.5h on M15)
    "MAX_DAILY_TRADES": 6,    # Max trades per day
    # Credentials (0 = use current terminal)
    "MT5_LOGIN": 297647959,           
    "MT5_PASSWORD": "Arinze123.",
    "MT5_SERVER": "Exness-MT5Trial9" 
}

def initialize_mt5():
    if not mt5.initialize():
        logger.error(f"initialize() failed, error code = {mt5.last_error()}")
        sys.exit(1)
        
    # Attempt login if credentials provided
    if RISK_PARAMS["MT5_LOGIN"] != 0:
        authorized = mt5.login(
            login=RISK_PARAMS["MT5_LOGIN"], 
            password=RISK_PARAMS["MT5_PASSWORD"], 
            server=RISK_PARAMS["MT5_SERVER"]
        )
        if authorized:
            logger.info(f"Logged in to account #{RISK_PARAMS['MT5_LOGIN']}")
            
            # Print account balance
            account_info = mt5.account_info()
            if account_info:
                logger.info(f"Account Balance: {account_info.balance:.2f} {account_info.currency}")
                logger.info(f"Account Equity: {account_info.equity:.2f} {account_info.currency}")
                logger.info(f"Free Margin: {account_info.margin_free:.2f} {account_info.currency}")
        else:
            logger.error(f"Failed to login to account #{RISK_PARAMS['MT5_LOGIN']}, error code: {mt5.last_error()}")
            sys.exit(1)
            
    logger.info(f"MT5 Initialized. Connected to {mt5.terminal_info().name}")



def get_data():
    rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, LOOKBACK_BARS)
    if rates is None:
        logger.error(f"Failed to get rates. Error: {mt5.last_error()}")
        return None
    
    df = pd.DataFrame(rates)
    logger.info(f"Retrieved {len(df)} bars for {SYMBOL}")
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    # Rename for consistency
    df.rename(columns={'tick_volume': 'Volume', 'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
    return df

def calculate_heiken_ashi_and_features(df):
    logger.debug("Calculating Heiken Ashi candles...")
    # 1. Heiken Ashi Calculation
    ha_open = np.zeros(len(df))
    ha_close = np.zeros(len(df))
    ha_high = np.zeros(len(df))
    ha_low = np.zeros(len(df))
    
    # First bar
    ha_open[0] = (df['Open'].iloc[0] + df['Close'].iloc[0]) / 2
    ha_close[0] = (df['Open'].iloc[0] + df['High'].iloc[0] + df['Low'].iloc[0] + df['Close'].iloc[0]) / 4
    ha_high[0] = max(df['High'].iloc[0], ha_open[0], ha_close[0])
    ha_low[0] = min(df['Low'].iloc[0], ha_open[0], ha_close[0])
    
    # Subsequent
    for i in range(1, len(df)):
        ha_close[i] = (df['Open'].iloc[i] + df['High'].iloc[i] + df['Low'].iloc[i] + df['Close'].iloc[i]) / 4
        ha_open[i] = (ha_open[i-1] + ha_close[i-1]) / 2
        ha_high[i] = max(df['High'].iloc[i], ha_open[i], ha_close[i])
        ha_low[i] = min(df['Low'].iloc[i], ha_open[i], ha_close[i])
        
    df['HA_Open'] = ha_open
    df['HA_High'] = ha_high
    df['HA_Low'] = ha_low
    df['HA_Close'] = ha_close
    logger.debug("Heiken Ashi calculations complete.")
    
    # 2. HA Metrics
    df['HA_Body'] = abs(df['HA_Close'] - df['HA_Open'])
    df['HA_Range'] = df['HA_High'] - df['HA_Low']
    df['HA_Close_Change'] = df['HA_Close'].pct_change()
    df['HA_Momentum'] = df['HA_Close'] - df['HA_Close'].shift(5) # 5-bar momentum
    df['HA_Volatility'] = df['HA_Range'].rolling(5).std()
    
    # 3. K-Means Cluster Density (Last Bar Only needed, but requires window)
    logger.debug("Calculating Rolling K-Means...")
    window = 252
    if len(df) < window + 1:
        logger.warning("Not enough data for K-Means")
        return None
        
    # We only need the feature for the LAST closed bar (row -1)
    # Features used for clustering: HA_Open, HA_High, HA_Low, HA_Close
    cluster_features = ['HA_Open', 'HA_High', 'HA_Low', 'HA_Close']
    
    # Get window for the last point
    X = df[cluster_features].iloc[-window:].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=3)
    clusters = kmeans.fit_predict(X_scaled)
    
    current_cluster = clusters[-1]
    cluster_count = np.sum(clusters == current_cluster)
    density = (cluster_count / window) * 100
    
    df['Cluster_Density'] = 0.5 # Default
    df.iloc[-1, df.columns.get_loc('Cluster_Density')] = density
    logger.info(f"K-Means: Cluster {current_cluster}, Density {density:.2f}%")
    
    # 4. Patterns
    df['Consecutive_Up'] = 0
    df['Consecutive_Down'] = 0
    up_count = 0
    down_count = 0
    
    for i in range(1, len(df)):
        if df['HA_Close'].iloc[i] > df['HA_Close'].iloc[i-1]:
            up_count += 1
            down_count = 0
        elif df['HA_Close'].iloc[i] < df['HA_Close'].iloc[i-1]:
            down_count += 1
            up_count = 0
        else:
            up_count = 0
            down_count = 0
        
        df.iloc[i, df.columns.get_loc('Consecutive_Up')] = up_count
        df.iloc[i, df.columns.get_loc('Consecutive_Down')] = down_count

    # 5. Volume
    df['Volume_Change'] = df['Volume'].pct_change()
    df['Volume_MA_5'] = df['Volume'].rolling(5).mean()
    df['Volume_Ratio'] = df['Volume'] / df['Volume_MA_5']
    
    # Replace NaNs
    df.fillna(0, inplace=True)
    
    # Extract feature vector for the last bar
    # Use -1 (live bar) or -2 (last closed bar)? 
    # Usually models trained on closed bars -> use -2? 
    # Or if fetching current incomplete bar -> -1. 
    # Let's assume prediction is for NEXT movement based on logic.
    # We will use the last available row.
    last_row = df.iloc[-1]
    
    feature_columns = [
        'HA_Open', 'HA_High', 'HA_Low', 'HA_Close',
        'HA_Body', 'HA_Range', 'HA_Close_Change',
        'HA_Momentum', 'HA_Volatility',
        'Cluster_Density',
        'Consecutive_Up', 'Consecutive_Down',
        'Volume', 'Volume_Change', 'Volume_Ratio'
    ]
    
    return [float(last_row[col]) for col in feature_columns]

def get_prediction(features):
    try:
        response = requests.post(API_URL, json={"features": features}, timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            logger.warning(f"API Error: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Connection Error: {e}")
        return None

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
        logger.info("New day: Reset daily trade count.")

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
        logger.debug(f"Creating/Holding position matching signal {signal}")
        return
        
    # --- Close Logic (with Min Holding check) ---
    if current_direction != 0:
        # Check Min Holding Bars
        # Time difference in seconds
        duration_sec = time.time() - current_pos.time
        bars_held = duration_sec / (15 * 60) # M15 = 900 seconds
        
        if bars_held < RISK_PARAMS["MIN_HOLDING_BARS"]:
            logger.info(f"Signal flip, but holding: {bars_held:.1f}/{RISK_PARAMS['MIN_HOLDING_BARS']} bars.")
            return

        logger.info("Closing opposite position...")
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
            logger.error(f"Close failed: {result.comment}")
            return
        else:
            logger.info("Position closed. Ready to reverse.")
            # Wait a tick?
            time.sleep(1)

    # --- Open Logic (with Max Daily Trades check) ---
    if daily_trade_state["count"] >= RISK_PARAMS["MAX_DAILY_TRADES"]:
        logger.warning(f"Daily trade limit reached ({daily_trade_state['count']}/{RISK_PARAMS['MAX_DAILY_TRADES']}). Skipping.")
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
        logger.info(f"Open Trade Result: {result.comment}")
        daily_trade_state["count"] += 1
    else:
        logger.error(f"Open Trade Failed: {result.comment}")



# ... imports and config already at top ...

async def get_prediction(websocket, features):
    try:
        await websocket.send(json.dumps({"features": features}))
        response = await websocket.recv()
        return json.loads(response)
    except Exception as e:
        logger.error(f"WebSocket Error: {e}")
        return None

async def main_loop():
    initialize_mt5()
    logger.info("Bot Started. connecting to WebSocket...")
    
    while True:
        try:
            async with websockets.connect(WS_URL) as websocket:
                logger.info("Connected to Prediction Server")
                
                while True:
                    # High Frequency Loop? Or Candle Close?
                    # For now, stick to 1-minute loop or wait for next candle
                    
                    df = get_data()
                    if df is not None:
                        features = calculate_heiken_ashi_and_features(df)
                        if features:
                            logger.debug(f"Features: {features[:3]}...")
                            
                            # Async Prediction
                            result = await get_prediction(websocket, features)
                            
                            if result:
                                if "error" in result:
                                    logger.error(f"Server Error: {result['error']}")
                                else:
                                    logger.info(f"Signal: {result['signal']} ({result['confidence']:.2f})")
                                    execute_trade(result['signal'], result['confidence']) # Keep synchronous for now as MT5 is sync
                    
                    await asyncio.sleep(60)
                    
        except (websockets.ConnectionClosed, ConnectionRefusedError) as e:
            logger.error(f"Connection lost/refused: {e}. Retrying in 3s...")
            await asyncio.sleep(3)
        except KeyboardInterrupt:
            logger.info("Bot shutting down...")
            mt5.shutdown()
            break
        except Exception as e:
            logger.error(f"Unexpected Error: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        pass
