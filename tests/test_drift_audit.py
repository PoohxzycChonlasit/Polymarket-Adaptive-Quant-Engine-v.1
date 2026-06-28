"""Regression tests for tools/_drift_audit.py helpers.

Tests verify:
  T1  market_regime column maps to 0 UNKNOWN
  T2  COMPRESSION excluded from nc_PF end-to-end (with extreme-PnL discriminator)
  T3  legacy 'regime' column still resolves (dual-schema fallback)
  T4  missing required columns raises SystemExit (fail-loud guard)
  T5  n=70 fixture: all trades land in correct ISO week; phase buckets cover all 70

Offline/reporting only — no runtime imports, no strategy/risk/execution changes.
"""
from __future__ import annotations

import datetime

import pytest

import tools.audit._drift_audit as drift


# ---------------------------------------------------------------------------
# T1 — market_regime maps correctly, 0 UNKNOWN
# ---------------------------------------------------------------------------

def test_market_regime_maps_zero_unknown() -> None:
    """_regime() on market_regime-keyed rows produces 0 UNKNOWN."""
    rows = [
        {'market_regime': 'COMPRESSION'},
        {'market_regime': 'TREND_DOWN'},
        {'market_regime': 'SIDEWAY'},
        {'market_regime': 'TREND_UP'},
    ]
    results = [drift._regime(r) for r in rows]
    assert results == ['COMPRESSION', 'TREND_DOWN', 'SIDEWAY', 'TREND_UP']
    assert 'UNKNOWN' not in results


# ---------------------------------------------------------------------------
# T2 — COMPRESSION excluded from nc_PF
# ---------------------------------------------------------------------------

def test_compression_excluded_from_nc_pf() -> None:
    """_nc_pf uses only non-COMPRESSION trades.

    Two COMPRESSION entries carry +10.0 PnL each — if wrongly included, nc_PF
    would exceed 100.  Correct nc_PF (3 non-COMPRESSION trades, 2W/1L) = 2.5.
    The test asserts the correct value and confirms the inflation would be large,
    so a pass is never vacuous.
    """
    window = [
        {'regime': 'COMPRESSION', 'pnl': +10.0},  # must be excluded
        {'regime': 'COMPRESSION', 'pnl': +10.0},  # must be excluded
        {'regime': 'TREND_DOWN',  'pnl': +0.03},  # win
        {'regime': 'SIDEWAY',     'pnl': +0.02},  # win
        {'regime': 'TREND_UP',    'pnl': -0.02},  # loss
    ]
    result = drift._nc_pf(window)
    # Non-COMPRESSION wins=0.05, losses=0.02 → PF = 2.5
    assert result == pytest.approx(2.5)
    # Confirm that COMPRESSION inclusion would inflate materially
    all_wins   = [t['pnl'] for t in window if t['pnl'] > 0]
    all_losses = [t['pnl'] for t in window if t['pnl'] < 0]
    inflated_pf = sum(all_wins) / abs(sum(all_losses))
    assert inflated_pf > 100, 'Test fixture does not demonstrate meaningful distortion'


# ---------------------------------------------------------------------------
# T3 — legacy 'regime' fallback (dual-schema compatibility)
# ---------------------------------------------------------------------------

def test_dual_schema_fallback() -> None:
    """_regime() resolves correctly for all three input shapes."""
    # Legacy CSV (regime only)
    assert drift._regime({'regime': 'TREND_DOWN'}) == 'TREND_DOWN'
    # Canonical export (market_regime only)
    assert drift._regime({'market_regime': 'SIDEWAY'}) == 'SIDEWAY'
    # Both present: market_regime wins
    assert drift._regime({'market_regime': 'SIDEWAY', 'regime': 'COMPRESSION'}) == 'SIDEWAY'
    # Neither present → UNKNOWN
    assert drift._regime({}) == 'UNKNOWN'
    # Empty strings count as absent → UNKNOWN
    assert drift._regime({'market_regime': '', 'regime': ''}) == 'UNKNOWN'


# ---------------------------------------------------------------------------
# T4 — missing required columns raises SystemExit (fail-loud guard)
# ---------------------------------------------------------------------------

def test_missing_required_columns_raises_system_exit() -> None:
    """_validate_regime_column raises SystemExit when neither column is present."""
    with pytest.raises(SystemExit):
        drift._validate_regime_column(['asset', 'side', 'hold_seconds', 'pnl_usdc'])


