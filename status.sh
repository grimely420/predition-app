#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "=========================================="
echo "Prediction System Status"
echo "=========================================="
echo ""
echo "Processes:"
ps aux | grep -E "shared\.collector|shared\.api|services\.predictor_loop|start_all" | grep -v grep | awk '{print "  " $11 " " $12 " " $13 " " $14}'
echo ""
for coin in btc bnb hype; do
    count=$(python3 -c "from prediction.shared.coin_config import get_coin_config; cfg=get_coin_config('$coin'); import sqlite3; print(sqlite3.connect(cfg.db_path).cursor().execute('SELECT COUNT(*) FROM prices').fetchone()[0])" 2>/dev/null)
    echo "${coin^^} Count: ${count:-0}"
done
echo ""
echo "Unified API: $(curl -s http://localhost:5000/health | python3 -c "import sys,json; print(json.load(sys.stdin).get('status', 'offline'))" 2>/dev/null || echo 'offline')"
echo ""
echo "Dashboard: http://localhost:5000"
echo "Endpoints:"
echo "  http://localhost:5000/coins"
echo "  http://localhost:5000/predict/<coin>"
echo "  http://localhost:5000/predict/<coin>/<5|10|15>"
echo "  http://localhost:5000/stats/<coin>"
echo "  http://localhost:5000/health"
