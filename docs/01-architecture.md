# Architecture — AI Investment Research Platform

> Bloomberg Terminal + Perplexity + ChatGPT + TradingView — research, not trading.
> The system explains WHY a recommendation exists. It never trades, never claims certainty.

## 1. High-Level System Diagram

```
                        ┌─────────────────────────────────────────┐
                        │              Next.js Frontend            │
                        │  (App Router, Shadcn, Recharts, WS)      │
                        └───────────────┬─────────────────────────┘
                                        │ HTTPS / WSS
                        ┌───────────────▼─────────────────────────┐
                        │            FastAPI Gateway               │
                        │   /api/v1/* (REST)   /ws/* (WebSocket)   │
                        └──────┬──────────────────────┬───────────┘
                               │                      │
              ┌────────────────▼───────┐   ┌──────────▼──────────┐
              │   Application Layer    │   │  Realtime Publisher │
              │  (Use Cases / Services)│   │  (Redis Pub/Sub)    │
              └────────────────┬───────┘   └──────────┬──────────┘
                               │                      │
        ┌──────────────────────▼──────────────────────▼──────────┐
        │                     Domain Layer                        │
        │   Entities · Value Objects · Domain Services · Events   │
        └──────────────────────┬──────────────────────────────────┘
                               │ ports (interfaces)
        ┌──────────────────────▼──────────────────────────────────┐
        │                 Infrastructure Layer                     │
        │  PostgreSQL │ Redis │ Qdrant │ AI Providers │ Market APIs │
        └───────────────────────────────────────────────────────────┘

        ┌───────────────────────────────────────────────────────────┐
        │            Celery Workers (agents run here)               │
        │  beat schedule → queues: data, analysis, ai, alerts       │
        └───────────────────────────────────────────────────────────┘
```

## 2. Clean Architecture Layers (backend)

Dependency rule: source code dependencies point **inward only**.

| Layer | Package | Contains | Depends on |
|---|---|---|---|
| Domain | `app/domain` | Entities, value objects, domain events, repository **interfaces** (ports), domain services | nothing |
| Application | `app/application` | Use cases, DTOs, agent orchestration, unit-of-work interface | domain |
| Infrastructure | `app/infrastructure` | SQLAlchemy repos, Redis cache, Qdrant client, AI provider adapters, market-data adapters, Celery tasks | application, domain |
| Presentation | `app/api` | FastAPI routers, WebSocket handlers, request/response schemas, auth middleware | application |

Cross-cutting: `app/core` (config, DI container, logging, errors, security primitives).

## 3. Bounded Contexts (DDD)

| Context | Aggregates | Notes |
|---|---|---|
| Identity | User | Auth, OAuth, JWT, roles |
| MarketData | Company, HistoricalPrice, MarketEvent | Ingestion-heavy, append-only price data |
| Intelligence | News, Technicals, Fundamentals, Indicator | Agent outputs, structured analysis |
| Research | ResearchReport, Recommendation, AIReasoning, Prediction | AI-generated, always with reasoning trail |
| Portfolio | Portfolio, PortfolioTransaction, Watchlist | User-owned aggregates |
| Alerting | Alert, Notification | Event-driven, realtime delivery |
| Learning | PredictionHistory, LearningData | Feedback loop for scoring calibration |

Contexts communicate through domain events (in-process) and Celery messages (cross-process). No context reaches into another's tables.

## 4. AI Provider Abstraction (core requirement)

```
domain/ports/ai_provider.py
    class AIProvider(Protocol):
        async def chat(request: ChatRequest) -> ChatResponse
        async def chat_structured(request, schema: type[BaseModel]) -> BaseModel
        async def embed(texts: list[str]) -> list[list[float]]

infrastructure/ai/
    registry.py          # name -> adapter class, reads settings.AI_PROVIDER
    router.py            # per-agent overrides, fallback chain, retries, cost log
    providers/
        gemini.py claude.py openai.py groq.py openrouter.py
        ollama.py deepseek.py mistral.py
```

Rules:
- **No agent ever imports a concrete provider.** Agents receive `AIProvider` via DI.
- Provider selected by env (`AI_PROVIDER=claude`), overridable per agent (`AI_PROVIDER__RESEARCH=openrouter`).
- Fallback chain: on provider failure, router tries the next configured provider.
- `chat_structured` handles JSON-mode/tool-use differences per provider so agents just get validated Pydantic models.

## 5. Agent Architecture

Agents are **application-layer services**, executed by Celery workers, each in its own module with a shared base:

```
application/agents/base.py     # AgentBase: run() lifecycle, input contract,
                               # output persistence, tracing, error policy
application/agents/<name>/     # one package per agent, max ~300 lines/file
```

Two kinds:
- **Deterministic** (no AI): technical_analysis, fundamental_analysis — pure Python, unit-testable math.
- **AI-powered**: news_intelligence, market_intelligence*, research, opportunity, recommendation, learning — call `AIProvider.chat_structured()` only.

(*market intelligence is hybrid: numeric feeds are deterministic, macro narrative uses AI.)

Every AI output is persisted with its full reasoning (`AIReasoning` table) — auditability is a product feature.

## 6. Data Flow (pipeline)

```
beat: every 1m  → data_collection(prices, news)         queue: data
beat: every 5m  → technicals, market snapshot           queue: analysis
beat: every 15m → news_intelligence (new articles)      queue: ai
beat: hourly    → fundamentals refresh, master score    queue: analysis
beat: daily     → research, opportunity, learning eval  queue: ai
event-driven    → recommendation (score change), alerts queue: alerts
```

Agents never call each other directly. Each reads its inputs from the DB (previous agents' persisted outputs) and writes its own — restartable, idempotent, independently scalable.

## 7. Realtime

- FastAPI WebSocket endpoint per topic: `/ws/prices`, `/ws/notifications`, `/ws/alerts`.
- Workers publish to Redis pub/sub channels; API nodes subscribe and fan out to sockets.
- Stateless API nodes → horizontal scaling to 100k users; sticky sessions not required.

## 8. Scalability Posture (100k+ users)

- Stateless API + JWT → scale API horizontally behind a load balancer.
- Read-heavy endpoints cached in Redis with short TTL (quotes 5s, scores 60s).
- Price history: monthly-partitioned table, covering index on (company_id, ts).
- Celery queues split by workload class so slow AI jobs never starve price refresh.
- Qdrant for news/report embeddings → semantic search without scanning Postgres.
- All AI calls metered (tokens, latency, cost) in a usage log for budgeting.

## 9. Non-Negotiables

- Max 300 lines per file. One responsibility per module.
- Every use case behind an interface; DI via lightweight container (`app/core/container.py`).
- Alembic for every schema change. No `create_all` in production paths.
- Recommendations always include uncertainty language + confidence + reasoning; UI renders the "why" before the "what".
- This platform must never place, suggest placing automatically, or execute trades.
