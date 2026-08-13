import type { Check, CheckConfig, CheckResult, Context } from "./check.js";

export const mcpCheck: Check = {
  async run(check: CheckConfig, ctx: Context): Promise<CheckResult> {
    const servers = ctx.readMcpServers();
    if (servers.includes(check.name)) {
      return { status: "pass", check, detail: `MCP '${check.name}' declared` };
    }
    return {
      status: "fail",
      check,
      message: `MCP '${check.name}' not declared`,
      fix: check.fix ?? `add '${check.name}' to mcpServers in .mcp.json`,
    };
  },
};
