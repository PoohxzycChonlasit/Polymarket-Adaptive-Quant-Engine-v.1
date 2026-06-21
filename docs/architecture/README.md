# Architecture Directory
Central repository for core system specs, engines design plans, and schemas.

## 1. Purpose
Defines the technical blueprints, engine designs, data schemas, and pipeline structures of the Polymarket trading engine.

## 2. What Belongs Here
* Engine design specifications (e.g., Inventory Engine, Slim Index, telemetry overlay).
* Data pipeline wiring plans and data flow specs.
* Project file structures and documentation maps.

## 3. What Does NOT Belong Here
* Performance reports (relocate to `docs/reports/`).
* Validation check outputs (relocate to `docs/evidence/`).
* Development test codes or scripts.

## 4. Read-First Files
* Check [PROJECT_STRUCTURE.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/PROJECT_STRUCTURE.md) for root-level overview.
* Read the active engine spec corresponding to your role.

## 5. Historical Files Policy
Architectural specifications represent active blueprints. If a design is superseded, it must be marked with a "SUPERSEDED BY" alert at the top, referencing the new specification file.

## 6. Active/Current Files Policy
Active specifications must match the current logic implemented in the codebase. Any deviation represents a doc-code mismatch that must be resolved.

## 7. Notes for AI Agents
> [!IMPORTANT]
> When implementing code changes, verify your modifications comply with the structural blueprints outlined in these files.
