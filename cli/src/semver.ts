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
  if (!a) return { ok: false, reason: `Unable to parse version "${actual}"` };
  if (min) {
    const m = semver.coerce(min);
    if (!m) return { ok: false, reason: `configured min "${min}" is not a valid version` };
    if (semver.lt(a, m)) return { ok: false, reason: `${actual} < ${min}` };
  }
  if (max) {
    const x = semver.coerce(max);
    if (!x) return { ok: false, reason: `configured max "${max}" is not a valid version` };
    if (semver.gt(a, x)) return { ok: false, reason: `${actual} > ${max}` };
  }
  return { ok: true };
}
