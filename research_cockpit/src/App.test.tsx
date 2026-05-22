import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";
import App from "./App";
import mockData from "./mock/execution_reality_mock.json";

describe("Research Cockpit MVP skeleton", () => {
  it("renders the required offline dashboard pages from mock data only", () => {
    const html = renderToString(<App />);

    expect(html).toContain("Research Cockpit v2");
    expect(html).toContain("Overview");
    expect(html).toContain("Execution Reality");
    expect(html).toContain("Quote Age");
    expect(html).toContain("Outcome Truth");
    expect(html).toContain("Trend");
    expect(html).toContain("Readiness");
    expect(html).toContain("Alerts");
    expect(html).toContain("Mock JSON only");
    expect(html).toContain(mockData.run.runId);
  });

  it("keeps Phase 6 blockers visible", () => {
    const html = renderToString(<App />);

    expect(html).toContain("BTC low");
    expect(html).toContain("TP stalled");
    expect(html).toContain("Phase6 blocked");
    expect(html).toContain("65%");
  });
});
