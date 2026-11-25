"""Guard boundaries/original budget flow; scripted judge is not visual accuracy."""
import copy
import io
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from PIL import Image
from defense.core import Controller, Journal, Limits, PublicView, VisibleImage
from native_direction_consistency import check_direction


def candidate(words,direction='down',kind='scroll'):
    payload={'type':kind,'direction':direction}if kind=='scroll'else{'type':kind}
    return words+'\n<action>'+json.dumps(payload)+'</action>'


def parse(text):
    import re
    x=json.loads(re.findall(r'<action>(.*?)</action>',text,re.S)[0])
    return {'name':x['type'],'payload':x,'parsed':True,'executor_fallback_wait':False}


def view(name='original'):
    out=io.BytesIO();Image.new('RGB',(80,60),'white').save(out,format='PNG')
    return PublicView(name,[{'role':'system','content':'original system'},
                           {'role':'assistant','content':'complete old history preserved'},
                           {'role':'user','content':'Task: inspect actual evidence'}],(VisibleImage(out.getvalue()),))


def verdict(v,wait=False):
    return {'claims':[],'action':{'status':'supported','target_kind':'content','reason':'scripted test only',
            'evidence':[{'observation_id':v.observation_id,'image_index':0,'coordinate_space':'pixels',
                         'box_xyxy':[0,0,80,60],'description':'scripted current image'}]},
            'acknowledges_visual_deficit':False,'pure_wait':wait}


class Boundaries(unittest.TestCase):
    def test_unconditional_conflict_rejects_without_replacement(self):
        s=candidate('I need to scroll up to inspect the image.')
        r=check_direction(s,parse(s));self.assertTrue(r['reject']);self.assertFalse(r['replacement_action_supplied'])
    def test_back_up_is_recognized(self):
        s=candidate('Let me scroll back up to inspect the image.')
        self.assertTrue(check_direction(s,parse(s))['reject'])
    def test_matching_up_allowed(self):
        s=candidate("I'll scroll up to inspect.",'up');self.assertFalse(check_direction(s,parse(s))['reject'])
    def test_matching_down_allowed(self):
        s=candidate('I will scroll down to inspect.');self.assertFalse(check_direction(s,parse(s))['reject'])
    def test_conditional_intent_abstains(self):
        s=candidate('I will scroll up if more evidence is needed.');self.assertFalse(check_direction(s,parse(s))['reject'])
    def test_prior_action_is_not_current_intent(self):
        s=candidate('I scrolled up previously. I will scroll down now.');self.assertFalse(check_direction(s,parse(s))['reject'])
    def test_quote_is_not_current_plan(self):
        s=candidate('The earlier report said "I will scroll up". I will scroll down now.');self.assertFalse(check_direction(s,parse(s))['reject'])
    def test_multiple_intents_abstain(self):
        s=candidate('I will scroll up. I will scroll down.');self.assertEqual(check_direction(s,parse(s))['status'],'ambiguous_or_unrecognized_intent')
    def test_other_action_not_interpreted_as_scroll(self):
        s=candidate('I need to scroll up.',kind='back');self.assertEqual(check_direction(s,parse(s))['status'],'not_scroll')
    def test_pure_wait_excluded_even_with_old_direction_text(self):
        s=candidate('Previous plan: scroll up.',kind='wait');self.assertEqual(check_direction(s,parse(s))['status'],'native_wait_excluded')
    def test_missing_native_direction_abstains(self):
        s=candidate('I will scroll up.');p=parse(s);p['payload'].pop('direction');self.assertFalse(check_direction(s,p)['reject'])
    def test_inputs_not_mutated(self):
        s=candidate('I will scroll up.');p=parse(s);old=copy.deepcopy(p);check_direction(s,p);self.assertEqual(p,old)


class BudgetFlow(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.path=Path(self.tmp.name)/'journal'
    def ctl(self,wait=False,arm='post_only'):
        return Controller(lambda _,v,c:verdict(v,wait),Journal(self.path),arm,Limits(),sleeper=lambda _:None)
    def events(self):return [json.loads(l)for l in(self.path/'events.jsonl').read_text().splitlines()]
    def test_recovery_regenerates_original_json_not_edit(self):
        seq=iter([candidate('I will scroll up.'),candidate('I will scroll up.','up')]);c=self.ctl()
        r=c.decide(view(),lambda *_:next(seq),parse,None)
        self.assertEqual(r['status'],'accepted');self.assertEqual(r['regenerations'],1)
        self.assertEqual(c.actor_calls,2);self.assertEqual(c.verifier_calls,2)
        self.assertEqual([e['data']['text']for e in self.events()if e['kind']=='candidate'][0],candidate('I will scroll up.'))
        self.assertFalse(any(e['kind']=='action_executed'for e in self.events()))
    def test_persistent_conflict_stops_at_original_two_regens(self):
        c=self.ctl();r=c.decide(view(),lambda *_:candidate('I will scroll up.'),parse,None)
        self.assertEqual(r['reason'],'regeneration_cap');self.assertEqual(c.actor_calls,3);self.assertEqual(r['regenerations'],2)
    def test_live_recapture_uses_original_two_cap(self):
        c=self.ctl();n=[]
        def fresh():n.append(1);return replace(view(),observation_id='fresh'+str(len(n)))
        r=c.decide(view(),lambda *_:candidate('I will scroll up.'),parse,fresh)
        self.assertEqual(r['reason'],'regeneration_cap');self.assertEqual(len(n),2)
    def test_full_prefix_retained_on_regeneration(self):
        original=view();seen=[]
        def actor(v,_):
            self.assertEqual(v.messages[:len(original.messages)],original.messages);seen.append(v)
            return candidate('I will scroll up.','down'if len(seen)==1 else'up')
        self.assertEqual(self.ctl().decide(original,actor,parse,None)['status'],'accepted')
        self.assertEqual(len(original.messages),3);self.assertGreater(len(seen[1].messages),len(original.messages))
    def test_baseline_has_no_extra_judge_or_guard(self):
        c=self.ctl(arm='baseline');r=c.decide(view(),lambda *_:candidate('I will scroll up.'),parse,None)
        self.assertEqual(r['status'],'accepted');self.assertEqual(c.verifier_calls,0)
        self.assertFalse(any(e['kind']=='native_direction_consistency'for e in self.events()))
    def test_wait_not_rejected_by_guard(self):
        c=self.ctl(wait=True);r=c.decide(view(),lambda *_:candidate('Waiting.',kind='wait'),parse,None)
        self.assertEqual(r['status'],'accepted');self.assertEqual(r['regenerations'],0)
    def test_original_caps_unchanged(self):
        l=self.ctl().limits;self.assertEqual((l.max_actor_calls,l.max_verifier_calls,l.max_regenerations,l.max_recaptures,l.max_format_retries),(70,140,2,2,1))
    def test_supported_original_verdict_preserved(self):
        c=self.ctl();c.decide(view(),lambda *_:candidate('I will scroll up.'),parse,None)
        rows=[e['data']['verdict']for e in self.events()if e['kind']=='verdict']
        self.assertTrue(rows);self.assertTrue(all(v['action']['status']=='supported'for v in rows))


if __name__=='__main__':unittest.main()
