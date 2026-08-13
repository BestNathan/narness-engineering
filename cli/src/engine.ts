import type { Config } from "./config.js";
import type { CheckResult, Context } from "./checks/check.js";
import { getCheck } from "./registry.js";

export async function runChecks(config: Config, ctx: Context): Promise<CheckResult[]> {
  const results: CheckResult[] = [];
  for (const check of config.checks) {
    const impl = getCheck(check.type);
    if (!impl) {
      throw new Error(`unknown check type "${check.type}"`);
    }
    try {
      results.push(await impl.run(check, ctx));
    } catch (err) {
      results.push({ status: "error", check, message: `checker error: ${(err as Error).message}` });
    }
  }
  return results;
}
