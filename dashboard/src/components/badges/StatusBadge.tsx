import type { Tone } from "../../types/dashboard";

const BADGE_CLASSES: Record<Tone, string> = {
  good: "border-[#c6ebc9] bg-[#e6f4ea] text-[#008f39]",
  warn: "border-[#f0dc82] bg-[#fef7e0] text-[#b8860b]",
  bad: "border-[#f5c6cb] bg-[#fce8e6] text-[#c62828]",
  neutral: "border-[#d9d9d9] bg-[#f1f3f4] text-[#404040]",
};

export function StatusBadge({ label, tone = "neutral" }: { label: string; tone?: Tone }) {
  const badgeClass = BADGE_CLASSES[tone] || BADGE_CLASSES.neutral;
  return (
    <span className={`inline-flex items-center text-[12px] font-mono font-bold px-2.5 py-1 border rounded uppercase tracking-wider ${badgeClass}`}>
      {label}
    </span>
  );
}
