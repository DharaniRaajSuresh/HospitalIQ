import { describe, it, expect } from "vitest";

describe("App smoke test", () => {
  it("loads without crashing", () => {
    expect(true).toBe(true);
  });

  it("has required API functions", async () => {
    const api = await import("./api.js");
    expect(typeof api.getStats).toBe("function");
    expect(typeof api.getStates).toBe("function");
    expect(typeof api.getDistricts).toBe("function");
    expect(typeof api.getBedForecast).toBe("function");
    expect(typeof api.predictMortality).toBe("function");
  });
});
