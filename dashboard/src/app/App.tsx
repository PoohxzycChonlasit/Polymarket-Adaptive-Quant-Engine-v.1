import { AppShell, ApiOffline } from "./layouts/AppShell";
import { AppRoutes } from "./router/AppRouter";
import { useDashboardState } from "../hooks/useDashboardState";

export default function App() {
  const { alerts, healthQuery, state, stateQuery } = useDashboardState();

  if (stateQuery.isError && !state) {
    return <ApiOffline error={stateQuery.error} />;
  }

  return (
    <AppShell
      state={state}
      isFetching={stateQuery.isFetching}
      apiStatus={healthQuery.data?.status}
      stateError={stateQuery.isError}
    >
      {stateQuery.isLoading ? <div className="loading-card">Loading dashboard state...</div> : null}
      <AppRoutes state={state} alerts={alerts} />
    </AppShell>
  );
}
