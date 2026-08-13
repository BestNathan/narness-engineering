import { describe, it, expect } from "vitest";
import { mkdtempSync, writeFileSync, mkdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { findConfig, loadConfig } from "../src/config.js";

function tmpProject() {
  const dir = mkdtempSync(join(tmpdir(), "narness-"));
  mkdirSync(join(dir, "src"), { recursive: true });
  return dir;
}

describe("findConfig", () => {
  it("在当前目录找到 .narness.toml", () => {
    const dir = tmpProject();
    writeFileSync(join(dir, ".narness.toml"), "[[checks]]\ntype=\"exists\"\nname=\"rg\"\n");
    expect(findConfig(dir)).toBe(join(dir, ".narness.toml"));
  });
  it("从子目录向上找到 .narness.toml", () => {
    const dir = tmpProject();
    writeFileSync(join(dir, ".narness.toml"), "[[checks]]\n");
    expect(findConfig(join(dir, "src"))).toBe(join(dir, ".narness.toml"));
  });
  it("找不到返回 null", () => {
    const dir = tmpProject();
    expect(findConfig(dir)).toBeNull();
  });
});

describe("loadConfig", () => {
  it("解析 checks 数组", () => {
    const dir = tmpProject();
    const p = join(dir, ".narness.toml");
    writeFileSync(p, '[[checks]]\ntype = "version"\nname = "node"\nmin = "22"\n');
    const cfg = loadConfig(p);
    expect(cfg.checks).toHaveLength(1);
    expect(cfg.checks[0]).toEqual({ type: "version", name: "node", min: "22" });
  });
  it("缺失 name 抛错", () => {
    const dir = tmpProject();
    const p = join(dir, ".narness.toml");
    writeFileSync(p, '[[checks]]\ntype = "version"\n');
    expect(() => loadConfig(p)).toThrow();
  });
});
