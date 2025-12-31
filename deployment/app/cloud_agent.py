import os
import asyncio
import json
import logging
import joblib
import numpy as np
import pandas as pd
import aiohttp
import websockets
import ssl
from datetime import datetime
from fastapi import FastAPI
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

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

# === FastAPI App ===
app = FastAPI()

@app.get("/")
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
            features = np.array(features).reshape(1, -1)
            
            X_rf = self.scalers['rf'].transform(features)
            rf_pred = self.models['rf'].predict(X_rf)[0]
            rf_conf = np.max(self.models['rf'].predict_proba(X_rf))
            rf_vote = 1 if rf_pred == 1 else -1

            X_xgb = self.scalers['xgb'].transform(features)
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
            df['HA_Close_Change'] = df['HA_Close'].pct_change()
            df['HA_Momentum'] = df['HA_Close'] - df['HA_Close'].shift(5)
            df['HA_Volatility'] = df['HA_Range'].rolling(5).std()
            df['Cluster_Density'] = 50.0 
            
            up, down = 0, 0
            ha_c = df['HA_Close'].values
            cons_up, cons_down = np.zeros(n), np.zeros(n)
            for i in range(1, n):
                if ha_c[i] > ha_c[i-1]: up, down = up+1, 0
                elif ha_c[i] < ha_c[i-1]: down, up = down+1, 0
                else: up, down = 0, 0
                cons_up[i], cons_down[i] = up, down
            
            df['Consecutive_Up'] = cons_up
            df['Consecutive_Down'] = cons_down
            df['Volume_Change'] = df['Volume'].pct_change()
            df['Volume_Ratio'] = 1.0
            df.fillna(0, inplace=True)
            
            feat_cols = [
                'HA_Open', 'HA_High', 'HA_Low', 'HA_Close',
                'HA_Body', 'HA_Range', 'HA_Close_Change',
                'HA_Momentum', 'HA_Volatility', 'Cluster_Density',
                'Consecutive_Up', 'Consecutive_Down',
                'Volume', 'Volume_Change', 'Volume_Ratio'
            ]
            last = df.iloc[-1]
            return [float(last[c]) for c in feat_cols], last['time']
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

        if force:
            # Force mode: always report result
            side = "BUY" if signal == 1 else ("SELL" if signal == -1 else "NEUTRAL")
            await self.bot.send_message(
                f"🔎 **Force Analysis**\nTime: {time_idx}\nSignal: {side}\nConf: {conf:.2f}\nRF:{rf} XGB:{xgb}"
            )
        else:
            if signal != 0:
                logger.info(f"Signal Detected: {signal} (Conf: {conf})")
                await self.bot.send_alert(signal, conf, rf, xgb, time_idx)

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
                logger.error(f"WebSocket error: {e}")
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
    agent = TradingAgent()
    asyncio.create_task(agent.start())

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
