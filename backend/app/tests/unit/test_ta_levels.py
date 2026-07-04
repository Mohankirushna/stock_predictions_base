from app.application.agents.technical_analysis.levels import find_levels


def test_finds_clustered_support_and_resistance() -> None:
    # window=1: a bar is a pivot low/high if it's the extreme of itself and
    # its immediate neighbors. lows has pivots at i=1 (9), i=3 (8), i=5 (9);
    # clustering (1.5%) merges the two 9s into one level of strength 2.
    lows = [10, 9, 10, 8, 10, 9, 10]
    highs = [12, 13, 12, 14, 12, 13, 12]

    support, resistance = find_levels(highs, lows, window=1, cluster_pct=0.015, max_levels=3)

    assert support[0].price == 9
    assert support[0].strength == 2
    assert support[1].price == 8
    assert support[1].strength == 1

    assert resistance[0].price == 13
    assert resistance[0].strength == 2
    assert resistance[1].price == 14
    assert resistance[1].strength == 1


def test_no_pivots_returns_empty_lists() -> None:
    # Strictly monotonic — no local extremes anywhere.
    values = list(range(10))
    support, resistance = find_levels(values, values, window=2)
    assert support == []
    assert resistance == []


def test_max_levels_caps_output() -> None:
    lows = [10, 5, 10, 4, 10, 3, 10, 2, 10, 1, 10]
    highs = [x + 20 for x in lows]
    support, _ = find_levels(highs, lows, window=1, max_levels=2)
    assert len(support) <= 2


def test_levels_sorted_by_strength_descending() -> None:
    lows = [10, 9, 10, 8, 10, 9, 10, 9, 10]
    highs = [x + 5 for x in lows]
    support, _ = find_levels(highs, lows, window=1, cluster_pct=0.015)
    strengths = [lv.strength for lv in support]
    assert strengths == sorted(strengths, reverse=True)
