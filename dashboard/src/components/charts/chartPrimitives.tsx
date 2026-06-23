import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { ChartRow } from "../../types/dashboard";
import { EmptyState } from "../common/EmptyState";

const COLORS = ["#000000", "#404040", "#666666", "#8c8c8c", "#b3b3b3", "#d9d9d9"];

function truncateLabel(name: string, max = 14) {
  const trimmed = String(name ?? "").trim();
  if (trimmed.length <= max) {
    return trimmed;
  }
  return `${trimmed.slice(0, Math.max(1, max - 3))}...`;
}

export function PieMetricChart({
  data,
  emptyLabel,
  height = 320,
}: {
  data: ChartRow[];
  emptyLabel: string;
  height?: number;
}) {
  if (!data.length) {
    return <EmptyState label={emptyLabel} />;
  }

  return (
    <ResponsiveContainer width="100%" height={Math.max(height, 320)}>
      <PieChart>
        <Pie data={data} dataKey="value" nameKey="name" innerRadius={42} outerRadius={78} paddingAngle={2} label={{ fontSize: 13, fill: "#000000" }}>
          {data.map((entry, index) => (
            <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip contentStyle={{ backgroundColor: "#ffffff", border: "1px solid #d9d9d9", fontSize: "13px", color: "#000000" }} />
        <Legend wrapperStyle={{ fontSize: "13px", color: "#000000", fontFamily: "Inter, system-ui, sans-serif" }} formatter={(value) => truncateLabel(String(value), 18)} />
      </PieChart>
    </ResponsiveContainer>
  );
}

export function BarMetricChart({
  data,
  emptyLabel,
  unit,
  height = 380,
}: {
  data: ChartRow[];
  emptyLabel: string;
  unit?: string;
  height?: number;
}) {
  if (!data.length) {
    return <EmptyState label={emptyLabel} />;
  }

  const processedData = data.map(item => ({
    ...item,
    fullName: item.name,
    shortName: truncateLabel(item.name, 15),
  }));

  return (
    <ResponsiveContainer width="100%" height={Math.max(height, 380)}>
      <BarChart data={processedData.slice(0, 8)} margin={{ top: 18, right: 18, left: 8, bottom: 92 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#d0d0d0" />
        <XAxis
          dataKey="shortName"
          angle={-45}
          textAnchor="end"
          interval={0}
          height={90}
          stroke="#404040"
          tick={{ fontSize: 13, fill: "#000000", fontWeight: 500 }}
          tickMargin={16}
        />
        <YAxis stroke="#404040" tick={{ fontSize: 13, fill: "#000000", fontWeight: 500 }} width={48} />
        <Tooltip
          contentStyle={{ backgroundColor: "#ffffff", border: "1px solid #d9d9d9", fontSize: "13px", color: "#000000" }}
          labelFormatter={(_, payload) => String(payload?.[0]?.payload?.fullName ?? "")}
          formatter={(value) => [`${value}${unit ? ` ${unit}` : ""}`, "value"]}
        />
        <Bar dataKey="value" fill="#404040" radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
