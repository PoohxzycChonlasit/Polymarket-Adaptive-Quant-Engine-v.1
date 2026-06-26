# REGISTRY_INDEX_INTEGRATION_PLAN

This plan defines the exact locations where the registry files must be added in `DOCUMENTATION_MAP.md` and `FILE_INDEX.md` once a file-modification task is approved.

---

## 1. DOCUMENTATION_MAP.md Integration

### Location
Insert a new section `## Research Governance & Active Questions` directly after `## Agent Router And Roles` (around line 50).

### Content to Insert
```markdown
## Research Governance & Active Questions

These files coordinate the active research scopes, past audit verifications, and proposed system parameter changes:

| File | Purpose |
|------|---------|
| `docs/research/ACTIVE_QUESTION.md` | Defines the single active question blocking strategy changes. |
| `docs/research/AUDIT_REGISTRY.json` | JSON list of all completed backtest, replay, and pipeline audits. |
| `docs/research/DECISION_REGISTRY.json` | JSON list of proposed or approved parameter and configuration changes. |
| `docs/research/GOVERNANCE_NAVIGATION_HUB.md` | Hierarchy of truth, promotion gates, and review procedures. |
```

### Rationale
Documentation Map maps files by domain. Creating a dedicated Governance category prevents the registry files from being buried in the general Research or Operations lists.

---

## 2. FILE_INDEX.md Integration

### Location
Insert the new files directly into the `## Start Here` table (lines 6-25), at the end of the first table block (directly after `docs/PROJECT_CLEANUP_REPORT.md` at line 24).

### Content to Insert
```markdown
| `docs/research/ACTIVE_QUESTION.md` | Enforces active question alignment and blocking constraints. |
| `docs/research/AUDIT_REGISTRY.json` | Registry of verified quant audits to prevent duplication. |
| `docs/research/DECISION_REGISTRY.json` | Registry of proposed parameter changes to prevent drift. |
```

### Rationale
Agents check `FILE_INDEX.md` during session startup. Placing the registries in the `Start Here` table ensures that any agent parses them immediately at startup.
