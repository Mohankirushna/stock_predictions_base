# Database Schema (PostgreSQL)

Conventions: UUID PKs (`id`), `created_at`/`updated_at` timestamptz on every table,
snake_case, FKs indexed, soft-delete only where noted. Alembic owns all migrations.

## Identity

**users**
- id, email (unique), hashed_password (nullable — OAuth-only users), full_name
- auth_provider enum(local, google), oauth_sub (nullable, unique with provider)
- role enum(user, admin), is_active, email_verified
- preferences jsonb (theme, notification settings)

## MarketData

**companies**
- id, symbol (unique, indexed), name, exchange, sector, industry, country
- market_cap numeric, currency, logo_url, description
- is_active, last_synced_at

**historical_prices**  *(partitioned by month on ts)*
- id, company_id FK, ts timestamptz, interval enum(1m,5m,1h,1d)
- open, high, low, close, volume numeric
- unique (company_id, ts, interval)

**market_events**
- id, event_type enum(earnings, dividend, split, fed_meeting, cpi, macro, other)
- company_id FK nullable (macro events have none), title, scheduled_at, importance smallint, payload jsonb

## Intelligence

**news**
- id, company_id FK nullable, source, url (unique), title, content text
- published_at, collected_at
- sentiment numeric(-1..1), importance smallint(0..10), summary text
- risks jsonb, opportunities jsonb, industry_impact jsonb, expected_impact text
- analyzed_at nullable (null = awaiting News Intelligence Agent), embedding_id (qdrant ref)

**technicals**  *(latest snapshot per company+interval; history in indicators)*
- id, company_id FK, interval, computed_at
- ema_20/50/200, rsi_14, macd, macd_signal, macd_hist, atr_14, vwap
- bb_upper, bb_mid, bb_lower
- support jsonb[], resistance jsonb[], trend enum(strong_up, up, neutral, down, strong_down)
- signals jsonb  — {golden_cross, death_cross, breakout, volume_spike, patterns[]}

**indicators**  *(time series of computed indicator values)*
- id, company_id FK, name, interval, ts, value numeric, meta jsonb
- index (company_id, name, interval, ts)

**fundamentals**
- id, company_id FK, period enum(quarterly, annual, ttm), fiscal_date
- revenue, revenue_growth_yoy, net_income, eps, eps_growth_yoy
- total_debt, debt_to_equity, free_cash_flow, operating_cash_flow
- roe, roa, pe, peg, gross_margin, operating_margin, net_margin
- institutional_ownership_pct, dividend_yield, dividend_payout_ratio
- unique (company_id, period, fiscal_date)

## Research

**research_reports**
- id, company_id FK, generated_by (agent name), ai_provider, ai_model
- sections jsonb — {competition, products, management, moat, industry,
  policies, growth, regulatory_risks, acquisitions, catalysts}
- summary text, embedding_id, version int

**recommendations**
- id, company_id FK, user_id FK nullable (null = platform-wide)
- action enum(strong_buy, buy, hold, reduce, avoid) — research guidance, not orders
- current_price, entry_zone_low, entry_zone_high, stop_loss
- take_profit_1/2/3, holding_period enum(swing, short, medium, long)
- confidence numeric(0..1), risk_reward numeric
- pros jsonb[], cons jsonb[], explanation text, uncertainty_note text (required)
- master_score numeric(0..100), score_breakdown jsonb
  — {news, technicals, fundamentals, momentum, institutional, risk, macro}
- ai_reasoning_id FK, status enum(active, expired, superseded)

**ai_reasoning**
- id, agent, ai_provider, ai_model, prompt_hash
- inputs_digest jsonb (what data the agent saw), raw_output text
- tokens_in/out int, latency_ms int, cost_usd numeric

**predictions**
- id, recommendation_id FK, company_id FK, predicted_at
- horizon enum(1d, 7d, 30d, 90d), expected_direction enum(up, down, sideways)
- expected_range_low/high, confidence

**prediction_history**  *(Learning Agent evaluations)*
- id, prediction_id FK, evaluated_at, horizon
- actual_price, hit_stop_loss bool, hit_tp1/tp2/tp3 bool
- max_drawdown_pct, max_gain_pct, direction_correct bool, accuracy_score numeric

**learning_data**
- id, scope enum(global, sector, agent, provider), key text
- metric jsonb (rolling accuracy, calibration curve, weight adjustments), window text

## Portfolio

**watchlists**
- id, user_id FK, name, is_default
**watchlist_items**
- id, watchlist_id FK, company_id FK, added_at, note — unique (watchlist_id, company_id)

**portfolios**
- id, user_id FK, name, base_currency, cash_balance numeric

**portfolio_transactions**
- id, portfolio_id FK, company_id FK, side enum(buy, sell)  *(user-recorded, never executed by us)*
- quantity, price, fees, executed_at, note

## Alerting

**alerts**
- id, user_id FK, company_id FK, alert_type enum(sentiment_shift, breakout,
  support_break, resistance_break, volume_spike, analyst_upgrade,
  confidence_change, price_target)
- condition jsonb, is_active, last_triggered_at, cooldown_minutes

**notifications**
- id, user_id FK, alert_id FK nullable, type, title, body
- payload jsonb, channel enum(ws, email), read_at nullable, sent_at

## Cross-cutting

- **ai_usage_log**: id, provider, model, agent, tokens_in/out, cost_usd, ts — budget dashboards.
- Qdrant collections: `news_embeddings`, `report_embeddings` (payload: postgres id, symbol, date).
- Redis keyspace: `quote:{symbol}` (TTL 5s), `score:{symbol}` (TTL 60s), `session:{jti}`, pub/sub channels `prices`, `notifs:{user_id}`.
