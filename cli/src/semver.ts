import semver from "semver";

export function extractVersion(output: string): string | null {
  const m = output.match(/\d+\.\d+(\.\d+)?/);
  return m ? m[0] : null;
}

export function compareVersion(
  actual: string,
  min?: string,
  max?: string
): { ok: boolean; reason?: string } {
  const a = semver.coerce(actual);
  if (!a) return { ok: false, reason: `无法解析版本 "${actual}"` };
  if (min) {
    const m = semver.coerce(min);
    if (!m) return { ok: false, reason: `配置的 min "${min}" 不是合法版本` };
    if (semver.lt(a, m)) return { ok: false, reason: `${actual} < ${min}` };
  }
  if (max) {
    const x = semver.coerce(max);
    if (!x) return { ok: false, reason: `配置的 max "${max}" 不是合法版本` };
    if (semver.gt(a, x)) return { ok: false, reason: `${actual} > ${max}` };
  }
  return { ok: true };
}
