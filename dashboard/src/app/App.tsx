import { AppShell, ApiOffline } from "./layouts/AppShell";
import { useDashboardState } from "../hooks/useDashboardState";
import { OverviewPage } from "../pages/overview/OverviewPage";

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
      <OverviewPage state={state} alerts={alerts} />
    </AppShell>
  );
}