def test_validate_passes_canonical_schema() -> None:
    """_validate_regime_column does not exit when market_regime is present."""
    drift._validate_regime_column(['asset', 'market_regime', 'pnl_usdc'])  # must not raise


def test_validate_passes_legacy_schema() -> None:
    """_validate_regime_column does not exit when regime is present (legacy CSV)."""
    drift._validate_regime_column(['asset', 'regime', 'pnl_usdc'])  # must not raise


def test_validate_raises_on_empty_fieldnames() -> None:
    """_validate_regime_column raises SystemExit on an empty or None fieldnames list."""
    with pytest.raises(SystemExit):
        drift._validate_regime_column([])
    with pytest.raises(SystemExit):
        drift._validate_regime_column(None)


# ---------------------------------------------------------------------------
# T5 — n=70 fixture: ISO week assignment and phase segmentation
# ---------------------------------------------------------------------------

def test_week_and_phase_correct_at_n70() -> None:
    """All 70 trades land in the correct ISO week; phase buckets cover all 70 with no gaps.

    Fixture: 70 consecutive dates starting 2026-05-20 (W21) through late July (W30+).
    The range deliberately crosses W23→W24 to exercise the hardcoded-boundary bug.
    """
    start = datetime.date(2026, 5, 20)
    dates = [(start + datetime.timedelta(days=i)).isoformat() for i in range(70)]
    assert len(dates) == 70

    # --- Week assignment ---
    week_bins: dict[str, list[str]] = {}
    for d in dates:
        w = drift._iso_week(d)   # date string '2026-MM-DD' is valid input
        week_bins.setdefault(w, []).append(d)

    assert 'WUNK' not in week_bins, 'Some valid dates produced sentinel week label WUNK'

    total_in_weeks = sum(len(v) for v in week_bins.values())
    assert total_in_weeks == 70, f'Week bins covered {total_in_weeks}/70 dates'

    # Every date must be assigned to its actual ISO week (not collapsed to W23)
    for label, assigned_dates in week_bins.items():
        for d in assigned_dates:
            d_obj = datetime.date.fromisoformat(d)
            _, actual_week, _ = d_obj.isocalendar()
            expected = f'W{actual_week:02d}'
            assert label == expected, (
                f'Date {d} (actual {expected}) was mislabeled {label}'
            )

    # Fixture must include W24+ to prove the regression is exercised
    assert any(label >= 'W24' for label in week_bins), (
        'Test fixture does not reach W24; cannot verify post-W23 mislabeling regression'
    )

    # --- Phase segmentation (n=70) ---
    buckets = drift._phase_buckets(70)
    assert len(buckets) == 3

    all_covered: set[int] = set()
    for _label, lo, hi in buckets:
        for idx in range(lo, hi + 1):
            assert idx not in all_covered, f'Index {idx} appears in multiple phase buckets'
            all_covered.add(idx)

    assert all_covered == set(range(1, 71)), (
        f'Phase buckets cover {len(all_covered)} indices; '
        f'missing: {set(range(1, 71)) - all_covered}'
    )


# ---------------------------------------------------------------------------
# Shared fixture row for _row_qualifies tests (T6, T7, T8)
# ---------------------------------------------------------------------------

_GOOD_ROW: dict = {
    'asset': 'ETH',
    'side': 'YES',
    'canonical_entry_lifecycle_phase': 'OPENING_SCAN',
    'hold_seconds': '49',
    'canonical_retained_flag': 'true',
    'trade_result': 'TP',
    'pnl_usdc': '0.005657',
    'market_regime': 'TREND_DOWN',
}


# ---------------------------------------------------------------------------
# T6 — canonical_retained_flag dedup guard
# ---------------------------------------------------------------------------

def test_row_qualifies_canonical_retained_flag() -> None:
    """canonical_retained_flag=false rows are excluded; true/absent/None rows are included.

    Dedup guard mirrors _mark_duplicates() in canonical_regime_export:
    a logical opportunity fired by two bot runs produces two rows with the same
    canonical_opportunity_key.  The export marks the later execution 'false'.
    The drift audit must honour this to stay aligned with canonical n.
    """
    # Retained row passes
    assert drift._row_qualifies({**_GOOD_ROW, 'canonical_retained_flag': 'true'})
    # Excluded duplicate is rejected
    assert not drift._row_qualifies({**_GOOD_ROW, 'canonical_retained_flag': 'false'})
    # Missing column defaults to included (legacy-CSV safety — no dedup column in old CSVs)
    no_flag = {k: v for k, v in _GOOD_ROW.items() if k != 'canonical_retained_flag'}
    assert drift._row_qualifies(no_flag)
    # None value also defaults to included (defensive — CSV DictReader always yields str)
    assert drift._row_qualifies({**_GOOD_ROW, 'canonical_retained_flag': None})
    # Case-insensitive: 'False' is also excluded
    assert not drift._row_qualifies({**_GOOD_ROW, 'canonical_retained_flag': 'False'})


