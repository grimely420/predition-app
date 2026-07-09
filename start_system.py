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
    
    btc_db = os.path.join(BASE_DIR, "prediction", "bitcoin", "bitcoin_prices.db")
    bnb_db = os.path.join(BASE_DIR, "prediction", "bnb", "bnb_prices.db")
    
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
                [VENV_PYTHON, os.path.join(BASE_DIR, "prediction", "bitcoin", "model.py")],
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
                [VENV_PYTHON, os.path.join(BASE_DIR, "prediction", "bnb", "model.py")],
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
    """Start the unified multi-horizon prediction system."""
    print("=" * 60)
    print("STARTING MULTI-HORIZON PREDICTION SYSTEM")
    print("=" * 60)
    print("Coins: BTC, BNB, HYPE")
    print("Horizons: 5, 10, 15 minutes")
    print("=" * 60)

    script = os.path.join(BASE_DIR, "prediction", "start_all.py")
    logger.info(f"Starting unified launcher: {script}")

    proc = subprocess.Popen(
        [VENV_PYTHON, script],
        cwd=BASE_DIR,
        stdout=None,
        stderr=None,
        start_new_session=True,
    )
    processes.append(proc)

    print(f"Unified launcher started (PID: {proc.pid})")
    print("API: http://localhost:5000")
    print("Logs: logs/")
    print("Press Ctrl+C to stop all components")
    print("=" * 60)

    try:
        while True:
            if proc.poll() is not None:
                logger.warning(f"Launcher exited with code {proc.returncode}")
                break
            time.sleep(5)
    except KeyboardInterrupt:
        signal_handler(None, None)


if __name__ == "__main__":
    main()
