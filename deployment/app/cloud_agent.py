import os
import asyncio
import json
import logging
import warnings
import joblib
import numpy as np
import pandas as pd
import aiohttp
import websockets
import ssl
import traceback
from datetime import datetime
from fastapi import FastAPI
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

# Suppress sklearn feature name warnings (cosmetic only, column order is correct)
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

# === Configuration ===
SYMBOL = "BTC-USD"
GRANULARITY = 900  # 15 minutes
WS_URL = "wss://ws-feed.exchange.coinbase.com"
REST_URL = f"https://api.exchange.coinbase.com/products/{SYMBOL}/candles"
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
LOG_FILE = "agent.log"
POLL_INTERVAL_SEC = 30
HISTORY_LIMIT = 600  # Feed model 600 bars of context

# Telegram Config
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8450202456:AAE605CSV6eZiVSoNlcEVxlbEDHQsSrQo9E")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "8521249438")

# === Logging Setup ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# === Global State ===
global_agent = None

# === HTML Template ===
def get_dashboard_html(status, last_analysis, logs):
    # Determine status color
    status_color = "#4ade80" if status == "Active" else "#f87171"
    
    # Format logs for terminal view
    terminal_output = "".join(logs) if logs else "No logs available..."

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>HFT Cloud Agent</title>
        <style>
            :root {{
                --bg: #1a1b26;
                --card-bg: #24283b;
                --text: #a9b1d6;
                --accent: #7aa2f7;
                --success: #4ade80;
                --danger: #f87171;
                --border: #414868;
            }}
            body {{
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                background-color: var(--bg);
                color: var(--text);
                margin: 0;
                padding: 20px;
                line-height: 1.5;
            }}
            .container {{
                max-width: 1000px;
                margin: 0 auto;
            }}
            .header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 30px;
                padding-bottom: 20px;
                border-bottom: 1px solid var(--border);
            }}
            h1 {{ margin: 0; color: white; }}
            .status-badge {{
                background: {status_color}20;
                color: {status_color};
                padding: 5px 12px;
                border-radius: 20px;
                border: 1px solid {status_color};
                font-weight: 600;
            }}
            .grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            .card {{
                background: var(--card-bg);
                border-radius: 12px;
                padding: 20px;
                border: 1px solid var(--border);
            }}
            .card-title {{
                color: var(--accent);
                font-size: 0.9em;
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 15px;
                font-weight: 600;
            }}
            .stat-value {{
                font-size: 1.5em;
                color: white;
                font-weight: 700;
            }}
            .stat-sub {{
                font-size: 0.9em;
                color: #565f89;
                margin-top: 5px;
            }}
            .terminal {{
                background: #0f111a;
                border-radius: 8px;
                padding: 15px;
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.85em;
                color: #c0caf5;
                height: 400px;
                overflow-y: auto;
                white-space: pre-wrap;
                border: 1px solid var(--border);
            }}
            .btn {{
                background: var(--accent);
                color: #1a1b26;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: 600;
                cursor: pointer;
                transition: opacity 0.2s;
            }}
            .btn:hover {{ opacity: 0.9; }}
            .controls {{
                display: flex;
                gap: 10px;
                margin-top: 20px;
            }}
        </style>
        <script>
            // Auto-scroll terminal to bottom
            window.onload = function() {{
                var terminal = document.getElementById("terminal");
                terminal.scrollTop = terminal.scrollHeight;
            }};
        </script>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 HFT Cloud Agent</h1>
                <span class="status-badge">{status}</span>
            </div>

            <div class="grid">
                <div class="card">
                    <div class="card-title">Last Analysis</div>
                    <div class="stat-value">{last_analysis.get('signal', 'N/A')}</div>
                    <div class="stat-sub">
                        Time: {last_analysis.get('time', 'Waiting...')} <br>
                        Confidence: {last_analysis.get('conf', '0.0')}%
                    </div>
                </div>
                <div class="card">
                    <div class="card-title">Model Status</div>
                    <div class="stat-sub">
                        RF Vote: {last_analysis.get('rf', 'N/A')} <br>
                        XGB Vote: {last_analysis.get('xgb', 'N/A')} <br>
                        Symbol: {SYMBOL}
                    </div>
                </div>
            </div>

            <div class="card">
                <div class="card-title">Terminal Output</div>
                <div id="terminal" class="terminal">{terminal_output}</div>
                
                <div class="controls">
                    <form action="/analyze" method="post">
                        <button type="submit" class="btn">⚡ Force Analysis Now</button>
                    </form>
                    <button onclick="window.location.reload()" class="btn" style="background: var(--card-bg); color: white; border: 1px solid var(--border)">🔄 Refresh</button>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

