# UI Wireframes — dark, TradingView-inspired

Design system: near-black canvas `#0B0E14`, panel `#11151F`, border `#1E2530`,
text `#E6EAF2`/`#8B93A7`, bull `#16C784`, bear `#EA3943`, accent `#4C8DFF`.
Inter for UI, JetBrains Mono for prices. Framer Motion for panel/score transitions.
Shell: fixed left sidebar (icons + labels), topbar with global symbol search (⌘K), notification bell (live badge), provider/status dot.

## Dashboard (home)
```
┌ Sidebar ┬──────────────────────────────────────────────────────────┐
│ Dash    │ Market overview strip: S&P · NASDAQ · VIX · F&G · BTC     │
│ Markets ├───────────────────────────────┬──────────────────────────┤
│ Company │ AI Opportunities (cards:      │ Trending news feed        │
│ Portfol │  score gauge, catalyst chips, │ (sentiment dot, importance│
│ Researc │  confidence bar, WHY link)    │  badge, source, time)     │
│ Watchl  ├───────────────┬───────────────┼──────────────────────────┤
│ Alerts  │ Top gainers   │ Top losers    │ Upcoming earnings         │
│ Predict ├───────────────┴───────────────┼──────────────────────────┤
│ Leaderb │ Most bullish (score≥75)       │ Most bearish (score≤25)  │
│ Settings└───────────────────────────────┴──────────────────────────┘
```

## Company page — the flagship
```
Header: LOGO AAPL · Apple Inc · $189.34 ▲1.2% (live) · sector chip · [＋Watchlist] [Alert]
────────────────────────────────────────────────────────────────────
│ Candlestick chart (Recharts, intervals 1D 1W 1M 1Y)               │
│ overlays: EMA20/50/200, BB · panes: RSI, MACD, volume             │
│ chart annotations: entry zone band, SL line, TP1/2/3 lines        │
────────────────┬───────────────────────────────────────────────────
│ AI Rec card   │ Master Score 78/100 (radial gauge)                │
│ action BUY*   │ breakdown bars: News Tech Fund Mom Inst Risk Macro│
│ entry 185–188 │ *tooltip: "research guidance, not financial advice"│
│ SL 179        │ Why? → expandable reasoning (pros/cons/uncertainty)│
│ TP 195/204/218│                                                    │
────────────────┴───────────────────────────────────────────────────
Tabs: News · Technicals · Financial Statements · AI Research ·
      Competitors · Prediction History (accuracy %, hit/miss timeline)
```

## Portfolio
- Summary row: total value, day P&L, total P&L, risk score dial, health grade (A–F).
- Donut: sector exposure · treemap: allocation · line: value history.
- Holdings table with live prices; drawer per holding = mini company view.
- "Rebalancing suggestions" panel — AI text with reasons, never auto-executes.

## Research
- Report library (filter by symbol/date/provider) + "Generate report" action with async progress.
- Report reader: sectioned nav (Moat, Competition, Management, Catalysts, Risks…), citation chips to source news.

## Watchlist
- Dense live table: price, day%, score sparkline (7d), signal chips (⚡breakout, ☠ death-cross), alert shortcuts. Multiple named lists as tabs.

## Alerts / Predictions / Leaderboard
- Alerts: rule builder (type → condition → cooldown), trigger history timeline.
- Predictions: table of past calls with outcome badges (hit TP2 ✓, stopped ✗), calibration chart (confidence vs realized accuracy).
- Leaderboard: accuracy ranked by sector, horizon, and AI provider — transparency about model performance.

## Settings / Admin
- Settings: profile, theme, notification channels, default watchlist.
- Admin: AI provider picker + fallback order, per-agent model override, score-weight sliders, spend dashboard, agent run console with last-run status.

Realtime behavior: price cells flash green/red on tick; notification bell streams via WS with toast; score gauge animates on change.
Every AI element follows the rule: **claim → confidence → reasoning link**, uncertainty always visible.
