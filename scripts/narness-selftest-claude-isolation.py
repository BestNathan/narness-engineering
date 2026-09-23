#!/usr/bin/env python3
"""Exercise the production mount policy on a hosted runner, without model calls."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('adapter', ROOT / 'scripts/narness-claude-adapter.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)
runner_spec = importlib.util.spec_from_file_location(
    'runner', ROOT / 'scripts/ai-native-repo-experiment.py')
runner = importlib.util.module_from_spec(runner_spec)
runner_spec.loader.exec_module(runner)

with tempfile.TemporaryDirectory(prefix='isolation-canary-') as temp:
    outer = Path(temp)
    subject = outer / 'subject'
    subject.mkdir()
    subprocess.run(['git', 'init', '-q', str(subject)], check=True)
    hidden = outer / 'gold.json'
    hidden.write_text('hidden evaluation canary')
    prior = outer / 'prior-memory.md'
    prior.write_text('previous run canary')
    (subject / 'escape').symlink_to(hidden)
    (subject / 'hello.txt').write_text('subject')
    (subject / 'node_modules').mkdir()
    (subject / 'node_modules' / 'trusted.js').write_text('trusted dependency')
    probe = r'''
import json, os, socket
from pathlib import Path
assert Path.cwd() == Path('/workspace')
assert Path('hello.txt').read_text() == 'subject'
for path in HIDDEN_PATHS:
    assert not Path(path).exists(), path
assert not Path('/workspace/escape').exists()
assert not Path('/proc/1/root' + HIDDEN_PATHS[0]).exists()
assert not Path('/home/agent/.claude/prior').exists()
assert not Path('/tmp/prior').exists()
assert os.environ['HOME'] == '/home/agent'
assert os.environ['CLAUDE_CONFIG_DIR'] == '/home/agent/.claude'
assert os.environ['TMPDIR'] == '/tmp'
assert 'NARNESS_RUN_DIR' not in os.environ
assert 'GITHUB_TOKEN' not in os.environ
assert 'ANTHROPIC_API_KEY' not in os.environ
assert 'ANTHROPIC_AUTH_TOKEN' not in os.environ
assert 'ANTHROPIC_BASE_URL' not in os.environ
for address in [('1.1.1.1', 443), ('127.0.0.1', 19999)]:
    try:
        socket.create_connection(address, timeout=1)
    except OSError:
        pass
    else:
        raise AssertionError('network namespace escape')
Path('/home/agent/.claude/prior').write_text('private state')
Path('/tmp/prior').write_text('private state')
Path('written.txt').write_text('subject write')
for forbidden in (Path('.git/config'), Path('node_modules/trusted.js')):
    try:
        forbidden.write_text('tampered')
    except OSError:
        pass
    else:
        raise AssertionError(f'read-only agent metadata/dependency is writable: {forbidden}')
try:
    Path('/usr/isolation-write-probe').write_text('forbidden')
except OSError:
    pass
else:
    raise AssertionError('runtime is writable')
print('filesystem, PID view, symlink, environment and private state: PASS')
'''
    probe = probe.replace('HIDDEN_PATHS', repr([str(hidden), str(prior), str(ROOT), str(Path.home())]))
    env = {'ANTHROPIC_API_KEY': 'synthetic-only',
           'ANTHROPIC_BASE_URL': json.dumps([str(hidden), str(prior), str(ROOT), str(Path.home())]),
           'NARNESS_RUN_DIR': str(outer), 'GITHUB_TOKEN': 'must-not-leak'}
    for _ in range(2):
        p = adapter.sandbox_launch(subject, ['/usr/bin/python3', '-c', probe], env,
                                   stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True)
        stdout, stderr = p.communicate(timeout=30)
        assert p.returncode == 0, stderr
        print(stdout.strip())
    assert (subject / 'written.txt').read_text() == 'subject write'
    assert hidden.read_text() == 'hidden evaluation canary'
    argv, clean = adapter.sandbox_command(subject, ['/bin/true'], env)
    assert 'synthetic-only' not in ' '.join(argv), 'credential leaked into argv'
    assert '--unshare-all' in argv
    assert '--disable-userns' not in argv, 'nested Bash sandbox requires user namespaces'
    assert clean['CLAUDE_CODE_SUBPROCESS_ENV_SCRUB'] == '1'
    settings_arg = adapter.cli_args('frozen-model', 'high', 100)
    settings = json.loads(settings_arg[settings_arg.index('--settings') + 1])
    sandbox = settings['sandbox']
    assert sandbox['enabled'] is True
    assert sandbox['failIfUnavailable'] is True
    assert sandbox['allowUnsandboxedCommands'] is False
    assert sandbox['enableWeakerNestedSandbox'] is False
    assert sandbox['excludedCommands'] == []
    assert sandbox['network']['strictAllowlist'] is True
    assert sandbox['network']['allowedDomains'] == []
    assert sandbox['network']['allowUnixSockets'] == []
    assert sandbox['network']['allowAllUnixSockets'] is False
    denied_env = {item['name'] for item in sandbox['credentials']['envVars']
                  if item['mode'] == 'deny'}
    assert {'ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'ANTHROPIC_BASE_URL'} <= denied_env
    # The real installed client must be runnable through exactly the same policy.
    claude = shutil.which('claude')
    assert claude, 'Install the pinned Claude client before the hosted smoke test'
    p = adapter.sandbox_launch(subject, [claude, '--version'], {},
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = p.communicate(timeout=30)
    assert p.returncode == 0, stderr
    print('sandboxed Claude version: ' + stdout.strip())
    calls = []

    class Response:
        status = 200
        chunks = iter([b'data: {"ok":true}\n\n', b''])
        def getheader(self, name, default=None):
            return 'text/event-stream'
        def read1(self, size):
            return next(self.chunks)

    class Connection:
        def __init__(self, host, port, timeout):
            assert (host, port) == ('provider.example', 443)
        def request(self, method, path, body, headers):
            calls.append((method, path, body, headers))
        def getresponse(self):
            return Response()
        def close(self):
            pass

    gateway_probe = r'''
import http.client, json, os
assert os.environ['ANTHROPIC_API_KEY'] == 'sandbox-placeholder'
assert os.environ['ANTHROPIC_BASE_URL'] == 'http://127.0.0.1:18080'
def request(method, path, model, expected, tools=None):
    conn = http.client.HTTPConnection('127.0.0.1', 18080, timeout=10)
    payload = {'model': model}
    if tools is not None:
        payload['tools'] = tools
    conn.request(method, path, json.dumps(payload),
                 {'Host': 'github.com', 'Authorization': 'Bearer attacker'})
    res = conn.getresponse()
    assert res.status == expected, (path, res.status)
    data = res.read()
    conn.close()
    return data
assert b'"ok":true' in request(
    'POST', '/v1/messages?beta=true', 'frozen-model', 200,
    [{'name': 'Bash', 'description': 'local', 'input_schema': {'type': 'object'}}])
request('POST', '/v1/messages', 'other-model', 403)
request('POST', '/v1/messages', 'frozen-model', 403,
        [{'name': 'WebSearch', 'input_schema': {'type': 'object'}}])
request('POST', '/v1/messages', 'frozen-model', 403,
        [{'type': 'web_search_20260318', 'name': 'web_search'}])
request('POST', '/../../gold.json', 'frozen-model', 403)
request('POST', 'https://github.com/gold.json', 'frozen-model', 403)
request('GET', '/v1/messages', 'frozen-model', 501)
request('CONNECT', 'github.com:443', 'frozen-model', 501)
print('fixed-provider gateway, model filter, streaming and credential isolation: PASS')
'''
    with patch.object(adapter.http.client, 'HTTPSConnection', Connection):
        with adapter.model_gateway('https://provider.example/anthropic', 'real-secret-canary', 'frozen-model') as gateway:
            p = adapter.sandbox_launch(subject, ['/usr/bin/python3', '-c', gateway_probe], {},
                                       gateway_socket=gateway, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, text=True)
            stdout, stderr = p.communicate(timeout=30)
            assert p.returncode == 0, stderr
            print(stdout.strip())
    assert len(calls) == 1
    assert calls[0][1] == '/anthropic/v1/messages?beta=true'
    assert calls[0][3]['x-api-key'] == 'real-secret-canary'
    assert calls[0][3]['Authorization'] == 'Bearer real-secret-canary'
    assert 'Host' not in calls[0][3]

    # Prove the nested sandbox runtime can run inside the outer namespace and
    # blocks both the provider TCP bridge and its Unix socket. This is the
    # confused-deputy boundary for Claude's Bash tool.
    dependency_probe = r'''
import shutil
import subprocess
required = ['which', 'rg', 'bwrap', 'socat', 'srt']
missing = [name for name in required if shutil.which(name) is None]
assert not missing, f'outer sandbox hides nested dependencies: {missing}'
for name in ('rg', 'bwrap', 'socat'):
    resolved = subprocess.run(
        ['which', name], text=True, capture_output=True, check=False)
    assert resolved.returncode == 0 and resolved.stdout.strip(), (
        name, resolved.returncode, resolved.stderr)
print('outer namespace nested-sandbox dependencies: PASS')
'''
    p = adapter.sandbox_launch(
        subject,
        ['/usr/bin/python3', '-c', dependency_probe],
        {},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, stderr = p.communicate(timeout=30)
    assert p.returncode == 0, stderr
    print(stdout.strip())

    srt_settings = subject / 'srt-settings.json'
    srt_settings.write_text(json.dumps({
        'network': {
            'allowedDomains': [],
            'deniedDomains': ['127.0.0.1', '[::1]'],
            'allowUnixSockets': [],
            'allowLocalBinding': False,
        },
        'filesystem': {
            'denyRead': [],
            'allowRead': [],
            'allowWrite': ['.'],
            'denyWrite': [],
        },
        'credentials': {
            'envVars': [
                {'name': 'ANTHROPIC_API_KEY', 'mode': 'deny'},
                {'name': 'ANTHROPIC_AUTH_TOKEN', 'mode': 'deny'},
                {'name': 'ANTHROPIC_BASE_URL', 'mode': 'deny'},
            ],
        },
    }))
    bash_probe = r'''
import os, socket
assert 'ANTHROPIC_API_KEY' not in os.environ
assert 'ANTHROPIC_AUTH_TOKEN' not in os.environ
assert 'ANTHROPIC_BASE_URL' not in os.environ
for kind, target in [
    ('tcp', ('127.0.0.1', 18080)),
    ('unix', '/run/provider.sock'),
]:
    sock = socket.socket(socket.AF_INET if kind == 'tcp' else socket.AF_UNIX,
                         socket.SOCK_STREAM)
    sock.settimeout(2)
    try:
        sock.connect(target)
    except OSError:
        pass
    else:
        raise AssertionError(f'{kind} provider channel escaped nested sandbox')
    finally:
        sock.close()
print('nested Bash network/unix-socket isolation: PASS')
'''
    with patch.object(adapter.http.client, 'HTTPSConnection', Connection):
        with adapter.model_gateway(
            'https://provider.example/anthropic',
            'real-secret-canary',
            'frozen-model',
        ) as gateway:
            p = adapter.sandbox_launch(
                subject,
                ['srt', '--settings', '/workspace/srt-settings.json',
                 '/usr/bin/python3', '-c', bash_probe],
                {},
                gateway_socket=gateway,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = p.communicate(timeout=30)
            assert p.returncode == 0, stderr
            print(stdout.strip())

    # Post-agent validation is also a hard sandbox: no host paths, credentials,
    # or network, and controller oracle writes refuse symlink traversal.
    validation = outer / 'validation'
    validation.mkdir()
    subprocess.run(['git', 'init', '-q', str(validation)], check=True)
    (validation / 'hello.txt').write_text('validation')
    (validation / 'oracle-link').symlink_to(hidden)
    try:
        runner.safe_write_beneath(validation, 'oracle-link', 'overwrite')
    except OSError:
        pass
    else:
        raise AssertionError('controller followed an agent-controlled oracle symlink')
    assert hidden.read_text() == 'hidden evaluation canary'

    old_secret = os.environ.get('ANTHROPIC_API_KEY')
    os.environ['ANTHROPIC_API_KEY'] = 'host-secret-must-not-leak'
    try:
        validation_probe = r'''
import os, socket
from pathlib import Path
assert Path.cwd() == Path('/workspace')
assert 'ANTHROPIC_API_KEY' not in os.environ
assert not Path(HIDDEN).exists()
try:
    socket.create_connection(('1.1.1.1', 443), timeout=1)
except OSError:
    pass
else:
    raise AssertionError('validation sandbox has outbound network')
Path('validation-write.txt').write_text('ok')
print('post-agent validation sandbox: PASS')
'''.replace('HIDDEN', repr(str(hidden)))
        result = runner.run_validation_sandbox(
            validation, validation_probe, [])
        assert result['exit_code'] == 0, result['stderr']
        print(result['stdout'].strip())
    finally:
        if old_secret is None:
            os.environ.pop('ANTHROPIC_API_KEY', None)
        else:
            os.environ['ANTHROPIC_API_KEY'] = old_secret

    # The runner-level state contract is a fresh standalone checkout, not merely
    # a fresh HOME. A second checkout cannot observe workspace state from the first.
    source = outer / 'source'
    source.mkdir()
    subprocess.run(['git', 'init', '-q', str(source)], check=True)
    (source / 'base.txt').write_text('base')
    subprocess.run(['git', '-C', str(source), 'add', 'base.txt'], check=True)
    subprocess.run([
        'git', '-C', str(source), '-c', 'user.name=Narness',
        '-c', 'user.email=narness@example.invalid', 'commit', '-qm', 'base'
    ], check=True)
    source_sha = subprocess.check_output(
        ['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    run_a = outer / 'run-a'
    run_b = outer / 'run-b'
    runner.create_isolated_checkout(source, run_a, source_sha)
    (run_a / 'cross-run-canary').write_text('private run state')
    runner.create_isolated_checkout(source, run_b, source_sha)
    assert not (run_b / 'cross-run-canary').exists()
    print('fresh checkout cross-run state isolation: PASS')

    # Linked checkouts must fail before any child is started.
    shutil.rmtree(subject / '.git')
    (subject / '.git').write_text('gitdir: ' + str(outer))
    try:
        adapter.sandbox_command(subject, ['/bin/true'], {})
    except RuntimeError:
        pass
    else:
        raise AssertionError('linked checkout accepted')
print('Hosted Claude execution isolation: PASS (no model requests)')
