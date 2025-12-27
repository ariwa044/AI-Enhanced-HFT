# Deployment Walkthrough

This guide details how to deploy your AI Trading Bot using Docker and how to connect your local MetaTrader 5 client.

## 1. Local Testing (Optional)

You can test the server locally before using Docker.

### Start the Server
```bash
uvicorn deployment.app.main:app --reload --port 8000
```

### Test the Endpoint
```bash
python deployment/test_server_local.py
```

## 2. Docker Deployment

### Build Image
**Important:** Run this from the project root, pointing to the `deployment/` directory.
```bash
docker build -t hft-trading-bot deployment/
```

### Run Container
```bash
docker run -p 8000:8000 hft-trading-bot
```

### Verify Docker Container
While the container is running, open a new terminal and run:
```bash
python deployment/test_server_local.py
```
You should see a successful JSON response:
```json
{
  "signal": 1,
  "confidence": 1.0, 
  ...
}
```

## 3. Deploy to Render (Cloud)

1.  Push your code to a GitHub repository.
2.  Log in to [Render](https://render.com/).
3.  Click "New +" -> "Web Service".
4.  Connect your GitHub repository.
5.  Select **Docker** as the Runtime.
6.  **Root Directory**: Set this to `deployment`.
    *   *This is critical so Render finds the Dockerfile correctly.*
7.  Click "Create Web Service".
8.  Once deployed, copy your **Service URL**.

## 4. Client Setup (Windows PC with MT5)

1.  Copy `client/trade_client.py` to your Windows machine.
2.  Install Python dependencies on Windows:
    ```bash
    pip install MetaTrader5 pandas numpy requests scikit-learn
    ```
3.  Open `client/trade_client.py` and update the `API_URL` (I have already done this for you):
    ```python
    API_URL = "https://ai-main-ai-92945097390.europe-west2.run.app/predict"
    ```
4.  Open MetaTrader 5 and ensure "Algo Trading" is enabled.
5.  Run the client:
    ```bash
    python trade_client.py
    ```

## 5. Verification Checklist

- [x] **Server**: Docker container starts and loads models (`✓ Random Forest loaded`, `✓ XGBoost loaded`).
- [x] **Server**: `/` endpoint is accessible (HTTP 200 OK).
- [ ] **Server**: `/predict` endpoint returns valid signals (Run `test_server_local.py` against Docker).
- [ ] **Client**: Connects to MT5 and receives live predictions.
