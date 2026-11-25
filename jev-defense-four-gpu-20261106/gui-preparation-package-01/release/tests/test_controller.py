"""Scripted callbacks test control-flow guarantees, NOT semantic detector accuracy."""
import io,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image
from defense.core import *

def png(color='white'):
    out=io.BytesIO();Image.new('RGB',(80,60),color).save(out,format='PNG');return out.getvalue()
def view(n='o1',color='white'):
    return PublicView(n,[{'role':'user','content':'Task: find bike'}],(VisibleImage(png(color)),))
def citation(v):return {'observation_id':v.observation_id,'image_index':0,'box_xyxy':[0,0,80,60],'description':'visible area'}
def screen(v,status='usable'):
    return {'status':status,'visible':['frame'],'limitations':[],'loading':'not_observed','evidence':[citation(v)],'reason':'test fixture'}
def verdict(v,status='supported',wait=False):
    return {'claims':[{'id':'c1','kind':'gui_fact','text':'field filled','status':status,'evidence':[citation(v)],'reason':'fixture',
            'dependent_decisions':['action','finish']}],
            'action':{'status':status,'target_kind':'input','reason':'fixture','evidence':[citation(v)]},
            'acknowledges_visual_deficit':False,'pure_wait':wait}
def parse(s):
    if s=='INVALID':raise ValueError('bad native syntax')
    return {'name':'wait'if s=='WAIT'else'click','parsed':True,'executor_fallback_wait':False}

