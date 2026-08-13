import type { Check } from "./checks/check.js";
import { versionCheck } from "./checks/version.js";
import { existsCheck } from "./checks/exists.js";
import { mcpCheck } from "./checks/mcp.js";

export const registry: Record<string, Check> = {
  version: versionCheck,
  exists: existsCheck,
  mcp: mcpCheck,
};

export function getCheck(type: string): Check | undefined {
  return registry[type];
}
