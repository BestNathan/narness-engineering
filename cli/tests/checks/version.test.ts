import { describe, it, expect } from "vitest";
import { versionCheck } from "../../src/checks/version.js";
import type { Context } from "../../src/checks/check.js";

function ctx(stdout: string, code = 0): Context {
  return {
    cwd: "/tmp",
    runCommand: async () => ({ code, stdout, stderr: "" }),
    which: () => true,
    readMcpServers: () => [],
  };
}

describe("versionCheck", () => {
  it("passes when the version satisfies", async () => {
    const r = await versionCheck.run({ type: "version", name: "node", min: "22" }, ctx("v22.14.0"));
    expect(r.status).toBe("pass");
    expect(r.detail).toContain("22.14.0");
  });
  it("fails when the version is too low", async () => {
    const r = await versionCheck.run({ type: "version", name: "node", min: "22" }, ctx("v18.0.0"));
    expect(r.status).toBe("fail");
  });
  it("errors when the command fails", async () => {
    const r = await versionCheck.run({ type: "version", name: "node", min: "22" }, ctx("", 127));
    expect(r.status).toBe("error");
  });
});
