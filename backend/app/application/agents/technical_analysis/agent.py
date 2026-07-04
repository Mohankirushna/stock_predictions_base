"""Agent 3 — Technical Analysis. Pure Python, no AI: reads price history
already persisted by the Data Collection Agent (M6) and computes indicators,
support/resistance, trend, and signals into a TechnicalSnapshot per
company + interval.
"""
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.application.agents.base import AgentBase
from app.application.agents.technical_analysis import indicators, levels, signals
from app.application.agents.technical_analysis.trend import classify_trend
from app.domain.intelligence.technicals import Level, Signals, TechnicalSnapshot
from app.domain.market.price import PriceBar, PriceInterval
from app.domain.ports.unit_of_work import UnitOfWork

_LOOKBACK_DAYS = 400  # enough daily bars for EMA-200 to warm up
_MIN_BARS = 20  # below this, indicators are too noisy to be meaningful


class TechnicalAnalysisAgent(AgentBase):
    name = "technical_analysis"

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        super().__init__()
        self._uow_factory = uow_factory

    async def _execute(
        self, symbols: list[str], *, interval: PriceInterval = PriceInterval.D1
    ) -> dict[str, Any]:
        computed, skipped = 0, []
        end = datetime.now(UTC)
        start = end - timedelta(days=_LOOKBACK_DAYS)

        async with self._uow_factory() as uow:
            for symbol in symbols:
                company = await uow.companies.get_by_symbol(symbol)
                if company is None:
                    skipped.append(symbol)
                    continue
                bars = await uow.prices.get_bars(company.id, interval, start, end)
                if len(bars) < _MIN_BARS:
                    skipped.append(symbol)
                    continue
                snapshot = build_snapshot(company.id, interval, bars)
                await uow.technicals.save_snapshot(snapshot)
                computed += 1
            await uow.commit()

        return {"computed": computed, "skipped": skipped}


def build_snapshot(company_id: UUID, interval: PriceInterval, bars: Sequence[PriceBar]) -> TechnicalSnapshot:
    """Bars must be chronological (oldest→newest) — matches PriceRepository.get_bars ordering."""
    opens = [float(b.open) for b in bars]
    highs = [float(b.high) for b in bars]
    lows = [float(b.low) for b in bars]
    closes = [float(b.close) for b in bars]
    volumes = [float(b.volume) for b in bars]

    ema20_series = indicators.ema_series(closes, 20)
    ema50_series = indicators.ema_series(closes, 50)
    ema200_series = indicators.ema_series(closes, 200)
    ema20 = ema20_series[-1] if ema20_series else None
    ema50 = ema50_series[-1] if ema50_series else None
    ema200 = ema200_series[-1] if ema200_series else None

    macd_result = indicators.macd(closes)
    bb = indicators.bollinger_bands(closes)
    support, resistance = levels.find_levels(highs, lows)

    latest_close = closes[-1]
    golden, death = signals.detect_golden_death_cross(ema50_series, ema200_series)
    sig = Signals(
        golden_cross=golden,
        death_cross=death,
        breakout=signals.detect_breakout(latest_close, [lv.price for lv in resistance]),
        breakdown=signals.detect_breakdown(latest_close, [lv.price for lv in support]),
        volume_spike=signals.detect_volume_spike(volumes),
        patterns=tuple(signals.detect_candlestick_patterns(opens, highs, lows, closes)),
    )

    return TechnicalSnapshot(
        company_id=company_id, interval=interval, computed_at=datetime.now(UTC),
        ema_20=_dec(ema20), ema_50=_dec(ema50), ema_200=_dec(ema200),
        rsi_14=_dec(indicators.rsi(closes)),
        macd=_dec(macd_result[0]) if macd_result else None,
        macd_signal=_dec(macd_result[1]) if macd_result else None,
        macd_hist=_dec(macd_result[2]) if macd_result else None,
        atr_14=_dec(indicators.atr(highs, lows, closes)),
        vwap=_dec(indicators.vwap(highs, lows, closes, volumes)),
        bb_upper=_dec(bb[0]) if bb else None,
        bb_mid=_dec(bb[1]) if bb else None,
        bb_lower=_dec(bb[2]) if bb else None,
        support=[Level(Decimal(str(round(lv.price, 6))), lv.strength) for lv in support],
        resistance=[Level(Decimal(str(round(lv.price, 6))), lv.strength) for lv in resistance],
        trend=classify_trend(latest_close, ema20, ema50, ema200),
        signals=sig,
    )


def _dec(value: float | None) -> Decimal | None:
    return None if value is None else Decimal(str(round(value, 6)))
