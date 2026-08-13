import { execFileSync } from "node:child_process";
import { readFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";
import { findConfig, loadConfig } from "./config.js";
import { runChecks } from "./engine.js";
import { reportHuman, reportJson } from "./report.js";
import type { Context } from "./checks/check.js";

function realContext(cwd: string): Context {
  return {
    cwd,
    runCommand(cmd, args) {
      try {
        const stdout = execFileSync(cmd, args, { encoding: "utf8" });
        return Promise.resolve({ code: 0, stdout, stderr: "" });
      } catch (err) {
        const e = err as { status?: number; stdout?: string; stderr?: string };
        return Promise.resolve({ code: e.status ?? 1, stdout: e.stdout ?? "", stderr: e.stderr ?? "" });
      }
    },
    which(cmd) {
      try {
        execFileSync("command", ["-v", cmd], { stdio: "ignore" });
        return true;
      } catch {
        return false;
      }
    },
    readMcpServers() {
      const p = resolve(cwd, ".mcp.json");
      if (!existsSync(p)) return [];
      try {
        const data = JSON.parse(readFileSync(p, "utf8")) as { mcpServers?: Record<string, unknown> };
        return Object.keys(data.mcpServers ?? {});
      } catch {
        return [];
      }
    },
  };
}

function parseArgs(argv: string[]) {
  const json = argv.includes("--json");
  const configFlag = argv.find((a) => a.startsWith("--config="));
  const configPath = configFlag ? configFlag.slice("--config=".length) : undefined;
  return { json, configPath };
}

async function main() {
  const { json, configPath } = parseArgs(process.argv.slice(2));
  const cwd = process.cwd();

  const path = configPath ? resolve(configPath) : findConfig(cwd);
  if (!path) {
    console.error("未找到 .narness.toml（已从当前目录向上查找）");
    process.exit(2);
  }

  let config;
  try {
    config = loadConfig(path);
  } catch (err) {
    console.error(`配置解析失败: ${(err as Error).message}`);
    process.exit(2);
  }

  const results = await runChecks(config, realContext(cwd));
  console.log(json ? reportJson(results) : reportHuman(results));

  const failed = results.some((r) => r.status !== "pass");
  process.exit(failed ? 1 : 0);
}

main();
