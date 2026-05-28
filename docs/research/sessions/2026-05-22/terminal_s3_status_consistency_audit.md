# Terminal S3 Status Consistency Audit

Date: 2026-05-22

Document type: read-only consistency audit.

Runtime behavior changed: No.
Live behavior changed: No.
Paper launch: No.
Replay run: No.
Code changed: No.
Tests run: none, docs-only.

---

## Scope

Determine whether the Terminal UI V2 label `S3 READY` is correct or misleading.

Reported terminal sample:

```
PolyTrade Execution Reality
...
Phase6 BLOCKED
S3 READY
```

Research evidence previously recorded:

```
S3 = CAUTION
No promotion
Evidence harvest mode
```

---

## Files Inspected

- `utils/display.py` — full render path for S3 label
- `tests/test_terminal_dashboard_display.py` — test fixture source
- `polymarket/trader.py` — `dashboard_probe_counts()` and runtime call sites
- `main.py` — display update call sites
- `docs/research/runtime_health/execution_reality_daily_monitor.md`
- `docs/research/sessions/2026-05-22/phase5_evidence_monitor.md`
- `docs/research/sessions/2026-05-21/warmup_session_maturation_audit.md`
- `docs/research/sessions/2026-05-21/model_visibility_entry_handoff_audit.md`
- `docs/research/sessions/2026-05-22/execution_reality_replay_gap_audit.md`
- `runtime_clean_validation_2026-05-19.md`

Files intentionally not inspected: strategy modules, risk modules, live config, JSONL, offline reports, runtime logs.

---

## Finding 1 — Three Separate S3 Labels Exist in the UI

### Label A: Header `| S3 [s3_status] |`

**Location:** `utils/display.py:2056–2077`, inside `_header()` method.

```python
s3 = self._safe_text(self._execution_reality.get("s3_status"), "n/a")
# rendered as:
line2.append(" | S3 ", style="grey70")
line2.append(self._clip(s3, 12), style=self._traffic_label_style(s3))
```

**Source:** `_execution_reality["s3_status"]`, initialized as `""` in `PolymarketRealtimeDisplay.__init__`.

**Runtime value:** Always `n/a`. `update_execution_reality()` — the only method that can write `s3_status` — is **never called from `polymarket/trader.py` or `main.py`**. Confirmed by grep: zero matches in both files.

**What it shows at runtime:** `| S3 n/a |`

---

### Label B: Research Cockpit panel — SEM-C / S3 section

**Location:** `utils/display.py:2549–2590`, inside `_quant_research_panel()`.

```python
probe0_raw = obs.get("zero_size_probe_count", None)
probe0_ok = probe0_raw is not None and int(probe0_raw) >= 15
s3_probe_ready = bool(obs.get("s3_probe_ready", probe0_ok))
s3_hint = "READY" if s3_probe_ready else "collecting"
# rendered as:
(" S3:", "grey70"), (s3_hint, "bright_green" if s3_probe_ready else "bright_yellow"),
```

**Source:** `_research_obs["zero_size_probe_count"]`, populated by `display.update_research_obs(**trader.dashboard_probe_counts())` called from `main.py:610` every cycle.

**Runtime logic:** Shows `S3: READY` once the in-session `zero_size_probe_count` accumulates to 15 or more. This threshold is met whenever the bot has had 15+ cycles where risk sizing returned zero.

**What it shows at runtime:** `S3: READY` within a few minutes of any active paper session. The threshold of 15 zero-size probes is a mechanical session counter, not an evidence gate.

---

### Label C: Test fixture

**Location:** `tests/test_terminal_dashboard_display.py:448–453`

```python
display.update_execution_reality(
    readiness_pct=65.0,
    phase6_status="BLOCKED",
    s3_status="READY",
    git_clean_state="dirty",
)
```

This hardcodes `s3_status="READY"` alongside `phase6_status="BLOCKED"` as a rendering test fixture. The exact combination matches the terminal sample reported. The test verifies that the header renders the passed values correctly. It is **not** an assertion that S3 is actually READY.

---

## Finding 2 — Naming Collision Between Two Definitions of "S3"

There are two distinct definitions of "S3" in use simultaneously:

| Definition | Location | Meaning | Threshold |
|---|---|---|---|
| Research evidence S3 | Research docs, audit reports | Stage 3 evidence readiness: warmup maturation, model visibility at entry, MFE/MAE path, paired trade counts, expiry coverage, latency truth | Multiple gates, all open |
| Probe S3 | `_quant_research_panel()` in display.py | Semantic Probe 3 mechanically initialized (enough zero-size probes for raw probe validity) | `zero_size_probe_count >= 15` |

The Research Cockpit panel uses the word `S3: READY` to mean "Probe S3 has enough raw samples." Research docs use `S3 = CAUTION` to mean "Stage 3 evidence is insufficient for promotion." These are not the same concept.

---

## Finding 3 — Current Research Evidence State for S3

All five research documents reviewed are consistent:

### `warmup_session_maturation_audit.md` (2026-05-21)

```
S3 remains CAUTION and should not be promoted until runtime duration,
close count, stable liquidity, visible model output at entry, expiry
coverage, and MFE/MAE path evidence improve.
```

Open blockers identified:
- True run-start bins (0–60 min) have zero observed trades
- 31/42 entries are THIN depth
- model_output_ready=false on all 42 trade opens (serialization bug)
- No expiry closes
- No MFE/MAE close-path truth

