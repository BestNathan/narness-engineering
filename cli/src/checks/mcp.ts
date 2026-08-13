import type { Check, CheckConfig, CheckResult, Context } from "./check.js";

export const mcpCheck: Check = {
  async run(check: CheckConfig, ctx: Context): Promise<CheckResult> {
    const servers = ctx.readMcpServers();
    if (servers.includes(check.name)) {
      return { status: "pass", check, detail: `MCP '${check.name}' 已声明` };
    }
    return {
      status: "fail",
      check,
      message: `MCP '${check.name}' 未声明`,
      fix: check.fix ?? `请在 .mcp.json 的 mcpServers 中添加 '${check.name}'`,
    };
  },
};
