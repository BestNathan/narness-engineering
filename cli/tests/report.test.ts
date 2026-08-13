import { describe, it, expect } from "vitest";
import { reportHuman, reportJson } from "../src/report.js";
import type { CheckResult } from "../src/checks/check.js";

const results: CheckResult[] = [
  { status: "pass", check: { type: "version", name: "node" }, detail: "node 22.14.0" },
  { status: "fail", check: { type: "exists", name: "rg" }, message: "缺少工具: rg", fix: "brew install ripgrep" },
];

describe("reportHuman", () => {
  it("含 pass/fail 标记与修复建议", () => {
    const out = reportHuman(results);
    expect(out).toContain("✔");
    expect(out).toContain("✗");
    expect(out).toContain("brew install ripgrep");
    expect(out).toContain("1 passed, 1 failed");
  });
});

describe("reportJson", () => {
  it("输出可解析的结构化 JSON", () => {
    const out = reportJson(results);
    const obj = JSON.parse(out);
    expect(obj.ok).toBe(false);
    expect(obj.passed).toBe(1);
    expect(obj.failed).toBe(1);
    expect(obj.results).toHaveLength(2);
    expect(obj.results[1].fix).toBe("brew install ripgrep");
  });
});
