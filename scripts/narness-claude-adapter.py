#!/usr/bin/env python3
"""Translate Claude Code stream-json into the unchanged benchmark trace contract.

The active execution path invokes an installed Claude Code binary directly from
the isolated subject checkout. Only the Anthropic credential and base URL are
passed to that child process; Narness paths and other harness environment values
are scrubbed before launch.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import signal
import shutil
import sys
import time

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('trace_commands', ROOT / 'scripts/ai-native-codex-adapter.py')
common = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)
TOOLS = 'Bash,Read,Edit,Write,Glob,Grep'
AGENT_KEYS = (
    'claude_version',
    'claude_bin',
    'base_url',
    'credential_env',
    'runtime_mode',
    'max_turns',
    'command_mapper_sha256',
)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def capture(args):
    return subprocess.check_output(args, text=True).strip()


def runtime_identity(expected_model, *, require_credentials=True):
    """Return non-secret identity data for the installed direct Claude client."""
    claude_bin = os.environ.get('NARNESS_CLAUDE_BIN', 'claude')
    resolved = shutil.which(claude_bin)
    if resolved is None:
        raise RuntimeError(
            f"Claude Code executable not found: {claude_bin!r}. "
            "Install @anthropic-ai/claude-code and ensure it is on PATH."
        )

    version = capture([resolved, '--version'])
    base_url = os.environ.get('ANTHROPIC_BASE_URL')
    if not base_url:
        raise RuntimeError('ANTHROPIC_BASE_URL is required for the direct Claude pilot')
    if not (base_url.startswith('https://') or base_url.startswith('http://')):
        raise RuntimeError('ANTHROPIC_BASE_URL must be an http(s) URL')

    credential_env = next(
        (name for name in ('ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN') if os.environ.get(name)),
        None,
    )
    if require_credentials and credential_env is None:
        raise RuntimeError(
            'Set ANTHROPIC_API_KEY (or ANTHROPIC_AUTH_TOKEN) before running Claude pilots'
        )

    if expected_model in ('sonnet', 'opus', 'haiku', 'default'):
        raise RuntimeError('Use an explicit Claude model ID, not a moving alias')

    return {
        'claude_version': version,
        'claude_bin': resolved,
        'base_url': base_url,
        'credential_env': credential_env,
        'runtime_mode': 'direct-host',
    }


def cli_args(model, effort, max_turns):
    return ['claude', '-p', '--output-format', 'stream-json', '--verbose',
            '--model', model, '--effort', effort, '--max-turns', str(max_turns),
            '--permission-mode', 'dontAsk',
            '--no-session-persistence', '--setting-sources', '',
            '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}',
            '--disable-slash-commands', '--tools', TOOLS,
            '--allowedTools', 'Bash(*)', 'Read', 'Edit', 'Write', 'Glob', 'Grep',
            '--disallowedTools', 'Agent', 'Task', 'WebFetch', 'WebSearch', 'EndConversation', 'mcp__*',
            '--settings', '{"disableAllHooks":true}']


class Translator:
    def __init__(self, trace, origin):
        self.trace, self.origin = trace, origin
        self.pending, self.seen = {}, set()
        self.results = 0
        self.resolved_models = set()

    def emit(self, kind, **values):
        common.append_jsonl(self.trace, {'type': kind, 'ts_ms': common.now_ms(self.origin), **values})

    @staticmethod
    def path(value):
        if not isinstance(value, str):
            return ''
        return value.removeprefix('/workspace/').removeprefix('./')

    def process(self, event):
        if event.get('parent_tool_use_id'):
            raise RuntimeError('Unexpected subagent event')
        kind = event.get('type')
        if kind == 'assistant':
            message = event.get('message', {})
            for block in message.get('content', []):
                if block.get('type') == 'tool_use':
                    ident = block['id']
                    if ident not in self.seen:
                        if block['name'] not in TOOLS.split(','):
                            raise RuntimeError('Unexpected tool: ' + block['name'])
                        self.pending[ident] = block
                        self.seen.add(ident)
        elif kind == 'user':
            for block in event.get('message', {}).get('content', []):
                if block.get('type') != 'tool_result':
                    continue
                call = self.pending.pop(block['tool_use_id'], None)
                if call is None:
                    raise RuntimeError('Unmatched tool result')
                name, args = call['name'], call.get('input', {})
                failed = bool(block.get('is_error'))
                content = block.get('content', '')
                if isinstance(content, list):
                    content = '\n'.join(b.get('text', '') for b in content)
                if not isinstance(content, str):
                    content = json.dumps(content)
                if name == 'Bash':
                    command = args.get('command', '').replace('/workspace/', str(Path.cwd()) + '/')
                    # Claude's stream reports is_error rather than the exact shell exit code.
                    common.emit_command_trace(self.trace, self.origin, command, 1 if failed else 0,
                                              content.replace('/workspace/', str(Path.cwd()) + '/'))
                elif not failed and name == 'Read':
                    self.emit('read', path=self.path(args.get('file_path')))
                elif not failed and name in ('Edit', 'Write'):
                    self.emit('edit', paths=[self.path(args.get('file_path'))], operation='claude-' + name.lower())
                elif name in ('Glob', 'Grep'):
                    results = []
                    if not failed:
                        for line in content.splitlines():
                            candidate = line.split(':', 1)[0].strip()
                            candidate = self.path(candidate)
                            if candidate and (Path.cwd() / candidate).is_file():
                                results.append(candidate)
                    self.emit('glob' if name == 'Glob' else 'search',
                              pattern=args.get('pattern'), query=args.get('pattern'), results=sorted(set(results)))
        elif kind == 'result':
            self.results += 1
            if self.results != 1 or event.get('is_error') or event.get('subtype') != 'success':
                raise RuntimeError('Claude task did not produce one successful terminal result')
            usage = event.get('usage')
            if not isinstance(usage, dict) or 'input_tokens' not in usage or 'output_tokens' not in usage:
                raise RuntimeError('Claude result omitted usage')
            model_usage = event.get('modelUsage') or {}
            self.resolved_models.update(model_usage)
            self.emit('usage', input_tokens=int(usage['input_tokens']) + int(usage.get('cache_read_input_tokens', 0)) + int(usage.get('cache_creation_input_tokens', 0)),
                      output_tokens=int(usage['output_tokens']), cached_tokens=int(usage.get('cache_read_input_tokens', 0)),
                      reasoning_tokens=0, reasoning_tokens_available=False,
                      source='claude-result-cumulative', resolved_models=sorted(self.resolved_models))

    def finish(self):
        if self.pending or self.results != 1:
            raise RuntimeError('Incomplete tool results or missing terminal Claude result')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', required=True)
    ap.add_argument('--effort', default='high')
    ap.add_argument('--max-turns', type=int, default=100)
    ap.add_argument('--replay-jsonl', type=Path)
    ap.add_argument('--inspect-runtime', action='store_true')
    args = ap.parse_args()
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    if args.inspect_runtime:
        print(json.dumps(runtime_identity(args.model), sort_keys=True))
        return 0
    run_dir = Path(os.environ['NARNESS_RUN_DIR']).resolve()
    trace = Path(os.environ['NARNESS_TRACE_FILE']).resolve()
    prompt = Path(os.environ['NARNESS_PROMPT_FILE']).read_text()
    raw = run_dir / 'claude.raw.jsonl'
    stderr = run_dir / 'claude.stderr.log'
    trace.write_text('')
    origin = time.monotonic()
    identity = {} if args.replay_jsonl else runtime_identity(args.model)
    cfg = {'type': 'agent-config', 'ts_ms': 0,
           'agent': 'claude-code-replay' if args.replay_jsonl else 'claude-code',
           'model': args.model, 'reasoning_effort': args.effort, 'max_turns': args.max_turns,
           'adapter_file_sha256': digest(__file__), 'command_mapper_sha256': digest(ROOT / 'scripts/ai-native-codex-adapter.py'),
           'adapter_repository_sha': common.adapter_repo_head(),
           'network': 'provider-direct', 'subagents_enabled': False, 'web_search': 'disabled',
           'permission_profile': 'claude-direct-narness-r6',
           'filesystem_read_scope': 'isolated standalone subject checkout',
           'shell_environment_allowlist': ['PATH', 'HOME', 'TMPDIR', 'TMP', 'TEMP', 'LANG', 'LC_*', 'SHELL', 'USER', 'ANTHROPIC_BASE_URL', 'ANTHROPIC_API_KEY'],
           'harness_environment_scrubbed': True, 'raw_trace_file': 'claude.raw.jsonl', **identity}
    common.append_jsonl(trace, cfg)
    translator = Translator(trace, origin)
    proc = None
    rc = 1
    try:
        with raw.open('w') as output, stderr.open('w') as err:
            if args.replay_jsonl:
                stream = args.replay_jsonl.open()
            else:
                command = cli_args(args.model, args.effort, args.max_turns)
                command[0] = identity['claude_bin']
                allowed = {'PATH', 'HOME', 'TMPDIR', 'TMP', 'TEMP', 'LANG', 'SHELL', 'USER', 'ANTHROPIC_BASE_URL', 'ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC'}
                child_env = {key: value for key, value in os.environ.items() if key in allowed or key.startswith('LC_')}
                child_env['ANTHROPIC_BASE_URL'] = identity['base_url']
                child_env['CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC'] = '1'
                for key in ('ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN'):
                    if key != identity['credential_env']:
                        child_env.pop(key, None)
                proc = subprocess.Popen(command, cwd=Path.cwd(), env=child_env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=err, text=True)
                proc.stdin.write(prompt)
                proc.stdin.close()
                stream = proc.stdout
            with stream:
                for line in stream:
                    output.write(line)
                    output.flush()
                    if line.strip():
                        translator.process(json.loads(line))
            if proc and proc.wait() != 0:
                raise RuntimeError('Claude container exited unsuccessfully; inspect its preserved stderr')
            translator.finish()
            rc = 0
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            proc.wait()
        common.append_jsonl(trace, {'type': 'agent-exit', 'ts_ms': common.now_ms(origin), 'exit_code': rc})
    return rc

if __name__ == '__main__':
    raise SystemExit(main())
