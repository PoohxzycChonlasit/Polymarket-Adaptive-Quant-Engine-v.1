import { StorageSection } from "../../features/storage/StorageSection";
import type { DashboardState } from "../../types/dashboard";

export function StoragePage({ state }: { state?: DashboardState }) {
  return <StorageSection state={state} />;
}
