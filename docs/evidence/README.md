# Evidence Directory
Central folder containing validation checks, SQLite dry run results, and paper testing telemetry logs.

## 1. Purpose
Tracks empirical data proving logic correctness, SQLite indexing validity, and passive shadow telemetry accuracy.

## 2. What Belongs Here
* SQLite real data validation summaries.
* Bounded runtime validation logs for shadow telemetry.
* Schema compatibility validations.

## 3. What Does NOT Belong Here
* Trading scripts or system code.
* Daily performance summaries (written to `scratch/` or VPS log folders).
* Active risk parameters.

## 4. Read-First Files
* Check the latest dated validation run file to see the most recent test assertions.

## 5. Historical Files Policy
Evidence documents are immutable records demonstrating that a specific code build passed real-data testing. They are archived to maintain a traceable safety history.

## 6. Active/Current Files Policy
New validation runs must output new files here without editing or deleting old validation records.

## 7. Notes for AI Agents
> [!TIP]
> Use these validation logs as blueprints when constructing validation scripts or verifying data integrity metrics.