# ---------------------------------------------------------------------------
# T7 — outcome quality gate
# ---------------------------------------------------------------------------

def test_row_qualifies_outcome_gate() -> None:
    """Rows without a resolved trade_result AND without pnl_usdc are excluded.

    Gate mirrors canonical_regime_export._cell_qualifies():
      trade_result in {TP, SL}  OR  pnl_usdc not empty  -> include
      neither satisfied -> exclude (open or unresolved trade)
    Either signal alone is sufficient.
    """
    # Both present: pass
    assert drift._row_qualifies({**_GOOD_ROW, 'trade_result': 'TP', 'pnl_usdc': '0.01'})
    assert drift._row_qualifies({**_GOOD_ROW, 'trade_result': 'SL', 'pnl_usdc': '-0.01'})
    # trade_result alone suffices (empty pnl)
    assert drift._row_qualifies({**_GOOD_ROW, 'trade_result': 'TP', 'pnl_usdc': ''})
    # pnl_usdc alone suffices (no trade_result)
    assert drift._row_qualifies({**_GOOD_ROW, 'trade_result': '', 'pnl_usdc': '0.01'})
    # Neither: excluded
    assert not drift._row_qualifies({**_GOOD_ROW, 'trade_result': '', 'pnl_usdc': ''})
    assert not drift._row_qualifies({**_GOOD_ROW, 'trade_result': '', 'pnl_usdc': None})
    # Other trade_result values are not treated as resolved
    assert not drift._row_qualifies({**_GOOD_ROW, 'trade_result': 'OPEN', 'pnl_usdc': ''})


# ---------------------------------------------------------------------------
# T8 — count reproduction: fixture with duplicate pair + unresolved row
# ---------------------------------------------------------------------------

def test_count_reproduction_canonical_filter() -> None:
    """_row_qualifies applied to a mixed fixture reproduces the 63->62 dedup mechanism.

    Fixture design (mirrors the N62_N63_RECONCILIATION_AUDIT duplicate pair):
      5 canonical qualifying rows                        -> all pass
      1 duplicate row (canonical_retained_flag='false') -> excluded by filter 5
      1 unresolved row (no trade_result, no pnl_usdc)   -> excluded by filter 6
    Expected qualifying count: 5.

    This test validates both new filters work together in a counting context,
    matching requirement #5 of the Patch Drift Audit Canonical Retained Filter task.
    """
    def _row(**overrides: object) -> dict:
        return {**_GOOD_ROW, **overrides}

    fixture: list[dict] = [
        # 5 canonical qualifying rows — varied result / pnl combinations
        _row(hold_seconds='30', canonical_retained_flag='true',
             trade_result='TP', pnl_usdc='0.005657'),
        _row(hold_seconds='45', canonical_retained_flag='true',
             trade_result='SL', pnl_usdc='-0.003000'),
        _row(hold_seconds='60', canonical_retained_flag='true',
             trade_result='TP', pnl_usdc=''),           # trade_result alone suffices
        _row(hold_seconds='20', canonical_retained_flag='true',
             trade_result='', pnl_usdc='0.004000'),     # pnl_usdc alone suffices
        _row(hold_seconds='90', canonical_retained_flag='true',
             trade_result='TP', pnl_usdc='0.010044'),
        # 1 duplicate — second execution of same opportunity (2026-05-28 pattern)
        _row(hold_seconds='55', canonical_retained_flag='false',
             trade_result='TP', pnl_usdc='0.010044'),
        # 1 unresolved — open trade; no outcome yet
        _row(hold_seconds='25', canonical_retained_flag='true',
             trade_result='', pnl_usdc=''),
    ]

    qualifying = [r for r in fixture if drift._row_qualifies(r)]
    assert len(qualifying) == 5, (
        f'Expected 5 qualifying rows; got {len(qualifying)}. '
        'Both dedup guard (filter 5) and outcome gate (filter 6) must be active.'
    )
