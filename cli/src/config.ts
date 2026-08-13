import { parse } from "smol-toml";
import { readFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import type { CheckConfig } from "./checks/check.js";

export interface Config {
  checks: CheckConfig[];
}

export function findConfig(startDir: string): string | null {
  let dir = startDir;
  for (;;) {
    const p = join(dir, ".narness.toml");
    if (existsSync(p)) return p;
    const parent = dirname(dir);
    if (parent === dir) return null;
    dir = parent;
  }
}

export function loadConfig(path: string): Config {
  const raw = readFileSync(path, "utf8");
  let parsed: unknown;
  try {
    parsed = parse(raw);
  } catch (err) {
    throw new Error(`TOML parse failed: ${(err as Error).message}`);
  }
  const obj = (parsed ?? {}) as { checks?: unknown };
  if (obj.checks !== undefined && !Array.isArray(obj.checks)) {
    throw new Error(`checks must be an array`);
  }
  const checks = ((obj.checks ?? []) as unknown[]).map(normalizeCheck);
  return { checks };
}

function normalizeCheck(c: unknown): CheckConfig {
  if (typeof c !== "object" || c === null) {
    throw new Error(`invalid check entry: ${JSON.stringify(c)}`);
  }
  const o = c as Record<string, unknown>;
  if (typeof o.type !== "string" || typeof o.name !== "string") {
    throw new Error(`check is missing type/name: ${JSON.stringify(c)}`);
  }
  if (o.names !== undefined && !Array.isArray(o.names)) {
    throw new Error(`check ${o.name}: names must be an array`);
  }
  return {
    type: o.type,
    name: o.name,
    min: typeof o.min === "string" ? o.min : undefined,
    max: typeof o.max === "string" ? o.max : undefined,
    names: Array.isArray(o.names) && o.names.every((n) => typeof n === "string") ? (o.names as string[]) : undefined,
    fix: typeof o.fix === "string" ? o.fix : undefined,
  };
}
