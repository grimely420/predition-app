"""Shared professional dashboard template for independent coin APIs."""

import json

DASHBOARD_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>__COIN_DISPLAY__ Prediction Dashboard | Crypto Forecast API</title>
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
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px; margin-bottom: 28px; }
        .card {
            background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius);
            padding: 22px; box-shadow: var(--shadow); transition: transform 0.2s, border-color 0.2s;
        }
        .card:hover { border-color: rgba(99, 102, 241, 0.35); }
        .card h3 { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-muted); margin-bottom: 10px; }
        .card .big { font-size: 2rem; font-weight: 700; letter-spacing: -0.03em; }
        .section-title { font-size: 1.1rem; font-weight: 700; margin-bottom: 18px; display: flex; align-items: center; gap: 10px; }
        .endpoint-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 18px; }
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
        .prediction-card { background: var(--surface); border-radius: var(--radius); padding: 22px; border: 1px solid var(--border); }
        .prediction-card h4 { font-size: 1rem; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
        .metric-row { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 10px; }
        .metric-label { color: var(--text-muted); font-size: 0.9rem; }
        .metric-value { font-family: 'JetBrains Mono', monospace; font-weight: 700; font-size: 1.1rem; }
        .positive { color: var(--success); }
        .negative { color: var(--danger); }
        .muted { color: var(--text-muted); }
        .prediction-table { width: 100%; border-collapse: collapse; }
        .prediction-table th, .prediction-table td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border); font-size: 0.85rem; }
        .prediction-table th { color: var(--text-muted); font-weight: 600; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.05em; }
        .prediction-table td { font-family: 'JetBrains Mono', monospace; }
        .badge {
            display: inline-block; padding: 3px 8px; border-radius: 999px; font-size: 0.7rem; font-weight: 700;
            border: 1px solid transparent;
        }
        .badge.ok { background: rgba(16, 185, 129, 0.12); color: var(--success); border-color: var(--success); }
        .badge.bad { background: rgba(239, 68, 68, 0.12); color: var(--danger); border-color: var(--danger); }
        .badge.pending { background: rgba(6, 182, 212, 0.12); color: var(--info); border-color: var(--info); }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; }
        .stats-item { background: var(--surface-2); border: 1px solid var(--border); border-radius: 10px; padding: 14px; }
        .stats-item .label { font-size: 0.75rem; color: var(--text-muted); margin-bottom: 4px; text-transform: uppercase; }
        .stats-item .value { font-family: 'JetBrains Mono', monospace; font-weight: 600; font-size: 1rem; }
        footer { text-align: center; color: var(--text-muted); font-size: 0.8rem; padding: 30px 0; }
        .empty { color: var(--text-muted); font-size: 0.9rem; padding: 12px 0; }
        @media (max-width: 640px) {
            .wrap { padding: 18px; }
            .brand h1 { font-size: 1.2rem; }
            .endpoint-grid { grid-template-columns: 1fr; }
            .metric-row { flex-direction: column; align-items: flex-start; gap: 4px; }
        }
    </style>
