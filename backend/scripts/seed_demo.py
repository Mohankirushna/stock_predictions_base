"""Seeds a small, realistic demo dataset so every page in the frontend has
something real to render without waiting on the scheduled agents.

Idempotent: re-running skips any company that already exists by symbol.

Usage (from backend/, with the venv active and Postgres/Redis reachable):
    python scripts/seed_demo.py
"""
import asyncio
import random
import sys
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.container import container  # noqa: E402
from app.domain.common.values import PriceRange  # noqa: E402
from app.domain.intelligence.fundamentals import FundamentalSnapshot, Period  # noqa: E402
from app.domain.intelligence.market_context import CACHE_KEY as MARKET_CONTEXT_CACHE_KEY  # noqa: E402
from app.domain.intelligence.market_context import MarketContext  # noqa: E402
from app.domain.intelligence.news import NewsAnalysis, NewsArticle  # noqa: E402
from app.domain.intelligence.technicals import Level, Signals, TechnicalSnapshot, Trend  # noqa: E402
from app.domain.market.company import Company  # noqa: E402
from app.domain.market.market_event import EventType, MarketEvent  # noqa: E402
from app.domain.market.price import PriceBar, PriceInterval  # noqa: E402
from app.domain.ports.cache import Cache  # noqa: E402
from app.domain.ports.unit_of_work import UnitOfWork  # noqa: E402
from app.domain.research.opportunity import CACHE_KEY as OPPORTUNITIES_CACHE_KEY  # noqa: E402
from app.domain.research.opportunity import OpportunityCandidate  # noqa: E402
from app.domain.research.prediction import Direction, Horizon, Prediction  # noqa: E402
from app.domain.research.recommendation import Action, HoldingPeriod, Recommendation, ScoreBreakdown  # noqa: E402
from app.main import create_app  # noqa: E402

random.seed(7)  # reproducible demo data across runs


COMPANIES: list[dict] = [
    dict(
        symbol="NEBULA", name="Nebula Cloud Systems", exchange="NASDAQ", sector="Technology",
        industry="Cloud Infrastructure", start_price=180.0, drift=(0.2, 2.2), action=Action.STRONG_BUY,
        score=88.0, breakdown=dict(news=82, technicals=90, fundamentals=85, momentum=88, institutional=80, risk=60, macro=65),
        news_title="Nebula Cloud beats revenue estimates, raises full-year guidance",
        news_sentiment=0.7, news_importance=8,
        pros=["Accelerating enterprise cloud adoption", "Golden cross with rising volume", "Raised guidance two quarters running"],
        cons=["Premium valuation versus sector", "Customer concentration in top 10 accounts"],
    ),
    dict(
        symbol="QUANTA", name="Quanta Semiconductor", exchange="NASDAQ", sector="Technology",
        industry="Semiconductors", start_price=95.0, drift=(0.05, 1.8), action=Action.BUY,
        score=74.0, breakdown=dict(news=68, technicals=76, fundamentals=78, momentum=70, institutional=72, risk=55, macro=60),
        news_title="Quanta Semiconductor announces next-gen chip design win",
        news_sentiment=0.4, news_importance=6,
        pros=["New design win with a major OEM", "Improving gross margins"],
        cons=["Cyclical end-market exposure", "Elevated inventory levels"],
    ),
    dict(
        symbol="GREENGRID", name="GreenGrid Energy", exchange="NYSE", sector="Energy",
        industry="Renewable Power", start_price=42.0, drift=(-0.05, 1.2), action=Action.HOLD,
        score=52.0, breakdown=dict(news=50, technicals=48, fundamentals=55, momentum=50, institutional=52, risk=45, macro=55),
        news_title="GreenGrid Energy secures new solar farm contract",
        news_sentiment=0.15, news_importance=5,
        pros=["New long-term power purchase agreement"],
        cons=["Rate-sensitive balance sheet", "Regulatory subsidy uncertainty"],
    ),
    dict(
        symbol="MEDIVANT", name="Medivant Therapeutics", exchange="NASDAQ", sector="Healthcare",
        industry="Biotechnology", start_price=28.0, drift=(-0.15, 2.5), action=Action.REDUCE,
        score=38.0, breakdown=dict(news=30, technicals=35, fundamentals=45, momentum=30, institutional=40, risk=30, macro=50),
        news_title="Medivant Therapeutics trial results miss key secondary endpoint",
        news_sentiment=-0.55, news_importance=8,
        pros=["Deep pipeline beyond the lead candidate"],
        cons=["Lead trial missed a secondary endpoint", "Cash runway under 18 months", "Elevated dilution risk"],
    ),
    dict(
        symbol="RUSTBELT", name="Rustbelt Industrial Group", exchange="NYSE", sector="Industrials",
        industry="Heavy Machinery", start_price=61.0, drift=(-0.2, 1.5), action=Action.AVOID,
        score=24.0, breakdown=dict(news=20, technicals=22, fundamentals=28, momentum=18, institutional=30, risk=20, macro=45),
        news_title="Rustbelt Industrial warns on margin compression from input costs",
        news_sentiment=-0.5, news_importance=7,
        pros=["Order backlog remains at multi-year highs"],
        cons=["Margin compression from input costs", "Death cross on the daily chart", "Weak free cash flow conversion"],
    ),
    dict(
        symbol="FINCORE", name="FinCore Bancshares", exchange="NYSE", sector="Financials",
        industry="Regional Banking", start_price=54.0, drift=(0.08, 1.1), action=Action.BUY,
        score=70.0, breakdown=dict(news=62, technicals=68, fundamentals=75, momentum=65, institutional=70, risk=65, macro=58),
        news_title="FinCore Bancshares posts net interest margin expansion",
        news_sentiment=0.35, news_importance=5,
        pros=["Net interest margin expansion", "Improving efficiency ratio"],
        cons=["Regional loan book concentration"],
    ),
]


