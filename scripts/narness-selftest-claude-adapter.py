#!/usr/bin/env python3
"""Synthetic protocol tests; never real pilot evidence."""
import importlib.util
import json
from pathlib import Path
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('claude_adapter',ROOT/'scripts/narness-claude-adapter.py')
adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)

def call(ident,name,values):
    return {'type':'assistant','message':{'content':[{'type':'tool_use','id':ident,'name':name,'input':values}]}}
def result(ident,text='',error=False):
    return {'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':ident,'content':text,'is_error':error}]}}
def done():
    return {'type':'result','subtype':'success','is_error':False,
            'usage':{'input_tokens':10,'cache_creation_input_tokens':20,'cache_read_input_tokens':30,'output_tokens':5},
            'modelUsage':{'claude-test-model':{}}}

with tempfile.TemporaryDirectory() as td:
    trace=Path(td)/'trace.jsonl'
    t=adapter.Translator(trace,time.monotonic())
    read=call('r','Read',{'file_path':'/workspace/web/app.ts'})
    t.process(read);t.process(read) # Repeated assistant envelope is not a second call.
    t.process(result('r','source'))
    t.process(call('e','Edit',{'file_path':'/workspace/web/app.ts'}));t.process(result('e','ok'))
    t.process(call('b','Bash',{'command':'npm run build'}))
    t.process({'type':'tool_progress','parent_tool_use_id':'b',
                'tool_use_id':'b-heartbeat-0','tool_name':'Bash'})
    t.process(result('b','failure',True))
    t.process(done());t.finish()
    events=[json.loads(x) for x in trace.read_text().splitlines()]
    assert [e['type'] for e in events]==['read','edit','command','validation','usage']
    assert events[0]['path']=='web/app.ts'
    assert events[1]['paths']==['web/app.ts']
    assert events[3]['exit_code']==1
    assert events[-1]['input_tokens']==60 and events[-1]['cached_tokens']==30
    assert events[-1]['output_tokens']==5 and events[-1]['reasoning_tokens_available'] is False
    for bad in [done(), {'type':'assistant','parent_tool_use_id':'nested'},
                {'type':'tool_progress','parent_tool_use_id':'nested',
                 'tool_use_id':'nested-heartbeat-0','tool_name':'Bash'},
                call('x','WebFetch',{}),result('unknown')]:
        try: t.process(bad)
        except RuntimeError: pass
        else: raise AssertionError('invalid event was accepted')
    incomplete=adapter.Translator(Path(td)/'incomplete.jsonl',time.monotonic())
    incomplete.process(call('open','Read',{'file_path':'web/a.ts'}))
    try: incomplete.finish()
    except RuntimeError: pass
    else: raise AssertionError('incomplete stream accepted')
    bad_usage=adapter.Translator(Path(td)/'missing.jsonl',time.monotonic())
    try: bad_usage.process({'type':'result','subtype':'success'})
    except RuntimeError: pass
    else: raise AssertionError('missing usage accepted')
args=adapter.cli_args('claude-test-model','high',100)
assert '--no-session-persistence' in args and '--strict-mcp-config' in args
assert '--disable-slash-commands' in args and '--setting-sources' in args
assert 'Agent' not in adapter.TOOLS.split(',')
print('Claude stream translation, Bash progress heartbeats, cache accounting, replay rejection, and CLI contract: PASS')

# The common freezer must bind Claude raw evidence and reject image drift.
spec=importlib.util.spec_from_file_location('profile_test',ROOT/'scripts/selftest-ai-native-execution-profile.py')
profile_test=importlib.util.module_from_spec(spec);spec.loader.exec_module(profile_test)
with tempfile.TemporaryDirectory() as td:
    pilots=[]
    for task,treatment in [('T05','A'),('T08','B'),('T20','C')]:
        p=profile_test.make_pilot(Path(td),task=task,treatment=treatment,harness_sha='synthetic',scorer_sha='synthetic')
        cfg=json.loads((p/'trace.jsonl').read_text())
        cfg.update(
            agent='claude-code',
            claude_version='synthetic-cc',
            claude_bin='/usr/local/bin/claude',
            base_url='https://api.example.invalid',
            credential_env='ANTHROPIC_API_KEY',
            runtime_mode='bubblewrap-claude-bash-sandbox-provider-gateway-v2',
            bubblewrap_version='bubblewrap synthetic',
            sandbox_runtime_version='0.0.synthetic',
            provider_policy='fixed-https-origin-route-model-local-tool-schema-no-server-tools-v2',
            permission_profile='claude-bubblewrap-bash-sandbox-provider-gateway-v2',
            filesystem_read_scope='current subject plus read-only runtime; read-only .git/dependencies; private HOME/tmp',
            bash_network='strict-deny-all-including-loopback-and-unix-sockets',
            git_metadata='read-only',
            shell_environment_allowlist=[
                'PATH', 'HOME', 'CLAUDE_CONFIG_DIR', 'XDG_CONFIG_HOME',
                'XDG_CACHE_HOME', 'TMPDIR', 'TMP', 'TEMP', 'LANG',
                'SHELL', 'USER', 'ANTHROPIC_BASE_URL', 'ANTHROPIC_API_KEY',
                'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC',
                'CLAUDE_CODE_SUBPROCESS_ENV_SCRUB',
            ],
            harness_environment_scrubbed=True,
            command_mapper_sha256='synthetic',
        )
        (p/'trace.jsonl').write_text(json.dumps(cfg)+'\n')
        (p/'codex.raw.jsonl').rename(p/'claude.raw.jsonl')
        pilots.append(p)
    output=Path(td)/'profile.json'
    first=profile_test.freeze(pilots,output)
    assert first.returncode==0,first.stdout
    profile=json.loads(output.read_text())
    assert all('claude.raw.jsonl' in x['artifacts'] for x in profile['source_pilots'])
    assert 'command_mapper_file_sha256' in profile['tooling']
    cfg=json.loads((pilots[2]/'trace.jsonl').read_text());cfg['claude_bin']='/tmp/changed-claude'
    (pilots[2]/'trace.jsonl').write_text(json.dumps(cfg)+'\n')
    second=profile_test.freeze(pilots,output)
    assert second.returncode!=0 and 'claude_bin' in second.stdout
print('Claude profile evidence and installed-client drift gate: PASS')
