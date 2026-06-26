# GOVERNANCE_BOOTSTRAP_001_REFINED

## 1. Updated Registry Examples

### A. AUDIT_REGISTRY Example (`docs/research/AUDIT_REGISTRY.json`)
The registry has been updated to reflect the reclassification of `LOW_PRICE_EDGE_VALIDATION_001` to `PARTIAL`.

```json
{
  "audits": [
    {
      "audit_id": "RISK_PLAN_ZERO_FORENSIC_AUDIT_001",
      "title": "Analyze zero position-sizing skips in real-time execution loop",
      "owner": "Claude-3.5-Sonnet",
      "status": "VERIFIED",
      "verdict": "EDGE_REAL",
      "created_date": "2026-06-18",
      "last_updated": "2026-06-18",
      "superseded_by": null,
      "canonical": true,
      "next_action": "Incorporate confidence floor diagnostics into status monitoring"
    },
    {
      "audit_id": "LOW_PRICE_EDGE_VALIDATION_001",
      "title": "Verify expectation profile of contracts priced under 10 cents",
      "owner": "Claude-3.5-Sonnet",
      "status": "VERIFIED",
      "verdict": "EDGE_WEAK",
      "created_date": "2026-06-18",
      "last_updated": "2026-06-19",
      "superseded_by": null,
      "canonical": false,
      "next_action": "Investigate settlement truth resolution under active question LOW_PRICE_TRUTH_RESOLUTION_001"
    },
    {
      "audit_id": "SUB_5C_EXECUTION_REALITY_AUDIT",
      "title": "Forensic audit of executability gates for ask prices under 5 cents",
      "owner": "Claude-3.5-Sonnet",
      "status": "VERIFIED",
      "verdict": "OPEN_QUESTION",
      "created_date": "2026-06-18",
      "last_updated": "2026-06-19",
      "superseded_by": null,
      "canonical": false,
      "next_action": "Resolve official on-chain settlement keys before treating as executable"
    }
  ]
}
```

### B. DECISION_REGISTRY Example (`docs/research/DECISION_REGISTRY.json`)
Since `LOW_PRICE_TRUTH_RESOLUTION_001` remains open, the shadow sizer decision is corrected from `ACTIVE` to `PROPOSED`.

```json
{
  "decisions": [
    {
      "decision_id": "DEC_2026_06_18_SHADOW_SIZER_DESIGN",
      "evidence": "LOW_PRICE_EDGE_VALIDATION_001",
      "approved_by": "Operator",
      "status": "PROPOSED",
      "rationale": "Approve the development of a shadow-only sizer configuration to monitor simulated executability of contracts under 5 cents ask before any live activation.",
      "superseded_by": null
    }
  ]
}
```

---

## 2. Updated Research Authority Map

Categorization of completed audits by verification quality:

### A. CANONICAL (Highly Trusted / Source of Truth)
- **`REPLAY_METHODOLOGY_VALIDATION_001`**: verified payout, share math, and backtest settlement formulas.
- **`RISK_PLAN_ZERO_FORENSIC_001`**: verified real-time loop skippage metrics.
- **`CLOB_EMPTY_RESPONSE_FORENSIC_AUDIT`**: verified websocket warmup constraints.

### B. PARTIAL (Qualified Evidence / Incomplete Scope)
- **`EXECUTABLE_REALITY_AUDIT_001`**: initial liquidity parameters.
- **`SHADOW_SIZING_REPLAY_AUDIT_001`**: initial counterfactual sizing.
- **`LOW_PRICE_EDGE_VALIDATION_001`**: weakens low-price edge, but does not close the truth resolution question.

### C. OPEN_QUESTION (Under Active Investigation)
- **`SUB_5C_EXECUTION_REALITY_AUDIT`**: Gated by provisional proxy dependency.
- **`LOW_PRICE_TRUTH_RESOLUTION_001`**: On-chain token settlement check.

### D. SUPERSEDED (Obsolete / Do NOT Use)
- **All non-deduplicated replay reports**: Invalidated by duplication bias.
- **Early positive replay reports**: Invalidated by selection bias.
- **Obsolete HFT deployment reports**: Outdated by 5-minute market designs.

---

## 3. Active Question System V1 (`ACTIVE_QUESTION_SYSTEM_V1`)

To prevent multi-agent parallel investigations and scope sprawl, we enforce the following system rules:

1. **Strict Singularity**: `Maximum Active Questions = 1`. The repository must only focus on one active question at a time (recorded in `docs/research/ACTIVE_QUESTION.md`).
2. **Sequential Gate**: Before opening any new research frontier or hypothesis, the current active question must be closed.
3. **Allowed Closure States**: An active question can only transition to closed if the operator approves one of the following verdicts:
   - `EDGE_REAL`: Quantitative evidence confirms the edge is executable and profitable.
   - `REPLAY_ARTIFACT`: Evidence proves the findings are a simulation/replay bias.
   - `DATA_INSUFFICIENT`: Missing or corrupt logs make verification impossible.
   *No other state or verdict may close an active question.*

---

## 4. Governance Priority State (`PROJECT_PRIORITY_STATE`)

- **Current Priority State**: **Research Governance Buildout**
- **Current Active Question**: `LOW_PRICE_TRUTH_RESOLUTION_001`
- **Highest Priority**: Determine whether the sub-5c contract edge is **EDGE_REAL** (executable and backed by official settlement) or a **REPLAY_ARTIFACT** (dependent on snapshot proxies).
- **Core Governance Constraint**: No strategy logic, sizer weights, risk mode, or execution changes may be approved or implemented until `LOW_PRICE_TRUTH_RESOLUTION_001` is resolved.

---

## 5. Updated Implementation Sequence

1. **Registry Templates**: Create empty JSON skeletons for `docs/research/AUDIT_REGISTRY.json` and `docs/research/DECISION_REGISTRY.json`.
2. **Active Question File**: Create `docs/research/ACTIVE_QUESTION.md` containing `LOW_PRICE_TRUTH_RESOLUTION_001`.
3. **Core Rules Patch**: Insert the anti-loop checks, max polling limits, search pruning, and the *Active Question System V1* rules into `PROJECT_RULES.md`.
4. **Agent Rules Patch**: Insert registry check step and active question constraints into `AGENTS.md`.
