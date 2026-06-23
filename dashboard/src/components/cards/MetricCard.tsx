import type { Tone } from "../../types/dashboard";

const TONE_CLASSES: Record<Tone, string> = {
  good: "border-[#008f39]/30 bg-[#e6f4ea]/40 text-[#008f39]",
  warn: "border-[#b8860b]/30 bg-[#fef7e0]/40 text-[#b8860b]",
  bad: "border-[#c62828]/30 bg-[#fce8e6]/40 text-[#c62828]",
  neutral: "border-[#d9d9d9] bg-[#ffffff] text-[#000000]",
};

export function MetricCard({
  label,
  value,
  helper,
  tone = "neutral",
}: {
  label: string;
  value: string | number;
  helper?: string;
  tone?: Tone;
}) {
  const toneClass = TONE_CLASSES[tone] || TONE_CLASSES.neutral;
  return (
    <div className={`p-3 px-4 border rounded flex flex-col justify-between min-h-[72px] shadow-sm ${toneClass}`}>
      <span className="text-[12px] text-[#404040] font-bold uppercase tracking-wider leading-none">{label}</span>
      <strong className="text-xl font-mono font-semibold mt-2 text-[#000000] leading-none">{value}</strong>
      {helper ? <small className="text-[11px] text-[#666666] mt-2 truncate leading-none">{helper}</small> : null}
    </div>
  );
}

export function BloombergMetricRow({
  label,
  value,
  helper,
  tone = "neutral",
}: {
  label: string;
  value: string | number;
  helper?: string;
  tone?: Tone;
}) {
  const textColor = {
    good: "text-[#008f39]",
    warn: "text-[#b8860b]",
    bad: "text-[#c62828]",
    neutral: "text-[#000000]",
  }[tone] || "text-[#000000]";

  return (
    <div className="flex items-center py-2.5 text-[13px] font-mono border-b border-[#e5e5e5] last:border-b-0">
      <span className="text-[#404040] font-semibold uppercase tracking-wider select-all">{label}</span>
      <div className="flex-grow border-b border-dotted border-[#d9d9d9] mx-3 self-end mb-1.5"></div>
      <div className="flex items-center gap-2 shrink-0">
        {helper && <span className="text-[11px] text-[#666666] font-sans lowercase pr-1">{helper}</span>}
        <span className={`font-semibold text-[14px] ${textColor}`}>{value}</span>
      </div>
    </div>
  );
}
