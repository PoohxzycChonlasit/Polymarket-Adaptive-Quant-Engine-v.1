import axios from "axios";

import type { DashboardHealth, DashboardState } from "./types";

const API_BASE_URL = import.meta.env.VITE_DASHBOARD_API_BASE_URL ?? "";

export async function fetchDashboardState(): Promise<DashboardState> {
  const response = await axios.get<DashboardState>(
    `${API_BASE_URL}/api/dashboard/state`,
    { timeout: 5000 },
  );
  return response.data;
}

export async function fetchDashboardHealth(): Promise<DashboardHealth> {
  const response = await axios.get<DashboardHealth>(
    `${API_BASE_URL}/api/dashboard/health`,
    { timeout: 5000 },
  );
  return response.data;
}
