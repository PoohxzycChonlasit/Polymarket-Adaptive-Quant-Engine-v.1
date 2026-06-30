# QUERY-20260630-MARKET_AVAILABILITY_ENGINE_FALSE_NEGATIVE_REPAIR_001

## Metadata

query_id: QUERY-20260630-MARKET_AVAILABILITY_ENGINE_FALSE_NEGATIVE_REPAIR_001
query_timestamp: 2026-06-30T00:00:00Z
graph_version: SNAP-20260627-001
graph_files_read:
- docs/operations/knowledge_graph/REPO_GRAPH_NODES_001.jsonl
- docs/operations/knowledge_graph/REPO_GRAPH_EDGES_001.jsonl
- docs/operations/knowledge_graph/GRAPH_INDEX_001.json

## Scope

Target: `polymarket/market_availability_engine.py`

Required Class 6 queries:
- `safety_check(target)`
- `blast_radius(target)`
- `evidence_for_commit(prior_commit=4850a24f)`

## Safety Check

The seeded graph did not contain a node for `polymarket/market_availability_engine.py` or
`MarketAvailabilityEngine`. The graph search returned no direct matches for:

- `market_availability_engine`
- `MarketAvailabilityEngine`
- `gamma_fetcher`
- `GammaFetcher`
- `4850a24`

Fallback source checks were therefore required. The task target is a market-data scheduler
guard and does not touch the graph-protected permanent symbols:

- `_phase4_build_quote_lineage`
- `_phase4_quote_lineage_carry`
- `_last_quote_lineage_context`
- `_risk_plan_zero_diagnostics`
- `_diagnostic_float`
- `_diagnostic_int`
- live client order methods
- `.env`
- runtime data deletion
- execution/risk/sizing/reconciliation/wallet mutation paths

Safety findings: none for the scoped target. QS-010 is noted as a boundary constraint
because market availability is upstream of scan gating, but the planned repair does not
modify execution, risk, sizing, wallet, or order submission code.

## Blast Radius

Direct source-verified call path:

- `PolymarketTrader.__init__` creates `MarketAvailabilityEngine(self.settings)`.
- `PolymarketTrader.run_single_cycle()` calls `market_availability_engine.check()`.
- Non-`ACTIVE` availability returns early before market selection.
- `MarketAvailabilityResult.to_telemetry_payload()` is emitted as
  `log_market_availability_check`.

Blast radius score: MEDIUM.

Reason: the repair changes an upstream runtime data-availability gate that controls
whether the scanner proceeds. It does not alter order submission, execution, risk,
sizing, wallet/balance, reconciliation, strategy thresholds, or live flags.

## Evidence For Commit

Prior commit: `4850a24f619734f7790e2f0b504cabc77e398110`

Evidence:
- `docs/reports/MAIN_PAPER_RUNTIME_SMOKE_VERIFICATION_001.md`: paper runtime started,
  reached the decision loop, emitted telemetry, and shut down cleanly, but market data
  was degraded.
- `docs/reports/MARKET_DATA_ORDERBOOK_TRUE_EMPTY_RUNTIME_DIAGNOSTIC_001.md`: root cause
  classified as `AVAILABILITY_FALSE_NEGATIVE`; exact Gamma slug lookup and direct CLOB
  checks found active nonzero BTC/ETH books while MAE returned `MARKET_NOT_SCHEDULED`.
- Existing `tests/polymarket/test_market_availability_engine.py` covers broad scan
  ACTIVE/BETWEEN_EPOCHS/MARKET_NOT_SCHEDULED/API_UNAVAILABLE behavior.

Evidence grade: A+B+C.

## Execution Contract Attachment

```json
{
  "graph_query_id": "QUERY-20260630-MARKET_AVAILABILITY_ENGINE_FALSE_NEGATIVE_REPAIR_001",
  "graph_confidence": 0.72,
  "safety_findings_count": 0,
  "safety_findings": [],
  "affected_nodes_count": 4,
  "affected_edges_count": 3,
  "blast_radius_score": "MEDIUM",
  "safe_extraction_score": null,
  "recommended_workflow_tier": "LOOP",
  "fallback_required": true,
  "status": "PASS"
}
```

## Final Query Result

```json
{
  "$schema": "rkg_query_output_v1",
  "query_id": "QUERY-20260630-MARKET_AVAILABILITY_ENGINE_FALSE_NEGATIVE_REPAIR_001",
  "query_type": "safety_check|blast_radius|evidence_for_commit",
  "target": "polymarket/market_availability_engine.py",
  "status": "PASS",
  "safety_findings": [],
  "affected_nodes": [
    "polymarket/market_availability_engine.py",
    "polymarket/trader.py",
    "polymarket/gamma_fetcher.py",
    "tests/polymarket/test_market_availability_engine.py"
  ],
  "affected_edges": [
    "trader.__init__ creates MarketAvailabilityEngine",
    "run_single_cycle calls MarketAvailabilityEngine.check",
    "availability result emits market_availability_check telemetry"
  ],
  "evidence": [
    {
      "node_id": "docs/reports/MAIN_PAPER_RUNTIME_SMOKE_VERIFICATION_001.md",
      "grade": "A",
      "description": "paper smoke reached decision loop with market data degraded"
    },
    {
      "node_id": "docs/reports/MARKET_DATA_ORDERBOOK_TRUE_EMPTY_RUNTIME_DIAGNOSTIC_001.md",
      "grade": "A",
      "description": "diagnostic proved MAE false negative versus exact slug/direct CLOB checks"
    },
    {
      "node_id": "tests/polymarket/test_market_availability_engine.py",
      "grade": "C",
      "description": "existing offline tests cover broad scan behavior"
    }
  ],
  "recommended_workflow_tier": "LOOP",
  "stop_conditions": [],
  "confidence": 0.72,
  "evidence_grade": "A",
  "execution_contract_attachment": {
    "graph_query_id": "QUERY-20260630-MARKET_AVAILABILITY_ENGINE_FALSE_NEGATIVE_REPAIR_001",
    "graph_confidence": 0.72,
    "safety_findings_count": 0,
    "safety_findings": [],
    "affected_nodes_count": 4,
    "affected_edges_count": 3,
    "blast_radius_score": "MEDIUM",
    "safe_extraction_score": null,
    "recommended_workflow_tier": "LOOP",
    "fallback_required": true,
    "status": "PASS"
  }
}
```
