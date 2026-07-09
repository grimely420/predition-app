#!/bin/bash
# Start all prediction system components manually (no systemd)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"

# Create log directory
mkdir -p "$LOG_DIR"

echo "=========================================="
echo "Starting Prediction System"
echo "=========================================="

# Function to start a component
start_component() {
    local name=$1
    local script=$2
    local logfile=$3
    
    echo "Starting $name..."
    nohup "$VENV_PYTHON" "$SCRIPT_DIR/$script" > "$LOG_DIR/$logfile" 2>&1 &
    echo "  PID: $!"
    sleep 2
}

# Save PIDs to file for easy cleanup
PID_FILE="$SCRIPT_DIR/.running_pids"
echo "# Running PIDs $(date)" > "$PID_FILE"

# Start data collectors
echo ""
echo "[1/4] Starting data collectors..."
start_component "Bitcoin Collector" "bitcoin/collector.py" "btc-collector.log"
echo "$!:$SCRIPT_DIR/bitcoin/collector.py" >> "$PID_FILE"

start_component "BNB Collector" "bnb/collector.py" "bnb-collector.log"
echo "$!:$SCRIPT_DIR/bnb/collector.py" >> "$PID_FILE"

# Start APIs
echo ""
echo "[2/4] Starting prediction APIs..."
start_component "Bitcoin API (port 5001)" "bitcoin/api.py" "btc-api.log"
echo "$!:$SCRIPT_DIR/bitcoin/api.py" >> "$PID_FILE"

start_component "BNB API (port 5002)" "bnb/api.py" "bnb-api.log"
echo "$!:$SCRIPT_DIR/bnb/api.py" >> "$PID_FILE"

# Wait for APIs to be ready
echo ""
echo "  Waiting for APIs to initialize..."
sleep 5

# Start prediction generators
echo ""
echo "[3/4] Starting automatic prediction generators..."
start_component "Bitcoin Generator (15min)" "bitcoin/generate_predictions.py" "btc-generator.log"
echo "$!:$SCRIPT_DIR/bitcoin/generate_predictions.py" >> "$PID_FILE"

start_component "BNB Generator (5min)" "bnb/generate_predictions.py" "bnb-generator.log"
echo "$!:$SCRIPT_DIR/bnb/generate_predictions.py" >> "$PID_FILE"

echo ""
echo "[4/4] Starting health monitor..."
start_component "Health Monitor" "shared/health_monitor.py" "health-monitor.log"
echo "$!:$SCRIPT_DIR/shared/health_monitor.py" >> "$PID_FILE"

echo ""
echo "=========================================="
echo "All components started!"
echo "=========================================="
echo ""
echo "PIDs saved to: $PID_FILE"
echo "Logs directory: $LOG_DIR"
echo ""
echo "To view logs:"
echo "  tail -f $LOG_DIR/btc-collector.log"
echo "  tail -f $LOG_DIR/btc-api.log"
echo "  tail -f $LOG_DIR/btc-generator.log"
echo ""
echo "To stop all:"
echo "  ./stop_all.sh"
echo ""
echo "To check predictions:"
echo "  ./check_predictions.sh"
echo ""
echo "API Endpoints:"
echo "  Bitcoin: http://localhost:5001"
echo "  BNB:     http://localhost:5002"
echo ""
