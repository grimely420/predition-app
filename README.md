# Prediction App

Multi-coin cryptocurrency price prediction system using ensemble ML models. Supports Bitcoin (BTC), BNB, and HYPE with real-time price collection, feature engineering, XGBoost/ARIMA/Trend ensemble predictions, and automated model retraining.

## Architecture

```
predition-app/
├── prediction/               # Core prediction system
│   ├── shared/              # Shared modules (feature engine, models, API, etc.)
│   ├── bitcoin/             # BTC-specific config, collector, engine
│   ├── bnb/                 # BNB-specific config, collector, engine
│   ├── hype/               # HYPE-specific config, collector, engine
│   ├── services/            # Systemd service files & predictor loop
│   ├── start_all.py         # Unified launcher for all coins
│   └── logs/                # Service logs
├── start_all.sh             # Entry point (delegates to prediction/start_all.py)
├── start_system.py          # Alternative Python launcher
├── stop_all.sh              # Stop all services
├── status.sh                # System status check
└── requirements.txt         # Python dependencies
```

## Setup

### Prerequisites

- Python 3.10+
- pip

### Installation

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Running

### Quick Start (Recommended)

```bash
./start_all.sh
```

This starts all components:
- Price collectors for BTC, BNB, HYPE
- Unified prediction API on port 5000
- Predictor loops generating predictions every 5/10/15 minutes
- Auto-retrain daemons

### Alternative Launchers

```bash
# Python launcher
python3 start_system.py

# Individual coin (standalone mode)
cd prediction
python3 -m bitcoin.btc_predictor_loop
python3 -m bnb.bnb_predictor_loop
python3 -m hype.hype_predictor_loop
```

### Stopping

```bash
./stop_all.sh
```

### Status Check

```bash
./status.sh
```

## API Endpoints

### Unified API (port 5000)

| Endpoint | Description |
|----------|-------------|
| `GET /health` | System health check |
| `GET /<coin>/predict` | Get prediction for a coin (btc, bnb, hype) |
| `GET /<coin>/price` | Current price |

### Per-Coin APIs

| Service | Port | Endpoints |
|---------|------|-----------|
| BTC API | 5001 | `/predict`, `/health`, `/current_price`, `/accuracy_summary`, `/recent_predictions` |
| BNB API | 5002 | `/predict`, `/health`, `/current_price`, `/accuracy_summary`, `/recent_predictions` |
| HYPE API | 5003 | `/predict`, `/health`, `/current_price`, `/accuracy_summary`, `/recent_predictions` |

## Configuration

Each coin has its own configuration in `prediction/<coin>/<coin>_config.py`:

| Parameter | BTC | BNB | HYPE |
|-----------|-----|-----|------|
| Primary Horizon | 15 min | 5 min | 5 min |
| Collection Interval | 5 sec | 5 sec | 6 sec |
| Min Training Points | 1800 | 800 | 60 |
| Retrain Threshold | 10000 | 5000 | 10000 |
| API Port | 5001 | 5002 | 5003 |

## Systemd Services (Production)

For production deployments using systemd:

```bash
cd prediction/services
sudo ./install_services.sh
```

This installs:
- `prediction-api.service` - Unified API
- `prediction-collector@{btc,bnb,hype}.service` - Price collectors
- `prediction-predictor@{btc,bnb,hype}.service` - Predictor loops

## Model Training

Models auto-retrain when sufficient new data is collected. For manual training:

```bash
cd prediction

# Basic XGBoost model
python3 bitcoin/model.py
python3 bnb/model.py
python3 hype/model.py

# Advanced ensemble (XGBoost + regime detection)
python3 bitcoin/btc_model_advanced.py
python3 bnb/bnb_model_advanced.py
python3 hype/hype_model_advanced.py
```

## Logs

Logs are stored in `prediction/logs/`:
- `{coin}-collector.log` - Price collection logs
- `{coin}-predictor-loop.log` - Prediction generation logs
- `{coin}-api.log` - API request logs
- `{coin}-autoretrain.log` - Model retraining logs

## License

See [LICENSE](LICENSE) file.
