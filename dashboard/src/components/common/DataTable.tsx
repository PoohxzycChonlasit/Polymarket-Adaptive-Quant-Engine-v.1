import { EmptyState } from "./EmptyState";

export function DataTable({
  rows,
  columns,
  empty,
}: {
  rows: Record<string, unknown>[];
  columns: { key: string; label: string }[];
  empty: string;
}) {
  if (!rows.length) {
    return <EmptyState label={empty} />;
  }

  return (
    <div className="w-full overflow-x-auto border border-[#d9d9d9] rounded-lg bg-white shadow-sm">
      <table className="w-full border-collapse text-left min-w-[320px]">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key} className="p-3 px-4 bg-[#f2f2f2] text-[13px] font-mono font-bold text-black uppercase tracking-wider border-b border-[#d9d9d9] sticky top-0 z-10">
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-[#d9d9d9]/60">
          {rows.map((row, index) => (
            <tr key={`${row.code ?? row.name ?? index}`} className="odd:bg-white even:bg-[#f7f7f7] hover:bg-[#ececec] transition-colors">
              {columns.map((column) => (
                <td key={column.key} className="p-3 px-4 text-[13px] font-mono text-black">
                  {String(row[column.key] ?? "n/a")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
