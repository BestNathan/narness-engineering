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
  it("finds .narness.toml in the current directory", () => {
    const dir = tmpProject();
    writeFileSync(join(dir, ".narness.toml"), "[[checks]]\ntype=\"exists\"\nname=\"rg\"\n");
    expect(findConfig(dir)).toBe(join(dir, ".narness.toml"));
  });
  it("finds .narness.toml by walking up from a subdirectory", () => {
    const dir = tmpProject();
    writeFileSync(join(dir, ".narness.toml"), "[[checks]]\n");
    expect(findConfig(join(dir, "src"))).toBe(join(dir, ".narness.toml"));
  });
  it("returns null when not found", () => {
    const dir = tmpProject();
    expect(findConfig(dir)).toBeNull();
  });
});

describe("loadConfig", () => {
  it("parses the checks array", () => {
    const dir = tmpProject();
    const p = join(dir, ".narness.toml");
    writeFileSync(p, '[[checks]]\ntype = "version"\nname = "node"\nmin = "22"\n');
    const cfg = loadConfig(p);
    expect(cfg.checks).toHaveLength(1);
    expect(cfg.checks[0]).toEqual({ type: "version", name: "node", min: "22" });
  });
  it("throws when name is missing", () => {
    const dir = tmpProject();
    const p = join(dir, ".narness.toml");
    writeFileSync(p, '[[checks]]\ntype = "version"\n');
    expect(() => loadConfig(p)).toThrow();
  });
});
