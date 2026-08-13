import type { CheckResult } from "./checks/check.js";

export function reportHuman(results: CheckResult[]): string {
  const lines = results.map((r) => {
    const name = r.check.name;
    if (r.status === "pass") {
      return `✔ ${name}${r.detail ? " (" + r.detail + ")" : ""}`;
    }
    const mark = r.status === "error" ? "⚠" : "✗";
    const parts = [`${mark} ${name}`];
    if (r.message) parts.push(r.message);
    if (r.fix) parts.push(`→ ${r.fix}`);
    return parts.join("  ");
  });
  const passed = results.filter((r) => r.status === "pass").length;
  const failed = results.length - passed;
  lines.push("", `${passed} passed, ${failed} failed`);
  return lines.join("\n");
}

export function reportJson(results: CheckResult[]): string {
  const passed = results.filter((r) => r.status === "pass").length;
  const failed = results.length - passed;
  return JSON.stringify(
    {
      ok: failed === 0,
      passed,
      failed,
      results: results.map((r) => ({
        type: r.check.type,
        name: r.check.name,
        status: r.status,
        message: r.message,
        fix: r.fix,
        detail: r.detail,
      })),
    },
    null,
    2
  );
}
