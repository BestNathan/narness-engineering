import type { Check, CheckConfig, CheckResult, Context } from "./check.js";
import { extractVersion, compareVersion } from "../semver.js";

export const versionCheck: Check = {
  async run(check: CheckConfig, ctx: Context): Promise<CheckResult> {
    const res = await ctx.runCommand(check.name, ["--version"]);
    if (res.code !== 0) {
      return {
        status: "error",
        check,
        message: `${check.name} --version failed`,
        fix: check.fix ?? `please install ${check.name} first`,
      };
    }
    const actual = extractVersion(res.stdout);
    if (!actual) {
      return { status: "error", check, message: `unable to parse a version number from "${res.stdout.trim()}"` };
    }
    const cmp = compareVersion(actual, check.min, check.max);
    if (!cmp.ok) {
      const want = [check.min ? `>= ${check.min}` : "", check.max ? `<= ${check.max}` : ""]
        .filter(Boolean)
        .join(" and ");
      return {
        status: "fail",
        check,
        message: `version ${actual} does not meet requirements (needs ${want})`,
        fix: check.fix ?? `please upgrade ${check.name}`,
        detail: cmp.reason,
      };
    }
    return { status: "pass", check, detail: `${check.name} ${actual}` };
  },
};
