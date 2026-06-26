# RESEARCH_GOVERNANCE_V1_DESIGN

## 1. Executive Summary
This document designs **RESEARCH_GOVERNANCE_V1**, a cross-agent coordination and safety framework. It is designed to allow multiple AI agents (Gemini, Claude, Codex, ChatGPT) to collaborate on the `Polymarket-Adaptive-Quant-Engine-v.1` repository without scope drift, duplicate investigations, or context bloat.

The specification introduces:
- A centralized **Audit Ledger** for de-duplication.
- An **Active Search Directory** vs. **Pruned Archive** separation to conserve token usage.
- Strict **Stop/Escalate/Approval gates** for agents.
- A standardized **Audit Schema** for all future research runs.

---

## 2. Current State

The current repository employs a hybrid, document-driven governance model defined across:
- `docs/research/GOVERNANCE_NAVIGATION_HUB.md` (Promotion gates and truth layers)
- `docs/research/INFRASTRUCTURE_GOVERNANCE_MAP.md` (9-layer architecture: Runtime, Raw Evidence, etc.)
- `QUANT_FUTURE_DECISION_ENGINE.md` (Mandatory Three-Option Rule)
- `AGENTS.md` & `MASTER_AGENT_ROUTER.md` (Role definitions and allowed file scopes)

### Active Layers
- **Agent Governance**: Present (rules specify primary/supporting roles).
- **Decision Governance**: Present (Three-Option Rule).
- **Memory Governance**: Present (reusable checklists under `.codex/skills/` and session memory templates).
- **Project/Research Governance**: Partial (rules exist in docs, but lack execution/code-level tracking).

---

## 3. Governance Gap Analysis

The following gaps currently exist and cause multi-agent friction:
1. **No Shared Coordination State**: Agents cannot see if another agent is already running a replay or verifying a hypothesis, leading to redundant audits.
2. **Passive vs. Active Control**: Existing rules are descriptive documents. There is no active ledger tracking completed audits to prevent re-discovery.
3. **No File Pruning Rules**: Completed research remains in active paths (`docs/research/`), forcing future agents to scan large historical logs, wasting token context.
4. **Undefined Escalation Triggers**: Loop bounds and escalation triggers are manual rather than codified in a structured state machine.

---

## 4. RESEARCH_GOVERNANCE_V1 Specification

### A. Mission
To enforce mathematical rigor, prevent redundant investigations, protect runtime safety gates, and optimize context token usage during multi-agent quant operations.

### B. Scope
Applies to all AI agents (Gemini, Claude, Codex, ChatGPT) running research, backtest reviews, paper validation, data quality checks, or incident audits.

### C. Standardized Research Workflow
Every research task must advance through these explicit states:

```text
[State 0: Registry Check] ──> [State 1: Read-Only Audit] ──> [State 2: Evidence Summary]
                                                                     │
[State 5: Stage / Test] <── [State 4: Three-Option Decision] <── [State 3: Verdict Label]
         │
[State 6: Operator Gate] ──> [State 7: Archive / Prune]
```

1. **State 0: Registry Check**: Query `docs/research/AUDIT_LEDGER.json` to check if the hypothesis or date range was audited.
2. **State 1: Read-Only Audit**: Walk directories, parse logs, or run offline scripts. No code changes, no run loops.
3. **State 2: Evidence Summary**: Extract hard metrics and map them to exact lineage keys `(run_id, paper_trade_replay_key)`.
4. **State 3: Verdict Label**: Apply a standardized classification label.
5. **State 4: Three-Option Decision**: Run the three-option framework.
6. **State 5: Stage / Test**: Draft proposed modifications and run validation tests.
7. **State 6: Operator Gate**: Request operator review. No merge/delete actions allowed.
8. **State 7: Archive / Prune**: Move the file to `docs/archive/research/` and record its index in the ledger.

---

### D. Audit Schema (Mandatory Structure)
Every audit report must contain:
```markdown
# [AUDIT_ID] [Audit Name]

## Metadata
- **Author Agent**: [Gemini / Claude / Codex / ChatGPT]
- **Target Asset**: [BTC / ETH / ALL]
- **Lineage Keys**: [List of Run IDs / Replay Keys]
- **Input Logs**: [Relative file paths parsed]

## Objective
[What hypothesis is being validated]

## Evidence & Distributions
[Hard counts, win rates, execution ask depth, and spreads]

## Caveats & Anomalies
[Data gaps, proxy matches, or missing logs]

## Standardized Verdict
[Must select exactly one: EDGE_REAL | EDGE_WEAK | REPLAY_ARTIFACT | PIPELINE_INCIDENT | DATA_QUALITY_GAP]

## Options Analysis
[OPTION 1: Safe EV | OPTION 2: Aggressive Discovery | OPTION 3: Structural Path]

## Recommended Next Step
[Exactly one next action]
```

---

### E. Agent Boundary Gates

#### 1. When to STOP
- The objective is answered (verdict reached).
- Workflow loop limit is reached (e.g. 3 polling attempts or 30s wait on background tasks).
- Forbidden directory/file modification is required.
- No `run_id` lineage is present on parsed data.

#### 2. When to CONTINUE
- The agent is in the read-only phase, data is partial, and loop bounds are not exceeded.

#### 3. When to ESCALATE
- A contradiction is found (e.g., backtest expectancies mismatch live outcomes).
- Log corruption or schema drift prevents parsing.
- Different agents report conflicting verdicts on the same data.

#### 4. When to ASK FOR APPROVAL
- Transitioning from Research (docs-only) to Implementation (code changes).
- Running any file moves, renames, archives, or deletions.
- Enabling or disabling live trading flags.

---

### F. Allowed Actions
- Walk directories and inspect files in a read-only state.
- Create scratch scripts in the designated `scratch/` folder.
- Generate markdown artifacts inside the app data directory.
- Query manifests and log indexes.

### G. Forbidden Actions
- Modifying, renaming, moving, or deleting files in active workspace paths during research.
- Running or restarting the paper/live trading bot loop.
- Modifying strategy logic, risk sizing, or live flags.
- Treating planned infrastructure as implemented.
- Hiding data gaps or proxy matches in audit reports.

---

### H. Audit De-duplication & Search Pruning
1. **Audit Ledger**: A central JSON file `docs/research/AUDIT_LEDGER.json` tracks all executed audits:
   ```json
   {
     "audits": [
       {
         "audit_id": "SUB_5C_EXECUTION_REALITY_AUDIT",
         "verdict": "EDGE_REAL",
         "date_range": "2026-05-11/2026-05-18",
         "path": "docs/archive/research/SUB_5C_EXECUTION_REALITY_AUDIT.md"
       }
     ]
   }
   ```
2. **Search Pruning**: Completed research is moved out of active search paths into `docs/archive/research/`. 
3. **Agent Constraint**: `AGENTS.md` is updated to include: *"Do not scan files in `docs/archive/` unless specifically directed. Always check `docs/research/AUDIT_LEDGER.json` before initiating an audit."* This reduces token consumption by preventing agents from reading obsolete files.

---

## 5. Single Recommended Next Step

Add the `docs/research/AUDIT_LEDGER.json` file schema to the workspace as a docs-only template and initialize it with the current audit entries to prevent redundant future runs.
