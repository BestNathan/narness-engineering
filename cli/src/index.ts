#!/usr/bin/env node
import { execFileSync } from "node:child_process";
import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
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
      let dir = cwd;
      for (;;) {
        const p = resolve(dir, ".mcp.json");
        if (existsSync(p)) {
          try {
            const data = JSON.parse(readFileSync(p, "utf8")) as { mcpServers?: Record<string, unknown> };
            return Object.keys(data.mcpServers ?? {});
          } catch {
            return [];
          }
        }
        const parent = dirname(dir);
        if (parent === dir) return [];
        dir = parent;
      }
    },
  };
}

function parseArgs(argv: string[]) {
  const json = argv.includes("--json");
  let configPath: string | undefined;
  const idx = argv.indexOf("--config");
  if (idx >= 0 && idx + 1 < argv.length) {
    configPath = argv[idx + 1];
  } else {
    const flag = argv.find((a) => a.startsWith("--config="));
    if (flag) configPath = flag.slice("--config=".length);
  }
  return { json, configPath };
}

async function main() {
  const { json, configPath } = parseArgs(process.argv.slice(2));
  const cwd = process.cwd();

  const path = configPath ? resolve(configPath) : findConfig(cwd);
  if (!path) {
    console.error("Could not find .narness.toml (searched upward from the current directory)");
    process.exit(2);
  }

  let config;
  try {
    config = loadConfig(path);
  } catch (err) {
    console.error(`Config parse failed: ${(err as Error).message}`);
    process.exit(2);
  }

  let results;
  try {
    results = await runChecks(config, realContext(cwd));
  } catch (err) {
    console.error(`Config error: ${(err as Error).message}`);
    process.exit(2);
  }
  console.log(json ? reportJson(results) : reportHuman(results));

  const failed = results.some((r) => r.status !== "pass");
  process.exit(failed ? 1 : 0);
}

main();
