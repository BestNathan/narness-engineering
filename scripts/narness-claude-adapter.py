#!/usr/bin/env python3
"""Translate Claude Code stream-json into the unchanged benchmark trace contract.

The Claude client runs in an outer bubblewrap mount/PID/network namespace.
Claude's Bash tool is additionally forced through Claude Code's strict sandbox,
with no network or Unix-socket access and no provider environment. Only the
current subject checkout and runtime files are mounted; Git metadata and setup
dependencies are read-only. HOME, Claude state and temporary files are private
to each invocation. Provider access is limited to the client process through a
credential-bearing, fixed-provider Unix gateway.
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
import contextlib
import http.client
from http.server import BaseHTTPRequestHandler
import socketserver
import tempfile
import threading
from urllib.parse import urlsplit

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
    'sandbox_runtime_version',
    'provider_policy',
    'max_turns',
    'command_mapper_sha256',
)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def capture(args):
    return subprocess.check_output(args, text=True).strip()


def package_version_for_executable(executable, package_name):
    path = Path(executable).resolve()
    for parent in (path.parent, *path.parents):
        manifest = parent / 'package.json'
        if not manifest.is_file():
            continue
        try:
            data = json.loads(manifest.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if data.get('name') == package_name and data.get('version'):
            return str(data['version'])
    raise RuntimeError(f'Cannot resolve {package_name} version from {executable}')


def readonly_dependency_dirs(subject):
    """Return setup-produced dependency trees that the agent may execute but not alter."""
    result = []
    for root, dirs, _ in os.walk(subject):
        if '.git' in dirs:
            dirs.remove('.git')
        if 'node_modules' in dirs:
            candidate = Path(root) / 'node_modules'
            if candidate.is_dir() and not candidate.is_symlink():
                result.append(candidate)
            dirs.remove('node_modules')
    return result


def claude_settings():
    """Hard policy for Claude-spawned Bash processes.

    The outer namespace protects the host. This inner sandbox is what prevents a
    Bash tool (or one of its children) from reaching the provider bridge that the
    Claude client itself must use.
    """
    return {
        'disableAllHooks': True,
        'sandbox': {
            'enabled': True,
            'failIfUnavailable': True,
            'allowUnsandboxedCommands': False,
            'enableWeakerNestedSandbox': False,
            'excludedCommands': [],
            'network': {
                'allowedDomains': [],
                'deniedDomains': ['127.0.0.1', '[::1]'],
                'allowUnixSockets': [],
                'allowAllUnixSockets': False,
                'allowLocalBinding': False,
                'strictAllowlist': True,
            },
            'credentials': {
                'envVars': [
                    {'name': 'ANTHROPIC_API_KEY', 'mode': 'deny'},
                    {'name': 'ANTHROPIC_AUTH_TOKEN', 'mode': 'deny'},
                    {'name': 'ANTHROPIC_BASE_URL', 'mode': 'deny'},
                ],
            },
        },
    }


def sandbox_command(subject, command, environment, gateway_socket=None):
    """Build a deny-by-default filesystem view; never fall back to direct execution.

    Keep this policy in the adapter so its existing frozen file hash covers it.
    The caller must supply the standalone treatment checkout, never the controller.
    """
    bwrap = shutil.which('bwrap')
    if bwrap is None:
        raise RuntimeError('bubblewrap is required; direct-host fallback is forbidden')
    srt = shutil.which('srt')
    if srt is None:
        raise RuntimeError('Anthropic sandbox-runtime is required for Bash isolation')
    subject = Path(subject).resolve(strict=True)
    if not (subject / '.git').is_dir() or (subject / '.git').is_symlink():
        raise RuntimeError('Sandbox requires a standalone Git checkout')
    if (subject / '.git/objects/info/alternates').exists():
        raise RuntimeError('Shared Git object databases are forbidden')
    # Nested user namespaces are intentionally available *inside* this already
    # isolated namespace so Claude Code can put Bash in its own bwrap sandbox.
    # A nested namespace cannot recover mounts, host PIDs, or host networking
    # that the outer namespace never exposed.
    argv = [bwrap, '--unshare-all', '--unshare-user', '--die-with-parent',
            '--new-session', '--cap-drop', 'ALL']
    # Do not mount /, /home, /tmp, /run, /opt or the controller checkout.
    for path in ('/usr', '/bin', '/sbin', '/lib', '/lib64'):
        if Path(path).is_symlink():
            argv += ['--symlink', os.readlink(path), path]
        elif Path(path).exists():
            argv += ['--ro-bind', path, path]
    # Ubuntu's /usr/bin/which may resolve through /etc/alternatives. SRT uses
    # the external "which" binary for dependency discovery, so expose only
    # that system indirection rather than the host /etc tree.
    argv += ['--dir', '/etc']
    if Path('/etc/alternatives').is_dir():
        argv += ['--ro-bind', '/etc/alternatives', '/etc/alternatives']
    node = shutil.which('node')
    if node is None:
        raise RuntimeError('Node runtime is required')
    node_root = Path(node).resolve().parent.parent
    # setup-node installs both node and globally installed Claude beneath this
    # exact version directory. Reject arbitrary runtime mounts (e.g. HOME).
    if node_root != Path('/usr'):
        if not str(node_root).startswith('/opt/hostedtoolcache/node/'):
            raise RuntimeError('Use the GitHub setup-node runtime under /opt/hostedtoolcache/node')
        argv += ['--ro-bind', str(node_root), str(node_root)]
    argv += ['--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp',
             '--tmpfs', '/home', '--dir', '/home/agent',
             '--dir', '/home/agent/.claude', '--dir', '/home/agent/.cache',
             '--bind', str(subject), '/workspace',
             '--ro-bind', str(subject / '.git'), '/workspace/.git']
    for dependency in readonly_dependency_dirs(subject):
        relative = dependency.relative_to(subject)
        argv += ['--ro-bind', str(dependency), '/workspace/' + relative.as_posix()]
    argv += ['--chdir', '/workspace']
    clean = {'HOME': '/home/agent', 'CLAUDE_CONFIG_DIR': '/home/agent/.claude',
             'XDG_CONFIG_HOME': '/home/agent/.config', 'XDG_CACHE_HOME': '/home/agent/.cache',
             'TMPDIR': '/tmp', 'TMP': '/tmp', 'TEMP': '/tmp',
             'PATH': str(node_root / 'bin') + ':/usr/bin:/bin',
             'LANG': 'C.UTF-8', 'SHELL': '/bin/bash', 'USER': 'agent',
             'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC': '1',
             'CLAUDE_CODE_SUBPROCESS_ENV_SCRUB': '1'}
    if gateway_socket is not None:
        if shutil.which('socat') is None:
            raise RuntimeError('socat is required for the provider bridge')
        argv += ['--ro-bind', str(gateway_socket), '/run/provider.sock']
        clean['ANTHROPIC_BASE_URL'] = 'http://127.0.0.1:18080'
        clean['ANTHROPIC_API_KEY'] = 'sandbox-placeholder'
        command = ['/bin/bash', '-c',
                   'socat TCP-LISTEN:18080,bind=127.0.0.1,reuseaddr,fork '
                   'UNIX-CONNECT:/run/provider.sock & '
                   'for i in {1..50}; do '
                   'if (: >/dev/tcp/127.0.0.1/18080) 2>/dev/null; then exec "$@"; fi; '
                   'sleep 0.1; done; exit 70', 'provider-bridge', *command]
    return argv + ['--', *command], clean


def sandbox_launch(subject, command, environment, gateway_socket=None, **kwargs):
    """Real provider credentials never enter the sandbox or process argv."""
    argv, clean = sandbox_command(subject, command, environment, gateway_socket)
    return subprocess.Popen(argv, env=clean, close_fds=True, **kwargs)


@contextlib.contextmanager
def model_gateway(base_url, credential, model):
    """Expose only messages/count_tokens for one fixed HTTPS origin and model.

    Do not forward client routing/auth headers or follow upstream redirects.
    The socket is unique per invocation; no host TCP listener is exposed.
    """
    upstream = urlsplit(base_url)
    if (upstream.scheme != 'https' or not upstream.hostname or upstream.username
            or upstream.password or upstream.query or upstream.fragment):
        raise RuntimeError('Provider gateway requires a credential-free HTTPS base URL')

    allowed_local_tools = set(TOOLS.split(','))

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            if self.path not in ('/v1/messages', '/v1/messages?beta=true',
                                  '/v1/messages/count_tokens', '/v1/messages/count_tokens?beta=true'):
                self.send_error(403)
                return
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if self.headers.get('Transfer-Encoding') or not 0 < size <= 32 * 1024 * 1024:
                    self.send_error(413)
                    return
                body = self.rfile.read(size)
                payload = json.loads(body)
                if not isinstance(payload, dict) or payload.get('model') != model:
                    self.send_error(403)
                    return
                # Freeze the provider-side tool surface as well as the model.
                # Typed/server tools (web search, code execution, computer use,
                # etc.) are never part of this benchmark. Custom tools must be
                # exactly the local Claude Code tools admitted by cli_args().
                for tool in payload.get('tools', []):
                    if not isinstance(tool, dict) or tool.get('type'):
                        self.send_error(403)
                        return
                    if tool.get('name') not in allowed_local_tools:
                        self.send_error(403)
                        return
                headers = {'Content-Type': 'application/json', 'x-api-key': credential,
                           'Authorization': 'Bearer ' + credential,
                           'anthropic-version': self.headers.get('anthropic-version', '2023-06-01')}
                if self.headers.get('anthropic-beta'):
                    headers['anthropic-beta'] = self.headers['anthropic-beta']
                conn = http.client.HTTPSConnection(upstream.hostname, upstream.port or 443, timeout=180)
                try:
                    conn.request('POST', upstream.path.rstrip('/') + self.path, body, headers)
                    res = conn.getresponse()
                    self.send_response(res.status)
                    self.send_header('Content-Type', res.getheader('Content-Type', 'application/json'))
                    self.send_header('Connection', 'close')
                    self.end_headers()
                    while chunk := res.read1(8192):
                        self.wfile.write(chunk)
                        self.wfile.flush()
                finally:
                    conn.close()
            except Exception:
                # Never log credentials, request bodies or provider error details.
                self.close_connection = True

    class Server(socketserver.ThreadingUnixStreamServer):
        daemon_threads = True

    with tempfile.TemporaryDirectory(prefix='narness-provider-') as temp:
        sock = Path(temp) / 'provider.sock'
        with Server(str(sock), Handler) as server:
            os.chmod(sock, 0o600)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                yield sock
            finally:
                server.shutdown()
                thread.join(timeout=5)


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

    srt = shutil.which('srt')
    if srt is None:
        raise RuntimeError('Install @anthropic-ai/sandbox-runtime for Claude Bash isolation')

    return {
        'claude_version': version,
        'claude_bin': resolved,
        'base_url': base_url,
        'credential_env': credential_env,
        'runtime_mode': 'bubblewrap-claude-bash-sandbox-provider-gateway-v2',
        'bubblewrap_version': capture(['bwrap', '--version']),
        'sandbox_runtime_version': package_version_for_executable(
            srt, '@anthropic-ai/sandbox-runtime'),
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
            '--settings', json.dumps(claude_settings(), sort_keys=True, separators=(',', ':'))]


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
        kind = event.get('type')
        parent_id = event.get('parent_tool_use_id')
        if parent_id:
            parent = self.pending.get(parent_id)
            heartbeat_id = event.get('tool_use_id', '')
            if (
                kind == 'tool_progress'
                and parent is not None
                and parent.get('name') == event.get('tool_name')
                and event.get('tool_name') in TOOLS.split(',')
                and heartbeat_id.startswith(f'{parent_id}-heartbeat-')
            ):
                # Claude Code emits progress heartbeats for active root tool calls.
                # They are not subagent messages and carry no experiment event.
                return
            raise RuntimeError('Unexpected subagent event')
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
           'network': 'outer-private-net-fixed-provider; bash-strict-no-network', 'subagents_enabled': False, 'web_search': 'disabled',
           'permission_profile': 'claude-bubblewrap-bash-sandbox-provider-gateway-v2',
           'provider_policy': 'fixed-https-origin-route-model-local-tool-schema-no-server-tools-v2',
           'filesystem_read_scope': 'current subject plus read-only runtime; read-only .git/dependencies; private HOME/tmp',
           'bash_network': 'strict-deny-all-including-loopback-and-unix-sockets',
           'git_metadata': 'read-only',
           'shell_environment_allowlist': ['PATH', 'HOME', 'CLAUDE_CONFIG_DIR', 'XDG_CONFIG_HOME', 'XDG_CACHE_HOME', 'TMPDIR', 'TMP', 'TEMP', 'LANG', 'SHELL', 'USER', 'ANTHROPIC_BASE_URL', 'ANTHROPIC_API_KEY', 'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC', 'CLAUDE_CODE_SUBPROCESS_ENV_SCRUB'],
           'harness_environment_scrubbed': True, 'raw_trace_file': 'claude.raw.jsonl', **identity}
    common.append_jsonl(trace, cfg)
    translator = Translator(trace, origin)
    proc = None
    rc = 1
    try:
        with contextlib.ExitStack() as resources, raw.open('w') as output, stderr.open('w') as err:
            if args.replay_jsonl:
                stream = args.replay_jsonl.open()
            else:
                command = cli_args(args.model, args.effort, args.max_turns)
                command[0] = identity['claude_bin']
                allowed = {'PATH', 'HOME', 'TMPDIR', 'TMP', 'TEMP', 'LANG', 'SHELL', 'USER', 'ANTHROPIC_BASE_URL', 'ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC', 'CLAUDE_CODE_SUBPROCESS_ENV_SCRUB'}
                child_env = {key: value for key, value in os.environ.items() if key in allowed or key.startswith('LC_')}
                child_env['ANTHROPIC_BASE_URL'] = identity['base_url']
                child_env['CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC'] = '1'
                child_env['CLAUDE_CODE_SUBPROCESS_ENV_SCRUB'] = '1'
                for key in ('ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN'):
                    if key != identity['credential_env']:
                        child_env.pop(key, None)
                gateway = resources.enter_context(model_gateway(
                    identity['base_url'], child_env[identity['credential_env']], args.model))
                proc = sandbox_launch(Path.cwd(), command, child_env, gateway_socket=gateway, cwd=Path.cwd(), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=err, text=True)
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
