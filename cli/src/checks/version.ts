import type { Check, CheckConfig, CheckResult, Context } from "./check.js";
import { extractVersion, compareVersion } from "../semver.js";

export const versionCheck: Check = {
  async run(check: CheckConfig, ctx: Context): Promise<CheckResult> {
    const res = await ctx.runCommand(check.name, ["--version"]);
    if (res.code !== 0) {
      return {
        status: "error",
        check,
        message: `${check.name} --version 执行失败`,
        fix: check.fix ?? `请先安装 ${check.name}`,
      };
    }
    const actual = extractVersion(res.stdout);
    if (!actual) {
      return { status: "error", check, message: `无法从 "${res.stdout.trim()}" 解析版本号` };
    }
    const cmp = compareVersion(actual, check.min, check.max);
    if (!cmp.ok) {
      const want = [check.min ? `>= ${check.min}` : "", check.max ? `<= ${check.max}` : ""]
        .filter(Boolean)
        .join(" 且 ");
      return {
        status: "fail",
        check,
        message: `版本 ${actual} 不满足要求（需 ${want}）`,
        fix: check.fix ?? `请升级 ${check.name}`,
        detail: cmp.reason,
      };
    }
    return { status: "pass", check, detail: `${check.name} ${actual}` };
  },
};
