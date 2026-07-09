#!/bin/bash
# Start all prediction system components (unified multi-horizon launcher).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"
if [ ! -f "$VENV_PYTHON" ]; then
    VENV_PYTHON="python3"
fi

echo "=========================================="
echo "Starting Multi-Horizon Prediction System"
echo "=========================================="

# The Python launcher starts the unified API, one collector per coin,
# and one predictor loop per coin. It manages all child processes and
# writes a .running_pids file for stop_all.sh.
exec "$VENV_PYTHON" "$SCRIPT_DIR/prediction/start_all.py"
