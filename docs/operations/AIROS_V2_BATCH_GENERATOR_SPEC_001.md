# AIROS_V2_BATCH_GENERATOR_SPEC_001

**Status:** ACTIVE  
**Date:** 2026-06-28  
**Purpose:** Implementation specification for the AIROS v2 Batch Generator engine.

---

## 1. Input & Output Schemas

### 1.1 Input Schema (`dependency_graph.json` & `repository_index.json`)
The generator consumes parsed file lists and import linkages:
```json
{
  "files": {
    "tools/old_script.py": {
      "lines": 350,
      "outbound_imports": ["tools.utils_helper"],
      "inbound_imports": ["tests.test_old_script"]
    }
  }
}
```

### 1.2 Output Schema (`batch_candidates.json`)
The generator outputs optimal batch clusters:
```json
{
  "batches": [
    {
      "batch_id": "BATCH_SHADOW_001",
      "risk_level": "SAFE_ATOMIC",
      "files_to_move": [
        { "src": "tools/old_script.py", "dest": "tools/shadow/old_script.py" }
      ],
      "test_files": ["tests/test_old_script.py"],
      "total_lines": 350,
      "blast_radius_score": 1
    }
  ]
}
```

---

## 2. Batch Size Rules & Risk Thresholds

* **Maximum files per batch:** 12 files.
* **Maximum lines changed per batch:** 1,500 lines.
* **Risk Thresholds:**
  * Score $\le 3$: `SAFE_ATOMIC` (Direct execution).
  * Score $4 - 7$: `MEDIUM_ATOMIC` (Direct execution with dry run).
  * Score $8 - 11$: `PLAN_REQUIRED` (Design plan task required).
  * Score $\ge 12$: `DO_NOT_MOVE` (Migration blocked).

---

## 3. File Clustering Algorithm

The generator clusters files using a **Connected Component Graph Clustering** method:
1. **Identify Candidates:** Extract all files residing in the root `tools/` directory.
2. **Build Adjacency Matrix:** Extract relationships from `dependency_graph.json`.
3. **Cluster components:** Identify strongly connected subgraphs (files that import each other).
4. **Group by target destination:** Group candidate clusters by their target target subdirectory (e.g. `/shadow`, `/audit`).
5. **Apply size constraints:** If a cluster exceeds 12 files or 1,500 lines, split it along the weakest dependency edges.

---

## 4. Forbidden Grouping Rules

* **No Cross-Tier Mix:** Never mix files targeting different folders (e.g., do not bundle `/shadow` moves with `/audit` moves).
* **No Runtime Mix:** Never include core files (`polymarket/`, `config/`) in a batch.
* **No Sizing/Risk Mix:** Never group files linked to the sizer, risk, or execution path with diagnostic/research tools.

---

## 5. Sample Batch Output

```json
{
  "batches": [
    {
      "batch_id": "BATCH_AUDIT_001",
      "risk_level": "SAFE_ATOMIC",
      "files_to_move": [
        { "src": "tools/_opp_capture_audit.py", "dest": "tools/audit/_opp_capture_audit.py" }
      ],
      "test_files": [],
      "total_lines": 120,
      "blast_radius_score": 0
    }
  ]
}
```

---

## 6. Operator Approval Thresholds

* **SAFE_ATOMIC / MEDIUM_ATOMIC:** Auto-approved for direct implementation within the loop.
* **PLAN_REQUIRED / DO_NOT_MOVE:** Explicit operator approval required (system rejects auto-generation).
