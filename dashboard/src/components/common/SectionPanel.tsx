import type { ReactNode } from "react";

export function SectionPanel({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <section className="bg-white border border-[#d9d9d9] rounded-lg p-4 mb-3 flex flex-col shadow-sm">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 mb-3 pb-2 border-b border-[#d9d9d9]">
        <h2 className="text-[15px] font-bold text-black tracking-tight m-0">{title}</h2>
        {subtitle ? <p className="text-[12px] text-[#404040] m-0">{subtitle}</p> : null}
      </div>
      {children}
    </section>
  );
}
