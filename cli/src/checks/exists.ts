import type { Check, CheckConfig, CheckResult, Context } from "./check.js";

export const existsCheck: Check = {
  async run(check: CheckConfig, ctx: Context): Promise<CheckResult> {
    const targets = [check.name, ...(check.names ?? [])];
    const missing = targets.filter((t) => !ctx.which(t));
    if (missing.length === 0) {
      return { status: "pass", check, detail: targets.join(", ") + " 已安装" };
    }
    const list = missing.join(", ");
    return {
      status: "fail",
      check,
      message: `缺少工具: ${list}`,
      fix: check.fix ?? `请安装 ${list}`,
    };
  },
};
