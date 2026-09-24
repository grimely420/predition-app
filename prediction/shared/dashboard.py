"""Live Kalshi prediction decision dashboard HTML for the Flask API root."""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kalshi Crypto Prediction & Decision Terminal | CF Benchmarks BRTI</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #090b0e;
            --surface: #12151c;
            --surface-2: #1a1e27;
            --surface-3: #222734;
            --border: rgba(255, 255, 255, 0.08);
            --border-highlight: rgba(99, 102, 241, 0.3);
            --text: #f1f3f7;
            --muted: #8b92a5;
            --accent: #6366f1;
            --accent-glow: rgba(99, 102, 241, 0.15);
            --up: #10b981;
            --up-bg: rgba(16, 185, 129, 0.12);
            --down: #ef4444;
            --down-bg: rgba(239, 68, 68, 0.12);
            --neutral: #f59e0b;
            --neutral-bg: rgba(245, 158, 11, 0.12);
            --cyan: #06b6d4;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background: var(--bg);
            color: var(--text);
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            line-height: 1.5;
            padding: 20px 24px;
        }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
            margin-bottom: 20px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border);
        }
        .header-left {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .logo-badge {
            background: linear-gradient(135deg, #6366f1, #a855f7);
            color: #fff;
            font-weight: 800;
            padding: 6px 12px;
            border-radius: 8px;
            font-size: 0.85rem;
            letter-spacing: 0.5px;
        }
        h1 {
            font-size: 1.45rem;
            font-weight: 700;
            letter-spacing: -0.5px;
        }
        .header-meta {
            display: flex;
            align-items: center;
            gap: 16px;
            font-size: 0.85rem;
            color: var(--muted);
        }
        .live-indicator {
            display: flex;
            align-items: center;
            gap: 6px;
            color: var(--up);
            font-weight: 600;
            font-size: 0.8rem;
        }
        .pulse-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--up);
            box-shadow: 0 0 10px var(--up);
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse {
            0% { transform: scale(0.95); opacity: 0.8; }
            50% { transform: scale(1.3); opacity: 1; }
            100% { transform: scale(0.95); opacity: 0.8; }
        }

        /* Top Kalshi Round & News Bar */
        .top-banner {
            display: grid;
            grid-template-columns: 1.2fr 1fr;
            gap: 16px;
            margin-bottom: 24px;
        }
        @media (max-width: 900px) {
            .top-banner { grid-template-columns: 1fr; }
        }
        .banner-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px 20px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .banner-card.highlight {
            border-color: var(--border-highlight);
            background: linear-gradient(145deg, var(--surface), #151928);
        }
        .banner-title {
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--muted);
            margin-bottom: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .round-timer-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
        }
        .countdown-digits {
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.9rem;
            font-weight: 700;
            color: #fff;
        }
        .round-sub {
            font-size: 0.85rem;
            color: var(--muted);
        }
        .progress-bar-container {
            width: 100%;
            height: 6px;
            background: var(--surface-3);
            border-radius: 3px;
            overflow: hidden;
            margin-top: 12px;
        }
        .progress-bar-fill {
            height: 100%;
            background: linear-gradient(90deg, #6366f1, #10b981);
            transition: width 1s linear;
        }

        .sentiment-score-row {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-top: 4px;
        }
        .sentiment-score-badge {
            font-size: 1.4rem;
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
        }
        .sentiment-meter {
            flex: 1;
            height: 8px;
            background: var(--surface-3);
            border-radius: 4px;
            position: relative;
            overflow: hidden;
        }
        .sentiment-fill {
            position: absolute;
            top: 0;
            bottom: 0;
            transition: width 0.5s ease, left 0.5s ease;
        }

        /* Coin Prediction Cards */
        .coins-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(370px, 1fr));
            gap: 20px;
            margin-bottom: 24px;
        }
        .coin-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 16px;
            box-shadow: 0 8px 30px rgba(0,0,0,0.3);
            transition: transform 0.2s, border-color 0.2s;
        }
        .coin-card:hover {
            border-color: rgba(255,255,255,0.15);
        }
        .coin-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }
        .coin-title-group {
            display: flex;
            align-items: baseline;
            gap: 8px;
        }
        .coin-sym {
            font-size: 1.4rem;
            font-weight: 800;
            letter-spacing: -0.5px;
        }
        .coin-series-tag {
            font-size: 0.72rem;
            font-family: 'JetBrains Mono', monospace;
            background: var(--surface-2);
            color: var(--cyan);
            padding: 2px 6px;
            border-radius: 4px;
            border: 1px solid rgba(6, 182, 212, 0.2);
        }
        .coin-price {
            font-size: 1.7rem;
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
            text-align: right;
        }
        .benchmark-label {
            font-size: 0.75rem;
            color: var(--muted);
            text-align: right;
        }

        /* Decision Box */
        .decision-box {
            background: var(--surface-2);
            border-radius: 10px;
            padding: 14px;
            border: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .decision-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .decision-badge {
            font-size: 0.85rem;
            font-weight: 800;
            padding: 5px 12px;
            border-radius: 6px;
            letter-spacing: 0.3px;
            text-transform: uppercase;
        }
        .decision-edge {
            font-size: 0.8rem;
            font-weight: 600;
            color: var(--muted);
        }
        .prob-bar-group {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        .prob-bar-labels {
            display: flex;
            justify-content: space-between;
            font-size: 0.8rem;
            font-family: 'JetBrains Mono', monospace;
        }
        .prob-bar {
            height: 10px;
            border-radius: 50px;
            background: rgba(239, 68, 68, 0.3);
            display: flex;
            overflow: hidden;
        }
        .prob-bar-yes {
            background: var(--up);
            height: 100%;
            transition: width 0.4s ease;
        }

        /* Round Metrics Table */
        .round-metrics {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            background: var(--surface-2);
            border-radius: 8px;
            padding: 12px;
            font-size: 0.85rem;
        }
        .metric-cell {
            display: flex;
            flex-direction: column;
        }
        .metric-label {
            color: var(--muted);
            font-size: 0.75rem;
        }
        .metric-val {
            font-family: 'JetBrains Mono', monospace;
            font-weight: 600;
            font-size: 0.95rem;
        }

        /* Next Round Widget */
        .next-round-box {
            background: rgba(99, 102, 241, 0.06);
            border: 1px dashed rgba(99, 102, 241, 0.3);
            border-radius: 8px;
            padding: 10px 12px;
            font-size: 0.8rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .next-round-label {
            color: var(--muted);
        }
        .next-round-val {
            font-weight: 700;
        }

        /* Prediction Horizon Table */
        .table-wrap {
            overflow-x: auto;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.82rem;
            margin-top: 4px;
        }
        th, td {
            text-align: left;
            padding: 6px 4px;
            border-bottom: 1px solid var(--border);
        }
        th {
            color: var(--muted);
            font-weight: 500;
        }
        td.num {
            font-family: 'JetBrains Mono', monospace;
        }

        /* News & Analysis Section */
        .news-section {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 20px;
            box-shadow: 0 8px 30px rgba(0,0,0,0.3);
        }
        .news-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }
        .news-list {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 12px;
        }
        .news-item {
            background: var(--surface-2);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 12px 14px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            gap: 8px;
            transition: border-color 0.2s;
        }
        .news-item:hover {
            border-color: rgba(255,255,255,0.2);
        }
        .news-title {
            font-size: 0.88rem;
            font-weight: 600;
            color: var(--text);
            text-decoration: none;
            line-height: 1.4;
        }
        .news-title:hover {
            color: var(--accent);
        }
        .news-meta {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.75rem;
            color: var(--muted);
        }
        .news-badges {
            display: flex;
            gap: 6px;
            align-items: center;
        }
        .badge {
            display: inline-block;
            padding: 2px 7px;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: 700;
            text-transform: uppercase;
        }
        .badge.up { background: var(--up-bg); color: var(--up); }
        .badge.down { background: var(--down-bg); color: var(--down); }
        .badge.neutral { background: var(--neutral-bg); color: var(--neutral); }
        .coin-pill {
            background: var(--surface-3);
            color: #d1d5db;
            padding: 1px 6px;
            border-radius: 3px;
            font-size: 0.68rem;
            font-weight: 600;
        }

        /* Collapsible Technical Drawer */
        .collapsible-toggle {
            background: none;
            border: 1px solid var(--border);
            color: var(--muted);
            padding: 8px 14px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.8rem;
            display: flex;
            align-items: center;
            gap: 6px;
            margin-top: 20px;
        }
        .collapsible-toggle:hover {
            color: var(--text);
            border-color: rgba(255,255,255,0.2);
        }
        .hl-drawer {
            display: none;
            margin-top: 16px;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 18px;
        }
        .hl-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 10px;
            margin-bottom: 14px;
        }
        .hl-item {
            background: var(--surface-2);
            padding: 10px;
            border-radius: 6px;
        }
        .hl-label { color: var(--muted); font-size: 0.72rem; }
        .hl-value { font-size: 0.95rem; font-weight: 600; font-family: 'JetBrains Mono', monospace; }
    </style>
</head>
<body>
    <header>
        <div class="header-left">
            <span class="logo-badge">KALSHI IQ</span>
            <h1>Crypto Prediction & Decision Terminal</h1>
        </div>
        <div class="header-meta">
            <div class="live-indicator">
                <span class="pulse-dot"></span>
                <span>CF BENCHMARKS RTI FEEDS LIVE</span>
            </div>
            <div id="last-updated">Connecting...</div>
        </div>
    </header>

    <!-- Top Round & Global News Bar -->
    <div class="top-banner">
        <div class="banner-card highlight">
            <div class="banner-title">
                <span>Active 15-Minute Kalshi Round</span>
                <span id="round-window" style="font-family:'JetBrains Mono', monospace; font-weight:600; color:#fff;">--:-- – --:-- UTC</span>
            </div>
            <div class="round-timer-row">
                <div>
                    <div class="countdown-digits" id="round-countdown">--:--</div>
                    <div class="round-sub" id="round-state">Tracking settlement minute</div>
                </div>
                <div style="text-align: right;">
                    <div class="round-sub">Next Round Opens In</div>
                    <div style="font-family:'JetBrains Mono', monospace; font-size:1.15rem; font-weight:600; color:var(--cyan);" id="next-round-countdown">--:--</div>
                </div>
            </div>
            <div class="progress-bar-container">
                <div class="progress-bar-fill" id="round-progress" style="width: 0%;"></div>
            </div>
        </div>

        <div class="banner-card">
            <div class="banner-title">
                <span>Global Crypto News Sentiment (5–17 Min Impact)</span>
                <span id="news-status" style="font-size:0.75rem;">Scanning 40+ headlines</span>
            </div>
            <div class="sentiment-score-row">
                <div class="sentiment-score-badge" id="global-sentiment-score">+0.00</div>
                <div style="flex:1;">
                    <div style="display:flex; justify-content:space-between; font-size:0.75rem; color:var(--muted); margin-bottom:2px;">
                        <span>BEARISH</span>
                        <span>NEUTRAL</span>
                        <span>BULLISH</span>
                    </div>
                    <div class="sentiment-meter">
                        <div class="sentiment-fill" id="sentiment-fill" style="left:50%; width:0%; background:var(--up);"></div>
                    </div>
                </div>
            </div>
            <div class="round-sub" style="margin-top: 8px;" id="news-velocity-sub">
                Velocity: 0 headlines in last 15 mins · Macro sentiment drift: Flat
            </div>
        </div>
    </div>

    <!-- 3 Core Coins: BTC, BNB, HYPE -->
    <div class="coins-grid" id="coins-container"></div>

    <!-- Live Breaking News Section -->
    <div class="news-section">
        <div class="news-header">
            <div>
                <h2 style="font-size:1.15rem; font-weight:700;">Breaking Crypto News & Market Sentiment</h2>
                <p style="color:var(--muted); font-size:0.8rem;">Real-time feed with weighted impact on upcoming 5–17 minute prediction cycles</p>
            </div>
            <div id="news-count-badge" class="coin-pill">0 articles indexed</div>
        </div>
        <div class="news-list" id="news-container"></div>
    </div>

    <!-- Collapsible Technical / Hyperliquid Drawer -->
    <button class="collapsible-toggle" onclick="toggleHLDrawer()">
        <span>&#9660; Toggle Advanced Hyperliquid On-Chain Data</span>
    </button>
    <div class="hl-drawer" id="hl-drawer">
        <h3 style="font-size:0.95rem; margin-bottom:12px; color:var(--muted);">Hyperliquid HYPE Market Metrics & Candles</h3>
        <div class="hl-grid" id="hl-grid"></div>
        <div class="table-wrap">
            <table>
                <thead><tr><th>Time</th><th>Open</th><th>High</th><th>Low</th><th>Close</th><th>Volume</th><th>Trades</th></tr></thead>
                <tbody id="hl-candles"></tbody>
            </table>
        </div>
    </div>

    <script>
        const COINS = ['btc', 'bnb', 'hype'];
        const REFRESH_INTERVAL_MS = 3000;

        function fmt(n, d=2) {
            if (n == null || isNaN(n)) return '-';
            return Number(n).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
        }

        function fmtUsd(n, d=2) {
            if (n == null || isNaN(n)) return '-';
            return '$' + fmt(n, d);
        }

        function pct(n, d=2) {
            if (n == null || isNaN(n)) return '-';
            const num = Number(n);
            return (num > 0 ? '+' : '') + num.toFixed(d) + '%';
        }

        function toggleHLDrawer() {
            const drawer = document.getElementById('hl-drawer');
            drawer.style.display = drawer.style.display === 'block' ? 'none' : 'block';
        }

        function renderCoinCard(coin, feed, kalshi) {
            const timing = kalshi && kalshi.timing ? kalshi.timing.current_round : {};
            const nextTiming = kalshi && kalshi.timing ? kalshi.timing.next_round : {};
            const pricing = kalshi && kalshi.pricing ? kalshi.pricing : {};
            const decision = kalshi && kalshi.decision ? kalshi.decision : {};
            const nextOutlook = kalshi && kalshi.next_round_outlook ? kalshi.next_round_outlook : {};

            const curPrice = pricing.current_price || (feed ? feed.price : 0);
            const openPrice = pricing.round_open_price || curPrice;
            const deltaUsd = pricing.delta_usd || 0;
            const deltaPct = pricing.delta_pct || 0;
            const deltaCls = deltaUsd >= 0 ? 'up' : 'down';

            const rec = decision.recommendation || 'CALCULATING...';
            const recColor = decision.badge_color || '#8b92a5';
            const probYes = decision.prob_yes_up != null ? decision.prob_yes_up : 0.50;
            const probNo = decision.prob_no_down != null ? decision.prob_no_down : 0.50;
            const edge = decision.edge_pct != null ? decision.edge_pct : 0.0;
            const conf = decision.confidence_pct != null ? decision.confidence_pct : 0;

            const series = kalshi ? kalshi.series : `KX${coin.toUpperCase()}15M`;
            const rtiName = kalshi ? kalshi.benchmark_index : 'CF Benchmarks RTI';

            // Multi-horizon rows (5m, 10m, 15m)
            const horizons = [5, 10, 15];
            let rows = '';
            for (const h of horizons) {
                const pred = feed && feed.predictions ? feed.predictions.find(p => p.horizon_minutes === h) : null;
                const pPrice = pred ? pred.predicted_price : '-';
                const chg = pred ? pred.change_percent : 0;
                const chgCls = chg > 0 ? 'up' : (chg < 0 ? 'down' : 'neutral');
                const pUp = pred && pred.prob_up != null ? (pred.prob_up * 100).toFixed(0) + '%' : '-';
                const pDown = pred && pred.prob_down != null ? (pred.prob_down * 100).toFixed(0) + '%' : '-';
                const newsSig = pred && pred.news_sentiment != null ? pred.news_sentiment : 0;
                rows += `<tr>
                    <td><strong>${h}m</strong></td>
                    <td class="num">${fmtUsd(pPrice, coin === 'hype' ? 4 : 2)}</td>
                    <td class="num"><span class="badge ${chgCls}">${pct(chg, 3)}</span></td>
                    <td class="num" style="color:var(--up);">${pUp}</td>
                    <td class="num" style="color:var(--down);">${pDown}</td>
                    <td class="num">${pct(newsSig * 10, 1)}</td>
                </tr>`;
            }

            return `
            <div class="coin-card" id="card-${coin}">
                <div class="coin-header">
                    <div>
                        <div class="coin-title-group">
                            <span class="coin-sym">${coin.toUpperCase()}</span>
                            <span class="coin-series-tag">${series}</span>
                        </div>
                        <div style="font-size:0.75rem; color:var(--muted); margin-top:2px;">${rtiName}</div>
                    </div>
                    <div>
                        <div class="coin-price">${fmtUsd(curPrice, coin === 'hype' ? 4 : 2)}</div>
                        <div class="benchmark-label">Live Benchmark Index</div>
                    </div>
                </div>

                <!-- Actionable Kalshi Decision Box -->
                <div class="decision-box">
                    <div class="decision-header">
                        <span class="decision-badge" style="background:${recColor}22; color:${recColor}; border:1px solid ${recColor}55;">
                            ${rec}
                        </span>
                        <span class="decision-edge">Edge: +${edge.toFixed(1)}% (Conviction ${conf}%)</span>
                    </div>

                    <div class="prob-bar-group">
                        <div class="prob-bar-labels">
                            <span style="color:var(--up);">YES (UP): ${(probYes * 100).toFixed(1)}%</span>
                            <span style="color:var(--down);">NO (DOWN): ${(probNo * 100).toFixed(1)}%</span>
                        </div>
                        <div class="prob-bar">
                            <div class="prob-bar-yes" style="width: ${probYes * 100}%;"></div>
                        </div>
                    </div>
                </div>

                <!-- 15-Minute Round Metrics -->
                <div class="round-metrics">
                    <div class="metric-cell">
                        <span class="metric-label">Round Open (Strike)</span>
                        <span class="metric-val">${fmtUsd(openPrice, coin === 'hype' ? 4 : 2)}</span>
                    </div>
                    <div class="metric-cell">
                        <span class="metric-label">Current Round Delta</span>
                        <span class="metric-val" style="color:var(--${deltaCls});">
                            ${deltaUsd >= 0 ? '+' : ''}${fmtUsd(deltaUsd, coin === 'hype' ? 4 : 2)} (${pct(deltaPct, 3)})
                        </span>
                    </div>
                    <div class="metric-cell">
                        <span class="metric-label">Projected Settlement</span>
                        <span class="metric-val">${fmtUsd(pricing.projected_settlement || curPrice, coin === 'hype' ? 4 : 2)}</span>
                    </div>
                    <div class="metric-cell">
                        <span class="metric-label">News Drift Factor</span>
                        <span class="metric-val" style="color:var(--cyan);">${pct(decision.news_drift_pct || 0, 3)}</span>
                    </div>
                </div>

                <!-- Next Upcoming Round (5-17m span) -->
                <div class="next-round-box">
                    <div>
                        <div class="next-round-label">NEXT ROUND (${nextTiming.label || 'Upcoming'})</div>
                        <div class="next-round-val" style="color:#fff;">${nextOutlook.suggested_action || 'Positioning...'}</div>
                    </div>
                    <div style="text-align:right;">
                        <span class="badge ${nextOutlook.bias && nextOutlook.bias.includes('UP') ? 'up' : (nextOutlook.bias && nextOutlook.bias.includes('DOWN') ? 'down' : 'neutral')}">
                            ${nextOutlook.bias || 'NEUTRAL'}
                        </span>
                    </div>
                </div>

                <!-- Horizon Predictions Table -->
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr><th>Span</th><th>Target Px</th><th>Predicted Move</th><th>P(Up)</th><th>P(Dn)</th><th>News Impact</th></tr>
                        </thead>
                        <tbody>${rows}</tbody>
                    </table>
                </div>
            </div>`;
        }

        function renderNews(newsData) {
            const listEl = document.getElementById('news-container');
            const articles = newsData.articles || [];
            document.getElementById('news-count-badge').textContent = `${newsData.total_articles || 0} articles indexed`;

            let html = '';
            for (const art of articles.slice(0, 9)) {
                const score = art.sentiment_score || 0;
                let badgeCls = 'neutral';
                let badgeLabel = 'NEUTRAL';
                if (score > 0.15) { badgeCls = 'up'; badgeLabel = `BULLISH +${score.toFixed(2)}`; }
                else if (score < -0.15) { badgeCls = 'down'; badgeLabel = `BEARISH ${score.toFixed(2)}`; }

                const ageMin = Math.round((art.age_seconds || 0) / 60);
                const ageText = ageMin < 1 ? 'Just now' : `${ageMin}m ago`;

                const coinPills = (art.coins || []).map(c => `<span class="coin-pill">${c.toUpperCase()}</span>`).join(' ');

                html += `
                <div class="news-item">
                    <div>
                        <div class="news-meta" style="margin-bottom:6px;">
                            <span style="color:var(--accent); font-weight:600;">${art.source}</span>
                            <span>${ageText}</span>
                        </div>
                        <a href="${art.link || '#'}" target="_blank" rel="noopener" class="news-title">${art.title}</a>
                    </div>
                    <div class="news-meta">
                        <div class="news-badges">
                            <span class="badge ${badgeCls}">${badgeLabel}</span>
                            ${coinPills}
                        </div>
                    </div>
                </div>`;
            }
            listEl.innerHTML = html || '<div style="color:var(--muted); padding:10px;">No recent breaking news fetched yet.</div>';

            // Update top news banner
            const gScore = newsData.global_sentiment || 0;
            const scoreBadge = document.getElementById('global-sentiment-score');
            scoreBadge.textContent = (gScore > 0 ? '+' : '') + gScore.toFixed(3);
            scoreBadge.style.color = gScore > 0.05 ? 'var(--up)' : (gScore < -0.05 ? 'var(--down)' : 'var(--neutral)');

            const fill = document.getElementById('sentiment-fill');
            const pctFill = Math.min(50, Math.abs(gScore) * 50);
            if (gScore >= 0) {
                fill.style.left = '50%';
                fill.style.width = pctFill + '%';
                fill.style.background = 'var(--up)';
            } else {
                fill.style.left = (50 - pctFill) + '%';
                fill.style.width = pctFill + '%';
                fill.style.background = 'var(--down)';
            }

            document.getElementById('news-velocity-sub').textContent =
                `Velocity: ${newsData.recent_15m_news_count || 0} breaking in last 15m · Total 30m: ${newsData.recent_30m_news_count || 0}`;
        }

        async function fetchAll() {
            try {
                // Fetch news
                const newsPromise = fetch('/news').then(r => r.ok ? r.json() : {});

                // Fetch coins and Kalshi data in parallel
                const coinPromises = COINS.map(async coin => {
                    const [feedRes, kalshiRes] = await Promise.all([
                        fetch(`/feed/${coin}`),
                        fetch(`/kalshi/${coin}`)
                    ]);
                    const feed = feedRes.ok ? await feedRes.json() : null;
                    const kalshi = kalshiRes.ok ? await kalshiRes.json() : null;
                    return { coin, feed, kalshi };
                });

                const [newsData, coinResults] = await Promise.all([newsPromise, Promise.all(coinPromises)]);

                // Render Top Round Countdown from the first coin's timing
                if (coinResults[0] && coinResults[0].kalshi && coinResults[0].kalshi.timing) {
                    const timing = coinResults[0].kalshi.timing.current_round;
                    const nextTiming = coinResults[0].kalshi.timing.next_round;

                    document.getElementById('round-window').textContent = timing.label;
                    const remSec = timing.remaining_seconds || 0;
                    const remMin = Math.floor(remSec / 60);
                    const remS = remSec % 60;
                    const countdownStr = `${String(remMin).padStart(2, '0')}:${String(remS).padStart(2, '0')}`;
                    document.getElementById('round-countdown').textContent = countdownStr;
                    document.getElementById('next-round-countdown').textContent = countdownStr;

                    const prog = timing.progress_pct || 0;
                    document.getElementById('round-progress').style.width = prog + '%';

                    if (remSec <= 60) {
                        document.getElementById('round-state').innerHTML = '<span style="color:var(--neutral); font-weight:700;">FINAL 60s TWAP SETTLEMENT IN PROGRESS</span>';
                    } else {
                        document.getElementById('round-state').textContent = `${(15 - (remSec/60)).toFixed(1)} mins elapsed into round`;
                    }
                }

                // Render Coin Cards
                let cardsHtml = '';
                for (const { coin, feed, kalshi } of coinResults) {
                    cardsHtml += renderCoinCard(coin, feed, kalshi);
                }
                document.getElementById('coins-container').innerHTML = cardsHtml;

                // Render News
                renderNews(newsData);

                document.getElementById('last-updated').textContent = 'Updated ' + new Date().toLocaleTimeString();

                // Render optional Hyperliquid details
                renderHL();

            } catch (err) {
                console.error("Dashboard refresh error:", err);
            }
        }

        async function renderHL() {
            try {
                const res = await fetch('/hl/hype');
                if (!res.ok) return;
                const data = await res.json();
                const snap = data.latest_snapshot || {};
                const items = [
                    ['Mark', snap.mark_px], ['Oracle', snap.oracle_px], ['Mid', snap.mid_px],
                    ['Funding', snap.funding], ['Open Interest', snap.open_interest],
                    ['Premium', snap.premium], ['Spread bps', snap.spread_bps],
                    ['Imbalance 5', snap.imbalance_5], ['Imbalance 20', snap.imbalance_20],
                    ['Day Vol USD', snap.day_ntl_vlm]
                ];
                let grid = '';
                for (const [label, val] of items) {
                    grid += `<div class="hl-item"><div class="hl-label">${label}</div><div class="hl-value">${val != null ? fmt(val, 4) : '-'}</div></div>`;
                }
                document.getElementById('hl-grid').innerHTML = grid;
                const candles = (data.candles_1m_tail || []).slice(-8).reverse();
                let tbody = '';
                for (const c of candles) {
                    tbody += `<tr>
                        <td>${new Date(c.timestamp).toLocaleTimeString()}</td>
                        <td class="num">${fmt(c.o, 3)}</td>
                        <td class="num">${fmt(c.h, 3)}</td>
                        <td class="num">${fmt(c.l, 3)}</td>
                        <td class="num">${fmt(c.c, 3)}</td>
                        <td class="num">${fmt(c.v, 1)}</td>
                        <td class="num">${c.n}</td>
                    </tr>`;
                }
                document.getElementById('hl-candles').innerHTML = tbody;
            } catch (e) {}
        }

        fetchAll();
        setInterval(fetchAll, REFRESH_INTERVAL_MS);
    </script>
</body>
</html>"""
