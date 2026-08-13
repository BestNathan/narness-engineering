import { describe, it, expect } from "vitest";
import { runChecks } from "../src/engine.js";
import type { Config } from "../src/config.js";
import type { Context } from "../src/checks/check.js";

function ctx(over: Partial<Context> = {}): Context {
  return {
    cwd: "/tmp",
    runCommand: async () => ({ code: 0, stdout: "v22.14.0", stderr: "" }),
    which: () => true,
    readMcpServers: () => ["filesystem"],
    ...over,
  };
}

describe("runChecks", () => {
  it("遍历所有 checks", async () => {
    const cfg: Config = {
      checks: [
        { type: "version", name: "node", min: "22" },
        { type: "exists", name: "rg" },
      ],
    };
    const results = await runChecks(cfg, ctx());
    expect(results).toHaveLength(2);
    expect(results.every((r) => r.status === "pass")).toBe(true);
  });
  it("未知 type 标记 error", async () => {
    const cfg: Config = { checks: [{ type: "nope", name: "x" }] };
    const results = await runChecks(cfg, ctx());
    expect(results[0].status).toBe("error");
    expect(results[0].message).toContain("未知检查类型");
  });
  it("检查器抛异常标记 error 且继续", async () => {
    const cfg: Config = {
      checks: [
        { type: "exists", name: "a" },
        { type: "exists", name: "b" },
      ],
    };
    const throwing: Context = ctx({ which: (c) => {
      if (c === "a") throw new Error("boom");
      return true;
    }});
    const results = await runChecks(cfg, throwing);
    expect(results[0].status).toBe("error");
    expect(results[1].status).toBe("pass");
  });
});
