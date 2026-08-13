import { describe, it, expect } from "vitest";
import { existsCheck } from "../../src/checks/exists.js";
import type { Context } from "../../src/checks/check.js";

function ctx(which: (c: string) => boolean): Context {
  return {
    cwd: "/tmp",
    runCommand: async () => ({ code: 0, stdout: "", stderr: "" }),
    which,
    readMcpServers: () => [],
  };
}

describe("existsCheck", () => {
  it("passes when the tool exists", async () => {
    const r = await existsCheck.run({ type: "exists", name: "rg" }, ctx((c) => c === "rg"));
    expect(r.status).toBe("pass");
  });
  it("fails with a fix when the tool is missing", async () => {
    const r = await existsCheck.run(
      { type: "exists", name: "rg", fix: "brew install ripgrep" },
      ctx(() => false)
    );
    expect(r.status).toBe("fail");
    expect(r.fix).toBe("brew install ripgrep");
  });
  it("checks multiple with a names array", async () => {
    const r = await existsCheck.run(
      { type: "exists", name: "rg", names: ["jq", "git"] },
      ctx((c) => c === "rg" || c === "git")
    );
    expect(r.status).toBe("fail");
    expect(r.message).toContain("jq");
  });
});
