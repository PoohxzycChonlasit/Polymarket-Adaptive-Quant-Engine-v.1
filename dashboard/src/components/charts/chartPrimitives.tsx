import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { ChartRow } from "../../types/dashboard";
import { EmptyState } from "../common/EmptyState";

const COLORS = ["#5eead4", "#60a5fa", "#c084fc", "#fbbf24", "#fb7185", "#a3e635"];

export function PieMetricChart({ data, emptyLabel }: { data: ChartRow[]; emptyLabel: string }) {
  if (!data.length) {
    return <EmptyState label={emptyLabel} />;
  }

  return (
    <ResponsiveContainer width="100%" height={230}>
      <PieChart>
        <Pie data={data} dataKey="value" nameKey="name" innerRadius={50} outerRadius={82} paddingAngle={2}>
          {data.map((entry, index) => (
            <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip />
      </PieChart>
    </ResponsiveContainer>
  );
}

export function BarMetricChart({
  data,
  emptyLabel,
  unit,
}: {
  data: ChartRow[];
  emptyLabel: string;
  unit?: string;
}) {
  if (!data.length) {
    return <EmptyState label={emptyLabel} />;
  }

  return (
    <ResponsiveContainer width="100%" height={250}>
      <BarChart data={data.slice(0, 8)} margin={{ top: 10, right: 10, left: 0, bottom: 24 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
        <XAxis dataKey="name" angle={-20} textAnchor="end" interval={0} height={70} stroke="#94a3b8" />
        <YAxis stroke="#94a3b8" />
        <Tooltip formatter={(value) => [`${value}${unit ? ` ${unit}` : ""}`, "value"]} />
        <Bar dataKey="value" fill="#5eead4" radius={[6, 6, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
