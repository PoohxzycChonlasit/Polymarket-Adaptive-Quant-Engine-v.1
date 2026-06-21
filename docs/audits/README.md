# Audits Directory
Central directory mapping codebase audits, pre-commit checks, safety reviews, and forensic check logs.

## 1. Purpose
Tracks structural codebase reviews, security audits, and forensic debugging notes.

## 2. What Belongs Here
* Codebase audits (e.g., duplicate open trade forensics, signal cluster analysis).
* Pre-commit checklist audits (e.g., pre-commit checks for indexes, patches, and telemetry).
* Volatility, risk boundary, and validation audits.

## 3. What Does NOT Belong Here
* Active rules or instructions (kept in root `AGENTS.md` or `PROJECT_RULES.md`).
* Daily performance summaries (relocate to `docs/reports/` or `scratch/`).
* Validation run telemetry files (relocate to `docs/evidence/` or `runtime/quant_data/`).

## 4. Read-First Files
* Check [docs/research/AUDIT_REGISTRY.json](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/research/AUDIT_REGISTRY.json) to see what audits are registered.
* Read the latest pre-commit audit file to understand the latest checks performed.

## 5. Historical Files Policy
Audits represent immutable point-in-time forensic reviews of the repository state at a specific commit. They describe historical contexts and resolved issues, not current system configuration.

## 6. Active/Current Files Policy
Only the latest pre-commit checks represent the active status of the current files.

## 7. Notes for AI Agents
> [!IMPORTANT]
> Do not treat recommendations or findings in old audit logs as active code specifications or system rules. Consult only root `AGENTS.md` and `PROJECT_RULES.md` for active operational constraints.