def _bars(company_id, start_price: float, drift: tuple[float, float], days: int, now: datetime) -> list[PriceBar]:
    price = start_price
    bars: list[PriceBar] = []
    for i in range(days, 0, -1):
        ts = now - timedelta(days=i)
        change = random.uniform(*drift) + random.uniform(-1.5, 1.5)
        open_p = price
        close_p = max(1.0, price + change)
        high_p = max(open_p, close_p) + random.uniform(0.1, 1.5)
        low_p = max(0.5, min(open_p, close_p) - random.uniform(0.1, 1.5))
        volume = random.randint(1_500_000, 9_000_000)
        bars.append(
            PriceBar(
                company_id=company_id, ts=ts, interval=PriceInterval.D1,
                open=Decimal(str(round(open_p, 2))), high=Decimal(str(round(high_p, 2))),
                low=Decimal(str(round(low_p, 2))), close=Decimal(str(round(close_p, 2))),
                volume=Decimal(volume),
            )
        )
        price = close_p
    return bars


async def _seed_company(uow: UnitOfWork, spec: dict, now: datetime) -> None:
    async with uow:
        existing = await uow.companies.get_by_symbol(spec["symbol"])
    if existing is not None:
        print(f"  {spec['symbol']}: already seeded, skipping")
        return

    company = Company(
        symbol=spec["symbol"], name=spec["name"], exchange=spec["exchange"], sector=spec["sector"],
        industry=spec["industry"], country="US", currency="USD",
        market_cap=Decimal(str(random.randint(2, 400))) * Decimal("1000000000"),
        description=f"{spec['name']} — demo data for the AI Investment Research Platform.",
        last_synced_at=now,
    )
    async with uow:
        await uow.companies.add(company)
        await uow.commit()

    bars = _bars(company.id, spec["start_price"], spec["drift"], 90, now)
    async with uow:
        await uow.prices.add_bars(bars)
        await uow.commit()

    last_close = float(bars[-1].close)
    trend = Trend.STRONG_UP if spec["score"] >= 80 else Trend.UP if spec["score"] >= 60 else (
        Trend.NEUTRAL if spec["score"] >= 45 else Trend.DOWN if spec["score"] >= 30 else Trend.STRONG_DOWN
    )

    async with uow:
        await uow.technicals.save_snapshot(
            TechnicalSnapshot(
                company_id=company.id, interval=PriceInterval.D1, computed_at=now,
                ema_20=Decimal(str(round(last_close * 0.98, 2))),
                ema_50=Decimal(str(round(last_close * 0.95, 2))),
                ema_200=Decimal(str(round(last_close * 0.88, 2))),
                rsi_14=Decimal(str(round(30 + spec["score"] * 0.5, 1))),
                macd=Decimal(str(round((spec["score"] - 50) / 25, 2))),
                macd_signal=Decimal(str(round((spec["score"] - 55) / 30, 2))),
                macd_hist=Decimal(str(round((spec["score"] - 50) / 60, 2))),
                atr_14=Decimal(str(round(last_close * 0.02, 2))),
                vwap=Decimal(str(round(last_close * 0.995, 2))),
                bb_upper=Decimal(str(round(last_close * 1.05, 2))),
                bb_mid=Decimal(str(round(last_close, 2))),
                bb_lower=Decimal(str(round(last_close * 0.95, 2))),
                trend=trend,
                signals=Signals(
                    golden_cross=spec["score"] >= 75, death_cross=spec["score"] <= 30,
                    breakout=spec["score"] >= 80, breakdown=spec["score"] <= 25,
                    volume_spike=spec["score"] >= 70 or spec["score"] <= 30,
                ),
                support=[Level(price=Decimal(str(round(last_close * 0.92, 2))), strength=3)],
                resistance=[Level(price=Decimal(str(round(last_close * 1.08, 2))), strength=2)],
            )
        )
        await uow.fundamentals.save(
            FundamentalSnapshot(
                company_id=company.id, period=Period.TTM, fiscal_date=date.today(),
                revenue=Decimal(str(random.randint(500, 20000))) * Decimal("1000000"),
                revenue_growth_yoy=Decimal(str(round(spec["score"] / 4, 1))),
                net_income=Decimal(str(random.randint(20, 3000))) * Decimal("1000000"),
                eps=Decimal(str(round(last_close / random.uniform(10, 30), 2))),
                eps_growth_yoy=Decimal(str(round(spec["score"] / 5, 1))),
                total_debt=Decimal(str(random.randint(100, 5000))) * Decimal("1000000"),
                debt_to_equity=Decimal(str(round(random.uniform(0.2, 1.5), 2))),
                free_cash_flow=Decimal(str(random.randint(10, 2000))) * Decimal("1000000"),
                operating_cash_flow=Decimal(str(random.randint(20, 2500))) * Decimal("1000000"),
                roe=Decimal(str(round(spec["score"] / 3, 1))),
                roa=Decimal(str(round(spec["score"] / 6, 1))),
                pe=Decimal(str(round(random.uniform(10, 35), 1))),
                peg=Decimal(str(round(random.uniform(0.8, 2.5), 2))),
                gross_margin=Decimal(str(round(random.uniform(30, 70), 1))),
                operating_margin=Decimal(str(round(random.uniform(10, 35), 1))),
                net_margin=Decimal(str(round(random.uniform(5, 25), 1))),
                institutional_ownership_pct=Decimal(str(round(random.uniform(40, 85), 1))),
                dividend_yield=Decimal(str(round(random.uniform(0, 2.5), 2))),
                dividend_payout_ratio=Decimal(str(round(random.uniform(0, 30), 1))),
            )
        )

        article = NewsArticle(
            source="Wire", url=f"https://example.com/news/{spec['symbol'].lower()}-1",
            title=spec["news_title"], content="...", published_at=now - timedelta(hours=random.randint(1, 48)),
            company_id=company.id,
        )
        article.attach_analysis(
            NewsAnalysis(
                sentiment=spec["news_sentiment"], importance=spec["news_importance"],
                summary=spec["news_title"], industry=spec["sector"],
                expected_impact="positive" if spec["news_sentiment"] > 0 else "negative",
            ),
            at=now,
        )
        await uow.news.add(article)

        entry_low = last_close * 0.96
        entry_high = last_close
        stop_loss = last_close * (0.90 if spec["action"] != Action.AVOID else 0.95)
        tp_mult = {Action.STRONG_BUY: (1.12, 1.22, 1.35), Action.BUY: (1.08, 1.15, 1.25)}.get(
            spec["action"], (1.05, 1.10, 1.15)
        )
        rec = Recommendation(
            company_id=company.id, action=spec["action"], current_price=Decimal(str(round(last_close, 2))),
            entry_zone=PriceRange(Decimal(str(round(entry_low, 2))), Decimal(str(round(entry_high, 2)))),
            stop_loss=Decimal(str(round(stop_loss, 2))),
            take_profit_1=Decimal(str(round(last_close * tp_mult[0], 2))),
            take_profit_2=Decimal(str(round(last_close * tp_mult[1], 2))),
            take_profit_3=Decimal(str(round(last_close * tp_mult[2], 2))),
            holding_period=HoldingPeriod.MEDIUM,
            confidence=min(0.9, max(0.4, spec["score"] / 100)),
            risk_reward=Decimal(str(round(random.uniform(1.2, 2.8), 2))),
            pros=spec["pros"], cons=spec["cons"],
            explanation=(
                f"{spec['name']} scores {spec['score']:.0f}/100 on the master score, driven by its "
                f"{spec['sector'].lower()} sector positioning and the technical/fundamental mix above. "
                f"See the pros and cons for the specific drivers behind this call."
            ),
            uncertainty_note="Demo research illustration — not investment advice; confidence is capped and macro conditions can shift quickly.",
            master_score=spec["score"],
            score_breakdown=ScoreBreakdown(**spec["breakdown"]),
        )
        await uow.recommendations.add(rec)
        await uow.flush()

        for horizon, days_ago, direction in [
            (Horizon.D30, 30, Direction.UP if spec["score"] >= 55 else Direction.DOWN),
            (Horizon.D7, 7, Direction.UP if spec["score"] >= 50 else Direction.SIDEWAYS),
            (Horizon.D1, 1, Direction.SIDEWAYS),
        ]:
            await uow.predictions.add(
                Prediction(
                    recommendation_id=rec.id, company_id=company.id,
                    predicted_at=now - timedelta(days=days_ago),
                    horizon=horizon, expected_direction=direction,
                    expected_range=PriceRange(
                        Decimal(str(round(last_close * 0.93, 2))), Decimal(str(round(last_close * 1.08, 2)))
                    ),
                    confidence=min(0.85, max(0.4, spec["score"] / 100)),
                    price_at_prediction=Decimal(str(round(last_close * 0.95, 2))),
                )
            )
        await uow.commit()
    print(f"  {spec['symbol']}: seeded ({spec['action'].value}, score {spec['score']:.0f})")


