"""Acceptance and original recovery limits using frozen source replies, no GUI/model."""
import base64,copy,hashlib,json,tempfile,unittest
from pathlib import Path
from defense.core import Controller,Journal,Limits,PublicView,VisibleImage

class ComparisonController(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.fixture=json.loads((Path(__file__).parent/'strict-price-source-fixture.json').read_bytes());p=self.fixture['public'];raws={}
        for message in p['messages']:
            if isinstance(message['content'],list):
                for block in message['content']:
                    if block['type']=='image_url':
                        u=block['image_url'];u=u['url']if isinstance(u,dict)else u;raw=base64.b64decode(u.split(',',1)[1]);raws[hashlib.sha256(raw).hexdigest()]=raw
        self.view=PublicView(p['observation_id'],p['messages'],tuple(VisibleImage(raws[x['sha256']],x['role'])for x in p['images']),p['recent_action'],p['execution_feedback'],p['observed_at'])
        self.proposal={'name':'scroll','payload':{'type':'scroll','direction':'up'},'parsed':True,'executor_fallback_wait':False,'coordinate_space':'normalized_1000'}
    def controller(self):
        cite={'observation_id':self.view.observation_id,'image_index':0,'coordinate_space':'pixels','box_xyxy':[400,160,1130,310],'description':'Source book row'}
        verdict=copy.deepcopy(self.fixture['verdict'])
        # This unit isolates routing. The original reason refers to an archived
        # reference bank; do not impersonate that bank in a current-only fixture.
        # Preserve the real verdict in the fixture, use an explicit canned reason.
        verdict['action']['reason']='Synthetic acceptance-boundary response; current source book row only.'
        replies=[{'status':'usable','visible':['Source book row'],'limitations':[],'loading':'not_observed','evidence':[cite],'reason':'Frozen source test'},verdict]
        self.requests=[]
        def judge(system,view,candidate):self.requests.append((system,view.data(),candidate));return json.dumps(replies.pop(0))
        return Controller(judge,Journal(Path(self.tmp.name)/'journal'),'joint',Limits(probe_history_reports=True),sleeper=lambda _:None)
    def test_actual_equal_group_blocked_without_rewrite(self):
        c=self.controller();text=self.fixture['candidate'];p=copy.deepcopy(self.proposal)
        r=c.decide(self.view,lambda v,x:text,lambda _:p,None)
        self.assertEqual(r['status'],'blocked');self.assertEqual(c.actor_calls,1);self.assertEqual(c.verifier_calls,2);self.assertEqual(p,self.proposal)
        es=[json.loads(x)for x in(c.log.root/'events.jsonl').read_text(encoding='utf-8').splitlines()]
        self.assertTrue(any(e['kind']=='strict_price_comparison'and e['data']['reject']for e in es))
        self.assertFalse(any(e['kind']in {'decision_accepted','action_executed'}for e in es))
    def test_earlier_equal_price_items_not_strictly_cheaper(self):
        c=self.controller();text=self.fixture['candidate'].replace('cheaper items','earlier items')
        r=c.decide(self.view,lambda v,x:text,lambda _:self.proposal,None)
        self.assertEqual(r['status'],'accepted');self.assertEqual(r['candidate'],text);self.assertEqual(r['proposal'],self.proposal)
    def test_original_recovery_limits(self):
        limits=Limits();self.assertEqual(limits.max_regenerations,2);self.assertEqual(limits.max_recaptures,2);self.assertEqual(limits.max_format_retries,1)

if __name__=='__main__':unittest.main()
