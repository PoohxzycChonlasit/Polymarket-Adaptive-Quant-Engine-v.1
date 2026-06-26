# QUANT_TERMINAL_UI_V3_BLOOMBERG_REPORT_001

Date: 2026-06-23

Final verdict: QUANT_TERMINAL_UI_V3_BLOOMBERG_PASS

## Scope

Implemented frontend-only Bloomberg-style readability refinements for the React dashboard.

No backend logic, API calls, dashboard aggregator behavior, runtime, strategy, EV, risk engine, sizing, execution, polling behavior, websocket behavior, or chart data calculations were changed.

## UI Changes Made

### Layered Light Theme

- Normalized the visual system around a light institutional palette:
  - body background: `#f5f5f5`
  - panels/cards: `#ffffff`
  - borders: `#d9d9d9`
  - primary text: `#000000`
  - secondary text: `#404040`
  - muted text: `#666666`
  - grid lines: `#d0d0d0`
  - success: `#008f39`
  - warning: `#b8860b`
  - critical: `#c62828`
- Removed remaining dark terminal styling from the shell, storage panels, empty states, and research page.
- Preserved a layered page/panel/card hierarchy rather than pure white everywhere.

### Information Hierarchy

- Strengthened Tier 1 metrics in the global header:
  - Bankroll
  - Portfolio Equity
  - Realized PnL
  - Risk Mode
- Increased their visual weight with larger type, stronger borders, and more whitespace.
- Kept Tier 2/Tier 3 panels smaller but more readable.

### Chart Readability

- Increased bar chart minimum height to at least `380px`.
- Increased pie chart minimum height to at least `320px`.
- Increased chart axis font size to `13px`.
- Rotated X-axis labels to `-45deg`.
- Added intelligent label truncation while preserving full labels in tooltips.
- Increased chart bottom margin and tick spacing.
- Switched tooltips to white background, black text, gray border.
- Replaced cramped chart cards with white panels and larger headings.

### Signal Funnel

- Rebuilt the funnel into clear, full-width cards:
  - Decisions
  - Signal Passed
  - Risk Passed
  - Entries
- Shows absolute counts, percentages, and drop-off helper text.
- Removed unreadable arrow glyph artifacts.
- Uses vertical stacking below `1600px` and four-column layout at wider widths.

### Tables

- Increased table text size and row padding.
- Kept sticky headers.
- Ensured header background is `#f2f2f2` with black text.
- Preserved alternating row colors and hover highlight:
  - odd: `#ffffff`
  - even: `#f7f7f7`
  - hover: `#ececec`

### Research Terminal

- Replaced mock-looking research tables with roadmap placeholders:
  - Replay Analytics
  - Session Analytics
  - Regime Analytics
  - Expectancy Analytics
  - Backtesting Workbench
  - Monte Carlo Lab
- Kept all placeholders explicitly read-only.

### Storage Terminal

- Converted storage panels to the same white/light hierarchy.
- Improved storage chart/table separation.
- Kept existing telemetry fields and display logic.

## Files Modified

- `dashboard/src/app/layouts/AppShell.tsx`
- `dashboard/src/components/badges/StatusBadge.tsx`
- `dashboard/src/components/cards/MetricCard.tsx`
- `dashboard/src/components/charts/chartPrimitives.tsx`
- `dashboard/src/components/common/DataTable.tsx`
- `dashboard/src/components/common/EmptyState.tsx`
- `dashboard/src/components/common/ReadOnlyBanner.tsx`
- `dashboard/src/components/common/SectionPanel.tsx`
- `dashboard/src/components/navigation/Sidebar.tsx`
- `dashboard/src/components/navigation/Topbar.tsx`
- `dashboard/src/features/portfolio/PortfolioSection.tsx`
- `dashboard/src/features/risk/RiskSection.tsx`
- `dashboard/src/features/signals/SignalIntelligenceSection.tsx`
- `dashboard/src/features/storage/StorageSection.tsx`
- `dashboard/src/pages/research/ResearchPage.tsx`
- `dashboard/src/styles/styles.css`
- `QUANT_TERMINAL_UI_V3_BLOOMBERG_REPORT_001.md`
- `QUANT_TERMINAL_UI_V3_BLOOMBERG_PRE_COMMIT_AUDIT_001.md`

## Screenshots

Before/after screenshots were not captured in this run. Validation was performed through test/build checks and targeted source inspection.

## Validation

Commands run:

```powershell
cd dashboard
npm run test:run
npm run build
cd ..
git diff --check
```

Results:

- `npm run test:run`: PASS, 3 files / 12 tests
- `npm run build`: PASS
- `git diff --check`: PASS

Known note:

- Vite continues to emit the existing non-blocking bundle-size warning.

## Final Confirmation

Runtime changed: No
Strategy changed: No
EV changed: No
Risk changed: No
Sizing changed: No
Execution changed: No
Backend changed: No
API calls changed: No
Chart data changed: No
Live trading changed: No

