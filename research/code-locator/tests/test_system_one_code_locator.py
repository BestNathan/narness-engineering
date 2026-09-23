import importlib.util, pathlib, sys, tempfile, unittest

PROJECT_ROOT=pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH=PROJECT_ROOT/'src'/'system_one_code_locator.py'
SPEC=importlib.util.spec_from_file_location('system_one_code_locator',MODULE_PATH)
MODULE=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=MODULE
SPEC.loader.exec_module(MODULE)

class DemoTest(unittest.TestCase):
    def fixture(self):
        return PROJECT_ROOT/'fixtures'/'repository'

    def test_progressive_localization(self):
        with tempfile.TemporaryDirectory() as temp:
            trace=MODULE.Trace(pathlib.Path(temp)/'trace.jsonl')
            scorer=MODULE.OfflineScorer(trace)
            result=MODULE.run(
                self.fixture(),
                'Help me optimize the websocket connection implementation',
                scorer,trace,.35,.50,.50,.60,
            )
            self.assertIn('web/src/ws',[x['id'] for x in result['directories']])
            self.assertIn('web/src/ws/client.ts',[x['id'] for x in result['files']])
            self.assertTrue(any(
                x['path']=='web/src/ws/client.ts' and 'WebSocket' in x['content']
                for x in result['snippets']
            ))
            events=[
                __import__('json').loads(x)['event']
                for x in pathlib.Path(trace.path).read_text().splitlines()
            ]
            self.assertIn('search_started',events)
            self.assertIn('threshold_applied',events)
            self.assertIn('search_completed',events)

    def test_file_frontier_uses_direct_files_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp)/'repo'
            parent=root/'src'
            child=parent/'nested'
            child.mkdir(parents=True)

            (parent/'direct.py').write_text('DIRECT = True\n',encoding='utf-8')
            (child/'nested.py').write_text('NESTED = True\n',encoding='utf-8')

            selected_parent=[{
                'id':'src',
                'payload':{'path':'src'},
                'score':0.9,
            }]
            parent_files=MODULE.files(root,selected_parent)

            self.assertEqual(['src/direct.py'],[x['id'] for x in parent_files])

            selected_both=[
                *selected_parent,
                {
                    'id':'src/nested',
                    'payload':{'path':'src/nested'},
                    'score':0.9,
                },
            ]
            both_files=MODULE.files(root,selected_both)

            self.assertEqual(
                ['src/direct.py','src/nested/nested.py'],
                [x['id'] for x in both_files],
            )

    def test_request_uses_noul(self):
        with tempfile.TemporaryDirectory() as temp:
            trace=MODULE.Trace(pathlib.Path(temp)/'trace.jsonl')
            scorer=MODULE.SystemOneScorer('test',trace)
            candidates=[
                {'id':'web/src/ws','payload':{'path':'web/src/ws'}},
                {'id':'server','payload':{'path':'server'}},
            ]
            scorer._request=lambda payload: {
                'model':'jev-test',
                'answers':{
                    f'candidate_{i}':{'type':'noul','noul':0.5}
                    for i in range(2)
                },
                'usage':{'input_tokens':1,'output_tokens':1},
            }
            scored,_=scorer.score('optimize websocket','directory',candidates)
            self.assertEqual(2,len(scored))
            records=[
                __import__('json').loads(x)
                for x in pathlib.Path(trace.path).read_text().splitlines()
            ]
            request=next(
                x for x in records if x['event']=='system_one_request'
            )['request']
            self.assertTrue(all(
                q['type']=='noul' for q in request['questions'].values()
            ))

    def test_system_one_scores_large_stage_in_one_request(self):
        with tempfile.TemporaryDirectory() as temp:
            trace=MODULE.Trace(pathlib.Path(temp)/'trace.jsonl')
            scorer=MODULE.SystemOneScorer('test',trace,batch_size=2)
            candidates=[
                {'id':f'candidate-{i}','payload':{'path':f'candidate-{i}'}}
                for i in range(125)
            ]
            calls=[]

            def fake_request(payload):
                calls.append(payload)
                return {
                    'model':'jev-test',
                    'answers':{
                        key:{'type':'noul','noul':0.5}
                        for key in payload['questions']
                    },
                    'usage':{'input_tokens':125,'output_tokens':125},
                }

            scorer._request=fake_request
            scored,usage=scorer.score('locate websocket','file',candidates)

            self.assertEqual(1,len(calls))
            self.assertEqual(125,len(calls[0]['questions']))
            self.assertEqual(125,len(scored))
            self.assertEqual(1,usage['model_calls'])

    def test_symbol_frontier_preserves_multiline_semantics(self):
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp)/'repo'
            source=root/'src'
            source.mkdir(parents=True)
            path=source/'client.ts'
            path.write_text(
                'export class Client {\n'
                '  connect(url: string) {\n'
                '    const socket = new WebSocket(url);\n'
                '    socket.onclose = () => this.reconnect(url);\n'
                '  }\n'
                '\n'
                '  reconnect(url: string) {\n'
                '    return this.connect(url);\n'
                '  }\n'
                '}\n',
                encoding='utf-8',
            )
            file={
                'id':'src/client.ts',
                'payload':{
                    'path':'src/client.ts',
                    'filename':'client.ts',
                    'extension':'.ts',
                },
            }

            candidates=MODULE.symbols(root,file)
            by_name={x['payload']['name']:x for x in candidates}

            self.assertIn('Client',by_name)
            self.assertIn('connect',by_name)
            self.assertIn('reconnect',by_name)
            self.assertEqual((2,5),(
                by_name['connect']['payload']['start_line'],
                by_name['connect']['payload']['end_line'],
            ))
            self.assertNotIn('content',by_name['connect']['payload'])
            self.assertIn(
                'connect(url: string)',
                by_name['connect']['payload']['signature'],
            )

    def test_python_multiline_function_is_one_symbol(self):
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp)/'repo'
            source=root/'src'
            source.mkdir(parents=True)
            path=source/'client.py'
            path.write_text(
                'def websocket_connect(url):\n'
                '    socket = open_socket(url)\n'
                '    if socket:\n'
                '        return socket\n'
                '\n'
                'def unrelated():\n'
                '    return None\n',
                encoding='utf-8',
            )
            file={
                'id':'src/client.py',
                'payload':{
                    'path':'src/client.py',
                    'filename':'client.py',
                    'extension':'.py',
                },
            }

            candidates=MODULE.symbols(root,file)
            names=[x['payload']['name'] for x in candidates]

            self.assertEqual(['websocket_connect','unrelated'],names)
            first=candidates[0]['payload']
            self.assertEqual(1,first['start_line'])
            self.assertEqual(5,first['end_line'])

    def test_outline_frontier_groups_symbols_by_scope(self):
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp)/'repo'
            source=root/'src'
            source.mkdir(parents=True)
            (source/'one.ts').write_text(
                'export class One {\n'
                '  connect() { return 1; }\n'
                '  close() { return 2; }\n'
                '}\n',
                encoding='utf-8',
            )
            (source/'two.ts').write_text(
                'export class Two {\n'
                '  unrelated() { return 3; }\n'
                '}\n',
                encoding='utf-8',
            )
            files=[
                {
                    'id':'src/one.ts',
                    'payload':{
                        'path':'src/one.ts',
                        'filename':'one.ts',
                        'extension':'.ts',
                    },
                },
                {
                    'id':'src/two.ts',
                    'payload':{
                        'path':'src/two.ts',
                        'filename':'two.ts',
                        'extension':'.ts',
                    },
                },
            ]

            candidates,symbols_by_outline=MODULE.outlines(root,files)

            self.assertEqual(2,len(candidates))
            one=next(
                item for item in candidates
                if item['payload']['path']=='src/one.ts'
            )
            payload=one['payload']
            self.assertEqual('class',payload['scope_kind'])
            self.assertEqual('One',payload['scope_name'])
            self.assertGreaterEqual(payload['member_count'],3)
            self.assertNotIn('content',payload)
            self.assertTrue(any(
                item['name']=='connect'
                for item in payload['members']
            ))
            self.assertGreaterEqual(
                len(symbols_by_outline[one['id']]),
                3,
            )

    def test_file_level_symbols_share_one_module_scope(self):
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp)/'repo'
            source=root/'src'
            source.mkdir(parents=True)
            (source/'module.py').write_text(
                'def first():\n    return 1\n\n'
                'def second():\n    return 2\n\n'
                'def third():\n    return 3\n',
                encoding='utf-8',
            )
            files=[{
                'id':'src/module.py',
                'payload':{
                    'path':'src/module.py',
                    'filename':'module.py',
                    'extension':'.py',
                },
            }]

            candidates,symbols_by_outline=MODULE.outlines(root,files)

            self.assertEqual(1,len(candidates))
            outline=candidates[0]
            self.assertEqual('module',outline['payload']['scope_kind'])
            self.assertEqual(3,outline['payload']['member_count'])
            self.assertEqual(3,len(symbols_by_outline[outline['id']]))

    def test_outline_selection_gates_symbol_expansion(self):
        class GateScorer:
            model='gate-test'

            def __init__(self):
                self.stages=[]
                self.symbol_ids=[]

            def score(self,query,stage,candidates):
                self.stages.append(stage)
                if stage == 'outline':
                    scored=[]
                    for candidate in candidates:
                        score=0.99 if candidate['payload']['path'].endswith('one.py') else 0.01
                        scored.append({**candidate,'score':score})
                else:
                    scored=[{**candidate,'score':0.99} for candidate in candidates]
                if stage == 'symbol':
                    self.symbol_ids=[x['id'] for x in candidates]
                return scored,{
                    'model_calls':1 if candidates else 0,
                    'input_tokens':0,
                    'output_tokens':0,
                }

        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp)/'repo'
            source=root/'src'
            source.mkdir(parents=True)
            (source/'one.py').write_text(
                'def wanted():\n    return "websocket"\n',
                encoding='utf-8',
            )
            (source/'two.py').write_text(
                'def unwanted():\n    return "other"\n',
                encoding='utf-8',
            )

            trace=MODULE.Trace(pathlib.Path(temp)/'trace.jsonl')
            scorer=GateScorer()
            MODULE.run(
                root,
                'locate websocket',
                scorer,
                trace,
                .1,.1,.5,.1,
            )

            self.assertEqual(
                ['directory','file','outline','symbol'],
                scorer.stages,
            )
            self.assertTrue(scorer.symbol_ids)
            self.assertTrue(all(
                item.startswith('src/one.py::')
                for item in scorer.symbol_ids
            ))

    def test_run_uses_exactly_one_model_call_per_stage(self):
        class CountingScorer:
            model='counting-test'

            def __init__(self):
                self.stages=[]

            def score(self,query,stage,candidates):
                self.stages.append(stage)
                return (
                    [{**candidate,'score':0.99} for candidate in candidates],
                    {
                        'model_calls':1 if candidates else 0,
                        'input_tokens':0,
                        'output_tokens':0,
                    },
                )

        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp)/'repo'
            source=root/'src'
            source.mkdir(parents=True)
            (source/'one.py').write_text(
                'def connect_one():\n    return "websocket"\n',
                encoding='utf-8',
            )
            (source/'two.py').write_text(
                'def connect_two():\n    return "websocket"\n',
                encoding='utf-8',
            )

            trace=MODULE.Trace(pathlib.Path(temp)/'trace.jsonl')
            scorer=CountingScorer()
            result=MODULE.run(
                root,
                'locate websocket connection',
                scorer,
                trace,
                .1,.1,.1,.1,
            )

            self.assertEqual(['directory','file','outline','symbol'],scorer.stages)
            self.assertEqual(4,result['metrics']['model_calls'])
            self.assertEqual('one_request_per_stage',result['metrics']['request_strategy'])
            self.assertEqual(2,result['metrics']['files_selected'])

    def test_transient_520_is_retried(self):
        with tempfile.TemporaryDirectory() as temp:
            trace=MODULE.Trace(pathlib.Path(temp)/'trace.jsonl')
            scorer=MODULE.SystemOneScorer('test',trace)
            calls={'count':0}
            original_urlopen=MODULE.urllib.request.urlopen
            original_sleep=MODULE.time.sleep

            class Response:
                def __enter__(self):
                    return self
                def __exit__(self,*args):
                    return False
                def read(self):
                    return b'{"answers":{},"usage":{}}'

            def fake_urlopen(*args,**kwargs):
                calls['count'] += 1
                if calls['count'] == 1:
                    raise MODULE.urllib.error.HTTPError(
                        'https://api.typesafe.ai/v1/systemone',
                        520,
                        'origin error',
                        hdrs=None,
                        fp=None,
                    )
                return Response()

            try:
                MODULE.urllib.request.urlopen=fake_urlopen
                MODULE.time.sleep=lambda _: None
                scorer._request({'model':'jev-latest','questions':{}})
            finally:
                MODULE.urllib.request.urlopen=original_urlopen
                MODULE.time.sleep=original_sleep

            self.assertEqual(2,calls['count'])
            records=[
                __import__('json').loads(x)
                for x in pathlib.Path(trace.path).read_text().splitlines()
            ]
            retry=next(x for x in records if x['event']=='system_one_retry')
            self.assertEqual(520,retry['status'])

if __name__=='__main__':
    unittest.main()