</head>
<body>
    <div class="wrap">
        <header>
            <div class="brand">
                <div class="brand-icon">__COIN_EMOJI__</div>
                <div>
                    <h1>__COIN_DISPLAY__ Prediction Dashboard</h1>
                    <p>Independent __COIN_DISPLAY__ forecasting API</p>
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
                <h3>Current Price</h3>
                <div class="big" id="currentPrice">—</div>
                <p class="muted" id="priceUpdate">—</p>
            </div>
            <div class="card">
                <h3>Accuracy</h3>
                <div class="big" id="accuracyValue">—%</div>
                <p class="muted" id="accuracySub">—</p>
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
            <h2 class="section-title">&#128200; Latest Prediction</h2>
            <div id="predictionCard"><div class="empty">Loading...</div></div>
        </section>

        <section style="margin-bottom: 28px;">
            <h2 class="section-title">&#128310; Recent Predictions</h2>
            <div id="recentTable"><div class="empty">Loading...</div></div>
        </section>

        <section style="margin-bottom: 28px;">
            <h2 class="section-title">&#128202; __STATS_TITLE__</h2>
            <div id="statsGrid"><div class="empty">Loading...</div></div>
        </section>

        <footer>
            __COIN_DISPLAY__ Prediction API &middot; Independent service endpoint
        </footer>
    </div>

    <script>
        window.SERVICE_ENDPOINTS = __ENDPOINTS__;

        function renderEndpoints() {
            const grid = document.getElementById('endpointGrid');
            grid.innerHTML = window.SERVICE_ENDPOINTS.map((ep, i) => `
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
                const ok = data.status === 'ok' || data.status === 'healthy';
                setHealth(ok, ok ? 'All systems operational' : (data.message || 'Service issue'));
            } catch (e) {
                setHealth(false, 'Unreachable');
            }
        }

        async function fetchCurrentPrice() {
            try {
                const data = await (await fetch('/current_price')).json();
                document.getElementById('currentPrice').textContent = fmtUsd(data.price);
                document.getElementById('priceUpdate').textContent = data.timestamp || 'live';
            } catch (e) {
                document.getElementById('currentPrice').textContent = '—';
            }
        }

        async function fetchAccuracy() {
            try {
                const data = await (await fetch('/accuracy_summary')).json();
                document.getElementById('accuracyValue').textContent = (data.accuracy_percent || 0) + '%';
                document.getElementById('accuracySub').textContent = `${data.predictions_within_threshold || 0} / ${data.last_n_predictions || 0} within ${data.threshold || 1}%`;
            } catch (e) {
                document.getElementById('accuracyValue').textContent = '—%';
            }
        }

        function fmtUsd(n) {
            if (n == null) return '—';
            return '$' + Number(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 });
        }

        function fmtPct(n) {
            if (n == null) return '—';
            const v = Number(n);
            const sign = v > 0 ? '+' : '';
            return `${sign}${v.toFixed(4)}%`;
        }

        function findPredictedPrice(obj) {
            for (const key of Object.keys(obj || {})) {
                if (key.startsWith('predicted_price_')) return obj[key];
            }
            return obj.predicted_price;
        }

        async function fetchLatestPrediction() {
            const card = document.getElementById('predictionCard');
            try {
                const data = await (await fetch('/predict')).json();
                if (!data.success) {
                    card.innerHTML = '<div class="empty">No prediction available</div>';
                    return;
                }
                const pred = findPredictedPrice(data);
                const cls = data.change_percent > 0 ? 'positive' : (data.change_percent < 0 ? 'negative' : 'muted');
                const conf = data.confidence_interval;
                let confHtml = '—';
                if (Array.isArray(conf) && conf.length === 2) {
                    confHtml = `${fmtUsd(conf[0])} – ${fmtUsd(conf[1])}`;
                } else if (conf && typeof conf === 'object') {
                    const vals = Object.values(conf);
                    if (vals.length === 2) confHtml = `${fmtUsd(vals[0])} – ${fmtUsd(vals[1])}`;
                }
                card.innerHTML = `
                    <div class="prediction-card">
                        <h4>&#11088; Latest Forecast</h4>
                        <div class="metric-row"><span class="metric-label">Current price</span><span class="metric-value">${fmtUsd(data.current_price)}</span></div>
                        <div class="metric-row"><span class="metric-label">Predicted price</span><span class="metric-value">${fmtUsd(pred)}</span></div>
                        <div class="metric-row"><span class="metric-label">Change</span><span class="metric-value ${cls}">${fmtPct(data.change_percent)}</span></div>
                        <div class="metric-row"><span class="metric-label">Confidence interval</span><span class="metric-value muted">${confHtml}</span></div>
                        <div class="metric-row"><span class="metric-label">Model</span><span class="metric-value muted">${data.model_used || '—'}</span></div>
                        <div class="metric-row"><span class="metric-label">Horizon</span><span class="metric-value muted">${data.prediction_horizon || '—'} min</span></div>
                    </div>
                `;
            } catch (e) {
                card.innerHTML = '<div class="empty">Error loading prediction</div>';
            }
        }

        function statusBadge(p) {
            if (p.is_correct === true) return '<span class="badge ok">&#10003; ACCURATE</span>';
            if (p.is_correct === false) return '<span class="badge bad">&#10007; DEVIATED</span>';
            return '<span class="badge pending">VALIDATING</span>';
        }

        async function fetchRecentPredictions() {
            const table = document.getElementById('recentTable');
            try {
                const data = await (await fetch('/recent_predictions')).json();
                const rows = Array.isArray(data) ? data : (data.predictions || []);
                if (!rows.length) {
                    table.innerHTML = '<div class="empty">No recent predictions</div>';
                    return;
                }
                const tbody = rows.slice(0, 12).map(p => `
                    <tr>
                        <td>${p.prediction_time || '—'}</td>
                        <td>${fmtUsd(p.predicted_price)}</td>
                        <td>${fmtUsd(p.actual_price)}</td>
                        <td>${p.error_percent != null ? p.error_percent + '%' : '—'}</td>
                        <td>${p.model_used || '—'}</td>
                        <td>${statusBadge(p)}</td>
                    </tr>
                `).join('');
                table.innerHTML = `
                    <div class="prediction-card" style="overflow-x:auto;">
                        <table class="prediction-table">
                            <thead><tr><th>Time</th><th>Predicted</th><th>Actual</th><th>Error %</th><th>Model</th><th>Status</th></tr></thead>
                            <tbody>${tbody}</tbody>
                        </table>
                    </div>
                `;
            } catch (e) {
                table.innerHTML = '<div class="empty">Error loading predictions</div>';
            }
        }

        async function fetchDetailedStats() {
            const grid = document.getElementById('statsGrid');
            try {
                const data = await (await fetch('__STATS_ENDPOINT__')).json();
                const items = Object.entries(data).map(([k, v]) => {
                    let display = v;
                    if (typeof v === 'number') display = Number(v).toLocaleString();
                    if (typeof v === 'boolean') display = v ? 'Yes' : 'No';
                    if (v && typeof v === 'object') display = JSON.stringify(v);
                    return `<div class="stats-item"><div class="label">${k.replace(/_/g, ' ')}</div><div class="value">${display}</div></div>`;
                }).join('');
                grid.innerHTML = `<div class="stats-grid">${items}</div>`;
            } catch (e) {
                grid.innerHTML = '<div class="empty">Error loading stats</div>';
            }
        }

        function updateTimestamp() {
            document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
        }

        async function refreshAll() {
            await Promise.all([
                fetchHealth(), fetchCurrentPrice(), fetchAccuracy(),
                fetchLatestPrediction(), fetchRecentPredictions(), fetchDetailedStats()
            ]);
            updateTimestamp();
        }

        renderEndpoints();
        refreshAll();
        setInterval(refreshAll, 15000);
    </script>
</body>
</html>"""


def coin_dashboard_html(
    coin: str,
    display_name: str,
    endpoints: list,
    coin_emoji: str = "&#11088;",
    stats_endpoint: str = "/detailed_stats",
    stats_title: str = "Detailed Stats"
) -> str:
    """Return a professional HTML dashboard for an independent coin API.

    Args:
        coin: Lower-case coin identifier (e.g. 'btc', 'bnb', 'hype').
        display_name: Human-readable coin name (e.g. 'Bitcoin', 'BNB').
        endpoints: List of dicts with 'method', 'path', and 'desc' for the explorer.
        coin_emoji: HTML entity or emoji for the brand icon.
        stats_endpoint: Endpoint to poll for the detailed stats section.
        stats_title: Title shown above the detailed stats section.
    """
    return (
        DASHBOARD_TEMPLATE
        .replace("__COIN__", coin)
        .replace("__COIN_DISPLAY__", display_name)
        .replace("__COIN_EMOJI__", coin_emoji)
        .replace("__ENDPOINTS__", json.dumps(endpoints))
        .replace("__STATS_ENDPOINT__", stats_endpoint)
        .replace("__STATS_TITLE__", stats_title)
    )
