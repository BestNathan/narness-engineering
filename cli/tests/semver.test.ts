import { describe, it, expect } from "vitest";
import { extractVersion, compareVersion } from "../src/semver.js";

describe("extractVersion", () => {
  it("extracts v22.14.0 from node", () => {
    expect(extractVersion("v22.14.0")).toBe("22.14.0");
  });
  it("extracts cargo 1.70.0 (...) from cargo", () => {
    expect(extractVersion("cargo 1.70.0 (abc123 2023-01-01)")).toBe("1.70.0");
  });
  it("extracts git version 2.39.2 from git", () => {
    expect(extractVersion("git version 2.39.2")).toBe("2.39.2");
  });
  it("returns null when no version", () => {
    expect(extractVersion("not a version")).toBeNull();
  });
});

describe("compareVersion", () => {
  it("22.14.0 satisfies min=22", () => {
    expect(compareVersion("22.14.0", "22").ok).toBe(true);
  });
  it("18.0.0 does not satisfy min=22", () => {
    expect(compareVersion("18.0.0", "22").ok).toBe(false);
  });
  it("22 satisfies min=22 (loose format)", () => {
    expect(compareVersion("22", "22").ok).toBe(true);
  });
  it("30.0.0 does not satisfy max=22", () => {
    expect(compareVersion("30.0.0", undefined, "22").ok).toBe(false);
  });
  it("unparseable version returns not ok", () => {
    expect(compareVersion("abc", "22").ok).toBe(false);
  });
});
