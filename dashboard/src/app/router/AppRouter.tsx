import { Route, Routes } from "react-router-dom";

import { AlertsPage } from "../../pages/alerts/AlertsPage";
import { NotFoundPage } from "../../pages/not-found/NotFoundPage";
import { OverviewPage } from "../../pages/overview/OverviewPage";
import { ResearchPage } from "../../pages/research/ResearchPage";
import { RiskPage } from "../../pages/risk/RiskPage";
import { SignalsPage } from "../../pages/signals/SignalsPage";
import { StoragePage } from "../../pages/storage/StoragePage";
import { TradesPage } from "../../pages/trades/TradesPage";
import type { AlertRecord, DashboardState } from "../../types/dashboard";

export function AppRoutes({ state, alerts }: { state?: DashboardState; alerts?: AlertRecord[] }) {
  return (
    <Routes>
      <Route path="/" element={<OverviewPage state={state} alerts={alerts} />} />
      <Route path="/signals" element={<SignalsPage state={state} />} />
      <Route path="/trades" element={<TradesPage state={state} />} />
      <Route path="/risk" element={<RiskPage state={state} />} />
      <Route path="/research" element={<ResearchPage />} />
      <Route path="/storage" element={<StoragePage state={state} />} />
      <Route path="/alerts" element={<AlertsPage alerts={alerts} state={state} />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