async def _seed_market_context(cache: Cache, now: datetime) -> None:
    context = MarketContext(
        market_trend=Trend.UP,
        fear_greed=58,
        vix=16.4,
        interest_rate_pct=4.25,
        oil=78.30,
        gold=2385.50,
        btc=68_400.0,
        sector_trends={
            "Technology": "up", "Energy": "neutral", "Healthcare": "down",
            "Industrials": "down", "Financials": "up",
        },
        narrative="Risk appetite remains constructive as megacap tech earnings beat estimates.",
        risks=("Sticky core inflation could delay rate cuts", "Geopolitical supply-chain disruption"),
        outlook="Cautiously bullish into the next earnings cycle, with breadth improving outside of megacaps.",
    )
    await cache.set(MARKET_CONTEXT_CACHE_KEY, context.to_dict(), ttl_seconds=6 * 3600)
    print("  market context: seeded")


async def _seed_opportunities(cache: Cache) -> None:
    candidates = [
        OpportunityCandidate(
            symbol="NEBULA", company_name="Nebula Cloud Systems",
            reasons=["Accelerating cloud revenue growth", "Raised full-year guidance", "Golden cross on daily chart"],
            confidence=0.78, catalysts=["Q3 earnings beat", "New enterprise contracts"],
            risk="Valuation is rich relative to sector peers",
            entry_zone_low=Decimal("175"), entry_zone_high=Decimal("185"),
        ),
        OpportunityCandidate(
            symbol="FINCORE", company_name="FinCore Bancshares",
            reasons=["Net interest margin expansion", "Improving efficiency ratio"],
            confidence=0.62, catalysts=["NIM expansion", "Loan growth reacceleration"],
            risk="Regional loan book concentration",
            entry_zone_low=Decimal("52"), entry_zone_high=Decimal("56"),
        ),
        OpportunityCandidate(
            symbol="QUANTA", company_name="Quanta Semiconductor",
            reasons=["New design win with a major OEM", "Margins troughing"],
            confidence=0.55, catalysts=["Design win ramp", "Inventory normalization"],
            risk="Cyclical end-market exposure",
            entry_zone_low=Decimal("90"), entry_zone_high=Decimal("98"),
        ),
    ]
    await cache.set(OPPORTUNITIES_CACHE_KEY, [c.to_dict() for c in candidates], ttl_seconds=6 * 3600)
    print(f"  opportunities: seeded ({len(candidates)})")


