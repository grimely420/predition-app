#!/usr/bin/env python3
"""Unified Flask API for all coins and horizons."""

from flask import Flask, Response, jsonify, request

from .coin_config import get_coin_config, list_coins
from .data_store import DataStore
from .feature_engine import FeatureEngine
from .model_manager import ModelManager
from .predictor_core import Predictor
from .validator import Validator
from .utils import setup_logging

logger = setup_logging("API")

_CACHE = {}


def get_components(coin_id: str):
    """Return cached components for a coin."""
    key = coin_id.lower()
    if key not in _CACHE:
        cfg = get_coin_config(key)
        ds = DataStore(cfg.db_path, cfg.symbol)
        fe = FeatureEngine(ds, cfg.symbol)
        mm = ModelManager(cfg, ds, fe)
        pred = Predictor(cfg, ds, fe, mm)
        val = Validator(cfg, ds)
        _CACHE[key] = (cfg, ds, fe, mm, pred, val)
    return _CACHE[key]


def create_app() -> Flask:
    app = Flask(__name__)
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

    @app.route('/predict/<coin_id>/<int:horizon>', methods=['GET'])
    def predict_one(coin_id, horizon):
        try:
            cfg, ds, fe, mm, pred, val = get_components(coin_id)
        except Exception as e:
            return jsonify(error=str(e)), 400
        if horizon not in cfg.prediction_horizons:
            return jsonify(error=f"Invalid horizon: {horizon}"), 400
        result = pred.predict(horizon)
        if result is None:
            return jsonify(error='Prediction failed'), 503
        return jsonify(result)

    @app.route('/predict/<coin_id>', methods=['GET'])
    def predict_all(coin_id):
        try:
            cfg, ds, fe, mm, pred, val = get_components(coin_id)
        except Exception as e:
            return jsonify(error=str(e)), 400
        results = []
        for h in cfg.prediction_horizons:
            r = pred.predict(h)
            if r:
                results.append(r)
        if not results:
            return jsonify(error='No predictions available'), 503
        return jsonify({'coin_id': coin_id, 'predictions': results})

    @app.route('/validate/<coin_id>', methods=['POST'])
    def validate_coin(coin_id):
        try:
            cfg, ds, fe, mm, pred, val = get_components(coin_id)
        except Exception as e:
            return jsonify(error=str(e)), 400
        n = val.validate()
        return jsonify({'coin_id': coin_id, 'validated': n})

    @app.route('/stats/<coin_id>', methods=['GET'])
    def stats(coin_id):
        try:
            cfg, ds, fe, mm, pred, val = get_components(coin_id)
        except Exception as e:
            return jsonify(error=str(e)), 400
        return jsonify({
            'coin_id': coin_id,
            'price_count': ds.count_prices(),
            'stats': {
                h: ds.get_prediction_stats(horizon=h)
                for h in cfg.prediction_horizons
            }
        })

    INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cryptocurrency Prediction API | Unified Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #0f1115;
            --surface: #161922;
            --surface-2: #1e212b;
            --border: rgba(255, 255, 255, 0.08);
            --text: #f0f2f5;
            --text-muted: #8b92a8;
            --accent: #6366f1;
            --accent-2: #8b5cf6;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --info: #06b6d4;
            --radius: 14px;
            --shadow: 0 10px 40px rgba(0, 0, 0, 0.25);
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Inter', sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.5;
            min-height: 100vh;
        }
        .wrap { max-width: 1280px; margin: 0 auto; padding: 28px; }
        header {
            display: flex; align-items: center; justify-content: space-between;
            gap: 20px; flex-wrap: wrap; margin-bottom: 28px;
        }
        .brand { display: flex; align-items: center; gap: 14px; }
        .brand-icon {
            width: 48px; height: 48px; border-radius: var(--radius);
            background: linear-gradient(135deg, var(--accent), var(--accent-2));
            display: grid; place-items: center; font-size: 22px; box-shadow: var(--shadow);
        }
        .brand h1 { font-size: 1.4rem; font-weight: 700; letter-spacing: -0.02em; }
        .brand p { color: var(--text-muted); font-size: 0.9rem; margin-top: 2px; }
        .status-pill {
            display: inline-flex; align-items: center; gap: 8px;
            padding: 8px 16px; border-radius: 999px; font-size: 0.85rem; font-weight: 600;
            background: var(--surface); border: 1px solid var(--border);
        }
        .dot { width: 8px; height: 8px; border-radius: 50%; }
        .dot.ok { background: var(--success); box-shadow: 0 0 10px var(--success); }
        .dot.warn { background: var(--warning); box-shadow: 0 0 10px var(--warning); }
        .dot.err { background: var(--danger); box-shadow: 0 0 10px var(--danger); }
        .refresh-btn {
            background: var(--surface-2); color: var(--text); border: 1px solid var(--border);
            padding: 8px 16px; border-radius: 999px; cursor: pointer; font-weight: 500;
            transition: 0.2s; display: inline-flex; align-items: center; gap: 8px;
        }
        .refresh-btn:hover { background: var(--surface); border-color: var(--accent); }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 20px; margin-bottom: 28px; }
        .card {
            background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius);
            padding: 22px; box-shadow: var(--shadow); transition: transform 0.2s, border-color 0.2s;
        }
        .card:hover { border-color: rgba(99, 102, 241, 0.35); }
        .card h3 { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-muted); margin-bottom: 10px; }
        .card .big { font-size: 2rem; font-weight: 700; letter-spacing: -0.03em; }
        .coin-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-top: 8px; }
        .coin-chip {
            background: var(--surface-2); border: 1px solid var(--border); border-radius: 999px;
            padding: 6px 14px; font-size: 0.85rem; font-weight: 600; text-transform: uppercase;
        }
        .section-title { font-size: 1.1rem; font-weight: 700; margin-bottom: 18px; display: flex; align-items: center; gap: 10px; }
        .endpoint-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 18px; }
        .endpoint {
            background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius);
            overflow: hidden; display: flex; flex-direction: column;
        }
        .endpoint-head {
            padding: 16px 18px; border-bottom: 1px solid var(--border); display: flex;
            justify-content: space-between; align-items: center; gap: 12px;
        }
        .endpoint-meta { display: flex; align-items: center; gap: 10px; }
        .method {
            font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; font-weight: 700;
            padding: 4px 8px; border-radius: 6px; color: #fff;
        }
        .method.get { background: var(--accent); }
        .method.post { background: var(--success); }
        .path { font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; color: var(--text); font-weight: 500; }
        .endpoint-body { padding: 16px 18px; flex: 1; display: flex; flex-direction: column; gap: 14px; }
        .endpoint-desc { color: var(--text-muted); font-size: 0.9rem; }
        .try-btn {
            align-self: flex-start; background: var(--surface-2); color: var(--text); border: 1px solid var(--border);
            padding: 8px 16px; border-radius: 999px; cursor: pointer; font-size: 0.85rem; font-weight: 600;
            transition: 0.2s;
        }
        .try-btn:hover { background: var(--accent); border-color: var(--accent); }
        .response {
            display: none; background: var(--bg); border: 1px solid var(--border); border-radius: 10px;
            padding: 14px; font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; overflow-x: auto;
            white-space: pre-wrap; color: #c7d2fe;
        }
        .response.visible { display: block; }
        .prediction-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 18px; }
        .prediction-card { background: var(--surface); border-radius: var(--radius); padding: 20px; border: 1px solid var(--border); }
        .prediction-card h4 { font-size: 1rem; margin-bottom: 14px; display: flex; align-items: center; gap: 8px; }
        .price-line { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px; }
        .price-label { color: var(--text-muted); font-size: 0.85rem; }
        .price-value { font-family: 'JetBrains Mono', monospace; font-weight: 700; font-size: 1.15rem; }
        .positive { color: var(--success); }
        .negative { color: var(--danger); }
        .muted { color: var(--text-muted); }
        .horizon-list { display: flex; flex-direction: column; gap: 10px; margin-top: 14px; }
        .horizon-item {
            background: var(--surface-2); border: 1px solid var(--border); border-radius: 10px;
            padding: 12px 14px; display: grid; grid-template-columns: 1fr auto auto; gap: 14px; align-items: center;
        }
        .horizon-item .time { font-size: 0.8rem; color: var(--text-muted); }
        .horizon-item .pred { font-family: 'JetBrains Mono', monospace; font-weight: 600; }
        .horizon-item .change { font-size: 0.85rem; font-weight: 600; }
        .stats-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        .stats-table th, .stats-table td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border); font-size: 0.85rem; }
        .stats-table th { color: var(--text-muted); font-weight: 600; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.05em; }
        .stats-table td { font-family: 'JetBrains Mono', monospace; }
        .bar-wrap { background: var(--surface-2); border-radius: 999px; height: 8px; overflow: hidden; margin-top: 6px; }
        .bar { height: 100%; border-radius: 999px; background: linear-gradient(90deg, var(--accent), var(--accent-2)); }
        footer { text-align: center; color: var(--text-muted); font-size: 0.8rem; padding: 30px 0; }
        .empty { color: var(--text-muted); font-size: 0.9rem; padding: 12px 0; }
        @media (max-width: 640px) {
            .wrap { padding: 18px; }
            .brand h1 { font-size: 1.2rem; }
            .endpoint-grid, .prediction-grid { grid-template-columns: 1fr; }
            .horizon-item { grid-template-columns: 1fr; gap: 6px; }
        }
    </style>
