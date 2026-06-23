export function EmptyState({ label }: { label: string }) {
  return (
    <div className="flex min-h-[96px] items-center justify-center p-4 border border-dashed border-[#d9d9d9] rounded-lg text-[13px] text-[#666666] bg-[#f7f7f7] font-mono">
      {label}
    </div>
  );
}
