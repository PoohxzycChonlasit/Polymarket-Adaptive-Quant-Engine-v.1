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
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key}>{column.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={`${row.code ?? row.name ?? index}`}>
              {columns.map((column) => (
                <td key={column.key}>{String(row[column.key] ?? "n/a")}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