</head>
<body>
    <div class="wrap">
        <header>
            <div class="brand">
                <div class="brand-icon">&#128200;</div>
                <div>
                    <h1>Prediction API Dashboard</h1>
                    <p>Unified multi-coin, multi-horizon cryptocurrency forecasting</p>
                </div>
            </div>
            <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
                <span class="status-pill" id="healthPill"><span class="dot ok" id="healthDot"></span><span id="healthText">Loading...</span></span>
                <button class="refresh-btn" onclick="refreshAll()">&#x21bb; Refresh</button>
            </div>
        </header>

        <section class="grid">
            <div class="card">
                <h3>API Health</h3>
                <div class="big" id="healthBig">—</div>
                <p class="muted" id="healthSub">checking service status</p>
            </div>
            <div class="card">
                <h3>Supported Coins</h3>
                <div class="big" id="coinCount">—</div>
                <div class="coin-row" id="coinRow"></div>
            </div>
            <div class="card">
                <h3>Total Price Points</h3>
                <div class="big" id="priceCount">—</div>
                <p class="muted" id="priceSub">across all databases</p>
            </div>
            <div class="card">
                <h3>Last Update</h3>
                <div class="big" id="lastUpdate">—</div>
                <p class="muted">auto-refreshes every 15s</p>
            </div>
        </section>

        <section style="margin-bottom: 28px;">
            <h2 class="section-title">&#128161; Endpoint Explorer</h2>
            <div class="endpoint-grid" id="endpointGrid"></div>
        </section>

        <section style="margin-bottom: 28px;">
            <h2 class="section-title">&#128200; Live Predictions</h2>
            <div class="prediction-grid" id="predictionGrid"></div>
        </section>

        <section style="margin-bottom: 28px;">
            <h2 class="section-title">&#128202; Prediction Accuracy Stats</h2>
            <div class="prediction-grid" id="statsGrid"></div>
        </section>

        <footer>
            Cryptocurrency Prediction API &middot; BTC, BNB, HYPE &middot; 5 / 10 / 15 minute horizons
        </footer>
    </div>

    <script>
        const COINS = ['btc', 'bnb', 'hype'];

        function buildEndpoints() {
            const endpoints = [
                { method: 'GET', path: '/', desc: 'This dashboard page. Returns the API overview and documentation.' },
                { method: 'GET', path: '/health', desc: 'Service health check. Returns the current API status.' },
                { method: 'GET', path: '/coins', desc: 'List every supported coin identifier.' }
            ];
            for (const coin of COINS) {
                endpoints.push(
                    { method: 'GET', path: `/predict/${coin}`, desc: `All horizon predictions for ${coin.toUpperCase()} (5, 10, 15 min).` },
                    { method: 'GET', path: `/predict/${coin}/5`, desc: `Single 5-minute prediction for ${coin.toUpperCase()}.` },
                    { method: 'GET', path: `/predict/${coin}/10`, desc: `Single 10-minute prediction for ${coin.toUpperCase()}.` },
                    { method: 'GET', path: `/predict/${coin}/15`, desc: `Single 15-minute prediction for ${coin.toUpperCase()}.` },
                    { method: 'GET', path: `/stats/${coin}`, desc: `Accuracy and error statistics per horizon for ${coin.toUpperCase()}.` },
                    { method: 'POST', path: `/validate/${coin}`, desc: `Validate recent ${coin.toUpperCase()} predictions against live prices.` }
                );
            }
            return endpoints;
        }

        function renderEndpoints() {
            const endpoints = buildEndpoints();
            const grid = document.getElementById('endpointGrid');
            grid.innerHTML = endpoints.map((ep, i) => `
                <div class="endpoint">
                    <div class="endpoint-head">
                        <div class="endpoint-meta">
                            <span class="method ${ep.method.toLowerCase()}">${ep.method}</span>
                            <span class="path">${ep.path}</span>
                        </div>
                    </div>
                    <div class="endpoint-body">
                        <div class="endpoint-desc">${ep.desc}</div>
                        <button class="try-btn" onclick="tryEndpoint(${i}, '${ep.method}', '${ep.path}')">Try it</button>
                        <pre class="response" id="resp-${i}"></pre>
                    </div>
                </div>
            `).join('');
        }

        async function tryEndpoint(idx, method, path) {
            const panel = document.getElementById('resp-' + idx);
            panel.classList.add('visible');
            panel.textContent = 'Loading...';
            try {
                const res = await fetch(path, { method });
                const data = await res.json();
                panel.textContent = `HTTP ${res.status} ${res.statusText}\n${JSON.stringify(data, null, 2)}`;
            } catch (e) {
                panel.textContent = 'Error: ' + e.message;
            }
        }

        function setHealth(ok, text) {
            const pill = document.getElementById('healthPill');
            const dot = document.getElementById('healthDot');
            const txt = document.getElementById('healthText');
            const big = document.getElementById('healthBig');
            const sub = document.getElementById('healthSub');
            dot.className = 'dot ' + (ok ? 'ok' : 'err');
            txt.textContent = text;
            big.textContent = ok ? 'Healthy' : 'Degraded';
            sub.textContent = text;
        }

        async function fetchHealth() {
            try {
                const res = await fetch('/health');
                const data = await res.json();
                setHealth(data.status === 'ok', data.status === 'ok' ? 'All systems operational' : 'Service issue detected');
            } catch (e) {
                setHealth(false, 'Unreachable');
            }
        }

        async function fetchCoins() {
            try {
                const data = await (await fetch('/coins')).json();
                const coins = data.coins || [];
                document.getElementById('coinCount').textContent = coins.length;
                document.getElementById('coinRow').innerHTML = coins.map(c => `<span class="coin-chip">${c}</span>`).join('');
            } catch (e) {
                document.getElementById('coinCount').textContent = '—';
            }
        }

        function fmtUsd(n) {
            if (n == null) return '—';
            return '$' + Number(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        }

        function fmtPct(n) {
            if (n == null) return '—';
            const v = Number(n);
            const sign = v > 0 ? '+' : '';
            return `${sign}${v.toFixed(4)}%`;
        }

        async function fetchPredictions() {
            const grid = document.getElementById('predictionGrid');
            grid.innerHTML = '';
            for (const coin of COINS) {
                const card = document.createElement('div');
                card.className = 'prediction-card';
                card.innerHTML = `<h4>&#11088; ${coin.toUpperCase()}</h4><div class="empty">Loading...</div>`;
                grid.appendChild(card);
                try {
                    const data = await (await fetch(`/predict/${coin}`)).json();
                    const preds = data.predictions || [];
                    if (!preds.length) {
                        card.querySelector('div').textContent = 'No predictions available';
                        continue;
                    }
                    const first = preds[0];
                    card.innerHTML = `
                        <h4>&#11088; ${coin.toUpperCase()}</h4>
                        <div class="price-line"><span class="price-label">Current price</span><span class="price-value">${fmtUsd(first.current_price)}</span></div>
                        <div class="price-line"><span class="price-label">Model</span><span class="price-value muted">${first.model_used || '—'}</span></div>
                        <div class="horizon-list">
                            ${preds.map(p => {
                                const cls = p.change_percent > 0 ? 'positive' : (p.change_percent < 0 ? 'negative' : 'muted');
                                const conf = Array.isArray(p.confidence_interval) ? `${fmtUsd(p.confidence_interval[0])} – ${fmtUsd(p.confidence_interval[1])}` : '—';
                                return `<div class="horizon-item">
                                    <div><div class="time">${p.horizon_minutes}-minute horizon</div><div class="pred">${fmtUsd(p.predicted_price)}</div></div>
                                    <div class="change ${cls}">${fmtPct(p.change_percent)}</div>
                                    <div class="muted" style="font-size:0.78rem;text-align:right;">${conf}</div>
                                </div>`;
                            }).join('')}
                        </div>
                    `;
                } catch (e) {
                    card.innerHTML = `<h4>&#11088; ${coin.toUpperCase()}</h4><div class="empty">Error loading predictions</div>`;
                }
            }
        }

        async function fetchStats() {
            const grid = document.getElementById('statsGrid');
            grid.innerHTML = '';
            let totalPrices = 0;
            for (const coin of COINS) {
                const card = document.createElement('div');
                card.className = 'prediction-card';
                card.innerHTML = `<h4>&#128293; ${coin.toUpperCase()} Stats</h4><div class="empty">Loading...</div>`;
                grid.appendChild(card);
                try {
                    const data = await (await fetch(`/stats/${coin}`)).json();
                    totalPrices += data.price_count || 0;
                    const stats = data.stats || {};
                    const rows = Object.entries(stats).map(([h, s]) => {
                        const acc = s.accuracy_pct_1pct || 0;
                        return `<tr>
                            <td>${h} min</td>
                            <td>${acc.toFixed(1)}%</td>
                            <td>${(s.avg_abs_error_pct || 0).toFixed(4)}%</td>
                            <td>${s.total || 0}</td>
                        </tr>`;
                    }).join('');
                    card.innerHTML = `
                        <h4>&#128293; ${coin.toUpperCase()} Stats</h4>
                        <table class="stats-table">
                            <thead><tr><th>Horizon</th><th>Accuracy</th><th>Avg Error</th><th>Total</th></tr></thead>
                            <tbody>${rows}</tbody>
                        </table>
                    `;
                } catch (e) {
                    card.innerHTML = `<h4>&#128293; ${coin.toUpperCase()} Stats</h4><div class="empty">Error loading stats</div>`;
                }
            }
            document.getElementById('priceCount').textContent = totalPrices.toLocaleString();
        }

        function updateTimestamp() {
            const now = new Date();
            document.getElementById('lastUpdate').textContent = now.toLocaleTimeString();
            document.getElementById('priceSub').textContent = 'across all databases · updated ' + now.toLocaleTimeString();
        }

        async function refreshAll() {
            await Promise.all([fetchHealth(), fetchCoins(), fetchPredictions(), fetchStats()]);
            updateTimestamp();
        }

        renderEndpoints();
        refreshAll();
        setInterval(refreshAll, 15000);
    </script>
</body>
</html>"""

    @app.route('/', methods=['GET'])
    def index():
        return Response(INDEX_HTML, mimetype='text/html')

    @app.route('/coins', methods=['GET'])
    def coins():
        return jsonify({'coins': list_coins()})

    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({'status': 'ok'})

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, threaded=True)
