#!/usr/bin/env python3
"""
HYPE prediction system configuration.
"""

import os

# Base directory - use relative path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Paths
DB_PATH = os.path.join(BASE_DIR, "hype", "hype_prices.db")
MODEL_DIR = os.path.join(BASE_DIR, "hype", "models")

# API Settings
SYMBOL = "HYPE"
PREDICTION_HORIZONS = [5, 10, 15]  # minutes
COLLECTION_INTERVAL = 6  # seconds

# Model Settings
MIN_TRAIN_POINTS = 60
RETRAIN_EVERY_N_POINTS = 10000

# API Server
API_HOST = "0.0.0.0"
API_PORT = 5000  # shared unified API

# Create directories
os.makedirs(MODEL_DIR, exist_ok=True)
