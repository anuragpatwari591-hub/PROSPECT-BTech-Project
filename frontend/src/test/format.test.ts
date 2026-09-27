import { formatValue, levelFor, relativeTime } from "../lib/format";

describe("formatValue", () => {
  it("handles missing values", () => { expect(formatValue(null)).toBe("—"); expect(formatValue(undefined, "days")).toBe("—"); });
  it("formats ratios as percentages", () => { expect(formatValue(0.456, "ratio 0–1")).toBe("46%"); });
  it("signs percentage changes", () => { expect(formatValue(-31.25, "%")).toBe("-31.3%"); expect(formatValue(12, "%")).toBe("+12%"); });
  it("appends units except plain counts", () => { expect(formatValue(4.2, "days")).toBe("4.2 days"); expect(formatValue(1234, "commits")).toBe("1,234"); });
});

describe("levelFor", () => {
  it("uses the same thresholds as the backend", () => {
    expect([0, 24.9, 25, 50, 75, 100].map(levelFor)).toEqual(["LOW", "LOW", "MEDIUM", "HIGH", "CRITICAL", "CRITICAL"]);
  });
});

describe("relativeTime", () => {
  it("describes elapsed time", () => {
    const now = Date.parse("2026-09-17T12:00:00Z");
    expect(relativeTime("2026-09-17T11:30:00Z", now)).toBe("30 min ago");
    expect(relativeTime("2026-09-10T12:00:00Z", now)).toBe("7 days ago");
    expect(relativeTime(null, now)).toBe("never");
  });
});
