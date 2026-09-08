"""Live prediction dashboard HTML for the Flask API root."""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Prediction Dashboard</title>
    <style>
        :root {
            --bg: #0b0d10;
            --surface: #151922;
            --surface-2: #1e222b;
            --border: rgba(255,255,255,0.08);
            --text: #e8eaf0;
            --muted: #8b92a8;
            --accent: #6366f1;
            --up: #10b981;
            --down: #ef4444;
            --flat: #f59e0b;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background: var(--bg);
            color: var(--text);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            line-height: 1.5;
            padding: 24px;
        }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
            margin-bottom: 24px;
        }
        h1 { font-size: 1.6rem; }
        #last-updated { color: var(--muted); font-size: 0.9rem; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 20px; }
        .card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 18px;
            box-shadow: 0 6px 24px rgba(0,0,0,0.25);
        }
        .card h2 {
            font-size: 1.1rem;
            margin-bottom: 12px;
            display: flex;
            justify-content: space-between;
        }
        .price { font-size: 1.8rem; font-weight: 600; }
        .muted { color: var(--muted); font-size: 0.85rem; }
        .badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .up { background: rgba(16,185,129,0.12); color: var(--up); }
        .down { background: rgba(239,68,68,0.12); color: var(--down); }
        .flat { background: rgba(245,158,11,0.12); color: var(--flat); }
        table { width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 0.9rem; }
        th, td { text-align: left; padding: 8px 6px; border-bottom: 1px solid var(--border); }
        th { color: var(--muted); font-weight: 500; }
        td.num { font-family: "SF Mono", monospace; }
        .bar { height: 6px; border-radius: 3px; background: var(--surface-2); overflow: hidden; margin-top: 4px; }
        .bar-fill { height: 100%; }
        .hl-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-top: 12px; }
        .hl-item { background: var(--surface-2); padding: 10px; border-radius: 8px; }
        .hl-label { color: var(--muted); font-size: 0.75rem; }
        .hl-value { font-size: 1.1rem; font-weight: 600; }
    </style>
