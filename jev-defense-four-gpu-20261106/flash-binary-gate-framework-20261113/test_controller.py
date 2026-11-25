import tempfile,threading,unittest
from pathlib import Path
from gate_core import Decision,digest
from run_controller import run
from test_gate import GOOD,REVISION,CONTRACT
class Adapter:
    def __init__(self):self.dispatches=[];self.observations=[];self.captures=0
    def capture_png(self):self.captures+=1;return GOOD
    def done(self):return len(self.dispatches)>=1
    def actor(self,frame):return 'NATIVE_STOP'
    def parse(self,reply):return reply
    def execute(self,proposal):self.dispatches.append(proposal);return {'environment_action':False,'native_stop':True}
    def observe_result(self,result):self.observations.append(result)
class Tests(unittest.TestCase):
    def test_stop_file_prevents_initial_capture(self):
        with tempfile.TemporaryDirectory()as tmp:
            p=Path(tmp);stop=p/'STOP';stop.touch();a=Adapter()
            r=run(a,client=None,contract_sha256=CONTRACT,evidence=p/'run',stop_file=stop)
            self.assertEqual(r['status'],'cancelled');self.assertEqual(a.captures,0)
    def test_native_stop_is_dispatched_without_claiming_environment_action(self):
        class Check:
            def decide(self,png):return Decision('YES',digest(png),'fresh',REVISION,CONTRACT)
        with tempfile.TemporaryDirectory()as tmp:
            p=Path(tmp);a=Adapter();r=run(a,client=Check(),contract_sha256=CONTRACT,evidence=p/'run',stop_file=p/'STOP')
            self.assertEqual(r['status'],'native_done');self.assertEqual(a.dispatches,['NATIVE_STOP']);self.assertFalse(a.observations[0]['execution']['environment_action'])
    def test_initial_capture_exception_is_technical(self):
        class Broken(Adapter):
            def capture_png(self):raise ConnectionError('original environment disconnected')
        with tempfile.TemporaryDirectory()as tmp:
            p=Path(tmp);a=Broken();r=run(a,client=None,contract_sha256=CONTRACT,evidence=p/'run',stop_file=p/'STOP')
            self.assertEqual(r['status'],'technical_failure');self.assertEqual(r['gate_calls'],0)
if __name__=='__main__':unittest.main(verbosity=2)
