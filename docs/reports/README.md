# Reports Directory
Central directory for implementation reports, commit reports, and status summaries.

## 1. Purpose
Documents point-in-time summaries of development milestones, git commit records, and system verification results.

## 2. What Belongs Here
* Staged commit reports (e.g., Slim Index commits, Shadow Telemetry commits).
* Implementation reports (e.g., daily automated reports, snapshot archiver implementation).
* Recovery, restart, and status updates.

## 3. What Does NOT Belong Here
* Active guidelines (kept in root `AGENTS.md` or `PROJECT_RULES.md`).
* Strategy code or risk parameter files.
* Test suite code files.

## 4. Read-First Files
* Check [CURRENT_PROJECT_STATUS.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/CURRENT_PROJECT_STATUS.md) at the root for the active project status.
* Check [docs/reports/README.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/reports/README.md) (this file) to locate historical reports.

## 5. Historical Files Policy
Reports are historical logs summarizing specific changes merged or validated at a particular date. They are preserved for auditability and must not be used as active specifications.

## 6. Active/Current Files Policy
Active status tracking must be written only to the root `CURRENT_PROJECT_STATUS.md`.

## 7. Notes for AI Agents
> [!NOTE]
> When completing a task, always compile a new implementation/commit report following the naming and format patterns in this folder, and link it in the final summary.
