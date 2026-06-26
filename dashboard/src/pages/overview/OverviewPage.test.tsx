import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { AppShell } from "../../app/layouts/AppShell";
import { OverviewPage } from "./OverviewPage";

describe("OverviewPage", () => {
  it("renders the read-only observability banner", () => {
    const html = renderToStaticMarkup(
      <MemoryRouter>
        <AppShell isFetching={false} stateError={false}>
          <OverviewPage />
        </AppShell>
      </MemoryRouter>,
    );

    expect(html).toContain("OBSERVABILITY ONLY");
  });
});
