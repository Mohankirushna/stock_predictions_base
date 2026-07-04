# Folder Structure

```
stocks_new/
├── docker-compose.yml
├── .env.example
├── ROADMAP.md
├── docs/                          # planning + living design docs
│
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   │   └── versions/
│   └── app/
│       ├── main.py                # FastAPI app factory only
│       │
│       ├── core/                  # cross-cutting
│       │   ├── config.py          # pydantic-settings, env-driven
│       │   ├── container.py       # DI container (wiring of ports→adapters)
│       │   ├── logging.py
│       │   ├── errors.py          # error hierarchy + handlers
│       │   └── security/          # jwt.py, oauth.py, passwords.py
│       │
│       ├── domain/                # NO external imports
│       │   ├── common/            # base Entity, ValueObject, DomainEvent
│       │   ├── identity/          # user entity, roles
│       │   ├── market/            # company, price, market_event
│       │   ├── intelligence/      # news, technicals, fundamentals, indicator
│       │   ├── research/          # recommendation, report, reasoning, prediction
│       │   ├── portfolio/         # portfolio, transaction, watchlist
│       │   ├── alerting/          # alert, notification
│       │   ├── learning/          # prediction_history, learning_data
│       │   └── ports/             # ALL interfaces: repositories, ai_provider,
│       │                          # market_data_source, cache, vector_store,
│       │                          # notifier, unit_of_work
│       │
│       ├── application/
│       │   ├── dto/               # request/response DTOs per context
│       │   ├── use_cases/         # one file per use case, grouped by context
│       │   │   ├── identity/  market/  research/  portfolio/  alerting/
│       │   ├── agents/
│       │   │   ├── base.py
│       │   │   ├── data_collection/
│       │   │   ├── news_intelligence/
│       │   │   ├── technical_analysis/     # pure python: indicators/, patterns/, levels/
│       │   │   ├── fundamental_analysis/   # pure python: ratios/, growth/, dividends/
│       │   │   ├── market_intelligence/
│       │   │   ├── research/
│       │   │   ├── opportunity/
│       │   │   ├── recommendation/
│       │   │   ├── portfolio/
│       │   │   ├── alert/
│       │   │   └── learning/
│       │   └── scoring/           # master score composition (weights, normalizers)
│       │
│       ├── infrastructure/
│       │   ├── db/                # engine, session, UoW impl, base model
│       │   │   └── models/        # SQLAlchemy models per context
│       │   ├── repositories/      # port implementations, per context
│       │   ├── ai/
│       │   │   ├── registry.py  router.py  usage_log.py
│       │   │   └── providers/     # gemini.py claude.py openai.py groq.py
│       │   │                      # openrouter.py ollama.py deepseek.py mistral.py
│       │   ├── market_data/       # yfinance/alpha-vantage/finnhub adapters + interface impl
│       │   ├── cache/             # redis client, cache port impl
│       │   ├── vector/            # qdrant client, embeddings store
│       │   ├── notifications/     # websocket publisher, email stub
│       │   └── tasks/             # celery app, beat schedule, task defs per queue
│       │
│       ├── api/
│       │   ├── deps.py            # FastAPI dependencies (auth, DI bridges)
│       │   ├── v1/                # routers: auth, users, companies, markets,
│       │   │                      # news, research, recommendations, portfolios,
│       │   │                      # watchlists, alerts, predictions, admin
│       │   └── ws/                # prices.py, notifications.py, manager.py
│       │
│       └── tests/
│           ├── unit/              # domain + agents (deterministic ones fully covered)
│           ├── integration/       # repos against test DB
│           └── api/               # httpx endpoint tests
│
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── next.config.mjs
    ├── tailwind.config.ts
    └── src/
        ├── app/                   # App Router
        │   ├── (auth)/login  register
        │   ├── (app)/dashboard  markets  companies/[symbol]  portfolio
        │   │        research  watchlist  alerts  predictions  leaderboard
        │   │        settings  admin
        │   └── layout.tsx
        ├── components/
        │   ├── ui/                # shadcn primitives
        │   ├── charts/            # candlestick, sparkline, score-gauge, allocation
        │   ├── company/  market/  portfolio/  research/  alerts/
        │   └── layout/            # sidebar, topbar, command palette
        ├── lib/
        │   ├── api/               # typed client per resource, fetch wrapper
        │   ├── ws/                # websocket hook + reconnect logic
        │   ├── auth/              # session, token refresh
        │   └── utils/
        ├── hooks/
        ├── stores/                # zustand slices (watchlist, prices, notifications)
        └── types/                 # shared API types (mirrors backend DTOs)
```

Rules: max 300 lines/file · one module = one responsibility · shared logic lives in the lowest layer that owns it, never duplicated.
