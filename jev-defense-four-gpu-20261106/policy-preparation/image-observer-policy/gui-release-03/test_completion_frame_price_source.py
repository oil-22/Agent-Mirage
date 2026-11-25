"""Engineering boundaries, not model/image semantic tests."""
import copy,io,json,tempfile,unittest
from pathlib import Path
from PIL import Image
from defense.core import Controller,Journal,Limits,PublicView,VisibleImage,ValidationError,digest
from completion_frame_price_source import referenced_price_frames,check_completion_frame_prices

class SourceBoundaries(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        b=io.BytesIO();Image.new('RGB',(1280,720),'white').save(b,format='PNG');self.im=VisibleImage(b.getvalue())
        self.view=PublicView('current',[{'role':'user','content':'ACTOR_SENTINEL'}],(self.im,))
    def controller(self,replies):
        self.requests=[]
        def judge(system,v,candidate):self.requests.append((system,v.data(),candidate));return json.dumps(replies.pop(0))
        return Controller(judge,Journal(Path(self.tmp.name)/'journal'),'joint',Limits(),sleeper=lambda _:None)
    def reading(self,visible=None):return {'status':'usable','visible':visible or ['Image0 item A at $5.00'],'limitations':[],'loading':'not_observed','evidence':[{'observation_id':'current','image_index':0,'coordinate_space':'pixels','box_xyxy':[1,1,20,20],'description':'Synthetic test only'}],'reason':'Synthetic only'}
    def relation(self,status):return {'claims':[],'action':{'status':status,'target_kind':'not_applicable','reason':'Synthetic price-source relation only','evidence':[{'source':'candidate','span_id':'full'}]},'pure_wait':False,'acknowledges_visual_deficit':False}
    def test_indices_deduplicated(self):self.assertEqual(referenced_price_frames({'visible':['Reference image8(index8) item at5.00 $']}),[8])
    def test_no_numbered_source_abstains(self):
        c=self.controller([]);r=check_completion_frame_prices(c,self.view,{'visible':['Item at $5.00']});self.assertIsNone(r['agrees']);self.assertFalse(r['reject']);self.assertEqual(c.verifier_calls,0)
    def test_no_price_abstains(self):self.assertEqual(referenced_price_frames({'visible':['Image8 has a book']}),[])
    def test_outside_index_strictly_rejected(self):
        c=self.controller([])
        with self.assertRaises(ValidationError):check_completion_frame_prices(c,self.view,self.reading(['Image1 item at $5.00']))
        self.assertEqual(c.verifier_calls,0)
    def test_negative_relation_withholds_without_edits(self):
        c=self.controller([self.reading(),self.relation('insufficient')]);r=self.reading();old=copy.deepcopy(r);v=copy.deepcopy(self.view.data());a=check_completion_frame_prices(c,self.view,r)
        self.assertTrue(a['reject']);self.assertEqual(r,old);self.assertEqual(self.view.data(),v)
        self.assertIsNone(self.requests[0][2]);self.assertNotIn('ACTOR_SENTINEL',json.dumps(self.requests[0]));self.assertEqual(self.requests[1][1]['images'],[])
    def test_support_is_not_completion_certificate(self):
        c=self.controller([self.reading(),self.relation('supported')]);r=check_completion_frame_prices(c,self.view,self.reading());self.assertFalse(r['reject']);self.assertFalse(r['minimum_certified'])
    def test_frozen_reads_reused_only_as_data(self):
        c=self.controller([self.reading(),self.relation('insufficient'),self.relation('supported')]);a=check_completion_frame_prices(c,self.view,self.reading());b=check_completion_frame_prices(c,self.view,self.reading())
        self.assertEqual(a['source_records_sha256'],b['source_records_sha256']);self.assertEqual(c.verifier_calls,3)
    def test_missing_reference_origin_rejected(self):
        c=self.controller([]);v=PublicView('current',[],(VisibleImage(self.im.raw,'reference'),))
        with self.assertRaises(ValidationError):check_completion_frame_prices(c,v,self.reading())
    def test_ambiguous_candidate_not_supplied(self):
        c=self.controller([self.reading(),self.relation('supported')]);check_completion_frame_prices(c,self.view,self.reading());self.assertNotIn('actual_candidate',json.loads(self.requests[1][2]))

if __name__=='__main__':unittest.main()
