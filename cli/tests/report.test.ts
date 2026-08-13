import { describe, it, expect } from "vitest";
import { reportHuman, reportJson } from "../src/report.js";
import type { CheckResult } from "../src/checks/check.js";

const results: CheckResult[] = [
  { status: "pass", check: { type: "version", name: "node" }, detail: "node 22.14.0" },
  { status: "fail", check: { type: "exists", name: "rg" }, message: "missing tool(s): rg", fix: "brew install ripgrep" },
];

describe("reportHuman", () => {
  it("includes pass/fail marks and fix suggestions", () => {
    const out = reportHuman(results);
    expect(out).toContain("✔");
    expect(out).toContain("✗");
    expect(out).toContain("brew install ripgrep");
    expect(out).toContain("1 passed, 1 failed");
  });
});

describe("reportJson", () => {
  it("emits parseable structured JSON", () => {
    const out = reportJson(results);
    const obj = JSON.parse(out);
    expect(obj.ok).toBe(false);
    expect(obj.passed).toBe(1);
    expect(obj.failed).toBe(1);
    expect(obj.results).toHaveLength(2);
    expect(obj.results[1].fix).toBe("brew install ripgrep");
  });
});
