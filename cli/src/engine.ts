import type { Config } from "./config.js";
import type { CheckResult, Context } from "./checks/check.js";
import { getCheck } from "./registry.js";

export async function runChecks(config: Config, ctx: Context): Promise<CheckResult[]> {
  const results: CheckResult[] = [];
  for (const check of config.checks) {
    const impl = getCheck(check.type);
    if (!impl) {
      throw new Error(`未知检查类型 "${check.type}"`);
    }
    try {
      results.push(await impl.run(check, ctx));
    } catch (err) {
      results.push({ status: "error", check, message: `检查器异常: ${(err as Error).message}` });
    }
  }
  return results;
}