### `model_visibility_entry_handoff_audit.md` (2026-05-21)

```
S3 should remain CAUTION until entry journal observability preserves
the model fields that already exist upstream.
```

Confirmed: model output drops at `_emit_trade_opened_event()` due to `**phase2_detail` overwriting scalar fields. This is a blocking observability gap for S3.

### `execution_reality_replay_gap_audit.md` (2026-05-22)

```
S3 status: CAUTION.
No promotion.
Reason: execution reality remains incomplete. Fill truth remains
simulated, not executable. Delay and stale-quote replay cannot be
computed reliably. Final derisk, cancel, late-fill, and expiry
realism remain unproven.
```

### `phase5_evidence_monitor.md` (2026-05-22)

```
Gate status is still not ready because paired count, BTC coverage,
and TP coverage remain below threshold.
```

Current readiness gates:

| Gate | Required | Current | Status |
|---|---:|---:|---|
| Confirmed paired trades | 20 | 9 | NOT MET |
| BTC confirmed paired trades | 5 | 1 | NOT MET |
| TP/WIN confirmed outcomes | 5 | 3 | NOT MET |
| SL/LOSS confirmed outcomes | 5 | 6 | MET |
| 60s+ quote-age evidence | 1 | 1 | MET |

Phase 6 readiness: 65.0%. Three gates still open.

### `execution_reality_daily_monitor.md` (2026-05-22)

```
COLLECT_MORE_EVIDENCE
Phase 6 is not ready. Paired count, BTC evidence, and TP evidence
remain insufficient.
```

### `runtime_clean_validation_2026-05-19.md`

Contains the header field:
```
s3_status: CAUTION
```

This was the last recorded explicit s3_status in a validation document.

---

## Root Cause of the Inconsistency

The terminal sample showing `Phase6 BLOCKED | S3 READY` has one of two sources:

1. **Test output observed**: `test_execution_reality_header_renders_phase_a_status_fields` sets `s3_status="READY"` as a rendering fixture value. If the user observed this during a test run or in test output, the label would match exactly. This is the most likely source of the reported sample.

2. **Research Cockpit panel**: During any active paper session, `S3: READY` appears in the SEM-C/S3 section of the Research Cockpit panel once `zero_size_probe_count >= 15`. This label means "the zero-size probe counter is above its minimum initialization threshold" — not "S3 evidence is complete."

Neither source reflects the actual research evidence state. The research evidence state is `S3 CAUTION`.

---

## Correct Label Assessment

| Label candidate | Accurate? | Reasoning |
|---|---|---|
| `S3 READY` | **No** | Implies promotion criteria met. Three readiness gates open. Multiple evidence blockers open. Not supported by any research doc. |
| `S3 CAUTION` | **Yes** | Matches all five research docs reviewed. Correctly represents the mixed evidence state. |
| `S3 NOT_PROMOTED` | **Yes** | Accurate and explicit. Used in audit headers. Makes promotion status clear. |
| `S3 READY_FOR_REVIEW` | **Partial** | Implies the evidence is ready for review, but the daily monitor says "COLLECT_MORE_EVIDENCE." Misleading. |

**Recommended terminal label:** `S3 CAUTION`

---

## Specific Issues to Fix (Not in This Task)

These fixes were NOT made in this audit. They are findings only.

### Issue 1 — Header `s3_status` never updated at runtime

`update_execution_reality(s3_status=...)` is not called from `main.py` or `trader.py`. The header permanently shows `S3 n/a` at runtime. This is a dead display field. It needs a runtime call site to be useful.

**Correct runtime value to pass:** `"CAUTION"` based on current evidence.

### Issue 2 — Research Cockpit `S3: READY` threshold is too low

`zero_size_probe_count >= 15` is met in any normal session within minutes. The label `S3: READY` is misleading when it only means "probe initialized." It should be renamed to `S3 probes: initialized` or `S3 probes: active` to distinguish from the research evidence state.

### Issue 3 — Test fixture uses incorrect evidence value

`tests/test_terminal_dashboard_display.py:451` sets `s3_status="READY"` as a rendering test value. The correct evidence-consistent value is `"CAUTION"`. This does not affect rendering correctness (the rendering test verifies display, not evidence state), but the test fixture value creates a false expectation if read as evidence.

### Issue 4 — No runtime wiring from research state to header S3 label

The header's `| Phase6 ... | S3 ... |` line was designed to surface evidence state at a glance, but the state is never populated from the runtime. The intended flow described in `docs/research/performance/terminal_ui_v2_redesign.md:588` (`display.update_execution_reality(**summary)`) was not implemented.

---

## Recommendation

The correct terminal label for S3, based on consolidated evidence from all five research documents, is:

```
S3 CAUTION
```

Do not promote S3. Do not relabel to READY. Continue accumulating evidence:

- Paired trades toward 20 (currently 9)
- BTC confirmed pairs toward 5 (currently 1)
- TP outcomes toward 5 (currently 3)
- Fix model field drop at `_emit_trade_opened_event()` (separately scoped observability task)
- Accumulate expiry closes and MFE/MAE close-path truth
- Confirm latency truth fields before executable EV claims

---

## Safety Verification

- Runtime behavior changed: No
- Live behavior changed: No
- Code modified: No
- Strategy/risk/execution modified: No
- Paper runtime launched: No
- Replay tools run: No
- Tests run: none, read-only audit
- Persistent tests: unchanged, none deleted
