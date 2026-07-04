# Project Roadmap — AI Investment Research Platform

Status legend: ✅ done · 🔨 in progress · ⬜ pending

## Phase 0 — Planning ✅
- ✅ Architecture ([docs/01-architecture.md](docs/01-architecture.md))
- ✅ Folder structure ([docs/02-folder-structure.md](docs/02-folder-structure.md))
- ✅ Database schema ([docs/03-database-schema.md](docs/03-database-schema.md))
- ✅ API specification ([docs/04-api-spec.md](docs/04-api-spec.md))
- ✅ UI wireframes ([docs/05-ui-wireframes.md](docs/05-ui-wireframes.md))
- ✅ Agent interactions ([docs/06-agent-interactions.md](docs/06-agent-interactions.md))

## Phase 1 — Backend Foundation ✅
- ✅ M1: Core skeleton
  - pyproject, Dockerfile, docker-compose (postgres, redis, qdrant, api, worker, beat)
  - app/core: config, logging, errors, DI container
  - app/main.py FastAPI factory + health endpoint · 8 tests passing
- ✅ M2: Domain layer — entities, value objects, ports (all interfaces incl. AIProvider) · 31 tests, lint clean
- ✅ M3: Database — 21 SQLAlchemy models, async engine, UoW + 16 repos, Alembic migration applied · 34 tests (3 integration vs live PG)
- ✅ M4: Auth — bcrypt hashing, JWT access/refresh with single-use rotation, revocation store port, register/login/refresh/logout/me, Google OAuth (authorize + callback) · 55 tests total, lint clean
- ✅ M5: AI provider layer — registry, fallback-chain router, per-agent overrides, 8 adapters (Gemini, Claude, OpenAI, Groq, OpenRouter, Ollama, DeepSeek, Mistral), usage log → ai_usage_log · 87 tests total, lint clean

## Phase 2 — Data & Deterministic Analysis ✅
- ✅ M6: Finnhub market-data adapter (quotes, history, profile, news, fundamentals-raw, ratings, insider trades) + AgentBase lifecycle + Data Collection Agent (Agent 1) — persists companies/prices/news, idempotent · 108 tests total, lint clean
- ✅ M7: Technical Analysis Agent (Agent 3) — pure Python EMA/RSI/MACD/ATR/VWAP/Bollinger, support/resistance clustering, trend classification, golden/death cross, breakout/breakdown, volume spikes, candlestick patterns · 151 tests total, lint clean
- ✅ M8: Fundamental Analysis Agent (Agent 4) — pure Python vendor-metric mapping (defensive multi-alias lookup) + genuine derivations (PEG, dividend payout ratio) · 181 tests total, lint clean
- ✅ M9: Celery app (worker+beat verified live against Redis), queue routing (data/analysis), beat schedule for M6-M8 agents, Redis cache adapter, Redis-backed token revocation (replacing the M4 in-memory store), real readiness ping · 182 tests total, lint clean

## Phase 3 — AI Agents
- ✅ M10: News Intelligence Agent (Agent 2) — Qdrant vector store adapter, pydantic structured-output schema, per-article resilience (one bad article doesn't sink the batch), best-effort embedding (search value-add, never undoes a successful analysis), every AI call logged to ai_reasoning, Celery task on the `ai` queue (every 15 min), real Qdrant readiness ping · 197 tests total, lint clean
- ✅ M11: Market Intelligence Agent (Agent 5) — hybrid: deterministic trend/sector/fear&greed/commodity proxies (pure Python) + AI macro narrative (graceful degradation on AI failure), Redis-cached MarketContext for downstream agents, hourly Celery task · 207 tests total, lint clean
- ✅ M12: Research Agent (Agent 6) — 10-section reports (missing section = validation error), context builder reading all upstream agent outputs with explicit "not available" gaps, 7-day freshness skip + force flag + version bump, report embeddings in Qdrant, daily pre-open Celery task · 214 tests total, lint clean
- ✅ M13: Opportunity Discovery Agent (Agent 7) — batched single-call market scan (excludes watchlisted companies, skips no-signal candidates), hallucinated-symbol rejection, Redis-cached ranked picks for the dashboard, daily pre-open Celery task · 225 tests total, lint clean
- ✅ M14: Master Score engine (admin-tunable weights via Redis override) + Recommendation Agent (Agent 8) — entry/stop/TP ladder, confidence cap, mandatory uncertainty note · 245 tests total, lint clean

## Phase 4 — User Features ✅
- ✅ M15: Companies/Markets/News/Research REST endpoints (health, auth, companies, markets, news, research, recommendations)
- ✅ M16: Watchlists + Portfolio + transactions + Portfolio Agent (Agent 9) analytics (allocation, sector exposure, diversification/risk scores, health grade, rebalancing suggestions)
- ✅ M17: Alert Agent (Agent 10) + notifications + WebSocket layer (prices, notifications, alerts channels; Redis pub/sub fan-out)
- ✅ M18: Learning Agent (Agent 11) + predictions + leaderboard endpoints (rolling accuracy by sector/horizon)
- ✅ M19: Admin endpoints (stats, AI usage log, agent console — run any agent on demand, score-weight overrides)

## Phase 5 — Frontend ✅
- ✅ M20: Next.js 16 scaffold — Tailwind v4, shadcn-style primitives, dark theme, app shell (sidebar/topbar/⌘K), auth pages + session
- ✅ M21: API client layer (envelope + 401 refresh-retry) + WS hooks + zustand stores
- ✅ M22: Dashboard (home) page — market strip, AI opportunities, trending news, movers, earnings calendar, bullish/bearish ranked lists
- ✅ M23: Company page — custom SVG candlestick chart with entry/stop/TP overlay, volume + RSI panes, AI recommendation card with score breakdown, 6-tab detail (news/technicals/financials/research/competitors/predictions)
- ✅ M24: Markets (sector heatmap, movers, macro calendar) + Companies directory + Watchlist (multi-list, live prices/scores) pages
- ✅ M25: Portfolio page — allocation/sector donut charts, health grade, rebalancing suggestions, transaction recording, holdings table
- ✅ M26: Research screener (opportunities + filterable recommendation list) + Predictions lookup + Leaderboard pages
- ✅ M27: Alerts (CRUD, active/paused toggle) + Notifications UI (realtime via the M17 WebSocket layer)
- ✅ M28: Settings (profile, admin shortcut) + Admin console (stats, score-weight editor, 10-agent run console, AI usage log) pages

## Phase 6 — Hardening ✅
- ✅ M29: Frontend Vitest + Testing Library harness (formatters, component regression tests) alongside the existing 340-test backend suite
- ✅ M30: Redis-backed per-IP rate limiting (tighter window on auth endpoints), request-ID middleware + structured-log correlation, reusable idempotent seed script (`backend/scripts/seed_demo.py`), root README · 348 backend tests total, lint clean
