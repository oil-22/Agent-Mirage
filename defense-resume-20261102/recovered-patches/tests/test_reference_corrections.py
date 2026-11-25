"""Reference evidence is not indexed into the smaller original actor image list."""
import json,tempfile,unittest
from pathlib import Path
from defense.core import *
from test_controller import view,citation,parse

class ReferenceCorrectionTests(unittest.TestCase):
    def test_past_supported_fact_does_not_crash_current_state_invalidation(self):
        def judge(_,v,candidate):
            self.assertEqual(len(v.images),2)
            reference={**citation(v),'image_index':1}
            return {'claims':[
                {'id':'past','kind':'gui_fact','text':'Previously the item cost5','status':'supported','evidence':[reference],'reason':'past delivered frame','dependent_decisions':[]},
                {'id':'now','kind':'gui_fact','text':'The menu is open','status':'insufficient','evidence':[],'reason':'not established','dependent_decisions':['action']}],
                'action':{'status':'insufficient','target_kind':'unknown','reason':'current menu unknown','evidence':[]},
                'acknowledges_visual_deficit':False,'pure_wait':False}
        with tempfile.TemporaryDirectory()as t:
            root=Path(t)/'journal';c=Controller(judge,Journal(root),'post_only',Limits(max_regenerations=0))
            c.remember(view('past','blue'),'Previously the item cost5')
            result=c.decide(view('now'),lambda *_:'Previously the item cost5. The menu is open.',parse,None)
            self.assertEqual(result['reason'],'regeneration_cap')
            invalidations=[json.loads(line)['data']for line in(root/'events.jsonl').read_text().splitlines()if json.loads(line)['kind']=='state_invalidated']
            fact=next(x for x in invalidations[0]['corrections']if x['claim']=='The menu is open')
            self.assertEqual(fact['confirmed_current_observations'],[])

if __name__=='__main__':unittest.main()
