import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { AppShell } from "../../app/layouts/AppShell";
import { OverviewPage } from "./OverviewPage";

describe("OverviewPage", () => {
  it("renders the read-only observability banner", () => {
    const html = renderToStaticMarkup(
      <AppShell isFetching={false} stateError={false}>
        <OverviewPage />
      </AppShell>,
    );

    expect(html).toContain("READ ONLY DASHBOARD - OBSERVABILITY ONLY");
  });
});