async def _seed_market_events(uow: UnitOfWork, now: datetime) -> None:
    async with uow:
        existing = await uow.market_events.between(now.date(), (now + timedelta(days=45)).date())
    if existing:
        print("  market events: already seeded, skipping")
        return

    async with uow:
        symbol_to_id = {}
        for spec in COMPANIES:
            company = await uow.companies.get_by_symbol(spec["symbol"])
            if company:
                symbol_to_id[spec["symbol"]] = company.id

        events = [
            MarketEvent(
                event_type=EventType.EARNINGS, title=f"{spec['name']} Q3 earnings call",
                scheduled_at=now + timedelta(days=random.randint(3, 30)),
                company_id=symbol_to_id.get(spec["symbol"]), importance=7,
            )
            for spec in COMPANIES
            if spec["symbol"] in symbol_to_id
        ]
        events.append(
            MarketEvent(
                event_type=EventType.FED_MEETING, title="FOMC rate decision",
                scheduled_at=now + timedelta(days=18), importance=9,
            )
        )
        events.append(
            MarketEvent(
                event_type=EventType.CPI, title="CPI inflation report",
                scheduled_at=now + timedelta(days=9), importance=8,
            )
        )
        for event in events:
            await uow.market_events.add(event)
        await uow.commit()
    print(f"  market events: seeded ({len(events)})")


async def main() -> None:
    create_app()
    uow = container.resolve(UnitOfWork)
    cache = container.resolve(Cache)
    now = datetime.now(UTC)

    print("Seeding demo companies…")
    for spec in COMPANIES:
        await _seed_company(uow, spec, now)

    print("Seeding market context…")
    await _seed_market_context(cache, now)

    print("Seeding opportunities…")
    await _seed_opportunities(cache)

    print("Seeding market events…")
    await _seed_market_events(uow, now)

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