</head>
<body>
    <header>
        <h1>Crypto Prediction Dashboard</h1>
        <div id="last-updated">Loading...</div>
    </header>

    <div class="grid" id="coins"></div>
    <div id="hl-section" class="card" style="margin-top: 20px; display:none;">
        <h2>HYPE Hyperliquid Data</h2>
        <div class="hl-grid" id="hl-grid"></div>
        <table>
            <thead><tr><th>Time</th><th>Open</th><th>High</th><th>Low</th><th>Close</th><th>Volume</th><th>Trades</th></tr></thead>
            <tbody id="hl-candles"></tbody>
        </table>
    </div>

    <script>
        const COINS = ['btc', 'bnb', 'hype'];
        const REFRESH_MS = 5000;

        function fmt(num, digits=4) {
            if (num == null) return '-';
            return Number(num).toFixed(digits);
        }

        function pct(num) {
            if (num == null) return '-';
            return (Number(num) > 0 ? '+' : '') + Number(num).toFixed(4) + '%';
        }

        function trendClass(change) {
            const c = Number(change);
            if (c > 0.02) return 'up';
            if (c < -0.02) return 'down';
            return 'flat';
        }

        function cardHtml(coin, feed, stats) {
            let rows = '';
            const horizons = [5, 10, 15];
            for (const h of horizons) {
                const pred = feed && feed.predictions ? feed.predictions.find(p => p.horizon_minutes === h) : null;
                const st = stats && stats[h] ? stats[h] : {};
                const dir = trendClass(pred ? pred.change_percent : 0);
                const signal = pred ? pred.signal_strength : null;
                const probUp = pred ? pred.prob_up : null;
                const probDown = pred ? pred.prob_down : null;
                const expPnl = pred ? pred.expected_pnl_pct : null;
                rows += `<tr>
                    <td>${h}m</td>
                    <td class="num">${pred ? pred.predicted_price : '-'}</td>
                    <td class="num"><span class="badge ${dir}">${pct(pred ? pred.change_percent : 0)}</span></td>
                    <td class="num">${pct(pred ? pred.raw_change_percent : 0)}</td>
                    <td class="num">${fmt(signal, 4)}</td>
                    <td class="num" style="color:var(--up)">${probUp != null ? (probUp*100).toFixed(1)+'%' : '-'}</td>
                    <td class="num" style="color:var(--down)">${probDown != null ? (probDown*100).toFixed(1)+'%' : '-'}</td>
                    <td class="num ${expPnl > 0 ? 'up' : 'down'}">${pct(expPnl)}</td>
                    <td class="num">${st.direction_accuracy_pct != null ? st.direction_accuracy_pct.toFixed(1)+'%' : '-'}</td>
                    <td class="num">${st.beat_naive_pct != null ? st.beat_naive_pct.toFixed(1)+'%' : '-'}</td>
                </tr>`;
            }
            return `
                <div class="card" id="card-${coin}">
                    <h2>
                        <span>${coin.toUpperCase()} <span class="price">${feed && feed.price ? feed.price : '-'}</span></span>
                        <span class="muted">${feed && feed.model ? feed.model : ''}</span>
                    </h2>
                    <div class="muted">Last price: ${feed && feed.price_timestamp ? new Date(feed.price_timestamp).toLocaleString() : '-'} | conf mult: ${feed && feed.confidence_multiplier != null ? feed.confidence_multiplier : '-'}</div>
                    <table>
                        <thead>
                            <tr>
                                <th>H</th><th>Predicted</th><th>Net Change</th><th>Raw</th>
                                <th>Signal</th><th>Prob Up</th><th>Prob Down</th><th>Exp PnL</th>
                                <th>Dir Acc</th><th>Beat Naive</th>
                            </tr>
                        </thead>
                        <tbody>${rows}</tbody>
                    </table>
                </div>`;
        }

        async function fetchCoin(coin) {
            const [feedRes, statsRes] = await Promise.all([
                fetch(`/feed/${coin}`),
                fetch(`/stats/${coin}`)
            ]);
            const feed = feedRes.ok ? await feedRes.json() : {};
            const stats = statsRes.ok ? await statsRes.json() : {stats: {}};
            return {coin, feed, stats: stats.stats};
        }

        async function render() {
            const results = await Promise.all(COINS.map(fetchCoin));
            const container = document.getElementById('coins');
            let html = '';
            for (const {coin, feed, stats} of results) {
                html += cardHtml(coin, feed, stats);
            }
            container.innerHTML = html;
            document.getElementById('last-updated').textContent = 'Updated ' + new Date().toLocaleString();
            renderHL();
        }

        async function renderHL() {
            const res = await fetch('/hl/hype');
            if (!res.ok) { document.getElementById('hl-section').style.display = 'none'; return; }
            const data = await res.json();
            document.getElementById('hl-section').style.display = 'block';
            const snap = data.latest_snapshot || {};
            const items = [
                ['Mark', snap.mark_px], ['Oracle', snap.oracle_px], ['Mid', snap.mid_px],
                ['Funding', snap.funding], ['Open Interest', snap.open_interest],
                ['Premium', snap.premium], ['Spread bps', snap.spread_bps],
                ['Imbalance 5', snap.imbalance_5], ['Imbalance 20', snap.imbalance_20],
                ['Day Ntl Vol', snap.day_ntl_vlm]
            ];
            let grid = '';
            for (const [label, val] of items) {
                grid += `<div class="hl-item"><div class="hl-label">${label}</div><div class="hl-value">${val != null ? fmt(val, 6) : '-'}</div></div>`;
            }
            document.getElementById('hl-grid').innerHTML = grid;
            const candles = data.candles_1m_tail || [];
            const tail = candles.slice(-10).reverse();
            let tbody = '';
            for (const c of tail) {
                tbody += `<tr>
                    <td>${new Date(c.timestamp).toLocaleTimeString()}</td>
                    <td class="num">${fmt(c.o)}</td>
                    <td class="num">${fmt(c.h)}</td>
                    <td class="num">${fmt(c.l)}</td>
                    <td class="num">${fmt(c.c)}</td>
                    <td class="num">${fmt(c.v, 2)}</td>
                    <td class="num">${c.n}</td>
                </tr>`;
            }
            document.getElementById('hl-candles').innerHTML = tbody;
        }

        render();
        setInterval(render, REFRESH_MS);
    </script>
</body>
</html>"""
