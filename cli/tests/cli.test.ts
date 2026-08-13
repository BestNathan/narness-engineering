import { describe, it, expect, beforeAll } from "vitest";
import { execFileSync } from "node:child_process";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const distIndex = fileURLToPath(new URL("../dist/index.js", import.meta.url));

function runIn(fixture: string, args: string[] = []) {
  try {
    const stdout = execFileSync("node", [distIndex, ...args], { cwd: fixture, encoding: "utf8" });
    return { code: 0, stdout, stderr: "" };
  } catch (err) {
    const e = err as { status?: number; stdout?: string; stderr?: string };
    return { code: e.status ?? 1, stdout: e.stdout ?? "", stderr: e.stderr ?? "" };
  }
}

describe("CLI 集成", () => {
  let dir: string;
  beforeAll(() => {
    dir = mkdtempSync(join(tmpdir(), "narness-cli-"));
  });

  it("全部通过则 exit 0", () => {
    writeFileSync(join(dir, ".narness.toml"), '[[checks]]\ntype = "version"\nname = "node"\nmin = "18"\n');
    const r = runIn(dir);
    expect(r.code).toBe(0);
    expect(r.stdout).toContain("✔");
  });

  it("有失败则 exit 1", () => {
    writeFileSync(join(dir, ".narness.toml"), '[[checks]]\ntype = "exists"\nname = "definitely-not-a-real-cmd-xyz"\n');
    const r = runIn(dir);
    expect(r.code).toBe(1);
    expect(r.stdout).toContain("✗");
  });

  it("--json 输出结构化", () => {
    writeFileSync(join(dir, ".narness.toml"), '[[checks]]\ntype = "exists"\nname = "git"\n');
    const r = runIn(dir, ["--json"]);
    expect(r.code).toBe(0);
    const obj = JSON.parse(r.stdout);
    expect(obj.ok).toBe(true);
    expect(obj.results[0].name).toBe("git");
  });

  it("无配置则 exit 2", () => {
    const empty = mkdtempSync(join(tmpdir(), "narness-empty-"));
    const r = runIn(empty);
    expect(r.code).toBe(2);
  });
});
