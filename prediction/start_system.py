#!/usr/bin/env python3
"""
Start all prediction system components automatically.
"""

import subprocess
import sys
import os
import time
import signal
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("System-Launcher")

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Use the project virtual environment
VENV_PYTHON = os.path.join(BASE_DIR, ".venv", "bin", "python")
if not os.path.exists(VENV_PYTHON):
    VENV_PYTHON = sys.executable
    logger.warning(f"Virtual environment not found, using {VENV_PYTHON}")

# Track processes
processes = []


def signal_handler(sig, frame):
    """Handle shutdown signals."""
    logger.info("Shutting down all components...")
    for proc in processes:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except:
            try:
                proc.kill()
            except:
                pass
    logger.info("All components stopped")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def start_component(name, script_path, wait_time=2):
    """Start a system component."""
    logger.info(f"Starting {name}...")
    
    try:
        # Use python from virtual environment
        python_exe = VENV_PYTHON
        
        proc = subprocess.Popen(
            [python_exe, script_path],
            cwd=BASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
        )
        
        processes.append(proc)
        logger.info(f"  {name} started (PID: {proc.pid})")
        time.sleep(wait_time)  # Wait for component to initialize
        return True
        
    except Exception as e:
        logger.error(f"  Failed to start {name}: {e}")
        return False


def check_data_available():
    """Check if there's enough data for training."""
    import sqlite3
    
    btc_db = os.path.join(BASE_DIR, "bitcoin", "bitcoin_prices.db")
    bnb_db = os.path.join(BASE_DIR, "bnb", "bnb_prices.db")
    
    btc_count = 0
    bnb_count = 0
    
    if os.path.exists(btc_db):
        try:
            conn = sqlite3.connect(btc_db)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM prices")
            btc_count = c.fetchone()[0]
            conn.close()
        except:
            pass
    
    if os.path.exists(bnb_db):
        try:
            conn = sqlite3.connect(bnb_db)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM prices")
            bnb_count = c.fetchone()[0]
            conn.close()
        except:
            pass
    
    return btc_count, bnb_count


def train_models_if_needed():
    """Train models if data is available."""
    btc_count, bnb_count = check_data_available()
    
    logger.info(f"Data status - Bitcoin: {btc_count} points, BNB: {bnb_count} points")
    
    # Train Bitcoin model if enough data
    if btc_count >= 1800:
        logger.info("Training Bitcoin model...")
        try:
            result = subprocess.run(
                [VENV_PYTHON, os.path.join(BASE_DIR, "bitcoin", "model.py")],
                cwd=BASE_DIR,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            if result.returncode == 0:
                logger.info("  Bitcoin model trained successfully")
            else:
                logger.warning(f"  Bitcoin model training issues: {result.stderr}")
        except Exception as e:
            logger.error(f"  Bitcoin model training failed: {e}")
    else:
        logger.warning(f"  Bitcoin needs {1800 - btc_count} more data points for training")
    
    # Train BNB model if enough data
    if bnb_count >= 800:
        logger.info("Training BNB model...")
        try:
            result = subprocess.run(
                [VENV_PYTHON, os.path.join(BASE_DIR, "bnb", "model.py")],
                cwd=BASE_DIR,
                capture_output=True,
                text=True,
                timeout=300
            )
            if result.returncode == 0:
                logger.info("  BNB model trained successfully")
            else:
                logger.warning(f"  BNB model training issues: {result.stderr}")
        except Exception as e:
            logger.error(f"  BNB model training failed: {e}")
    else:
        logger.warning(f"  BNB needs {800 - bnb_count} more data points for training")


def main():
    """Start all system components."""
    print("=" * 60)
    print("STARTING CRYPTOCURRENCY PREDICTION SYSTEM")
    print("=" * 60)
    
    # Step 1: Train models if data is available
    print("\n[1/4] Checking and training models...")
    train_models_if_needed()
    
    # Step 2: Start data collectors
    print("\n[2/4] Starting data collectors...")
    start_component("Bitcoin Collector", os.path.join(BASE_DIR, "bitcoin", "collector.py"))
    start_component("BNB Collector", os.path.join(BASE_DIR, "bnb", "collector.py"))
    
    # Step 3: Start APIs
    print("\n[3/4] Starting prediction APIs...")
    start_component("Bitcoin API", os.path.join(BASE_DIR, "bitcoin", "api.py"))
    start_component("BNB API", os.path.join(BASE_DIR, "bnb", "api.py"))
    
    # Wait for APIs to be ready
    print("\n  Waiting for APIs to initialize...")
    time.sleep(5)
    
    # Step 4: Start prediction generators
    print("\n[4/4] Starting automatic prediction generators...")
    start_component("Bitcoin Generator (15min)", os.path.join(BASE_DIR, "bitcoin", "generate_predictions.py"))
    start_component("BNB Generator (5min)", os.path.join(BASE_DIR, "bnb", "generate_predictions.py"))
    
    # Summary
    print("\n" + "=" * 60)
    print("SYSTEM STARTED SUCCESSFULLY!")
    print("=" * 60)
    print("\nComponents running:")
    print("  - Data collectors: Collecting prices every 5 seconds")
    print("  - Prediction APIs: Ready on ports 5001 (BTC) and 5002 (BNB)")
    print("  - Auto-predictions:")
    print("    * Bitcoin: Every 15 minutes")
    print("    * BNB: Every 5 minutes")
    print("\nPress Ctrl+C to stop all components")
    print("=" * 60)
    
    # Keep main process running
    try:
        while True:
            # Check if any process died
            for proc in processes:
                if proc.poll() is not None:
                    logger.warning(f"Process {proc.pid} exited with code {proc.returncode}")
            time.sleep(5)
    except KeyboardInterrupt:
        signal_handler(None, None)


if __name__ == "__main__":
    main()