# === FastAPI App ===
from fastapi.responses import HTMLResponse
from fastapi.requests import Request
from fastapi.responses import RedirectResponse

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def home():
    if not global_agent:
        return "<h1>Agent initializing... please refresh in a few seconds.</h1>"
    
    # Read logs
    logs = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r') as f:
            logs = f.readlines()[-100:]  # Last 100 lines

    status = "Active" if global_agent.active else "Paused"
    
    return get_dashboard_html(status, global_agent.last_analysis, logs)

@app.post("/analyze")
async def force_analyze():
    if global_agent:
        await global_agent.process_market_update(force=True)
    return RedirectResponse(url="/", status_code=303)

@app.get("/health")
def health_check():
    return {"status": "running", "connection": "websocket_active"}

# === Model Wrapper ===
class EnsembleModel:
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.loaded = False

    def load_models(self):
        logger.info("Loading models...")
        try:
            self.models['rf'] = joblib.load(os.path.join(MODEL_DIR, "randomforest_ha15m_trend_model.pkl"))
            self.scalers['rf'] = joblib.load(os.path.join(MODEL_DIR, "scaler_randomforest_ha15m.save"))
            self.models['xgb'] = joblib.load(os.path.join(MODEL_DIR, "xgboost_ha15m_trend_model.pkl"))
            self.scalers['xgb'] = joblib.load(os.path.join(MODEL_DIR, "scaler_xgboost_ha15m.save"))
            self.loaded = True
            logger.info("[+] Models loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load models: {e}")
            self.loaded = False

    def predict(self, features):
        if not self.loaded: return 0, 0.0, 0, 0
        try:
            # Define feature sets specific to each model
            # Both models appear to share the same 15-feature set found in XGB inspection
            feature_cols = [
                'HA_Open', 'HA_High', 'HA_Low', 'HA_Close',
                'HA_Body', 'HA_Range', 
                'Close_Change', 'Close_Pct_Change',
                'Volume', 'Volume_Change', 'Volume_MA', 
                'Cluster', 'Cluster_Density', 
                'HA_Up_Signal', 'HA_Down_Signal'
            ]
            
            rf_cols = feature_cols
            xgb_cols = feature_cols

            # Input `features` is now a dictionary of all potential features
            # Create DataFrames for each model using only their required columns
            df_rf = pd.DataFrame([features])[rf_cols]
            df_xgb = pd.DataFrame([features])[xgb_cols]
            
            # Predict RF - Use .values to silence feature name warnings
            X_rf = self.scalers['rf'].transform(df_rf.values)
            rf_pred = self.models['rf'].predict(X_rf)[0]
            rf_conf = np.max(self.models['rf'].predict_proba(X_rf))
            rf_vote = 1 if rf_pred == 1 else -1

            # Predict XGB - Use .values to silence feature name warnings
            X_xgb = self.scalers['xgb'].transform(df_xgb.values)
            xgb_pred = self.models['xgb'].predict(X_xgb)[0]
            xgb_conf = np.max(self.models['xgb'].predict_proba(X_xgb))
            xgb_vote = 1 if xgb_pred == 1 else -1

            if rf_vote == 1 and xgb_vote == 1: final_signal = 1
            elif rf_vote == -1 and xgb_vote == -1: final_signal = -1
            else: final_signal = 0

            avg_conf = (rf_conf + xgb_conf) / 2
            return final_signal, avg_conf, rf_vote, xgb_vote
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return 0, 0.0, 0, 0

