import { describe, it, expect } from "vitest";
import { mcpCheck } from "../../src/checks/mcp.js";
import type { Context } from "../../src/checks/check.js";

function ctx(servers: string[]): Context {
  return {
    cwd: "/tmp",
    runCommand: async () => ({ code: 0, stdout: "", stderr: "" }),
    which: () => true,
    readMcpServers: () => servers,
  };
}

describe("mcpCheck", () => {
  it("passes when declared", async () => {
    const r = await mcpCheck.run({ type: "mcp", name: "filesystem" }, ctx(["filesystem", "github"]));
    expect(r.status).toBe("pass");
  });
  it("fails with a fix when not declared", async () => {
    const r = await mcpCheck.run({ type: "mcp", name: "filesystem" }, ctx(["github"]));
    expect(r.status).toBe("fail");
    expect(r.fix).toContain(".mcp.json");
  });
});
