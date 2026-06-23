import type { Tone } from "../../types/dashboard";

export function StatusBadge({ label, tone = "neutral" }: { label: string; tone?: Tone }) {
  return <span className={`status-badge status-${tone}`}>{label}</span>;
}