# === Telegram Bot ===
class TelegramBot:
    def __init__(self):
        self.token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.valid = "YOUR_BOT" not in self.token and self.token is not None

    async def send_message(self, text, chat_id=None):
        if not self.valid: return
        target = chat_id if chat_id else self.chat_id
        payload = {"chat_id": target, "text": text, "parse_mode": "Markdown"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.base_url}/sendMessage", json=payload) as resp:
                    if resp.status != 200:
                        logger.error(f"Telegram error: {await resp.text()}")
        except Exception as e:
            logger.error(f"Telegram connect error: {e}")

    async def send_alert(self, signal, confidence, rf_vote, xgb_vote, timestamp):
        if signal == 1:
            header = "🔵 **BUY Trade Signal** 🔵"
        else:
            header = "🔴 **SELL Trade Signal** 🔴"

        msg = (
            f"{header}\n\n"
            f"**Symbol:** {SYMBOL}\n"
            f"**Time:** {timestamp}\n"
            f"**Confidence:** {confidence*100:.1f}%\n"
            f"**Models:** RF({rf_vote}) XGB({xgb_vote})"
        )
        await self.send_message(msg)

    async def poll_commands(self, command_handler):
        if not self.valid: return
        offset = 0
        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    params = {"offset": offset + 1, "timeout": 10}
                    async with session.get(f"{self.base_url}/getUpdates", params=params) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get("ok"):
                                for update in data.get("result", []):
                                    offset = update["update_id"]
                                    if "message" in update and "text" in update["message"]:
                                        text = update["message"]["text"].strip()
                                        cid = str(update["message"]["chat"]["id"])
                                        if TELEGRAM_CHAT_ID and cid != str(TELEGRAM_CHAT_ID): continue
                                        if text.startswith("/"):
                                            await command_handler(text, cid)
            except Exception as e:
                logger.error(f"Polling error: {e}")
                await asyncio.sleep(5)
            await asyncio.sleep(1)

    async def send_logs(self, chat_id):
        try:
            if not os.path.exists(LOG_FILE):
                await self.send_message("No logs found.", chat_id)
                return
            with open(LOG_FILE, 'r') as f:
                lines = f.readlines()[-20:]
            await self.send_message(f"📋 **Logs**:\n```\n{''.join(lines)}\n```", chat_id)
        except Exception as e:
            await self.send_message(f"Error fetching logs: {e}", chat_id)