class ControlTests(unittest.TestCase):
    def test_separate_invalidations_survive_later_regeneration(self):
        count=0;seen=[];observed=0
        def judge(_,v,candidate):
            nonlocal count
            if candidate is None:return screen(v)
            count+=1;value=verdict(v,'insufficient'if count<3 else'supported')
            value['claims'][0]['text']='old A'if count==1 else'old B'
            return value
        def actor(v,corrections):
            seen.append(corrections)
            # The flagged assertions must actually occur in the actor source;
            # invented judge text is no longer copied into correction feedback.
            return ['old A','old B','CLICK'][len(seen)-1]
        def capture():
            nonlocal observed
            observed+=1;return view('fresh'+str(observed))
        c=self.ctl(judge)
        self.assertEqual(c.decide(view(),actor,parse,capture)['status'],'accepted')
        claims={x['claim']for x in seen[-1]}
        self.assertTrue({'old A','old B'}<=claims)
    def test_explicit_format_retry_preserves_invalid_raw_and_counts_calls(self):
        replies=iter(['```json\n{}\n```',json.dumps(screen(view()))])
        c=self.ctl(lambda *_:next(replies))
        self.assertEqual(c.inspect('screen',view())['status'],'usable')
        self.assertEqual(c.verifier_calls,2)
        self.assertEqual(sum(x['kind']=='verifier_format_failure'for x in self.events()),1)
    def test_two_bad_replies_remain_failure_without_clamping(self):
        bad=screen(view());bad['evidence'][0]['box_xyxy']=[0,0,1000,1000]
        c=self.ctl(lambda *_:bad)
        with self.assertRaises(ValidationError):c.inspect('screen',view())
        self.assertEqual(c.verifier_calls,2)
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def ctl(self,judge,arm='joint',limits=None):
        j=Journal(self.root/'run');return Controller(judge,j,arm,limits,sleeper=lambda _:None)
    def events(self):return [json.loads(x)for x in (self.root/'run/events.jsonl').read_text().splitlines()]
    def test_baseline_no_judge_and_no_prompt_edit(self):
        def actor(v,c):self.assertEqual(c,[]);self.assertEqual(v.messages,view().messages);return 'CLICK'
        c=self.ctl(lambda *_:self.fail('baseline judge called'),'baseline')
        r=c.decide(view(),actor,parse,None);self.assertEqual(r['status'],'accepted');self.assertTrue(r['execution_pending'])
    def test_missing_image_no_actor_without_fresh_capture(self):
        c=self.ctl(lambda *_:self.fail('judge on missing image'))
        r=c.decide(PublicView('missing',[],()),lambda *_:self.fail('actor called'),parse,None)
        self.assertEqual(r['status'],'blocked');self.assertEqual(c.actor_calls,0)
    def test_corrupt_image_recorded_and_blocked(self):
        c=self.ctl(lambda *_:None)
        r=c.decide(PublicView('bad',[],(VisibleImage(b'badpng'),)),lambda *_:'CLICK',parse,None)
        self.assertEqual(r['status'],'blocked')
    def test_white_metric_is_not_semantic_reject(self):
        c=self.ctl(lambda _,v,cand:screen(v)if cand is None else verdict(v))
        self.assertEqual(c.decide(view(),lambda *_:'CLICK',parse,None)['status'],'accepted')
    def test_unstable_readiness_bounded_no_generation(self):
        c=self.ctl(lambda _,v,cand:screen(v,'limited'))
        counter=iter([view('o2'),view('o3')])
        r=c.decide(view(),lambda *_:self.fail('actor'),parse,lambda:next(counter))
        self.assertEqual(r['recaptures'],2);self.assertEqual(r['status'],'blocked')
    def test_state_fix_requires_new_decision_and_records_old_candidate(self):
        v=iter([view('o2','blue')]);seen=[]
        def judge(_,obs,cand):return screen(obs)if cand is None else verdict(obs,'contradicted'if cand=='WRONG'else'supported')
        def actor(obs,corrections):seen.append(corrections);return 'WRONG'if len(seen)==1 else'FIXED'
        c=self.ctl(judge);r=c.decide(view(),actor,parse,lambda:next(v))
        self.assertEqual(r['status'],'accepted');self.assertEqual(r['candidate'],'FIXED')
        self.assertTrue(seen[1]);self.assertEqual([e['data']['text']for e in self.events()if e['kind']=='candidate'],['WRONG','FIXED'])
        self.assertIsNone(r['semantic_mirage']);self.assertIsNone(r['task_recovered'])
    def test_uncertain_requires_fresh_not_archived_restore(self):
        c=self.ctl(lambda _,v,cand:verdict(v,'uncertain'),'post_only')
        r=c.decide(view(),lambda *_:'CLICK',parse,None)
        self.assertEqual(r['reason'],'live_recapture_unavailable')
    def test_contradiction_can_reconsider_same_current_evidence(self):
        answers=iter(['WRONG','FIXED'])
        c=self.ctl(lambda _,v,cand:verdict(v,'contradicted'if cand=='WRONG'else'supported'),'post_only')
        r=c.decide(view(),lambda *_:next(answers),parse,None)
        self.assertEqual(r['status'],'accepted');self.assertEqual(r['recaptures'],0)
    def test_old_action_still_rejected_after_state_reword(self):
        c=self.ctl(lambda _,v,cand:verdict(v,'contradicted'),'post_only')
        counter=iter([view('o2'),view('o3')])
        r=c.decide(view(),lambda *_:'SAME WRONG CLICK',parse,lambda:next(counter))
        self.assertEqual(r['status'],'blocked');self.assertEqual(r['regenerations'],2)
    def test_fabricated_region_fails_closed(self):
        def judge(_,v,cand):
            x=verdict(v);x['claims'][0]['evidence'][0]['box_xyxy']=[0,0,800,600];return x
        c=self.ctl(judge,'post_only');r=c.decide(view(),lambda *_:'CLICK',parse,None)
        self.assertTrue(r['reason'].startswith('candidate_verifier_error'))
    def test_fabricated_text_citation_rejected(self):
        with self.assertRaises(ValidationError):validate_evidence([{'message_index':0,'quote':'hidden correct answer'}],view())
    def test_parser_failure_not_wait_or_mirage(self):
        c=self.ctl(lambda *_:self.fail('judge'),'baseline');r=c.decide(view(),lambda *_:'INVALID',parse,None)
        self.assertEqual(r['reason'],'native_parser_error');self.assertIsNone(r['semantic_mirage'])
    def test_wait_not_executor_fallback(self):
        self.assertFalse(checked_wait({'name':'wait','parsed':True,'executor_fallback_wait':True}))
        self.assertFalse(checked_wait({'name':'wait','parsed':False}))
    def test_wait_flag_not_blindly_trusted(self):
        c=self.ctl(lambda _,v,cand:verdict(v,wait=True),'post_only')
        r=c.decide(view(),lambda *_:'CLICK',parse,None)
        self.assertEqual(r['reason'],'wait_parser_verifier_disagreement')
    def test_wait_does_not_excuse_a_separate_unsupported_positive_fact(self):
        def judge(_,v,c):
            r=verdict(v,'insufficient',wait=True);r['claims'][0]['text']='field is focused'
            r['action']['status']='supported';return r
        c=self.ctl(judge,'post_only')
        r=c.decide(view(),lambda *_:'WAIT',parse,None)
        self.assertEqual(r['status'],'blocked')
        self.assertTrue(any(e['kind']=='state_invalidated'for e in self.events()))
    def test_wait_loading_hypothesis_is_accepted_without_proving_network_state(self):
        def judge(_,v,c):
            r=verdict(v,wait=True);r['claims'][0].update(kind='hypothesis',text='page is loading',status='uncertain')
            return r
        c=self.ctl(judge,'post_only');r=c.decide(view(),lambda *_:'WAIT',parse,None)
        self.assertEqual(r['status'],'accepted');self.assertEqual(r['regenerations'],0)
    def test_full_history_not_truncated(self):
        messages=[{'role':'assistant','content':f'History{i} '+('long '*400)}for i in range(100)]
        obs=PublicView('long',messages,(VisibleImage(png()),))
        def actor(v,c):self.assertEqual(v.messages,messages);return 'CLICK'
        self.ctl(lambda *_:None,'baseline').decide(obs,actor,parse,None)
    def test_journal_hash_chain_and_immutable_root(self):
        c=self.ctl(lambda *_:None,'baseline');c.decide(view(),lambda *_:'CLICK',parse,None)
        prev='0'*64
        for e in self.events():
            h=e.pop('sha256');self.assertEqual(e['previous'],prev);self.assertEqual(digest(canonical(e)),h);prev=h
        with self.assertRaises(FileExistsError):Journal(self.root/'run')
    def test_fresh_observation_id_required(self):
        c=self.ctl(lambda _,v,cand:screen(v,'limited'))
        with self.assertRaises(ValidationError):c.decide(view(),lambda *_:'CLICK',parse,lambda:view())
    def test_call_budget_failure_not_semantic_negative(self):
        c=self.ctl(lambda *_:None,'post_only',Limits(max_actor_calls=0))
        r=c.decide(view(),lambda *_:self.fail('actor'),parse,None)
        self.assertEqual(r['reason'],'actor_call_cap');self.assertIsNone(r['semantic_mirage'])

if __name__=='__main__':unittest.main(verbosity=2)
