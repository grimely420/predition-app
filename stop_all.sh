#!/bin/bash
# Stop all prediction system components

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/.running_pids"

# Patterns that match prediction system processes
PATTERNS=(
    "prediction/start_all.py"
    "shared/collector.py"
    "shared/api.py"
    "services/predictor_loop.py"
    "hype/hype_predictor_loop.py"
    "bnb/bnb_predictor_loop.py"
    "bitcoin/btc_predictor_loop.py"
)

echo "=========================================="
echo "Stopping Prediction System"
echo "=========================================="

if [ -f "$PID_FILE" ]; then
    echo "Stopping processes from PID file..."

    # Read PIDs and kill them
    while IFS=: read -r pid script || [ -n "$pid" ]; do
        # Skip comment lines
        [[ "$pid" =~ ^# ]] && continue

        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            echo "  Stopping PID $pid ($(basename "$script"))"
            kill "$pid" 2>/dev/null
            sleep 1

            # Force kill if still running
            if kill -0 "$pid" 2>/dev/null; then
                echo "  Force killing PID $pid"
                kill -9 "$pid" 2>/dev/null
            fi
        fi
    done < "$PID_FILE"

    # Remove PID file
    rm "$PID_FILE"
    echo ""
fi

# Also clean up any orphaned processes by pattern
for pattern in "${PATTERNS[@]}"; do
    pids=$(pgrep -f "$pattern" 2>/dev/null)
    if [ -n "$pids" ]; then
        echo "Stopping orphaned $pattern processes: $pids"
        echo "$pids" | xargs kill 2>/dev/null
        sleep 1
        remaining=$(pgrep -f "$pattern" 2>/dev/null)
        if [ -n "$remaining" ]; then
            echo "Force killing remaining: $remaining"
            echo "$remaining" | xargs kill -9 2>/dev/null
        fi
    fi
done

echo ""
echo "=========================================="
echo "System stopped."
echo "=========================================="