# === Trading Agent ===
class TradingAgent:
    def __init__(self):
        self.ensemble = EnsembleModel()
        self.bot = TelegramBot()
        self.active = True
        self.last_analysis = {} # Store last analysis result
        self.last_signal = {"signal": None, "confidence": None} # For deduplication

    async def fetch_historical_candles(self):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(REST_URL, params={'granularity': GRANULARITY}) as resp:
                    if resp.status != 200: return None
                    data = await resp.json()
            
            df = pd.DataFrame(data, columns=['time', 'low', 'high', 'open', 'close', 'volume'])
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df = df.sort_values('time').reset_index(drop=True)
            df.rename(columns={'volume': 'Volume', 'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
            return df
        except Exception as e:
            logger.error(f"Error fetching candles: {e}")
            return None

    def calculate_features(self, df):
        if len(df) < 50: return None, None
        try:
            o, h, l, c = df['Open'].values, df['High'].values, df['Low'].values, df['Close'].values
            n = len(df)
            
            ha_open = np.zeros(n)
            ha_close = (o + h + l + c) / 4
            ha_open[0] = (o[0] + c[0]) / 2
            for i in range(1, n):
                ha_open[i] = (ha_open[i-1] + ha_close[i-1]) / 2
            
            ha_high = np.maximum(h, np.maximum(ha_open, ha_close))
            ha_low = np.minimum(l, np.minimum(ha_open, ha_close))
            
            df['HA_Open'] = ha_open
            df['HA_High'] = ha_high
            df['HA_Low'] = ha_low
            df['HA_Close'] = ha_close
            
            df['HA_Body'] = abs(df['HA_Close'] - df['HA_Open'])
            df['HA_Range'] = df['HA_High'] - df['HA_Low']
            # === 4. Feature Engineering Logic ===
            
            # --- Clustering Feature ---
            # Match trade_client.py logic: Use 4 HA columns + Scaling
            if len(df) >= 252:
                window_data = df.iloc[-252:].copy()
                cluster_features = ['HA_Open', 'HA_High', 'HA_Low', 'HA_Close']
                X_cluster = window_data[cluster_features].values
                
                # Scale data for K-Means (Crucial matches client)
                scaler_cluster = StandardScaler()
                X_scaled = scaler_cluster.fit_transform(X_cluster)
                
                kmeans = KMeans(n_clusters=3, n_init=3, max_iter=100, random_state=42)
                cluster_labels = kmeans.fit_predict(X_scaled)
                
                # Current cluster ID (0, 1, or 2)
                df.loc[df.index[-1], 'Cluster'] = int(cluster_labels[-1])
                
                # Density for XGBoost
                cluster_count = np.sum(cluster_labels == cluster_labels[-1])
                df.loc[df.index[-1], 'Cluster_Density'] = (cluster_count / 252.0) * 100
            else:
                df.loc[df.index[-1], 'Cluster'] = 0
                df.loc[df.index[-1], 'Cluster_Density'] = 50.0

            # --- Volume Features ---
            df['Volume_MA_5'] = df['Volume'].rolling(5).mean()
            df['Volume_Ratio'] = df['Volume'] / df['Volume_MA_5']
            df['Volume_Ratio'] = df['Volume_Ratio'].fillna(1.0)
            
            # Alias for XGBoost which expects "Volume_MA"
            df['Volume_MA'] = df['Volume_MA_5']
            df['Volume_Change'] = df['Volume'].pct_change()

            # --- Price Change Features ---
            # Based on logs: Close_Change, Close_Pct_Change
            df['Close_Change'] = df['HA_Close'].diff()
            df['Close_Pct_Change'] = df['HA_Close'].pct_change()

            # --- Signal Booleans ---
            # HA_Up_Signal (Green Candle), HA_Down_Signal (Red Candle)
            df['HA_Up_Signal'] = (df['HA_Close'] > df['HA_Open']).astype(int)
            df['HA_Down_Signal'] = (df['HA_Close'] < df['HA_Open']).astype(int)

            df.fillna(0, inplace=True)
            
            # Return the last row as a dictionary containing ALL calculated features
            # The predict() method will select what it needs
            last = df.iloc[-1].to_dict()
            return last, last['time']
        except Exception as e:
            logger.error(f"Feature Calc Error: {e}")
            return None, None

    async def process_market_update(self, force=False):
        if not self.active and not force: return

        df = await self.fetch_historical_candles()
        if df is None: return

        features, time_idx = self.calculate_features(df)
        if not features: return

        signal, conf, rf, xgb = self.ensemble.predict(features)
        
        # Update internal state for dashboard
        side = "BUY" if signal == 1 else ("SELL" if signal == -1 else "NEUTRAL")
        self.last_analysis = {
            "signal": side,
            "conf": round(conf * 100, 1),
            "rf": rf,
            "xgb": xgb,
            "time": str(time_idx)
        }

        if force:
            # Force mode: always report result
            side = "BUY" if signal == 1 else ("SELL" if signal == -1 else "NEUTRAL")
            await self.bot.send_message(
                f"🔎 **Force Analysis**\nTime: {time_idx}\nSignal: {side}\nConf: {conf:.2f}\nRF:{rf} XGB:{xgb}"
            )
        else:
            if signal != 0:
                # Deduplication: Only log if signal type OR confidence changed
                rounded_conf = round(conf, 4)  # Avoid floating point noise
                if (signal != self.last_signal["signal"] or 
                    rounded_conf != self.last_signal["confidence"]):
                    logger.info(f"Signal Detected: {signal} (Conf: {conf})")
                    await self.bot.send_alert(signal, conf, rf, xgb, time_idx)
                    # Update last signal
                    self.last_signal = {"signal": signal, "confidence": rounded_conf}

    async def handle_telegram_command(self, text, chat_id):
        cmd = text.lower().split()[0]
        if cmd == "/start":
            self.active = True
            await self.bot.send_message("✅ **Agent Started**", chat_id)
        elif cmd == "/stop":
            self.active = False
            await self.bot.send_message("🛑 **Agent Paused**", chat_id)
        elif cmd == "/force":
            await self.bot.send_message("🔄 **Forcing Analysis...**", chat_id)
            await self.process_market_update(force=True)
        elif cmd == "/logs":
            await self.bot.send_logs(chat_id)
        elif cmd == "/status":
            state = "Active 🟢" if self.active else "Paused 🔴"
            await self.bot.send_message(f"ℹ **Status**: {state}\n**Symbol**: {SYMBOL}", chat_id)
        elif cmd == "/help":
            await self.bot.send_message(
                "🤖 **Commands**:\n/start - Resume\n/stop - Pause\n/force - Analyze now\n/status - Status\n/logs - Logs", chat_id
            )

    async def ws_handler(self):
        ssl_context = ssl.create_default_context()
        while True:
            try:
                logger.info(f"Connecting to {WS_URL}...")
                async with websockets.connect(WS_URL, ssl=ssl_context, ping_interval=20, ping_timeout=20) as ws:
                    await ws.send(json.dumps({"type": "subscribe", "product_ids": [SYMBOL], "channels": ["ticker"]}))
                    logger.info("[+] Subscribed to ticker")
                    if self.bot.valid:
                        await self.bot.send_message("⚡ **WebSocket Connected**")
                    async for _ in ws:
                        pass
            except Exception as e:
                # DETAILED LOGGING HERE
                error_trace = traceback.format_exc()
                logger.error(f"WebSocket Error: {e}\n{error_trace}")
                await asyncio.sleep(5)

    async def analysis_loop(self):
        while True:
            await self.process_market_update()
            await asyncio.sleep(POLL_INTERVAL_SEC)

    async def start(self):
        self.ensemble.load_models()
        await asyncio.gather(
            self.ws_handler(),
            self.bot.poll_commands(self.handle_telegram_command),
            self.analysis_loop()
        )

@app.on_event("startup")
async def startup_event():
    global global_agent
    global_agent = TradingAgent()
    asyncio.create_task(global_agent.start())

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    # reload=False ensures startup event fires properly
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)
