# Runtime Reports Index — 2026-05-18

```
phase: Evidence Report Preservation Phase 6
generated_at: 2026-05-18
copy_only: true
source_dir: runtime/reports/
dest_dir: docs/research/sessions/2026-05-18/runtime_reports/
originals_preserved: yes
runtime_behavior_changed: No
live_behavior_changed: No
```

These are read-only copies of finalized offline analysis reports from `runtime/reports/`.
The originals remain in `runtime/reports/` (gitignored). These copies are the git-tracked permanent record.

---

## Copied Reports

### 1. risk_gate_transition_diagnosis_2026-05-18.md

| Field | Value |
|---|---|
| Source | `runtime/reports/risk_gate_transition_diagnosis_2026-05-18.md` |
| Copied filename | `risk_gate_transition_diagnosis_2026-05-18.md` |
| Size | 13 KB |
| Source date | 2026-05-18 10:03 |
| Original preserved | Yes |

**Purpose:** Diagnoses why RISK_GATE became the dominant bottleneck (94% of events) after the orderbook handoff patch cleared ORDERBOOK blocks. Classifies all 65 risk gate events into 4 protection types (max_entries_per_epoch, FINAL_DERISK cutoff, BTC confidence_too_low, max_active_positions). Concludes: no false blocking — all gates operating as designed. Documents 3 observability gaps.

**Session:** 2026-05-18 post-fix runtime observation (~9-minute window, 69 decision events)
**Related JSONL:** `runtime/quant_data/decision_log/2026-05-18.jsonl`

---

### 2. position_maturity_observation_2026-05-18.md

| Field | Value |
|---|---|
| Source | `runtime/reports/position_maturity_observation_2026-05-18.md` |
| Copied filename | `position_maturity_observation_2026-05-18.md` |
| Size | 14 KB |
| Source date | 2026-05-18 10:12 |
| Original preserved | Yes |

**Purpose:** Determines whether the runtime accumulates sufficient stabilized positions for Phase 3 (S3) assessment. Covers: 2 positions opened and closed (both ETH, both stop_loss), BTC confidence gap, MICRO_SURVIVAL sizing path, entry cap behavior, historical trade journal quality (May 08–14 close-only unusable, May 18 first paired evidence). Concludes: evidence accumulation resumed but not yet sufficient for S3.

**Session:** 2026-05-18 post-fix observation (2 ETH positions, $20.10 paper balance, mode=MICRO_SURVIVAL)
**Related JSONL:** `runtime/quant_data/trade_journal/2026-05-18.jsonl`, `risk_log/2026-05-18.jsonl`

---

### 3. paired_trade_evidence_quality_audit_2026-05-18.md

| Field | Value |
|---|---|
| Source | `runtime/reports/paired_trade_evidence_quality_audit_2026-05-18.md` |
| Copied filename | `paired_trade_evidence_quality_audit_2026-05-18.md` |
| Size | 23 KB |
| Source date | 2026-05-18 10:21 |
| Original preserved | Yes |

**Purpose:** Verifies May 18 trade_open/trade_close evidence is clean enough for future replay and maturity tracking. Cross-producer field comparison across decision_log, execution_log, trade_journal, risk_log. Finds: PnL arithmetic exact, pairing clean; candidate_trace_id diverges across producers (identity gap that drove the Paired Trade Identity Continuity Instrumentation v1 implementation). Documents `paper_trade_replay_key` as the recommended stable join key.

**Session:** 2026-05-18 paired evidence (2 ETH positions: inv_20260518_77fdc3512494, inv_20260518_bf04c81128f7)
**Related JSONL:** `runtime/quant_data/trade_journal/2026-05-18.jsonl`, `execution_log/2026-05-18.jsonl`

---

## Skipped Files

None. All 3 files in `runtime/reports/` were finalized human-readable `.md` reports and were copied.

`runtime/reports/multi_session_validation/` — directory does not exist (no multi-session runs completed yet).

---

## Verification

```
runtime/reports/ originals intact: YES (sizes match: 23118, 14171, 13084 bytes)
JSONL lines in copies: 0 (grep -c "^{" confirmed 0 for all 3 files)
Copies in git staging: pending (git add)
```
