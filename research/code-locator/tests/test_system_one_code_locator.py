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
                scorer,trace,.35,.50,.60,
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
