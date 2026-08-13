import { describe, it, expect } from "vitest";
import { extractVersion, compareVersion } from "../src/semver.js";

describe("extractVersion", () => {
  it("提取 node 的 v22.14.0", () => {
    expect(extractVersion("v22.14.0")).toBe("22.14.0");
  });
  it("提取 cargo 的 cargo 1.70.0 (...)", () => {
    expect(extractVersion("cargo 1.70.0 (abc123 2023-01-01)")).toBe("1.70.0");
  });
  it("提取 git 的 git version 2.39.2", () => {
    expect(extractVersion("git version 2.39.2")).toBe("2.39.2");
  });
  it("无版本号返回 null", () => {
    expect(extractVersion("not a version")).toBeNull();
  });
});

describe("compareVersion", () => {
  it("22.14.0 满足 min=22", () => {
    expect(compareVersion("22.14.0", "22").ok).toBe(true);
  });
  it("18.0.0 不满足 min=22", () => {
    expect(compareVersion("18.0.0", "22").ok).toBe(false);
  });
  it("22 满足 min=22（宽松格式）", () => {
    expect(compareVersion("22", "22").ok).toBe(true);
  });
  it("30.0.0 不满足 max=22", () => {
    expect(compareVersion("30.0.0", undefined, "22").ok).toBe(false);
  });
  it("无法解析的版本返回不 ok", () => {
    expect(compareVersion("abc", "22").ok).toBe(false);
  });
});
