"""Beat schedule and queue routing — cadences from
docs/06-agent-interactions.md, limited to agents that exist so far (M6-M18).
"""
from celery.schedules import crontab

beat_schedule = {
    "collect-market-data": {"task": "data.collect_market_data", "schedule": 60.0},  # every 1 min
    "compute-technicals": {"task": "analysis.compute_technicals", "schedule": 300.0},  # every 5 min
    "compute-fundamentals": {"task": "analysis.compute_fundamentals", "schedule": crontab(minute=0)},  # hourly
    "analyze-news": {"task": "ai.analyze_news", "schedule": 900.0},  # every 15 min
    "market-intelligence": {"task": "ai.market_intelligence", "schedule": 3600.0},  # hourly snapshot
    # Daily pre-open; the agent itself skips reports fresher than 7 days.
    "refresh-research": {"task": "ai.refresh_research", "schedule": crontab(hour=8, minute=0)},
    "discover-opportunities": {"task": "ai.discover_opportunities", "schedule": crontab(hour=8, minute=30)},
    # The doc calls for event-driven regeneration "on score delta" — until
    # that event bus exists (needs M17's alerting infra), this periodic
    # fallback keeps recommendations from going stale.
    "generate-recommendations": {"task": "alerts.generate_recommendations", "schedule": 1800.0},
    # Same event-bus caveat as recommendations above: a periodic sweep
    # stands in for "on signal write" until a real event bus exists.
    "evaluate-alerts": {"task": "alerts.evaluate_alerts", "schedule": 300.0},
    "evaluate-predictions": {"task": "ai.evaluate_predictions", "schedule": crontab(hour=21, minute=0)},  # post-close
}

task_routes = {
    "data.*": {"queue": "data"},
    "analysis.*": {"queue": "analysis"},
    "ai.*": {"queue": "ai"},
    "alerts.*": {"queue": "alerts"},
}
