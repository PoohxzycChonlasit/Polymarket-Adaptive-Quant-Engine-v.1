import { describe, expect, it } from "vitest";

import {
  entriesFromRecord,
  formatCurrency,
  sumRecordValues,
  toWinLossRows,
} from "./formatters";
import { getStateTone } from "./guards";

describe("dashboard data helpers", () => {
  it("turns count records into sorted chart rows", () => {
    expect(entriesFromRecord({ ETH: 2, BTC: 5 })).toEqual([
      { name: "BTC", value: 5 },
      { name: "ETH", value: 2 },
    ]);
  });

  it("sums numeric record values only", () => {
    expect(sumRecordValues({ a: 2, b: "skip", c: 3 })).toBe(5);
  });

  it("builds win loss rows from trade summary", () => {
    expect(
      toWinLossRows({
        win_count: 3,
        loss_count: 2,
        breakeven_count: 1,
      }),
    ).toEqual([
      { name: "Wins", value: 3 },
      { name: "Losses", value: 2 },
      { name: "Breakeven", value: 1 },
    ]);
  });

  it("formats numbers as compact currency", () => {
    expect(formatCurrency(12.3456)).toBe("$12.35");
  });

  it("classifies dashboard state tones", () => {
    expect(getStateTone("OK")).toBe("good");
    expect(getStateTone("PARTIAL")).toBe("warn");
    expect(getStateTone("ERROR")).toBe("bad");
  });
});
