import type { ChartRow, CountRecord, DashboardState, Tone } from "./types";

export function numericValue(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

export function entriesFromRecord(record?: CountRecord | null): ChartRow[] {
  if (!record) {
    return [];
  }

  return Object.entries(record)
    .map(([name, rawValue]) => ({ name, value: numericValue(rawValue) ?? 0 }))
    .filter((row) => row.value > 0)
    .sort((a, b) => b.value - a.value || a.name.localeCompare(b.name));
}

export function sumRecordValues(record?: CountRecord | null): number {
  return entriesFromRecord(record).reduce((total, row) => total + row.value, 0);
}

export function toWinLossRows(today?: Record<string, unknown>): ChartRow[] {
  return [
    { name: "Wins", value: numericValue(today?.win_count) ?? 0 },
    { name: "Losses", value: numericValue(today?.loss_count) ?? 0 },
    { name: "Breakeven", value: numericValue(today?.breakeven_count) ?? 0 },
  ].filter((row) => row.value > 0);
}

export function getStateTone(stateStatus?: string): Tone {
  if (stateStatus === "OK") {
    return "good";
  }
  if (stateStatus === "PARTIAL") {
    return "warn";
  }
  if (stateStatus === "ERROR") {
    return "bad";
  }
  return "neutral";
}

export function formatCurrency(value: unknown): string {
  const numeric = numericValue(value);
  if (numeric === null) {
    return "n/a";
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(numeric);
}

export function formatNumber(value: unknown, digits = 2): string {
  const numeric = numericValue(value);
  if (numeric === null) {
    return "n/a";
  }
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: digits,
  }).format(numeric);
}

export function formatPercent(value: unknown): string {
  const numeric = numericValue(value);
  if (numeric === null) {
    return "n/a";
  }
  const normalized = Math.abs(numeric) <= 1 ? numeric : numeric / 100;
  return new Intl.NumberFormat("en-US", {
    style: "percent",
    maximumFractionDigits: 1,
  }).format(normalized);
}

export function storageRows(state?: DashboardState): ChartRow[] {
  const categories = state?.storage?.categories;
  if (!categories) {
    return [];
  }

  return Object.entries(categories)
    .map(([name, details]) => ({
      name,
      value:
        numericValue(details?.size_mb) ??
        numericValue(details?.total_size_mb) ??
        numericValue(details?.size_bytes) ??
        0,
    }))
    .filter((row) => row.value > 0)
    .sort((a, b) => b.value - a.value);
}

export function storageUnitLabel(state?: DashboardState): string {
  const rows = storageRows(state);
  const hasByteLike = rows.some((row) => row.value > 100000);
  return hasByteLike ? "bytes" : "MB";
}
