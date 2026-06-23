import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { AppRoutes } from "./AppRouter";
import { Sidebar } from "../../components/navigation/Sidebar";

describe("dashboard router", () => {
  function renderRoute(path: string) {
    return renderToStaticMarkup(
      <MemoryRouter initialEntries={[path]}>
        <AppRoutes />
      </MemoryRouter>,
    );
  }

  it("renders overview route", () => {
    expect(renderRoute("/")).toContain("Runtime Health");
  });

  it("renders signals route", () => {
    expect(renderRoute("/signals")).toContain("Signal Intelligence");
  });

  it("renders storage route", () => {
    expect(renderRoute("/storage")).toContain("Storage");
  });

  it("renders alerts route", () => {
    expect(renderRoute("/alerts")).toContain("Alerts");
  });

  it("marks the active navigation route", () => {
    const html = renderToStaticMarkup(
      <MemoryRouter initialEntries={["/signals"]}>
        <Sidebar />
      </MemoryRouter>,
    );

    expect(html).toContain("nav-link active");
    expect(html).toContain("Signals");
  });

  it("renders not found for unknown routes", () => {
    expect(renderRoute("/unknown")).toContain("Dashboard page not found");
  });
});
