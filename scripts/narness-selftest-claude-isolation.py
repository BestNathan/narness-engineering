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
    assert '--unshare-all' in argv and '--disable-userns' in argv
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
def request(method, path, model, expected):
    conn = http.client.HTTPConnection('127.0.0.1', 18080, timeout=10)
    conn.request(method, path, json.dumps({'model': model}),
                 {'Host': 'github.com', 'Authorization': 'Bearer attacker'})
    res = conn.getresponse()
    assert res.status == expected, (path, res.status)
    data = res.read()
    conn.close()
    return data
assert b'"ok":true' in request('POST', '/v1/messages?beta=true', 'frozen-model', 200)
request('POST', '/v1/messages', 'other-model', 403)
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
    # Linked checkouts must fail before any child is started.
    shutil.rmtree(subject / '.git')
    (subject / '.git').write_text('gitdir: ' + str(outer))
    try:
        adapter.sandbox_command(subject, ['/bin/true'], {})
    except RuntimeError:
        pass
    else:
        raise AssertionError('linked checkout accepted')
print('Hosted Claude filesystem isolation: PASS (no model requests)')
