"""Source-bound retry/budget checks; canned replies are not semantic outcomes."""
import base64,copy,hashlib,json,tempfile,unittest
from pathlib import Path
from defense.core import Controller,Journal,Limits,PublicView,VisibleImage,ValidationError

class ControllerBoundary(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.fixture=json.loads((Path(__file__).parent/'pagination-count-fixture.json').read_bytes())
        p=self.fixture['public'];raws={}
        for message in p['messages']:
            if isinstance(message['content'],list):
                for block in message['content']:
                    if block['type']=='image_url':
                        url=block['image_url'];url=url['url']if isinstance(url,dict)else url
                        raw=base64.b64decode(url.split(',',1)[1]);raws[hashlib.sha256(raw).hexdigest()]=raw
        images=tuple(VisibleImage(raws[i['sha256']],i['role'])for i in p['images'])
        self.view=PublicView(p['observation_id'],p['messages'],images,p['recent_action'],p['execution_feedback'],p['observed_at'])
        self.proposal={'name':'click','payload':{'type':'click','x':559,'y':679},'parsed':True,'executor_fallback_wait':False,'coordinate_space':'normalized_1000'}
    def controller(self,replies):
        self.requests=[]
        def judge(system,view,candidate):
            self.requests.append((system,copy.deepcopy(view.data()),candidate))
            return json.dumps(replies.pop(0))
        return Controller(judge,Journal(Path(self.tmp.name)/'journal'),'joint',Limits(),sleeper=lambda _:None)
    def test_actual_false_support_rechecked_with_original_inputs(self):
        first=copy.deepcopy(self.fixture['verdict']);second=copy.deepcopy(first)
        second['claims'][1]['status']='insufficient';second['claims'][1]['reason']='Exact remaining count is not established by these shortcuts.'
        c=self.controller([first,second]);original=self.view.data();candidate=self.fixture['candidate']
        result=c.inspect('verify',self.view,candidate,self.proposal)
        self.assertEqual(result['claims'][1]['status'],'insufficient');self.assertEqual(c.verifier_calls,2)
        self.assertEqual(first,self.fixture['verdict']);self.assertEqual(self.view.data(),original)
        for _,view,text in self.requests:self.assertEqual(view,original);self.assertEqual(text,candidate)
        self.assertIn('No corrected count',self.requests[1][0])
    def test_repeat_conflict_exhausts_original_retry(self):
        c=self.controller([copy.deepcopy(self.fixture['verdict'])for _ in range(2)])
        with self.assertRaises(ValidationError):c.inspect('verify',self.view,self.fixture['candidate'],self.proposal)
        self.assertEqual(c.verifier_calls,2)
    def test_unrelated_supported_claim_is_unchanged(self):
        row=copy.deepcopy(self.fixture['verdict']);row['claims']=row['claims'][:1]
        c=self.controller([copy.deepcopy(row)])
        result=c.inspect('verify',self.view,self.fixture['candidate'],self.proposal)
        self.assertEqual(result['claims'],row['claims']);self.assertEqual(c.verifier_calls,1)

if __name__=='__main__':unittest.main()
