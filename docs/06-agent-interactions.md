# Agent Interactions

Principle: agents are **decoupled through the database**. Each agent reads persisted
outputs of upstream agents and writes its own. No direct agent→agent calls.
Celery beat + domain events drive execution.

## Dependency graph

```
                      ┌──────────────────────┐
                      │ 1 Data Collection     │  (external APIs → DB)
                      └──┬────┬────┬────┬────┘
              prices/news│    │    │    │filings, holdings, ratings
        ┌────────────────┘    │    │    └───────────────┐
        ▼                     ▼    ▼                    ▼
┌───────────────┐  ┌────────────────┐  ┌─────────────────────┐
│ 3 Technical    │  │ 2 News Intel   │  │ 4 Fundamental        │
│   (pure py)    │  │   (AI, JSON)   │  │   (pure py)          │
└───────┬───────┘  └───────┬────────┘  └──────────┬──────────┘
        │                  │                      │
        │        ┌─────────▼────────┐             │
        │        │ 5 Market Intel    │ (macro: VIX, rates, F&G…)
        │        └─────────┬────────┘             │
        └─────────┬────────┴───────────┬──────────┘
                  ▼                    ▼
        ┌──────────────────┐  ┌──────────────────┐
        │ 6 Research (AI)   │  │ 7 Opportunity(AI)│ (scans beyond watchlists)
        └────────┬─────────┘  └────────┬─────────┘
                 └──────────┬──────────┘
                            ▼
                 ┌────────────────────┐     writes Recommendation +
                 │ 8 Recommendation    │──►  Prediction + AIReasoning +
                 │   (AI, master score)│     MasterScore breakdown
                 └──────┬───────┬─────┘
                        │       │
              ┌─────────▼──┐ ┌──▼──────────┐
              │ 9 Portfolio │ │ 10 Alert     │──► notifications → WS
              └────────────┘ └─────────────┘
                        ▲
              ┌─────────┴──────────┐
              │ 11 Learning         │ evaluates predictions at 1/7/30/90d,
              │  (feedback loop)    │ writes LearningData → adjusts score
              └────────────────────┘  weights & confidence calibration
```

## Contracts (Pydantic, versioned)

Every agent has `input.py` / `output.py` schemas. Key ones:

- **NewsAnalysis**: companies[], sentiment(-1..1), summary, importance(0-10), risks[], opportunities[], industry, expected_impact — `chat_structured` enforced.
- **TechnicalSnapshot**: indicator values + signals{golden_cross, death_cross, breakout, volume_spike, patterns[]} + support[]/resistance[] + trend.
- **FundamentalSnapshot**: ratios + growth + dividend metrics + institutional %.
- **MarketContext**: market_trend, sector_trends{}, fear_greed, vix, rates, oil, gold, btc, macro_events[].
- **ResearchReport**: 10 fixed sections (competition…catalysts), each with sources.
- **OpportunityList[]**: symbol, reasons[], confidence, catalysts[], risk, entry_zone.
- **RecommendationOutput**: price, entry zone, SL, TP1-3, holding_time, confidence, risk_reward, pros[], cons[], explanation, uncertainty_note (required non-empty).
- **LearningEvaluation**: per horizon — direction_correct, hit_sl/tp, max_drawdown, max_gain, accuracy_score.

## Master Score composition (`application/scoring/`)

```
score = Σ wᵢ · componentᵢ        components normalized to 0..100
weights (defaults, admin-tunable, Learning-Agent-adjusted):
  news .15 · technicals .20 · fundamentals .20 · momentum .15
  institutional .10 · risk .10 (inverted) · macro .10
```
Learning Agent nudges weights per sector within bounds [0.05, 0.30]; every
adjustment is stored in `learning_data` with the evidence window.

## Scheduling (Celery beat)

| Cadence | Tasks | Queue |
|---|---|---|
| 1 min | refresh prices (watchlisted+held first), collect news | data |
| 5 min | technicals recompute, market snapshot, watchlist scores | analysis |
| 15 min | news intelligence on unanalyzed articles (batch) | ai |
| 1 h | fundamentals sync, master-score refresh, portfolio analytics | analysis |
| daily pre-open | market intel full, research refresh (stale>7d), opportunity scan | ai |
| daily post-close | learning evaluation for due predictions | ai |
| event | recommendation regen on score delta >10; alert eval on any signal write | alerts |

## Failure policy

- Retries with exponential backoff (3x); AI tasks also rotate to fallback provider via router.
- Idempotency: tasks keyed by (agent, company, window) — duplicate beats no-op.
- A failed upstream agent degrades gracefully: Recommendation Agent runs with
  whatever inputs exist and lowers confidence + notes the missing input in
  `uncertainty_note` ("fundamentals stale: 9 days").
- Dead-letter queue + admin console visibility for every failed run.
