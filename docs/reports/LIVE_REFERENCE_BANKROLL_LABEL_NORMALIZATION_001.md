# LIVE_REFERENCE_BANKROLL_LABEL_NORMALIZATION_001

## 1. Observed Mismatch
Paper runs were reporting `valid_for_live_20_bankroll_claim: false` while local `live_reference_bankroll_usd` was evaluated as `10.0`. Retaining the hardcoded "20" in the validity label caused semantic mismatch and ambiguity in evidence logs, as it implied an arbitrary limit that didn't adapt to actual local constraints.

## 2. Fields Normalized
- **Replaced Field**: `valid_for_live_20_bankroll_claim` is superseded by `valid_for_live_reference_bankroll_claim`.
- **Target Objects Updated**: 
  - `BankrollState` inside `polymarket/trader.py`
  - `enrich_paper_accounting_telemetry()` mapping logic inside `polymarket/observability/paper_accounting_telemetry.py`
  - Output metrics inside `tools/canonical_run_evidence_summary_builder.py`

## 3. Compatibility Policy
- The legacy field `valid_for_live_20_bankroll_claim` is aliased backwards to `deprecated_valid_for_live_20_bankroll_claim`. 
- `deprecated_valid_for_live_20_bankroll_claim` dynamically returns `True` or `False` ONLY when `settings.account_balance == 20.0`. Otherwise it explicitly drops to `False`.
- The Canonical Builder is updated to check if `live_reference_bankroll_usd != 20.0` AND the deprecated claim field exists. If true, it attaches a `capital_reference_warning` indicating that the live basis deviates from the historical $20 claim logic.

## 4. Why No .env / Config Change Was Made
This normalization ensures the code safely parses and adapts to whatever is within the `.env`. Altering local `.env` parameters to mock a $20 environment would obscure real engine integration testing, effectively manipulating facts instead of resolving the telemetry structure flaw.

## 5. Why Extended Paper Runs Must Wait
Operating prolonged tests with logically corrupt or heavily mismatched fields breaks canonical parsing schemas. Accumulating 10,000+ lifecycle events under a "live_20_claim" tag against a `$10.0` parameter makes retroactive validation extremely brittle and invalidates trust in automated output structures.

## 6. Behavior Proofs
- **No Runtime Trading Behavior Change**: Modifications solely restricted to telemetry emitting dictionaries (`payload.setdefault`) and dataclass attributes (`BankrollState`). No order calculation thresholds were shifted.
- **No Strategy / EV Threshold Change**: `polymarket/risk_modes.py` and entry gates remained unadjusted.
- **Tests Validated**: Unit test `test_paper_accounting_telemetry.py` updated and asserts both the new `valid_for_live_reference_bankroll_claim` operation and the `capital_reference_warning` generation accurately.

## 7. Next Steps
- Extended paper sessions can now proceed safely, capturing evidence fully detached from static "20" definitions, ensuring canonical builders evaluate reality correctly.
