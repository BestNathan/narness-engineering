export interface CheckConfig {
  type: string;
  name: string;
  min?: string;
  max?: string;
  names?: string[];
  fix?: string;
}

export type CheckStatus = "pass" | "fail" | "error";

export interface CheckResult {
  status: CheckStatus;
  check: CheckConfig;
  message?: string;
  fix?: string;
  detail?: string;
}

export interface CommandResult {
  code: number;
  stdout: string;
  stderr: string;
}

export interface Context {
  cwd: string;
  runCommand(cmd: string, args: string[]): Promise<CommandResult>;
  which(cmd: string): boolean;
  readMcpServers(): string[];
}

export interface Check {
  run(check: CheckConfig, ctx: Context): Promise<CheckResult>;
}
