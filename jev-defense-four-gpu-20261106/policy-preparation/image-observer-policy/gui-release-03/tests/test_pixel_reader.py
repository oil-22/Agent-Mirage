"""Actual transport projection and preserved strict validation on nonsquare images."""
import copy,io,json,tempfile,unittest
from pathlib import Path
from PIL import Image
from defense.core import *

class PixelReaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.log=Journal(Path(self.tmp.name)/'run')
        raw=io.BytesIO();Image.new('RGB',(1280,720),'white').save(raw,format='PNG')
        self.view=PublicView('obs',[],(VisibleImage(raw.getvalue(),'current'),))
        self.query={'mode':'point_probe','x':667,'y':679,'coordinate_space':'normalized_1000',
                    'pixel_point':[853.76,488.88],'original_size':[1280,720]}
    def tearDown(self):self.tmp.cleanup()
    def result(self,box=(838,470,878,510),space='pixels'):
        return {'kind':'button','visible_text':'fixture','reason':'synthetic geometry only','evidence':[
            {'observation_id':'obs','image_index':0,'coordinate_space':space,'box_xyxy':list(box),'description':'fixture'}]}
    def test_projection_and_log_match_real_sent_payload_original_query_intact(self):
        original=copy.deepcopy(self.query);seen=[]
        def judge(system,v,q):
            self.assertNotIn('normalized',system);self.assertNotIn('679',system)
            self.assertEqual(q,{'mode':'point_probe','coordinate_space':'pixels','pixel_point':[853.76,488.88],'original_size':[1280,720]})
            self.assertEqual(v.images[0].raw,self.view.images[0].raw);seen.append(q)
            return self.result()
        c=Controller(judge,self.log,'joint',Limits());c.inspect('point',self.view,self.query)
        self.assertEqual(self.query,original)
        req=json.loads((self.log.root/'events.jsonl').read_text().splitlines()[0])['data']
        self.assertEqual(req['candidate'],seen[0]);self.assertEqual(req['mechanical_original_query'],original)
    def test_mixed_units_still_fail_on_both_calls_without_repair(self):
        systems=[]
        def judge(s,v,q):systems.append(s);return self.result((845,655,878,705),'normalized_1000')
        c=Controller(judge,self.log,'joint',Limits())
        with self.assertRaisesRegex(ValidationError,'Point not inside'):c.inspect('point',self.view,self.query)
        self.assertEqual(c.verifier_calls,2)
        self.assertIn('coordinate_space pixels on BOTH axes',systems[1])
        self.assertEqual(self.query['x'],667)
    def test_background_unknown_keeps_empty_evidence(self):
        r={'kind':'unknown','visible_text':'','reason':'unidentified','evidence':[]}
        c=Controller(lambda *_:r,self.log,'joint',Limits())
        self.assertEqual(c.inspect('point',self.view,self.query),r)
    def test_projection_does_not_change_total_verifier_cap(self):
        c=Controller(lambda *_:self.result(),self.log,'joint',Limits(max_verifier_calls=0))
        with self.assertRaises(BudgetExhausted):c.inspect('point',self.view,self.query)
        self.assertEqual(c.verifier_calls,0)

if __name__=='__main__':unittest.main()
