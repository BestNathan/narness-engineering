import importlib.util, pathlib, sys, tempfile, unittest

MODULE_PATH=pathlib.Path(__file__).with_name('system_one_code_locator.py')
SPEC=importlib.util.spec_from_file_location('system_one_code_locator',MODULE_PATH)
MODULE=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=MODULE
SPEC.loader.exec_module(MODULE)

class DemoTest(unittest.TestCase):
    def fixture(self):
        return pathlib.Path(__file__).with_name('fixtures')/'repository'

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

if __name__=='__main__':
    unittest.main()
