import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchDashboardHealth, fetchDashboardState } from "../services/api/dashboardApi";

export function useDashboardState() {
  const stateQuery = useQuery({
    queryKey: ["dashboard-state"],
    queryFn: fetchDashboardState,
  });
  const healthQuery = useQuery({
    queryKey: ["dashboard-health"],
    queryFn: fetchDashboardHealth,
  });

  const alerts = useMemo(() => {
    const state = stateQuery.data;
    return state?.alerts?.active?.length ? state.alerts.active : state?.alerts?.recent;
  }, [stateQuery.data]);

  return {
    alerts,
    healthQuery,
    state: stateQuery.data,
    stateQuery,
  };
}
