# API Specification — /api/v1

All responses envelope: `{ "data": ..., "meta": { pagination? }, "error": null }`.
Errors: RFC-7807-style `{ "error": { "code", "message", "details" } }`.
Auth: `Authorization: Bearer <access_jwt>`; refresh via httpOnly cookie.

## Auth
| Method | Path | Notes |
|---|---|---|
| POST | /auth/register | email+password |
| POST | /auth/login | returns access + sets refresh cookie |
| POST | /auth/refresh | rotate tokens |
| POST | /auth/logout | revoke refresh (jti blacklist in Redis) |
| GET  | /auth/google | OAuth redirect |
| GET  | /auth/google/callback | code exchange → tokens |
| GET  | /auth/me | current user |

## Companies & Markets
| GET | /companies?search=&sector=&page= | paginated directory |
| GET | /companies/{symbol} | profile + latest score |
| GET | /companies/{symbol}/prices?interval=1d&from=&to= | OHLCV |
| GET | /companies/{symbol}/technicals?interval= | latest snapshot + signals |
| GET | /companies/{symbol}/fundamentals?period= | ratio history |
| GET | /companies/{symbol}/news?page= | analyzed articles |
| GET | /companies/{symbol}/research | latest report (sectioned) |
| GET | /companies/{symbol}/recommendation | active rec + score breakdown |
| GET | /companies/{symbol}/predictions | history + accuracy stats |
| GET | /companies/{symbol}/competitors | peer comparison |
| GET | /markets/overview | indices, breadth, fear&greed, vix, rates, oil, gold, btc |
| GET | /markets/movers?type=gainers|losers | top movers |
| GET | /markets/sectors | sector heat |
| GET | /markets/events?from=&to= | earnings calendar, macro events |

## Research & AI
| GET | /research/opportunities | Opportunity Agent output, ranked |
| POST | /research/reports/{symbol}/generate | enqueue Research Agent (202 + task id) |
| GET | /research/tasks/{task_id} | job status |
| GET | /recommendations?min_score=&sector= | screener over active recs |
| GET | /predictions/leaderboard | accuracy by sector/horizon/model |

## Portfolio & Watchlists
| GET/POST | /portfolios · GET/PATCH/DELETE /portfolios/{id} |
| POST | /portfolios/{id}/transactions | record buy/sell (bookkeeping only) |
| GET | /portfolios/{id}/analytics | P&L, allocation, diversification, risk score, health, rebalancing suggestions |
| GET/POST | /watchlists · DELETE /watchlists/{id} |
| POST/DELETE | /watchlists/{id}/items/{symbol} |

## Alerts & Notifications
| GET/POST | /alerts · PATCH/DELETE /alerts/{id} |
| GET | /notifications?unread= · POST /notifications/read-all |

## Admin (role=admin)
| GET | /admin/stats | users, jobs, AI spend |
| GET | /admin/ai-usage?provider=&from= | usage log |
| POST | /admin/agents/{name}/run | manual trigger |
| GET/PATCH | /admin/settings | provider selection, score weights |

## WebSocket
| /ws/prices?symbols=AAPL,MSFT | tick: `{symbol, price, change_pct, ts}` |
| /ws/notifications | authenticated; `{type, title, body, payload}` |
| /ws/alerts | alert-trigger stream for open dashboards |

Handshake: `?token=<access_jwt>` validated on connect; heartbeat ping/pong 30s;
server closes on token expiry, client silently re-connects with refreshed token.

## Conventions
- Pagination: `?page=&size=` → `meta: {page, size, total}`.
- Rate limits (Redis sliding window): anon 30/min, user 120/min, admin unlimited.
- All AI-generated payloads include `confidence`, `uncertainty_note`, `reasoning_ref`.
- Versioning: breaking changes → /api/v2, v1 kept during deprecation window.
